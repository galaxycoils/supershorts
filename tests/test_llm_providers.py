import unittest
from unittest.mock import patch, MagicMock
from src.infrastructure.llm import get_llm_service, LMStudioLLMService, OllamaLLMService

class TestLLMProviders(unittest.TestCase):

    @patch('src.infrastructure.llm.OllamaLLMService')
    def test_factory_default(self, mock_ollama):
        service = get_llm_service(provider='ollama', model='test-model')
        mock_ollama.assert_called_with(model='test-model')

    @patch('src.infrastructure.llm.LMStudioLLMService')
    def test_factory_lmstudio(self, mock_lms):
        service = get_llm_service(provider='lmstudio', model='test-model')
        mock_lms.assert_called_with(model='test-model')

    @patch('requests.post')
    def test_lmstudio_generate(self, mock_post):
        # Mock successful OpenAI-style response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': '{"result": "success"}'
                }
            }]
        }
        mock_post.return_value = mock_response

        service = LMStudioLLMService(model='test-model')
        result = service.generate("test prompt", json_mode=True)
        
        self.assertEqual(result, {"result": "success"})
        mock_post.assert_called()

    @patch('requests.post')
    def test_lmstudio_generate_with_markdown(self, mock_post):
        # Mock response with markdown code blocks
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'Here is the JSON:\n```json\n{"key": "value"}\n```'
                }
            }]
        }
        mock_post.return_value = mock_response

        service = LMStudioLLMService(model='test-model')
        result = service.generate("test prompt", json_mode=True)
        
        self.assertEqual(result, {"key": "value"})

if __name__ == '__main__':
    unittest.main()
