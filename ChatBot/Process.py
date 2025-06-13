from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
import uvicorn
from contextlib import asynccontextmanager
import asyncio
import sys
import os


from src.app.services.dbConnect import DBConnection as db
from src.app.services.nosqlConnection import NoSQLConnectionManager as ncm
from src.main.routers.salesAgentRouters import router as sales_routers
from src.main.routers.supportAgentRouters import router as support_routers
from src.main.routers.configRouters import router as config_routers
from src.main.routers.fileRouters import router as file_routers
from src.main.routers.healthCheckRouters import router as health_routers
from src.main.routers.chatRouters import router as chat_routers
from src.main.routers.jiraRouters import router as service_issues_routers


nosql_conn = None
ai_db_pool_name = 'ai_db_conn_service'

agent_files_upload_dir = "../../DownloadedFiles/AgentFiles"
os.makedirs(agent_files_upload_dir, exist_ok=True)

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@asynccontextmanager
async def lifespan(ab_app: FastAPI):
    with open('configuration/db_config.json', 'rb') as db_details:
        db_details = json.load(db_details)
    ai_db_details = db_details.get('WAI_NONPROD')
    nosql_db_details = db_details.get('WAI_NoSQL')

    db.initialize_pool(None, ai_db_pool_name, db_details=ai_db_details) # type: ignore[attr-defined]
    ab_app.state.nosql_conn = ncm.get_nosql_conn(nosql_db_details=nosql_db_details, private_key_file='../certs/oci_private.pem') # type: ignore[attr-defined]

    yield
    db.close_pool(ai_db_pool_name)
    ncm.close_nosql_conn(ab_app.state.nosql_conn) # type: ignore[attr-defined]


app = FastAPI(
    lifespan=lifespan,
    title="ChatBot",
    version='0.3.1',
    description="An intelligent Winfo AI Agents APIs"
)


origin_regex = r"^https:\/\/([a-zA-Z0-9-]+\.)*winfosolutions\.com(:\d+)?$"

app.add_middleware(
    CORSMiddleware, # type: ignore[arg-type]
    allow_origin_regex=origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def enforce_https(request: Request, call_next):
    if request.url.scheme != "https":
        raise HTTPException(status_code=403, detail="HTTPS is required")
    return await call_next(request)


app.state.db_config_path = 'configuration/db_config.json' # type: ignore[attr-defined]
app.state.log_dir = 'logs' # type: ignore[attr-defined]
app.state.google_key_config_path = 'configuration/Google_Key(WAI).json' # type: ignore[attr-defined]
app.state.ai_db_pool_name = 'ai_db_conn_service' # type: ignore[attr-defined]
app.state.nosql_oci_private_key = '../certs/oci_private.pem' # type: ignore[attr-defined]
app.state.agent_files_upload_dir = "DownloadedFiles/AgentFiles" # type: ignore[attr-defined]
app.state.jira_config_path = "configuration/jira_config.json" # type: ignore[attr-defined]


app.include_router(health_routers, prefix="/Check", tags=["Health"])
app.include_router(sales_routers, prefix="/WAI/PreSalesAgent", tags=["PreSalesAgent"])
app.include_router(support_routers, prefix="/WAI", tags=["SupportAgent"])
app.include_router(config_routers, prefix="/WAI/Config", tags=["Configuration"])
app.include_router(chat_routers, prefix="/WAI/Chat", tags=["Chat"])
app.include_router(service_issues_routers, prefix="/WAI/Issues", tags=["Service Issues"])
app.include_router(file_routers, prefix="/WAI/File", tags=["File"])


if __name__ == "__main__":
    cert_path = "../certs/fullchain.pem"
    key_path = "../certs/privkey.pem"

    uvicorn.run(
        app,
        port=8110,
        ssl_keyfile=key_path,
        ssl_certfile=cert_path,
        timeout_keep_alive=0
    )