<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { api, streamPost } from '../api'
import MarkdownBlock from './MarkdownBlock.vue'
import SourceList from './SourceList.vue'

const FALLBACK_QUOTES = [
  '一条老街，半城烟火。',
  '砖缝里藏着城市的年轮。',
  '走得慢一点，才听得见旧事。',
  '每座老建筑都是一封未寄的信。',
  '把脚步交给巷子，把故事交给时间。',
  '手艺人指尖的温度，是一座城的记忆。',
  '地名会变，传说不改。',
  '晨光爬上骑楼时，城市刚醒。'
]

const expanded = ref(false)
const quotes = ref(FALLBACK_QUOTES)
const quoteIndex = ref(0)
const quoteVisible = ref(true)
const messages = ref([])
const input = ref('')
const loading = ref(false)
const scrollRef = ref(null)
const inputRef = ref(null)
const hoverExpand = ref(false)
let stopStream = null

const currentQuote = computed(() => quotes.value[quoteIndex.value] || FALLBACK_QUOTES[0])

const QUICK_QUESTIONS = [
  '这条老街最早叫什么名字？',
  '这里有哪些非遗手艺？',
  '推荐一条半日人文漫步路线',
  '这座古建筑的建造年代是？'
]

function startQuoteLoop() {
  const timer = window.setInterval(() => {
    if (expanded.value) return
    quoteVisible.value = false
    window.setTimeout(() => {
      quoteIndex.value = (quoteIndex.value + 1) % quotes.value.length
      quoteVisible.value = true
    }, 460)
  }, 5200)
  return timer
}

async function loadQuotes() {
  try {
    const data = await api.quotes(8)
    if (data?.quotes?.length) quotes.value = data.quotes
  } catch (e) {
    quotes.value = FALLBACK_QUOTES
  }
}

function open() {
  expanded.value = true
  window.setTimeout(() => {
    inputRef.value?.focus()
    scrollToBottom()
  }, 440)
}

function close() {
  expanded.value = false
  stopStream?.()
  stopStream = null
  loading.value = false
}

function toggle() {
  expanded.value ? close() : open()
}

function scrollToBottom() {
  nextTick(() => {
    const el = scrollRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function send(text) {
  const question = (text ?? input.value).trim()
  if (!question || loading.value) return
  input.value = ''
  messages.value.push({ role: 'user', content: question })
  messages.value.push({ role: 'assistant', content: '', sources: [], pending: true })
  loading.value = true
  scrollToBottom()

  const target = messages.value[messages.value.length - 1]
  stopStream = streamPost('/chat/stream', { question, top_k: 5 }, {
    onSources: (sources) => {
      target.sources = sources
      scrollToBottom()
    },
    onDelta: (delta) => {
      target.content += delta
      scrollToBottom()
    },
    onDone: () => {
      target.pending = false
      loading.value = false
      stopStream = null
      scrollToBottom()
    },
    onError: (err) => {
      target.pending = false
      target.content = `⚠️ ${err.message}`
      loading.value = false
      stopStream = null
    }
  })
}

function stopGenerate() {
  stopStream?.()
  stopStream = null
  loading.value = false
  const last = messages.value[messages.value.length - 1]
  if (last?.pending) last.pending = false
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    send()
  }
}

let timer = null

function onDocKeydown(e) {
  if (e.key === 'Escape' && expanded.value) close()
}

onMounted(() => {
  loadQuotes()
  timer = startQuoteLoop()
  document.addEventListener('keydown', onDocKeydown)
})

onUnmounted(() => {
  window.clearInterval(timer)
  document.removeEventListener('keydown', onDocKeydown)
  stopStream?.()
})

watch(expanded, (v) => {
  document.body.classList.toggle('capsule-open', v)
})
</script>

<template>
  <transition name="veil">
    <div v-if="expanded" class="veil" @click="close"></div>
  </transition>

  <div
    class="capsule"
    :class="{ expanded, hover: hoverExpand && !expanded }"
    @click="!expanded && toggle()"
    @mouseenter="hoverExpand = true"
    @mouseleave="hoverExpand = false"
  >
    <!-- 常态：窄条短句 -->
    <div v-if="!expanded" class="capsule-idle">
      <span class="pulse-dot"></span>
      <span :key="currentQuote" class="quote-text">{{ currentQuote }}</span>
      <span class="hint">{{ hoverExpand ? '问一句' : '·' }}</span>
    </div>

    <!-- 展开：对话面板 -->
    <transition name="panel">
      <div v-if="expanded" class="capsule-panel" @click.stop>
        <header class="panel-head">
          <div class="head-left">
            <span class="seal-dot">拾</span>
            <div>
              <div class="title">随行向导</div>
              <div class="sub">CITY WALK COMPANION</div>
            </div>
          </div>
          <button class="icon-btn" title="收起 (Esc)" @click="close">−</button>
        </header>

        <div ref="scrollRef" class="panel-body">
          <div v-if="!messages.length" class="welcome">
            <p class="welcome-title">想问哪条街、哪座楼、哪个传说？</p>
            <p class="welcome-sub">回答标注资料出处，资料未载会如实说明。</p>
            <div class="chips">
              <button v-for="q in QUICK_QUESTIONS" :key="q" class="chip" @click="send(q)">{{ q }}</button>
            </div>
          </div>

          <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role">
            <div class="avatar">{{ m.role === 'user' ? '我' : '叙' }}</div>
            <div class="bubble">
              <MarkdownBlock v-if="m.role === 'assistant'" :content="m.content" />
              <span v-else class="plain">{{ m.content }}</span>
              <span v-if="m.pending" class="caret"></span>
              <SourceList v-if="m.role === 'assistant' && !m.pending && m.sources?.length" :sources="m.sources" />
            </div>
          </div>
        </div>

        <footer class="panel-foot">
          <textarea
            ref="inputRef"
            v-model="input"
            rows="1"
            placeholder="输入地点或问题，Enter 发送"
            @keydown="onKeydown"
          ></textarea>
          <button v-if="!loading" class="send" :disabled="!input.trim()" @click="send()">发送</button>
          <button v-else class="send stop" @click="stopGenerate">停止</button>
        </footer>
      </div>
    </transition>
  </div>
</template>

<style scoped>
/* ---------- 遮罩 ---------- */
.veil {
  position: fixed;
  inset: 0;
  background: rgba(23, 20, 15, 0.32);
  backdrop-filter: blur(3px);
  z-index: 900;
}

.veil-enter-active,
.veil-leave-active {
  transition: opacity 0.5s var(--ease-soft);
}

.veil-enter-from,
.veil-leave-to {
  opacity: 0;
}

/* ---------- 胶囊本体：灵动岛形变 ---------- */
.capsule {
  position: fixed;
  left: 50%;
  bottom: 32px;
  transform: translateX(-50%);
  z-index: 1000;
  overflow: hidden;
  cursor: pointer;

  width: 240px;
  height: 46px;
  border-radius: 23px;
  background: rgba(23, 20, 15, 0.92);
  border: 1px solid rgba(246, 241, 230, 0.14);
  backdrop-filter: blur(14px);
  box-shadow: var(--shadow-cap);
  transition:
    width 0.62s var(--ease-soft),
    height 0.62s var(--ease-soft),
    border-radius 0.62s var(--ease-soft),
    background 0.5s var(--ease-soft),
    border-color 0.5s var(--ease-soft),
    box-shadow 0.5s var(--ease-soft),
    bottom 0.45s var(--ease-soft);
}

.capsule.hover {
  width: 280px;
  background: rgba(23, 20, 15, 0.96);
  border-color: rgba(246, 241, 230, 0.26);
}

.capsule:active:not(.expanded) {
  transform: translateX(-50%) scale(0.975);
}

.capsule.expanded {
  width: min(540px, 94vw);
  height: min(640px, 82vh);
  border-radius: 22px;
  background: var(--paper-2);
  border: 1px solid var(--line);
  cursor: default;
  box-shadow: 0 30px 80px rgba(23, 20, 15, 0.32);
}

/* ---------- 常态内容 ---------- */
.capsule-idle {
  height: 100%;
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 0 16px 0 18px;
  color: #f6f1e6;
  user-select: none;
}

.pulse-dot {
  flex: none;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--gold);
  animation: pulse 2.8s infinite;
}

@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(184, 147, 90, 0.5); }
  70% { box-shadow: 0 0 0 9px rgba(184, 147, 90, 0); }
  100% { box-shadow: 0 0 0 0 rgba(184, 147, 90, 0); }
}

.quote-text {
  flex: 1;
  font-family: var(--font-serif);
  font-size: 13.5px;
  letter-spacing: 0.16em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  animation: quoteIn 0.62s var(--ease-soft);
}

@keyframes quoteIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: none; }
}

.hint {
  flex: none;
  font-size: 10px;
  letter-spacing: 0.24em;
  color: rgba(246, 241, 230, 0.55);
}

/* ---------- 面板 ---------- */
.capsule-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.panel-head {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--line);
}

.head-left {
  display: flex;
  align-items: center;
  gap: 11px;
}

.seal-dot {
  width: 30px;
  height: 30px;
  background: var(--seal);
  color: #fdf6ee;
  font-family: var(--font-serif);
  font-size: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.title {
  font-family: var(--font-serif);
  font-size: 15px;
  letter-spacing: 0.2em;
}

.sub {
  font-size: 8.5px;
  letter-spacing: 0.3em;
  color: var(--ink-3);
  line-height: 1.5;
}

.icon-btn {
  width: 28px;
  height: 28px;
  border: 1px solid var(--line);
  background: transparent;
  color: var(--ink-2);
  font-size: 15px;
  line-height: 1;
  transition: all 0.24s;
}

.icon-btn:hover {
  background: var(--ink);
  border-color: var(--ink);
  color: var(--paper-2);
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 18px 18px 8px;
  background: var(--paper-2);
}

.welcome {
  padding: 6px 2px 10px;
}

.welcome-title {
  margin: 0 0 6px;
  font-family: var(--font-serif);
  font-size: 16px;
  letter-spacing: 0.14em;
}

.welcome-sub {
  margin: 0 0 14px;
  font-size: 12px;
  letter-spacing: 0.08em;
  color: var(--ink-3);
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.chip {
  padding: 5px 12px;
  border: 1px solid var(--line);
  background: transparent;
  font-size: 12px;
  letter-spacing: 0.06em;
  color: var(--ink-2);
  transition: all 0.24s var(--ease-soft);
}

.chip:hover {
  background: var(--ink);
  border-color: var(--ink);
  color: var(--paper-2);
}

.msg {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}

.avatar {
  flex: none;
  width: 26px;
  height: 26px;
  font-family: var(--font-serif);
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--paper-3);
  color: var(--ink-2);
}

.msg.user {
  flex-direction: row-reverse;
}

.msg.user .avatar {
  background: var(--ink);
  color: var(--paper-2);
}

.bubble {
  max-width: 84%;
  padding: 2px 0;
  background: transparent;
  border: 0;
  font-size: 14px;
  word-break: break-word;
}

.msg.user .bubble {
  background: var(--ink);
  color: #f6f1e6;
  border-color: var(--ink);
  padding: 8px 14px;
  text-align: right;
}

.plain {
  font-family: var(--font-serif);
  font-size: 14.5px;
  letter-spacing: 0.05em;
  line-height: 1.85;
  white-space: pre-wrap;
}

.caret {
  display: inline-block;
  width: 6px;
  height: 14px;
  margin-left: 3px;
  background: var(--seal);
  vertical-align: -2px;
  animation: blink 1s steps(2) infinite;
}

@keyframes blink {
  50% { opacity: 0; }
}

.panel-foot {
  flex: none;
  display: flex;
  gap: 10px;
  align-items: flex-end;
  padding: 12px 14px;
  border-top: 1px solid var(--line);
  background: var(--paper-2);
}

.panel-foot textarea {
  flex: 1;
  resize: none;
  max-height: 96px;
  border-color: var(--line-soft);
}

.send {
  flex: none;
  height: 38px;
  padding: 0 18px;
  border: 1px solid var(--ink);
  background: var(--ink);
  color: var(--paper-2);
  font-size: 12.5px;
  letter-spacing: 0.16em;
  transition: all 0.24s;
}

.send:hover {
  background: var(--seal);
  border-color: var(--seal);
}

.send:disabled {
  background: transparent;
  border-color: var(--line);
  color: var(--ink-3);
  cursor: not-allowed;
}

.send.stop {
  background: transparent;
  color: var(--ink);
}

/* ---------- 内容切换 ---------- */
.panel-enter-active,
.panel-leave-active {
  transition: opacity 0.4s ease, transform 0.4s var(--ease-soft);
  transition-delay: 0.18s;
}

.panel-enter-from,
.panel-leave-to {
  opacity: 0;
  transform: translateY(12px);
}

</style>
