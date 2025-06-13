import re


class TextCleaner:
    @classmethod
    def clean_whitespace(cls, text: str) -> str:
        """
        Cleans whitespace in a block of text according to specific rules:
        - Removes leading/trailing whitespace from each logical line.
        - Collapses multiple spaces/tabs within lines to a single space.
        - Normalizes single line breaks within paragraphs to spaces.
        - Preserves paragraph breaks (represented by blank lines).

        Args:
            text (str): The input text to clean.

        Returns:
            str: The cleaned text with normalized whitespace.
        """
        cleaned_paragraphs = []
        current_paragraph_lines = []

        lines = text.splitlines()

        for raw_line in lines:
            line = raw_line.strip()
            line = re.sub(r'[ \t]+', ' ', line)

            if line:
                current_paragraph_lines.append(line)
            else:
                if current_paragraph_lines:
                    paragraph_text = ' '.join(current_paragraph_lines)
                    cleaned_paragraphs.append(paragraph_text)
                    current_paragraph_lines = []

        if current_paragraph_lines:
            paragraph_text = ' '.join(current_paragraph_lines)
            cleaned_paragraphs.append(paragraph_text)

        return '\n\n'.join(cleaned_paragraphs)

