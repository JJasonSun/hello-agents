import os
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

# Define backend root directory
BACKEND_ROOT = Path(__file__).resolve().parent.parent

class SearchAPI(Enum):
    """搜索 API 提供商（仅支持混合搜索：Tavily + SerpApi）。"""
    HYBRID = "hybrid"


class Configuration(BaseModel):
    """DeepCast Agent Configuration."""

    max_web_research_loops: int = Field(
        default=3,
        title="Research Depth",
        description="Number of research iterations",
    )
    llm_provider: str = Field(
        default="custom",
        title="LLM 提供商",
        description="提供商标识符 (custom)",
    )
    search_api: SearchAPI = Field(
        default=SearchAPI.HYBRID,
        title="搜索 API",
        description="使用混合搜索引擎 (Tavily + SerpApi)",
    )
    enable_notes: bool = Field(
        default=True,
        title="启用笔记",
        description="是否在 NoteTool 中存储任务进度",
    )
    notes_workspace: str = Field(
        default=str(BACKEND_ROOT / "output" / "notes"),
        title="笔记工作区",
        description="NoteTool 持久化任务笔记的目录",
    )
    fetch_full_page: bool = Field(
        default=True,
        title="获取完整页面",
        description="在搜索结果中包含完整页面内容",
    )
    strip_thinking_tokens: bool = Field(
        default=False,
        title="移除思考 Token",
        description="是否从模型响应中移除 <think> token",
    )
    use_tool_calling: bool = Field(
        default=False,
        title="使用工具调用",
        description="使用工具调用而非 JSON 模式进行结构化输出",
    )
    llm_api_key: str | None = Field(
        default=None,
        title="LLM API 密钥",
        description="使用自定义 OpenAI 兼容服务时的可选 API 密钥",
    )
    llm_base_url: str | None = Field(
        default=None,
        title="LLM 基础 URL",
        description="使用自定义 OpenAI 兼容服务时的可选基础 URL",
    )
    llm_model_id: str | None = Field(
        default=None,
        title="LLM 模型 ID",
        description="自定义 OpenAI 兼容服务的可选模型标识符",
    )
    smart_llm_model: str | None = Field(
        default="ecnu-reasoner",
        title="Smart LLM Model",
        description="复杂推理任务使用的模型 ID (e.g. Planning, Reporting)",
    )
    fast_llm_model: str | None = Field(
        default="ecnu-max",
        title="Fast LLM Model",
        description="快速响应任务使用的模型 ID (e.g. Web Research, Script Generation)",
    )
    tts_api_key: str | None = Field(
        default=None,
        title="TTS API 密钥",
        description="TTS 服务的 API 密钥",
    )
    tts_base_url: str = Field(
        default="https://chat.ecnu.edu.cn/open/api/v1/audio/speech",
        title="TTS 基础 URL",
        description="TTS API 的基础 URL",
    )
    tts_model: str = Field(
        default="ecnu-tts",
        title="TTS 模型",
        description="TTS 服务的模型标识符",
    )
    audio_output_dir: str = Field(
        default=str(BACKEND_ROOT / "output" / "audio"),
        title="音频输出目录",
        description="保存生成的音频文件的目录",
    )
    ffmpeg_path: str | None = Field(
        default=None,
        title="FFmpeg 路径",
        description="ffmpeg 可执行文件的路径",
    )
    tavily_api_key: str | None = Field(
        default=None,
        title="Tavily API 密钥",
        description="Tavily 搜索的 API 密钥",
    )
    serpapi_api_key: str | None = Field(
        default=None,
        title="SerpApi 密钥",
        description="SerpApi 的 API 密钥",
    )

    @field_validator("notes_workspace", "audio_output_dir")
    @classmethod
    def resolve_path(cls, v: str) -> str:
        """确保路径是绝对路径，如果是相对路径则基于 BACKEND_ROOT 解析。"""
        if v is None:
            return v
        path = Path(v)
        if not path.is_absolute():
            return str(BACKEND_ROOT / path)
        return v

    @classmethod
    def from_env(cls, overrides: dict[str, Any] | None = None) -> "Configuration":
        """
        使用环境变量和覆盖项创建配置对象。
        
        Args:
            overrides: 可选的配置覆盖字典。
            
        Returns:
            初始化的配置对象。
        """
        raw_values: dict[str, Any] = {}

        # 基于字段名从环境变量加载值
        for field_name in cls.model_fields.keys():
            env_key = field_name.upper()
            if env_key in os.environ:
                raw_values[field_name] = os.environ[env_key]

        # 显式环境名称的额外映射
        env_aliases = {
            "llm_provider": os.getenv("LLM_PROVIDER"),
            "llm_api_key": os.getenv("LLM_API_KEY"),
            "llm_model_id": os.getenv("LLM_MODEL_ID"),
            "smart_llm_model": os.getenv("SMART_LLM_MODEL"),
            "fast_llm_model": os.getenv("FAST_LLM_MODEL"),
            "llm_base_url": os.getenv("LLM_BASE_URL"),
            "max_web_research_loops": os.getenv("MAX_WEB_RESEARCH_LOOPS"),
            "fetch_full_page": os.getenv("FETCH_FULL_PAGE"),
            "strip_thinking_tokens": os.getenv("STRIP_THINKING_TOKENS"),
            "use_tool_calling": os.getenv("USE_TOOL_CALLING"),
            "search_api": os.getenv("SEARCH_API"),
            "enable_notes": os.getenv("ENABLE_NOTES"),
            "notes_workspace": os.getenv("NOTES_WORKSPACE"),
            "tts_api_key": os.getenv("TTS_API_KEY"),
            "tts_base_url": os.getenv("TTS_BASE_URL"),
            "tts_model": os.getenv("TTS_MODEL"),
            "audio_output_dir": os.getenv("AUDIO_OUTPUT_DIR"),
            "ffmpeg_path": os.getenv("FFMPEG_PATH"),
            "tavily_api_key": os.getenv("TAVILY_API_KEY"),
            "serpapi_api_key": os.getenv("SERPAPI_API_KEY"),
        }

        # 处理 NO_PROXY
        no_proxy = os.getenv("NO_PROXY")
        if no_proxy:
            os.environ["NO_PROXY"] = no_proxy
            # 同时设置为小写以兼容
            os.environ["no_proxy"] = no_proxy

        for key, value in env_aliases.items():
            if value is not None:
                raw_values.setdefault(key, value)

        if overrides:
            for key, value in overrides.items():
                if value is not None:
                    raw_values[key] = value

        return cls(**raw_values)

    def resolved_model(self) -> str | None:
        """尽力解析要使用的模型标识符。"""
        return self.llm_model_id
