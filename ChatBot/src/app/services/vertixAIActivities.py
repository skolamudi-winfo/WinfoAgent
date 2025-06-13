import vertexai
from google.oauth2 import service_account
import json
import time
from google import genai
from google.genai.types import Tool, GenerateContentConfig, GoogleSearch
from vertexai.generative_models import GenerativeModel, SafetySetting
import os


class MimeTypes:
    """"""
    @classmethod
    def get_mime_type(cls, file_path):
        """Determines the MIME type based on the file extension."""
        _, file_extension = os.path.splitext(file_path)
        file_extension = file_extension.lower()

        mime_types = {
            ".pdf": "application/pdf",
            ".txt": "text/plain",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xls": "application/vnd.ms-excel",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".ppt": "application/vnd.ms-powerpoint",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".csv": "text/csv",
            ".html": "text/html",
            ".htm": "text/html",
            ".json": "application/json",
            ".xml": "application/xml",
            ".zip": "application/zip",
        }

        return mime_types.get(file_extension, "application/octet-stream")


class VertexAIService:
    def __init__(self, logger, model_name="gemini-1.5-flash-002", location="us-central1"):
        self.logger = logger
        self.model_name = model_name
        self.location = location

    @classmethod
    def _authenticate_model(
            cls,
            logger,
            model_name="gemini-1.5-flash-002",
            location="us-central1",
            google_key_config_path="configuration/Google_Key(WinfoBots).json",
            system_instruction="You are a helpful assistant.",
            response_schema=None
    ):
        logger.info(f"Authenticating using Service Account")
        try:
            with open(google_key_config_path) as c:
                credentials_info = json.load(c)

            safety_settings = [
                SafetySetting(
                    category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=SafetySetting.HarmBlockThreshold.OFF
                ),
                SafetySetting(
                    category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=SafetySetting.HarmBlockThreshold.OFF
                ),
                SafetySetting(
                    category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=SafetySetting.HarmBlockThreshold.OFF
                ),
                SafetySetting(
                    category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=SafetySetting.HarmBlockThreshold.OFF
                ),
            ]

            if response_schema:
                generation_config = {
                    "max_output_tokens": 8192,
                    "temperature": 1,
                    "top_p": 0.95,
                    "response_mime_type": "application/json",
                    "response_schema": response_schema,
                }
            else:
                generation_config = {
                    "max_output_tokens": 8192,
                    "temperature": 1,
                    "top_p": 0.95,
                    "response_mime_type": "text/plain"
                }

            # print(f"Response Schema: {generation_config}")

            credentials = service_account.Credentials.from_service_account_info(credentials_info)
            project_id = credentials_info["project_id"]
            vertexai.init(project=project_id, location=location, credentials=credentials)
            model = GenerativeModel(
                model_name=model_name,
                system_instruction=system_instruction,
                generation_config=generation_config,
                safety_settings=safety_settings
                # ,stream=True
            )
            logger.info("Model authenticated successfully..")
            return model
        except Exception as e:
            logger.error(f'Error while Authenticating using Service Account - {e}')
            return None

    @classmethod
    def _retry_with_backoff(cls, func, logger, retries=3, initial_delay=10):
        for attempt in range(1, retries+1):
            try:
                return func()
            except Exception as l_e:
                logger.warning(f'Attempt {attempt}/{retries} failed.', exc_info=True)
                if attempt == retries:
                    raise l_e
                delay = initial_delay * attempt
                logger.warning(f'Retrying after {delay:.1f} seconds...', exc_info=True)
                time.sleep(delay)
                return None
        return None

    @classmethod
    def get_prompt_response(cls, prompt, logger, model_name='gemini-2.0-flash', location='us-central1',
                            response_schema=None, google_search=False, api_key=None,
                            google_key_config_path='../configuration/Google_Key(WinfoBots).json',
                            system_instruction="You are a helpful assistant.", thinking=False):

        logger.info(f"get prompt response function called.")

        if google_search and model_name.__contains__('gemini-2.0') and api_key:
            try:
                client = genai.Client(http_options={'api_version': 'v1alpha'}, api_key=api_key) # type: ignore[attr-defined]
                google_search_tool = Tool(google_search=GoogleSearch())

                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=GenerateContentConfig(
                        tools=[google_search_tool],
                        response_modalities=["TEXT"],
                    ),
                )

                company_market_info = "".join(part.text for part in response.candidates[0].content.parts)
                return company_market_info
            except Exception as e:
                logger.error(f'Failed to get the prompt response from google search: {e}')
                logger.error(f"prompt: {prompt}")
                return ''
        # elif model_name.__contains__('2.5') and thinking:
        #     pass
            #generation_config=genai.GenerationConfig(
            #     thinking_budget_tokens=0 # Disables thinking
            # )
        else:
            try:
                model = cls._retry_with_backoff(
                    lambda: cls._authenticate_model(
                        logger, model_name=model_name,
                        location=location, google_key_config_path=google_key_config_path,
                        system_instruction=system_instruction, response_schema=response_schema),
                    logger)

                response = cls._retry_with_backoff(lambda: model.generate_content(prompt), logger)
                return response.text
            except Exception as e:
                logger.error(f'Failed to get the prompt response: {e}')
                logger.error(f"prompt: {prompt}")
                return ''


if __name__ == '__main__':
    from src.app.utils.loggerConfig import LoggerManager as lg
    # from vertexai.generative_models import Part

    l_logger = lg.configure_logger('../../../logs/prompts')
    # l_prompt = f"""what is winfobots?"""
    # print(f"prompt: {prompt} \n")
    # l_response_schema = {"type":"OBJECT","properties":{"text":{"type":"STRING","description":"The chatbot's text response."}},"required":["text"]}
    # print(VertexAIService.get_prompt_response(l_prompt, l_logger, model_name='gemini-2.0-flash-exp', google_search=False, response_schema=l_response_schema))
    # file_part = Part.from_uri(
    #     uri='gs://winfobots/SupportDocs/TestParser.pdf',
    #     mime_type='application/pdf',
    # )

    # l_prompt = """
    # analyze the provided attachment and extract the actual content from it. With proper headings when required.
    #         """
    # l_system_instruction = """
    # You are a very professional document analyzer specialist. Understand the documents provided and return the response based on the prompt asked by the user we might have images inside the pdf, analyze the images as well inside the pdf.
    #         """

    # contents = [file_part, l_prompt]
    l_config_file = '../../../configuration/Google_Key(WAI).json'
    with open(l_config_file) as l_config_data:
        service_account_details = json.load(l_config_data)

    l_api_key = service_account_details.get('api_key')
    contents = "what is winfobots?"
    file_content = VertexAIService.get_prompt_response(
        contents, l_logger, model_name='gemini-2.0-flash-001',
        google_key_config_path=l_config_file,
        api_key=l_api_key,
        google_search=True
    )

    print(file_content)

    lg.shutdown_logger(l_logger)
