import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


class TextChunkProcessor:
    @classmethod
    def get_tokenizer(cls, logger):
        """
        Returns the cl100k_base tokenizer for token counting purposes.

        Args:
            logger (Logger): An initialized logger instance from LoggerManager.

        Returns:
            tiktoken.Encoding: A tiktoken tokenizer instance using cl100k_base.

        Raises:
            Exception: If the tokenizer fails to initialize.
        """
        try:
            tokenizer = tiktoken.get_encoding("cl100k_base")
            logger.info("Using cl100k_base tokenizer (local & free).")
            return tokenizer
        except Exception as e:
            logger.error(f"Failed to load cl100k_base tokenizer: {e}")
            raise Exception(f"Tokenizer not initialized. Error {e}")

    @classmethod
    def chunk_text(cls, text: str, chunk_size: int, chunk_overlap: int, tokenizer, logger) -> list[Document]:
        """
        Chunks the input text into documents based on token count.

        Args:
            text (str): The text content to chunk.
            chunk_size (int): The target number of tokens per chunk.
            chunk_overlap (int): The number of tokens to overlap between chunks.
            tokenizer (tiktoken.Encoding): The tokenizer instance to use for counting tokens.
            logger (Logger): An initialized logger instance from LoggerManager.

        Returns:
            list[Document]: A list of Langchain Document objects representing the chunks.

        Raises:
            ValueError: If chunk_overlap is greater than or equal to chunk_size, or if tokenizer is None.
        """
        if not text:
            logger.warning("Input text is empty. Returning empty list.")
            return []
        if chunk_overlap >= chunk_size:
            logger.error("Configuration error: chunk_overlap must be smaller than chunk_size.")
            raise ValueError("chunk_overlap must be smaller than chunk_size.")
        if tokenizer is None:
            logger.error("Configuration error: Tokenizer instance is required.")
            raise ValueError("Tokenizer instance is required.")

        def token_len_fn(segment: str) -> int:
            """
            Calculates token length using the provided tokenizer.

            Args:
                segment (str): The text segment to calculate token length for.

            Returns:
                int: The token length of the segment.
            """
            try:
                return len(tokenizer.encode(segment))
            except Exception as le:
                logger.error(f"Tokenizer error during length calculation: {le}")
                return 0

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=token_len_fn,
            add_start_index=True
        )

        try:
            docs = splitter.create_documents([text])
            logger.info(f"Created {len(docs)} document chunks.")
            return docs
        except Exception as e:
            logger.error(f"Error during chunking process: {e}", exc_info=True)
            return []
