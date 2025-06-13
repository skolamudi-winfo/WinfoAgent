from fastapi import APIRouter, BackgroundTasks, Depends
import traceback


from src.main.models.salesModels import SalesChatRequest
from src.app.chatbot.chatBot import SalesChatBot as scb
from src.app.services.dbConnect import DBConnection as db
from src.app.utils.loggerConfig import LoggerManager as lg
from src.main.dependencies import (
    get_ai_db_pool_dependency,
    get_google_key_config_path_dependency,
    get_log_dir_path
)

router = APIRouter()


async def process_sales_request(
    data: dict,
    query_level: str,
    ai_db_pool_name: str,
    google_key_config_path: str,
    log_dir_path: str
):
    ai_db_conn = None
    logger = lg.configure_logger(f"{log_dir_path}/WAI{query_level}Agent")
    try:
        logger.info(f"Processing {query_level} chatbot request...")
        ai_db_conn = db.get_connection(ai_db_pool_name)
        data["query_level"] = query_level
        bot_res, chat_id, query_id = await scb.sales_chatbot(
            data,
            ai_db_conn,
            logger,
            model_name="gemini-2.5-flash-preview-05-20",
            nearest_neighbours=30,
            google_key_config_path=google_key_config_path
        )
        return {
            "data_type": "text",
            "data": bot_res or "Unable to fetch response, please contact support.",
            "chat_id": chat_id,
            "query_id": query_id,
        }
    except Exception as e:
        logger.error(f"Exception in chatbot process: {e}\n{traceback.format_exc()}")
        return {"data_type": "text", "data": "Error processing request.", "chat_id": None, "query_id": None}
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
    "/Advanced",
    summary="Start Advanced Pre-Sales Chat",
    description="Initiates an advanced pre-sales chatbot query as a background task. Returns immediately with a processing message.",
    operation_id="sales_chatbot_advanced"
)
async def sales_chatbot_advanced(
    request: SalesChatRequest,
    background_tasks: BackgroundTasks,
    ai_db_pool_name=Depends(get_ai_db_pool_dependency),
    google_key_config_path=Depends(get_google_key_config_path_dependency),
    log_dir_path=Depends(get_log_dir_path)
):
    """Handles advanced chatbot queries asynchronously."""
    background_tasks.add_task(
        process_sales_request,
        request.model_dump(),
        "Advanced",
        ai_db_pool_name=ai_db_pool_name,
        google_key_config_path=google_key_config_path,
        log_dir_path=log_dir_path
    )
    return {"data_type": "text", "data": "Processing started in the background."}

@router.post(
    "/Basic",
    summary="Start Basic Pre-Sales Chat",
    description="Processes a basic pre-sales chatbot query and returns the response synchronously.",
    operation_id="sales_chatbot_basic"
)
async def sales_chatbot_basic(
    request: SalesChatRequest,
    ai_db_pool_name=Depends(get_ai_db_pool_dependency),
    google_key_config_path=Depends(get_google_key_config_path_dependency),
    log_dir_path=Depends(get_log_dir_path)
):
    """Handles basic chatbot queries."""
    return await process_sales_request(
        request.model_dump(),
        "Basic",
        ai_db_pool_name=ai_db_pool_name,
        google_key_config_path=google_key_config_path,
        log_dir_path=log_dir_path
    )
