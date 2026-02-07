"""
VIVOHOME AI - Gradio App with Direct Tools
Compatible với Gradio 4.x và 5.x
"""

import gradio as gr
from tools import lookup_csv, search_products, extract_model, describe_image
from logger import app_logger
from query_parser import parse_query
from database import search_with_intent

app_logger.info("🚀 VIVOHOME AI Starting...")

def chat_with_agent(message, history):
    """Xử lý tin nhắn - gọi tools trực tiếp"""
    # Parse message
    user_text = message.get("text", "") if isinstance(message, dict) else str(message)
    user_files = message.get("files", []) if isinstance(message, dict) else []
    
    # Log query
    app_logger.info(f"📥 User query: {user_text[:100]}")
    
    image_path = None
    if user_files:
        image_path = user_files[0] if isinstance(user_files[0], str) else user_files[0].name
        app_logger.info(f"📷 Image uploaded: {image_path}")
    
    try:
        # === TRƯỜNG HỢP 1: CÓ ẢNH ===
        if image_path:
            # Bước 1: Trích xuất Model
            model_result = extract_model(image_path)
            
            if model_result.get("found"):
                model_code = model_result["model"]
                app_logger.info(f"✅ Extracted model: {model_code}")
                
                # Bước 2: Tra cứu Database
                product = lookup_csv(model_code)
                
                if product.get("found"):
                    app_logger.info(f"✅ Product found: {product['ten_san_pham']}")
                    return f"""📦 **Thông tin sản phẩm từ ảnh:**
- Tên: {product['ten_san_pham']}
- Model: {product['model']}
- Giá: **{product['gia']:,} VND**
- Nhóm: {product['nhom_hang']}

_Trích xuất từ ảnh: Model {model_code}_"""
                else:
                    app_logger.warning(f"⚠️ Model not in DB: {model_code}")
                    return f"Đã trích xuất Model: {model_code}, nhưng không tìm thấy trong hệ thống VIVOHOME."
            else:
                app_logger.warning("⚠️ Cannot extract model from image")
                # Fallback: Mô tả ảnh
                desc_result = describe_image(image_path)
                if desc_result.get("success"):
                    return f"📷 {desc_result['description']}\n\n_Không tìm thấy mã Model trên ảnh để tra giá._"
                else:
                    return "Không thể đọc được thông tin từ ảnh."
        
        # === TRƯỜNG HỢP 2: CHỈ TEXT - FULL RAG SEARCH ===
        else:
            # Try RAG engine first
            try:
                from rag_engine import rag_engine
                
                # Full RAG search with semantic + web fallback
                app_logger.info(f"🧠 RAG Search: {user_text}")
                response = rag_engine.process(user_text)
                return response
                
            except ImportError as e:
                # Fallback to basic search if RAG not available
                app_logger.warning(f"⚠️ RAG Engine not available: {e}")
                
                intent = parse_query(user_text)
                search_result = search_with_intent(user_text, intent, max_results=3)
                
                if search_result.get("found"):
                    products = search_result["products"]
                    lines = ["📦 **Sản phẩm tìm được:**"]
                    for p in products:
                        lines.append(f"- {p['ten']} ({p['model']}): **{p['gia']:,} VND**")
                    return "\n".join(lines)
                else:
                    return "Xin lỗi, không tìm thấy sản phẩm."
    
    except Exception as e:
        app_logger.error(f"❌ Error: {str(e)}", exc_info=True)
        return f"❌ Lỗi: {str(e)}\n\nĐảm bảo vLLM Server đang chạy!"

# === GRADIO UI WITH CUSTOM THEME ===

# Custom CSS for modern look
custom_css = """
#chatbot {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 15px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.message-wrap {
    background: rgba(255, 255, 255, 0.95) !important;
    border-radius: 12px !important;
    padding: 12px !important;
    margin: 8px 0 !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05) !important;
}

.bot .message-wrap {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: white !important;
}

.user .message-wrap {
    background: #f8f9fa !important;
}

#component-0 {
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.contain {
    max-width: 1200px !important;
    margin: auto !important;
}

h1 {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800 !important;
    font-size: 2.5em !important;
    text-align: center !important;
    margin-bottom: 0.5em !important;
}

.description {
    text-align: center;
    font-size: 1.1em;
    color: #555;
    margin-bottom: 2em;
}

.example-container {
    background: white;
    border-radius: 12px;
    padding: 15px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    margin: 10px 0;
}

footer {
    text-align: center;
    margin-top: 2em;
    color: #888;
    font-size: 0.9em;
}
"""

# Create Gradio interface with custom theme
with gr.Blocks(
    theme=gr.themes.Soft(
        primary_hue="purple",
        secondary_hue="blue",
        neutral_hue="slate",
        font=gr.themes.GoogleFont("Inter"),
    ),
    css=custom_css,
    title="VIVOHOME AI - Smart Shopping Assistant"
) as demo:
    
    # Header
    gr.Markdown(
        """
        # 🏢 VIVOHOME AI Assistant
        ### Trợ lý mua sắm thông minh với Vision AI
        """
    )
    
    # Description with icons
    gr.Markdown(
        """
        <div class="description">
        <p>🧠 <b>Intent Detection</b> • 🔍 <b>Smart Search</b> • 📷 <b>Vision-RAG</b></p>
        <p style="color: #888; font-size: 0.95em;">Hỏi về giá sản phẩm bằng text hoặc upload ảnh tem nhãn</p>
        </div>
        """,
        elem_classes="description"
    )
    
    # Main chat interface
    chatbot = gr.Chatbot(
        label="💬 Chat",
        height=500,
        show_label=False,
        avatar_images=(
            None,  # User avatar
            "https://raw.githubusercontent.com/gradio-app/gradio/main/guides/assets/logo.png"  # Bot avatar
        ),
        elem_id="chatbot"
    )
    
    # Input area
    with gr.Row():
        with gr.Column(scale=4):
            msg = gr.MultimodalTextbox(
                placeholder="💬 Hỏi về sản phẩm hoặc 📷 upload ảnh tem nhãn...",
                file_types=["image"],
                show_label=False,
                submit_btn="Gửi",
                stop_btn="Dừng"
            )
        with gr.Column(scale=1):
            clear = gr.Button("🗑️ Xóa lịch sử", variant="secondary")
    
    # Examples section with better styling
    gr.Markdown("### 💡 Ví dụ câu hỏi:")
    
    with gr.Row():
        with gr.Column():
            gr.Examples(
                examples=[
                    {"text": "TV giá cao nhất", "files": []},
                    {"text": "Tủ lạnh rẻ nhất", "files": []},
                    {"text": "So sánh TV Samsung và LG", "files": []},
                ],
                inputs=msg,
                label="🎯 Intent Detection"
            )
        
        with gr.Column():
            gr.Examples(
                examples=[
                    {"text": "Máy lọc nước Hòa Phát", "files": []},
                    {"text": "Bình tắm Rossi 15 lít", "files": []},
                    {"text": "có những loại tivi nào", "files": []},
                ],
                inputs=msg,
                label="🔍 Smart Search"
            )
    
    # Footer
    gr.Markdown(
        """
        ---
        <footer>
        <p>⚡ Powered by <b>Qwen2-VL-7B</b> • <b>vLLM</b> • <b>SQLite</b> • <b>Gradio</b></p>
        <p style="font-size: 0.85em; color: #aaa;">Built with ❤️ for VIVOHOME Electronics</p>
        </footer>
        """
    )
    
    # Chat logic - Fixed for Gradio 6.0
    def respond(message, chat_history):
        """Handle chat messages with Gradio 6.0 format"""
        # Get bot response
        bot_response = chat_with_agent(message, chat_history)
        
        # Format message for display
        if isinstance(message, dict):
            # Multimodal message
            user_msg = message.get("text", "")
            if message.get("files"):
                user_msg += f" [📷 Image uploaded]"
        else:
            user_msg = str(message)
        
        # Append to history in correct format
        chat_history.append({"role": "user", "content": user_msg})
        chat_history.append({"role": "assistant", "content": bot_response})
        
        return "", chat_history
    
    msg.submit(respond, [msg, chatbot], [msg, chatbot])
    clear.click(lambda: [], None, chatbot, queue=False)

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 VIVOHOME AI Agent - Premium UI")
    print("=" * 50)
    demo.launch(share=True)