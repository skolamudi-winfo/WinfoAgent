import os
import glob
import json
import time

from chatPackages.loggerConfig import LoggerManager as lg
from chatPackages.dbConnect import DBConnection as db
from chatPackages.nosqlConnection import NoSQLConnectionManager as cm
from chatPackages.pdfStringExtract import PDFUtils as pdfu


def sales_content_preparation(conn, logger):
    from chatPackages.chatBot import SalesChatBot, PDFProcessingService

    google_key_config_path = 'configuration/Google_Key(WinfoBots).json'
    product = 'WinfoTest'

    folder_path = "DownloadedFiles/need to process/pre process"
    for l_file_path in glob.glob(os.path.join(folder_path, "*")):
        PDFProcessingService.upload_pdf_to_gcs(l_file_path, 'SalesDocs', logger, pdf_chuck_size=3,
                                               google_key_path=google_key_config_path, bucket_name='winfobots',
                                               download_path='DownloadedFiles')

    with conn.cursor() as l_db_cursor:
        SalesChatBot.ContentPreparationService.content_preparation(
            bucket_name='winfobots',
            gcs_folder_path='SalesDocs',
            product=product,
            db_cursor=l_db_cursor,
            logger=logger,
            google_key_config_path=google_key_config_path
        )

    SalesChatBot.QuestionService.store_questions_db(product, conn, logger,
                                                    google_key_config_path=google_key_config_path)

    SalesChatBot.EmbeddingService.store_question_embedding_db(conn, logger,
                                                              google_key_config_path=google_key_config_path)

def winfobots_support_content_preparation(nosql_conn, app_conn, logger):
    from chatPackages.chatBot import WinfoBotsSupportProcessFiles

    google_key_config_path = 'configuration/Google_Key(WAI).json'
    product = 'WinfoBots'
    process_area = 'Supply Chain Management'

    folder_path_list = [
        "DownloadedFiles/Advanced Energy/Sales Order Creation - EBS",
        "DownloadedFiles/Advanced Energy/Sales Order Creation - SAP"
    ]

    for folder_path in folder_path_list:
        if folder_path.__contains__('EBS'):
            process_name = 'Sales Order Creation EBS'
        else:
            process_name = 'Sales Order Creation SAP'

        print(f"process_name: {process_name}")
        files_with_extensions = [
            f for f in glob.glob(os.path.join(folder_path, "**"), recursive=True)
            if os.path.isfile(f)
        ]
        print(files_with_extensions)
        for file_path in files_with_extensions:
            print(f"l_file_path: {file_path}")
            base_file_name = ''.join(os.path.basename(file_path).split('.')[:-1])
            print(f"base_file_name: {base_file_name}")

            try:
                pdf_chunk_file_paths = pdfu.split_pdf(
                    file_path, file_name=base_file_name, logger=logger, pdf_chuck_size=3,
                    download_path='DownloadedFiles/SupportDocs'
                )
            except Exception as e:
                logger.error(f"Failed to create chunks for file {file_path}. \nError: {e}")
                pdf_chunk_file_paths = []

            print(f"pdf_chunk_file_paths: {pdf_chunk_file_paths}")
            # break

            for each_file_chunk in pdf_chunk_file_paths:
                print(f"each_file_chunk: {each_file_chunk}")
                WinfoBotsSupportProcessFiles.ContentPreparationService.llm_content_preparation(
                    file_path=each_file_chunk,
                    product_name=product,
                    process_area=process_area,
                    process_name=process_name,
                    sub_process=base_file_name,
                    nosql_conn=nosql_conn,
                    logger=logger,
                    google_key_config_path=google_key_config_path
                )
                # break
                time.sleep(10)
            # break

    WinfoBotsSupportProcessFiles.QuestionService.store_questions_db(
        nosql_conn, app_conn, logger, google_key_config_path=google_key_config_path
    )

    WinfoBotsSupportProcessFiles.EmbeddingService.store_question_embedding_db(
        app_conn, logger, google_key_config_path=google_key_config_path
    )


def oracle_support_content_preparation(nosql_conn, app_conn, logger):
    from chatPackages.chatBot import OracleSupportProcessFiles

    google_key_config_path = 'configuration/Google_Key(WAI).json'
    product = 'Oracle'
    model_name='gemini-2.0-flash-001'
    location='us-central1'
    folder_path = "DownloadedFiles/SupportDocs/Oracle(WelFull)"

    files_process_details = {
  "best-practices-for-scheduled-processes.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Procurement",
    "sub_process": "Best Practices for Scheduled Processes"
  },
  "configuring-and-extending-applications.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Procurement",
    "sub_process": "Configuring and Extending Applications"
  },
  "creating-a-business-intelligence-cloud-extract.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Procurement",
    "sub_process": "Creating a Business Intelligence Cloud Extract"
  },
  "creating-and-administering-analytics-and-reports-for-procurement.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Procurement",
    "sub_process": "Creating and Administering Analytics and Reports for Procurement"
  },
  "extending-redwood-applications-for-hcm-and-scm-using-visual-builder-studio.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Procurement",
    "sub_process": "Extending Redwood Applications for HCM and SCM Using Visual Builder Studio"
  },
  "extract-data-stores-for-procurement.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Procurement",
    "sub_process": "Extract Data Stores for Procurement"
  },
  "getting-started-oracle-cloud.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Procurement",
    "sub_process": "Getting Started with Oracle Cloud Applications"
  },
  "how-do-i-get-started-with-sustainability.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Procurement",
    "sub_process": "How do I get started with Sustainability?"
  },
  "implementing-and-using-journeys.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Procurement",
    "sub_process": "Implementing and Using Journeys"
  },
  "implementing-enterprise-contracts.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Procurement",
    "sub_process": "Implementing Enterprise Contracts"
  },
  "implementing-procurement.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Procurement",
    "sub_process": "Implementing Procurement"
  },
  "integration-playbooks-for-procurement.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Procurement",
    "sub_process": "Integration Playbooks for Procurement"
  },
  "managing-and-monitoring-oracle-cloud.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Procurement",
    "sub_process": "Managing and Monitoring Oracle Cloud"
  },
  "scheduled-processes-for-procurement.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Procurement",
    "sub_process": "Scheduled Processes for Procurement"
  },
  "securing-erp.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Procurement",
    "sub_process": "Securing ERP"
  },
  "security-reference-for-common-features.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Procurement",
    "sub_process": "Security Reference for Common Features"
  },
  "security-reference-for-procurement.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Procurement",
    "sub_process": "Security Reference for Procurement"
  },
  "subject-areas-for-transactional-business-intelligence-in-procurement.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Procurement",
    "sub_process": "Subject Areas for Transactional Business Intelligence in Procurement"
  },
  "understanding-enterprise-structures.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Procurement",
    "sub_process": "Understanding Enterprise Structures"
  },
  "using-common-features.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Procurement",
    "sub_process": "Using Common Features"
  },
  "using-functional-setup-manager.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Procurement",
    "sub_process": "Using Functional Setup Manager"
  },
  "using-procurement-contracts.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Procurement",
    "sub_process": "Using Procurement Contracts"
  }
}
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        print(f"The path '{folder_path}' is not a valid directory.")
        return

    for absolute_file_path in glob.glob(os.path.join(folder_path, "*")):
        file = os.path.basename(absolute_file_path)
        try:
            # absolute_path = os.path.abspath(os.path.join(root, file))
            print(f"Absolute File Path: {absolute_file_path}, File Name: {file}")
            process_name = files_process_details.get(file).get('process_name')
            process_area = files_process_details.get(file).get('process_area')
            sub_process = files_process_details.get(file).get('sub_process')
            print(f"process_name: {process_name}, \nprocess_area: {process_area}, \nsub_process: {sub_process}")
        except Exception as e:
            logger.error(f"Failed to load the files content for file - {file}. \nError: {e}")
            continue

        OracleSupportProcessFiles.ContentPreparationService.content_preparation(
            absolute_file_path,
            file,
            product,
            process_name,
            process_area,
            sub_process,
            nosql_conn,
            logger,
            google_key_config_path=google_key_config_path,
            model_name=model_name,
            location=location
        )

    OracleSupportProcessFiles.EmbeddingService.store_content_embedding_db(
        nosql_conn, app_conn, logger, google_key_config_path=google_key_config_path
    )


if __name__ == '__main__':
    l_logger = lg.configure_logger('logs/load_files')
    l_config = "configuration/config.json"
    pool_name = 'oci_db_load_files'

    with open(l_config, 'rb') as config_data:
        config_data = json.load(config_data)

    l_app_conn_details = config_data['WAI_NONPROD']
    l_app_conn = db.connect_db(pool_name, db_details=l_app_conn_details)

    if config_data['WAI_NoSQL'] and str(config_data['WAI_NoSQL']['DatabaseType']).lower() == 'nosql':
        oci_config_data = config_data['WAI_NoSQL']
    else:
        oci_config_data = None

    l_handler = cm.get_nosql_conn(
        compartment_id=oci_config_data['compartment_id'],
        user_id=oci_config_data['user'],
        fingerprint=oci_config_data['fingerprint'],
        tenant_id=oci_config_data['tenancy'],
        region=oci_config_data['region'],
        private_key_file='../certs/oci_private.pem'
    )

    # sales_content_preparation(l_app_conn, l_logger)
    winfobots_support_content_preparation(l_handler, l_app_conn, l_logger)
    # oracle_support_content_preparation(l_handler, l_app_conn, l_logger)

    db.close_connection(l_app_conn, pool_name)
    cm.close_nosql_conn(l_handler)
    lg.shutdown_logger(l_logger)
