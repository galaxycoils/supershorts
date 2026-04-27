import pytest
import json
import os
import re
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
from src.infrastructure.llm import (
    safe_json_parse,
    ollama_generate,
    OllamaLLMService,
    LMStudioLLMService,
    get_llm_service,
    list_system_mcp_servers,
    sync_mcp_to_lmstudio
)

def test_safe_json_parse_markdown():
    text = "Here is the json: ```json\n{\"key\": \"value\"}\n``` and some more text."
    assert safe_json_parse(text) == {"key": "value"}
    
    text2 = "```\n{\"a\": 1}\n```"
    assert safe_json_parse(text2) == {"a": 1}

def test_safe_json_parse_last_ditch():
    text = "Random text {\"b\": 2} more junk"
    assert safe_json_parse(text) == {"b": 2}
    
    text_arr = "List: [1, 2, 3] end"
    assert safe_json_parse(text_arr) == [1, 2, 3]

def test_safe_json_parse_malformed_last_ditch():
    # Test regex fallback with extra junk around valid JSON
    assert safe_json_parse("junk {\"a\": 1} more junk") == {"a": 1}
    assert safe_json_parse("junk [1, 2] more junk") == [1, 2]

def test_safe_json_parse_regex_failure():
    # Regex matches but json.loads fails
    assert safe_json_parse("junk { malformed } junk") == {}
    assert safe_json_parse("junk [ malformed ] junk") == {}

def test_safe_json_parse_failure():
    assert safe_json_parse("invalid junk") == {}

@patch("src.infrastructure.llm.OllamaLLMService")
def test_ollama_generate_legacy(mock_service_class):
    mock_service = mock_service_class.return_value
    mock_service.generate.return_value = {"res": "ok"}
    
    result = ollama_generate("prompt")
    assert result == {"res": "ok"}
    mock_service_class.assert_called_once()

def test_base_llm_service_prepare_prompt_funny():
    with patch.dict(os.environ, {"LLM_TONE": "funny"}):
        service = OllamaLLMService("model")
        prompt = service._prepare_prompt("hello", json_mode=True)
        assert "Humorous" in prompt
        assert "ONLY valid JSON" in prompt

@patch("ollama.chat")
def test_ollama_llm_service_generate(mock_chat):
    mock_chat.return_value = {
        "message": {"content": "{\"status\": \"ok\"}"}
    }
    service = OllamaLLMService("test-model")
    result = service.generate("test prompt")
    assert result == {"status": "ok"}
    mock_chat.assert_called_once()

@patch("ollama.chat")
def test_ollama_llm_service_error(mock_chat):
    mock_chat.side_effect = Exception("Ollama error")
    service = OllamaLLMService("test-model")
    result = service.generate("test prompt")
    assert result == {}

@patch("requests.post")
def test_lmstudio_llm_service_generate(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "{\"lm\": \"studio\"}"}}]
    }
    mock_post.return_value = mock_response
    
    service = LMStudioLLMService("model")
    result = service.generate("prompt")
    assert result == {"lm": "studio"}

def test_get_llm_service_factory():
    with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}):
        assert isinstance(get_llm_service(), OllamaLLMService)
    
    with patch.dict(os.environ, {"LLM_PROVIDER": "lmstudio"}):
        assert isinstance(get_llm_service(), LMStudioLLMService)

def test_get_llm_service_explicit_params():
    service = get_llm_service(provider="ollama", model="custom-model")
    assert service.model == "custom-model"

def test_get_llm_service_lmstudio_explicit():
    service = get_llm_service(provider="lmstudio", model="custom-lm")
    assert isinstance(service, LMStudioLLMService)
    assert service.model == "custom-lm"

def test_get_llm_service_default_fallbacks():
    # Pass None, let both fallback
    with patch.dict(os.environ, {"LLM_PROVIDER": "ollama", "OLLAMA_MODEL": "env-model"}):
        service = get_llm_service(None, None)
        assert isinstance(service, OllamaLLMService)
        assert service.model == "env-model"

@patch("src.infrastructure.llm.Path")
def test_list_system_mcp_servers(mock_path_class):
    mock_claude_path = MagicMock()
    mock_claude_path.expanduser.return_value = mock_claude_path
    mock_claude_path.exists.return_value = True
    mock_claude_path.read_text.return_value = json.dumps({"mcpServers": {"server1": {"command": "node"}}})
    
    mock_gemini_path = MagicMock()
    mock_gemini_path.expanduser.return_value = mock_gemini_path
    mock_gemini_path.exists.return_value = True
    
    mock_manifest = MagicMock()
    mock_manifest.read_text.return_value = json.dumps({"mcpServers": {"ext1": {"command": "python", "args": ["${extensionPath}/main.py"]}}})
    mock_manifest.parent = Path("/mock/ext1")
    
    mock_gemini_path.glob.return_value = [mock_manifest]
    
    def path_side_effect(path_str):
        if "Claude" in path_str: return mock_claude_path
        if "gemini" in path_str: return mock_gemini_path
        return MagicMock()

    mock_path_class.side_effect = path_side_effect
    
    servers = list_system_mcp_servers()
    assert "server1" in servers
    assert "gemini_ext1" in servers

@patch("src.infrastructure.llm.Path")
def test_list_system_mcp_servers_gemini_read_error(mock_path_class):
    mock_gemini_path = MagicMock()
    mock_gemini_path.expanduser.return_value = mock_gemini_path
    mock_gemini_path.exists.return_value = True
    
    mock_manifest = MagicMock()
    mock_manifest.read_text.side_effect = Exception("JSON parse error")
    mock_gemini_path.glob.return_value = [mock_manifest]
    
    mock_path_class.side_effect = lambda p: mock_gemini_path if "gemini" in p else MagicMock(exists=lambda: False)
    
    servers = list_system_mcp_servers()
    assert servers == {}

@patch("src.infrastructure.llm.Path")
def test_list_system_mcp_servers_exceptions(mock_path_class):
    mock_claude_path = MagicMock()
    mock_claude_path.expanduser.return_value = mock_claude_path
    mock_claude_path.exists.return_value = True
    mock_claude_path.read_text.side_effect = Exception("Read error")
    
    mock_gemini_path = MagicMock()
    mock_gemini_path.expanduser.return_value = mock_gemini_path
    mock_gemini_path.exists.return_value = True
    mock_gemini_path.glob.side_effect = Exception("Glob error")
    
    def path_side_effect(path_str):
        if "Claude" in path_str: return mock_claude_path
        if "gemini" in path_str: return mock_gemini_path
        return MagicMock()
    mock_path_class.side_effect = path_side_effect
    
    servers = list_system_mcp_servers()
    assert servers == {}

@patch("src.infrastructure.llm.list_system_mcp_servers")
@patch("requests.get")
def test_sync_mcp_to_lmstudio_reachable(mock_get, mock_list):
    mock_list.return_value = {"s1": {}}
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response
    with patch("builtins.print") as mock_print:
        sync_mcp_to_lmstudio()
        mock_print.assert_any_call("✅ LM Studio is active.")

@patch("src.infrastructure.llm.list_system_mcp_servers")
def test_sync_mcp_to_lmstudio_no_servers(mock_list):
    mock_list.return_value = {}
    with patch("builtins.print") as mock_print:
        sync_mcp_to_lmstudio()
        mock_print.assert_any_call("No system MCP servers discovered.")

@patch("src.infrastructure.llm.list_system_mcp_servers")
@patch("requests.get")
def test_sync_mcp_to_lmstudio_unreachable(mock_get, mock_list):
    mock_list.return_value = {"s1": {}}
    mock_get.side_effect = Exception("Connection refused")
    with patch("builtins.print") as mock_print:
        sync_mcp_to_lmstudio()
        mock_print.assert_any_call("❌ LM Studio is not reachable. Ensure it is running on port 1234.")
