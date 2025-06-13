import json
import pandas as pd


class ContentManager:
    """Handles operations related to content storage and processing."""

    @classmethod
    def store_content(cls, content, db_cursor, logger):
        """
        Parses and stores content into the database.

        :param content: A JSON string containing content data with structure:
                        {'result': [{content_id, content, about}, ...]}
        :param db_cursor: A database cursor object used to execute SQL queries.
        :param logger: A logger object used to log information and errors.

        The function inserts each content item into the `sales_content` database table.
        Logs errors if any issues occur during insertion.
        """
        logger.info("Storing content in database...")
        content = json.loads(content)  # Parse JSON string
        content_list = content.get('result', [])

        for each_content in content_list:
            try:
                content_insert_query = (
                    "INSERT INTO sales_content(CONTENT_ID, CONTENT_TITLE, CONTENT, CREATED_DATE) "
                    "VALUES(:content_id, :content_title, :content, SYSTIMESTAMP)"
                )
                db_cursor.execute(
                    content_insert_query,
                    {
                        'content_id': each_content['content_id'],
                        'content_title': each_content['about'].strip(),
                        'content': each_content['content'].strip()
                    }
                )
                db_cursor.connection.commit()
            except Exception as e:
                logger.error(f"Error while storing content: {e}")

    @classmethod
    def convert_excel_to_json(cls, file_path):
        """
        Converts the first sheet of an Excel file to JSON format.
        :param file_path: Path to the Excel file
        :return: JSON data as a string
        """
        df = pd.read_excel(file_path, sheet_name=0, engine='openpyxl')  # Read first sheet
        json_data = df.to_json(orient='records')  # Convert to JSON format
        return json_data
