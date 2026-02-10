"""
VIVOHOME AI - Gradio Application
Premium shopping assistant UI with multimodal input (text + image).
"""

import gradio as gr

from config import APP_NAME, APP_VERSION, SHARE_LINK
from tools import lookup_product, extract_model, describe_image
from query_parser import parse_query
from database import search_with_intent
from logger import app_logger

# Lazy RAG import — gracefully degrade if optional deps are missing
try:
    from rag_engine import rag_engine
    _RAG_AVAILABLE = True
    app_logger.info("RAG Engine loaded successfully")
except ImportError as exc:
    _RAG_AVAILABLE = False
    app_logger.warning("RAG Engine not available: %s", exc)

app_logger.info("Starting %s v%s", APP_NAME, APP_VERSION)


# ---------------------------------------------------------------------------
# Chat handler
# ---------------------------------------------------------------------------

def chat_with_agent(message, history):
    """Process a user message (text and/or image) and return a response."""
    user_text = message.get("text", "") if isinstance(message, dict) else str(message)
    user_files = message.get("files", []) if isinstance(message, dict) else []

    app_logger.info("User query: %s", user_text[:100])

    image_path = None
    if user_files:
        image_path = user_files[0] if isinstance(user_files[0], str) else user_files[0].name
        app_logger.info("Image uploaded: %s", image_path)

    try:
        if image_path:
            return _handle_image(image_path)
        return _handle_text(user_text)
    except Exception as exc:
        app_logger.error("Error: %s", exc, exc_info=True)
        return f"❌ Lỗi: {exc}\n\nĐảm bảo vLLM Server đang chạy!"


def _handle_image(image_path: str) -> str:
    """Process an image input: extract model → lookup product."""
    model_result = extract_model(image_path)

    if model_result.get("found"):
        model_code = model_result["model"]
        app_logger.info("Extracted model: %s", model_code)

        product = lookup_product(model_code)
        if product.get("found"):
            app_logger.info("Product found: %s", product["ten_san_pham"])
            return (
                f"📦 **Thông tin sản phẩm từ ảnh:**\n"
                f"- Tên: {product['ten_san_pham']}\n"
                f"- Model: {product['model']}\n"
                f"- Giá: **{product['gia']:,} VND**\n"
                f"- Nhóm: {product['nhom_hang']}\n\n"
                f"_Trích xuất từ ảnh: Model {model_code}_"
            )
        app_logger.warning("Model not in DB: %s", model_code)
        return f"Đã trích xuất Model: **{model_code}**, nhưng không tìm thấy trong hệ thống VIVOHOME."

    # Fallback: describe the image
    app_logger.warning("Cannot extract model from image")
    desc = describe_image(image_path)
    if desc.get("success"):
        return f"📷 {desc['description']}\n\n_Không tìm thấy mã Model trên ảnh để tra giá._"
    return "Không thể đọc được thông tin từ ảnh."


def _handle_text(user_text: str) -> str:
    """Process a text-only query through RAG or basic search."""
    if _RAG_AVAILABLE:
        app_logger.info("RAG search: %s", user_text[:60])
        return rag_engine.process(user_text)

    # Basic fallback
    intent = parse_query(user_text)
    result = search_with_intent(user_text, intent, max_results=3)
    if result.get("found"):
        lines = ["📦 **Sản phẩm tìm được:**"]
        for p in result["products"]:
            lines.append(f"- {p['ten']} ({p['model']}): **{p['gia']:,} VND**")
        return "\n".join(lines)
    return "Xin lỗi, không tìm thấy sản phẩm."


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
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
}
"""


def _build_ui() -> gr.Blocks:
    """Build the Gradio Blocks interface."""
    with gr.Blocks(
        theme=gr.themes.Soft(
            primary_hue="purple",
            secondary_hue="blue",
            neutral_hue="slate",
            font=gr.themes.GoogleFont("Inter"),
        ),
        css=CUSTOM_CSS,
        title=f"{APP_NAME} v{APP_VERSION}",
    ) as demo:
        gr.Markdown(f"# 🏢 {APP_NAME}\n### Trợ lý mua sắm thông minh với Vision AI")
        gr.Markdown(
            '<div style="text-align:center;color:#555;">'
            "🧠 <b>Intent Detection</b> • 🔍 <b>Semantic Search</b> • "
            "📷 <b>Vision-RAG</b> • 🌐 <b>Web Fallback</b>"
            "</div>"
        )

        chatbot = gr.Chatbot(
            label="💬 Chat",
            height=500,
            show_label=False,
            elem_id="chatbot",
        )

        with gr.Row():
            with gr.Column(scale=4):
                msg = gr.MultimodalTextbox(
                    placeholder="💬 Hỏi về sản phẩm hoặc 📷 upload ảnh tem nhãn...",
                    file_types=["image"],
                    show_label=False,
                    submit_btn="Gửi",
                    stop_btn="Dừng",
                )
            with gr.Column(scale=1):
                clear = gr.Button("🗑️ Xóa lịch sử", variant="secondary")

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
                    label="🎯 Intent Detection",
                )
            with gr.Column():
                gr.Examples(
                    examples=[
                        {"text": "Máy lọc nước Hòa Phát", "files": []},
                        {"text": "Bình tắm Rossi 15 lít", "files": []},
                        {"text": "có những loại tivi nào", "files": []},
                    ],
                    inputs=msg,
                    label="🔍 Smart Search",
                )

        gr.Markdown(
            "---\n"
            f"<div style='text-align:center;color:#888;font-size:0.9em;'>"
            f"⚡ <b>{APP_NAME}</b> v{APP_VERSION} — "
            f"Powered by Qwen2-VL • ChromaDB • Tavily • Gradio</div>"
        )

        def respond(message, chat_history):
            bot_response = chat_with_agent(message, chat_history)
            user_msg = message.get("text", "") if isinstance(message, dict) else str(message)
            if isinstance(message, dict) and message.get("files"):
                user_msg += " [📷 Image]"
            chat_history.append({"role": "user", "content": user_msg})
            chat_history.append({"role": "assistant", "content": bot_response})
            return "", chat_history

        msg.submit(respond, [msg, chatbot], [msg, chatbot])
        clear.click(lambda: [], None, chatbot, queue=False)

    return demo


demo = _build_ui()

if __name__ == "__main__":
    print("=" * 50)
    print(f"🚀 {APP_NAME} v{APP_VERSION}")
    print("=" * 50)
    demo.launch(share=SHARE_LINK)