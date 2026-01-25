"""状态模型，用于深度研究工作流。"""

import operator
from dataclasses import dataclass, field
from typing import List, Optional

from typing_extensions import Annotated


@dataclass(kw_only=True)
class TodoItem:
    """单个待办任务项。"""

    id: int
    title: str
    intent: str
    query: str
    status: str = field(default="pending")
    summary: Optional[str] = field(default=None)
    sources_summary: Optional[str] = field(default=None)
    notices: list[str] = field(default_factory=list)
    note_id: Optional[str] = field(default=None)
    note_path: Optional[str] = field(default=None)
    stream_token: Optional[str] = field(default=None)


@dataclass(kw_only=True)
class SummaryState:
    research_topic: str = field(default=None)  # 研究主题
    search_query: str = field(default=None)  # 已弃用的占位符
    web_research_results: Annotated[list, operator.add] = field(default_factory=list)
    sources_gathered: Annotated[list, operator.add] = field(default_factory=list)
    research_loop_count: int = field(default=0)  # 研究循环次数
    running_summary: str = field(default=None)  # 传统摘要字段
    todo_items: Annotated[list, operator.add] = field(default_factory=list)  # 待办任务项列表
    structured_report: Optional[str] = field(default=None)  # 结构化报告（JSON 字符串）
    report_note_id: Optional[str] = field(default=None)  # 报告笔记 ID
    report_note_path: Optional[str] = field(default=None)  # 报告笔记路径
    podcast_script: Optional[list] = field(default=None)  # 播客脚本（JSON 字符串）


@dataclass(kw_only=True)
class SummaryStateInput:
    research_topic: str = field(default=None)  # 研究主题


@dataclass(kw_only=True)
class SummaryStateOutput:
    running_summary: str = field(default=None)  # 向后兼容的摘要文本
    report_markdown: Optional[str] = field(default=None)
    todo_items: List[TodoItem] = field(default_factory=list)
    podcast_script: Optional[list] = field(default=None)

