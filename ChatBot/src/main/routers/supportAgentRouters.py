from fastapi import APIRouter, Depends
import traceback


from src.main.models.supportModels import SupportChatRequest
from src.app.chatbot.chatBot import SupportChatBot as suppa
from src.app.services.dbConnect import DBConnection as db
from src.app.utils.loggerConfig import LoggerManager as lg
from src.main.dependencies import (
    get_ai_db_pool_dependency,
    get_nosql_conn_dependency,
    get_google_key_config_path_dependency,
    get_log_dir_path
)

router = APIRouter()


async def process_support_agent(
        data: dict,
        ai_db_pool_name,
        nosql_conn,
        google_key_config_path,
        log_dir_path
):
    ai_db_conn = None
    logger = lg.configure_logger(f"{log_dir_path}/WAISupportAgent")
    try:
        logger.info(f"Processing WAI Support Agent request...")
        ai_db_conn = db.get_connection(ai_db_pool_name)
        bot_res, chat_id, message_id = await suppa.support_agent(
        data,
        ai_db_conn,
        nosql_conn,
        logger,
        model_name='gemini-2.5-flash-preview-05-20',
        nearest_neighbours=30,
        google_key_config_path=google_key_config_path
    )
        return {
            "data_type": "text",
            "data": bot_res or {"resolution":"Unable to get the response, please contact support."},
            "chat_id": chat_id,
            "message_id": message_id,
        }
    except Exception as e:
        logger.error(f"Exception in chatbot process: {e}\n{traceback.format_exc()}")
        return {"data_type": "text", "data": "Error processing request.", "chat_id": None, "message_id": None}
    finally:
        if ai_db_conn:
            try:
                db.close_connection(ai_db_conn, ai_db_pool_name)
                logger.info("DB connection released.")
            except Exception as e:
                logger.error(f"Error releasing DB connection: {e}")

        logger.info("Closing chatbot logger.")
        lg.shutdown_logger(logger)


@router.post(
    "/SupportAgent",
    summary="Support Chatbot Interaction",
    description="Handles support chatbot queries for customer issues and returns the response.",
    operation_id="support_chatbot"
)
async def support_chatbot(
    request: SupportChatRequest,
    ai_db_pool_name=Depends(get_ai_db_pool_dependency),
    nosql_conn=Depends(get_nosql_conn_dependency),
    google_key_config_path=Depends(get_google_key_config_path_dependency),
    log_dir_path=Depends(get_log_dir_path)
):
    """Handles support chatbot queries."""
    return await process_support_agent(
        request.model_dump(),
        ai_db_pool_name=ai_db_pool_name,
        nosql_conn=nosql_conn,
        google_key_config_path=google_key_config_path,
        log_dir_path=log_dir_path
    )
