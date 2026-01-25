"""将研究报告转换为播客脚本的服务。"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, List

from hello_agents import ToolAwareSimpleAgent

from models import SummaryState
from config import Configuration
from utils import strip_thinking_tokens

logger = logging.getLogger(__name__)


class ScriptGenerationService:
    """从研究报告生成对话脚本。"""

    def __init__(self, script_agent: ToolAwareSimpleAgent, config: Configuration) -> None:
        self._agent = script_agent
        self._config = config

    def generate_script(self, state: SummaryState) -> List[dict[str, str]]:
        """
        基于结构化报告生成播客脚本。
        
        Args:
            state: 包含结构化报告的研究状态。
            
        Returns:
            对话脚本列表，每项包含 role 和 content。
        """

        if not state.structured_report:
            logger.warning("No structured report available for script generation.")
            return []

        prompt = f"<RESEARCH_REPORT>\n{state.structured_report}\n</RESEARCH_REPORT>"

        response = self._agent.run(prompt)
        self._agent.clear_history()

        if self._config.strip_thinking_tokens:
            response = strip_thinking_tokens(response)
        
        cleaned_response = response.strip()
        
        # 1. 尝试查找 Markdown 代码块
        code_block_pattern = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
        match = code_block_pattern.search(cleaned_response)
        if match:
            cleaned_response = match.group(1).strip()
        else:
            # 2. 尝试查找 [ 和 ] 之间的内容
            start = cleaned_response.find("[")
            end = cleaned_response.rfind("]")
            if start != -1 and end != -1 and end > start:
                cleaned_response = cleaned_response[start:end+1]
        
        try:
            script = json.loads(cleaned_response)
            if not isinstance(script, list):
                logger.error("Script generation output is not a list: %s", type(script))
                return []
            
            # 验证脚本格式
            valid_script = []
            for item in script:
                if isinstance(item, dict) and "role" in item and "content" in item:
                    valid_script.append(item)
            
            logger.info("Generated script with %d dialogue turns.", len(valid_script))
            return valid_script

        except json.JSONDecodeError:
            logger.error("Failed to parse script generation output as JSON: %s", response[:500])
            return []
