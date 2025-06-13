import json
from google.cloud import aiplatform
from google.oauth2 import service_account
from google.cloud import storage
import os


class GCSManager:
    """Handles Google Cloud Storage operations like upload, download, and file management."""
    @classmethod
    def parse_gcs_link(cls, gcs_link):
        """
        Parses a Google Cloud Storage (GCS) link and extracts the bucket name,
        blob name, and file name.

        Args:
            gcs_link: The GCS link (e.g., "gs://my-bucket/path/to/my-file.txt").

        Returns:
            A tuple containing (bucket_name, blob_name, file_name), or None if the link is invalid.
        """
        if not gcs_link.startswith("gs://"):
            return None  # Invalid GCS link

        try:
            parts = gcs_link[5:].split("/", 1)  # Remove "gs://" and split
            bucket_name = parts[0]
            blob_name = parts[1] if len(parts) > 1 else ""  # Handle cases where there's no blob name
            file_name = os.path.basename(blob_name) if blob_name else ""

            return bucket_name, blob_name, file_name

        except (ValueError, IndexError):
            return None, '', '' # Invalid GCS link

    @classmethod
    def get_gcs_client(cls, logger, google_key_path='configuration/Google_Key(WinfoBots).json'):
        """Returns a singleton instance of the Google Cloud Storage client."""
        try:
            logger.info('Initializing Google Cloud Storage client...')
            with open(google_key_path) as c:
                google_key = json.load(c)

            credentials = service_account.Credentials.from_service_account_info(google_key)
            project_id = google_key["project_id"]
            storage_client = storage.Client(project=project_id, credentials=credentials)
            return credentials, project_id, storage_client
        except Exception as e:
            logger.error(f'Error while creating Storage Client: {e}')
            return None, None, None


    @classmethod
    def upload_to_gcs(cls, bucket_name, source_file_path, destination_file_path, logger, google_key_path='configuration/Google_Key(WinfoBots).json'):
        """Uploads a file to Google Cloud Storage."""
        try:
            logger.info(f'Uploading {source_file_path} to GCS: {destination_file_path}')
            credentials, project_id, storage_client = cls.get_gcs_client(logger, google_key_path=google_key_path)
            if not storage_client:
                return False

            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(destination_file_path)
            blob.upload_from_filename(source_file_path)

            # Construct the GCS blob path
            gcs_path = f"gs://{bucket_name}/{destination_file_path}"
            logger.info(f'File uploaded to GCS: {gcs_path}')
            return gcs_path
        except Exception as e:
            logger.error(f'Error while uploading file to GCS: {e}')
            return None

    @classmethod
    def download_from_gcs(cls, bucket_name, source_file_path, destination_local_path, logger, google_key_path='../configuration/Google_key(WinfoBots).json'):
        """Downloads a file from Google Cloud Storage."""
        try:
            logger.info(f'Downloading {source_file_path} from GCS to {destination_local_path}')
            credentials, project_id, storage_client = cls.get_gcs_client(logger, google_key_path=google_key_path)
            if not storage_client:
                return None

            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(source_file_path)
            blob.download_to_filename(destination_local_path)
            logger.info(f'File downloaded successfully to {destination_local_path}')
            return destination_local_path
        except Exception as e:
            logger.error(f'Error while downloading file from GCS: {e}')
            return None

    @classmethod
    def get_file_content(cls, bucket_name, file_path, logger, google_key_path='../configuration/Google_key(WinfoBots).json'):
        """Retrieves file content from Google Cloud Storage."""
        try:
            with open(google_key_path, 'r') as config_file:
                gcs_config = json.load(config_file)

            logger.info(f'Fetching content from GCS file: {file_path}')
            credentials, project_id, storage_client = cls.get_gcs_client(logger, google_key_path=google_key_path)
            if not storage_client:
                return None

            aiplatform.init(credentials=credentials, project=project_id, location=gcs_config["location"])
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(file_path)

            file_content = blob.download_as_string()
            return file_content
        except Exception as e:
            logger.error(f'Error while retrieving file content from GCS: {file_path} - {e}')
            return None

    @classmethod
    def get_files_in_gcs(cls, bucket_name, folder_path, logger, google_key_path='../configuration/Google_key(WinfoBots).json'):
        """Lists all files in a specified GCS folder."""
        try:
            logger.info(f'Listing files in GCS bucket: {bucket_name}, folder: {folder_path}')
            credentials, project_id, storage_client = cls.get_gcs_client(logger, google_key_path=google_key_path)
            if not storage_client:
                return {"files": []}

            bucket = storage_client.bucket(bucket_name)
            blobs = bucket.list_blobs(prefix=folder_path)

            files = [
                {
                    "file_name": blob.name.split("/")[-1],
                    "file_path": f"gs://{bucket_name}/{blob.name}",
                    "file_type": blob.content_type,
                    "file_size": blob.size,
                    "blob_name": blob.name
                }
                for blob in blobs if blob.name.split("/")[-1]
            ]

            return {"files": files}
        except Exception as e:
            logger.error(f'Error listing files in GCS for bucket {bucket_name}: {e}')
            return {"files": []}

    @classmethod
    def delete_from_gcs(cls, bucket_name, gcs_file_path, logger, google_key_path='../configuration/Google_key(WinfoBots).json'):
        """Deletes a file from Google Cloud Storage."""
        try:
            logger.info(f'Deleting file from GCS: {gcs_file_path}')
            credentials, project_id, storage_client = cls.get_gcs_client(logger, google_key_path=google_key_path)
            if not storage_client:
                return False

            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(gcs_file_path)
            blob.delete()
            logger.info(f'File {gcs_file_path} deleted successfully from {bucket_name}')
            return True
        except Exception as e:
            logger.error(f'Error deleting file from GCS: {e}')
            return False


if __name__ == '__main__':
    from loggerConfig import LoggerManager as lg

    l_logger = lg.configure_logger('../logs/gcsActivities')

    local_file_path = '../DownloadedFiles/SupportDocs/PDD (Sales Order Creation - EBS)/Oracle Sales Order - AS IS.pdf'
    destination_gcs_path = 'WinfoBots/Oracle Sales Order - AS IS.pdf'

    print(GCSManager.upload_to_gcs('supportdocs', local_file_path, destination_gcs_path, l_logger, google_key_path='../configuration/Google_Key(WAI).json'))
    # print(GCSManager.get_files_in_gcs(l_bucket_name, 'SalesDocs', logger))
    # print(GCSManager.delete_from_gcs(l_bucket_name, 'SalesDocs/About WinfoBots1.pdf', logger))
    # print(GCSManager.download_from_gcs(l_bucket_name, 'SalesDocs/AP Period Close Process - PDD V1_part_1.pdf', '../DownloadedFiles/AP Period Close Process - PDD V1_part_1.pdf', l_logger))

    lg.shutdown_logger(l_logger)
