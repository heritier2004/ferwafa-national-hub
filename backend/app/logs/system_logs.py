import logging
import os
from datetime import datetime

# Ensure logs directory exists
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "system.log")),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("FERWAFA_INTEL")

def log_system_event(event_type: str, message: str):
    logger.info(f"[{event_type.upper()}] {message}")

def log_error(module: str, error_msg: str):
    logger.error(f"[{module.upper()}] {error_msg}")
