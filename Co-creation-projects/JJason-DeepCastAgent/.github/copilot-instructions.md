# DeepCast AI Coding Instructions

You are an expert AI agent working on **DeepCast**, an automated podcast generation engine based on the [HelloAgents](https://github.com/datawhalechina/Hello-Agents) framework.

## 🏗 Architecture Overview

### Backend (Python 3.10+ / FastAPI)
- **Entry Point**: [backend/src/main.py](backend/src/main.py) — FastAPI server at `localhost:8000`
- **Core Orchestrator**: [backend/src/agent.py](backend/src/agent.py) — `DeepResearchAgent` coordinates the entire workflow
- **Workflow Pipeline**: `Planning → Research (parallel threads) → Summarization → Reporting → Script → TTS → Audio Synthesis`
- **Service Layer**: [backend/src/services/](backend/src/services/) — decoupled business logic:
  - `planner.py` / `summarizer.py` / `reporter.py` — research phases
  - `script_generator.py` — converts report to dialogue
  - `audio_generator.py` — TTS per dialogue turn
  - `audio_synthesizer.py` — FFmpeg stitching
  - `search.py` — hybrid search via `hello_agents.tools.SearchTool`

### Frontend (Vue 3 / Vite / TypeScript)
- **SSE Streaming**: [frontend/src/services/api.ts](frontend/src/services/api.ts) connects to `/research/stream` via `fetch` + `ReadableStream`
- **Event Types**: `status`, `todo_list`, `task_status`, `search_result`, `summary`, `report`, `script`, `audio_progress`, `done`, `error`, `cancelled`

### Data Flow
```
User Topic → PlanningService (smart_llm) → TodoItems[]
           → [Parallel Workers] SearchTool → SummarizationService (fast_llm)
           → ReportingService (smart_llm) → ScriptGenerationService → AudioGenerationService → PodcastSynthesisService
           → Output: report.md + podcast.mp3
```

## 🛠 Developer Workflows

```bash
# Backend (requires .env configured from env.example)
cd backend && python src/main.py

# Frontend
cd frontend && npm install && npm run dev

# Verification scripts (run from project root)
python backend/scripts/verify_ecnu_llm.py   # Test LLM
python backend/scripts/verify_ecnu_tts.py   # Test TTS
python backend/scripts/verify_ffmpeg.py     # Check FFmpeg
python backend/scripts/verify_search.py     # Test search APIs
```

## 💡 Key Patterns

### LLM Model Selection
- **`smart_llm` (`ecnu-reasoner`)**: For complex reasoning — planning (`todo_agent`), reporting (`report_agent`)
- **`fast_llm` (`ecnu-max`)**: For high-volume tasks — task summarization, script generation
- Configured in [backend/src/config.py](backend/src/config.py) via `SMART_LLM_MODEL` / `FAST_LLM_MODEL`

### Agent Definition Pattern
Agents are created in `DeepResearchAgent.__init__` using `ToolAwareSimpleAgent`:
```python
self.todo_agent = self._create_tool_aware_agent(
    name="研究规划专家",
    system_prompt=todo_planner_system_prompt,  # from prompts.py
    llm=self.smart_llm,
)
```

### Structured Output
- **Models**: [backend/src/models.py](backend/src/models.py) — `SummaryState`, `TodoItem`, `SummaryStateOutput`
- **Prompts**: [backend/src/prompts.py](backend/src/prompts.py) — JSON output instructions embedded in system prompts
- When adding new agent outputs, define Pydantic model + update corresponding prompt's `<输出格式>` section

### Podcast Voices (TTS)
| Role | Voice ID | Character |
|------|----------|-----------|
| Host (夏雨) | `xiayu` | Curious, humorous, audience proxy |
| Guest (李华) | `liwa` | Knowledgeable expert |

Voice mapping in [backend/src/services/audio_generator.py](backend/src/services/audio_generator.py) `_get_voice_for_role()`

### Streaming Events
The `run_stream()` method in `DeepResearchAgent` uses a multi-threaded worker pattern:
- Each `TodoItem` gets its own thread
- Events are pushed to a `Queue` and yielded to the SSE endpoint
- Supports cancellation via `cancel()` / `is_cancelled()` / `CancelledException`

## ⚠️ Common Pitfalls

| Issue | Solution |
|-------|----------|
| FFmpeg errors in synthesis | Set `FFMPEG_PATH` in `.env` (Windows: `C:\ffmpeg\bin\ffmpeg.exe`) |
| Empty search results | Ensure `TAVILY_API_KEY` or `SERP_API_KEY` is configured |
| LLM timeout | Increase `LLM_TIMEOUT` (default 60s) for complex topics |
| Notes not persisting | Check `NOTES_WORKSPACE` path exists and is writable |
| CORS issues | Frontend proxy in `vite.config.ts`; backend allows all origins by default |

## 📁 Output Artifacts
- **Notes**: `backend/output/notes/` — `note_*.md` + `notes_index.json`
- **Audio**: `backend/output/audio/` — individual MP3s + final `podcast_*.mp3`
- Served statically at `/output/...` via FastAPI `StaticFiles`
