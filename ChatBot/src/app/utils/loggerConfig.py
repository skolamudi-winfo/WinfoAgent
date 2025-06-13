"""
A module for configuring loggers.
"""

import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import os


class LoggerManager:
    """
    LoggerManager is a class for configuring and managing multiple loggers.
    """
    # Dictionary to hold logger instances
    loggers = {}

    @classmethod
    def configure_logger(cls, logger_path, include_time=True):
        """
        Configure a logger with the specified path.

        Parameters:
        logger_path (str): The path to the logger.

        Returns:
        logging.Logger: The configured logger instance.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S%f") if include_time else None
        log_directory = logger_path if logger_path.__contains__('logs') else f"{logger_path}_logs"
        logger_name = os.path.basename(logger_path)
        logger_name = f"{logger_name}_log_{timestamp}.log" if timestamp else f"{logger_name}_log.log"

        # Create the log directory if it doesn't exist
        os.makedirs(log_directory, exist_ok=True)

        # Define the log filename with a timestamp
        log_filename = os.path.join(log_directory, logger_name)

        # If the logger already exists, return it
        if logger_name in cls.loggers:
            return cls.loggers[logger_name][0]

        # Create and configure the logger
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)  # Set logging level to DEBUG
        logger.propagate = False  # Ensure logs don't propagate to root logger (console)

        # Create a file handler
        # file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler = RotatingFileHandler(log_filename, encoding='utf-8', maxBytes=5000 * 1024, backupCount=200)
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        file_handler.setFormatter(formatter)

        # Add the file handler to the logger
        logger.addHandler(file_handler)

        # Store the logger and its handler in the dictionary
        cls.loggers[logger_name] = (logger, file_handler)

        return logger

    @classmethod
    def get_logger(cls, logger_name):
        """
        Retrieve a logger instance by name from the dictionary.

        Parameters:
        logger_name (str): The name of the logger.

        Returns:
        logging.Logger: The logger instance, or None if not found.
        """
        logger_entry = cls.loggers.get(logger_name)
        return logger_entry[0] if logger_entry else None

    @classmethod
    def shutdown_logger(cls, logger):
        """
        Shutdown a logger by closing all handlers and removing it from the dictionary.

        Parameters:
        logger (logging.Logger): The logger instance to shut down.
        """
        # Find the logger in the dictionary
        logger_entry = next(
            (entry for entry in cls.loggers.values() if entry[0] == logger), None
        )

        if logger_entry:
            _, file_handler = logger_entry
            # Close the file handler and remove it from the logger
            file_handler.close()
            logger.removeHandler(file_handler)
            # Remove all other handlers (if any)
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
            # Remove logger from the dictionary
            cls.loggers = {
                k: v for k, v in cls.loggers.items() if v[0] != logger
            }
            # Clear the logger to free resources
            logger.handlers.clear()


if __name__ == '__main__':
    logger1 = LoggerManager.configure_logger('../logs/process_trigger1')
    logger2 = LoggerManager.configure_logger('../logs/process_trigger1', include_time=False)

    logger1.debug("This is a debug message for logger1.")
    logger2.info("This is an info message for logger2.")

    LoggerManager.shutdown_logger(logger1)
    LoggerManager.shutdown_logger(logger2)
