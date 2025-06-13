import json
from fastapi import FastAPI, BackgroundTasks, Body, Request, HTTPException, Depends
from pydantic import BaseModel
import uvicorn
import traceback
import asyncio
import sys
from contextlib import asynccontextmanager

from chatPackages.dbConnect import DBConnection as db
from chatPackages.loggerConfig import LoggerManager as lg
from chatPackages.chatBot import SalesChatBot as scb
from chatPackages.chatBot import ChatOperations as co
from chatPackages.chatBot import SupportChatBot as suppa
from chatPackages.jiraActivities import JiraActivities as ja
from chatPackages.nosqlConnection import NoSQLConnectionManager as ncm
from NoSQLMetaData.configDataInsertion import PromptConfigManager as pcm

GOOGLE_KEY_CONFIG_PATH = 'configuration/Google_Key(WAI).json'

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

ai_db_pool = None
nosql_conn = None
ai_db_pool_name = 'ai_db_conn_service'

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles app startup and shutdown."""
    global ai_db_pool
    global nosql_conn

    with open('configuration/config.json', 'rb') as db_details:
        db_details = json.load(db_details)

    ai_db_details = db_details.get('WAI_NONPROD')
    nosql_db_details = db_details.get('WAI_NoSQL')

    ai_db_pool = db.initialize_pool(None, ai_db_pool_name, db_details=ai_db_details)
    nosql_conn = ncm.get_nosql_conn(nosql_db_details=nosql_db_details, private_key_file='../certs/oci_private.pem')

    yield
    db.close_pool(ai_db_pool_name)
    ncm.close_nosql_conn(nosql_conn)
    

app = FastAPI(lifespan=lifespan,title="ChatBot")


class SalesChatRequest(BaseModel):
    question: str
    session_id: str
    query_level: str
    user_name: str
    chat_id: str
    product_name: str


class SupportChatRequest(BaseModel):
    user_message: str
    session_id: str
    chat_id: str
    user_name: str
    issue_id: str
    customer_name: str
    product_name: str


class MessageFeedback(BaseModel):
    chat_id: str
    message_id: int
    feedback: dict


class JiraRequest(BaseModel):
    status: str
    assignee: str
    project_name: str


class ChatResponse(BaseModel):
    chat_id: str
    message_id: int


async def load_issue():
    logger = lg.configure_logger(f"logs/WAISupportAgentIssueLoader")
    ai_db_conn = db.get_connection(ai_db_pool_name)
    ja.jira_support_agents(
        ai_db_conn,
        nosql_conn,
        logger,
        google_key_config_path=GOOGLE_KEY_CONFIG_PATH,
        jira_config_path='configuration/jira_config.json'
    )

    if ai_db_conn:
        try:
            db.close_connection(ai_db_conn, ai_db_pool_name)
            logger.info("DB connection released.")
        except Exception as e:
            logger.error(f"Error releasing DB connection: {e}")

    logger.info("Closing 'issue loader' logger..")
    lg.shutdown_logger(logger)


async def process_sales_request(data: dict, query_level: str):
    ai_db_conn = None
    logger = lg.configure_logger(f"logs/WAI{query_level}Agent")
    try:
        logger.info(f"Processing {query_level} chatbot request...")
        ai_db_conn = db.get_connection(ai_db_pool_name)
        data["query_level"] = query_level
        bot_res, chat_id, query_id = await scb.sales_chatbot(
            data,
            ai_db_conn,
            logger,
            model_name="gemini-2.0-flash-001",
            nearest_neighbours=30,
            google_key_config_path=GOOGLE_KEY_CONFIG_PATH,
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


async def process_support_agent(data: dict):
    ai_db_conn = None
    logger = lg.configure_logger(f"logs/WAISupportAgent")
    try:
        logger.info(f"Processing WAI Support Agent request...")
        ai_db_conn = db.get_connection(ai_db_pool_name)
        bot_res, chat_id, message_id = await suppa.support_agent(
        data,
        ai_db_conn,
        nosql_conn,
        logger,
        model_name='gemini-2.0-flash-001',
        nearest_neighbours=30,
        google_key_config_path=GOOGLE_KEY_CONFIG_PATH
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


def limit_body_size(max_size: int):
    async def dependency(request: Request):
        body = await request.body()

        if len(body) > max_size:
            raise HTTPException(status_code=413, detail="Request body too large")

        try:
            parsed_json = json.loads(body)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON body")

        request.state.parsed_json = parsed_json

    return dependency


@app.get("/")
async def health_check():
    return {"status": "Success"}

@app.get("/TestConnections")
async def test_connections():
    """Tests database and logging connections."""
    logger = lg.configure_logger("logs/testConnections")
    ai_db_conn = None
    l_nosql_conn = None
    try:
        logger.info("Testing database connection...")
        ai_db_conn = db.get_connection(ai_db_pool_name)

        with open('configuration/config.json', 'rb') as db_details:
            db_details = json.load(db_details)

        l_nosql_db_details = db_details.get('WAI_NoSQL')
        l_nosql_conn = ncm.get_nosql_conn(nosql_db_details=l_nosql_db_details, private_key_file='../certs/oci_private.pem')
        return {"message": "Logger and database connections are working fine."}
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return {"error": str(e)}
    finally:
        if ai_db_conn:
            db.close_connection(ai_db_conn, ai_db_pool_name)
            logger.info("Application DB connection released.")

        if l_nosql_conn:
            ncm.close_nosql_conn(l_nosql_conn)
            logger.info("NoSQL DB connection released.")

        logger.info("Closing connection test logger.")
        lg.shutdown_logger(logger)

@app.get("/WAI/LoadIssues")
async def issue_loader(background_tasks: BackgroundTasks):
    """Handles issues loader asynchronously."""
    background_tasks.add_task(load_issue)
    return "Processing started in the background, it will take a few minutes..."

@app.post("/WAI/PreSalesAgent/Advanced")
async def sales_chatbot_advanced(request: SalesChatRequest, background_tasks: BackgroundTasks):
    """Handles advanced chatbot queries asynchronously."""
    background_tasks.add_task(process_sales_request, request.model_dump(), "Advanced")
    return {"data_type": "text", "data": "Processing started in the background."}

@app.post("/WAI/PreSalesAgent/Basic")
async def sales_chatbot_basic(request: SalesChatRequest):
    """Handles basic chatbot queries."""
    return await process_sales_request(request.model_dump(), "Basic")

@app.post("/WAI/Chat/SupportAgent")
async def support_chatbot(request: SupportChatRequest):
    """Handles support chatbot queries."""
    return await process_support_agent(request.model_dump())

@app.post("/WAI/Chat/MaxMessageId")
async def max_message_id(data: dict):
    logger = lg.configure_logger(f"logs/MaxQueryIdBot")
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

@app.post("/WAI/Chat/Response")
async def agent_chat_response(data: ChatResponse):
    logger = lg.configure_logger(f"logs/ChatResponse")
    logger.info(f"Processing Chat Response chatbot request...")
    try:
        data = data.model_dump()
        chat_id = data.get('chat_id')
        message_id = data.get('message_id')
        chat_resp = scb.get_chat_response(chat_id, message_id, nosql_conn, logger)
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

@app.post("/WAI/Chat/History")
async def get_chat_history(data: dict):
    logger = lg.configure_logger("logs/ChatHistory")
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

@app.post("/WAI/Config/PromptManager", dependencies=[Depends(limit_body_size(10 * 1024 * 1024))])
async def prompt_config_manager(config_data: list=Body(...)):
    logger = lg.configure_logger("logs/PromptConfigManager")
    res = await pcm.manage_prompts_config(config_data, nosql_conn, logger)
    lg.shutdown_logger(logger)

    return res

@app.post("/WAI/Chat/Feedback")
async def insert_message_feedback(request: MessageFeedback):
    logger = lg.configure_logger("logs/MessageFeedback")
    msg_insert_flg = co.update_message_feedback(request.model_dump(), nosql_conn, logger)
    lg.shutdown_logger(logger)

    return msg_insert_flg


if __name__ == "__main__":
    cert_path = "../certs/cert.pem"
    key_path = "../certs/privkey.pem"

    uvicorn.run(
        app
        ,port=8110
        ,ssl_keyfile=key_path
        ,ssl_certfile=cert_path
        ,timeout_keep_alive=0
    )
