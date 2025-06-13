import json
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel
from google.oauth2 import service_account
import time

from src.app.services.gcsActivities import GCSManager as gcs


class VertexAIConnector:
    """Manages authentication and connection setup with Vertex AI."""

    _credentials = None
    _project_id = None
    _location = None

    @classmethod
    def initialize_vertex_ai(cls, google_key_config_path='configuration/Google_Key(WinfoBots).json',
                             location="europe-central2"):
        """Initialize Vertex AI once and reuse credentials."""
        if cls._credentials is None:
            with open(google_key_config_path, 'r') as c:
                google_key = json.load(c)

            cls._credentials = service_account.Credentials.from_service_account_info(google_key)
            cls._project_id = google_key["project_id"]
            cls._location = location

            aiplatform.init(credentials=cls._credentials, project=cls._project_id, location=location)

        return cls._credentials, cls._project_id, cls._location


class EmbeddingManager:
    """Handles text embedding operations using Vertex AI."""

    @classmethod
    def _retry_with_backoff(cls, func, logger, retries=3, initial_delay=10, max_delay=60):
        for attempt in range(1, retries + 1):
            try:
                return func()
            except Exception as l_e:
                logger.warning(f'Attempt {attempt}/{retries} failed.', exc_info=True)
                if attempt == retries:
                    raise l_e
                delay = min(initial_delay * (2 ** (attempt - 1)), max_delay)
                logger.warning(f'Retrying after {delay:.1f} seconds...', exc_info=True)
                time.sleep(delay)

    @classmethod
    def get_embedding(
            cls, input_data, logger, embedding_model='text-embedding-005', task='RETRIEVAL_DOCUMENT',
            dimensions=256, google_key_config_path='../configuration/Google_Key(WinfoBots).json', location='us-central1'
    ):
        """Generate embeddings for a given text."""
        credentials, project_id, location = VertexAIConnector.initialize_vertex_ai(
            google_key_config_path=google_key_config_path, location=location)
        aiplatform.init(credentials=credentials, project=project_id, location=location)

        try:
            embedding_input = TextEmbeddingInput(input_data.strip(), task)
            model = TextEmbeddingModel.from_pretrained(embedding_model)
            dimensionality = {'output_dimensionality': dimensions}

            def embedding_function():
                return model.get_embeddings([embedding_input], **dimensionality)[0].values

            embedding = cls._retry_with_backoff(embedding_function, logger)

        except Exception as e:
            logger.error(f'Exception while Creating Embedding for text : {e}', exc_info=True)
            embedding = []

        return embedding

    @classmethod
    def create_embeddings(
            cls, processed_data, logger, embedding_model_name='text-embedding-005', task='RETRIEVAL_DOCUMENT',
            dimensions=300, google_key_config_path='configuration/Google_Key(WinfoBots).json', location='us-central1'
    ):
        """Generate embeddings for multiple texts."""
        embeddings = []
        try:
            for each_line in processed_data:
                query_id = each_line['query_id']
                query = each_line['query']
                embedding = cls.get_embedding(
                    query,
                    logger,
                    embedding_model=embedding_model_name,
                    task=task,
                    dimensions=dimensions,
                    google_key_config_path=google_key_config_path,
                    location=location
                )
                embeddings.append({
                    'query_id': query_id,
                    'embedding': embedding
                })
        except Exception as e:
            logger.error(f'Exception while Creating Embedding for text : {e}')

        return embeddings


class IndexManager:
    """Handles operations related to Vertex AI Matching Engine indexes."""

    @classmethod
    def upsert_data(cls, embedding_file_path, index, logger):
        """Insert embeddings into the index."""
        try:
            logger.info(f'Upsert Data Function Called')
            with open(embedding_file_path) as embedding:
                datapoints = []
                for line in embedding:
                    item = json.loads(line)
                    datapoints.append(
                        {"datapoint_id": str(item["id"]), "feature_vector": item["embedding"]}
                    )

            # Insert datapoints into the index in batches
            for i in range(0, len(datapoints), 1000):
                index.upsert_datapoints(datapoints=datapoints[i: i + 1000])
        except Exception as e:
            logger.error(f'Exception in Upsert Data : {e}')

    @classmethod
    def create_index(
            cls, vs_index_id, display_name,  logger, dimensions=256, approximate_neighbors_count=150,
            index_update_method="STREAM_UPDATE", location="us-central1"
    ):
        """Create a new index in Vertex AI Matching Engine."""
        try:
            logger.info(f'Create Index Function Called')
            credentials, project_id, _ = gcs.get_gcs_client(logger)
            aiplatform.init(credentials=credentials, project=project_id, location=location)

            try:
                existing_index = aiplatform.MatchingEngineIndex(index_name=vs_index_id)
                return existing_index
            except Exception as e:
                logger.info(f"Index not found. Creating a new one. Error: {e}")

            index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
                display_name=display_name,
                dimensions=dimensions,
                approximate_neighbors_count=approximate_neighbors_count,
                index_update_method=index_update_method,
            )

            index_endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
                display_name=display_name, public_endpoint_enabled=True
            )
            index_endpoint.deploy_index(index=index, deployed_index_id=vs_index_id)

            return index
        except Exception as e:
            logger.error(f'Exception while Creating an Index : {e}')


class QueryManager:
    """Handles querying the index for relevant embeddings."""

    @classmethod
    def query_index(cls, query_text, embedding_path, logger, vs_index_project_id='1072587883685',
                    vs_index_location='us-central1', vs_index_endpoint='6032079119653535744',
                    deployed_index_id='wb_1733493202025', num_neighbors=40, dimensions=256,
                    google_key_config_path='configuration/Google_Key(WinfoBots).json',
                    location='us-central1'):
        """Perform a similarity search on the index."""
        logger.info(f'Query Index Function Called')
        final_texts = []
        try:
            credentials, project_id, _ = gcs.get_gcs_client(logger)
            aiplatform.init(credentials=credentials, project=project_id, location=location)

            query_embedding = EmbeddingManager.get_embedding(
                'text-embedding-005', query_text, logger, dimensions=dimensions,
                google_key_config_path=google_key_config_path, location=location
            )

            query_texts = {}
            query_answers = {}

            with open(embedding_path) as f:
                for line in f:
                    p = json.loads(line.strip())
                    q_id = p['id']
                    query_texts[q_id] = p["text"]
                    query_answers[q_id] = p["answer"]

            index_endpoint = aiplatform.MatchingEngineIndexEndpoint(
                index_endpoint_name=f'projects/{vs_index_project_id}/locations/{vs_index_location}/indexEndpoints/{vs_index_endpoint}'
            )

            resp = index_endpoint.find_neighbors(
                deployed_index_id=deployed_index_id,
                queries=[query_embedding],
                num_neighbors=num_neighbors
            )

            for neighbor in resp[0]:
                f_id = int(neighbor.id)
                final_texts.append({"question": query_texts[f_id], "answer": query_answers[f_id]})
        except Exception as e:
            logger.error(f'Exception while Query Index - {e}')

        return final_texts


if __name__ == '__main__':
    from loggerConfig import LoggerManager as lg

    l_logger = lg.configure_logger('../logs/embeddingActivities')

    print(EmbeddingManager.get_embedding(
        'what are the advantages of winfobots?',
        l_logger,
        embedding_model='text-embedding-005',
        google_key_config_path='../configuration/Google_Key(WAI).json',
        location='us-central1'
    ))

    lg.shutdown_logger(l_logger)
