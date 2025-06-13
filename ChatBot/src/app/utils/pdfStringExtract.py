from concurrent.futures import ThreadPoolExecutor
import fitz  # PyMuPDF
from pdf2image import convert_from_path
from io import BytesIO
from PIL import Image
import warnings
import json
import os
import pdfplumber  # For table extraction
import pandas as pd
import re
import mimetypes
from vertexai.generative_models import Part

from src.app.services.vertixAIActivities import VertexAIService
from src.app.utils.dataCleaning import TextCleaner as tc
from src.app.utils.dataChunk import TextChunkProcessor as tcp
from src.app.utils.imgStringExtract import GoogleVisionOCR as gv

Image.MAX_IMAGE_PIXELS = None  # Disable the limit entirely


class PDFUtils:

    @classmethod
    def pdf_page_count(cls, pdf_file_path):
        """Returns the total number of pages in the PDF."""
        pdf_document = fitz.open(pdf_file_path)
        total_pages = pdf_document.page_count
        pdf_document.close()
        return total_pages

    @classmethod
    def split_pdf(cls, pdf_file_path, file_name, logger, pdf_chuck_size=10, download_path='../DownloadedFiles'):
        """Splits a PDF file into smaller chunks with a given number of pages."""
        logger.info('split_pdf() called.')

        pdf_document = fitz.open(pdf_file_path)
        total_pages = pdf_document.page_count

        chunk_start = 0
        chunk_index = 1
        chunk_file_paths = []

        while chunk_start < total_pages:
            chunk_end = min(chunk_start + pdf_chuck_size, total_pages)

            # Create a new PDF
            new_pdf = fitz.open()

            # Add pages to the new PDF
            for page_num in range(chunk_start, chunk_end):
                new_pdf.insert_pdf(pdf_document, from_page=page_num, to_page=page_num)

            # Save the new PDF with the appropriate chunk name
            output_file_name = f"{download_path}/{file_name}_part_{chunk_index}.pdf"
            new_pdf.save(output_file_name)
            output_file_path = os.path.abspath(output_file_name)
            chunk_file_paths.append(output_file_path)

            chunk_start += pdf_chuck_size
            chunk_index += 1
            new_pdf.close()

        pdf_document.close()
        logger.info('PDF recreation completed.')

        return chunk_file_paths

    @classmethod
    def extract_text_and_tables_from_pdf(cls, pdf_path, logger):
        """Extracts text and tabular data from a PDF file."""
        extracted_content = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Extract plain text
                    text = page.extract_text()
                    if text:
                        extracted_content.append({"type": "text", "content": text.strip()})

                    # Extract tables
                    tables = page.extract_tables()
                    for table in tables:
                        df = pd.DataFrame(table)  # Convert table to DataFrame
                        table_text = df.to_markdown(index=False)  # Convert table to Markdown for formatting
                        extracted_content.append({"type": "table", "content": table_text})

            res_text = ''
            for each_item in extracted_content:
                if each_item['type'] == 'table':
                    continue
                res_text += each_item['content'] + '\n'

            return res_text

        except Exception as e:
            logger.error(f"Error extracting content from PDF: {e}")
            return ''


class PDFConversion:

    @classmethod
    def convert_pdf_to_images(cls, pdf_file, pdf_start, pdf_end, logger):
        """Converts specific pages of a PDF to images."""
        logger.info('convert_pdf_to_images function started.')
        images = []

        pdf_document = fitz.open(pdf_file)

        for page_number in range(pdf_start - 1, pdf_end):
            page = pdf_document[page_number]
            image = page.get_pixmap()

            # Convert the Pixmap to a PIL Image
            pil_image = Image.frombytes("RGB", (image.width, image.height), image.samples)

            # Save the PIL Image data to a BytesIO buffer
            image_buffer = BytesIO()
            pil_image.save(image_buffer, format="PNG")
            image_bytes = image_buffer.getvalue()
            images.append(image_bytes)

        pdf_document.close()
        return images

    @classmethod
    def convert_imgpdf_to_images(cls, pdf_path, pdf_start, pdf_end, logger, dpi=300):
        """Converts image-based PDFs to images using pdf2image."""
        logger.info('convert_imgpdf_to_images function started.')
        images = []
        pdf_images = None

        # Suppress the DecompressionBombWarning for large images
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', Image.DecompressionBombWarning)

            # Convert PDF to images using pdf2image
            try:
                pdf_images = convert_from_path(pdf_path, dpi=dpi, fmt='png', first_page=pdf_start, last_page=pdf_end,
                                               poppler_path='../poppler/usr/bin')
                if len(pdf_images) < 1:
                    logger.info('No page to convert into image(PNG) using pdf2image.')
                else:
                    logger.info('Converted pdf pages to images(PNG) using pdf2image.')
            except Exception as e:
                logger.error(f'Unable to convert pdf to image. Error details: {e}')

        for i, pil_image in enumerate(pdf_images):
            # Save the PIL Image data to a BytesIO buffer
            image_buffer = BytesIO()
            pil_image.save(image_buffer, format="PNG")
            image_bytes = image_buffer.getvalue()
            images.append(image_bytes)

        logger.info('Converted pdf images to bytes.')

        return images


class PDFProcessing:

    @classmethod
    def required_pages(cls, pdf_path, logger, pdf_end_str=None):
        """Determines the required page range for the PDF based on the presence of text or images."""
        logger.info('required_pages function started.')
        res_pages = 1
        img_flg = False

        with fitz.open(pdf_path) as doc:
            for page_number in range(doc.page_count):
                page = doc[page_number]

                text = page.get_text()
                images = page.get_images(full=True)

                if len(text.strip()) == 0 or images:
                    res_pages = doc.page_count
                    img_flg = True
                    break

                if pdf_end_str and pdf_end_str in text:
                    img_flg = False
                    res_pages = page_number + 1
                    break

        return img_flg, res_pages

    @classmethod
    def get_pdf_string(cls, file_path, logger, data_end_str=None, pages_range=None, img_flg=True):
        """Extracts text content from a PDF, processing images if necessary."""
        logger.info('get_pdf_string function started.')
        if pages_range:
            pdf_start, pdf_end = str(pages_range).split('-')
            pdf_start = int(pdf_start)
            pdf_end = int(pdf_end)
        else:
            pdf_start = 1
            img_flg, pdf_end = cls.required_pages(file_path, logger, data_end_str)

        pdf_str = ''

        if img_flg:
            pdf_images = PDFConversion.convert_imgpdf_to_images(file_path, pdf_start, pdf_end, logger)
        else:
            pdf_images = PDFConversion.convert_pdf_to_images(file_path, pdf_start, pdf_end, logger)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []

            for i, img in enumerate(pdf_images):
                future = executor.submit(gv.get_string, img, False, logger, data_end_str, i)
                futures.append(future)

            for future in futures:
                try:
                    thread_id, response_sequence = future.result(timeout=60)
                    try:
                        # print(f"response_sequence: {response_sequence}")
                        img_resp = json.loads(response_sequence)
                        img_str = str(json.dumps(img_resp['response'], ensure_ascii=False))
                        img_str = img_str[1:-1]

                        if data_end_str and data_end_str in img_str:
                            pdf_str = pdf_str + img_str + ','
                            break

                        pdf_str = pdf_str + img_str + ','

                    except json.JSONDecodeError as e:
                        logger.error(f'Failed to convert image string to json. Error details: {str(e)}')
                        logger.error(f'Problematic part of the string: {img_resp}')
                        continue

                except Exception as e:
                    logger.error(f'Failed to get thread result. Error details: {str(e)}')

        executor.shutdown(wait=True)

        return '{' + f'"response": [{pdf_str[:-1]}]' + '}'


class PDFProcessor:
    @classmethod
    def extract_pdf_content(cls, pdf_path, logger, model_name='gemini-2.0-flash-001',
                            location='us-central1', google_key_path='../configuration/Google_Key(WinfoBots).json'):
        """
        Extracts text content from a PDF file, including embedded markers for images.

        Args:
            pdf_path (str): Path to the PDF file.
            logger (Logger): Logger instance for logging messages.
            model_name (str): Name of the LLM model to use for processing.
            location (str): Location of the LLM service.
            google_key_path (str): Path to the Google API key configuration file.

        Returns:
            str: Extracted text content from the PDF.
        """
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            logger.error(f"Failed to open PDF {pdf_path}: {e}")
            return None

        page_count = doc.page_count
        logger.info(f"Processing '{os.path.basename(pdf_path)}' ({page_count} pages)")

        pdf_string = ''
        for page_num in range(page_count):
            try:
                page = doc[page_num]
                current_page_num = page_num + 1

                content = cls.extract_page_content(
                    page, current_page_num, logger, model_name=model_name,
                    location=location, google_key_path=google_key_path
                )
                pdf_string += content + '\n'
            except Exception as page_e:
                logger.error(f"Failed processing page {page_num + 1} of {os.path.basename(pdf_path)}: {page_e}", exc_info=True)
        doc.close()
        logger.info(f"Finished initial PDF processing for '{os.path.basename(pdf_path)}'.")

        return pdf_string

    @classmethod
    def extract_page_content(cls, page, page_num, logger, model_name='gemini-2.0-flash-001',
                             location='us-central1', google_key_path='../configuration/Google_Key(WinfoBots).json'):
        """
        Extracts content from a single page of a PDF, including text and image markers.

        Args:
            page (fitz.Page): The PDF page object.
            page_num (int): The current page number.
            logger (Logger): Logger instance for logging messages.
            model_name (str): Name of the LLM model to use for processing.
            location (str): Location of the LLM service.
            google_key_path (str): Path to the Google API key configuration file.

        Returns:
            str: Extracted content from the page.
        """
        logger.info("Extract page content function called.")
        output = ""
        image_count = 0

        page_dict = page.get_text("dict")
        blocks = page_dict.get("blocks", [])
        sorted_blocks = sorted(blocks, key=lambda b: b["bbox"][1])

        for block in sorted_blocks:
            block_type = block.get("type")

            if block_type == 0:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        output += span.get("text", "") + " "
                    output += "\n"

            elif block_type == 1:
                image_bytes = block.get("image")
                ext = block.get("ext")

                try:
                    image_count += 1
                    image_name = f"page_{page_num}_image_{image_count}.{ext}"
                    mime_type = mimetypes.guess_type(image_name)[0]
                    if not mime_type:
                        mime_type = 'application/octet-stream'

                    system_instruction = """
                    You are an AI image analysis expert. Describe the key elements and purpose of the provided image within the context of a document page.
                    """
                    description_prompt_text = """
                    Extract the actual content from the image using advanced OCR techniques and explain the content clearly.
                    """

                    image_part = Part.from_data(image_bytes, mime_type=mime_type)
                    llm_prompt_content = [image_part, description_prompt_text]

                    description = VertexAIService.get_prompt_response(
                        prompt=llm_prompt_content,
                        logger=logger,
                        model_name=model_name,
                        location=location,
                        google_key_config_path=google_key_path,
                        system_instruction=system_instruction,
                    )
                    description = description.strip()

                    output += f"[IMAGE DESCRIPTION: {description}]\n\n" if description else ''
                except Exception as e:
                    logger.error(f"Failed to extract/save image on page {page_num}: {e}", exc_info=True)
            else:
                logger.debug(f"Skipping unsupported block type {block_type}.")

        return output

    @classmethod
    def get_pdf_content(cls, pdf_path, logger, model_name='gemini-2.0-flash-001',
                        location='us-central1', google_key_path='../configuration/Google_Key(WinfoBots).json'):
        """
        Extracts and cleans the content of a PDF file.

        Args:
            pdf_path (str): Path to the PDF file.
            logger (Logger): Logger instance for logging messages.
            model_name (str): Name of the LLM model to use for processing.
            location (str): Location of the LLM service.
            google_key_path (str): Path to the Google API key configuration file.

        Returns:
            str: Cleaned content of the PDF.
        """
        logger.info("Get pdf content function called.")

        page_string = cls.extract_pdf_content(
            pdf_path, logger,
            model_name=model_name,
            location=location,
            google_key_path=google_key_path
        )
        cleaned_content = tc.clean_whitespace(page_string)

        return cleaned_content

    @classmethod
    def get_pdf_content_chunks(cls, pdf_path, logger, model_name='gemini-2.0-flash-001',
                               location='us-central1', google_key_path='../configuration/Google_Key(WinfoBots).json',
                               chunk_token_size=256, chunk_overlap_tokens=50):
        """
        Splits the cleaned content of a PDF into chunks for further processing.

        Args:
            pdf_path (str): Path to the PDF file.
            logger (Logger): Logger instance for logging messages.
            model_name (str): Name of the LLM model to use for processing.
            location (str): Location of the LLM service.
            google_key_path (str): Path to the Google API key configuration file.
            chunk_token_size (int): Maximum size of each chunk in tokens.
            chunk_overlap_tokens (int): Number of overlapping tokens between chunks.

        Returns:
            list: List of content chunks.
        """
        logger.info("Get pdf content chunks function called.")

        chunks = []
        cleaned_content = cls.get_pdf_content(
            pdf_path,
            logger,
            model_name=model_name,
            location=location,
            google_key_path=google_key_path
        )

        tokenizer = tcp.get_tokenizer(logger)
        print(f"cleaned_content: {cleaned_content}")
        documents = tcp.chunk_text(
            text=cleaned_content,
            chunk_size=chunk_token_size,
            chunk_overlap=chunk_overlap_tokens,
            tokenizer=tokenizer,
            logger=logger
        )

        for i, doc in enumerate(documents, 1):
            each_chunk = {
                "section_text": doc.page_content
            }
            chunks.append(each_chunk)

        return {"content": chunks}


class ImageProcessor:
    @classmethod
    def find_image_markers(cls, pdf_string, logger):
        """
        Finds unique image markers in the given PDF content string.

        Args:
            pdf_string (str): The content of the PDF as a string.
            logger (Logger): Logger instance for logging messages.

        Returns:
            list: List of dictionaries containing marker information and positions.
        """
        marker_regex = re.compile(r"(page_(\d+)_image_(\d+)_counter_(\d+))")
        markers_to_process = []
        try:
            for match in marker_regex.finditer(pdf_string):
                unique_marker_text = match.group(0)
                markers_to_process.append({'marker': unique_marker_text, 'pos': match.start()})
            markers_to_process = sorted(markers_to_process, key=lambda item: item['pos'])
            logger.info(f"Found {len(markers_to_process)} image markers.")
        except Exception as e:
            logger.error(f"Error finding unique markers in pdf_string: {e}", exc_info=True)
        return markers_to_process

    @classmethod
    def find_image_file(cls, marker, output_dir, logger):
        """
        Finds the corresponding image file for a given marker.

        Args:
            marker (str): The unique marker string for the image.
            output_dir (str): Directory where the images are stored.
            logger (Logger): Logger instance for logging messages.

        Returns:
            tuple: Path to the image file and its MIME type, or (None, None) if not found.
        """
        image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.webp']
        for ext in image_extensions:
            potential_path = os.path.join(output_dir, f"{marker}{ext}")
            if os.path.exists(potential_path):
                mime_type = mimetypes.guess_type(potential_path)[0]
                if not mime_type:
                    mime_type = 'application/octet-stream'
                return potential_path, mime_type
        logger.warning(f"No image file found for marker {marker}.")
        return None, None


class LLMProcessor:
    @classmethod
    def get_image_description(cls, image_path, mime_type, model_name, location, key_path, system_instruction, logger):
        """
        Calls the LLM to generate a description for the given image.

        Args:
            image_path (str): Path to the image file.
            mime_type (str): MIME type of the image.
            model_name (str): Name of the LLM model to use for processing.
            location (str): Location of the LLM service.
            key_path (str): Path to the Google API key configuration file.
            system_instruction (str): Instruction for the LLM system.
            logger (Logger): Logger instance for logging messages.

        Returns:
            str: Description of the image, or None if an error occurs.
        """
        description_prompt_text = "Describe this image concisely, focusing on its content relevant to a document."

        try:
            with open(image_path, "rb") as img_file:
                image_bytes = img_file.read()

            if not image_bytes:
                logger.warning(f"Image file {image_path} is empty. Skipping LLM call.")
                return None

            image_part = Part.from_data(image_bytes, mime_type=mime_type)
            llm_prompt_content = [image_part, description_prompt_text]

            description = VertexAIService.get_prompt_response(
                prompt=llm_prompt_content,
                logger=logger,
                model_name=model_name,
                location=location,
                google_key_config_path=key_path,
                system_instruction=system_instruction,
            )

            logger.info(f"Successfully received description for '{image_path}'.")
            return description.strip()

        except Exception as e:
            logger.error(f"Failed for {image_path} with error: {e}", exc_info=True)
            return None

    @classmethod
    def replace_marker_with_description(cls, pdf_string, markers, output_dir, model_name, location, key_path, system_instruction, logger):
        """
        Replaces image markers in the PDF content with descriptions generated by the LLM.

        Args:
            pdf_string (str): The content of the PDF as a string.
            markers (list): List of image markers to replace.
            output_dir (str): Directory where the images are stored.
            model_name (str): Name of the LLM model to use for processing.
            location (str): Location of the LLM service.
            key_path (str): Path to the Google API key configuration file.
            system_instruction (str): Instruction for the LLM system.
            logger (Logger): Logger instance for logging messages.

        Returns:
            str: Updated PDF content with image descriptions.
        """
        replacements_made = 0
        for marker_info in markers:
            marker = marker_info['marker']
            image_path, mime_type = ImageProcessor.find_image_file(marker, output_dir, logger)
            if image_path and mime_type:
                description = cls.get_image_description(image_path, mime_type, model_name, location, key_path, system_instruction, logger)
                replacement_text = f"[Image Description: {description}]" if description else f"[Image Description: Error]"
                pdf_string = pdf_string.replace(marker, replacement_text, 1)
                replacements_made += 1
            else:
                logger.warning(f"Skipping marker {marker} due to missing image file.")
        logger.info(f"Replaced {replacements_made} markers with descriptions.")
        return pdf_string


class Utility:
    @classmethod
    def cleanup_downloaded_images(cls, output_dir, logger):
        """
        Deletes all image files in the specified directory and removes the folder if empty.

        Args:
            output_dir (str): Directory containing the downloaded images.
            logger (Logger): Logger instance for logging messages.
        """
        try:
            images_deleted = True

            for root, _, files in os.walk(output_dir):
                for file in files:
                    if file.endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp')):
                        file_path = os.path.join(root, file)
                        try:
                            os.remove(file_path)
                        except Exception as e:
                            logger.error(f"Failed to delete image file: {file_path}. Error: {e}")
                            images_deleted = False

            if images_deleted:
                if not os.listdir(output_dir):
                    try:
                        os.rmdir(output_dir)
                        logger.info(f"Deleted folder: {output_dir}")
                    except Exception as e:
                        logger.error(f"Failed to delete folder: {output_dir}. Error: {e}")
                else:
                    logger.warning(f"Folder {output_dir} is not empty. Skipping folder deletion.")
            else:
                logger.warning(f"Some image files could not be deleted. Folder {output_dir} will not be removed.")

        except Exception as e:
            logger.error(f"Error during cleanup of downloaded images: {e}", exc_info=True)

    @classmethod
    def process_content_files_with_llm(cls, pdf_string, output_dir, model_name, location, key_path, system_instruction, logger):
        """
        Processes the PDF content by replacing image markers with LLM-generated descriptions.

        Args:
            pdf_string (str): The content of the PDF as a string.
            output_dir (str): Directory where the images are stored.
            model_name (str): Name of the LLM model to use for processing.
            location (str): Location of the LLM service.
            key_path (str): Path to the Google API key configuration file.
            system_instruction (str): Instruction for the LLM system.
            logger (Logger): Logger instance for logging messages.

        Returns:
            str: Updated PDF content with image descriptions.
        """
        markers = ImageProcessor.find_image_markers(pdf_string, logger)
        updated_string = LLMProcessor.replace_marker_with_description(pdf_string, markers, output_dir, model_name, location, key_path, system_instruction, logger)
        return updated_string


if __name__ == '__main__':
    from loggerConfig import LoggerManager as lg
    l_logger = lg.configure_logger('../logs/pdf_string_extract')
    # l_conn = ''

    # l_file = '../DownloadedFiles/AP Period Close Process - PDD V1_part_1.pdf'
    #
    # print(f'Final PDF string: {PDFProcessing.get_pdf_string(l_file, l_conn, l_logger)}')
    # print(f'Total pages: {PDFUtils.pdf_page_count(file)}')
    # print(f'Required pages: {PDFProcessing.required_pages(file, logger)}')
    # print(f'Split PDF: {PDFUtils.split_pdf(file, "test", logger)}')
    # print(f'Extract text and tables: {PDFUtils.extract_text_and_tables_from_pdf(file)}')

    l_google_key_path = r"../configuration/Google_Key(WinfoBots).json"
    l_pdf_path = r"../DownloadedFiles/SupportDocs/About WinfoBots1.pdf"
    l_model_name = "gemini-2.0-flash-001"
    l_location = "us-central1"

    pdf_content = PDFProcessor.get_pdf_content_chunks(
        l_pdf_path,
        l_logger,
        model_name=l_model_name,
        location=l_location,
        google_key_path=l_google_key_path,
        chunk_token_size=256,
        chunk_overlap_tokens=50
    )

    print(f"pdf_content: {pdf_content}")

    lg.shutdown_logger(l_logger)