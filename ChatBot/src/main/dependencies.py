from fastapi import Request

def get_ai_db_pool_dependency(request: Request):
    return request.app.state.ai_db_pool_name

def get_nosql_conn_dependency(request: Request):
    return request.app.state.nosql_conn

def get_google_key_config_path_dependency(request: Request):
    return request.app.state.google_key_config_path

def get_log_dir_path(request: Request):
    return request.app.state.log_dir

def get_db_config_path(request: Request):
    return request.app.state.db_config_path

def get_nosql_oci_private_key(request: Request):
    return request.app.state.nosql_oci_private_key

def get_agent_files_upload_dir(request: Request):
    return request.app.state.agent_files_upload_dir

def get_jira_config_path(request: Request):
    return request.app.state.jira_config_path
