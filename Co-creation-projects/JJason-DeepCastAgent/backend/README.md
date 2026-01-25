# DeepCast

## 📝 项目简介

**DeepCast** 是一个自动化播客生成智能体，具备深度全网调研能力。它不仅能够对用户给定的主题进行全网深度调研并生成专业报告，还能进一步将研究成果转化为生动的**双人对谈播客（Podcast）**。

DeepCast 旨在解决信息获取的"枯燥"问题，将严肃的深度研究报告转化为易于消化的音频内容，让用户可以在通勤、运动等场景下高效获取知识。

## ✨ 核心功能

- [x] **深度全网调研**：自动拆解问题，多轮搜索（Hybrid Search），生成结构化深度报告。
- [x] **自动化脚本生成**：将研究报告改编为 Host (Xiayu) 与 Guest (Liwa) 的对谈脚本。
- [x] **高品质语音合成**：基于 ECNU-TTS 生成逼真的双人对话音频。
- [x] **一键播客生成**：自动合成最终 MP3 文件，即刻收听。

## 🛠️ 技术栈

- **框架**: [HelloAgents](https://github.com/datawhalechina/Hello-Agents)
- **后端**: FastAPI, Python 3.10+
- **模型支持**:
    - 推理/脚本: `ecnu-max`, `ecnu-reasoner`
    - 语音: `ecnu-tts`
- **搜索服务**: 
    - 混合搜索 (Hybrid Search): Tavily + SerpApi (Google)
    - 备用方案: DuckDuckGo
- **音频处理**: Pydub, FFmpeg

## 🚀 快速开始

### 1. 环境准备

- Python 3.10+
- `uv` 包管理器 (推荐)
- **FFmpeg**: 必须安装并配置到系统 PATH，或在配置中指定路径。

### 2. 安装依赖

```bash
cd backend
uv sync
# 或者使用 pip
# pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `env.example` 为 `.env` 并填入必要的配置：

```bash
cp env.example .env
```

**关键配置项**：

- **LLM**:
    ```env
    LLM_PROVIDER=custom
    LLM_MODEL_ID=ecnu-max
    LLM_API_KEY=your_key
    LLM_BASE_URL=https://chat.ecnu.edu.cn/open/api/v1
    ```

- **TTS**:
    ```env
    TTS_API_KEY=your_key
    TTS_BASE_URL=https://chat.ecnu.edu.cn/open/api/v1/audio/speech
    TTS_MODEL=ecnu-tts
    ```

- **搜索 (推荐配置)**:
    ```env
    SEARCH_API=hybrid
    TAVILY_API_KEY=your_tavily_key
    SERPAPI_API_KEY=your_serpapi_key
    ```

- **音频工具**:
    ```env
    # 如果 ffmpeg 不在系统 PATH 中，请指定绝对路径
    FFMPEG_PATH=C:\ffmpeg\bin\ffmpeg.exe
    ```

### 4. 运行项目

```bash
uv run src/main.py
```

## 🧪 验证脚本

项目包含一系列测试脚本，用于验证各组件配置是否正确：

- `tests/verify_ffmpeg.py`: 检查 FFmpeg 是否可用。
- `tests/verify_search.py`: 测试混合搜索（Tavily/SerpApi）是否连通。
- `tests/verify_ecnu_tts.py`: 测试 TTS 语音生成服务。

## 🤝 贡献指南

欢迎提出 Issue 和 Pull Request！

## 📄 许可证

MIT License
