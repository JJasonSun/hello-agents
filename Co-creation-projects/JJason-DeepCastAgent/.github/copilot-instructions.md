# DeepCast AI Coding Instructions

You are an expert AI agent working on **DeepCast**, an automated podcast generation engine based on the [HelloAgents](https://github.com/datawhalechina/Hello-Agents) framework.

## 🏗 Big Picture Architecture

- **Backend (Python/FastAPI)**: Orchestrates the research-to-podcast workflow.
  - **Core Agent (`DeepResearchAgent`)**: Found in [backend/src/agent.py](backend/src/agent.py). It coordinates multiple specialized agents.
  - **Workflow**: `Planning` -> `Research (Loop)` -> `Summarization` -> `Reporting` -> `Scripting` -> `TTS Generation` -> `Synthesis`.
  - **Services**: Decoupled logic in [backend/src/services/](backend/src/services/). Key integrations: Hybrid Search (Tavily + SerpApi), ECNU-TTS.
  - **Storage**: JSON/MD notes in `backend/output/notes/`, MP3s in `backend/output/audio/`.
- **Frontend (Vue 3/Vite/TypeScript)**: Real-time UI for monitoring progress and playing output.
  - **Streaming**: Uses SSE via `fetch` at `/research/stream` to receive state updates.

## 🛠 Critical Developer Workflows

- **Backend Startup**: 
  - Ensure `.env` is configured correctly (refer to [backend/env.example](backend/env.example)).
  - Run: `cd backend && python src/main.py` (Default: `http://localhost:8000`).
- **Frontend Startup**:
  - Run: `cd frontend && npm install && npm run dev` (Default: `http://localhost:5173`).
- **Environment Verification**:
  - Use scripts in [backend/scripts/](backend/scripts/) to verify dependencies:
    - `python backend/scripts/verify_ecnu_llm.py`: Test LLM access.
    - `python backend/scripts/verify_ecnu_tts.py`: Test TTS service.
    - `python backend/scripts/verify_ffmpeg.py`: Check FFmpeg installation (required for audio stitching).

## 💡 Key Patterns & Conventions

- **Agent Experts**: Defined in `DeepResearchAgent.__init__` using prompts from [backend/src/prompts.py](backend/src/prompts.py).
  - Use `smart_llm` (`ecnu-reasoner`) for planning and reporting.
  - Use `fast_llm` (`ecnu-max`) for search summarization and script generation.
- **Structured Output**: 
  - Heavily relies on Pydantic models in [backend/src/models.py](backend/src/models.py).
  - When modifying agent responses, ensure the parser in [backend/src/agent.py](backend/src/agent.py) matches the new schema.
- **Podcast Roles**: 
  - Host: `xiayu` (Female/Professional). 
  - Guest: `liwa` (Male/Knowledgeable).
  - Voice assignments are handled in [backend/src/services/audio_generator.py](backend/src/services/audio_generator.py).
- **Tooling**: Uses `HelloAgents`' `NoteTool` for persistence. All research finding should be logged as notes.

## ⚠️ Common Pitfalls

- **FFmpeg**: Errors in `audio_synthesizer.py` often stem from missing or incorrectly configured FFmpeg path in `.env`.
- **API Keys**: Ensure `TAVILY_API_KEY` or `SERP_API_KEY` is present; otherwise, research will yield no results.
- **CORS**: The FastAPI app in `main.py` has CORS enabled for all origins, but changing this requires updating `frontend/vite.config.ts`.
