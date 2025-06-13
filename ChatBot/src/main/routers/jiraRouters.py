from fastapi import APIRouter, BackgroundTasks, Depends

from src.main.dependencies import (
    get_ai_db_pool_dependency,
    get_nosql_conn_dependency,
    get_google_key_config_path_dependency,
    get_log_dir_path,
    get_jira_config_path
)
from src.app.services.dbConnect import DBConnection as db
from src.app.utils.loggerConfig import LoggerManager as lg
from src.app.services.jiraActivities import JiraActivities as ja


router = APIRouter()


async def load_issue(
    ai_db_pool_name,
    nosql_conn,
    google_key_config_path,
    log_dir_path,
    jira_config_path
):
    logger = lg.configure_logger(f"{log_dir_path}/WAISupportAgentIssueLoader")
    ai_db_conn = db.get_connection(ai_db_pool_name)
    await ja.jira_support_agents(
        ai_db_conn,
        nosql_conn,
        logger,
        google_key_config_path=google_key_config_path,
        jira_config_path=jira_config_path
    )

    if ai_db_conn:
        try:
            db.close_connection(ai_db_conn, ai_db_pool_name)
            logger.info("DB connection released.")
        except Exception as e:
            logger.error(f"Error releasing DB connection: {e}")

    logger.info("Closing 'issue loader' logger..")
    lg.shutdown_logger(logger)


@router.get(
    "/Load",
    summary="Load Latest Support Issues",
    description="Triggers an asynchronous background task to fetch the latest support tickets from Jira and update the database.",
    operation_id="issue_loader"
)
async def issue_loader(
    background_tasks: BackgroundTasks,
    ai_db_pool_name=Depends(get_ai_db_pool_dependency),
    nosql_conn=Depends(get_nosql_conn_dependency),
    google_key_config_path=Depends(get_google_key_config_path_dependency),
    log_dir_path=Depends(get_log_dir_path),
    jira_config_path=Depends(get_jira_config_path)
):
    """Handles issues loader asynchronously."""
    background_tasks.add_task(
        load_issue,
        ai_db_pool_name=ai_db_pool_name,
        nosql_conn=nosql_conn,
        google_key_config_path=google_key_config_path,
        log_dir_path=log_dir_path,
        jira_config_path=jira_config_path
    )
    return "Fetching the latest tickets, it will take a few minutes..."
