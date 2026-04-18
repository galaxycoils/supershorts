import json
import re
import concurrent.futures
import ollama
from src.core.config import OLLAMA_MODEL, OLLAMA_TIMEOUT

def safe_json_parse(text: str) -> dict:
    """Parse JSON tolerantly: strip trailing commas, control chars, BOM."""
    text = text.strip().lstrip('\ufeff')
    text = re.sub(r',\s*([}\]])', r'\1', text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return json.loads(text)

def ollama_generate(prompt: str, json_mode: bool = True) -> dict:
    full_prompt = prompt
    if json_mode:
        full_prompt += "\n\nRespond with ONLY valid JSON. No explanations, no markdown, no extra text."

    def _call():
        return ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{'role': 'user', 'content': full_prompt}],
            options={
                'temperature': 0.6,
                'num_ctx': 4096,
                'num_gpu': 1,
                'num_thread': 8,
                'repeat_penalty': 1.1
            }
        )

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(_call)
            response = future.result(timeout=OLLAMA_TIMEOUT)
    except concurrent.futures.TimeoutError:
        print(f"⚠️ Ollama timed out after {OLLAMA_TIMEOUT}s — returning empty result.")
        return {}
    except Exception as e:
        print(f"⚠️ Ollama error: {e}")
        return {}

    text = response['message']['content'].strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
    
    try:
        return safe_json_parse(text)
    except Exception as e:
        print(f"⚠️ JSON parse failed: {e}\nRaw output: {text[:200]}")
        # Last-ditch regex for array if root is array
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            try: return json.loads(match.group(0))
            except: pass
        return {}
