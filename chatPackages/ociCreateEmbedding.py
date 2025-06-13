import json
import oci
import pandas as pd
import string
import os

import chatPackages.db_connect as oci_db


CONFIG_PROFILE = "DEFAULT"
config = oci.config.from_file('../configuration/oci_ai_config.txt', CONFIG_PROFILE)


def get_excel_data(file_path):
    processed_content_list = []

    try:
        df = pd.read_excel(file_path)

        for index, row in df.iterrows():
            query = row['query']
            answer = row['answer']
            content_id = row['content_id']

            processed_content = query.lower()
            processed_content = processed_content.translate(str.maketrans('', '', string.punctuation))
            processed_data = {'answer': answer,
                              'query': processed_content,
                              'content_id': content_id}
            processed_content_list.append(processed_data)

        processed_content_list = json.dumps(processed_content_list, indent=2)
    except Exception as e:
        print(f'Exception in get excel data: {e}')

    return processed_content_list


def get_embedding(
        input_text,
        logger,
        compartment_id="ocid1.compartment.oc1..aaaaaaaa4s2upstujcl2qp2kz5zw2v2a7cc3naotw3cgybjsp2neoxumqncq",
        endpoint="https://inference.generativeai.uk-london-1.oci.oraclecloud.com",
        model_id="cohere.embed-english-v3.0"
):
    logger.info(f'Get Embedding Function Called')
    generative_ai_inference_client = oci.generative_ai_inference.GenerativeAiInferenceClient(
        config=config,
        service_endpoint=endpoint,
        retry_strategy=oci.retry.NoneRetryStrategy(),
        timeout=(10, 240)
    )
    embed_text_detail = oci.generative_ai_inference.models.EmbedTextDetails()
    embed_text_detail.serving_mode = oci.generative_ai_inference.models.OnDemandServingMode(
        model_id=model_id
    )
    embed_text_detail.inputs = [input_text.lower()]
    embed_text_detail.truncate = "NONE"
    embed_text_detail.compartment_id = compartment_id

    embed_text_response = generative_ai_inference_client.embed_text(embed_text_detail)

    if hasattr(embed_text_response.data, "embeddings"):
        embeddings = embed_text_response.data.embeddings
        return embeddings
    else:
        return None


def create_embedding(processed_data):
    embeddings = []
    processed_data = json.loads(processed_data)
    embedding_id = 1

    for each_line in processed_data:
        # answer = each_line['answer']
        query = each_line['query']
        content_id = each_line['content_id']
        embedding = get_embedding(query)
        embeddings.append({
            'id': embedding_id,
            'query': query.strip(),
            'content_id': content_id,
            'embedding': embedding[0]
        })

        embedding_id += 1

    return embeddings


def create_jsonl_file(embedding_data, file_name):
    file_path = f'DownloadedFiles/embedding/{file_name}.jsonl'

    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)
    try:
        with open(file_path, 'w') as f:
            for each_entity in embedding_data:
                json.dump(each_entity, f)
                f.write('\n')
        return file_path
    except Exception as e:
        print(f'Failed to write content to jsonl file. Error details: {e}')
        return ''


def insert_query_data_embeddings(embedding_file_path):
    with open(embedding_file_path) as emb_data:
        conn = oci_db.connect_db()
        with conn.cursor() as db_cursor:
            embedding_insert_query = (
                "INSERT INTO SALES_DOC_EMBEDDING(VECTOR_ID, CONTENT_ID, QUERY, EMBEDDING) "
                "VALUES(:vector_id, :content_id, :query, :embedding)"
            )
            for each_embedding in emb_data:
                insert_embedding_db(each_embedding, embedding_insert_query, db_cursor)

        oci_db.close_connection(conn)


def insert_embedding_db(embedding_row, embedding_insert_query, db_cursor):
    embedding_row = json.loads(embedding_row)
    db_cursor.execute(
        embedding_insert_query,
        {
            'vector_id': embedding_row['id'],
            'content_id': embedding_row['content_id'],
            'query': embedding_row['query'],
            'embedding': f"{embedding_row['embedding']}"
        }
    )
    db_cursor.connection.commit()


def create_excel_from_jsonl(jsonl_file_path, excel_file_path):
    """
    Reads a .jsonl file and writes the data to an Excel file with specified columns.

    Parameters:
    - jsonl_file_path (str): Path to the input .jsonl file.
    - excel_file_path (str): Path where the output Excel file will be saved.

    Returns:
    - None
    """
    # List to hold parsed data
    data = []

    try:
        # Open the .jsonl file and parse each line
        with open(jsonl_file_path, 'r') as file:
            for line in file:
                record = json.loads(line.strip())  # Parse JSON line
                data.append({
                    'id': record.get('id'),
                    'content_id': record.get('content_id'),
                    'query': record.get('query'),
                    'answer': record.get('answer'),
                    'embedding': record.get('embedding')
                })

        # Create a DataFrame
        df = pd.DataFrame(data)

        # Save the DataFrame to an Excel file
        df.to_excel(excel_file_path, index=False)

        print(f"Excel file created successfully: {excel_file_path}")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == '__main__':
    # l_file_name = 'DownloadedFiles/SalesQueries(update).xlsx'
    # l_processed_content = get_excel_data(l_file_name)
    # print(f'l_processed_content: {l_processed_content}')
    # l_embeddings = create_embedding(l_processed_content)
    # print(f'l_embeddings: {l_embeddings}')
    # l_embedding_file_path = create_jsonl_file(l_embeddings, 'SalesEmbedding(update)')
    # print(f'l_embedding_file_path: {l_embedding_file_path}')
    # create_excel_from_jsonl('DownloadedFiles/embedding/SalesEmbedding.jsonl', 'DownloadedFiles/embedding/SalesEmbedding.xlsx')
    # insert_query_data_embeddings('DownloadedFiles/embedding/SalesEmbedding(update).jsonl')


    # from oci_db_connect import DBConnection as oci_db
    from loggerConfig import LoggerManager as lg

    l_logger = lg.configure_logger('../logs/create_embedding')

    # conn = oci_db.connect_db('../configuration/oci_db_config.json')
    # with conn.cursor() as db_cursor:
    #     query = "SELECT query_id, QUERY FROM SALES_CONTENT_EMBEDDING_NEW_LLAMA"
    #     db_cursor.execute(query)
    #     rows = db_cursor.fetchall()
    #     for row in rows:
    #         embedding = get_embedding(str(row[1]), l_logger)
    #         print(f"question: {row[1]}")
    #         print(embedding[0])
    #
    #         update_query = f"UPDATE SALES_CONTENT_EMBEDDING_NEW_LLAMA SET EMBEDDING = '{embedding[0]}' WHERE QUERY_ID = :query_id"
    #         db_cursor.execute(update_query, {'query_id': row[0]})
    #         db_cursor.connection.commit()
            # break
    txt = "how does winfobots free up human resources from repetitive tasks"
    print(get_embedding(txt, logger=l_logger))

    lg.shutdown_logger(l_logger)
    # oci_db.close_connection(conn)


