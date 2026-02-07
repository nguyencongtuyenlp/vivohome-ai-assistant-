"""
VIVOHOME AI - Agent Core Module
ReAct Loop + State Management + Evaluator
"""

import requests
import re
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from tools import (
    VLLM_URL, REASONING_MODEL, VISION_MODEL,
    get_tool_descriptions, execute_tool, clean_response, encode_image
)

# === AGENT STATE ===
@dataclass
class AgentState:
    """Quản lý trạng thái của Agent trong một phiên làm việc"""
    messages: List[Dict] = field(default_factory=list)
    current_query: str = ""
    image_path: Optional[str] = None
    tool_calls: List[Dict] = field(default_factory=list)
    observations: List[str] = field(default_factory=list)
    final_answer: Optional[str] = None
    iteration: int = 0
    
    def estimate_tokens(self) -> int:
        """Ước tính số tokens (1 token ≈ 4 ký tự tiếng Việt)"""
        total_chars = sum(len(str(m.get('content', ''))) for m in self.messages)
        total_chars += len(self.current_query)
        total_chars += sum(len(str(obs)) for obs in self.observations)
        return total_chars // 4
    
    def prune_if_needed(self, max_tokens: int = 1800):
        """Cắt tỉa lịch sử nếu vượt quá token limit"""
        while self.estimate_tokens() > max_tokens and len(self.messages) > 2:
            # Giữ lại system prompt (index 0) và tin gần nhất
            self.messages.pop(1)
        
        # Cũng cắt observations nếu quá dài
        while len(self.observations) > 3:
            self.observations.pop(0)

# === REACT PROMPT TEMPLATE ===
REACT_SYSTEM_PROMPT = """Bạn là AI Agent của VIVOHOME. Hãy suy nghĩ từng bước và sử dụng công cụ khi cần thiết.

CÁC CÔNG CỤ CÓ SẴN:
{tool_descriptions}

QUY TRÌNH REACT:
1. Thought: Phân tích yêu cầu của khách
2. Action: Chọn một công cụ phù hợp (hoặc "FINISH" nếu đã đủ thông tin)
3. Action Input: Tham số cho công cụ (JSON format)

LƯU Ý:
- Nếu có ảnh, ưu tiên dùng extract_model trước để lấy mã Model
- Sau khi có Model, dùng lookup_csv để tra giá
- Nếu không có ảnh và khách hỏi chung, dùng search_products
- Khi đã đủ thông tin, Action = "FINISH" và đưa ra câu trả lời

FORMAT ĐẦU RA (BẮT BUỘC):
Thought: [suy nghĩ của bạn]
Action: [tên_công_cụ hoặc FINISH]
Action Input: {{"param": "value"}}
"""

def build_react_prompt(query: str, image_context: str = "", observations: List[str] = None) -> str:
    """Xây dựng prompt cho ReAct loop"""
    prompt = REACT_SYSTEM_PROMPT.format(tool_descriptions=get_tool_descriptions())
    prompt += f"\n\nCÂU HỎI CỦA KHÁCH: {query}"
    
    if image_context:
        prompt += f"\n\n[CÓ ẢNH ĐÍNH KÈM: {image_context}]"
    
    if observations:
        prompt += "\n\nKẾT QUẢ TỪ CÁC CÔNG CỤ ĐÃ DÙNG:"
        for i, obs in enumerate(observations, 1):
            prompt += f"\n{i}. {obs}"
    
    prompt += "\n\nBắt đầu suy nghĩ:"
    return prompt

# === PARSE REACT OUTPUT ===
def parse_react_output(text: str) -> Dict[str, Any]:
    """Parse output của LLM theo format ReAct"""
    result = {"thought": "", "action": "", "action_input": {}}
    
    # Clean response first
    text = clean_response(text)
    
    # Extract Thought
    thought_match = re.search(r'Thought:\s*(.+?)(?=Action:|$)', text, re.DOTALL | re.IGNORECASE)
    if thought_match:
        result["thought"] = thought_match.group(1).strip()
    
    # Extract Action
    action_match = re.search(r'Action:\s*(\w+)', text, re.IGNORECASE)
    if action_match:
        result["action"] = action_match.group(1).strip()
    
    # Extract Action Input
    input_match = re.search(r'Action Input:\s*(\{.+?\})', text, re.DOTALL)
    if input_match:
        try:
            result["action_input"] = json.loads(input_match.group(1))
        except json.JSONDecodeError:
            # Fallback: extract simple value
            simple_match = re.search(r'Action Input:\s*(.+?)(?=\n|$)', text)
            if simple_match:
                result["action_input"] = {"value": simple_match.group(1).strip()}
    
    return result

# === REACT AGENT ===
class ReActAgent:
    """ReAct Agent với vòng lặp Thought-Action-Observation"""
    
    def __init__(self, max_iterations: int = 3, max_tokens: int = 1800):
        self.max_iterations = max_iterations
        self.max_tokens = max_tokens
    
    def _call_llm(self, prompt: str, image_path: Optional[str] = None) -> str:
        """Gọi LLM (Vision hoặc Text)"""
        if image_path:
            # Dùng Vision model
            base64_img = encode_image(image_path)
            messages = [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
                ]
            }]
            model = VISION_MODEL
        else:
            # Dùng Reasoning model
            messages = [{"role": "user", "content": prompt}]
            model = REASONING_MODEL
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 400
        }
        
        try:
            r = requests.post(VLLM_URL, json=payload, timeout=60)
            result = r.json()
            if 'choices' in result:
                return result['choices'][0]['message']['content']
        except Exception as e:
            return f"Lỗi LLM: {e}"
        
        return "Không nhận được phản hồi từ LLM"
    
    def run(self, query: str, image_path: Optional[str] = None) -> str:
        """Chạy ReAct loop"""
        state = AgentState(current_query=query, image_path=image_path)
        
        image_context = "Có ảnh đính kèm, hãy dùng extract_model để lấy mã Model" if image_path else ""
        
        for iteration in range(self.max_iterations):
            state.iteration = iteration + 1
            state.prune_if_needed(self.max_tokens)
            
            # Build prompt
            prompt = build_react_prompt(query, image_context, state.observations)
            
            # Call LLM (chỉ dùng image ở lần đầu nếu cần describe)
            llm_response = self._call_llm(prompt, image_path=None)
            
            # Parse response
            parsed = parse_react_output(llm_response)
            
            # Check if FINISH
            if parsed["action"].upper() == "FINISH" or not parsed["action"]:
                # Generate final answer
                state.final_answer = self._generate_final_answer(state, parsed["thought"])
                break
            
            # Execute tool
            action_input = parsed["action_input"]
            
            # Handle image path for vision tools
            if parsed["action"] in ["extract_model", "describe_image"] and image_path:
                action_input["image_path"] = image_path
            elif parsed["action"] == "lookup_csv" and "model_code" in action_input:
                pass  # Already has model_code
            elif parsed["action"] == "search_products" and "query" in action_input:
                pass  # Already has query
            elif parsed["action"] == "lookup_csv" and "value" in action_input:
                action_input = {"model_code": action_input["value"]}
            elif parsed["action"] == "search_products" and "value" in action_input:
                action_input = {"query": action_input["value"]}
            
            # Execute
            tool_result = execute_tool(parsed["action"], **action_input)
            
            # Record
            state.tool_calls.append({"action": parsed["action"], "input": action_input})
            observation = f"[{parsed['action']}] → {json.dumps(tool_result, ensure_ascii=False)}"
            state.observations.append(observation)
        
        # If we exhausted iterations without FINISH
        if not state.final_answer:
            state.final_answer = self._generate_final_answer(state, "Đã thử nhiều lần")
        
        return state.final_answer
    
    def _generate_final_answer(self, state: AgentState, last_thought: str) -> str:
        """Tạo câu trả lời cuối cùng từ observations"""
        # Tìm thông tin sản phẩm từ observations
        product_info = None
        for obs in state.observations:
            if '"found": true' in obs.lower() or '"found":true' in obs.lower():
                try:
                    # Extract JSON from observation
                    json_match = re.search(r'\{.*\}', obs)
                    if json_match:
                        data = json.loads(json_match.group())
                        if data.get("found") and data.get("ten_san_pham"):
                            product_info = data
                            break
                        elif data.get("found") and data.get("products"):
                            product_info = data
                            break
                except:
                    pass
        
        if product_info:
            if "ten_san_pham" in product_info:
                return f"""📦 **Thông tin sản phẩm:**
- Tên: {product_info['ten_san_pham']}
- Model: {product_info['model']}
- Giá: **{product_info['gia']:,} VND**
- Nhóm: {product_info.get('nhom_hang', 'N/A')}"""
            elif "products" in product_info:
                lines = ["📦 **Sản phẩm tìm được:**"]
                for p in product_info["products"]:
                    lines.append(f"- {p['ten']} ({p['model']}): **{p['gia']:,} VND**")
                return "\n".join(lines)
        
        # Fallback: summarize observations
        if state.observations:
            return f"Dựa trên thông tin tìm được:\n" + "\n".join(state.observations[-2:])
        
        return "Xin lỗi, tôi không tìm thấy thông tin về sản phẩm này trong hệ thống VIVOHOME."

# === MODEL-BASED EVALUATOR ===
def evaluate_response(question: str, ai_answer: str, ground_truth: Optional[Dict] = None) -> Dict:
    """
    Dùng DeepSeek làm giám khảo chấm điểm câu trả lời.
    Returns: {"score": 1-5, "feedback": str}
    """
    eval_prompt = f"""Chấm điểm câu trả lời của AI bán hàng (thang 1-5).

Câu hỏi khách: {question}
Câu trả lời AI: {ai_answer}
{"Dữ liệu thực: " + str(ground_truth) if ground_truth else ""}

Tiêu chí:
1 = Sai hoàn toàn
2 = Sai một phần
3 = Đúng nhưng thiếu
4 = Đúng và đầy đủ
5 = Xuất sắc

Trả lời format: SCORE: [số] | FEEDBACK: [nhận xét ngắn]"""

    try:
        payload = {
            "model": REASONING_MODEL,
            "messages": [{"role": "user", "content": eval_prompt}],
            "temperature": 0.1,
            "max_tokens": 100
        }
        r = requests.post(VLLM_URL, json=payload, timeout=30)
        result = r.json()
        
        if 'choices' in result:
            text = clean_response(result['choices'][0]['message']['content'])
            score_match = re.search(r'SCORE:\s*(\d)', text)
            feedback_match = re.search(r'FEEDBACK:\s*(.+)', text)
            
            return {
                "score": int(score_match.group(1)) if score_match else 3,
                "feedback": feedback_match.group(1).strip() if feedback_match else text
            }
    except:
        pass
    
    return {"score": 0, "feedback": "Không thể đánh giá"}

# === TEST ===
if __name__ == "__main__":
    agent = ReActAgent(max_iterations=3)
    
    # Test 1: Text query
    print("=" * 50)
    print("TEST 1: Text query")
    result = agent.run("Bình tắm Rossi 15 lít giá bao nhiêu?")
    print(result)
    
    # Evaluate
    eval_result = evaluate_response(
        "Bình tắm Rossi 15 lít giá bao nhiêu?",
        result,
        {"gia": 1500000}
    )
    print(f"\n📊 Evaluation: Score={eval_result['score']}/5 | {eval_result['feedback']}")
