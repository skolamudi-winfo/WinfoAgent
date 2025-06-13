from fastapi import APIRouter, Depends
import json


from src.main.dependencies import get_ai_db_pool_dependency, get_log_dir_path, get_db_config_path, get_nosql_oci_private_key
from src.app.utils.loggerConfig import LoggerManager as lg
from src.app.services.dbConnect import DBConnection as db
from src.app.services.nosqlConnection import NoSQLConnectionManager as ncm

router = APIRouter()


@router.get(
    "/Health",
    summary="Health Check",
    description="Returns the health status of the ChatBot API.",
    operation_id="health_check"
)
async def health_check():
    return {"status": "Success"}

@router.get(
    "/TestConnections",
    summary="Test Database and Logger Connections",
    description="Tests the connectivity to the main database, NoSQL database, and logger. Returns a message indicating the status.",
    operation_id="test_connections"
)
async def test_connections(
        ai_db_pool_name=Depends(get_ai_db_pool_dependency),
        log_dir_path=Depends(get_log_dir_path),
        db_config_path=Depends(get_db_config_path),
        nosql_oci_private_key=Depends(get_nosql_oci_private_key)
):
    """Tests database and logging connections."""
    logger = lg.configure_logger(f"{log_dir_path}/testConnections")
    ai_db_conn = None
    l_nosql_conn = None
    try:
        logger.info("Testing database connection...")
        ai_db_conn = db.get_connection(ai_db_pool_name)

        with open(db_config_path, 'rb') as db_details:
            db_details = json.load(db_details)

        l_nosql_db_details = db_details.get('WAI_NoSQL')
        l_nosql_conn = ncm.get_nosql_conn(nosql_db_details=l_nosql_db_details, private_key_file=nosql_oci_private_key)
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
