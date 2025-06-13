from base64 import b64encode
import json
import requests

from chatPackages.dataValidation import DataSanitizer as ds


class GoogleVisionOCR:
    ENDPOINT_URL = 'https://vision.googleapis.com/v1/images:annotate'

    @classmethod
    def add_missing_coordinates(cls, json_data):
        """
        Ensures that all bounding box coordinates have 'x' and 'y' values.
        If missing, assigns them a default value of 0.
        """
        for item in json_data.get("textAnnotations", []):
            for vertex in item["boundingPoly"]["vertices"]:
                vertex.setdefault("x", 0)
                vertex.setdefault("y", 0)
        return json_data

    @classmethod
    def make_image_data_list(cls, image_file, b64_flg, logger):
        """
        Prepares the image data request payload for Google Vision API.
        """
        img_requests = []
        try:
            ctxt = image_file if b64_flg else b64encode(image_file).decode()
            img_requests.append({
                'image': {'content': ctxt},
                'features': [{'type': 'TEXT_DETECTION', 'maxResults': 1}]
            })
        except Exception as e:
            logger.error(f'Error while preparing image data: {str(e)}')
        return img_requests

    @classmethod
    def make_image_data(cls, image_file, b64_flg, logger):
        """
        Converts the image request data into JSON format.
        """
        img_dict = cls.make_image_data_list(image_file, b64_flg, logger)
        return json.dumps({"requests": img_dict}).encode()

    @classmethod
    def sort_json(cls, raw_json_data, sort_type, logger):
        """
        Sorts the extracted text data based on x or y coordinates.
        """
        key_func = lambda x: (
        x['boundingPoly']['vertices'][0]['y'], x['boundingPoly']['vertices'][0]['x']) if sort_type == 'y' else \
            (x['boundingPoly']['vertices'][0]['x'], x['boundingPoly']['vertices'][0]['y'])
        return sorted(raw_json_data, key=key_func)

    @classmethod
    def json_str(cls, sorted_json_data, logger, res_str=''):
        """
        Converts sorted JSON data into a structured text string.
        """
        if len(sorted_json_data) == 0:
            return res_str.strip(',')

        nxt_row = []
        translation_table = str.maketrans({"\"": "\\\""})
        row_str = '"'
        row_data = cls.sort_json(sorted_json_data, 'x', logger)

        prev_y, prev_x = max(v['y'] for v in row_data[0]['boundingPoly']['vertices']), max(
            v['x'] for v in row_data[0]['boundingPoly']['vertices'])

        for wrd in row_data:
            wrd_y, wrd_x = min(v['y'] for v in wrd['boundingPoly']['vertices']), min(
                v['x'] for v in wrd['boundingPoly']['vertices'])

            if prev_y <= wrd_y:
                nxt_row.append(wrd)
            else:
                row_str += f' {ds.encode_special_chars(wrd["description"].translate(translation_table), logger)}'
                prev_x, prev_y = max(v['x'] for v in wrd['boundingPoly']['vertices']), max(
                    v['y'] for v in wrd['boundingPoly']['vertices'])

        return cls.json_str(nxt_row, logger, res_str + row_str + '",').strip(',')

    @classmethod
    def split_rows(cls, sorted_json_data, data_end_str, logger):
        """
        Splits JSON data into rows based on y-coordinate similarity.
        """
        min_y = min(v['y'] for v in sorted_json_data[0]['boundingPoly']['vertices'])
        max_y = max(v['y'] for v in sorted_json_data[0]['boundingPoly']['vertices'])
        img_str, row_list = '', []

        for annotation in sorted_json_data:
            wrd_y = annotation['boundingPoly']['vertices'][0]['y']
            if min_y <= wrd_y <= max_y:
                row_list.append(annotation)
            else:
                min_y, max_y = min(v['y'] for v in annotation['boundingPoly']['vertices']), max(
                    v['y'] for v in annotation['boundingPoly']['vertices'])
                if row_list:
                    row_str = cls.json_str(row_list, logger)
                    img_str += row_str + ','
                    row_list = []
                    if data_end_str and data_end_str in img_str:
                        return img_str.strip(',')

        return img_str + cls.json_str(row_list, logger).strip(',')

    @classmethod
    def request_ocr(cls, api_key, img, b64_flg, logger):
        """
        Sends an OCR request to Google Vision API.
        """
        try:
            response = requests.post(
                cls.ENDPOINT_URL,
                data=cls.make_image_data(img, b64_flg, logger),
                params={'key': api_key},
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f'OCR API request failed: {str(e)}')
            return None

    @classmethod
    def get_string(cls, img_file, b64_flg, conn, logger, data_end_str=None, i=1):
        """
        Processes an image to extract text using OCR and formats the output.
        """
        try:
            ocr_api_key = 'AIzaSyDBA0kvXlacuu90iGCKgZQl2rawkQqAM78'
            if not ocr_api_key or not img_file:
                logger.error('Missing OCR API key or image file.')
                return i, ''

            response = cls.request_ocr(ocr_api_key, img_file, b64_flg, logger)
            if response and response.status_code == 200 and not response.json().get('error'):
                img_json_response = cls.add_missing_coordinates(response.json()['responses'][0])
                sorted_json = cls.sort_json(img_json_response['textAnnotations'][1:], 'y', logger)
                final_str = cls.split_rows(sorted_json, data_end_str, logger).strip(',')
                return i, '{' + f'"response": [{final_str}]' + '}'
            else:
                logger.error('Invalid OCR API response.')
                return i, ''
        except Exception as e:
            logger.error(f'Error extracting text from image: {str(e)}')
            return i, ''

    @classmethod
    def get_img_string(cls, img_file_path, conn, logger, data_end_str=None):
        """
        Reads an image from file and extracts text.
        """
        with open(img_file_path, 'rb') as f:
            img = f.read()
            _, result = cls.get_string(img, False, conn, logger, data_end_str=data_end_str)
        return result


if __name__ == "__main__":
    from loggerConfig import LoggerManager as lg

    l_logger = lg.configure_logger('../logs/imgStringExtract')

    # Example image file path (Replace with actual image file path)
    image_path = "C:/Users/SatishKumarKolamudi/Downloads/Screenshot_2.png"

    # Example usage
    extracted_text = GoogleVisionOCR.get_img_string(image_path, None, l_logger)

    print(f"Extracted Text: {extracted_text}")

    lg.shutdown_logger(l_logger)
