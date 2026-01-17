import os
import logging
import json
from pythonjsonlogger import jsonlogger

def setup_logging(name="telegram_mcp"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.ERROR)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)

    console_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")
    console_handler.setFormatter(console_formatter)

    # Create file handler
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # go up one level from backend/
    log_file_path = os.path.join(script_dir, "mcp_errors.log")

    try:
        file_handler = logging.FileHandler(log_file_path, mode="a")
        file_handler.setLevel(logging.ERROR)

        json_formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
        file_handler.setFormatter(json_formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    except Exception as log_error:
        print(f"WARNING: Error setting up log file: {log_error}")
        logger.addHandler(console_handler)
        logger.error(f"Failed to set up log file handler: {log_error}")

    return logger

logger = setup_logging()
