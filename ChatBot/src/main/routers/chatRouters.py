from fastapi import APIRouter, Depends
import traceback

from src.app.services.dbConnect import DBConnection as db
from src.main.dependencies import get_nosql_conn_dependency, get_ai_db_pool_dependency, get_log_dir_path
from src.app.utils.loggerConfig import LoggerManager as lg
from src.main.models.chatModels import ChatResponse, MessageFeedback
from src.app.chatbot.chatBot import ChatOperations as co

router = APIRouter()


@router.get(
    "/ChatID/Generate",
    summary="Generate a chat ID",
    description="Generate a chat ID for new messages by taking the size of chat ID.",
    operation_id="gen_chat_id"
)
async def gen_chat_id():
    return {"chat_id": co.generate_chat_id()}

@router.get(
    "/ChatID/Get/{issue_id}",
    summary="Generate a chat ID",
    description="Generate a chat ID for new messages by taking the size of chat ID.",
    operation_id="get_chat_id"
)
async def get_chat_id(
    issue_id: str,
    nosql_conn=Depends(get_nosql_conn_dependency),
    log_dir_path=Depends(get_log_dir_path)
):
    logger = lg.configure_logger(f"{log_dir_path}/GetChatID")
    logger.info(f"Fetching the existing chat ID..")
    try:
        chat_id = co.get_chat_id(issue_id, nosql_conn)
    except Exception as e:
        logger.warning(f"Failed to get the existing chat ID. Error: {e}")
        chat_id = 0
    return {"chat_id": chat_id}


@router.post(
    "/MaxMessageId",
    summary="Get Maximum Message ID",
    description="Retrieves the maximum message ID for a given chat session, chat ID, and issue ID.",
    operation_id="max_message_id"
)
async def max_message_id(
        data: dict,
        nosql_conn=Depends(get_nosql_conn_dependency),
        ai_db_pool_name=Depends(get_ai_db_pool_dependency),
        log_dir_path=Depends(get_log_dir_path)
):
    logger = lg.configure_logger(f"{log_dir_path}/MaxQueryIdBot")
    logger.info(f"Processing Max QueryId chatbot request...")
    ai_db_conn = None
    try:
        ai_db_conn = db.get_connection(ai_db_pool_name)
        session_id = data.get('session_id')
        chat_id = data.get('chat_id')
        issue_id = data.get('issue_id')
        r_max_message_id = co.get_max_message_id(session_id, chat_id, nosql_conn, logger, issue_id=issue_id)
        return {
            "data_type": "text",
            "max_message_id": r_max_message_id,
            "chat_id": chat_id
        }
    except Exception as e:
        logger.error(f"Exception in chatbot process: {e}\n{traceback.format_exc()}")
        return {"data_type": "text", "max_query_id": 0, "chat_id": None}
    finally:
        if ai_db_conn:
            db.close_connection(ai_db_conn, ai_db_pool_name)
            logger.info("DB connection released.")
        logger.info("Closing chatbot logger.")
        lg.shutdown_logger(logger)

@router.post(
    "/Response",
    summary="Get Chat Response by Message ID",
    description="Fetches a specific chat response from the database using chat ID and message ID.",
    operation_id="agent_chat_response"
)
async def agent_chat_response(
        data: ChatResponse,
        nosql_conn=Depends(get_nosql_conn_dependency),
        log_dir_path=Depends(get_log_dir_path)
):
    logger = lg.configure_logger(f"{log_dir_path}/ChatResponse")
    logger.info(f"Processing Chat Response chatbot request...")
    try:
        data = data.model_dump()
        chat_id = data.get('chat_id')
        message_id = data.get('message_id')
        chat_resp = co.get_chat_response(chat_id, message_id, nosql_conn, logger)
        return {
            "data_type": "text",
            "data": chat_resp,
            "chat_id": chat_id,
            "message_id": message_id
        }
    except Exception as e:
        logger.error(f"Exception in chatbot process: {e}\n{traceback.format_exc()}")
        return {"data_type": "text", "data": '', "chat_id": None, "message_id": None}
    finally:
        logger.info("Closing chatbot logger.")
        lg.shutdown_logger(logger)

@router.post(
    "/History",
    summary="Get Chat History",
    description="Retrieves the full chat history for a given chat session, chat ID, and issue ID.",
    operation_id="get_chat_history"
)
async def get_chat_history(
        data: dict,
        nosql_conn=Depends(get_nosql_conn_dependency),
        ai_db_pool_name=Depends(get_ai_db_pool_dependency),
        log_dir_path=Depends(get_log_dir_path)
):
    logger = lg.configure_logger(f"{log_dir_path}/ChatHistory")
    logger.info(f"Processing Chat Response chatbot request...")
    ai_db_conn = None
    try:
        ai_db_conn = db.get_connection(ai_db_pool_name)
        session_id = data.get('session_id')
        chat_id = data.get('chat_id')
        issue_id = data.get('issue_id')
        all_prv_chats, prv_chats_cnt = co.get_chat_history(
            chat_id, nosql_conn, logger, issue_id=issue_id
        )

        if prv_chats_cnt == 0:
            all_prv_chats = {
                "session_id": str(session_id),
                "chat_id": chat_id,
                "messages": [],
            }

        return all_prv_chats
    except Exception as e:
        logger.error(f"Exception in chatbot process: {e}\n{traceback.format_exc()}")
        return {"messages": []}
    finally:
        if ai_db_conn:
            db.close_connection(ai_db_conn, ai_db_pool_name)
            logger.info("DB connection released.")
        logger.info("Closing chatbot logger.")
        lg.shutdown_logger(logger)

@router.post(
    "/Feedback",
    summary="Insert Message Feedback",
    description="Inserts or updates feedback for a specific chat message in the NoSQL database.",
    operation_id="insert_message_feedback"
)
async def insert_message_feedback(
        request: MessageFeedback,
        nosql_conn=Depends(get_nosql_conn_dependency),
        log_dir_path=Depends(get_log_dir_path)
):
    logger = lg.configure_logger(f"{log_dir_path}/MessageFeedback")
    msg_insert_flg = co.update_message_feedback(request.model_dump(), nosql_conn, logger)
    lg.shutdown_logger(logger)

    return msg_insert_flg
