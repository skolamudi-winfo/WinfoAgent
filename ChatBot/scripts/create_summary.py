import json
from datetime import datetime, timezone, timedelta

from src.app.chatbot.aiAgents import SupportAgent as sa
from src.app.utils.loggerConfig import LoggerManager as lg
from src.app.chatbot.chatBot import ChatOperations as co
from src.app.services.nosqlConnection import NoSQLTableManager as tm
from src.app.services.nosqlConnection import NoSQLConnectionManager


class CreateSummary:
    """"""

    @classmethod
    def __get_chat_len(cls, prev_chats, loger):
        loger.info("Chat count function called.")
        try:
            messages = prev_chats.get("messages", [])
            return len(messages)
        except Exception as e:
            loger.error(f"Failed to find the len of messages. Error details: {e}")
            return 0

    @classmethod
    def _summarizer(cls, each_ticket, nosql_conn, logger,
                    google_key_config_path='../configuration/Google_Key(WinfoBots).json'):
        logger.info("Ticket summarizer function called.")
        previous_conv = []

        issue_id = each_ticket.get('issue_id')
        chat_id = each_ticket.get('chat_id')
        processed_msg_id = int(each_ticket.get('processed_message_id'))
        total_summary = each_ticket.get('summary')
        ticket_description = total_summary.get('ticket_description ')
        ai_comments = total_summary.get('ai_comments')
        ticket_comments = total_summary.get('all_comments')
        chat_summary = total_summary.get('chat_summary')
        customer_name = each_ticket.get('customer_name')
        processed_comment_id = each_ticket.get('processed_comment_id')
        processed_comment_id = int(processed_comment_id)
        product_name = each_ticket.get('product_name')

        prev_chat_cnt, prev_chats = co.get_chat_history(chat_id, nosql_conn, logger)
        chat_len = cls.__get_chat_len(prev_chats, logger)
        nxt_msgs_cnt = chat_len - processed_msg_id

        if prev_chat_cnt > 0 and processed_msg_id > 0:
            previous_conv = co.prev_chats_list(prev_chats, logger, prev_chat_cnt=nxt_msgs_cnt)

        if len(previous_conv) == 0:
            return

        try:
            unprocessed_ticket_comments = ticket_comments[processed_comment_id:]
        except Exception as e:
            logger.error(f"Unable to parse the unprocessed comments. Error: {e}")
            unprocessed_ticket_comments = []

        chat_summary = sa.Agents.agent5(
            customer_name, product_name, ticket_description, unprocessed_ticket_comments, previous_conv,
            chat_summary, ai_comments, nosql_conn, logger, google_key_config_path=google_key_config_path
        )

        each_ticket['summary']['chat_summary'] = chat_summary
        each_ticket["last_accessed_time"] = datetime.now(timezone.utc).isoformat(timespec='microseconds')

        try:
            update_flg = tm.execute_update_query(nosql_conn, each_ticket, 'TicketSummary')
        except Exception as e:
            logger.error(
                f"Failed to update chat summary for chat id - {chat_id} with issue ticket - {issue_id}. Error: {e}"
            )


    @classmethod
    def summarizer_schedular(
            cls, nosql_conn, logger, google_key_config_path='../configuration/Google_Key(WinfoBots).json'
    ):
        logger.info("Summary schedular function called.")

        chat_summary_query = f'''
        select 
            issue_id,
            chat_id,
            processed_message_id,
            ticket_status,
            summary,
            customer_name,
            processed_comment_id,
            product_name,
            last_accessed_time
        from TicketSummary
        '''

        print(f"chat_summary_query: {chat_summary_query}")

        try:
            data = tm.execute_select_query(nosql_conn, chat_summary_query)
            now = datetime.now(timezone.utc)
            time_threshold = now - timedelta(hours=3)
            chat_summary_details = []
            for row in data:
                last_accessed = row.get('last_accessed_time')
                if last_accessed is not None:
                    if last_accessed.tzinfo is None:
                        last_accessed = last_accessed.replace(tzinfo=timezone.utc)
                    if last_accessed >= time_threshold:
                        chat_summary_details.append(row)
        except Exception as e:
            logger.error(f"Failed to get the summary details from DB. Error details: {e}\nchat_summary_query: {chat_summary_query}")
            chat_summary_details = []

        print(f"chat_summary_details: {chat_summary_details}")
        try:
            for each_ticket in chat_summary_details:
                cls._summarizer(
                    each_ticket,
                    nosql_conn,
                    logger,
                    google_key_config_path=google_key_config_path
                )
        except Exception as e:
            logger.error(f"Failed to summarize the tickets from ticket summary table. Error details: {e}")


if __name__ == '__main__':
    l_logger = lg.configure_logger('logs/CreateSummary')
    pool_name = 'app_db_conn_summary'
    with open('configuration/db_config.json', 'rb') as db_details:
        config_data = json.load(db_details)

    if config_data['WAI_NoSQL'] and str(config_data['WAI_NoSQL']['DatabaseType']).lower() == 'nosql':
        oci_config_data = config_data['WAI_NoSQL']
    else:
        oci_config_data = None

    l_nosql_conn = NoSQLConnectionManager.get_nosql_conn(
        nosql_db_details=oci_config_data,
        private_key_file='../certs/oci_private.pem'
    )

    CreateSummary.summarizer_schedular(
        l_nosql_conn,
        l_logger,
        google_key_config_path='configuration/Google_Key(WinfoBots).json'
    )

    NoSQLConnectionManager.close_nosql_conn(l_nosql_conn)
    lg.shutdown_logger(l_logger)
