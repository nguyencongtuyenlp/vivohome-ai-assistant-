"""
VIVOHOME AI - Vision Tools
Functions for image analysis using vLLM + Qwen2-VL.
"""

import base64
import re
from typing import Dict, Any

import requests

from app_config import VLLM_URL, VISION_MODEL, VLLM_TIMEOUT
from database import search_by_model, search_by_keywords
from logger import get_logger

logger = get_logger("tools")


# ---------------------------------------------------------------------------
# Image utilities
# ---------------------------------------------------------------------------

def encode_image(image_path: str) -> str:
    """Encode an image file to a base64 string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _call_vision(prompt: str, image_path: str, *,
                 temperature: float = 0.1, max_tokens: int = 50) -> str:
    """Send a vision request to the vLLM server and return the text response."""
    b64 = encode_image(image_path)
    payload = {
        "model": VISION_MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            ],
        }],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    resp = requests.post(VLLM_URL, json=payload, timeout=VLLM_TIMEOUT)
    data = resp.json()
    if "choices" in data:
        return data["choices"][0]["message"]["content"].strip()
    raise RuntimeError(f"Unexpected vLLM response: {data}")


# ---------------------------------------------------------------------------
# Public tool functions
# ---------------------------------------------------------------------------

def lookup_product(model_code: str) -> Dict[str, Any]:
    """Look up a product in the database by model code."""
    if not model_code or len(model_code) < 2:
        return {"found": False, "message": "Mã model không hợp lệ"}
    result = search_by_model(model_code)
    if result.get("found"):
        return result
    return {"found": False, "message": f"Không tìm thấy model '{model_code}'"}


def search_products(query: str, max_results: int = 3) -> Dict[str, Any]:
    """Keyword search for products."""
    result = search_by_keywords(query, max_results)
    if result.get("found"):
        return result
    return {"found": False, "message": "Không tìm thấy sản phẩm phù hợp"}


def extract_model(image_path: str) -> Dict[str, Any]:
    """Extract a product model code from a label/sticker image."""
    try:
        prompt = (
            "Đọc tem nhãn và trích xuất MÃ MODEL sản phẩm. "
            "CHỈ TRẢ LỜI MÃ MODEL (ví dụ: RT20HAR8DBU), không giải thích."
        )
        raw = _call_vision(prompt, image_path)
        # Clean: take first line, remove non-alphanumeric
        model_text = re.sub(r"[^\w\-]", "", raw.split("\n")[0])
        if model_text:
            return {"found": True, "model": model_text}
        return {"found": False, "message": "Không thể trích xuất model từ ảnh"}
    except Exception as exc:
        logger.error("extract_model error: %s", exc)
        return {"found": False, "message": f"Lỗi Vision: {exc}"}


def describe_image(image_path: str) -> Dict[str, Any]:
    """Describe the contents of a product image."""
    try:
        prompt = "Mô tả ngắn gọn nội dung ảnh này (sản phẩm gì, thông số nếu có)."
        desc = _call_vision(prompt, image_path, temperature=0.2, max_tokens=200)
        # Strip <think>...</think> blocks if present
        desc = re.sub(r"<think>.*?</think>", "", desc, flags=re.DOTALL).strip()
        return {"success": True, "description": desc}
    except Exception as exc:
        logger.error("describe_image error: %s", exc)
        return {"success": False, "message": f"Lỗi: {exc}"}
