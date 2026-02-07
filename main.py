import requests

def test_vllm():
    url = "http://localhost:8000/v1/chat/completions"
    payload = {
        "model": "deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
        "messages": [
            {"role": "user", "content": "Tư vấn cho tôi một chiếc tủ lạnh Samsung inverter tiết kiệm điện cho cửa hàng điện máy."}
        ],
        "temperature": 0.7
    }
    
    response = requests.post(url, json=payload)
    print("AI Response:", response.json()['choices'][0]['message']['content'])

if __name__ == "__main__":
    test_vllm()