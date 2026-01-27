"""协调深度研究工作流的编排器。"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from queue import Empty, Queue
from threading import Lock, Thread
from typing import Any, Callable, Iterator

from hello_agents import HelloAgentsLLM, ToolAwareSimpleAgent
from hello_agents.tools import ToolRegistry
from hello_agents.tools.builtin.note_tool import NoteTool

from config import Configuration
from prompts import (
    report_writer_instructions,
    script_writer_instructions,
    task_summarizer_instructions,
    todo_planner_system_prompt,
)
from models import SummaryState, SummaryStateOutput, TodoItem
from services.planner import PlanningService
from services.reporter import ReportingService
from services.script_generator import ScriptGenerationService
from services.audio_generator import AudioGenerationService
from services.audio_synthesizer import PodcastSynthesisService
from services.search import dispatch_search, prepare_research_context
from services.summarizer import SummarizationService
from services.tool_events import ToolCallTracker

logger = logging.getLogger(__name__)


class DeepResearchAgent:
    """使用 HelloAgents 协调基于 TODO 的研究工作流的协调器。"""

    def __init__(self, config: Configuration | None = None) -> None:
        """使用配置和共享工具初始化协调器。"""
        self.config = config or Configuration.from_env()
        self.default_llm = self._init_llm(self.config.llm_model_id)
        self.smart_llm = self._init_llm(self.config.smart_llm_model)
        self.fast_llm = self._init_llm(self.config.fast_llm_model)

        self.note_tool = (
            NoteTool(workspace=self.config.notes_workspace)
            if self.config.enable_notes
            else None
        )
        self.tools_registry: ToolRegistry | None = None
        if self.note_tool:
            registry = ToolRegistry()
            registry.register_tool(self.note_tool)
            self.tools_registry = registry

        self._tool_tracker = ToolCallTracker(
            self.config.notes_workspace if self.config.enable_notes else None
        )
        self._tool_event_sink_enabled = False
        self._state_lock = Lock()

        self.todo_agent = self._create_tool_aware_agent(
            name="研究规划专家",
            system_prompt=todo_planner_system_prompt.strip(),
            llm=self.smart_llm,
        )
        self.report_agent = self._create_tool_aware_agent(
            name="报告撰写专家",
            system_prompt=report_writer_instructions.strip(),
            llm=self.smart_llm,
        )
        self.script_agent = self._create_tool_aware_agent(
            name="脚本策划专家",
            system_prompt=script_writer_instructions.strip(),
            llm=self.default_llm,
        )

        self._summarizer_factory: Callable[[], ToolAwareSimpleAgent] = lambda: self._create_tool_aware_agent(  # noqa: E501
            name="任务总结专家",
            system_prompt=task_summarizer_instructions.strip(),
            llm=self.fast_llm,
        )

        self.planner = PlanningService(self.todo_agent, self.config)
        self.summarizer = SummarizationService(self._summarizer_factory, self.config)
        self.reporting = ReportingService(self.report_agent, self.config)
        self.script_generator = ScriptGenerationService(self.script_agent, self.config)
        self.audio_generator = AudioGenerationService(self.config)

        self.podcast_synthesizer = PodcastSynthesisService(self.config)
        self._last_search_notices: list[str] = []

    # ------------------------------------------------------------------
    # 公共 API
    # ------------------------------------------------------------------
    def _init_llm(self, model_id_override: str | None = None) -> HelloAgentsLLM:
        """根据配置偏好实例化 HelloAgentsLLM。"""
        llm_kwargs: dict[str, Any] = {"temperature": 0.0}

        model_id = model_id_override or self.config.llm_model_id
        if model_id:
            llm_kwargs["model"] = model_id

        provider = (self.config.llm_provider or "").strip()
        if provider:
            llm_kwargs["provider"] = provider

        if self.config.llm_base_url:
            llm_kwargs["base_url"] = self.config.llm_base_url
        if self.config.llm_api_key:
            llm_kwargs["api_key"] = self.config.llm_api_key

        return HelloAgentsLLM(**llm_kwargs)

    def _create_tool_aware_agent(self, *, name: str, system_prompt: str, llm: HelloAgentsLLM) -> ToolAwareSimpleAgent:
        """实例化共享工具注册表和跟踪器的 ToolAwareSimpleAgent。"""
        return ToolAwareSimpleAgent(
            name=name,
            llm=llm,
            system_prompt=system_prompt,
            enable_tool_calling=self.tools_registry is not None,
            tool_registry=self.tools_registry,
            tool_call_listener=self._tool_tracker.record,
        )

    def _set_tool_event_sink(self, sink: Callable[[dict[str, Any]], None] | None) -> None:
        """启用或禁用立即工具事件回调。"""
        self._tool_event_sink_enabled = sink is not None
        self._tool_tracker.set_event_sink(sink)

    def run(self, topic: str) -> SummaryStateOutput:
        """
        执行研究工作流并返回最终报告（同步模式）。
        
        此方法按顺序执行以下步骤：
        1. 初始化状态和规划任务。
        2. 串行执行每个任务（搜索 + 总结）。
        3. 生成最终报告。
        4. 生成播客脚本。
        5. 生成音频文件并合成播客。
        """
        state = SummaryState(research_topic=topic)
        state.todo_items = self.planner.plan_todo_list(state)
        self._drain_tool_events(state)

        if not state.todo_items:
            logger.info("No TODO items generated; falling back to single task")
            state.todo_items = [self.planner.create_fallback_task(state)]

        for task in state.todo_items:
            for _ in self._execute_task(state, task, emit_stream=False):
                pass

        report = self.reporting.generate_report(state)
        self._drain_tool_events(state)
        state.structured_report = report
        state.running_summary = report
        self._persist_final_report(state, report)

        script = self.script_generator.generate_script(state)
        self._drain_tool_events(state)
        state.podcast_script = script

        # 为脚本生成音频
        task_id = f"task_{state.report_note_id}" if state.report_note_id else "task_default"
        audio_files = self.audio_generator.generate_audio(script, task_id)

        # 合成播客
        podcast_file = self.podcast_synthesizer.synthesize_podcast(audio_files, task_id)
        
        return SummaryStateOutput(
            running_summary=report,
            report_markdown=report,
            todo_items=state.todo_items,
            podcast_script=script,
        )

    def run_stream(self, topic: str) -> Iterator[dict[str, Any]]:
        """
        执行研究工作流并产生增量进度事件（流式模式）。
        
        此方法使用多线程并行执行研究任务，并通过生成器实时返回进度。
        主要步骤：
        1. 初始化并规划任务。
        2. 为每个任务启动一个工作线程进行并行处理。
        3. 实时流式传输任务状态、搜索结果和部分总结。
        4. 所有任务完成后，生成并流式传输最终报告。
        5. 生成并流式传输播客脚本和音频合成进度。
        """
        state = SummaryState(research_topic=topic)
        logger.debug("Starting streaming research: topic=%s", topic)
        yield {"type": "status", "message": "初始化研究流程"}

        state.todo_items = self.planner.plan_todo_list(state)
        for event in self._drain_tool_events(state, step=0):
            yield event
        if not state.todo_items:
            state.todo_items = [self.planner.create_fallback_task(state)]

        channel_map: dict[int, dict[str, Any]] = {}
        for index, task in enumerate(state.todo_items, start=1):
            token = f"task_{task.id}"
            task.stream_token = token
            channel_map[task.id] = {"step": index, "token": token}

        # 确保在开始多线程任务前，显式发送 todo_list 事件
        # 使用 list comprehension 确保 task 被正确序列化
        serialized_tasks = [self._serialize_task(t) for t in state.todo_items]
        logger.info(f"Emitting todo_list event with {len(serialized_tasks)} tasks")
        yield {
            "type": "todo_list",
            "tasks": serialized_tasks,
            "step": 0,
        }

        event_queue: Queue[dict[str, Any]] = Queue()

        def enqueue(
            event: dict[str, Any],
            *,
            task: TodoItem | None = None,
            step_override: int | None = None,
        ) -> None:
            payload = dict(event)
            target_task_id = payload.get("task_id")
            if task is not None:
                target_task_id = task.id
                payload["task_id"] = task.id

            channel = channel_map.get(target_task_id) if target_task_id is not None else None
            if channel:
                payload.setdefault("step", channel["step"])
                payload["stream_token"] = channel["token"]
            if step_override is not None:
                payload["step"] = step_override
            event_queue.put(payload)

        def tool_event_sink(event: dict[str, Any]) -> None:
            enqueue(event)

        self._set_tool_event_sink(tool_event_sink)

        threads: list[Thread] = []

        def worker(task: TodoItem, step: int) -> None:
            try:
                enqueue(
                    {
                        "type": "task_status",
                        "task_id": task.id,
                        "status": "in_progress",
                        "title": task.title,
                        "intent": task.intent,
                        "query": task.query,
                        "note_id": task.note_id,
                        "note_path": task.note_path,
                    },
                    task=task,
                )

                for event in self._execute_task(state, task, emit_stream=True, step=step):
                    enqueue(event, task=task)
            except Exception as exc:  # pragma: no cover - defensive guardrail
                logger.exception("Task execution failed", exc_info=exc)
                enqueue(
                    {
                        "type": "task_status",
                        "task_id": task.id,
                        "status": "failed",
                        "detail": str(exc),
                        "title": task.title,
                        "intent": task.intent,
                        "query": task.query,
                        "note_id": task.note_id,
                        "note_path": task.note_path,
                    },
                    task=task,
                )
            finally:
                enqueue({"type": "__task_done__", "task_id": task.id})

        for task in state.todo_items:
            step = channel_map.get(task.id, {}).get("step", 0)
            thread = Thread(target=worker, args=(task, step), daemon=True)
            threads.append(thread)
            thread.start()

        active_workers = len(state.todo_items)
        finished_workers = 0

        try:
            while finished_workers < active_workers:
                event = event_queue.get()
                if event.get("type") == "__task_done__":
                    finished_workers += 1
                    continue
                yield event

            while True:
                try:
                    event = event_queue.get_nowait()
                except Empty:
                    break
                if event.get("type") != "__task_done__":
                    yield event
        finally:
            self._set_tool_event_sink(None)
            for thread in threads:
                thread.join()

        yield {
            "type": "stage_change",
            "stage": "report",
            "message": "所有研究任务已完成，正在撰写深度研究报告...",
        }
        yield {"type": "log", "message": f"🧠 正在调用 {self.config.smart_llm_model} 模型撰写深度报告..."}
        report = self.reporting.generate_report(state)
        final_step = len(state.todo_items) + 1
        for event in self._drain_tool_events(state, step=final_step):
            yield event
        state.structured_report = report
        state.running_summary = report
        yield {"type": "log", "message": f"✓ 报告撰写完成，共 {len(report)} 字符"}

        note_event = self._persist_final_report(state, report)
        if note_event:
            yield note_event

        yield {
            "type": "final_report",
            "report": report,
            "note_id": state.report_note_id,
            "note_path": state.report_note_path,
        }

        yield {
            "type": "stage_change",
            "stage": "script",
            "message": "正在将研究报告转化为双人对谈播客脚本...",
        }
        yield {"type": "log", "message": f"🧠 正在调用 {self.config.fast_llm_model} 模型生成播客脚本..."}
        yield {"type": "log", "message": "脚本策划专家正在创作 Host (Xiayu) 与 Guest (Liwa) 的对话..."}
        script = self.script_generator.generate_script(state)
        for event in self._drain_tool_events(state):
            yield event
        state.podcast_script = script
        
        script_turns = len(script) if script else 0
        yield {"type": "log", "message": f"✓ 脚本生成完成，共 {script_turns} 轮对话"}
        
        if script_turns == 0:
            yield {"type": "log", "message": "⚠️ 警告：脚本为空，可能是解析失败，请检查后端日志"}
        
        yield {
            "type": "podcast_script",
            "script": script,
            "turns": script_turns,
        }

        yield {
            "type": "stage_change",
            "stage": "audio",
            "message": "正在调用 TTS 语音引擎生成音频...",
        }
        task_id = f"task_{state.report_note_id}" if state.report_note_id else "task_default"
        
        # 使用队列实现实时流式音频进度
        audio_event_queue: Queue[dict[str, Any]] = Queue()
        audio_result: list = []
        audio_error: list = []
        
        def audio_progress_callback(current, total, role, preview):
            """将进度事件放入队列以实现实时更新"""
            audio_event_queue.put({
                "type": "audio_progress",
                "current": current,
                "total": total,
                "role": role,
                "preview": preview,
                "message": f"[TTS {current}/{total}] 正在为 {role} 生成语音: {preview}",
            })
        
        def run_audio_generation():
            """在单独线程中运行音频生成"""
            try:
                files = self.audio_generator.generate_audio(script, task_id, audio_progress_callback)
                audio_result.append(files)
            except Exception as e:
                audio_error.append(str(e))
            finally:
                audio_event_queue.put({"type": "_audio_done"})
        
        yield {"type": "log", "message": f"准备为 {script_turns} 段对话生成语音..."}
        
        yield {
            "type": "audio_start",
            "total": script_turns,
            "message": f"开始生成 {script_turns} 段语音",
        }
        
        # 在独立线程中启动音频生成
        audio_thread = Thread(target=run_audio_generation, daemon=True)
        audio_thread.start()
        
        # 实时流式传输进度事件
        while True:
            try:
                event = audio_event_queue.get(timeout=0.1)
                if event.get("type") == "_audio_done":
                    break
                yield event
                # 每个片段完成后发送成功日志
                if event.get("type") == "audio_progress":
                    yield {
                        "type": "log", 
                        "message": f"[TTS {event['current']}/{event['total']}] ✓ {event['role']} 语音生成成功"
                    }
            except Empty:
                continue
        
        audio_thread.join(timeout=5.0)
        
        audio_files = audio_result[0] if audio_result else []
        audio_count = len(audio_files) if audio_files else 0
        
        if audio_error:
            yield {"type": "log", "message": f"⚠️ 音频生成出错: {audio_error[0]}"}
        
        yield {"type": "log", "message": f"语音生成完成，成功 {audio_count}/{script_turns} 段"}
        
        yield {
            "type": "audio_generated",
            "files": audio_files,
            "count": audio_count,
        }

        yield {
            "type": "stage_change",
            "stage": "synthesis",
            "message": "正在合成完整播客音频文件...",
        }
        yield {"type": "log", "message": "使用 FFmpeg 拼接所有语音片段..."}
        podcast_file = self.podcast_synthesizer.synthesize_podcast(audio_files, task_id)
        if podcast_file:
            yield {
                "type": "podcast_ready",
                "file": podcast_file,
            }

        yield {"type": "done"}

    # ------------------------------------------------------------------
    # 执行助手
    # ------------------------------------------------------------------
    def _execute_task(
        self,
        state: SummaryState,
        task: TodoItem,
        *,
        emit_stream: bool,
        step: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        """
        对单个任务运行搜索 + 总结逻辑。
        
        Args:
            state: 全局研究状态。
            task: 当前要执行的任务项。
            emit_stream: 是否产生流式事件（True 用于 run_stream，False 用于 run）。
            step: 当前步骤编号（仅用于流式事件）。
            
        Returns:
            事件字典的迭代器（即使 emit_stream=False，也可能产生少量内部事件，通常被忽略）。
        """
        task.status = "in_progress"

        search_result, notices, answer_text, backend = dispatch_search(
            task.query,
            self.config,
            state.research_loop_count,
        )
        self._last_search_notices = notices
        task.notices = notices

        if emit_stream:
            for event in self._drain_tool_events(state, step=step):
                yield event
        else:
            self._drain_tool_events(state)

        if notices and emit_stream:
            for notice in notices:
                if notice:
                    yield {
                        "type": "status",
                        "message": notice,
                        "task_id": task.id,
                        "step": step,
                    }

        if not search_result or not search_result.get("results"):
            task.status = "skipped"
            if emit_stream:
                for event in self._drain_tool_events(state, step=step):
                    yield event
                yield {
                    "type": "task_status",
                    "task_id": task.id,
                    "status": "skipped",
                    "title": task.title,
                    "intent": task.intent,
                    "note_id": task.note_id,
                    "note_path": task.note_path,
                    "step": step,
                }
            else:
                self._drain_tool_events(state)
            return
        else:
            if not emit_stream:
                self._drain_tool_events(state)

        sources_summary, context = prepare_research_context(
            search_result,
            answer_text,
            self.config,
        )

        task.sources_summary = sources_summary

        with self._state_lock:
            state.web_research_results.append(context)
            state.sources_gathered.append(sources_summary)
            state.research_loop_count += 1

        summary_text: str | None = None

        if emit_stream:
            for event in self._drain_tool_events(state, step=step):
                yield event
            yield {
                "type": "sources",
                "task_id": task.id,
                "latest_sources": sources_summary,
                "raw_context": context,
                "step": step,
                "backend": backend,
                "note_id": task.note_id,
                "note_path": task.note_path,
            }

            summary_stream, summary_getter = self.summarizer.stream_task_summary(state, task, context)
            try:
                for event in self._drain_tool_events(state, step=step):
                    yield event
                for chunk in summary_stream:
                    if chunk:
                        yield {
                            "type": "task_summary_chunk",
                            "task_id": task.id,
                            "content": chunk,
                            "note_id": task.note_id,
                            "step": step,
                        }
                    for event in self._drain_tool_events(state, step=step):
                        yield event
            finally:
                summary_text = summary_getter()
        else:
            summary_text = self.summarizer.summarize_task(state, task, context)
            self._drain_tool_events(state)

        task.summary = summary_text.strip() if summary_text else "暂无可用信息"
        task.status = "completed"

        if emit_stream:
            for event in self._drain_tool_events(state, step=step):
                yield event
            yield {
                "type": "task_status",
                "task_id": task.id,
                "status": "completed",
                "title": task.title,
                "intent": task.intent,
                "summary": task.summary,
                "sources_summary": task.sources_summary,
                "note_id": task.note_id,
                "note_path": task.note_path,
                "step": step,
            }
        else:
            self._drain_tool_events(state)

    def _drain_tool_events(
        self,
        state: SummaryState,
        *,
        step: int | None = None,
    ) -> list[dict[str, Any]]:
        """共享工具调用跟踪器的代理。"""
        events = self._tool_tracker.drain(state, step=step)
        if self._tool_event_sink_enabled:
            return []
        return events

    @property
    def _tool_call_events(self) -> list[dict[str, Any]]:
        """为旧版集成暴露记录的工具事件。"""
        return self._tool_tracker.as_dicts()

    def _serialize_task(self, task: TodoItem) -> dict[str, Any]:
        """将任务数据类转换为前端可序列化的字典。"""
        return {
            "id": task.id,
            "title": task.title,
            "intent": task.intent,
            "query": task.query,
            "status": task.status,
            "summary": task.summary,
            "sources_summary": task.sources_summary,
            "note_id": task.note_id,
            "note_path": task.note_path,
            "stream_token": task.stream_token,
        }

    def _persist_final_report(self, state: SummaryState, report: str) -> dict[str, Any] | None:
        if not self.note_tool or not report or not report.strip():
            return None

        note_title = f"研究报告：{state.research_topic}".strip() or "研究报告"
        tags = ["deep_research", "report"]
        content = report.strip()

        note_id = self._find_existing_report_note_id(state)
        response = ""

        if note_id:
            response = self.note_tool.run(
                {
                    "action": "update",
                    "note_id": note_id,
                    "title": note_title,
                    "note_type": "conclusion",
                    "tags": tags,
                    "content": content,
                }
            )
            if response.startswith("❌"):
                note_id = None

        if not note_id:
            response = self.note_tool.run(
                {
                    "action": "create",
                    "title": note_title,
                    "note_type": "conclusion",
                    "tags": tags,
                    "content": content,
                }
            )
            note_id = self._extract_note_id_from_text(response)

        if not note_id:
            return None

        state.report_note_id = note_id
        if self.config.notes_workspace:
            note_path = Path(self.config.notes_workspace) / f"{note_id}.md"
            state.report_note_path = str(note_path)
        else:
            note_path = None

        payload = {
            "type": "report_note",
            "note_id": note_id,
            "title": note_title,
            "content": content,
        }
        if note_path:
            payload["note_path"] = str(note_path)

        return payload

    def _find_existing_report_note_id(self, state: SummaryState) -> str | None:
        """
        查找与研究主题相关的现有报告笔记 ID。
        
        此方法检查当前状态是否已关联报告笔记 ID。如果没有，它会遍历已记录的工具事件，
        查找最近创建或更新的结论类型笔记，标题中包含研究主题的报告。
        
        Args:
            state: 当前研究状态，包含研究主题和已记录的工具事件。
            
        Returns:
            与研究主题相关的现有报告笔记 ID（如果存在），否则为 None。
        """
        if state.report_note_id:
            return state.report_note_id

        for event in reversed(self._tool_tracker.as_dicts()):
            if event.get("tool") != "note":
                continue

            parameters = event.get("parsed_parameters") or {}
            if not isinstance(parameters, dict):
                continue

            action = parameters.get("action")
            if action not in {"create", "update"}:
                continue

            note_type = parameters.get("note_type")
            if note_type != "conclusion":
                title = parameters.get("title")
                if not (isinstance(title, str) and title.startswith("研究报告")):
                    continue

            note_id = parameters.get("note_id")
            if not note_id:
                note_id = self._tool_tracker._extract_note_id(event.get("result", ""))  # type: ignore[attr-defined]

            if note_id:
                return note_id

        return None

    @staticmethod
    def _extract_note_id_from_text(response: str) -> str | None:
        if not response:
            return None

        match = re.search(r"ID:\s*([^\n]+)", response)
        if not match:
            return None

        return match.group(1).strip()


def run_deep_research(topic: str, config: Configuration | None = None) -> SummaryStateOutput:
    """镜像基于类的 API 的便捷函数。"""
    agent = DeepResearchAgent(config=config)
    return agent.run(topic)
