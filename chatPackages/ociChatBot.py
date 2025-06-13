import pandas as pd
import json
import os
import re
from pathlib import Path

from chatPackages.prompts import VertexAIService as pr
from chatPackages.oci_create_embedding import get_embedding


class FileManager:

    @classmethod
    def load_excel_data(cls, file_path):
        """Load data from an Excel file."""
        return pd.read_excel(file_path)

    @classmethod
    def ensure_directory_exists(cls, file_path):
        """Ensure the parent directory exists for the given file path."""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

    @classmethod
    def save_json_to_file(cls, data, file_path):
        """
        Save the given data as JSON to a file.

        Ensures the target directory exists before attempting to save.
        Raises appropriate errors if the file cannot be written or the data 
        is not serializable to JSON.
        """
        cls.ensure_directory_exists(file_path)
        try:
            with open(file_path, 'w') as file:
                json.dump(data, file, indent=4)
        except TypeError as e:
            raise ValueError(f"Provided data is not JSON serializable: {e}")
        except IOError as e:
            raise IOError(f"Error writing to file {file_path}: {e}")


class DataProcessor:

    @classmethod
    def generate_content_result(cls, sales_document):
        """
        Extracts content and content IDs from the sales document 
        and stores them in a results dictionary.
        """
        content_result = {}
        for _, row in sales_document.iterrows():
            content_result[int(row['content_id'])] = row['content']
        return {'result': content_result}

    @classmethod
    def clean_newlines(cls, input_string: str):
        """
        Cleans up consecutive newline characters in the string.

        Replaces multiple newlines with a single newline and trims leading 
        or trailing whitespace.
        """
        cleaned_string = re.sub(r'\n+', '\n', input_string)
        return cleaned_string.strip()


class ContentRetriever:

    @classmethod
    def gather_content(cls, content_file_path, logger, content_output_file='DownloadedFiles/Sales/content.json'):
        """
        Checks if the content JSON file exists; if not, loads content 
        from an Excel file and converts it into JSON format.
        """
        try:
            file_path = Path(content_output_file)
            if not file_path.is_file():
                logger.info(f'File does not exist: {content_output_file}')
                content = FileManager.load_excel_data(content_file_path)
                content_json = DataProcessor.generate_content_result(content)
                FileManager.save_json_to_file(content_json, content_output_file)
        except Exception as e:
            logger.error(f'Files not found: {e}')

    @classmethod
    def query_vectors(cls, query_embedding, num_neighbours, db_cursor, logger):
        """
        Queries the database to find the nearest content IDs 
        based on vector similarity to the query_embedding.
        """
        try:
            vectors_query = (
                f"SELECT DISTINCT content_id "
                f"FROM ("
                f"    SELECT * "
                f"    FROM sales_doc_embedding "
                f"    ORDER BY vector_distance(embedding, '{query_embedding[0]}') ASC "
                f"    FETCH FIRST {num_neighbours} ROWS ONLY"
                f")"
            )
            db_cursor.execute(vectors_query)
            vectors_data = db_cursor.fetchall()
            content_ids = [v_id[0] for v_id in vectors_data]
        except Exception as e:
            logger.error(f'Error fetching Content IDs from Database: {e}')
            content_ids = []
        return content_ids

    @classmethod
    def get_content(cls, content_ids, db_cursor, logger):
        """
        Retrieves content text for the specified content IDs 
        from the database table 'sales_content'.
        """
        logger.info('Get Content Function Called')
        if not content_ids:
            return []
        try:
            content_query = ("SELECT content FROM sales_content WHERE content_id IN (" +
                             ",".join(map(str, content_ids)) + ")")
            db_cursor.execute(content_query)
            sales_content = db_cursor.fetchall()
        except Exception as e:
            logger.error(f'Error fetching Content from Database: {e}')
            sales_content = []

        final_texts = [(str(content[0].read()) if hasattr(content[0], 'read') else str(content[0])) for content in
                       sales_content]
        return final_texts


class SalesChatBot:

    @classmethod
    def sales_chatbot_prompt(cls, query, reference_data, logger):
        """
        Generates a chatbot prompt to get a response from the model.

        Constructs a detailed prompt outlining the required behavior of the chatbot 
        and passes it along with the reference data for model processing.
        """
        try:
            logger.info('Sales Chat Bot Prompt Function called')
            prompt = f"""
You are a helpful assistant trained to provide concise and accurate answers to the users. Don't provide the user query again in the answer.
Objective: Provide a relevant response to a user query using a list of reference texts. Aim for the highest possible accuracy and relevance.

Instructions:Understand the Query: Carefully analyze the user's question or statement to grasp the intended inquiry.

Search for Exact Matches: Scan the provided list of reference texts for an exact match to the user query. 

Use Semantic Similarity: If no exact match is found, employ semantic similarity techniques to identify the closest match within the reference texts.

Fallback Response Handling: If a close match is still not found, synthesize a response based on the reference data that addresses the user's query to the best extent possible.

If the data is still insufficient for a constructive response, then return only the error message: "Unable to fetch the response, please contact the support team.

Error Handling: Should the reference data be insufficient to construct a suitable response, return only the specified error message: "Right now, I am unable to provide you the best answer for your query, please contact the support team".

Maintain Factual Accuracy: Ensure all responses are factually correct and align with the information contained within the reference texts.

Clarity and Conciseness: Responses should be clear, concise, and straightforward, facilitating easy understanding.

Input Requirements:User Query: A string representing the user's question or statement.

{query}

Reference Data: A list of strings containing relevant background information.

{reference_data} 

Expected Output:A string representing the generated response, adhering to the above guidelines. Please provide only the relevant answer in a structured manner with proper headings if needed and do not specify the source of content.

Example:
User Query: "What is the capital of France?"

Reference Data:"Paris is the capital of France."
"The Eiffel Tower is in Paris."
"France is in Europe."Expected

Output: "Paris is the capital of France."

Additional Considerations:Contextual Understanding:

Leverage the context provided by the user query and the reference texts to enhance the relevance of the response.

Semantic Similarity: Apply semantic analysis to find closely related content when direct answers are not evident.
Error Management: Implement robust error handling strategies to address data gaps or ambiguous queries effectively.
            """
            return pr.get_prompt_response(prompt, logger)
        except Exception as e:
            logger.error(f'Error fetching response from prompt: {e}')
            return ''

    @classmethod
    def sales_chatbot_oracle(cls, user_query, conn, logger, num_neighbours=30):
        """
        Main function to process a user query and generate a response.

        Uses an embedding of the query to find related content from the database,
        retrieves the corresponding content, and generates a chatbot response.
        """
        try:
            query_embedding = get_embedding(user_query, logger)
            with conn.cursor() as db_cursor:
                # Retrieve content IDs using query embeddings
                content_ids = ContentRetriever.query_vectors(query_embedding, num_neighbours, db_cursor, logger)
                content_ids.sort()

                # Get the actual content matching the IDs
                final_content = ContentRetriever.get_content(content_ids, db_cursor, logger)

            # Generate chatbot response based on the retrieved content
            res = cls.sales_chatbot_prompt(user_query, final_content, logger)
        except Exception as e:
            logger.error(f'Failed to start bot. Error details: {e}')
            res = ''

        return res
