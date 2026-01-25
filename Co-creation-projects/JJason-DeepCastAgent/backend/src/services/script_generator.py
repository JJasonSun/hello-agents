"""Service that converts the research report into a podcast script."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, List

from hello_agents import ToolAwareSimpleAgent

from models import SummaryState
from config import Configuration
from prompts import script_writer_instructions
from utils import strip_thinking_tokens

logger = logging.getLogger(__name__)


class ScriptGenerationService:
    """Generates a dialogue script from the research report."""

    def __init__(self, script_agent: ToolAwareSimpleAgent, config: Configuration) -> None:
        self._agent = script_agent
        self._config = config

    def generate_script(self, state: SummaryState) -> List[dict[str, str]]:
        """Generate a podcast script based on the structured report."""

        if not state.structured_report:
            logger.warning("No structured report available for script generation.")
            return []

        prompt = f"{script_writer_instructions}\n\n<RESEARCH_REPORT>\n{state.structured_report}\n</RESEARCH_REPORT>"

        response = self._agent.run(prompt)
        self._agent.clear_history()

        if self._config.strip_thinking_tokens:
            response = strip_thinking_tokens(response)
        
        cleaned_response = response.strip()
        
        # 1. Try to find markdown code block
        code_block_pattern = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
        match = code_block_pattern.search(cleaned_response)
        if match:
            cleaned_response = match.group(1).strip()
        else:
            # 2. Try to find content between [ and ]
            start = cleaned_response.find("[")
            end = cleaned_response.rfind("]")
            if start != -1 and end != -1 and end > start:
                cleaned_response = cleaned_response[start:end+1]
        
        try:
            script = json.loads(cleaned_response)
            if not isinstance(script, list):
                logger.error("Script generation output is not a list: %s", type(script))
                return []
            
            # Validate script format
            valid_script = []
            for item in script:
                if isinstance(item, dict) and "role" in item and "content" in item:
                    valid_script.append(item)
            
            logger.info("Generated script with %d dialogue turns.", len(valid_script))
            return valid_script

        except json.JSONDecodeError:
            logger.error("Failed to parse script generation output as JSON: %s", response[:500])
            return []
