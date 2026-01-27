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
        
        # 记录报告长度
        report_length = len(state.structured_report) if state.structured_report else 0
        logger.info("Generating script from report (%d chars)...", report_length)

        prompt = f"<RESEARCH_REPORT>\n{state.structured_report}\n</RESEARCH_REPORT>"

        response = self._agent.run(prompt)
        self._agent.clear_history()
        
        # 记录原始响应
        response_length = len(response) if response else 0
        logger.info("Received LLM response (%d chars)", response_length)

        if self._config.strip_thinking_tokens:
            response = strip_thinking_tokens(response)
        
        cleaned_response = response.strip()
        
        # 调试日志：记录原始响应的前500字符
        logger.debug("Raw LLM response (first 500 chars): %s", response[:500] if response else "EMPTY")
        
        # 1. 尝试查找 Markdown 代码块
        code_block_pattern = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
        match = code_block_pattern.search(cleaned_response)
        if match:
            cleaned_response = match.group(1).strip()
            logger.debug("Extracted from code block: %s", cleaned_response[:200] if cleaned_response else "EMPTY")
        else:
            # 2. 尝试查找 [ 和 ] 之间的内容
            start = cleaned_response.find("[")
            end = cleaned_response.rfind("]")
            if start != -1 and end != -1 and end > start:
                cleaned_response = cleaned_response[start:end+1]
                logger.debug("Extracted array from response: %s", cleaned_response[:200] if cleaned_response else "EMPTY")
            else:
                logger.warning("Could not find JSON array in response. Response preview: %s", cleaned_response[:300] if cleaned_response else "EMPTY")
        
        # 3. 修复常见的 JSON 格式问题
        # 替换单引号为双引号（某些 LLM 可能输出单引号）
        if cleaned_response and cleaned_response.startswith("["):
            # 尝试修复可能的格式问题
            cleaned_response = cleaned_response.replace("'", '"')
            # 移除可能的尾随逗号
            cleaned_response = re.sub(r',\s*]', ']', cleaned_response)
            cleaned_response = re.sub(r',\s*}', '}', cleaned_response)
        
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
                elif isinstance(item, dict):
                    # 尝试兼容其他可能的字段名
                    role = item.get("role") or item.get("speaker") or item.get("name") or ""
                    content = item.get("content") or item.get("text") or item.get("message") or ""
                    if role and content:
                        valid_script.append({"role": role, "content": content})
            
            logger.info("Generated script with %d dialogue turns.", len(valid_script))
            return valid_script

        except json.JSONDecodeError as e:
            logger.error("Failed to parse script generation output as JSON.")
            logger.error("JSON error: %s", str(e))
            logger.error("Cleaned response (first 500 chars): %s", cleaned_response[:500] if cleaned_response else "EMPTY")
            logger.error("Original response (first 1000 chars): %s", response[:1000] if response else "EMPTY")
            
            # 最后尝试：使用正则表达式提取对话
            return self._fallback_extract_dialogues(response)

    def _fallback_extract_dialogues(self, text: str) -> List[dict[str, str]]:
        """
        当 JSON 解析失败时，尝试用正则表达式提取对话内容。
        
        支持的格式：
        - {"role": "Host", "content": "..."}
        - Host: ...
        - **Host**: ...
        """
        dialogues = []
        
        # 方法1：尝试提取单个 JSON 对象
        json_obj_pattern = re.compile(
            r'\{\s*"role"\s*:\s*"([^"]+)"\s*,\s*"content"\s*:\s*"([^"]*(?:\\.[^"]*)*)"\s*\}',
            re.DOTALL
        )
        matches = json_obj_pattern.findall(text)
        if matches:
            for role, content in matches:
                # 解码转义字符
                try:
                    content = content.encode().decode('unicode_escape')
                except Exception:
                    pass
                dialogues.append({"role": role, "content": content})
            if dialogues:
                logger.info("Fallback extraction (JSON objects) found %d dialogues.", len(dialogues))
                return dialogues
        
        # 方法2：尝试提取 "Host: ..." 或 "**Host**: ..." 格式
        line_pattern = re.compile(
            r'(?:\*\*)?(?P<role>Host|Guest|Xiayu|Liwa)(?:\*\*)?\s*[:：]\s*(?P<content>.+?)(?=(?:\n(?:\*\*)?(?:Host|Guest|Xiayu|Liwa)(?:\*\*)?\s*[:：])|$)',
            re.DOTALL | re.IGNORECASE
        )
        matches = line_pattern.findall(text)
        if matches:
            for role, content in matches:
                content = content.strip().strip('"').strip("'")
                if content:
                    # 标准化角色名
                    role_normalized = "Host" if role.lower() in ["host", "xiayu"] else "Guest"
                    dialogues.append({"role": role_normalized, "content": content})
            if dialogues:
                logger.info("Fallback extraction (line format) found %d dialogues.", len(dialogues))
                return dialogues
        
        logger.warning("Fallback extraction failed. No dialogues found.")
        return []
