from chatPackages.nosqlConnection import NoSQLConnectionManager as cm, NoSQLSchemaManager as sm


def create_nosql_objects(handle):
    """"""
    create_sequence_table = """
    CREATE TABLE IF NOT EXISTS SequenceTable (
        name STRING,
        value INTEGER,
        PRIMARY KEY(name)
    )
    """

    create_chat_sessions = """
    CREATE TABLE IF NOT EXISTS ChatSessions (
        session_id STRING,
        chat_id STRING,
        user_name STRING,
        start_time TIMESTAMP(6),
        end_time TIMESTAMP(6),
        meta_data JSON,
        issue_id STRING,
        PRIMARY KEY(SHARD(chat_id))
    )
    """

    create_messages = """
    CREATE TABLE IF NOT EXISTS ChatMessages (
        chat_id STRING,
        message_id STRING,
        user_message STRING,
        response JSON,
        message_time TIMESTAMP(6),
        response_time TIMESTAMP(6),
        nearest_neighbours STRING,
        error_msg STRING,
        PRIMARY KEY(chat_id, message_id)
    )
    """

    create_feedback = """
    CREATE TABLE IF NOT EXISTS ChatFeedback (
        chat_id STRING,
        message_id INTEGER,
        feedback JSON,
        PRIMARY KEY(chat_id, message_id)
    )
    """

    create_customer_details = """
    CREATE TABLE IF NOT EXISTS CustomerProcessDetails (
        customer_process_detail_id INTEGER,
        customer_name STRING,
        process_name STRING,
        subprocess STRING,
        process_details JSON,
        product_name STRING,
        PRIMARY KEY(SHARD(customer_process_detail_id))
    )
    """

    create_sales_content = """
    CREATE TABLE IF NOT EXISTS SalesContent (
        content_id INTEGER,
        content_details JSON,
        file_name STRING,
        product STRING,
        questions_generated STRING,
        PRIMARY KEY(SHARD(content_id))
    )
    """

    create_support_content_doc = """
    CREATE TABLE IF NOT EXISTS SupportDocumentsContent (
        content_id INTEGER,
        content_details JSON,
        file_name STRING,
        product_name STRING,
        process_area STRING,
        process_name STRING,
        sub_process STRING,
        questions_generated STRING,
        PRIMARY KEY(SHARD(content_id))
    )
    """

    create_resolver_agent_response_support = """
    CREATE TABLE IF NOT EXISTS SupportResolverAgentResponses(
        chat_id INTEGER,
        message_id INTEGER,
        chat_start_time TIMESTAMP(6),
        chat_end_time TIMESTAMP(6),
        ag3_doc_resp JSON,
        ag3_app_db_resp JSON,
        ag3_oracle_db_resp JSON,
        ag5_resp JSON,
        ag6_resp JSON,
        ag7_resp JSON,
        PRIMARY KEY(chat_id, message_id)
    )
    """

    create_ticket_summary = """
    CREATE TABLE IF NOT EXISTS TicketSummary(
	issue_id STRING,
	chat_id STRING,
	processed_message_id INTEGER,
	processed_comment_id INTEGER,
	ticket_status STRING,
	summary JSON,
	customer_name STRING,
	product_name STRING,
	last_accessed_time TIMESTAMP(6),
	PRIMARY KEY(chat_id)	
    )
    """

    support_doc_content_index1 = """
    CREATE INDEX IF NOT EXISTS idx_proj_support_docs ON SupportDocumentsContent (
        content_id,
        questions_generated
    )
    """

    support_prompts_config = """
    CREATE TABLE IF NOT EXISTS WAIAgentPromptsConfig (
        agent_prompt_id INTEGER,
        system_instruction STRING,
        response_schema JSON,
        input_prompt STRING,
        prompt_level STRING,
        customer STRING,
        llm_model_name STRING,
        llm_server_location STRING,
        prompt_created_by STRING,
        google_search BOOLEAN,
        prompt_creation_time TIMESTAMP(6),
        prompt_last_updated TIMESTAMP(6),
        prompt_last_updated_by STRING,
        nearest_neighbours INTEGER,
        comments STRING,
        product_name STRING,
        PRIMARY KEY(agent_prompt_id)
    )
    """

    sm.create_table(handle, create_sequence_table, 'SequenceTable', read_units=50, write_units=50, storage_gb=1)
    sm.create_table(handle, create_chat_sessions, 'ChatSessions', read_units=50, write_units=50, storage_gb=2)
    sm.create_table(handle, create_messages, 'ChatMessages', read_units=50, write_units=50, storage_gb=2)
    sm.create_table(handle, create_feedback, 'ChatFeedback', read_units=10, write_units=20, storage_gb=1)
    sm.create_table(handle, create_customer_details, 'CustomerProcessDetails', read_units=50, write_units=10, storage_gb=1)
    sm.create_table(handle, create_sales_content, 'SalesContent', read_units=50, write_units=10, storage_gb=2)
    sm.create_table(handle, create_support_content_doc, 'SupportDocumentsContent', read_units=50, write_units=10, storage_gb=2)
    sm.create_table(handle, create_resolver_agent_response_support, 'SupportResolverAgentResponses', read_units=50, write_units=50, storage_gb=2)
    sm.create_table(handle, create_ticket_summary, 'TicketSummary', read_units=50, write_units=50, storage_gb=1)
    sm.create_table(handle, support_prompts_config, 'WAIAgentPromptsConfig', read_units=50, write_units=50, storage_gb=1)
    sm.create_index(handle, support_doc_content_index1)


if __name__ == '__main__':
    import json

    l_config = "../configuration/config.json"
    with open(l_config, 'rb') as config_data:
        config_data = json.load(config_data)

    if config_data['WAI_NoSQL'] and str(config_data['WAI_NoSQL']['DatabaseType']).lower() == 'nosql':
        oci_config_data = config_data['WAI_NoSQL']
    else:
        oci_config_data = None

    # print(oci_config_data)

    l_handler = cm.get_nosql_conn(
        compartment_id=oci_config_data['compartment_id'],
        user_id=oci_config_data['user'],
        fingerprint=oci_config_data['fingerprint'],
        tenant_id=oci_config_data['tenancy'],
        region=oci_config_data['region'],
        private_key_file='../../certs/oci_private.pem'
    )
    # print(l_handler)

    create_nosql_objects(l_handler)

    cm.close_nosql_conn(l_handler)
