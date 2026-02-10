"""
VIVOHOME AI - Centralized Configuration
All settings in one place. Override via environment variables.
"""

import os
from pathlib import Path

# === Paths ===
BASE_DIR = Path(__file__).parent
DB_PATH = str(BASE_DIR / "vivohome.db")
CSV_PATH = str(BASE_DIR / "product.csv")
CHROMA_PATH = str(BASE_DIR / "chroma_db")
LOG_DIR = str(BASE_DIR / "logs")

# === vLLM Server ===
VLLM_URL = os.getenv("VLLM_URL", "http://127.0.0.1:8000/v1/chat/completions")
VISION_MODEL = os.getenv("VISION_MODEL", "Qwen/Qwen2-VL-7B-Instruct-AWQ")

# === Tavily Web Search ===
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "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")
TAVILY_SEARCH_URL = "https://api.tavily.com/search"

# === RAG Settings ===
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.5"))
MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", "5"))
WEB_SEARCH_TIMEOUT = int(os.getenv("WEB_SEARCH_TIMEOUT", "10"))
VLLM_TIMEOUT = int(os.getenv("VLLM_TIMEOUT", "60"))

# === Embedding Model ===
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# === App Settings ===
APP_NAME = "VIVOHOME AI Assistant"
APP_VERSION = "2.0.0"
GRADIO_PORT = int(os.getenv("GRADIO_PORT", "7860"))
SHARE_LINK = os.getenv("SHARE_LINK", "true").lower() == "true"
