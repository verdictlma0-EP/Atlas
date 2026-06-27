import json
import re
from ..config import CONFIG
from ..kernel.events import EventBus

def call_llm(messages, model, provider="groq", is_json=False):
    import requests, time
    if provider == "groq":
        url = CONFIG["groq_url"]
        headers = {"Authorization": f"Bearer {CONFIG['groq_key']}", "Content-Type": "application/json"}
    else:  # deepseek
        url = CONFIG["deepseek_url"]
        headers = {"Authorization": f"Bearer {CONFIG['deepseek_key']}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "temperature": 0.0, "stream": False}
    for _ in range(2):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            if is_json:
                match = re.search(r'\{.*\}', content, re.DOTALL) or re.search(r'\[.*\]', content, re.DOTALL)
                if match:
                    content = match.group()
                json.loads(content)
            return content
        except Exception as e:
            time.sleep(1)
    return "{}"

def compile_intent(user_input: str) -> dict:
    sys_prompt = """
You are an Intent Compiler. Parse the user's request into a structured JSON object.
Output EXACTLY this schema:
{
    "intent": "brief description",
    "constraints": ["list", "of", "constraints"],
    "entities": ["relevant", "entities"]
}
Keep it short. No extra text. Only valid JSON.
"""
    resp = call_llm(
        [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_input}],
        CONFIG["intent_model"],
        provider="groq",
        is_json=True
    )
    return json.loads(resp)
