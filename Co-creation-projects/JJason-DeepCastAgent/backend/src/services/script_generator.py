"""将研究报告转换为播客脚本的服务。"""

from __future__ import annotations

import json
import logging

from openai import OpenAI

from config import Configuration
from models import SummaryState
from prompts import script_writer_instructions

logger = logging.getLogger(__name__)

# 播客脚本的 JSON Schema
SCRIPT_JSON_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "role": {
                "type": "string",
                "enum": ["Host", "Guest"],
                "description": "对话角色，Host 为主持人，Guest 为嘉宾"
            },
            "content": {
                "type": "string",
                "description": "对话内容"
            }
        },
        "required": ["role", "content"]
    },
    "minItems": 6,
    "maxItems": 15
}


class ScriptGenerationService:
    """从研究报告生成对话脚本（使用结构化输出）。"""

    def __init__(self, script_agent, config: Configuration) -> None:
        """初始化服务。"""
        self._config = config
        # 直接使用 OpenAI 客户端以支持结构化输出
        self._client = OpenAI(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url,
        )
        # 使用 fast_llm_model（ecnu-plus）进行脚本生成，它支持结构化输出
        self._model = config.fast_llm_model or "ecnu-plus"

    def generate_script(self, state: SummaryState) -> list[dict[str, str]]:
        """基于结构化报告生成播客脚本（使用结构化输出）。"""
        if not state.structured_report:
            logger.warning("No structured report available for script generation.")
            return []
        
        report_length = len(state.structured_report)
        logger.info("Generating script from report (%d chars) using structured output...", report_length)

        user_prompt = f"<RESEARCH_REPORT>\n{state.structured_report}\n</RESEARCH_REPORT>"

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": script_writer_instructions.strip()},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=4096,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "podcast_script",
                        "schema": SCRIPT_JSON_SCHEMA
                    },
                },
            )
            
            content = response.choices[0].message.content
            logger.info("Received structured response (%d chars)", len(content) if content else 0)
            
            if not content:
                logger.error("Empty response from LLM")
                return []
            
            # 直接解析 JSON（结构化输出保证格式正确）
            script = json.loads(content)
            
            if not isinstance(script, list):
                logger.error("Script output is not a list: %s", type(script))
                return []
            
            # 验证并标准化
            valid_script = []
            for item in script:
                if isinstance(item, dict) and "role" in item and "content" in item:
                    role = item["role"]
                    content = item["content"]
                    # 标准化角色名
                    if role.lower() in ["host", "xiayu"]:
                        role = "Host"
                    elif role.lower() in ["guest", "liwa"]:
                        role = "Guest"
                    valid_script.append({"role": role, "content": content})
            
            logger.info("Generated script with %d dialogue turns.", len(valid_script))
            return valid_script

        except json.JSONDecodeError as e:
            logger.error("JSON decode error (should not happen with structured output): %s", e)
            return []
        except Exception as e:
            logger.error("Script generation failed: %s", e)
            return []
