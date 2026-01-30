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
            <div class="setting-item search-hint">
              <span class="hint-icon">🔍</span>
              <span class="hint-text">使用混合搜索引擎 (Tavily + SerpApi)</span>
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
          <!-- 顶部：标题和控制 -->
          <header class="production-header">
            <h2>{{ podcastReady ? '🎉 播客制作完成！' : '正在制作您的播客' }}</h2>
            <button v-if="!podcastReady" class="cancel-btn" @click="cancelProduction">取消</button>
          </header>
          <p class="production-topic">「{{ form.topic }}」</p>

          <!-- 阶段进度指示器 -->
          <div class="stage-monitor" v-if="!podcastReady">
            <div class="stage-step" :class="{ active: productionStage === 'research', completed: isStageCompleted('research') }">
              <div class="step-icon">🔍</div>
              <div class="step-label">深度研究</div>
              <div class="step-progress" v-if="productionStage === 'research' && (todoList.length > 0 || totalTasks > 0)">
                {{ completedTasks }}/{{ todoList.length || totalTasks }}
              </div>
            </div>
            <div class="stage-line" :class="{ active: isStageCompleted('research') }"></div>
            <div class="stage-step" :class="{ active: productionStage === 'script', completed: isStageCompleted('script') }">
              <div class="step-icon">📝</div>
              <div class="step-label">剧本创作</div>
            </div>
            <div class="stage-line" :class="{ active: isStageCompleted('script') }"></div>
            <div class="stage-step" :class="{ active: productionStage === 'audio', completed: isStageCompleted('audio') }">
              <div class="step-icon">🎧</div>
              <div class="step-label">音频合成</div>
              <div class="step-progress" v-if="productionStage === 'audio' && audioProgress.total > 0">
                {{ audioProgress.current }}/{{ audioProgress.total }}
              </div>
            </div>
          </div>

          <!-- 当前执行状态卡片 -->
          <div class="current-status-card" v-if="currentStatusMessage && !podcastReady">
            <div class="status-indicator"></div>
            <span class="status-text">{{ currentStatusMessage }}</span>
          </div>

          <!-- 终端风格日志输出 -->
          <div class="terminal-log">
            <div class="log-header">
              <span class="log-header-title">执行日志 (Terminal)</span>
              <span class="log-count">{{ logs.length }} lines</span>
            </div>
            <div class="log-content" ref="logContainer">
              <div v-for="(log, i) in logs" :key="i" class="log-entry" :class="getLogClass(log.message)">
                <span class="log-time">{{ log.time }}</span>
                <span class="log-msg">{{ log.message }}</span>
              </div>
              <div v-if="logs.length === 0" class="log-placeholder">等待执行...</div>
              <!-- 等待动画指示器 -->
              <div v-if="isWaiting && logs.length > 0" class="log-entry log-waiting">
                <span class="log-time">{{ new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }) }}</span>
                <span class="log-msg waiting-indicator">⏳ 处理中{{ waitingDots }}</span>
              </div>
            </div>
          </div>

          <!-- 报告预览区（在日志下方） -->
          <div v-if="reportReady" class="report-section">
            <div class="section-header">
              <h3>📄 深度研究报告</h3>
              <button class="action-btn" @click="downloadReport">
                ⬇️ 下载报告
              </button>
            </div>
            <div class="report-content-box">
              <div class="markdown-report" v-html="md.render(reportMarkdown)"></div>
            </div>
          </div>

          <!-- 播客完成区 -->
          <div v-if="podcastReady" class="podcast-section">
            <div class="podcast-ready-card">
              <div class="ready-icon">🎉</div>
              <h3>播客制作完成！</h3>
              <p>您的播客音频已生成完毕</p>
              
              <!-- 简单音频播放器 -->
              <div class="simple-player">
                <audio 
                  ref="audioPlayer" 
                  :src="audioUrl" 
                  controls
                  @play="isPlaying = true"
                  @pause="isPlaying = false"
                ></audio>
              </div>
              
              <div class="podcast-actions">
                <a :href="audioUrl" download class="download-podcast-btn">
                  ⬇️ 下载 MP3
                </a>
                <button class="new-podcast-btn" @click="resetApp">
                  制作新播客
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 3. Player View: 独立播放器页面 -->
      <section v-else-if="currentView === 'player'" class="view-player" key="player">
        <div class="player-container">
          <button class="back-home-btn" @click="resetApp">
            ← 制作新播客
          </button>
          
          <div class="player-card">
            <div class="album-art">
              <div class="vinyl-record" :class="{ spinning: isPlaying }">
                <div class="vinyl-label">DC</div>
              </div>
            </div>

            <div class="track-info">
              <h3>{{ form.topic }}</h3>
              <p>DeepCast 原创播客</p>
            </div>

            <!-- 简单原生播放器 -->
            <div class="simple-player-large">
              <audio 
                ref="audioPlayer" 
                :src="audioUrl" 
                controls
                @play="isPlaying = true"
                @pause="isPlaying = false"
              ></audio>
            </div>

            <a :href="audioUrl" download class="download-btn-large">
              ⬇️ 下载 MP3
            </a>
          </div>

          <!-- 报告查看区 -->
          <div class="report-toggle-section">
            <button class="toggle-btn" @click="showReport = !showReport">
              {{ showReport ? '🔼 收起研究报告' : '🔽 查看研究报告' }}
            </button>
            <div v-if="showReport" class="report-panel">
              <div class="markdown-report" v-html="md.render(reportMarkdown)"></div>
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
import MarkdownIt from "markdown-it";

// Markdown renderer
const md = new MarkdownIt();

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
  topic: ""
});

const logs = ref<LogEntry[]>([]);
const isPlaying = ref(false);
const currentTime = ref(0);
const duration = ref(0);
const progressPercent = computed(() => (duration.value ? (currentTime.value / duration.value) * 100 : 0));
const showReport = ref(true); // 默认显示报告
const reportReady = ref(false); // 报告是否已生成
const podcastReady = ref(false); // 播客是否已生成

// Research Progress State
const totalTasks = ref(0);
const completedTasks = ref(0);
const todoList = ref<any[]>([]); // Store the full todo list
const researchProgress = computed(() => {
  if (totalTasks.value === 0) return "";
  return `(${completedTasks.value}/${totalTasks.value})`;
});

// Audio Progress State (新增)
const audioProgress = reactive({
  current: 0,
  total: 0,
  role: ""
});

// Current Status Message (新增)
const currentStatusMessage = ref("");

// 等待动画状态
const isWaiting = ref(false);
const waitingDots = ref(".");
let waitingInterval: ReturnType<typeof setInterval> | null = null;

// 启动等待动画
function startWaitingAnimation() {
  isWaiting.value = true;
  waitingDots.value = ".";
  waitingInterval = setInterval(() => {
    waitingDots.value = waitingDots.value.length >= 3 ? "." : waitingDots.value + ".";
  }, 500);
}

// 停止等待动画
function stopWaitingAnimation() {
  isWaiting.value = false;
  if (waitingInterval) {
    clearInterval(waitingInterval);
    waitingInterval = null;
  }
}

// Data
const podcastScript = ref<PodcastMessage[]>([]);
const reportMarkdown = ref("");
const audioUrl = ref("");
const currentTask = ref<any>(null); // 简化的任务状态

// Refs
const audioPlayer = ref<HTMLAudioElement | null>(null);
const logContainer = ref<HTMLElement | null>(null);
let abortController: AbortController | null = null;

// Helper: 根据日志内容返回样式类（终端风格）
function getLogClass(message: string): string {
  // 阶段变更 - 绿色高亮
  if (message.includes("[STAGE]") || message.includes("═══")) return "log-stage";
  // 任务状态
  if (message.includes("[TASK")) return "log-task";
  // 工具调用
  if (message.includes("[TOOL]")) return "log-tool";
  // 来源信息
  if (message.includes("[SOURCES]")) return "log-sources";
  // 成功/完成
  if (message.includes("✅") || message.includes("完成") || message.includes("SUCCESS")) return "log-success";
  // 错误
  if (message.includes("❌") || message.includes("失败") || message.includes("ERROR")) return "log-error";
  // 警告
  if (message.includes("⚠️") || message.includes("WARNING")) return "log-warning";
  // 开始/启动
  if (message.includes("🚀") || message.includes("开始") || message.includes("START")) return "log-start";
  // 规划
  if (message.includes("📋") || message.includes("PLAN")) return "log-plan";
  // 搜索
  if (message.includes("🔍") || message.includes("SEARCH")) return "log-search";
  // 音频
  if (message.includes("🎤") || message.includes("AUDIO") || message.includes("TTS")) return "log-audio";
  // 后端日志
  if (message.includes("💬")) return "log-backend";
  // INFO 级别（默认）
  if (message.includes("INFO:")) return "log-info";
  return "";
}

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
  // 重置新增的状态
  audioProgress.current = 0;
  audioProgress.total = 0;
  audioProgress.role = "";
  currentStatusMessage.value = "正在初始化...";
  reportReady.value = false;
  podcastReady.value = false;
  showReport.value = true;

  abortController = new AbortController();
  
  // 启动等待动画
  startWaitingAnimation();

  addLog("🚀 启动 DeepCast 制作流程...");
  addLog(`📌 主题: 「${form.topic}」`);

  try {
    await runResearchStream(
      { topic: form.topic },
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
  } finally {
    // 停止等待动画
    stopWaitingAnimation();
  }
}

function handleStreamEvent(event: ResearchStreamEvent) {
  // 0. Log event - 直接显示后端日志
  if (event.type === "log") {
    const msg = String((event as any).message || "");
    addLog(`INFO: ${msg}`);
    
    // 解析 TTS 成功日志来更新进度 (格式: [TTS 6/13] ✓ Host 语音生成成功)
    const ttsMatch = msg.match(/\[TTS (\d+)\/(\d+)\] ✓/);
    if (ttsMatch) {
      audioProgress.current = parseInt(ttsMatch[1], 10);
      audioProgress.total = parseInt(ttsMatch[2], 10);
    }
    return;
  }

  // 0.5. Stage Change (阶段切换事件)
  if (event.type === "stage_change") {
    const payload = event as any;
    const stage = payload.stage;
    const message = payload.message || "";
    
    // 更新当前状态消息
    currentStatusMessage.value = message;
    
    // 更新当前阶段并记录日志
    addLog(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
    addLog(`📌 [STAGE] ${stage.toUpperCase()} - ${message}`);
    addLog(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
    
    if (stage === "report") {
      productionStage.value = "research";
    } else if (stage === "script") {
      productionStage.value = "script";
    } else if (stage === "audio") {
      productionStage.value = "audio";
    }
    return;
  }

  // 1. Tool Calls (增加执行细节)
  if (event.type === "tool_call") {
    const payload = event as any;
    const tool = payload.tool;
    const agent = payload.agent || "Agent";
    const taskId = payload.task_id;
    const noteId = payload.note_id;
    const params = payload.parameters || payload.parsed_parameters || {};
    
    // 构建详细的日志信息，类似后端 INFO 输出
    let logParts = [`[TOOL] agent=${agent} tool=${tool}`];
    if (taskId) logParts.push(`task_id=${taskId}`);
    if (noteId) logParts.push(`note_id=${noteId}`);
    
    // 解析具体操作并添加关键参数
    if (tool === "note") {
      const action = params.action;
      const title = params.title;
      if (action) logParts.push(`action=${action}`);
      if (title) logParts.push(`title="${title}"`);
      addLog(`📝 ${logParts.join(' ')}`);
    } else if (tool === "search") {
      let query = params.input || params.query || "";
      if (query) logParts.push(`query="${query.slice(0, 50)}${query.length > 50 ? '...' : ''}"`);
      addLog(`🔍 ${logParts.join(' ')}`);
    } else {
      addLog(`🔧 ${logParts.join(' ')}`);
    }
    return;
  }

  // 2. Sources (发现来源)
  if (event.type === "sources") {
    const payload = event as any;
    const taskId = payload.task_id;
    const backend = payload.backend;
    let msg = `[SOURCES] task_id=${taskId}`;
    if (backend) msg += ` backend=${backend}`;
    const sourcesCount = payload.latest_sources ? payload.latest_sources.split('\n').filter((s: string) => s.trim()).length : 0;
    msg += ` found=${sourcesCount} sources`;
    addLog(`📚 ${msg}`);
    return;
  }

  // 3. Status Updates
  if (event.type === "status") {
    // 直接显示后端发来的消息
    let msg = String(event.message);
    addLog(`ℹ️ [STATUS] ${msg}`);
  }

  // 3.5 Todo List (Total Tasks)
  if (event.type === "todo_list") {
    console.log("Received todo_list event:", event);
    const payload = event as any;
    if (payload.tasks && Array.isArray(payload.tasks)) {
      todoList.value = payload.tasks;
      totalTasks.value = payload.tasks.length;
      addLog(`📋 [PLAN] 研究规划专家创建了 ${totalTasks.value} 个任务:`);
      // 列出每个任务的标题和查询
      payload.tasks.forEach((task: any, idx: number) => {
        addLog(`   └─ Task ${task.id}: ${task.title}`);
        if (task.query) {
          addLog(`      query="${task.query.slice(0, 60)}${task.query.length > 60 ? '...' : ''}"`);
        }
      });
    } else {
      console.warn("Received todo_list but tasks is empty or invalid", payload);
    }
  }

  // 4. Research Updates
  if (event.type === "task_status") {
    const payload = event as any;
    const taskId = payload.task_id;
    const status = payload.status;
    const title = payload.title || "";
    const query = payload.query || "";
    
    // 如果 todoList 为空但收到了 task_status，动态添加任务
    if (todoList.value.length === 0 || !todoList.value.find(t => t.id === taskId)) {
      todoList.value.push({
        id: taskId,
        title: title,
        status: status,
        query: query,
        intent: payload.intent || "",
      });
      // 更新总任务数（基于已知的最大 task_id）
      if (taskId > totalTasks.value) {
        totalTasks.value = taskId;
      }
    }
    
    // 更新内部状态
    const taskIndex = todoList.value.findIndex(t => t.id === taskId);
    if (taskIndex !== -1) {
      todoList.value[taskIndex].status = status;
      if (payload.summary) {
        todoList.value[taskIndex].summary = payload.summary;
      }
    }
    
    // 截断长查询内容
    const truncateText = (text: string, max: number) => 
      text.length > max ? text.slice(0, max) + "..." : text;
    
    // 获取当前已知的总任务数
    const getTotal = () => {
      if (todoList.value.length > 0) return todoList.value.length;
      if (totalTasks.value > 0) return totalTasks.value;
      // 根据 task_id 推断（假设 task_id 是从 1 开始的连续数字）
      return Math.max(taskId, completedTasks.value + 1);
    };
    
    if (status === "in_progress") {
      currentTask.value = payload;
      addLog(`🚀 [TASK ${taskId}] status=in_progress title="${title}"`);
      if (payload.intent) {
        addLog(`   ├─ intent: ${payload.intent}`);
      }
      if (query) {
        addLog(`   └─ query: "${truncateText(query, 60)}"`);
      }
    } else if (status === "completed") {
      completedTasks.value++;
      addLog(`✅ [TASK ${taskId}] status=completed (${completedTasks.value}/${getTotal()}) title="${title}"`);
    } else if (status === "skipped") {
      completedTasks.value++;
      addLog(`⏭️ [TASK ${taskId}] status=skipped (${completedTasks.value}/${getTotal()}) title="${title}"`);
    } else if (status === "failed") {
      completedTasks.value++;
      addLog(`❌ [TASK ${taskId}] status=failed (${completedTasks.value}/${getTotal()}) title="${title}" error="${payload.detail || 'unknown'}"`);
    }
  }
  
  // task_summary_chunk - 显示摘要片段（可选，减少日志噪音）
  if (event.type === "task_summary_chunk") {
      const payload = event as any;
      const taskIndex = todoList.value.findIndex(t => t.id === payload.task_id);
      
      if (taskIndex !== -1) {
        if (!todoList.value[taskIndex].summary) {
          todoList.value[taskIndex].summary = "";
          // 只在开始时显示一条日志
          addLog(`📄 [SUMMARY] task_id=${payload.task_id} 正在生成摘要...`);
        }
        todoList.value[taskIndex].summary += payload.content;
      }
  }

  // 5. Report Ready - 显示报告预览
  if (event.type === "final_report") {
    reportMarkdown.value = String(event.report);
    reportReady.value = true;
    currentStatusMessage.value = "深度研究报告已完成，继续生成播客...";
    const reportLen = String(event.report).length;
    addLog(`📄 [REPORT] status=completed length=${reportLen} chars`);
  }

  // 6. Script Ready
  if (event.type === "podcast_script") {
    const payload = event as any;
    podcastScript.value = payload.script || [];
    const turns = payload.turns ?? payload.script?.length ?? 0;
    productionStage.value = "audio";
    audioProgress.total = turns;
    audioProgress.current = 0;
    currentStatusMessage.value = turns > 0 
      ? `脚本完成，准备生成 ${turns} 段语音` 
      : "脚本为空，跳过音频生成";
    addLog(`🎙️ [SCRIPT] status=completed turns=${turns}`);
    // 不再输出额外的警告，后端会通过 log 事件发送
  }

  // 6.5. Audio Start
  if (event.type === "audio_start") {
    const payload = event as any;
    audioProgress.total = payload.total || 0;
    audioProgress.current = 0;
    addLog(`🎵 [AUDIO] status=started total=${payload.total}`);
  }

  // 7. Audio Progress
  if (event.type === "audio_progress") {
    const payload = event as any;
    audioProgress.current = payload.current;
    audioProgress.total = payload.total;
    audioProgress.role = payload.role;
    currentStatusMessage.value = `TTS ${payload.current}/${payload.total}: ${payload.role}`;
    // 不再输出 generating 日志，后端会在生成成功后发送 log 事件
  }

  // 8. Audio Generation Complete
  if (event.type === "audio_generated") {
    const payload = event as any;
    const count = payload.count ?? payload.files?.length ?? 0;
    currentStatusMessage.value = count > 0 
      ? `${count} 个音频片段已生成，正在合成...` 
      : "音频生成失败";
    addLog(`🎵 [AUDIO] status=completed count=${count}`);
    
    if (count === 0) {
      addLog(`⚠️ [WARNING] no audio files generated, check TTS config`);
    }
  }

  // 9. Podcast Ready (Final) - 设置播客就绪状态
  if (event.type === "podcast_ready") {
    const payload = event as any;
    const filename = String(payload.file).split(/[\\/]/).pop();
    if (filename) {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
      audioUrl.value = `${baseUrl}/output/audio/${filename}`;
      podcastReady.value = true;
      productionStage.value = "done";
      currentStatusMessage.value = "🎉 播客制作完成！";
      addLog(`🎉 [PODCAST] status=ready file=${filename}`);
      // 停止等待动画
      stopWaitingAnimation();
    }
  }

  // 10. Done event
  if (event.type === "done") {
    addLog(`✅ [DONE] all tasks completed`);
    stopWaitingAnimation();
    productionStage.value = "done";
    // 如果播客已就绪，确保状态正确
    if (podcastReady.value) {
      currentStatusMessage.value = "🎉 播客制作完成！";
    } else {
      currentStatusMessage.value = "全部完成";
    }
  }
}

function cancelProduction() {
  if (abortController) {
    abortController.abort();
    abortController = null;
  }
  stopWaitingAnimation();
  currentView.value = "setup";
  currentStatusMessage.value = "";
}

function resetApp() {
  currentView.value = "setup";
  form.topic = "";
  isPlaying.value = false;
  currentStatusMessage.value = "";
  stopWaitingAnimation();
  reportReady.value = false;
  podcastReady.value = false;
}

// 下载报告为 Markdown 文件
function downloadReport() {
  if (!reportMarkdown.value) return;
  const blob = new Blob([reportMarkdown.value], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${form.topic.slice(0, 30) || 'report'}_研究报告.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// 切换到播放器视图
function playPodcast() {
  currentView.value = "player";
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

/* 搜索引擎提示样式 */
.search-hint {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: rgba(96, 165, 250, 0.1);
  border: 1px solid rgba(96, 165, 250, 0.2);
  border-radius: 8px;
}

.hint-icon {
  font-size: 1rem;
}

.hint-text {
  color: #94a3b8;
  font-size: 0.9rem;
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

/* --- Production View (上下布局) --- */
.view-production {
  overflow-y: auto;
  width: 100%;
  display: block;
}

.production-content {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.production-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.production-header h2 {
  font-size: 1.5rem;
  margin: 0;
}

.production-topic {
  color: #94a3b8;
  font-size: 1rem;
  margin-top: 0;
  margin-bottom: 1rem;
  font-style: italic;
}

.cancel-btn {
  background: transparent;
  border: 1px solid rgba(239, 68, 68, 0.5);
  color: #fca5a5;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.cancel-btn:hover {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.8);
}

/* 报告区块 */
.report-section {
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  overflow: hidden;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  background: rgba(30, 41, 59, 0.8);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.section-header h3 {
  margin: 0;
  color: #f1f5f9;
  font-size: 1.1rem;
}

.action-btn {
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.action-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4);
}

.report-content-box {
  padding: 1.5rem;
  max-height: 500px;
  overflow-y: auto;
}

.report-content-box .markdown-report {
  font-size: 0.9rem;
  line-height: 1.7;
}

/* 播客完成区块 */
.podcast-section {
  margin-top: 1rem;
}

.podcast-ready-card {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(59, 130, 246, 0.2));
  border: 1px solid rgba(16, 185, 129, 0.3);
  border-radius: 16px;
  padding: 2rem;
  text-align: center;
}

.ready-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.podcast-ready-card h3 {
  color: #10b981;
  font-size: 1.5rem;
  margin-bottom: 0.5rem;
}

.podcast-ready-card p {
  color: #94a3b8;
  margin-bottom: 1rem;
}

/* 简单音频播放器 */
.simple-player {
  margin: 1.5rem auto;
  max-width: 400px;
}

.simple-player audio {
  width: 100%;
  height: 50px;
  border-radius: 8px;
}

.podcast-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
  margin-top: 1.5rem;
}

.download-podcast-btn {
  padding: 0.75rem 2rem;
  background: linear-gradient(135deg, #10b981, #059669);
  border: none;
  border-radius: 10px;
  color: white;
  font-size: 1rem;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.3s ease;
}

.download-podcast-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4);
}

.new-podcast-btn {
  padding: 0.75rem 2rem;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 10px;
  color: #94a3b8;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.new-podcast-btn:hover {
  border-color: rgba(255, 255, 255, 0.4);
  color: #f1f5f9;
}

/* 等待报告 */
.waiting-report {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  background: rgba(15, 23, 42, 0.5);
  border: 1px dashed rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  text-align: center;
}

.waiting-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  animation: bounce 2s infinite;
}

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.waiting-report p {
  color: #94a3b8;
  font-size: 1rem;
}

/* 响应式布局 */
@media (max-width: 1024px) {
  .production-layout {
    flex-direction: column;
  }
  
  .production-sidebar {
    flex: none;
  }
  
  .report-preview-section {
    max-height: 400px;
  }
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
  transition: background 0.3s ease;
}

.stage-line.active {
  background: linear-gradient(90deg, #3b82f6, #8b5cf6);
}

/* 当前状态卡片 */
.current-status-card {
  width: 100%;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 8px;
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.status-indicator {
  width: 10px;
  height: 10px;
  background: #3b82f6;
  border-radius: 50%;
  animation: pulse-status 1.5s infinite;
}

@keyframes pulse-status {
  0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4); }
  50% { opacity: 0.7; box-shadow: 0 0 0 8px rgba(59, 130, 246, 0); }
}

.status-text {
  color: #93c5fd;
  font-size: 0.95rem;
  font-weight: 500;
}

.terminal-log {
  width: 100%;
  background: #0a0a0a;
  border-radius: 8px;
  font-family: 'Fira Code', 'Cascadia Code', monospace;
  font-size: 0.82rem;
  height: 450px;
  margin-bottom: 1.5rem;
  border: 1px solid #1e293b;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 1rem;
  background: #111827;
  border-bottom: 1px solid #1e293b;
  font-size: 0.8rem;
  color: #64748b;
}

.log-header-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.log-header-title::before {
  content: '●';
  color: #4ade80;
  font-size: 0.6rem;
}

.log-count {
  color: #475569;
}

.log-content {
  height: calc(100% - 32px);
  overflow-y: auto;
  padding: 0.75rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.log-entry {
  display: flex;
  gap: 0.75rem;
  padding: 0.2rem 0;
  border-radius: 2px;
  line-height: 1.4;
}

.log-time {
  color: #475569;
  font-size: 0.8rem;
  flex-shrink: 0;
  min-width: 70px;
}

.log-msg {
  color: #cbd5e1;
  word-break: break-word;
  flex: 1;
}

.log-placeholder {
  color: #475569;
  font-style: italic;
  padding: 1rem 0;
  text-align: center;
}

/* 等待动画指示器 */
.log-entry.log-waiting .log-msg {
  color: #fbbf24;
  animation: pulse 1.5s ease-in-out infinite;
}

.waiting-indicator {
  font-family: monospace;
  letter-spacing: 2px;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* 日志类型样式 - 终端风格 */
.log-entry.log-success .log-msg { color: #4ade80; }
.log-entry.log-error .log-msg { color: #f87171; }
.log-entry.log-warning .log-msg { color: #fbbf24; }
.log-entry.log-start .log-msg { color: #60a5fa; }
.log-entry.log-plan .log-msg { color: #a78bfa; }
.log-entry.log-search .log-msg { color: #fbbf24; }
.log-entry.log-audio .log-msg { color: #f472b6; }

/* INFO 级别日志（工具调用） */
.log-entry.log-info .log-msg { 
  color: #94a3b8;
}

/* 阶段变更 */
.log-entry.log-stage .log-msg { 
  color: #34d399; 
  font-weight: 600;
  border-left: 3px solid #34d399;
  padding-left: 0.5rem;
  margin-left: -0.5rem;
}

/* 后端日志 */
.log-entry.log-backend .log-msg { 
  color: #64748b;
  font-style: italic;
}

/* 任务状态 */
.log-entry.log-task .log-msg {
  color: #60a5fa;
}

/* 工具调用 */
.log-entry.log-tool .log-msg {
  color: #a78bfa;
}

/* 来源信息 */
.log-entry.log-sources .log-msg {
  color: #fbbf24;
}

/* 步骤进度数字 */
.step-progress {
  font-size: 0.7rem;
  color: #60a5fa;
  background: rgba(96, 165, 250, 0.15);
  padding: 2px 6px;
  border-radius: 4px;
  margin-top: 0.25rem;
}

/* 任务计数器 */
.task-counter {
  font-weight: normal;
  color: #64748b;
  font-size: 0.9rem;
}

/* 旋转动画（用于进行中的任务图标） */
.spinning {
  display: inline-block;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 主题显示 */
.production-topic {
  color: #94a3b8;
  font-size: 1rem;
  margin-top: 0.25rem;
  font-style: italic;
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

/* --- Player View (简化版) --- */
.view-player {
  padding: 2rem;
  overflow-y: auto;
}

.player-container {
  max-width: 800px;
  margin: 0 auto;
}

.back-home-btn {
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
  margin-bottom: 2rem;
  font-size: 1rem;
}

.back-home-btn:hover {
  color: #fff;
}

.player-card {
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 2rem;
  text-align: center;
  margin-bottom: 2rem;
}

.album-art {
  width: 200px;
  height: 200px;
  margin: 0 auto 1.5rem;
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
  animation: vinylSpin 5s linear infinite;
}

@keyframes vinylSpin {
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
  margin-bottom: 1.5rem;
}

.track-info h3 {
  font-size: 1.25rem;
  margin-bottom: 0.5rem;
  background: none;
  -webkit-text-fill-color: initial;
  color: #fff;
}

.track-info p {
  color: #94a3b8;
  font-size: 0.9rem;
}

/* 简化的大播放器 */
.simple-player-large {
  margin: 1.5rem 0;
}

.simple-player-large audio {
  width: 100%;
  height: 50px;
  border-radius: 8px;
}

.download-btn-large {
  display: inline-block;
  padding: 0.75rem 2rem;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  border-radius: 10px;
  color: white;
  font-size: 1rem;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.3s ease;
}

.download-btn-large:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(59, 130, 246, 0.4);
}

/* 报告切换区 */
.report-toggle-section {
  margin-top: 2rem;
}

.toggle-btn {
  width: 100%;
  padding: 1rem;
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: #94a3b8;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.toggle-btn:hover {
  background: rgba(30, 41, 59, 0.8);
  color: #f1f5f9;
}

.report-panel {
  margin-top: 1rem;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 1.5rem;
  max-height: 500px;
  overflow-y: auto;
}

.markdown-report {
  max-width: 800px;
  margin: 0 auto;
  color: #e2e8f0;
  line-height: 1.7;
}

.markdown-report :deep(h1) {
  font-size: 1.6rem;
  margin-bottom: 1rem;
  color: #60a5fa;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding-bottom: 0.5rem;
}

.markdown-report :deep(h2) {
  font-size: 1.3rem;
  margin-top: 1.5rem;
  margin-bottom: 0.8rem;
  color: #c084fc;
}

.markdown-report :deep(h3) {
  font-size: 1.1rem;
  margin-top: 1.2rem;
  margin-bottom: 0.6rem;
  color: #e2e8f0;
}

.markdown-report :deep(p) {
  margin-bottom: 0.8rem;
  color: #cbd5e1;
}

.markdown-report :deep(ul),
.markdown-report :deep(ol) {
  padding-left: 1.5rem;
  margin-bottom: 0.8rem;
}

.markdown-report :deep(li) {
  margin-bottom: 0.4rem;
}

.markdown-report :deep(strong) {
  color: #fff;
  font-weight: 600;
}

.markdown-report :deep(code) {
  background: rgba(0, 0, 0, 0.3);
  padding: 2px 4px;
  border-radius: 3px;
  font-family: 'Fira Code', monospace;
  font-size: 0.85em;
  color: #f472b6;
}

.markdown-report :deep(blockquote) {
  border-left: 4px solid #60a5fa;
  padding-left: 1rem;
  margin: 1rem 0;
  color: #94a3b8;
  font-style: italic;
  background: rgba(255, 255, 255, 0.05);
  padding: 0.5rem 1rem;
  border-radius: 0 4px 4px 0;
}

.markdown-report :deep(a) {
  color: #60a5fa;
  text-decoration: none;
}

.markdown-report :deep(a:hover) {
  text-decoration: underline;
}

/* Transitions */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>
