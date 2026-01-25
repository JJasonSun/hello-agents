# DeepCast

## 📝 项目简介

**DeepCast** 是一个自动化播客生成智能体，具备深度全网调研能力。它不仅能够对用户给定的主题进行全网深度调研并生成专业报告，还能进一步将研究成果转化为生动的**双人对谈播客（Podcast）**。

DeepCast 旨在解决信息获取的"枯燥"问题，将严肃的深度研究报告转化为易于消化的音频内容，让用户可以在通勤、运动等场景下高效获取知识。

## ✨ 核心功能

- [x] **深度全网调研**：自动拆解问题，多轮搜索，生成结构化深度报告。
- [ ] **自动化脚本生成**：将研究报告改编为 Host (主持人) 与 Guest (专家) 的对谈脚本。
- [ ] **高品质语音合成**：基于 ECNU-TTS 生成逼真的双人对话音频。
- [ ] **一键播客生成**：自动合成最终 MP3 文件，即刻收听。

## 🛠️ 技术栈

- **框架**: [HelloAgents](https://github.com/datawhalechina/Hello-Agents)
- **后端**: FastAPI, Python 3.10+
- **模型支持**:
    - 推理/脚本: `ecnu-max`, `ecnu-reasoner`
    - 语音: `ecnu-tts`
- **工具**: Tavily (搜索), Pydub (音频处理)

## 🚀 快速开始

### 环境要求

- Python 3.10+
- `uv` 包管理器 (推荐) 或 `pip`

### 安装依赖

```bash
cd backend
uv sync
```

### 配置 API 密钥

复制 `.env.example` 到 `.env` 并填入必要的 API Key：

```bash
cp .env.example .env
```

需要配置：
- `LLM_PROVIDER`: 如 `openai` (兼容接口)
- `LLM_API_KEY`: 你的模型 API Key
- `SEARCH_API_KEY`: 搜索服务 Key (如 Tavily)

### 运行项目

```bash
python src/main.py
```

## 🤝 贡献指南

欢迎提出 Issue 和 Pull Request！

## 📄 许可证

MIT License
