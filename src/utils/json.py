import json
import re

def safe_json_parse(text: str) -> dict:
    """Parse JSON tolerantly: strip trailing commas, control chars, BOM."""
    text = text.strip().lstrip('\ufeff')
    text = re.sub(r',\s*([}\]])', r'\1', text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    try:
        return json.loads(text)
    except Exception:
        # Try finding array or object if raw text has fluff
        match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
        if match:
            try: return json.loads(match.group(0))
            except: pass
        raise
