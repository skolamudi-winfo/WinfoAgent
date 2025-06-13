import json


if __name__ == '__main__':
    from chatPackages.loggerConfig import LoggerManager as lg
    from chatPackages.dbConnect import DBConnection as db
    from chatPackages.jiraActivities import JiraActivities as ja

    with open('configuration/config.json', 'r') as db_details:
        db_details = json.load(db_details)
        winfobot_dev_db = db_details.get('WINFOBOT_DEV')
        ai_db = db_details.get('AI_DB')

    l_winfobot_dev_db_conn = db.connect_db('winfobot_dev_db', db_details=winfobot_dev_db)
    l_ai_db_conn = db.connect_db('ai_db', db_details=ai_db)
    l_logger = lg.configure_logger('logs/FetchTicketsFromPortal')
    l_product_name = 'WinfoBots'

    ja.jira_support_agents(
        l_winfobot_dev_db_conn,
        l_ai_db_conn,
        l_logger,
        google_key_config_path='configuration/Google_Key(WinfoBots).json',
        jira_config_path='configuration/jira_config.json',
        save_attachments_path='DownloadedFiles/JiraFiles'
    )

    db.close_connection(l_winfobot_dev_db_conn, 'winfobot_dev_db')
    db.close_connection(l_ai_db_conn, 'ai_db')
    db.close_all_pools()
    lg.shutdown_logger(l_logger)
