import unittest
from unittest.mock import MagicMock
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from services.script_generator import ScriptGenerationService
from models import SummaryState
from config import Configuration

class TestScriptGenerationService(unittest.TestCase):
    def setUp(self):
        self.mock_agent = MagicMock()
        self.mock_config = MagicMock()
        self.mock_config.strip_thinking_tokens = True
        self.service = ScriptGenerationService(self.mock_agent, self.mock_config)

    def test_generate_script_success(self):
        state = SummaryState(research_topic="Test Topic")
        state.structured_report = "# Test Report\nContent..."
        
        # Mock LLM response
        mock_response = """
        Thinking process...
        
        ```json
        [
            {"role": "Host", "content": "Hello"},
            {"role": "Guest", "content": "Hi there"}
        ]
        ```
        """
        self.mock_agent.run.return_value = mock_response

        script = self.service.generate_script(state)
        
        self.assertEqual(len(script), 2)
        self.assertEqual(script[0]['role'], "Host")
        self.assertEqual(script[0]['content'], "Hello")
        self.assertEqual(script[1]['role'], "Guest")
        self.assertEqual(script[1]['content'], "Hi there")

    def test_generate_script_no_report(self):
        state = SummaryState(research_topic="Test Topic")
        state.structured_report = None
        
        script = self.service.generate_script(state)
        self.assertEqual(script, [])

    def test_generate_script_invalid_json(self):
        state = SummaryState(research_topic="Test Topic")
        state.structured_report = "Report"
        
        self.mock_agent.run.return_value = "Not JSON"
        
        script = self.service.generate_script(state)
        self.assertEqual(script, [])

if __name__ == '__main__':
    unittest.main()
