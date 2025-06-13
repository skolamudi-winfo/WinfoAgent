from fastapi import APIRouter, Depends
from fastapi import HTTPException, Request
import json


from src.main.dependencies import get_nosql_conn_dependency, get_log_dir_path
from src.app.metadata.configDataManager import PromptConfigManager as pcm
from src.app.metadata.configDataManager import CustomerProcessDetailsConfigManager as cpdm
from src.app.utils.loggerConfig import LoggerManager as lg
from src.main.models.configModels import PromptConfigList, ProcessDetailsConfigList

router = APIRouter()

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


@router.post(
    "/PromptManager",
    dependencies=[Depends(limit_body_size(100 * 1024 * 1024))],
    summary="Manage Prompt Configurations",
    description="Insert, update, or delete prompt configurations for the chatbot. Accepts a list of prompt configurations.",
    operation_id="prompt_config_manager"
)
async def prompt_config_manager(
        config_data: PromptConfigList,
        nosql_conn=Depends(get_nosql_conn_dependency),
        log_dir_path=Depends(get_log_dir_path)
):
    logger = lg.configure_logger(f"{log_dir_path}/PromptConfigManager")
    config_data = config_data.model_dump()
    config_data = config_data.get('prompts')
    res = await pcm.manage_prompts_config(config_data, nosql_conn, logger)
    lg.shutdown_logger(logger)

    return res

@router.get(
    "/PromptsConfigData",
    summary="Get All Prompt Configurations",
    description="Fetches all configured prompts from the NoSQL database.",
    operation_id="get_configured_prompts"
)
async def get_configured_prompts(nosql_conn=Depends(get_nosql_conn_dependency), log_dir_path=Depends(get_log_dir_path)):
    logger = lg.configure_logger(f"{log_dir_path}/GetPromptsData")
    prompts_res = await pcm.get_prompts_data(nosql_conn, logger)
    lg.shutdown_logger(logger)

    return prompts_res

@router.post(
    "/CustomerProcessDetailsManager",
    dependencies=[Depends(limit_body_size(100 * 1024 * 1024))],
    summary="Manage Customer Process Details",
    description="Insert, update, or delete customer process details configuration. Accepts a list of process details.",
    operation_id="customer_process_details_manager"
)
async def prompt_config_manager(
        config_data: ProcessDetailsConfigList,
        nosql_conn=Depends(get_nosql_conn_dependency),
        log_dir_path=Depends(get_log_dir_path)
):
    logger = lg.configure_logger(f"{log_dir_path}/CustomerProcessDetailsConfigManager")
    config_data = config_data.model_dump()
    config_data = config_data.get('process_details')
    # print(config_data)
    res = await cpdm.manage_process_details_config(config_data, nosql_conn, logger)
    lg.shutdown_logger(logger)

    return res

@router.get(
    "/CustomerProcessConfigData",
    summary="Get All Customer Process Configurations",
    description="Fetches all configured customer process details from the NoSQL database.",
    operation_id="get_customer_process_config_data"
)
async def get_configured_process_data(nosql_conn=Depends(get_nosql_conn_dependency), log_dir_path=Depends(get_log_dir_path)):
    logger = lg.configure_logger(f"{log_dir_path}/GetCustomerProcessData")
    process_res = await cpdm.get_process_details_data(nosql_conn, logger)
    lg.shutdown_logger(logger)

    return process_res

