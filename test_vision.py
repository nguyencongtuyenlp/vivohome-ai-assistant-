import requests
import base64
import os

# 1. Hàm mã hóa ảnh sang Base64
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def ask_vision_ai(image_path, question):
    # Kiểm tra xem file ảnh có tồn tại không
    if not os.path.exists(image_path):
        return f"❌ Lỗi: Không tìm thấy file ảnh tại {image_path}"

    base64_image = encode_image(image_path)
    
    # Cấu trúc tin nhắn chuẩn cho Vision Model
    payload = {
        "model": "Qwen/Qwen2-VL-7B-Instruct-AWQ",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Bạn là chuyên gia điện máy VIVOHOME. Hãy nhìn ảnh và trả lời: {question}"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 512,
        "temperature": 0.2
    }

    url = "http://127.0.0.1:8000/v1/chat/completions"

    try:
        print(f"--- 📤 Đang gửi ảnh '{image_path}' lên AI... ---")
        response = requests.post(url, json=payload, timeout=90)
        result = response.json()
        
        if 'choices' in result:
            return result['choices'][0]['message']['content']
        else:
            return f"❌ Server trả về lỗi: {result}"
    except Exception as e:
        return f"❌ Lỗi kết nối: {e}"

if __name__ == "__main__":
    print("\n" + "="*50)
    print("📸 CHƯƠNG TRÌNH NHẬN DIỆN ẢNH VIVOHOME")
    print("="*50)
    
    # Tuyền hãy upload một tấm ảnh lên Lightning AI, đặt tên là 'test.jpg'
    # Sau đó hỏi câu hỏi liên quan đến ảnh đó
    image_to_test = "test.jpg" 
    user_q = "Trong ảnh này là sản phẩm gì, có lỗi gì không và hãy tra cứu model này?"
    
    answer = ask_vision_ai(image_to_test, user_q)
    print(f"\n💬 AI trả lời:\n{answer}")