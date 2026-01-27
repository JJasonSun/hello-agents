"""通过 HTTP 暴露 DeepResearchAgent 的 FastAPI 入口点。"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

# Ensure src directory is in sys.path for module imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from pydantic import BaseModel, Field

from agent import DeepResearchAgent
from config import Configuration, SearchAPI

# 添加控制台日志处理程序
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <4}</level> | <cyan>using_function:{function}</cyan> | <cyan>{file}:{line}</cyan> | <level>{message}</level>",
    colorize=True,
)


# 添加错误日志文件处理程序
logger.add(
    sink=sys.stderr,
    level="ERROR",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <4}</level> | <cyan>using_function:{function}</cyan> | <cyan>{file}:{line}</cyan> | <level>{message}</level>",
    colorize=True,
)


class ResearchRequest(BaseModel):
    """触发研究运行的负载。"""

    topic: str = Field(..., description="用户提供的研究主题")
    search_api: SearchAPI | None = Field(
        default=None,
        description="覆盖通过环境变量配置的默认搜索后端",
    )

class PodcastScript(BaseModel):
    """播客脚本内容模型。"""
    script: str = Field(..., description="生成的播客脚本内容")


class ResearchResponse(BaseModel):
    """包含生成报告和结构化任务的 HTTP 响应。"""

    report_markdown: str = Field(
        ..., description="Markdown 格式的研究报告，包含各个部分"
    )
    todo_items: list[dict[str, Any]] = Field(
        default_factory=list,
        description="带有摘要和来源的结构化待办事项",
    )
    podcast_script: PodcastScript | None = Field(
        default=None,
        description="生成的播客脚本内容",
    )


def _mask_secret(value: str | None, visible: int = 4) -> str:
    """在保持前导和尾随字符的同时，掩盖敏感令牌。"""
    if not value:
        return "unset"

    if len(value) <= visible * 2:
        return "*" * len(value)

    return f"{value[:visible]}...{value[-visible:]}"


def _build_config(payload: ResearchRequest) -> Configuration:
    overrides: dict[str, Any] = {}

    if payload.search_api is not None:
        overrides["search_api"] = payload.search_api

    return Configuration.from_env(overrides=overrides)


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。"""
    app = FastAPI(title="DeepCast - 自动播客生成智能体")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 确保输出目录存在
    # 使用绝对路径，基于 backend 根目录
    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(backend_root, "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # 挂载静态文件目录，用于访问生成的音频文件
    app.mount("/output", StaticFiles(directory=output_dir), name="output")

    @app.on_event("startup")
    def log_startup_configuration() -> None:
        """记录启动时的关键配置参数。"""
        config = Configuration.from_env()

        logger.info(
            "DeepResearch configuration loaded: provider=%s model=%s base_url=%s search_api=%s "
            "max_loops=%s fetch_full_page=%s tool_calling=%s strip_thinking=%s api_key=%s",
            config.llm_provider,
            config.resolved_model() or "unset",
            config.llm_base_url or "unset",
            (config.search_api.value if isinstance(config.search_api, SearchAPI) else config.search_api),
            config.max_web_research_loops,
            config.fetch_full_page,
            config.use_tool_calling,
            config.strip_thinking_tokens,
            _mask_secret(config.llm_api_key),
        )

    @app.get("/healthz")
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/research", response_model=ResearchResponse)
    def run_research(payload: ResearchRequest) -> ResearchResponse:
        """
        触发同步研究任务。
        
        执行完整的研究流程，并在 HTTP 响应中一次性返回所有结果。
        """
        try:
            config = _build_config(payload)
            agent = DeepResearchAgent(config=config)
            result = agent.run(payload.topic)
        except ValueError as exc:  # Likely due to unsupported configuration
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # pragma: no cover - defensive guardrail
            raise HTTPException(status_code=500, detail="Research failed") from exc

        todo_payload = [
            {
                "id": item.id,
                "title": item.title,
                "intent": item.intent,
                "query": item.query,
                "status": item.status,
                "summary": item.summary,
                "sources_summary": item.sources_summary,
                "note_id": item.note_id,
                "note_path": item.note_path,
            }
            for item in result.todo_items
        ]

        # 确保 podcast_script 类型正确，Pydantic 模型需要 PodcastScript 实例
        script_content = ""
        if result.podcast_script:
            if isinstance(result.podcast_script, (list, dict)):
                script_content = json.dumps(result.podcast_script, ensure_ascii=False)
            else:
                script_content = str(result.podcast_script)
        
        podcast_resp = PodcastScript(script=script_content)

        return ResearchResponse(
            report_markdown=(result.report_markdown or result.running_summary or ""),
            todo_items=todo_payload,
            podcast_script=podcast_resp,
        )

    @app.post("/research/stream")
    async def stream_research(payload: ResearchRequest, request: Request) -> StreamingResponse:
        """
        触发流式研究任务。
        
        通过 Server-Sent Events (SSE) 实时返回研究进度、日志和部分结果。
        支持客户端断开连接时自动取消后端任务。
        """
        try:
            config = _build_config(payload)
            agent = DeepResearchAgent(config=config)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        async def event_iterator():
            try:
                # 在线程池中运行同步生成器
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    # 将生成器转换为可在线程中运行的迭代
                    gen = agent.run_stream(payload.topic)
                    
                    while True:
                        # 检查客户端是否断开连接
                        if await request.is_disconnected():
                            logger.info("Client disconnected, cancelling research task")
                            agent.cancel()
                            break
                        
                        # 在线程池中获取下一个事件
                        loop = asyncio.get_event_loop()
                        try:
                            event = await asyncio.wait_for(
                                loop.run_in_executor(executor, lambda: next(gen, None)),
                                timeout=1.0
                            )
                        except asyncio.TimeoutError:
                            # 超时时继续检查连接状态
                            continue
                        
                        if event is None:
                            break
                            
                        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                        
                        # 如果是完成或取消事件，退出循环
                        if event.get("type") in ("done", "cancelled", "error"):
                            break
                            
            except Exception as exc:  # pragma: no cover - defensive guardrail
                logger.exception("Streaming research failed")
                error_payload = {"type": "error", "detail": str(exc)}
                yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            event_iterator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
