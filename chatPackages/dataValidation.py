import re


class Utils:
    @staticmethod
    def clean_string(text):
        """Removes special characters except single quotes and spaces."""
        return re.sub(r"[^a-zA-Z0-9\s']", "", text)


class DataSanitizer:
    """Handles encoding and decoding of special characters in data."""

    ENCODING_MAP = {
        '"': "&quot;",
        "'": "&apos;",
        "\\": "&#92;"
    }

    DECODING_MAP = {v: k for k, v in ENCODING_MAP.items()}  # Reverse mapping for decoding

    @classmethod
    def encode_special_chars(cls, p_str, logger):
        """Encodes special characters in a given string."""
        encoded_string = p_str
        try:
            for char, encoded_char in cls.ENCODING_MAP.items():
                encoded_string = encoded_string.replace(char, encoded_char)
        except Exception as e:
            logger.error(f'Failed to encode string. Error details: {e}')
        return encoded_string

    @classmethod
    def decode_special_chars(cls, p_str, logger):
        """Decodes special characters in a given string."""
        decoded_string = str(p_str)
        try:
            for encoded_char, char in cls.DECODING_MAP.items():
                decoded_string = decoded_string.replace(encoded_char, char)
        except Exception as e:
            logger.error(f'Failed to decode string. Error details: {e}')
        return decoded_string


if __name__ == '__main__':
    from loggerConfig import LoggerManager as lg

    l_logger = lg.configure_logger('../logs/datavalidation')

    # Testing
    # test_string = 'abc"xyz\'test\\example'
    # encoded = DataSanitizer.encode_special_chars(test_string, logger)
    # decoded = DataSanitizer.decode_special_chars(encoded, logger)
    #
    # print(f"Original: {test_string}")
    # print(f"Encoded:  {encoded}")
    # print(f"Decoded:  {decoded}")
    txt = "How does WinfoBots free up human resources from repetitive tasks?"
    print(Utils.clean_string(txt).lower())

    lg.shutdown_logger(l_logger)
