import requests
import base64
import re
from typing import Optional, Dict, Any
from database import search_by_model, search_by_keywords

# --- CẤU HÌNH ---
VLLM_URL = "http://127.0.0.1:8000/v1/chat/completions"
VISION_MODEL = "Qwen/Qwen2-VL-7B-Instruct-AWQ"
REASONING_MODEL = "casperhansen/deepseek-r1-distill-llama-8b-awq"

def encode_image(image_path: str) -> str:
    """Mã hóa ảnh sang Base64"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def clean_response(text: str) -> str:
    """Loại bỏ <think>...</think>"""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

# === TOOL 1: TRA CỨU SẢN PHẨM THEO MODEL ===
def lookup_csv(model_code: str) -> Dict[str, Any]:
    """
    Tra cứu database theo mã Model.
    Returns: dict với thông tin sản phẩm hoặc thông báo không tìm thấy
    """
    if not model_code or len(model_code) < 2:
        return {"found": False, "message": "Mã model không hợp lệ"}
    
    result = search_by_model(model_code)
    
    if result.get("found"):
        return result
    
    return {"found": False, "message": f"Không tìm thấy sản phẩm với model '{model_code}'"}

# === TOOL 2: TÌM KIẾM SẢN PHẨM THEO TỪ KHÓA ===
def search_products(query: str, max_results: int = 3) -> Dict[str, Any]:
    """
    Tìm kiếm sản phẩm theo từ khóa.
    Returns: dict với danh sách sản phẩm tìm được
    """
    result = search_by_keywords(query, max_results)
    
    if result.get("found"):
        return result
    
    return {"found": False, "message": "Không tìm thấy sản phẩm phù hợp"}

# === TOOL 3: TRÍCH XUẤT MODEL TỪ ẢNH ===
def extract_model(image_path: str) -> Dict[str, Any]:
    """
    Dùng Vision AI trích xuất mã Model từ ảnh tem nhãn.
    Returns: dict với model code hoặc lỗi
    """
    try:
        base64_img = encode_image(image_path)
        
        payload = {
            "model": VISION_MODEL,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Đọc tem nhãn và trích xuất MÃ MODEL sản phẩm. CHỈ TRẢ LỜI MÃ MODEL (ví dụ: RT20HAR8DBU), không giải thích."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
                ]
            }],
            "temperature": 0.1,
            "max_tokens": 50
        }
        
        r = requests.post(VLLM_URL, json=payload, timeout=60)
        result = r.json()
        
        if 'choices' in result:
            model_text = result['choices'][0]['message']['content'].strip()
            model_text = model_text.split('\n')[0].strip()
            model_text = re.sub(r'[^\w\-]', '', model_text)
            if model_text:
                return {"found": True, "model": model_text}
        
        return {"found": False, "message": "Không thể trích xuất model từ ảnh"}
    except Exception as e:
        return {"found": False, "message": f"Lỗi Vision: {e}"}

# === TOOL 4: MÔ TẢ NỘI DUNG ẢNH ===
def describe_image(image_path: str) -> Dict[str, Any]:
    """
    Dùng Vision AI mô tả nội dung ảnh.
    Returns: dict với mô tả hoặc lỗi
    """
    try:
        base64_img = encode_image(image_path)
        
        payload = {
            "model": VISION_MODEL,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Mô tả ngắn gọn nội dung ảnh này (sản phẩm gì, thông số nếu có)."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
                ]
            }],
            "temperature": 0.2,
            "max_tokens": 200
        }
        
        r = requests.post(VLLM_URL, json=payload, timeout=60)
        result = r.json()
        
        if 'choices' in result:
            desc = clean_response(result['choices'][0]['message']['content'])
            return {"success": True, "description": desc}
        
        return {"success": False, "message": "Không thể mô tả ảnh"}
    except Exception as e:
        return {"success": False, "message": f"Lỗi: {e}"}

# === ĐỊNH NGHĨA TOOLS CHO AGENT ===
TOOL_DEFINITIONS = [
    {
        "name": "lookup_csv",
        "description": "Tra cứu thông tin và giá sản phẩm theo mã Model. Dùng khi đã biết chính xác mã Model.",
        "parameters": {"model_code": "Mã model sản phẩm (ví dụ: RT20HAR8DBU)"},
        "function": lookup_csv
    },
    {
        "name": "search_products",
        "description": "Tìm kiếm sản phẩm theo từ khóa. Dùng khi khách hỏi chung về loại sản phẩm.",
        "parameters": {"query": "Từ khóa tìm kiếm (ví dụ: 'tủ lạnh Samsung')"},
        "function": search_products
    },
    {
        "name": "extract_model",
        "description": "Trích xuất mã Model từ ảnh tem nhãn sản phẩm. Dùng KHI CÓ ẢNH.",
        "parameters": {"image_path": "Đường dẫn tới file ảnh"},
        "function": extract_model
    },
    {
        "name": "describe_image",
        "description": "Mô tả nội dung ảnh sản phẩm. Dùng khi cần hiểu ảnh nhưng không cần tra cứu giá.",
        "parameters": {"image_path": "Đường dẫn tới file ảnh"},
        "function": describe_image
    }
]

def get_tool_descriptions() -> str:
    """Tạo mô tả tools cho prompt"""
    lines = []
    for t in TOOL_DEFINITIONS:
        params = ", ".join(f"{k}: {v}" for k, v in t["parameters"].items())
        lines.append(f"- {t['name']}: {t['description']} | Params: {params}")
    return "\n".join(lines)

def execute_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """Thực thi tool theo tên"""
    for t in TOOL_DEFINITIONS:
        if t["name"] == tool_name:
            return t["function"](**kwargs)
    return {"error": f"Tool '{tool_name}' không tồn tại"}
