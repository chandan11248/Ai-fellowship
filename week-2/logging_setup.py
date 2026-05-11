import logging
import sys
from pathlib import Path


def setup_logging(log_file: str = "app.log"):
    log_path = Path(__file__).parent / log_file
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured. Log file: {log_path}")
    return logger


logger = setup_logging()