import os
import subprocess
import sys
import re
import requests
import pandas as pd

# 1. Tự động cài thư viện (giữ nguyên từ bản cũ)
def install_if_missing(package):
    try:
        __import__(package)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install_if_missing("requests")
install_if_missing("pandas")

# --- BIẾN TOÀN CỤC ĐỂ LƯU LỊCH SỬ ---
# Cấu trúc: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
conversation_history = []

# 2. Tìm sản phẩm liên quan (Giữ nguyên logic lọc từ khóa của Tuyền)
def search_relevant_products(user_question, max_results=5):
    try:
        df = pd.read_csv("product.csv", encoding='utf-8-sig')
        df.columns = df.columns.str.strip()
        
        question_lower = user_question.lower()
        keywords = question_lower.split()
        
        def match_score(row):
            searchable = " ".join([str(row.get('Tên sản phẩm', '')), str(row.get('Model', '')), str(row.get('Thông số chính', ''))]).lower()
            return sum(1 for kw in keywords if kw in searchable)
        
        df['score'] = df.apply(match_score, axis=1)
        df = df.sort_values('score', ascending=False).head(max_results)
        
        knowledge = ""
        for _, row in df.iterrows():
            knowledge += f"- {row['Tên sản phẩm']} ({row.get('Model', '')}): {row['Giá (VND)']} VND\n"
        return knowledge
    except:
        return "Không tìm thấy dữ liệu."

# 3. Làm sạch phản hồi (Xóa phần <think>)
def clean_response(response):
    cleaned = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
    return cleaned.strip()

# 4. Hàm gọi AI có tích hợp BỘ NHỚ
def ask_vivohome(user_question):
    global conversation_history
    
    # Lấy kiến thức mới nhất dựa trên câu hỏi
    knowledge_base = search_relevant_products(user_question)
    
    # Tạo System Prompt để định hướng AI
    system_prompt = f"Bạn là nhân viên VIVOHOME. Dữ liệu sản phẩm:\n{knowledge_base}\nTrả lời ngắn gọn."

    # Thêm câu hỏi hiện tại vào lịch sử
    conversation_history.append({"role": "user", "content": user_question})

    # Chỉ giữ lại 6 tin nhắn gần nhất (3 cặp hỏi-đáp) để không bị lỗi tràn Token (1024 limit)
    recent_history = conversation_history[-6:]

    payload = {
        "model": "casperhansen/deepseek-r1-distill-llama-8b-awq",
        "messages": [{"role": "system", "content": system_prompt}] + recent_history,
        "temperature": 0.1,
        "max_tokens": 512
    }
    
    url = "http://127.0.0.1:8000/v1/chat/completions"
    
    try:
        r = requests.post(url, json=payload, timeout=60)
        result = r.json()
        
        if 'choices' in result:
            ai_answer = result['choices'][0]['message']['content']
            ai_answer_cleaned = clean_response(ai_answer)
            
            # LƯU CÂU TRẢ LỜI CỦA AI VÀO BỘ NHỚ
            conversation_history.append({"role": "assistant", "content": ai_answer_cleaned})
            
            return ai_answer_cleaned
        else:
            return "❌ Lỗi: Server không trả về nội dung."
    except Exception as e:
        return f"❌ Lỗi kết nối: {e}"

# 5. Vòng lặp Chat thực tế
if __name__ == "__main__":
    print("\n" + "="*50)
    print("🤖 AI VIVOHOME ĐÃ CÓ BỘ NHỚ - GÕ 'exit' ĐỂ THOÁT")
    print("="*50)
    
    while True:
        user_input = input("\n👤 Bạn: ")
        if user_input.lower() in ['exit', 'quit', 'thoát']:
            break
            
        answer = ask_vivohome(user_input)
        print(f"💬 AI: {answer}")