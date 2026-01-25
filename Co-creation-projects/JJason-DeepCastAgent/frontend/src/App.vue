<template>
  <div class="deepcast-container" :class="currentView">
    <div class="background-gradient"></div>

    <!-- 1. Setup View: 输入主题与配置 -->
    <transition name="fade" mode="out-in">
      <section v-if="currentView === 'setup'" class="view-setup" key="setup">
        <header class="brand-header">
          <div class="logo-icon">🎙️</div>
          <h1>DeepCast</h1>
          <p class="tagline">将深度研究转化为引人入胜的播客。</p>
        </header>

        <form @submit.prevent="startProduction" class="setup-form">
          <div class="input-group">
            <label>播客主题</label>
            <textarea 
              v-model="form.topic" 
              placeholder="今天我们聊点什么？（例如：AI Agent 的未来）"
              rows="3"
              required
              @keydown.enter.prevent="startProduction"
            ></textarea>
          </div>

          <div class="settings-row">
            <div class="setting-item">
              <label>搜索引擎</label>
              <div class="select-wrapper">
                <select v-model="form.searchApi">
                  <option value="hybrid">混合搜索 (Tavily + SerpApi)</option>
                  <option value="tavily">仅 Tavily</option>
                  <option value="serpapi">仅 SerpApi</option>
                </select>
                <span class="select-arrow">▼</span>
              </div>
            </div>
          </div>

          <button type="submit" class="cta-button" :disabled="!form.topic.trim()">
            <span>开始制作播客</span>
            <span class="icon">✨</span>
          </button>
        </form>
      </section>

      <!-- 2. Production View: 制作进度监控 -->
      <section v-else-if="currentView === 'producing'" class="view-production" key="production">
        <div class="production-content">
          <header class="production-header">
            <h2>正在制作您的播客</h2>
            <button class="cancel-btn" @click="cancelProduction">取消</button>
          </header>

          <div class="stage-monitor">
            <div class="stage-step" :class="{ active: productionStage === 'research', completed: isStageCompleted('research') }">
              <div class="step-icon">🔍</div>
              <div class="step-label">深度研究</div>
            </div>
            <div class="stage-line"></div>
            <div class="stage-step" :class="{ active: productionStage === 'script', completed: isStageCompleted('script') }">
              <div class="step-icon">📝</div>
              <div class="step-label">剧本创作</div>
            </div>
            <div class="stage-line"></div>
            <div class="stage-step" :class="{ active: productionStage === 'audio', completed: isStageCompleted('audio') }">
              <div class="step-icon">🎧</div>
              <div class="step-label">音频合成</div>
            </div>
          </div>

          <div class="terminal-log" v-if="logs.length > 0">
            <div class="log-content" ref="logContainer">
              <div v-for="(log, i) in logs" :key="i" class="log-entry">
                <span class="log-time">{{ log.time }}</span>
                <span class="log-msg">{{ log.message }}</span>
              </div>
            </div>
          </div>

          <div class="todo-list-container" v-if="todoList.length > 0">
            <h3>📋 研究任务清单</h3>
            <div class="todo-items">
              <div 
                v-for="task in todoList" 
                :key="task.id" 
                class="todo-item" 
                :class="task.status"
              >
                <div class="task-status-icon">
                  <span v-if="task.status === 'pending'">⏳</span>
                  <span v-else-if="task.status === 'in_progress'">🔄</span>
                  <span v-else-if="task.status === 'completed'">✅</span>
                  <span v-else-if="task.status === 'skipped'">⏭️</span>
                  <span v-else-if="task.status === 'failed'">❌</span>
                </div>
                <div class="task-content">
                  <div class="task-header">
                    <span class="task-title">{{ task.title }}</span>
                    <span class="task-intent">{{ task.intent }}</span>
                  </div>
                  <div class="task-summary" v-if="task.summary" v-html="md.render(task.summary)"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 3. Player View: 播放器与脚本 -->
      <section v-else-if="currentView === 'player'" class="view-player" key="player">
        <div class="player-layout">
          <!-- Left: Player Control -->
          <div class="player-sidebar">
            <button class="back-home-btn" @click="resetApp">
              ← 制作新播客
            </button>
            
            <div class="album-art">
              <div class="vinyl-record" :class="{ spinning: isPlaying }">
                <div class="vinyl-label">DC</div>
              </div>
            </div>

            <div class="track-info">
              <h3>{{ form.topic }}</h3>
              <p>DeepCast 原创播客</p>
            </div>

            <div class="audio-controls">
              <audio 
                ref="audioPlayer" 
                :src="audioUrl" 
                @timeupdate="onTimeUpdate"
                @ended="isPlaying = false"
                @play="isPlaying = true"
                @pause="isPlaying = false"
              ></audio>
              
              <div class="control-buttons">
                <button class="play-btn" @click="togglePlay">
                  {{ isPlaying ? '⏸' : '▶' }}
                </button>
                <a :href="audioUrl" download class="download-btn" title="下载 MP3">
                  ⬇
                </a>
              </div>
              
              <div class="progress-bar-wrapper" @click="seekAudio">
                <div class="progress-bar-bg">
                  <div class="progress-bar-fill" :style="{ width: progressPercent + '%' }"></div>
                </div>
                <div class="time-display">{{ formatTime(currentTime) }} / {{ formatTime(duration) }}</div>
              </div>
            </div>

            <div class="report-toggle">
              <button @click="showReport = !showReport">
                {{ showReport ? '隐藏深度研究报告' : '查看深度研究报告' }}
              </button>
            </div>
          </div>

          <!-- Right: Script / Report -->
          <div class="content-main">
            <div v-if="!showReport" class="script-chat">
              <div 
                v-for="(line, idx) in podcastScript" 
                :key="idx" 
                class="chat-bubble"
                :class="line.role.toLowerCase()"
              >
                <div class="avatar">{{ line.role[0] }}</div>
                <div class="bubble-content">
                  <div class="speaker-name">{{ line.role }}</div>
                  <p>{{ line.content }}</p>
                </div>
              </div>
            </div>

            <div v-else class="markdown-report">
              <div class="report-content" v-html="md.render(reportMarkdown)"></div>
            </div>
          </div>
        </div>
      </section>
    </transition>
  </div>
</template>

<script lang="ts" setup>
import { reactive, ref, computed, nextTick, watch } from "vue";
import { runResearchStream, type ResearchStreamEvent } from "./services/api";

// --- Types ---
type ViewState = "setup" | "producing" | "player";
type ProductionStage = "research" | "script" | "audio" | "done";

interface LogEntry {
  time: string;
  message: string;
}

interface PodcastMessage {
  role: string;
  content: string;
}

// --- State ---
const currentView = ref<ViewState>("setup");
const productionStage = ref<ProductionStage>("research");
const form = reactive({
  topic: "",
  searchApi: "hybrid"
});

const logs = ref<LogEntry[]>([]);
const isPlaying = ref(false);
const currentTime = ref(0);
const duration = ref(0);
const progressPercent = computed(() => (duration.value ? (currentTime.value / duration.value) * 100 : 0));
const showReport = ref(false);

// Research Progress State
const totalTasks = ref(0);
const completedTasks = ref(0);
const todoList = ref<any[]>([]); // Store the full todo list
const researchProgress = computed(() => {
  if (totalTasks.value === 0) return "";
  return `(${completedTasks.value}/${totalTasks.value})`;
});

// Data
const podcastScript = ref<PodcastMessage[]>([]);
const reportMarkdown = ref("");
const audioUrl = ref("");
const currentTask = ref<any>(null); // 简化的任务状态

// Refs
const audioPlayer = ref<HTMLAudioElement | null>(null);
const logContainer = ref<HTMLElement | null>(null);
let abortController: AbortController | null = null;

// --- Computed ---

// --- Methods ---

function isStageCompleted(stage: ProductionStage): boolean {
  const stages: ProductionStage[] = ["research", "script", "audio", "done"];
  return stages.indexOf(productionStage.value) > stages.indexOf(stage);
}

function addLog(message: string) {
  const time = new Date().toLocaleTimeString([], { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
  logs.value.push({ time, message });
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight;
    }
  });
}

async function startProduction() {
  if (!form.topic.trim()) return;

  currentView.value = "producing";
  productionStage.value = "research";
  logs.value = [];
  podcastScript.value = [];
  reportMarkdown.value = "";
  audioUrl.value = "";
  currentTask.value = null;
  todoList.value = [];
  totalTasks.value = 0;
  completedTasks.value = 0;

  abortController = new AbortController();

  addLog("🚀 启动 DeepCast 制作流程...");
  addLog(`主题: ${form.topic}`);

  try {
    await runResearchStream(
      { topic: form.topic, search_api: form.searchApi },
      handleStreamEvent,
      { signal: abortController.signal }
    );
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      addLog("🛑 制作已取消。");
    } else {
      addLog(`❌ 错误: ${err}`);
      alert("制作失败，请查看日志。");
    }
  }
}

function handleStreamEvent(event: ResearchStreamEvent) {
  // 1. Tool Calls (增加执行细节)
  if (event.type === "tool_call") {
    const payload = event as any;
    const tool = payload.tool;
    const agent = payload.agent || "Agent";
    
    // 解析具体操作
    if (tool === "search") {
      // 从参数中提取查询词（如果可能）
      // 假设参数结构 { input: "..." }
      // 由于 parameters 是 Record<string, unknown>，我们尝试转换为字符串
      let query = "";
      if (payload.parameters && typeof payload.parameters.input === "string") {
        query = payload.parameters.input;
      }
      addLog(`🔍 ${agent} 正在搜索: ${query || "相关信息"}`);
    } else if (tool === "note") {
      const action = payload.parameters?.action;
      if (action === "read") {
        addLog(`📖 ${agent} 正在阅读笔记`);
      } else if (action === "create" || action === "update") {
        addLog(`📝 ${agent} 正在记录关键信息`);
      }
    } else {
      addLog(`🔧 ${agent} 调用了工具: ${tool}`);
    }
    return;
  }

  // 2. Sources (发现来源)
  if (event.type === "sources") {
    addLog("📚 发现新的信息来源，正在分析...");
    return;
  }

  // 3. Status Updates
  if (event.type === "status") {
    // 翻译或直接显示
    let msg = String(event.message);
    if (msg.includes("初始化")) msg = "初始化研究流程...";
    if (msg.includes("脚本")) msg = "正在创作播客剧本...";
    if (msg.includes("语音") || msg.includes("音频")) msg = "正在合成语音...";
    
    // Translation for known English messages
    if (msg.includes("Researching")) msg = "正在进行深度搜索...";
    if (msg.includes("Generating")) msg = "正在生成内容...";
    if (msg.includes("Analyzing")) msg = "正在分析数据...";
    
    addLog(`ℹ️ ${msg}`);
    
    if (String(event.message).includes("脚本")) productionStage.value = "script";
    if (String(event.message).includes("语音") || String(event.message).includes("音频")) productionStage.value = "audio";
  }

  // 3.5 Todo List (Total Tasks)
  if (event.type === "todo_list") {
    console.log("Received todo_list event:", event);
    const payload = event as any;
    if (payload.tasks && Array.isArray(payload.tasks)) {
      todoList.value = payload.tasks; // Initialize list
      totalTasks.value = payload.tasks.length;
      addLog(`📋 规划了 ${totalTasks.value} 个研究任务`);
    } else {
      console.warn("Received todo_list but tasks is empty or invalid", payload);
    }
  }

  // 4. Research Updates
  if (event.type === "task_status") {
    const payload = event as any;
    if (payload.status === "in_progress") {
      currentTask.value = payload; // 简单的任务更新
      addLog(`👉 开始执行任务: ${payload.title || '未知任务'}`);
    } else if (payload.status === "completed") {
      completedTasks.value++;
      addLog(`✅ 任务完成: ${payload.title}`);
    } else if (payload.status === "skipped") {
      completedTasks.value++;
      addLog(`⏭️ 任务跳过: ${payload.title}`);
    } else if (payload.status === "failed") {
      completedTasks.value++;
      addLog(`❌ 任务失败: ${payload.title}`);
    }
  }
  
  if (event.type === "task_summary_chunk") {
      const payload = event as any;
      const taskIndex = todoList.value.findIndex(t => t.id === payload.task_id);
      
      if (taskIndex !== -1) {
        // Initialize summary if it doesn't exist
        if (!todoList.value[taskIndex].summary) {
          todoList.value[taskIndex].summary = "";
        }
        
        // Append chunk
        // Note: You might want to strip <think> tags if they leak through, 
        // but backend usually handles that.
        todoList.value[taskIndex].summary += payload.content;
        
        // Auto-scroll logic could go here if we had a ref to the specific item
      }
  }

  // 5. Report Ready
  if (event.type === "final_report") {
    reportMarkdown.value = String(event.report);
    addLog("📄 深度研究报告已生成。");
  }

  // 6. Script Ready
  if (event.type === "podcast_script") {
    const payload = event as any;
    podcastScript.value = payload.script;
    productionStage.value = "audio";
    addLog("🎙️ 播客剧本创作完成。");
  }

  // 7. Audio Generation (Detail)
  if (event.type === "audio_generated") {
    const files = (event as any).files || [];
    addLog(`🎵 已生成 ${files.length} 个音频片段。`);
  }

  // 8. Podcast Ready (Final)
  if (event.type === "podcast_ready") {
    const payload = event as any;
    // 后端返回的是文件路径，我们需要转换为 URL
    // 假设后端挂载了 /output 静态目录
    // payload.file 是绝对路径，我们需要提取文件名
    const filename = String(payload.file).split(/[\\/]/).pop();
    if (filename) {
      // 获取当前 API base URL (从 api.ts 逻辑推断，这里简化处理)
      // 在生产环境中应该从配置读取，这里假设是 localhost:8000
      const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
      audioUrl.value = `${baseUrl}/output/${filename}`;
      addLog("🎉 播客制作完成！即将开始播放...");
      productionStage.value = "done";
      
      // 延迟跳转到播放页
      setTimeout(() => {
        currentView.value = "player";
      }, 1500);
    }
  }
}

function cancelProduction() {
  if (abortController) {
    abortController.abort();
    abortController = null;
  }
  currentView.value = "setup";
}

function resetApp() {
  currentView.value = "setup";
  form.topic = "";
  isPlaying.value = false;
}

// Audio Controls
function togglePlay() {
  if (!audioPlayer.value) return;
  if (isPlaying.value) {
    audioPlayer.value.pause();
  } else {
    audioPlayer.value.play();
  }
}

function onTimeUpdate() {
  if (audioPlayer.value) {
    currentTime.value = audioPlayer.value.currentTime;
    duration.value = audioPlayer.value.duration || 0;
  }
}

function seekAudio(e: MouseEvent) {
  if (!audioPlayer.value || !duration.value) return;
  const target = e.currentTarget as HTMLElement;
  const rect = target.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const percent = x / rect.width;
  audioPlayer.value.currentTime = percent * duration.value;
}

function formatTime(seconds: number) {
  if (!seconds) return "0:00";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}
</script>

<style scoped>
/* --- Global & Layout --- */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
}
::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}

.deepcast-container {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  color: #fff;
  background: #0f172a;
  position: relative;
}

.background-gradient {
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle at center, #1e293b 0%, #0f172a 60%, #000 100%);
  z-index: 0;
  animation: pulseBg 20s infinite alternate;
}

@keyframes pulseBg {
  0% { transform: scale(1); }
  100% { transform: scale(1.1); }
}

section {
  position: relative;
  z-index: 1;
  height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
}

/* --- Setup View --- */
.view-setup {
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.brand-header {
  text-align: center;
  margin-bottom: 3rem;
}

.logo-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

h1 {
  font-size: 3rem;
  font-weight: 800;
  letter-spacing: -1px;
  background: linear-gradient(135deg, #60a5fa, #c084fc);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0;
}

.tagline {
  color: #94a3b8;
  font-size: 1.1rem;
  margin-top: 0.5rem;
}

.setup-form {
  width: 100%;
  max-width: 500px;
  background: rgba(30, 41, 59, 0.5);
  backdrop-filter: blur(10px);
  padding: 2rem;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}

.input-group label, .setting-item label {
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: #cbd5e1;
  margin-bottom: 0.5rem;
}

.input-group textarea {
  width: 100%;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #fff;
  padding: 1rem;
  border-radius: 8px;
  resize: none;
  font-size: 1rem;
  transition: border-color 0.2s;
}

.input-group textarea:focus {
  outline: none;
  border-color: #60a5fa;
}

.settings-row {
  margin: 1.5rem 0;
}

.select-wrapper {
  position: relative;
}

select {
  width: 100%;
  appearance: none;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #fff;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  font-size: 0.95rem;
  cursor: pointer;
}

.select-arrow {
  position: absolute;
  right: 1rem;
  top: 50%;
  transform: translateY(-50%);
  color: #64748b;
  pointer-events: none;
  font-size: 0.8rem;
}

.cta-button {
  width: 100%;
  padding: 1rem;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  border: none;
  border-radius: 8px;
  color: #fff;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  transition: transform 0.2s, opacity 0.2s;
}

.cta-button:hover:not(:disabled) {
  transform: translateY(-2px);
  opacity: 0.9;
}

.cta-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* --- Production View --- */
.view-production {
  overflow-y: auto;
  width: 100%;
  display: block;
}

.production-content {
  max-width: 800px;
  margin: 0 auto;
  padding: 4rem 2rem;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.todo-list-container {
  width: 100%;
  margin-top: 2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding-top: 2rem;
}

.todo-list-container h3 {
  margin-bottom: 1.5rem;
  color: #e2e8f0;
  font-size: 1.2rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.todo-items {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.todo-item {
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 1.5rem;
  display: flex;
  gap: 1rem;
  transition: all 0.3s ease;
}

.todo-item:hover {
  background: rgba(30, 41, 59, 0.8);
  border-color: rgba(96, 165, 250, 0.3);
}

.todo-item.in_progress {
  border-color: #60a5fa;
  box-shadow: 0 0 20px rgba(96, 165, 250, 0.1);
}

.todo-item.completed {
  border-color: rgba(16, 185, 129, 0.3);
}

.todo-item.failed {
  border-color: rgba(239, 68, 68, 0.3);
}

.task-status-icon {
  font-size: 1.5rem;
  padding-top: 0.2rem;
  min-width: 2rem;
  text-align: center;
}

.task-content {
  flex: 1;
  min-width: 0;
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.5rem;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.task-title {
  font-weight: 600;
  color: #f1f5f9;
  font-size: 1.05rem;
}

.task-intent {
  font-size: 0.8rem;
  color: #94a3b8;
  background: rgba(0, 0, 0, 0.2);
  padding: 2px 8px;
  border-radius: 4px;
}

.production-header {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 3rem;
}

.production-header h2 {
  font-size: 1.5rem;
  margin: 0;
}

.cancel-btn {
  background: transparent;
  border: 1px solid rgba(239, 68, 68, 0.5);
  color: #fca5a5;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
}

.stage-monitor {
  display: flex;
  align-items: center;
  width: 100%;
  margin-bottom: 3rem;
}

.stage-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  opacity: 0.4;
  transition: opacity 0.3s;
}

.stage-step.active, .stage-step.completed {
  opacity: 1;
}

.step-icon {
  width: 48px;
  height: 48px;
  background: #1e293b;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  border: 2px solid transparent;
}

.stage-step.active .step-icon {
  border-color: #60a5fa;
  box-shadow: 0 0 15px rgba(96, 165, 250, 0.3);
  animation: pulseIcon 1.5s infinite;
}

.stage-step.completed .step-icon {
  background: #10b981;
  color: #fff;
}

@keyframes pulseIcon {
  0% { transform: scale(1); }
  50% { transform: scale(1.05); }
  100% { transform: scale(1); }
}

.stage-line {
  flex: 1;
  height: 2px;
  background: #334155;
  margin: 0 1rem;
  position: relative;
  top: -14px;
}

.terminal-log {
  width: 100%;
  background: #000;
  border-radius: 8px;
  padding: 1rem;
  font-family: 'Fira Code', monospace;
  font-size: 0.9rem;
  height: 150px;
  margin-bottom: 2rem;
  border: 1px solid #333;
}

.log-content {
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.log-entry {
  display: flex;
  gap: 1rem;
}

.log-time {
  color: #64748b;
}

.log-msg {
  color: #e2e8f0;
}

.research-preview {
  width: 100%;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 8px;
  padding: 1rem;
  border-left: 4px solid #60a5fa;
}

.preview-header {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 0.5rem;
}

.badge {
  background: #2563eb;
  font-size: 0.7rem;
  padding: 2px 6px;
  border-radius: 4px;
  text-transform: uppercase;
}

.task-title {
  font-weight: 600;
}

.preview-body {
  color: #94a3b8;
  font-size: 0.9rem;
  line-height: 1.5;
}

/* --- Player View --- */
.view-player {
  padding: 0;
  overflow: hidden; /* Player view handles internal scrolling */
}

.player-layout {
  display: flex;
  height: 100%;
  width: 100%;
}

.player-sidebar {
  width: 400px;
  background: #0f172a;
  border-right: 1px solid #1e293b;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  z-index: 2;
}

.back-home-btn {
  align-self: flex-start;
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
  margin-bottom: 2rem;
}

.back-home-btn:hover {
  color: #fff;
}

.album-art {
  width: 260px;
  height: 260px;
  margin-bottom: 2rem;
  position: relative;
}

.vinyl-record {
  width: 100%;
  height: 100%;
  background: radial-gradient(circle, #222 20%, #111 21%, #111 30%, #222 31%, #222 60%, #111 61%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10px 30px rgba(0,0,0,0.5);
  border: 4px solid #333;
}

.vinyl-record.spinning {
  animation: spin 5s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.vinyl-label {
  width: 100px;
  height: 100px;
  background: #60a5fa;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 1.5rem;
  color: #fff;
}

.track-info {
  text-align: center;
  margin-bottom: 2rem;
}

.track-info h3 {
  font-size: 1.25rem;
  margin-bottom: 0.5rem;
  background: none;
  -webkit-text-fill-color: initial;
  color: #fff;
}

.audio-controls {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.control-buttons {
  display: flex;
  justify-content: center;
  gap: 1.5rem;
  align-items: center;
}

.play-btn {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: #fff;
  color: #0f172a;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.1s;
}

.play-btn:active {
  transform: scale(0.95);
}

.download-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(255,255,255,0.1);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  font-size: 1.2rem;
}

.progress-bar-wrapper {
  cursor: pointer;
  padding: 10px 0;
}

.progress-bar-bg {
  width: 100%;
  height: 4px;
  background: #334155;
  border-radius: 2px;
  position: relative;
}

.progress-bar-fill {
  height: 100%;
  background: #60a5fa;
  border-radius: 2px;
}

.time-display {
  font-size: 0.75rem;
  color: #64748b;
  margin-top: 0.5rem;
  text-align: right;
}

.report-toggle {
  margin-top: auto;
  width: 100%;
  text-align: center;
}

.report-toggle button {
  background: none;
  border: 1px solid #334155;
  color: #94a3b8;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.8rem;
  cursor: pointer;
}

.content-main {
  flex: 1;
  background: #1e293b;
  padding: 2rem;
  overflow-y: auto;
}

/* Chat UI */
.script-chat {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.chat-bubble {
  display: flex;
  gap: 1rem;
}

.chat-bubble.host {
  flex-direction: row;
}

.chat-bubble.guest {
  flex-direction: row-reverse;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #3b82f6;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  flex-shrink: 0;
}

.chat-bubble.guest .avatar {
  background: #8b5cf6;
}

.bubble-content {
  background: #334155;
  padding: 1rem;
  border-radius: 12px;
  border-top-left-radius: 2px;
  max-width: 80%;
  line-height: 1.6;
}

.chat-bubble.guest .bubble-content {
  background: #475569;
  border-radius: 12px;
  border-top-right-radius: 2px;
}

.speaker-name {
  font-size: 0.75rem;
  color: #94a3b8;
  margin-bottom: 0.25rem;
  text-transform: uppercase;
  font-weight: 600;
}

.markdown-report {
  max-width: 800px;
  margin: 0 auto;
  color: #e2e8f0;
  line-height: 1.7;
}

.task-summary {
  font-size: 0.85rem;
  color: #cbd5e1;
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px dashed rgba(255, 255, 255, 0.1);
  line-height: 1.6;
}

.task-summary :deep(h1),
.task-summary :deep(h2),
.task-summary :deep(h3),
.task-summary :deep(h4) {
  font-size: 0.95rem;
  font-weight: 700;
  margin-top: 0.8rem;
  margin-bottom: 0.4rem;
  color: #e2e8f0;
}

.task-summary :deep(p) {
  margin-bottom: 0.6rem;
}

.task-summary :deep(ul),
.task-summary :deep(ol) {
  padding-left: 1.2rem;
  margin-bottom: 0.6rem;
}

.task-summary :deep(li) {
  margin-bottom: 0.3rem;
}

.task-summary :deep(strong) {
  color: #60a5fa;
  font-weight: 600;
}

.task-summary :deep(code) {
  background: rgba(0, 0, 0, 0.3);
  padding: 2px 4px;
  border-radius: 3px;
  font-family: 'Fira Code', monospace;
  font-size: 0.8em;
  color: #f472b6;
}

.report-content {
  line-height: 1.8;
}

.report-content :deep(h1) {
  font-size: 1.8rem;
  margin-bottom: 1.5rem;
  color: #60a5fa;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding-bottom: 0.5rem;
}

.report-content :deep(h2) {
  font-size: 1.4rem;
  margin-top: 2rem;
  margin-bottom: 1rem;
  color: #c084fc;
}

.report-content :deep(h3) {
  font-size: 1.1rem;
  margin-top: 1.5rem;
  margin-bottom: 0.8rem;
  color: #e2e8f0;
}

.report-content :deep(p) {
  margin-bottom: 1rem;
  color: #cbd5e1;
}

.report-content :deep(ul),
.report-content :deep(ol) {
  padding-left: 1.5rem;
  margin-bottom: 1rem;
}

.report-content :deep(li) {
  margin-bottom: 0.5rem;
}

.report-content :deep(strong) {
  color: #fff;
  font-weight: 600;
}

.report-content :deep(blockquote) {
  border-left: 4px solid #60a5fa;
  padding-left: 1rem;
  margin: 1rem 0;
  color: #94a3b8;
  font-style: italic;
  background: rgba(255, 255, 255, 0.05);
  padding: 0.5rem 1rem;
  border-radius: 0 4px 4px 0;
}

/* Transitions */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>
