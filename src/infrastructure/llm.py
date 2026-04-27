import json
import logging
import os
import re
import concurrent.futures
import requests
from pathlib import Path
from typing import Any, Union, Optional, Callable, Dict, Type, List
from src.core.config import OLLAMA_MODEL, OLLAMA_TIMEOUT, LLM_PROVIDER, LMSTUDIO_BASE_URL
from src.core.interfaces import ILLMService

logger = logging.getLogger(__name__)

def safe_json_parse(text: str) -> Any:
    """Parse JSON tolerantly: strip trailing commas, control chars, BOM."""
    text = text.strip().lstrip('\ufeff')
    # Remove markdown code blocks if present
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
    
    text = text.strip()
    text = re.sub(r',\s*([}\]])', r'\1', text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    try:
        return json.loads(text)
    except Exception as e:
        # Last-ditch regex for array if root is array
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            try: return json.loads(match.group(0))
            except Exception: pass
        
        # Last-ditch regex for object
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try: return json.loads(match.group(0))
            except Exception: pass
            
        print(f"⚠️ JSON parse failed: {e}\nRaw output: {text[:200]}")
        return {}

def ollama_generate(prompt: str, json_mode: bool = True, model: str = OLLAMA_MODEL, timeout: int = OLLAMA_TIMEOUT) -> Union[dict, list]:
    """Legacy re-export for backward compatibility during refactor."""
    service = OllamaLLMService(model=model, timeout=timeout)
    return service.generate(prompt, json_mode)

class BaseLLMService(ILLMService):
    def __init__(self, model: str, timeout: int = OLLAMA_TIMEOUT):
        self.model = model
        self.timeout = timeout

    def _get_temperature(self) -> float:
        return float(os.environ.get('LLM_TEMPERATURE', '0.6'))

    def _prepare_prompt(self, prompt: str, json_mode: bool) -> str:
        full_prompt = prompt
        tone = os.environ.get("LLM_TONE", "educational")
        
        if tone == "funny":
            style_instr = "Style: Humorous, witty, and engaging. Use funny analogies and a lighthearted tone."
            full_prompt = f"{style_instr}\n\n{full_prompt}"
        
        if json_mode:
            full_prompt += "\n\nRespond with ONLY valid JSON. No explanations, no markdown, no extra text."
        return full_prompt

class OllamaLLMService(BaseLLMService):
    def generate(self, prompt: str, json_mode: bool = True) -> Union[dict, list]:
        import ollama
        full_prompt = self._prepare_prompt(prompt, json_mode)

        def _call() -> Any:
            return ollama.chat(
                model=self.model,
                messages=[{'role': 'user', 'content': full_prompt}],
                options={
                    'temperature': self._get_temperature(),
                    'num_ctx': 4096,
                    'num_gpu': 1,
                    'num_thread': 8,
                    'repeat_penalty': 1.1
                }
            )

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(_call)
                response = future.result(timeout=self.timeout)
            text = response['message']['content'].strip()
            return safe_json_parse(text)
        except Exception as e:
            print(f"⚠️ Ollama error: {e}")
            return {}

class LMStudioLLMService(BaseLLMService):
    def __init__(self, model: str, base_url: str = LMSTUDIO_BASE_URL, timeout: int = OLLAMA_TIMEOUT):
        super().__init__(model, timeout)
        self.base_url = base_url

    def generate(self, prompt: str, json_mode: bool = True) -> Union[dict, list]:
        full_prompt = self._prepare_prompt(prompt, json_mode)
        
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": full_prompt}],
            "temperature": self._get_temperature(),
        }
        
        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            text = data['choices'][0]['message']['content'].strip()
            return safe_json_parse(text)
        except Exception as e:
            print(f"⚠️ LM Studio error: {e}")
            return {}

def get_llm_service(provider: Optional[str] = None, model: Optional[str] = None) -> ILLMService:
    provider = provider or os.environ.get("LLM_PROVIDER", LLM_PROVIDER)
    model = model or os.environ.get("OLLAMA_MODEL", OLLAMA_MODEL)
    
    if provider == "lmstudio":
        return LMStudioLLMService(model=model)
    return OllamaLLMService(model=model)

# --- MCP Tool Discovery for LM Studio ---

def list_system_mcp_servers() -> Dict[str, Any]:
    """Discover MCP servers from Claude Desktop, Gemini CLI, and Codex."""
    servers = {}
    
    # 1. Claude Desktop
    claude_config = Path("~/Library/Application Support/Claude/claude_desktop_config.json").expanduser()
    if claude_config.exists():
        try:
            data = json.loads(claude_config.read_text())
            if "mcpServers" in data:
                servers.update(data["mcpServers"])
        except Exception as e: pass

    # 2. Gemini CLI
    gemini_dir = Path("~/.gemini/extensions").expanduser()
    if gemini_dir.exists():
        try:
            for manifest in gemini_dir.glob("*/gemini-extension.json"):
                try:
                    data = json.loads(manifest.read_text())
                    if "mcpServers" in data:
                        # Map to LM Studio expected format
                        for name, config in data["mcpServers"].items():
                            servers[f"gemini_{name}"] = {
                                "command": config.get("command"),
                                "args": [a.replace("${extensionPath}", str(manifest.parent)) for a in config.get("args", [])],
                                "env": config.get("env", {})
                            }
                except Exception as e: pass
        except Exception as e: pass

    return servers

def sync_mcp_to_lmstudio():
    """Attempt to push discovered MCP servers to LM Studio (if API supported)."""
    # Note: LM Studio 0.3.x MCP support is via filesystem config or UI.
    # We will print the suggested config for the user for now.
    servers = list_system_mcp_servers()
    if not servers:
        print("No system MCP servers discovered.")
        return
    
    print("\n🚀 Discovered MCP Servers for LM Studio:")
    print(json.dumps(servers, indent=2))
    
    # Check if LM Studio is reachable
    try:
        r = requests.get(f"{LMSTUDIO_BASE_URL.rstrip('/')}/models", timeout=2)
        if r.status_code == 200:
            print("✅ LM Studio is active.")
    except Exception as e:
        print("❌ LM Studio is not reachable. Ensure it is running on port 1234.")
