"""
VIVOHOME - Logging Configuration
Centralized logging cho toàn bộ hệ thống
"""

import logging
import os
from datetime import datetime

# Tạo thư mục logs nếu chưa có
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Tạo log file với timestamp
LOG_FILE = os.path.join(LOG_DIR, f"vivohome_{datetime.now().strftime('%Y%m%d')}.log")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()  # Cũng in ra console
    ]
)

# Tạo loggers cho từng module
def get_logger(name: str):
    """Lấy logger cho module"""
    return logging.getLogger(name)

# Export
app_logger = get_logger("app")
tools_logger = get_logger("tools")
db_logger = get_logger("database")
