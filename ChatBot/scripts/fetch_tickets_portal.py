import json


if __name__ == '__main__':
    import asyncio
    from src.app.utils.loggerConfig import LoggerManager as lg
    from src.app.services.dbConnect import DBConnection as db
    from src.app.services.jiraActivities import JiraActivities as ja
    from src.app.services.nosqlConnection import NoSQLConnectionManager as ncm

    with open('../configuration/db_config.json', 'r') as db_details:
        db_details = json.load(db_details)

        ai_db_details = db_details.get('WAI_NONPROD')
        nosql_db_details = db_details.get('WAI_NoSQL')

    l_wai_conn = db.connect_db('wai_nonprod', db_details=ai_db_details)
    nosql_conn = ncm.get_nosql_conn(nosql_db_details=nosql_db_details, private_key_file='../../certs/oci_private.pem')
    l_logger = lg.configure_logger('../logs/FetchTicketsFromPortal')
    asyncio.run(
        ja.jira_support_agents(
            l_wai_conn,
            nosql_conn,
            l_logger,
            google_key_config_path='../configuration/Google_Key(WAI).json',
            jira_config_path='../configuration/jira_config.json',
            save_attachments_path='../DownloadedFiles/JiraFiles'
        )
    )
    db.close_connection(l_wai_conn, 'wai_nonprod')
    db.close_all_pools()
    ncm.close_nosql_conn(nosql_conn)
    lg.shutdown_logger(l_logger)
