import os
import json
from datetime import datetime, timezone
import time
from vertexai.generative_models import Part
import asyncio
from borneo import PutRequest
import mimetypes
import uuid


from src.app.utils.pdfStringExtract import PDFUtils as pdfu
from src.app.utils.dataValidation import Utils as ut
from src.app.services.vertixAIActivities import VertexAIService as pr
from src.app.services.gcsActivities import GCSManager as gcs
from src.app.services.embeddingActivites import EmbeddingManager as em
from src.app.chatbot.aiAgents import SalesAgent as sa
from src.app.chatbot.aiAgents import SupportAgent as supa
from src.app.services.nosqlConnection import NoSQLTableManager as tm
from src.app.utils.pdfStringExtract import PDFProcessor as pdfp


class PDFProcessingService:
    @classmethod
    def upload_pdf_to_gcs(cls, file_path, gcs_folder, logger, pdf_chuck_size=5, download_path = '../DownloadedFiles', google_key_path='../configuration/Google_Key(Inizio).json', bucket_name='chatbot_winfo_bots'):
        """
        Splits a PDF file into chunks and uploads each chunk to Google Cloud Storage (GCS).
        """
        pdf_chunk_file_paths = pdfu.split_pdf(file_path, file_name=os.path.basename(file_path).split('.')[0],
                                              logger=logger, pdf_chuck_size=pdf_chuck_size, download_path=download_path)

        for pdf_chunk_file_path in pdf_chunk_file_paths:
            upload_status = gcs.upload_to_gcs(
                bucket_name, pdf_chunk_file_path,
                f'{gcs_folder}/{os.path.basename(pdf_chunk_file_path)}', logger,
                google_key_path=google_key_path
            )

            if upload_status:
                logger.info(f"PDF file {os.path.basename(pdf_chunk_file_path)} uploaded to GCS.")
            else:
                logger.error(f"Error uploading PDF file {os.path.basename(pdf_chunk_file_path)} to GCS.")


class ChatOperations:
    """"""

    @classmethod
    def generate_chat_id(cls):
        return str(uuid.uuid4())

    @classmethod
    def get_chat_id(cls, issue_id: str, nosql_conn):
        chat_id_q = f"SELECT chat_id FROM ChatSessions WHERE issue_id = '{issue_id}'"
        new_chat_id = tm.execute_select_query(nosql_conn, chat_id_q)
        try:
            new_chat_id = new_chat_id[0].get('chat_id')
            chat_id = new_chat_id
            return chat_id
        except Exception as e:
            raise e

    @classmethod
    def get_chat_history(cls, chat_id, nosql_conn, logger, issue_id=None):
        logger.info(
            f"Getting chat history for chat_id: {chat_id} and issue_id: {issue_id}"
        )

        if issue_id:
            prv_chats_cnt_q = f"SELECT count(1) as count FROM ChatSessions WHERE issue_id = '{issue_id}'"
        else:
            prv_chats_cnt_q = f"SELECT count(1) as count FROM ChatSessions WHERE chat_id = '{chat_id}'"

        try:
            prv_chats_cnt = tm.execute_select_query(nosql_conn, prv_chats_cnt_q)
            prv_chats_cnt = prv_chats_cnt[0].get('count')
        except Exception as e:
            logger.error(f"Error occurred while getting previous chat count. error: {e}\nchat session count query: {prv_chats_cnt_q}")
            prv_chats_cnt = 0

        try:
            if issue_id:
                chat_id_q = f"SELECT chat_id FROM ChatSessions WHERE issue_id = '{issue_id}'"
                new_chat_id = tm.execute_select_query(nosql_conn, chat_id_q)
                new_chat_id = new_chat_id[0].get('chat_id')
                chat_id = new_chat_id

            prv_chats_query = f"""
            select 
                message_id, 
                user_message, 
                response, 
                message_time, 
                response_time, 
                nearest_neighbours, 
                error_msg 
            from ChatMessages WHERE chat_id = '{chat_id}'
            order by message_id
            """

            prv_chats = tm.execute_select_query(nosql_conn, prv_chats_query)
        except Exception as e:
            logger.error(f"Error occurred while getting previous chats. error: {e}")
            prv_chats = None

        chat_hist = {}
        if prv_chats:
            try:
                session_details_q = f"""
                SELECT 
                    session_id, 
                    chat_id, 
                    user_name, 
                    start_time, 
                    end_time, 
                    meta_data 
                FROM ChatSessions 
                WHERE chat_id = '{chat_id}'
                """
                session_details = tm.execute_select_query(nosql_conn, session_details_q)
                session_details = session_details[0]
                for item in prv_chats:
                    item["message_id"] = int(item["message_id"])

                prv_chats = sorted(prv_chats, key=lambda x: x["message_id"])

                for chat in prv_chats:
                    try:
                        msg_feedback_query = f"""
                        SELECT 
                            feedback 
                        FROM ChatFeedback 
                        where chat_id = '{chat_id}' 
                            and message_id = {int(chat.get('message_id'))}
                        """
                        msg_feedback = tm.execute_select_query(nosql_conn, msg_feedback_query)
                        msg_feedback = msg_feedback[0].get('feedback')
                    except Exception as e:
                        logger.warning(
                            f"Unable to find feedback for \nchat id: {chat_id}\nmessage id: {chat.get('message_id')}"
                            f"\nError: {e}"
                        )
                        msg_feedback = {}

                    chat['message_id'] = str(chat.pop('message_id', ''))
                    chat['user_message'] = chat.pop('user_message', '')
                    chat['response'] = chat.get('response', '')
                    chat['message_time'] = chat.pop('message_time', '') #.strftime('%Y-%m-%d %H:%M:%S.%f')
                    chat['response_time'] = chat.get('response_time', '') #.strftime('%Y-%m-%d %H:%M:%S.%f')
                    chat['nearest_neighbours'] = chat.get('nearest_neighbours', '')
                    chat['error_msg'] = chat.get('error_msg', '')
                    chat['feedback'] = msg_feedback

                session_details['start_time'] = session_details.get('start_time') #.strftime('%Y-%m-%d %H:%M:%S.%f')
                session_details['end_time'] = session_details.get('end_time') #.strftime('%Y-%m-%d %H:%M:%S.%f')
                session_details['messages'] = prv_chats

                chat_hist = session_details
            except Exception as e:
                logger.error(f"Failed to get the chat history from DB. Error details: {e}")
            # print(f"chat_hist: {chat_hist}")
        return chat_hist, prv_chats_cnt

    @classmethod
    def prev_chats_list(cls, prev_chat, logger, prev_chat_cnt=3):
        """
        Extracts the last three chat messages after sorting by message_id.

        Args:
            prev_chat (dict): The input JSON data as a Python dictionary.

        Returns:
            list: A list of the last three chat messages.
            :param logger:
            :param prev_chat:
            :param prev_chat_cnt:
        """
        logger.info(f"getting the previous {prev_chat_cnt} chat history function called.")
        messages = prev_chat.get("messages", [])
        previous_queries = []

        try:
            if not messages:
                return []  # Return empty list if no messages exist

            # Sort messages by message_id (assuming numeric values)
            sorted_messages = sorted(messages, key=lambda x: int(x["message_id"]), reverse=True)

            # Get the last three chats
            last_chats = sorted_messages[:prev_chat_cnt]

            for chat in last_chats:
                temp_query = {
                    "Query": f"{chat['user_message']}",
                    "Response": f"{chat['response']}"
                }
                previous_queries.append(temp_query)
        except Exception as e:
            logger.error(f"Failed to get the previous {prev_chat_cnt} chat history. Error details: {e}")

        return previous_queries

    @classmethod
    def _initiate_chat(cls, session_id, chat_id, user_name, model_name, product, query_level, logger):
        logger.info('Initiate chat function called.')
        initiated_chat = {
            'session_id': session_id,
            'chat_id': chat_id,
            'user_name': user_name,
            'start_time': datetime.now(timezone.utc).isoformat(timespec='microseconds'),
            'end_time': '',
            'meta_data': {
                'model_used': model_name,
                'topic': product,
                'query_level': query_level
            },
            'messages': []
        }

        return initiated_chat

    @classmethod
    def _add_message_to_chat(cls, prv_chat, user_message, nearest_neighbours, logger):
        logger.info('Add message to chat function called.')
        messages = prv_chat.get("messages", [])
        try:
            if messages:
                message_id = max(int(item.get("message_id")) for item in messages) + 1
            else:
                message_id = 1
        except Exception as e:
            logger.error(f"Failed to get the maximum query id. Error details: {e}")
            message_id = 1

        # print(f"message_id: {message_id}")
        message_dict = {
                    'message_id': str(int(message_id)),
                    'user_message': user_message,
                    'response': '',
                    'message_time': datetime.now(timezone.utc).isoformat(timespec='microseconds'),
                    'response_time': '',
                    'nearest_neighbours': str(int(nearest_neighbours)),
                    'error_msg': ''
                }
        prv_chat['messages'].append(message_dict)

        # print(f"prv_chat after: {prv_chat}")
        return prv_chat, message_id

    @classmethod
    def _update_chat(cls, full_chat, resp, message_id, error_msg, logger):
        logger.info('Update chat function called.')
        try:
            full_chat['messages'][message_id - 1]['response'] = resp
            full_chat['messages'][message_id - 1]['response_time'] = datetime.now(timezone.utc).isoformat(timespec='microseconds')
            full_chat['messages'][message_id - 1]['error_msg'] = error_msg
            full_chat['end_time'] = datetime.now(timezone.utc).isoformat(timespec='microseconds')
        except Exception as e:
            logger.error(f"Error executing while updating chat: {e}")

        return full_chat

    @classmethod
    def _store_chat_db(cls, prv_chats_cnt, full_chat, session_id, chat_id, nosql_conn, logger, issue_id=''):
        logger.info('Store chat to db function called.')
        # print(f"prv_chats_cnt: {prv_chats_cnt}")
        # db_cursor.setinputsizes(chat=oracledb.DB_TYPE_CLOB)

        if prv_chats_cnt == 0:
            session_insertion_data = {
                "session_id": session_id,
                "chat_id": chat_id,
                "user_name": full_chat.get('user_name'),
                "start_time":full_chat.get('start_time'),
                "end_time":full_chat.get('end_time'),
                "meta_data":full_chat.get('meta_data')
            }
            if issue_id:
                session_insertion_data['issue_id'] = issue_id

            # print(f"full_chat: {full_chat}")

            try:
                # print(f"session_insertion_data: {session_insertion_data}")
                insertion_flg = tm.execute_insert_query(nosql_conn, session_insertion_data, 'ChatSessions')
                # for each_msg in full_chat.get('messages'):
                each_msg = full_chat.get('messages')[-1]
                msg_insertion_data = {
                    "chat_id": full_chat.get('chat_id'),
                    "message_id": each_msg.get('message_id'),
                    "user_message": each_msg.get('user_message'),
                    "response": each_msg.get('response'),
                    "message_time": each_msg.get('message_time'),
                    "response_time": each_msg.get('response_time'),
                    "nearest_neighbours": each_msg.get('nearest_neighbours'),
                    "error_msg": each_msg.get('error_msg')
                }
                # print(f"msg_insertion_data: {msg_insertion_data}")
                msg_insert_flg = tm.execute_insert_query(nosql_conn, msg_insertion_data, 'ChatMessages')
            except Exception as e:
                logger.error(f"Error executing while inserting chats to db: {e}")
                return False
        else:
            session_update_data = {
                "session_id": session_id,
                "chat_id": chat_id,
                "user_name": full_chat.get('user_name'),
                "start_time":full_chat.get('start_time'),
                "end_time":full_chat.get('end_time'),
                "meta_data":full_chat.get('meta_data')
            }
            if issue_id:
                session_update_data['issue_id'] = issue_id

            try:
                update_flg = tm.execute_update_query(nosql_conn, session_update_data, 'ChatSessions')
                # for each_msg in full_chat.get('messages'):
                each_msg = full_chat.get('messages')[-1]
                msg_insertion_data = {
                    "chat_id": full_chat.get('chat_id'),
                    "message_id": each_msg.get('message_id'),
                    "user_message": each_msg.get('user_message'),
                    "response": each_msg.get('response'),
                    "message_time": each_msg.get('message_time'),
                    "response_time": each_msg.get('response_time'),
                    "nearest_neighbours": each_msg.get('nearest_neighbours'),
                    "error_msg": each_msg.get('error_msg')
                }
                msg_insert_flg = tm.execute_insert_query(nosql_conn, msg_insertion_data, 'ChatMessages')
            except Exception as e:
                logger.error(f"Error executing while updating chats to db: {e}\nfull chat: {full_chat}")
                return False

        return True

    @classmethod
    def _get_prev_msgs(cls, prev_chat, logger, prv_chat_cnt=3):
        logger.info('Get chat history function called.')
        len_prev_chat = len(prev_chat['messages'])
        if len_prev_chat == 0:
            return []
        elif len_prev_chat < prv_chat_cnt:
            prv_chat_cnt = len_prev_chat
        else:
            prv_chat_cnt = prv_chat_cnt

        if prv_chat_cnt > 0:
            prev_msgs = prev_chat['messages'][-prv_chat_cnt:]
        else:
            prev_msgs = prev_chat['messages']

        return prev_msgs

    @classmethod
    def get_max_message_id(cls, session_id, chat_id, nosql_conn, logger, issue_id=None):
        logger.info(f"Maximum query id function called with session id: {session_id} and chat id: {chat_id}.")

        prev_chat, prv_chats_cnt = cls.get_chat_history(chat_id, nosql_conn, logger, issue_id=issue_id)

        if prv_chats_cnt == 0:
            return 0

        try:
            messages = prev_chat.get("messages", [])

            if messages:
                max_message_id = max(int(item["message_id"]) for item in messages)
            else:
                max_message_id = 0
        except Exception as e:
            logger.error(f"Failed to get the maximum query id. Error details: {e}")
            max_message_id = 0

        return max_message_id

    @classmethod
    def get_chat_response(cls, chat_id, message_id, nosql_conn, logger):
        logger.info(f"Getting the chat response function called.")

        try:
            chat_text_query = f"select response from ChatMessages WHERE chat_id = '{chat_id}' and message_id = '{message_id}'"
            chat_text = tm.execute_select_query(nosql_conn, chat_text_query)
            chat_text = chat_text[0].get('response')
        except Exception as e:
            logger.error(f"Failed to get the message response for \nchat id: {chat_id}\nmessage id: {message_id}\nError: {e}")
            chat_text = ''

        return chat_text

    @classmethod
    def update_message_feedback(cls, msg_feedback: dict, nosql_conn, logger):
        logger.info(f"Update message feedback function called with message feedback: {msg_feedback} .")
        try:
            feed_insert_flg = tm.execute_insert_query(nosql_conn, msg_feedback, 'ChatFeedback')
        except Exception as e:
            logger.error(f"Failed to insert feedback. \nError: {e}")
            feed_insert_flg = False

        return feed_insert_flg


class SalesChatBot(ChatOperations):
    """"""

    class EmbeddingService:
        @classmethod
        def store_question_embedding_db(cls, conn, logger,
                                        google_key_config_path='configuration/Google_Key(WinfoBots).json'):
            from concurrent.futures import ThreadPoolExecutor
            from typing import Tuple
            logger.info('store_question_embedding_db() called.')

            with conn.cursor() as db_cursor:
                content_questions_query = "SELECT QUERY_ID, QUERY FROM SALES_CONTENT_EMBEDDING_NEW WHERE embedding IS NULL ORDER BY 1"
                db_cursor.execute(content_questions_query)
                questions_data = db_cursor.fetchall()

            def process_question(question: Tuple[int, str]):
                query_id, query = question
                logger.info(f'Thread started: query_id={query_id}, query={query}')

                try:
                    query_embedding = em.get_embedding(
                        str(query), logger,
                        embedding_model='text-embedding-005',
                        dimensions=256,
                        google_key_config_path=google_key_config_path
                    )

                    if not query_embedding:
                        logger.warning(f"No embedding found for query_id={query_id}")
                        return

                    status = cls._update_question_embedding_db(
                        query_embedding, query_id, conn, logger
                    )
                    if not status:
                        logger.error(f"Update failed for query_id={query_id}")

                except Exception as e:
                    logger.exception(f"Error in thread for query_id={query_id}: {str(e)}")

            with ThreadPoolExecutor(max_workers=20) as executor:
                executor.map(process_question, questions_data)

        @classmethod
        def _update_question_embedding_db(cls, embedding, query_id, conn, logger):
            """
            Updates the embedding for a question in the database.
            """
            logger.info('update_question_embedding_db() called.')
            embedding = json.dumps(embedding)
            update_query = (
                "update SALES_CONTENT_EMBEDDING_NEW set embedding = :embedding where query_id = :query_id"
            )
            with conn.cursor() as db_cursor:
                try:
                    db_cursor.execute(
                        update_query,
                        {
                            'embedding': embedding,
                            'query_id': query_id
                        }
                    )
                    db_cursor.connection.commit()
                    return True
                except Exception as e:
                    logger.error(f"Error executing update_question_embedding_query: {e}")
                    logger.error(f"query_id: {query_id}, embedding: {embedding}")
                    return False


    class QuestionService:
        @classmethod
        def _get_questions(cls, content_id, title, content, product, logger,
                           google_key_config_path='../configuration/Google_Key(WinfoBots).json'):
            """
            Generates FAQ questions and detailed answers based on content using the prompting service.
            """

            system_instructions = f"""
    Your agenda is to create a FAQ questions for the information provided related to {product} Solution. 
    This FAQ questions will be helpful for Sales team to answer them to the clients, so create questions assuming that you heard about the topic which will be provided as an input and then answer the question based on the input provided assuming you are an {product} expert. 
    Make the questions as depth as possible and elaborate answers as much as possible so my sales team have the best information to gear up for the sales discussion. 
    Generate the maximum no.of questions we may get based content provided.
    For each question, provide a detailed and elaborate answer, in the format provided below.
    Ensure that the output is in exact JSON format.
    output: 
    {{ "result":[
    {{
      "question": "<question>",
      "answer": "<answer based on the content>"
    }},
    {{
      "question": "<question>",
      "answer": "<answer based on the content>"
    }}]
    }}

    Example output:
    {{
      "result": [
        {{
          "answer": "The WinfoBot dashboard status page is a feature within the WinfoBot application that allows users to monitor the progress of their asset retirement processes. It provides real-time updates on the status of each process they have initiated through the Winfobot.",
          "question": "What is the Winfobot dashboard status page?"
        }},
        {{
          "answer": "You can access the status page by clicking on the \"Asset Retirement\" option within the Winfobot application. This will redirect you to a page displaying the current status of all your asset retirement processes.",
          "question": "How do I access the status page of the Winfobot dashboard?"
        }},
        {{
          "answer": "The status page displays the progress of asset retirement processes initiated through Winfobot. It shows whether a process is 'New' (initiated), 'Failed' (encountered an error), or 'Success' (completed successfully).",
          "question": "What kind of information does the status page provide?"
        }},
        {{
          "answer": "The possible status updates are:\r\n\r\n   New: This indicates that the asset retirement process has just been initiated and is awaiting further processing.\r\n   Failed: This indicates that the asset retirement process encountered an error during execution. The user will also receive an error notification.\r\n   Success: This indicates that the asset retirement process has been completed successfully. The user will see a 'Success' status on the application and will also receive a success email.",
          "question": "What are the different status updates and what do they mean?"
        }}
      ]
    }}
            """
            response_schema = {
                "type": "OBJECT",
                "properties": {
                    "result": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "question": {
                                    "type": "STRING",
                                    "description": "The question asked."
                                },
                                "answer": {
                                    "type": "STRING",
                                    "description": "The answer to the question based on the provided content."
                                }
                            },
                            "required": [
                                "question",
                                "answer"
                            ]
                        },
                        "description": "An array of question-answer pairs."
                    }
                },
                "required": [
                    "result"
                ]
            }
            questionnaire_prompt = f"""
            Title of the content: {title}
            Given the following content:'''
            {content}
            '''
            """

            questions = pr.get_prompt_response(questionnaire_prompt, logger,
                                               google_key_config_path=google_key_config_path,
                                               response_schema=response_schema, system_instruction=system_instructions)

            try:
                start_index = questions.find('{')
                end_index = questions.rfind('}') + 1
                questions = questions[start_index:end_index]
                # questions = questions.replace('\\n', '\n').replace('\\t', '\t').replace('*', '')
                questions = json.loads(questions)  # Convert response to JSON
                # questions = json.dumps(questions, indent=4)
                # questions = json.loads(questions)
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON response for content_id - {content_id}: {e}")
                logger.error(f"content_id: {content_id}, questions: {questions}")
                questions = {'result': []}
            except Exception as e:
                logger.error(f"Error processing content_id - {content_id}: {e}")
                questions = {'result': []}

            return questions

        @classmethod
        def store_questions_db(cls, product, conn, logger, google_key_config_path='../configuration/Google_Key(WinfoBots).json'):
            """
            Fetches unprocessed content from the database, generates FAQ questions for it, and stores them.
            """
            logger.info('store_questions_db() called.')

            with conn.cursor() as db_cursor:
                contents_query = "select CONTENT_ID, TITLE, CONTENT from SALES_CONTENT WHERE QUESTIONS_GENERATED = 'No' order by 1"
                db_cursor.execute(contents_query)
                contents = db_cursor.fetchall()

                for content in contents:
                    content_id = content[0]
                    print(f"content id: {content_id}")
                    title = content[1]
                    content = content[2]
                    questions = cls._get_questions(content_id, title, content, product, logger,
                                                   google_key_config_path=google_key_config_path)
                    logger.info(f'questions: {questions}')
                    if len(questions['result']) > 0:
                        insert_status = cls._insert_questions_db(content_id, questions, db_cursor, logger)
                        if insert_status:
                            cls._update_sales_content_table(content_id, db_cursor, logger)
                    db_cursor.connection.commit()
                    time.sleep(10)

            logger.info("Finished processing all questions.")

        @classmethod
        def _insert_questions_db(cls, content_id, questions, db_cursor, logger):
            """
            Inserts generated FAQ questions into the database.
            """
            logger.info('insert_questions_db() called.')
            insertion_status = True

            for each_item in questions['result']:
                question = each_item['question']
                answer = each_item['answer']
                query_insertion = (
                    "insert into SALES_CONTENT_EMBEDDING_NEW (QUERY_ID, CONTENT_ID, QUERY, ANSWER) "
                    "values (SALES_CONTENT_EMBEDDING_SEQ.nextval, :content_id, :query, :answer)"
                )
                try:
                    db_cursor.execute(
                        query_insertion,
                        {
                            'content_id': content_id,
                            'query': ut.clean_string(question).lower(),
                            'answer': answer
                        }
                    )
                except Exception as e:
                    logger.error(f"Error executing query_insertion: {e}")
                    logger.error(f"content_id: {content_id}, query: {question}")
                    insertion_status = False

            return insertion_status

        @classmethod
        def _update_sales_content_table(cls, content_id, db_cursor, logger):
            """
            Marks content as processed (questions generated) in the database.
            """
            logger.info('update_sales_content_table() called.')

            sales_content_table_update = "update SALES_CONTENT set questions_generated = 'Yes' where content_id = :content_id"
            try:
                db_cursor.execute(
                    sales_content_table_update,
                    {
                        'content_id': content_id
                    }
                )
            except Exception as e:
                logger.error(f"Error executing sales_content_table_update: {e}")
                logger.error(f"content_id: {content_id}")


    class DatabaseService:
        @classmethod
        def _store_content_to_db(cls, content, file_name, product, db_cursor, logger):
            """
            Stores extracted content into the database.
            """
            flg = True
            logger.info('store_content_to_db() called.')
            try:
                content = json.loads(content)
                content = content['content']
                if len(content) == 0:
                    return False

                content_insert_query = """
                INSERT INTO SALES_CONTENT(content_id, content, title, created_date, file_name, product, QUESTIONS_GENERATED) 
                VALUES(sales_content_id_seq.nextval, :content, :title, sysdate, :file_name, :product, 'No')
                """

                for each_item in content:
                    logger.info(f'each_item: {each_item}, file_name: {file_name}, product: {product}')
                    title = each_item['section_title']
                    text = each_item['section_text']
                    # print(len(str(text).split()))
                    if len(str(text).split()) <= 20:
                        continue
                    try:
                        db_cursor.execute(
                            content_insert_query,
                            {
                                'content': text,
                                'title': title,
                                'file_name': file_name,
                                'product': product
                            }
                        )
                    except Exception as e:
                        logger.error(f"Error executing content_insert_query: {e}")
                        logger.error(f"content: {content}, title: {title}, file_name: {file_name}")
                        flg = False
                    db_cursor.connection.commit()
            except Exception as e:
                logger.error(f"Error storing content to database: {e}")
                logger.error(f"content: {content}, file_name: {file_name}")
                flg = False

            return flg


    class ContentPreparationService(DatabaseService):
        @classmethod
        def content_preparation(cls, bucket_name, gcs_folder_path, product, db_cursor, logger,
                                google_key_config_path='../configuration/Google_Key(WinfoBots).json'):
            """
            Reads files from GCS, processes their content, and stores the processed data in the database.
            """
            logger.info('content_preparation() called.')

            list_of_files = gcs.get_files_in_gcs(bucket_name, gcs_folder_path, logger,
                                                 google_key_path=google_key_config_path)
            list_of_files = list_of_files['files']
            # print(f'list_of_files: {list_of_files}')

            for file in list_of_files:
                # print(f'file: {file}')
                blob_name = str(file['blob_name'])
                file_name = str(file['file_name'])
                file_path = str(file['file_path'])
                # print(f'blob_name: {blob_name}')
                # print(f'file_name: {file_name}')

                # downloaded_file_path = gcs.download_from_gcs(
                #     bucket_name, blob_name, f'../DownloadedFiles/{file_name}', logger, google_key_path=google_key_config_path
                # )
                # print(f'downloaded_file_path: {downloaded_file_path}')

                # pdf_content = pdfp.get_pdf_string(downloaded_file_path, '', logger)
                file_part = Part.from_uri(
                    uri=file_path,
                    mime_type="application/pdf",
                )
                prompt = """
                analyze the provided attachment and extract the actual content from it. with proper headings when required.
                """
                system_instruction = """
                You are a very professional document analyzer specialist. Understand the documents provided and return the response based on the prompt asked by the user
                we might have images inside the pdf, analyze the images as well inside the pdf.
                """
                # system_instruction = """
                # You are a very professional document analyzer specialist. Understand the documents provided it might have images inside the pdf, analyze the images and extract the data from pdf.
                # """

                contents = [file_part, prompt]
                pdf_content = pr.get_prompt_response(
                    contents, logger, model_name='gemini-2.0-flash',
                    system_instruction=system_instruction,
                    google_key_config_path=google_key_config_path
                )

                try:
                    # pdf_content = json.loads(pdf_content)
                    # pdf_content = pdf_content['response']

                    if len(pdf_content) == 0:
                        continue
                    # else:
                    #     pdf_content = '\n'.join(pdf_content)

                    # print(f'pdf_content: {pdf_content}')

                    response_schema = {
                        "type": "OBJECT",
                        "properties": {
                            "content": {
                                "type": "ARRAY",
                                "items": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "section_title": {
                                            "type": "STRING",
                                            "description": "The title of the section."
                                        },
                                        "section_text": {
                                            "type": "STRING",
                                            "description": "The text content of the section."
                                        }
                                    },
                                    "required": [
                                        "section_title",
                                        "section_text"
                                    ]
                                },
                                "description": "An array of content sections."
                            }
                        },
                        "required": [
                            "content"
                        ]
                    }
                    system_instruction = '''
    You are an expert document segmentation analyst. Your task is to analyze the following document text and divide it into logically distinct sections, each representing a separate and coherent topic. The goal is to maximize clarity and organization for the reader. The number of sections should be determined by the inherent topic divisions within the document, striving for a structure that allows each section to be understood independently. Consider potential overlap and redundancy, aiming to minimize both. Focus on creating sections with a clear scope and internal coherence. Don't make any changes to the actual content until it required. Analyze the entire pdf provided and extract the actual content from the provided pdf based on the sections divided to store it in section_text.

    For each section, output the following in JSON format:

    {
    "content": [
    {
    "section_title": "<A concise and descriptive title for the section>",
    "section_text": "<The exact text from the document that belongs to this section>"
    },
    {
    "section_title": "<A concise and descriptive title for the section>",
    "section_text": "<The exact text from the document that belongs to this section>"
    },
    ...
    ]
    }
                    '''

                    prompt = f"""
                        Document text: {pdf_content}
                        """
                    try:
                        response = pr.get_prompt_response(prompt, logger, google_key_config_path=google_key_config_path,
                                                          system_instruction=system_instruction,
                                                          response_schema=response_schema)

                        start_index = response.find('{')
                        end_index = response.rfind('}') + 1
                        file_content = response[start_index:end_index]
                        # print(file_content)

                        ins_status = cls._store_content_to_db(file_content, file_name, product, db_cursor, logger)
                        if ins_status:
                            gcs.delete_from_gcs(bucket_name, blob_name, logger, google_key_path=google_key_config_path)
                            logger.info(f"File {file_name} deleted from GCS.")
                    except Exception as e:
                        logger.error(f"Error processing file {file_name} after prompt: {e}")
                except Exception as e:
                    logger.error(f"Error processing file {file_name}: {e}")

                # print(f"")
                # break
                time.sleep(10)


    @classmethod
    def _advanced_search(cls, user_query, model_name, google_key_config_path, nearest_neighbours, db_cursor, logger, previous_conversation=''):
        logger.info('Sales Bot started with advanced search.')
        try:

            res_ag1 = sa.Agents.agent1(user_query, logger, model_name=model_name,
                                       google_key_config_path=google_key_config_path, previous_conversation=previous_conversation)
            # print(f"Sales chart bot response for agent1: {res_ag1}")

            res_ag1 = json.loads(res_ag1)
            ls_ag1 = res_ag1['questions_to_answer']

            res_ag2 = sa.Agents.agent2(user_query, ls_ag1, logger, model_name=model_name,
                                       google_key_config_path=google_key_config_path, previous_conversation=previous_conversation)
            # print(f"Sales chart bot response for agent2: {res_ag2}")
            logger.info(f"Final agent2 response: {res_ag2}")

            categorized_questions = sa.GetContents.categorize_questions(res_ag2, logger)
            # print(f"categorized_questions: {categorized_questions}")
            logger.info(f"Categorized questions: {categorized_questions}")

            r_specific_responses = sa.GetContents.get_specific_questions_contents(
                categorized_questions['all_specific_questions'], db_cursor, logger,
                nearest_neighbours=nearest_neighbours,
                google_key_config_path=google_key_config_path,
                model_name=model_name
            )
            # print(f"specific_responses: {r_specific_responses}")

            r_generic_responses = sa.GetContents.get_generic_questions_contents(
                categorized_questions['all_generic_questions'], logger, google_key_config_path=google_key_config_path)
            # print(f"generic_responses: {r_generic_responses}")

            final_content = []
            if len(r_specific_responses) > 0:
                final_content.extend(r_specific_responses)

            if len(r_generic_responses) > 0:
                # final_content.extend(r_generic_responses)
                dist_sub_questions = []
                for each in final_content:
                    dist_sub_questions.append(each['ag1_question'])

                for each_generic_response in r_generic_responses:
                    if each_generic_response['ag1_question'] in dist_sub_questions:
                        final_content[dist_sub_questions.index(each_generic_response['ag1_question'])][
                            'response'] += f"\n\n{each_generic_response['response']}"
                    else:
                        final_content.append(each_generic_response)

            # print(f"final_content: {final_content}")

            f_res = ""
            retry = True
            retry_count = 0
            while retry:
                # Generate chatbot response based on the retrieved content
                ag4_resp = sa.Agents.agent4(user_query, final_content, '', logger, model_name=model_name,
                                            google_key_config_path=google_key_config_path, previous_conversation=previous_conversation)
                f_res += f"\n{ag4_resp['response']}"
                retry_count += 1
                if str(ag4_resp['finished_response']).lower() == 'yes' or retry_count == 5:
                    retry = False

            if len(categorized_questions['all_more_info_questions']) > 0:
                for each_more_info_questions in categorized_questions['all_more_info_questions']:
                    # ag1_question = each_more_info_questions['ag1_question']
                    sub_questions = each_more_info_questions['sub_questions']
                    if len(sub_questions) > 0:
                        for each_more_info_question in sub_questions:
                            f_res += f"\n\n{each_more_info_question}"
        except Exception as e:
            logger.error(f'Failed to complete advanced search for the user question. Error details: {e}')
            f_res = ''

        return f_res


    @classmethod
    def _basic_search(cls, user_query, model_name, google_key_config_path, nearest_neighbours, db_cursor, logger,
                      specific_details='WinfoBots', previous_conversation=''):
        logger.info("Sales Bot started with basic search.")
        user_query = ut.clean_string(user_query).lower()
        # print(f"each_sub_question: {each_sub_question}")
        prompt_resp = sa.Agents.basic_agent(
                user_query, db_cursor, logger, model_name=model_name,
                specific_details=specific_details, google_key_config_path=google_key_config_path,
                nearest_neighbours=nearest_neighbours, previous_conversation=previous_conversation
            )
        # print(f"prompt_resp: {prompt_resp}")

        return prompt_resp


    @classmethod
    async def sales_chatbot(cls, data, conn, logger, model_name='gemini-2.0-flash-001', nearest_neighbours=50, google_key_config_path='../configuration/Google_Key(WinfoBots).json'):
        """
        Main function to process a user query and generate a response.

        Uses an embedding of the query to find related content from the database,
        retrieves the corresponding content, and generates a chatbot response.
        """
        with conn.cursor() as db_cursor:
            try:
                if data:
                    user_query = data.get('question')
                    session_id = data.get('session_id')
                    user_name = data.get('user_name')
                    query_level = data.get('query_level')
                    product_name = data.get('product_name')
                    try:
                        chat_id = data['chat_id']
                    except KeyError:
                        logger.info('New chat started.')
                        chat_id = None
                else:
                    logger.error('No data received in the request.')
                    return '', '', ''

                error_msg = ''
                f_res = ''

                if not chat_id:
                    return 'Unable to fetch the response. Please contact support team.', '', ''
                prev_chat, prv_chats_cnt = cls.get_chat_history(chat_id, conn, logger)
                # print(f"prev_chat before adding new msg: {prev_chat}")
                # print(f"prv_chats_cnt: {prv_chats_cnt}")

                if not prev_chat:
                    prev_chat = cls._initiate_chat(session_id, chat_id, user_name, model_name, f'{product_name} Pre-Sales Agent', query_level, logger)
                    previous_conversation = ''
                else:
                    previous_conversation = cls.prev_chats_list(prev_chat, logger, prev_chat_cnt=3)

                prev_chat, query_id = cls._add_message_to_chat(prev_chat, user_query, nearest_neighbours, logger)
                # print(f"prev_chat after adding new msg: {prev_chat}")
                # print(f"query_id: {query_id}")
                if str(query_level).lower() == 'advanced':
                    f_res = cls._advanced_search(user_query, model_name, google_key_config_path, nearest_neighbours, db_cursor, logger, previous_conversation=previous_conversation)
                elif str(query_level).lower() == 'basic':
                    f_res = cls._basic_search(user_query, model_name, google_key_config_path, nearest_neighbours, db_cursor, logger, previous_conversation=previous_conversation, specific_details=product_name)
                else:
                    error_msg = f"Invalid query level: {query_level}. Please enter 'basic' or 'advanced'."
            except Exception as e:
                logger.error(f'Failed to start bot. Error details: {e}')
                error_msg = f"Error occurred while starting bot. Error details: {e}"

            full_chat = cls._update_chat(prev_chat, f_res, query_id, error_msg, logger)
            # print(f"full_chat: {full_chat}")
            # print(f"prv_chats_cnt: {prv_chats_cnt}")
            store_chat_status = cls._store_chat_db(prv_chats_cnt, full_chat, session_id, chat_id, db_cursor, logger)
            logger.info(f"Store chat status: {store_chat_status}")

        return f_res, chat_id, query_id


class SupportChatBot(ChatOperations):
    """"""

    @classmethod
    async def support_agent(
            cls, data, ai_db_conn, nosql_conn, logger, model_name='gemini-2.0-flash-001', nearest_neighbours=50,
            google_key_config_path='../configuration/Google_Key(WinfoBots).json'
    ):
        """
        The Main function to process a user query and generate a response.

        Uses an embedding of the query to find related content from the database,
        retrieves the corresponding content, and generates a chatbot response.
        """
        logger.info(f"Support chat agent called with following data:\n{data}")

        error_msg = ''

        if data:
            user_message = data.get('user_message')
            session_id = data.get('session_id')
            chat_id = data.get('chat_id')
            user_name = data.get('user_name')
            jira_ticket_id = data.get('issue_id').strip()
            customer_name = data.get('customer_name')
            product_name = data.get('product_name')
            sub_process = ''
            ticket_description = ''
            ticket_status = ''
            ticket_comments = ''
            process_name = ''
            initial_analysis = ''
        else:
            logger.error('No data received in the request.')
            return '', '', ''

        with ai_db_conn.cursor() as app_db_cursor:
            try:
                ticket_details_query = """
                SELECT description, ticket_status, all_comments, process_name, sub_process, ai_comments 
                from support_tickets where jira_ticket_id = :jira_ticket_id and customer_name = :customer_name
                """
                app_db_cursor.execute(
                    ticket_details_query,
                    {
                        'jira_ticket_id': jira_ticket_id,
                        'customer_name': customer_name
                    }
                )
                ticket_details = app_db_cursor.fetchone()
                ticket_description = ticket_details[0].read() if ticket_details[0] else ''
                ticket_status = ticket_details[1]
                ticket_comments = ticket_details[2].read() if ticket_details[2] else ''
                process_name = ticket_details[3]
                sub_process = ticket_details[4]
                initial_analysis = ticket_details[5].read() if ticket_details[5] else ''
            except Exception as e:
                logger.error(
                    f"""
                    Failed to get the ticket info from db for \nticket id - {jira_ticket_id}, 
                    \ncustomer_name - {customer_name}. Error details: {e}\nticket_details_query: {ticket_details_query}
                    """
                )

        if not chat_id:
            return 'Unable to fetch the response. Please contact support team.', '', ''
        prev_chat, prv_chats_cnt = cls.get_chat_history(chat_id, nosql_conn, logger, issue_id=jira_ticket_id)
        # print(f"prev_chat before adding new msg: {prev_chat}")
        # print(f"prv_chats_cnt: {prv_chats_cnt}")

        if not prev_chat:
            prev_chat = cls._initiate_chat(
                session_id, chat_id, user_name, model_name, f"{product_name} Support Agent",
                'Advanced', logger
            )

            '''Initiating chat summary'''
            asyncio.create_task(
                supa.initial_ticket_summary(
                    chat_id, jira_ticket_id, ticket_status, ticket_description, ticket_comments,
                    initial_analysis, customer_name, product_name, nosql_conn, logger, google_key_config_path
                )
            )

            previous_conversation = ''
        else:
            previous_conversation = cls.prev_chats_list(prev_chat, logger, prev_chat_cnt=3)

        prev_chat, message_id = cls._add_message_to_chat(prev_chat, user_message, nearest_neighbours, logger)
        # print(f"prev_chat after adding new msg: {prev_chat}")
        # print(f"message_id: {message_id}")

        try:
            chat_summary_query = f"""
                select 
                    summary 
                from TicketSummary 
                where chat_id = '{chat_id}' 
                and customer_name = '{customer_name}'
            """
            summary = tm.execute_select_query(nosql_conn, chat_summary_query)
            chat_summary = summary[0].get('summary').get('chat_summary')
        except Exception as e:
            logger.warning(f"Failed to get the chat summary from db. Error details: {e}")
            chat_summary = ''

        try:
            process_flow_query = f"""
            SELECT 
                process_details 
            FROM CustomerProcessDetails 
            where customer_name = '{customer_name}' 
            """

            if process_name:
                process_flow_query += " and process_name = '{process_name}'"
                process_data = tm.execute_select_query(nosql_conn, process_flow_query)
                process_flow = process_data[0].get('process_details').get('flow')
            else:
                process_flow = ''
        except Exception as e:
            logger.error(
                f"Failed to get the process flow for customer - {customer_name} with process - {process_name}. Error details:{e}"
            )
            process_flow = ''

        try:
            f_res = cls._advanced_search(
                user_message,
                ticket_description,
                initial_analysis=initial_analysis,
                chat_summary=chat_summary,
                product_name=product_name,
                process_name=process_name,
                customer_name=customer_name,
                sub_process=sub_process,
                google_key_config_path=google_key_config_path,
                process_flow=process_flow,
                ai_db_conn=ai_db_conn,
                nosql_conn=nosql_conn,
                logger=logger,
                previous_conversation=previous_conversation
            )
        except Exception as e:
            logger.error(f'Failed to start bot. Error details: {e}')
            error_msg = f"Error occurred while starting bot. Error details: {e}"
            f_res = {'resolution':'Agent is not responding. Please contact support team..'}

        full_chat = cls._update_chat(prev_chat, f_res, message_id, error_msg, logger)
        # print(f"full_chat: {full_chat}")
        # print(f"prv_chats_cnt: {prv_chats_cnt}")
        # with ai_db_conn.cursor() as ai_db_cursor:
            # print(f"jira_ticket_id: {jira_ticket_id}")
        store_chat_status = cls._store_chat_db(prv_chats_cnt, full_chat, session_id, chat_id,
                                               nosql_conn, logger, issue_id=jira_ticket_id)
        logger.info(f"Chat storing completed with status - {store_chat_status}")

        return f_res, chat_id, message_id


    @classmethod
    def _advanced_search(
            cls, user_message, ticket_description, initial_analysis, chat_summary, product_name, process_name,
            customer_name, sub_process, google_key_config_path, process_flow, ai_db_conn, nosql_conn,
            logger, previous_conversation=''
    ):
        logger.info('Sales Bot started with advanced search.')
        final_content = []
        try:
            res_ag6 = supa.Agents.agent6(
                product_name, previous_conversation, user_message, chat_summary, customer_name, process_name,
                process_flow, nosql_conn, logger, google_key_config_path=google_key_config_path
            )
            res_ag6 = json.loads(res_ag6)

            categorized_questions = supa.GetContents.group_questions_by_source(res_ag6, logger)
            # print(f"categorized_questions: {categorized_questions}")
            logger.info(f"Categorized questions: {categorized_questions}")

            doc_resp, winfo_db_data, oracle_db_data = supa.Agents.agent3(
                categorized_questions, product_name, process_name, customer_name, ai_db_conn, nosql_conn,
                logger, google_key_config_path=google_key_config_path
            )

            final_content.extend(doc_resp)
            final_content.extend(winfo_db_data)
            final_content.extend(oracle_db_data)

            # print(f"final_content: {final_content}")

            ag7_resp = supa.Agents.agent7(
                customer_name, product_name, ticket_description, initial_analysis, nosql_conn, logger,
                final_content, chat_summary, previous_conversation, user_message,
                google_key_config_path=google_key_config_path
            )
            f_res = {}
            if ag7_resp:
                ag7_resp = json.loads(ag7_resp)
                f_res['resolution'] = ag7_resp.get('resolution')
                assumptions = ag7_resp.get('assumptions')
                if assumptions:
                    f_res['assumptions'] = assumptions
                additional_questions = ag7_resp.get('additional_questions')
                if additional_questions:
                    f_res['additional_questions'] = additional_questions

        except Exception as e:
            logger.error(f'Failed to complete advanced search for the user question. Error details: {e}')
            f_res = {'resolution':'Agent is not responding. Please contact support team..'}

        return f_res


class OracleSupportProcessFiles:
    """"""
    class EmbeddingService:
        @classmethod
        def store_content_embedding_db(
                cls, nosql_conn, conn, logger, google_key_config_path='../configuration/Google_Key(WinfoBots).json',
                location='us-central1'
        ):
            """
            Fetches unprocessed questions from DB, generates embeddings, and stores them in the DB.
            """
            logger.info('store content embedding to db function called.')
            records_flg = True
            while records_flg:
                pass
                all_contents_query = f"""
                SELECT *
                FROM SupportDocumentsContent
                WHERE questions_generated = 'No' 
                and product_name = 'Oracle'
                """
                all_contents = tm.execute_select_query(nosql_conn, all_contents_query)
                logger.info(f"all_contents: {all_contents}")
                print(f"Query for contents: \n{all_contents_query}")
                print(f"all_contents: {all_contents}")
                if len(all_contents) == 0:
                    records_flg = False
                with conn.cursor() as db_cursor:
                    for content in all_contents:
                        content_id = content.get('content_id')
                        # title = content.get('content_details').get('title')
                        content_text = content.get('content_details').get('content')
                        process_name = content.get('process_name')
                        product_name = content.get('product_name')
                        process_area = content.get('process_area')
                        sub_process = content.get('sub_process')
                        customer_name = content.get('customer_name')
                        # print(
                        #     f"content id: {content_id},\ncontent_text: {content_text},\nprocess_name: {process_name},"
                        #     f"\nproduct_name: {product_name},\nprocess_area: {process_area},\nsub_process: {sub_process}"
                        # )
                        print(f"content id: {content_id}")

                        content_embedding = em.get_embedding(
                            ut.clean_string(content_text).lower(), logger, embedding_model='text-embedding-005', dimensions=256,
                            google_key_config_path=google_key_config_path, location=location
                        )
                        logger.info(f'query_embedding: {content_embedding}')
                        if len(content_embedding) == 0:
                            logger.info(f"No embedding found for content id - {content_id}")
                            continue

                        insert_status = cls._insert_questions_db(
                            content_id,
                            product_name,
                            process_name,
                            process_area,
                            sub_process,
                            customer_name,
                            content_embedding,
                            db_cursor,
                            logger
                        )
                        conn.commit()
                        if not insert_status:
                            logger.error(f"Error inserting content_embedding for content_id - {content_id}")
                        else:
                            content['questions_generated'] = "Yes"
                            update_flg = tm.execute_update_query(nosql_conn, content, 'SupportDocumentsContent')

                            if update_flg:
                                logger.info("content flag updated.")

        @classmethod
        def store_general_content_embedding_db(
                cls, nosql_conn, conn, logger, google_key_config_path='../configuration/Google_Key(WinfoBots).json',
                location='us-central1'
        ):
            """
            Fetches unprocessed questions from DB, generates embeddings, and stores them in the DB.
            """
            logger.info('store content embedding to db function called.')
            records_flg = True
            min_content_limit = 33700
            max_content_limit = 33800
            while records_flg:
                all_contents_query = f"""
                SELECT *
                FROM GeneralDocumentsContent
                WHERE questions_generated = 'No' 
                and product_name = 'Oracle'
                and (content_id > {min_content_limit} and content_id <= {max_content_limit})
                """
                all_contents = tm.execute_select_query(nosql_conn, all_contents_query)
                logger.info(f"all_contents: {all_contents}")
                print(f"Query for contents: \n{all_contents_query}")
                print(f"all_contents: {all_contents}")
                if len(all_contents) == 0:
                    records_flg = False
                with conn.cursor() as db_cursor:
                    for content in all_contents:
                        content_id = content.get('content_id')
                        # title = content.get('content_details').get('title')
                        content_text = content.get('content_details').get('content')
                        process_name = content.get('process_name')
                        product_name = content.get('product_name')
                        process_area = content.get('process_area')
                        sub_process = content.get('sub_process')
                        # print(
                        #     f"content id: {content_id},\ncontent_text: {content_text},\nprocess_name: {process_name},"
                        #     f"\nproduct_name: {product_name},\nprocess_area: {process_area},\nsub_process: {sub_process}"
                        # )
                        print(f"content id: {content_id}")

                        content_embedding = em.get_embedding(
                            ut.clean_string(content_text).lower(), logger, embedding_model='text-embedding-005', dimensions=256,
                            google_key_config_path=google_key_config_path, location=location
                        )
                        logger.info(f'query_embedding: {content_embedding}')
                        if len(content_embedding) == 0:
                            logger.info(f"No embedding found for content id - {content_id}")
                            continue

                        insert_status = cls._insert_general_questions_db(
                            content_id,
                            product_name,
                            process_name,
                            process_area,
                            sub_process,
                            content_embedding,
                            db_cursor,
                            logger
                        )
                        conn.commit()
                        if not insert_status:
                            logger.error(f"Error inserting content_embedding for content_id - {content_id}")
                        else:
                            content["questions_generated"] = "Yes"
                            update_flg = tm.execute_update_query(nosql_conn, content, 'GeneralDocumentsContent')

                            if update_flg:
                                logger.info("content flag updated.")

                    min_content_limit = max_content_limit
                    max_content_limit += 100

        @classmethod
        def _insert_questions_db(
                cls, content_id, product_name, process_name, process_area, sub_process, customer_name,
                embedding, db_cursor, logger
        ):
            """
            Inserts generated FAQ questions into the database.
            """
            logger.info('insert_questions_db() called.')
            insertion_status = True

            query_insertion = (
                "insert into support_content_embedding (QUERY_ID, CONTENT_ID, product_name, process_name, process_area, sub_process, embedding, CUSTOMER_NAME) "
                "values (support_content_embedding_id_seq.nextval, :content_id, :product_name, :process_name, :process_area, :sub_process, :embedding, :customer_name)"
            )
            try:
                db_cursor.execute(
                    query_insertion,
                    {
                        'content_id': content_id,
                        'product_name': product_name,
                        'process_name': process_name,
                        'process_area': process_area,
                        'sub_process': sub_process,
                        'customer_name': customer_name,
                        'embedding': json.dumps(embedding)
                    }
                )
            except Exception as e:
                logger.error(f"Error executing query_insertion: {e}")
                logger.error(f"content_id: {content_id}")
                insertion_status = False

            return insertion_status


        @classmethod
        def _insert_general_questions_db(
                cls, content_id, product_name, process_name, process_area, sub_process, embedding, db_cursor, logger
        ):
            """
            Inserts generated FAQ questions into the database.
            """
            logger.info('_insert_general_questions_db() called.')
            insertion_status = True

            query_insertion = (
                "insert into general_content_embedding (QUERY_ID, CONTENT_ID, product_name, process_name, process_area, sub_process, embedding) "
                "values (general_content_embedding_id_seq.nextval, :content_id, :product_name, :process_name, :process_area, :sub_process, :embedding)"
            )
            try:
                db_cursor.execute(
                    query_insertion,
                    {
                        'content_id': content_id,
                        'product_name': product_name,
                        'process_name': process_name,
                        'process_area': process_area,
                        'sub_process': sub_process,
                        'embedding': json.dumps(embedding)
                    }
                )
            except Exception as e:
                logger.error(f"Error executing query_insertion: {e}")
                logger.error(f"content_id: {content_id}")
                insertion_status = False

            return insertion_status


    class QuestionService:
        @classmethod
        def _get_questions(cls, content_id, title, content, process_name, product_name, logger,
                           google_key_config_path='../configuration/Google_Key(WinfoBots).json'):
            """
            Generates FAQ questions and detailed answers based on content using the prompting service.
            """

            system_instructions = f"""
Your agenda is to create a FAQ questions for the information provided related to the {process_name} process in {product_name} RPA Solution. 
This FAQ questions will be helpful for support/service team to answer them to the service tickets, so create questions assuming that you heard about the topic which will be provided as an input assuming you are an service expert. 
Make the questions as depth as possible so my support/service team have the best information to gear up for the service tickets. 
Generate the maximum no.of questions we may get based on content provided in the format provided below.
Ensure that the output is in exact JSON format.
output: 
{{ "question":[
"<question1>",
"<question2>",
]
}}

Example output:
{{
 "questions": [
  "What does the 'Needs Action' status in the Summary Table indicate regarding Purchase Orders?",
  "For Purchase Orders in 'Needs Action' status, what specific actions are typically required from the user?",
  "What are the common reasons why a Purchase Order might end up in the 'Needs Action' status?",
  "What does 'Pending Sales Order Entry' status signify about a Purchase Order?",
  "What conditions must be met for a Purchase Order to be classified as 'Pending Sales Order Entry'?",
  "What actions does the RPA robot perform on Purchase Orders in the 'Pending Sales Order Entry' status?",
  "What does 'Sales Order Entry in Progress' mean for a Purchase Order?"
 ]
}}
            """
            response_schema = {
                "type": "OBJECT",
                "properties": {
                    "questions": {
                        "type": "ARRAY",
                        "items": {
                            "type": "STRING",
                            "description": "A question about Purchase Order statuses."
                        },
                        "description": "An array of questions about Purchase Order statuses."
                    }
                },
                "required": [
                    "questions"
                ]
            }
            questionnaire_prompt = f"""
            Title of the content: {title}
            Given the following content:'''
            {content}
            '''
            """

            questions = pr.get_prompt_response(questionnaire_prompt, logger,
                                               google_key_config_path=google_key_config_path,
                                               response_schema=response_schema, system_instruction=system_instructions)

            try:
                start_index = questions.find('{')
                end_index = questions.rfind('}') + 1
                questions = questions[start_index:end_index]
                questions = json.loads(questions)
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON response for content_id - {content_id}: {e}")
                logger.error(f"content_id: {content_id}, questions: {questions}")
                questions = {'result': []}
            except Exception as e:
                logger.error(f"Error processing content_id - {content_id}: {e}")
                questions = {'result': []}

            return questions

        @classmethod
        def _get_all_support_content(cls, handle):
            query = """
            SELECT content_id,
                   content_details,
                   file_name,
                   product_name,
                   process_area,
                   process_name,
                   sub_process
            FROM SupportDocumentsContent
            WHERE questions_generated = 'No'
            """

            cleaned_result = tm.execute_select_query(handle, query)
            '''# print(f"query: {query}")
            request = QueryRequest().set_statement(query)

            all_rows = []
            result = handle.query(request)

            # Get initial results
            all_rows.extend(result.get_results())

            # Handle pagination using continuation key
            while result.get_continuation_key() is not None:
                request.set_continuation_key(result.get_continuation_key())
                result = handle.query(request)
                all_rows.extend(result.get_results())

            # print(f'before all_rows: {all_rows}')
            cleaned_result = []
            for row in all_rows:
                cleaned_row = {key: value if not isinstance(value, OrderedDict) else dict(value) for key, value in
                               row.items()}
                cleaned_result.append(cleaned_row)

            # print(f'cleaned_result: {cleaned_result}')'''

            return cleaned_result

        @classmethod
        def _update_support_content_table_rdb(cls, content_id, db_cursor, logger):
            """
            Marks content as processed (questions generated) in the database.
            """
            logger.info('update_sales_content_table() called.')

            sales_content_table_update = "update support_content set questions_generated = 'Yes' where content_id = :content_id"
            try:
                db_cursor.execute(
                    sales_content_table_update,
                    {
                        'content_id': content_id
                    }
                )
            except Exception as e:
                logger.error(f"Error executing sales_content_table_update: {e}")
                logger.error(f"content_id: {content_id}")

        @classmethod
        def _update_support_content_table_nosql(cls, content_id, nosql_conn, logger):
            """
            Marks content as processed (questions generated) in the database.
            """
            logger.info('update_sales_content_table_nosql() called.')

            try:
                row = {
                    'content_id': content_id,
                    'questions_generated': 'Yes'
                }
                request = PutRequest().set_table_name('SupportDocumentsContent').set_value(row).set_update(True)
                nosql_conn.put(request)
            except Exception as e:
                logger.error(f"Error executing sales_content_table_update: {e}")
                logger.error(f"content_id: {content_id}")


    class DatabaseService:
        """"""
        @classmethod
        def _store_content_to_nosql_db(cls, content, file_name, product, process_name, process_area, sub_process,
                                       customer_name, nosql_conn, logger):
            """
            Stores extracted content into the database.
            """
            flg = True
            logger.info('store_content_to_nosql_db() called.')
            try:
                # Sanitize content to escape control characters
                # content = content.replace('\n', '\\n').replace('\r', '\\r')
                # content = json.loads(content)
                content = content.get('content')
                if len(content) == 0:
                    return False

                for each_item in content:
                    logger.info(f'each_item: {each_item}, file_name: {file_name}, product: {product}')
                    content_id = tm.get_next_sequence_id(nosql_conn, "SupportContentIdSeq")
                    title = each_item.get('section_title')
                    text = each_item.get('section_text')
                    # Sanitize section_text
                    # text = text.replace('\n', '\\n').replace('\r', '\\r')
                    # print(len(str(text).split()))
                    if len(str(text).split()) <= 20:
                        continue

                    content_record = {
                        'content_id': content_id,
                        'content_details': {
                            'content': text,
                            'title': title
                        },
                        'file_name': file_name,
                        'product_name': product,
                        'process_name': process_name,
                        'process_area': process_area,
                        'sub_process': sub_process,
                        'customer_name': customer_name,
                        'questions_generated': 'No'
                    }
                    try:
                        flg = tm.execute_insert_query(nosql_conn, content_record, 'SupportDocumentsContent')
                    except Exception as e:
                        logger.error(f"Error executing content_insert_query: {e}")
                        logger.error(f"content_record: {content_record}")
                        flg = False

            except Exception as e:
                logger.error(f"Error storing content to nosql database: {e}")
                logger.error(f"content: {content}, file_name: {file_name}")
                flg = False

            return flg

        @classmethod
        def _store_general_content_to_nosql_db(cls, content, file_name, product, process_name, process_area, sub_process,
                                       nosql_conn, logger):
            """
            Stores extracted content into the database.
            """
            flg = True
            logger.info('_store_general_content_to_nosql_db() called.')
            try:
                # Sanitize content to escape control characters
                # content = content.replace('\n', '\\n').replace('\r', '\\r')
                # content = json.loads(content)
                content = content.get('content')
                if len(content) == 0:
                    return False

                for each_item in content:
                    logger.info(f'each_item: {each_item}, file_name: {file_name}, product: {product}')
                    content_id = tm.get_next_sequence_id(nosql_conn, "GeneralDocumentsContentIdSeq")
                    title = each_item.get('section_title')
                    text = each_item.get('section_text')
                    # Sanitize section_text
                    # text = text.replace('\n', '\\n').replace('\r', '\\r')
                    # print(len(str(text).split()))
                    if len(str(text).split()) <= 20:
                        continue

                    content_record = {
                        'content_id': content_id,
                        'content_details': {
                            'content': text,
                            'title': title
                        },
                        'file_name': file_name,
                        'product_name': product,
                        'process_name': process_name,
                        'process_area': process_area,
                        'sub_process': sub_process,
                        'questions_generated': 'No'
                    }
                    try:
                        put_request = PutRequest().set_table_name('GeneralDocumentsContent').set_value(content_record)
                        result = nosql_conn.put(put_request)

                        if result.get_version() is not None:
                            logger.info(
                                f"Record inserted into 'GeneralDocumentsContent' with content_id = {content_id}")
                        else:
                            logger.error(f"Failed to insert record.\n{content_record}")
                    except Exception as e:
                        logger.error(f"Error executing content_insert_query: {e}")
                        logger.error(f"content_record: {content_record}")
                        flg = False

            except Exception as e:
                logger.error(f"Error storing content to nosql database: {e}")
                logger.error(f"content: {content}, file_name: {file_name}")
                flg = False

            return flg


    class ContentPreparationService(DatabaseService):
        @classmethod
        def content_preparation(
                cls, pdf_path, file_name, product, process_name, process_area, sub_process, customer_name,
                nosql_conn, logger, google_key_config_path='../configuration/Google_Key(WinfoBots).json',
                model_name='gemini-2.0-flash-001', location='us-central1'
        ):
            """
            Reads files from GCS, processes their content, and stores the processed data in the database.
            """
            logger.info('content_preparation() called.')
            try:

                pdf_content = pdfp.get_pdf_content_chunks(
                    pdf_path,
                    logger,
                    model_name=model_name,
                    location=location,
                    google_key_path=google_key_config_path,
                    chunk_token_size=256,
                    chunk_overlap_tokens=50
                )
                # print(pdf_content)

                ins_status = cls._store_content_to_nosql_db(
                    pdf_content, file_name, product, process_name, process_area, sub_process, customer_name,
                    nosql_conn, logger
                )

                if ins_status:
                    logger.info(f"File {file_name} completed storing contents.")
                else:
                    logger.error(f"File {file_name} failed to store contents.")
            except Exception as e:
                logger.error(f"Error processing file {file_name} after prompt: {e}")

        @classmethod
        def general_content_preparation(
                cls, pdf_path, file_name, product, process_name, process_area, sub_process, nosql_conn, logger,
                google_key_config_path='../configuration/Google_Key(WinfoBots).json',
                model_name='gemini-2.0-flash-001', location='us-central1'
        ):
            """
            Reads files from GCS, processes their content, and stores the processed data in the database.
            """
            logger.info('general_content_preparation() called.')
            try:

                pdf_content = pdfp.get_pdf_content_chunks(
                    pdf_path,
                    logger,
                    model_name=model_name,
                    location=location,
                    google_key_path=google_key_config_path,
                    chunk_token_size=256,
                    chunk_overlap_tokens=50
                )
                # print(pdf_content)

                ins_status = cls._store_general_content_to_nosql_db(
                    pdf_content, file_name, product, process_name, process_area, sub_process, nosql_conn,
                    logger
                )

                if ins_status:
                    logger.info(f"File {file_name} deleted from GCS.")
            except Exception as e:
                logger.error(f"Error processing file {file_name} after prompt: {e}")


class WinfoBotsSupportProcessFiles:
    """"""
    class EmbeddingService:
        @classmethod
        def store_question_embedding_db(
                cls, conn, logger, google_key_config_path='../configuration/Google_Key(WinfoBots).json',
                location='us-central1'
        ):
            """
            Fetches unprocessed questions from DB, generates embeddings, and stores them in the DB.
            """
            logger.info('store_question_embedding_db() called.')

            with conn.cursor() as db_cursor:
                questions_query = "select QUERY_ID, QUERY from support_content_embedding WHERE embedding is null order by 1"
                db_cursor.execute(questions_query)
                questions_data = db_cursor.fetchall()

                for question in questions_data:
                    query_id = question[0]
                    query = str(question[1])
                    logger.info(f'query_id: {query_id}, query: {query}')

                    query_embedding = em.get_embedding(
                        query, logger, embedding_model='text-embedding-005', dimensions=256,
                        google_key_config_path=google_key_config_path, location=location
                    )
                    logger.info(f'query_embedding: {query_embedding}')
                    if len(query_embedding) == 0:
                        logger.info(f"No embedding found for query_id - {query_id}")
                        continue

                    update_status = cls._update_question_embedding_db(query_embedding, query_id, db_cursor, logger)
                    if not update_status:
                        logger.error(f"Error updating query_embedding for query_id - {query_id}")

                    # break

        @classmethod
        def _update_question_embedding_db(cls, embedding, query_id, db_cursor, logger):
            """
            Updates the embedding for a question in the database.
            """
            logger.info('update_question_embedding_db() called.')
            embedding = json.dumps(embedding)
            update_query = (
                "update support_content_embedding set embedding = :embedding where query_id = :query_id"
            )
            try:
                db_cursor.execute(
                    update_query,
                    {
                        'embedding': embedding,
                        'query_id': query_id
                    }
                )
                db_cursor.connection.commit()
                return True
            except Exception as e:
                logger.error(f"Error executing update_question_embedding_query: {e}")
                logger.error(f"query_id: {query_id}, embedding: {embedding}")
                return False

    class QuestionService:
        @classmethod
        def _get_questions(cls, content_id, title, content, process_name, product_name, logger,
                           google_key_config_path='../configuration/Google_Key(WinfoBots).json'):
            """
            Generates FAQ questions and detailed answers based on content using the prompting service.
            """

            system_instructions = f"""
    Your agenda is to create a FAQ questions for the information provided related to the {process_name} process in {product_name} RPA Solution. 
    This FAQ questions will be helpful for support/service team to answer them to the service tickets, so create questions assuming that you heard about the topic which will be provided as an input assuming you are an service expert. 
    Make the questions as depth as possible so my support/service team have the best information to gear up for the service tickets. 
    Generate the maximum no.of questions we may get based on content provided in the format provided below.
    Ensure that the output is in exact JSON format.
    output: 
    {{ "question":[
    "<question1>",
    "<question2>",
    ]
    }}

    Example output:
    {{
     "questions": [
      "What does the 'Needs Action' status in the Summary Table indicate regarding Purchase Orders?",
      "For Purchase Orders in 'Needs Action' status, what specific actions are typically required from the user?",
      "What are the common reasons why a Purchase Order might end up in the 'Needs Action' status?",
      "What does 'Pending Sales Order Entry' status signify about a Purchase Order?",
      "What conditions must be met for a Purchase Order to be classified as 'Pending Sales Order Entry'?",
      "What actions does the RPA robot perform on Purchase Orders in the 'Pending Sales Order Entry' status?",
      "What does 'Sales Order Entry in Progress' mean for a Purchase Order?"
     ]
    }}
                """
            response_schema = {
                "type": "OBJECT",
                "properties": {
                    "questions": {
                        "type": "ARRAY",
                        "items": {
                            "type": "STRING",
                            "description": "A question about Purchase Order statuses."
                        },
                        "description": "An array of questions about Purchase Order statuses."
                    }
                },
                "required": [
                    "questions"
                ]
            }
            questionnaire_prompt = f"""
                Title of the content: {title}
                Given the following content:'''
                {content}
                '''
                """

            questions = pr.get_prompt_response(questionnaire_prompt, logger,
                                               google_key_config_path=google_key_config_path,
                                               response_schema=response_schema, system_instruction=system_instructions)

            try:
                start_index = questions.find('{')
                end_index = questions.rfind('}') + 1
                questions = questions[start_index:end_index]
                questions = json.loads(questions)
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON response for content_id - {content_id}: {e}")
                logger.error(f"content_id: {content_id}, questions: {questions}")
                questions = {'result': []}
            except Exception as e:
                logger.error(f"Error processing content_id - {content_id}: {e}")
                questions = {'result': []}

            return questions

        @classmethod
        def _get_all_support_content(cls, handle):
            query = """
            SELECT content_id,
                   content_details,
                   file_name,
                   product_name,
                   process_area,
                   process_name,
                   sub_process,
                   file_name
            FROM SupportDocumentsContent
            WHERE questions_generated = 'No'
            """

            cleaned_result = tm.execute_select_query(handle, query)

            return cleaned_result

        @classmethod
        def store_questions_db(
                cls, nosql_conn, app_conn, logger,
                google_key_config_path='../configuration/Google_Key(WinfoBots).json'
        ):
            """
            Fetches unprocessed content from the database, generates FAQ questions for it, and stores them.
            """
            logger.info('store_questions_db() called.')

            records_flg = True
            while records_flg:
                all_contents_query = f"""
                SELECT *
                FROM SupportDocumentsContent
                WHERE questions_generated = 'No' 
                and product_name = 'WinfoBots'
                """
                contents = tm.execute_select_query(nosql_conn, all_contents_query)
                logger.info(f"contents: {contents}")
                print(f"Query for contents: \n{all_contents_query}")
                print(f"all_contents: {contents}")
                if len(contents) == 0:
                    records_flg = False

                with app_conn.cursor() as db_cursor:
                    for content in contents:
                        content_id = content.get('content_id')
                        title = content.get('content_details').get('title')
                        content_text = content.get('content_details').get('content')
                        process_name = content.get('process_name')
                        product_name = content.get('product_name')
                        process_area = content.get('process_area')
                        sub_process = content.get('sub_process')
                        # file_name = content.get('file_name')
                        customer_name = content.get('customer_name')
                        # print(f"content id: {content_id},\ntitle: {title},\ncontent_text: {content_text},\nprocess_name: {process_name},\nproduct_name: {product_name},\nprocess_area: {process_area},\nsub_process: {sub_process}")
                        print(f"content id: {content_id}")
                        # continue
                        questions = cls._get_questions(
                            content_id, title, content_text, process_name, product_name, logger,
                            google_key_config_path=google_key_config_path
                        )
                        print(f"questions: {questions}")
                        # continue
                        logger.info(f'questions: {questions}')
                        if len(questions['questions']) > 0:
                            insert_status = cls._insert_questions_db(
                                content_id, customer_name, questions, product_name, process_name, process_area,
                                sub_process, db_cursor, logger
                            )
                            if insert_status:
                                cls._update_support_content_table_nosql(
                                    content, nosql_conn, logger
                                )
                        app_conn.commit()
                        # break
                        time.sleep(3)

            logger.info("Finished processing all questions.")

        @classmethod
        def _insert_questions_db(
                cls, content_id, customer_name, questions, product_name, process_name, process_area, sub_process, db_cursor, logger
        ):
            """
            Inserts generated FAQ questions into the database.
            """
            logger.info('insert_questions_db() called.')
            insertion_status = True

            for each_question in questions['questions']:
                query_insertion = (
                    "insert into support_content_embedding (QUERY_ID, CONTENT_ID, QUERY, product_name, process_name, process_area, sub_process, customer_name) "
                    "values (support_content_embedding_id_seq.nextval, :content_id, :query, :product_name, :process_name, :process_area, :sub_process, :customer_name)"
                )
                try:
                    db_cursor.execute(
                        query_insertion,
                        {
                            'content_id': content_id,
                            'query': ut.clean_string(each_question).lower(),
                            'product_name': product_name,
                            'process_name': process_name,
                            'process_area': process_area,
                            'sub_process': sub_process,
                            'customer_name': customer_name
                        }
                    )
                except Exception as e:
                    logger.error(f"Error executing query_insertion: {e}")
                    logger.error(f"content_id: {content_id}, query: {each_question}")
                    insertion_status = False

            return insertion_status

        @classmethod
        def _update_support_content_table_rdb(cls, content_id, db_cursor, logger):
            """
            Marks content as processed (questions generated) in the database.
            """
            logger.info('update_sales_content_table() called.')

            sales_content_table_update = "update support_content set questions_generated = 'Yes' where content_id = :content_id"
            try:
                db_cursor.execute(
                    sales_content_table_update,
                    {
                        'content_id': content_id
                    }
                )
            except Exception as e:
                logger.error(f"Error executing sales_content_table_update: {e}")
                logger.error(f"content_id: {content_id}")

        @classmethod
        def _update_support_content_table_nosql(
                cls, content, nosql_conn, logger
        ):
            """
            Marks content as processed (questions generated) in the database.
            """
            logger.info('_update_sales_content_table_nosql() called.')
            try:
                content['questions_generated'] = 'Yes'
                update_flg = tm.execute_update_query(nosql_conn, content, 'SupportDocumentsContent')
            except Exception as e:
                logger.error(f"Error executing sales_content_table_update: {e}")
                logger.error(f"content_id: {content.get('content_id')}")

    class DatabaseService:
        """"""

        @classmethod
        def _store_content_to_db(cls, content, file_name, product, process_name, customer_name, db_cursor, logger):
            """
            Stores extracted content into the database.
            """
            flg = True
            logger.info('store_content_to_db() called.')
            try:
                content = json.loads(content)
                content = content['content']
                if len(content) == 0:
                    return False

                content_insert_query = """
    insert into support_content(
      content_id,
      title,
      content,
      file_name,
      process_name,
      customer_name,
      questions_generated,
      product_name
    )
    values(
      support_content_id_seq.nextval,
      :title,
      :content,
      :file_name,
      :process_name,
      :customer_name,
      'No',
      :product_name
    )
                    """

                for each_item in content:
                    logger.info(f'each_item: {each_item}, file_name: {file_name}, product: {product}')
                    title = each_item['section_title']
                    text = each_item['section_text']
                    # print(len(str(text).split()))
                    if len(str(text).split()) <= 20:
                        continue
                    try:
                        db_cursor.execute(
                            content_insert_query,
                            {
                                'content': text,
                                'title': title,
                                'file_name': file_name,
                                'product_name': product,
                                'process_name': process_name,
                                'customer_name': customer_name
                            }
                        )
                    except Exception as e:
                        logger.error(f"Error executing content_insert_query: {e}")
                        logger.error(f"content: {content}, title: {title}, file_name: {file_name}")
                        flg = False
                    db_cursor.connection.commit()
            except Exception as e:
                logger.error(f"Error storing content to database: {e}")
                logger.error(f"content: {content}, file_name: {file_name}")
                flg = False

            return flg

        @classmethod
        def _store_content_to_nosql_db(
                cls, content, product_name, process_area, process_name, sub_process, customer_name,
                file_name, nosql_conn, logger
        ):

            """
            Stores extracted content into the nosql database.
            """
            flg = True
            logger.info('store_content_to_nosql_db() called.')
            try:
                # Sanitize content to escape control characters
                # content = content.replace('\n', '\\n').replace('\r', '\\r')
                # content = json.loads(content)
                content = content.get('content')
                if len(content) == 0:
                    return False

                for each_item in content:
                    logger.info(f'each_item: {each_item}, file_name: {file_name}')
                    content_id = tm.get_next_sequence_id(nosql_conn, "SupportContentIdSeq")
                    title = each_item.get('section_title')
                    text = each_item.get('section_text')

                    if len(str(text).split()) <= 20:
                        continue

                    content_record = {
                        'content_id': content_id,
                        'content_details': {
                            'content': str(text),
                            'title': title
                        },
                        'file_name': file_name,
                        'product_name': product_name,
                        'process_area': process_area,
                        'process_name': process_name,
                        'sub_process': sub_process,
                        'customer_name': customer_name,
                        'questions_generated': 'No'
                    }
                    try:
                        # put_request = PutRequest().set_table_name('SupportDocumentsContent').set_value(content_record)
                        # result = nosql_conn.put(put_request)
                        # print(f"content_record: {content_record}")
                        insert_flg = tm.execute_insert_query(nosql_conn, content_record, 'SupportDocumentsContent')
                        if insert_flg:
                            logger.info(
                                f"Record inserted into 'SupportDocumentsContent' with content_id = {content_id}")
                        else:
                            logger.error(f"Failed to insert record.\n{content_record}")
                    except Exception as e:
                        logger.error(f"Error executing content_insert_query: {e}")
                        logger.error(f"content_record: {content_record}")
                        flg = False

            except Exception as e:
                logger.error(f"Error storing content to nosql database: {e}")
                logger.error(f"content: {content}, file_name: {file_name}")
                flg = False

            return flg

    class ContentPreparationService(DatabaseService):
        @classmethod
        def _content_preparation_gcp(
                cls, bucket_name, gcs_folder_path, product_name, process_area, process_name, sub_process, customer_name,
                nosql_conn, logger, google_key_config_path='../configuration/Google_Key(WinfoBots).json'
        ):
            """
            Reads files from GCS, processes their content, and stores the processed data in the database.
            """
            logger.info('content_preparation() called.')

            list_of_files = gcs.get_files_in_gcs(bucket_name, gcs_folder_path, logger,
                                                 google_key_path=google_key_config_path)
            list_of_files = list_of_files['files']
            # print(f'list_of_files: {list_of_files}')

            for file in list_of_files:
                # print(f'file: {file}')
                blob_name = str(file['blob_name'])
                file_name = str(file['file_name'])
                file_path = str(file['file_path'])

                file_part = Part.from_uri(
                    uri=file_path,
                    mime_type="application/pdf",
                )
                prompt = """
        Analyze the provided attachment and extract the actual content from it. With proper headings when required.
                        """
                system_instruction = """
        You are a highly skilled and professional Document Analysis Specialist AI with deep expertise in understanding and interpreting complex documents.
        Analyze the provided document thoroughly and return a comprehensive and well-structured response based on the specific prompt provided by the user.

        Document Types You May Encounter:
        The input document may contain a variety of data formats and visual elements, including but not limited to:
            - Scanned text or images
            - Tables (financial, transactional, or structured data)
            - Flowcharts or process diagrams
            - Charts or graphs (bar, pie, line, etc.)
            - Embedded images or logos
            - Annotations or footnotes

        Your Task:

            - Holistically analyze the entire document including visual, textual, and tabular data.
            - Extract or summarize content strictly according to the user’s prompt or question.
            - If the document contains tables, extract them in a descriptive and human-readable format, explaining:
                - The purpose of the table
                - Each row and column header with associated data
                - Key insights or totals, if available
            - If charts or flow diagrams are present:
                - Describe their layout and key elements
                - Summarize their meaning and context in the document

        Important Guidelines:
            - Do not skip or ignore any content, especially from tables or footnotes.
            - Provide data in a structured and clearly labeled format.
            - If any data is missing or not clearly identifiable, return "null" with a short explanation.
            - If values are derived or inferred (e.g., currency from country), explain your reasoning.
            - Assume the user is expecting clarity, completeness, and professional formatting in the output.
                        """

                contents = [file_part, prompt]
                pdf_content = pr.get_prompt_response(
                    contents, logger, model_name='gemini-2.0-flash',
                    system_instruction=system_instruction,
                    google_key_config_path=google_key_config_path
                )

                try:
                    if len(pdf_content) == 0:
                        continue

                    response_schema = {
                        "type": "OBJECT",
                        "properties": {
                            "content": {
                                "type": "ARRAY",
                                "items": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "section_title": {
                                            "type": "STRING",
                                            "description": "The title of the section."
                                        },
                                        "section_text": {
                                            "type": "STRING",
                                            "description": "The text content of the section."
                                        }
                                    },
                                    "required": [
                                        "section_title",
                                        "section_text"
                                    ]
                                },
                                "description": "An array of content sections."
                            }
                        },
                        "required": [
                            "content"
                        ]
                    }
                    system_instruction = '''
            You are an expert document segmentation analyst. Your task is to analyze the following document text and divide it into logically distinct sections, each representing a separate and coherent topic. The goal is to maximize clarity and organization for the reader. The number of sections should be determined by the inherent topic divisions within the document, striving for a structure that allows each section to be understood independently. Consider potential overlap and redundancy, aiming to minimize both. Focus on creating sections with a clear scope and internal coherence. Don't make any changes to the actual content until it required. Analyze the entire pdf provided and extract the actual content from the provided pdf based on the sections divided to store it in section_text.

            For each section, output the following in JSON format:

            {
            "content": [
            {
            "section_title": "<A concise and descriptive title for the section>",
            "section_text": "<The exact text from the document that belongs to this section>"
            },
            {
            "section_title": "<A concise and descriptive title for the section>",
            "section_text": "<The exact text from the document that belongs to this section>"
            },
            ...
            ]
            }
                            '''

                    prompt = f"""
                                Document text: {pdf_content}
                                """
                    try:
                        response = pr.get_prompt_response(prompt, logger, google_key_config_path=google_key_config_path,
                                                          system_instruction=system_instruction,
                                                          response_schema=response_schema)

                        start_index = response.find('{')
                        end_index = response.rfind('}') + 1
                        file_content = response[start_index:end_index]
                        # print(file_content)

                        ins_status = cls._store_content_to_nosql_db(
                            file_content, product_name, process_area, process_name, sub_process, customer_name,
                            file_name, nosql_conn, logger
                        )

                        if ins_status:
                            gcs.delete_from_gcs(bucket_name, blob_name, logger, google_key_path=google_key_config_path)
                            logger.info(f"File {file_name} deleted from GCS.")
                    except Exception as e:
                        logger.error(f"Error processing file {file_name} after prompt: {e}")
                except Exception as e:
                    logger.error(f"Error processing file {file_name}: {e}")

                # print(f"")
                # break
                time.sleep(10)

        @classmethod
        def llm_content_preparation(
                cls, file_path: str, product_name: str, process_area: str, process_name: str, sub_process: str,
                customer_name: str, nosql_conn, logger, model_name='gemini-2.0-flash',
                google_key_config_path='../configuration/Google_Key(WinfoBots).json'
        ):
            """
            Reads files from GCS, processes their content, and stores the processed data in the database.
            """
            logger.info('content_preparation() called.')

            with open(file_path, "rb") as f:
                file_bytes = f.read()

            file_name = os.path.basename(file_path)

            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type is None:
                mime_type = "application/octet-stream"
                logger.warning(f"Could not guess MIME type for {file_path}. \nUsing {mime_type}.")

            file_part = Part.from_data(
                data=file_bytes,
                mime_type=mime_type
            )
            prompt = """
    Analyze the provided attachment and extract the actual content from it. With proper headings when required.
                    """
            system_instruction = """
    You are a highly skilled and professional Document Analysis Specialist AI with deep expertise in understanding and interpreting complex documents.
    Analyze the provided document thoroughly and return a comprehensive and well-structured response based on the specific prompt provided by the user.

    Document Types You May Encounter:
    The input document may contain a variety of data formats and visual elements, including but not limited to:
        - Scanned text or images
        - Tables (financial, transactional, or structured data)
        - Flowcharts or process diagrams
        - Charts or graphs (bar, pie, line, etc.)
        - Embedded images or logos
        - Annotations or footnotes

    Your Task:

        - Holistically analyze the entire document including visual, textual, and tabular data.
        - Extract or summarize content strictly according to the user’s prompt or question.
        - If the document contains tables, extract them in a descriptive and human-readable format, explaining:
            - The purpose of the table
            - Each row and column header with associated data
            - Key insights or totals, if available
        - If charts or flow diagrams are present:
            - Describe their layout and key elements
            - Summarize their meaning and context in the document

    Important Guidelines:
        - Do not skip or ignore any content, especially from tables or footnotes.
        - Provide data in a structured and clearly labeled format.
        - If any data is missing or not clearly identifiable, return "null" with a short explanation.
        - If values are derived or inferred (e.g., currency from country), explain your reasoning.
        - Assume the user is expecting clarity, completeness, and professional formatting in the output.
                    """

            contents = [file_part, prompt]
            pdf_content = pr.get_prompt_response(
                contents, logger, model_name=model_name,
                system_instruction=system_instruction,
                google_key_config_path=google_key_config_path
            )

            try:
                if len(pdf_content) == 0:
                    return

                response_schema = {
                    "type": "OBJECT",
                    "properties": {
                        "content": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "section_title": {
                                        "type": "STRING",
                                        "description": "The title of the section."
                                    },
                                    "section_text": {
                                        "type": "STRING",
                                        "description": "The text content of the section."
                                    }
                                },
                                "required": [
                                    "section_title",
                                    "section_text"
                                ]
                            },
                            "description": "An array of content sections."
                        }
                    },
                    "required": [
                        "content"
                    ]
                }
                system_instruction = '''
        You are an expert document segmentation analyst. Your task is to analyze the following document text and divide it into logically distinct sections, each representing a separate and coherent topic. The goal is to maximize clarity and organization for the reader. The number of sections should be determined by the inherent topic divisions within the document, striving for a structure that allows each section to be understood independently. Consider potential overlap and redundancy, aiming to minimize both. Focus on creating sections with a clear scope and internal coherence. Don't make any changes to the actual content until it required. Analyze the entire pdf provided and extract the actual content from the provided pdf based on the sections divided to store it in section_text.

        For each section, output the following in JSON format:

        {
        "content": [
        {
        "section_title": "<A concise and descriptive title for the section>",
        "section_text": "<The exact text from the document that belongs to this section>"
        },
        {
        "section_title": "<A concise and descriptive title for the section>",
        "section_text": "<The exact text from the document that belongs to this section>"
        },
        ...
        ]
        }
                        '''
                prompt = f"""
                            Document text: {pdf_content}
                            """
                try:
                    response = pr.get_prompt_response(prompt, logger, google_key_config_path=google_key_config_path,
                                                      system_instruction=system_instruction,
                                                      response_schema=response_schema, model_name=model_name)

                    start_index = response.find('{')
                    end_index = response.rfind('}') + 1
                    file_content = response[start_index:end_index]
                    print(f"file_content: {file_content}")
                    file_content = json.loads(file_content)
                    ins_status = cls._store_content_to_nosql_db(
                        file_content, product_name, process_area, process_name, sub_process, customer_name,
                        file_name, nosql_conn, logger
                    )

                    if ins_status:
                        os.remove(file_path)
                        logger.info(f"File chunk '{file_name}' deleted from local system.")
                except Exception as e:
                    logger.error(f"Error processing file {file_name} after prompt: {e}")
            except Exception as e:
                logger.error(f"Error processing file {file_name}: {e}")

            # print(f"")
            # break
            # time.sleep(10)

        @classmethod
        def content_preparation(
                cls, pdf_path, file_name, product_name, process_area, process_name, sub_process, customer_name,
                nosql_conn, logger, google_key_config_path='../configuration/Google_Key(WinfoBots).json',
                model_name='gemini-2.0-flash-001', location='us-central1'
        ):
            """
            Reads files from local system, processes their content, and stores the processed data in the database.
            """
            logger.info('content_preparation() called.')
            try:

                pdf_content = pdfp.get_pdf_content_chunks(
                    pdf_path,
                    logger,
                    model_name=model_name,
                    location=location,
                    google_key_path=google_key_config_path,
                    chunk_token_size=256,
                    chunk_overlap_tokens=50
                )
                # print(pdf_content)

                ins_status = cls._store_content_to_nosql_db(
                    pdf_content, product_name, process_area, process_name, sub_process, customer_name,
                    file_name, nosql_conn, logger
                )

                if ins_status:
                    logger.info(f"File {file_name} deleted from GCS.")
            except Exception as e:
                logger.error(f"Error processing file {file_name} after prompt: {e}")
