<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api, streamPost } from '../api'
import MarkdownBlock from '../components/MarkdownBlock.vue'
import SourceList from '../components/SourceList.vue'
import PageHero from '../components/PageHero.vue'

const route = useRoute()

const docs = ref([])
const categories = ref([])
const catFilter = ref('')
const selectedDocIds = ref([])
const topK = ref(5)

const messages = ref([])
const input = ref('')
const loading = ref(false)
const scrollRef = ref(null)
const inputRef = ref(null)
let stopStream = null

const SUGGEST = [
  '这条老街的历史沿革是怎样的？',
  '关于这座古建筑有哪些记载？',
  '当地流传着哪些民间传说？',
  '有哪些值得记录的非遗手艺？'
]

const scopeText = computed(() => {
  if (selectedDocIds.value.length) return `${selectedDocIds.value.length} 篇指定文档`
  if (catFilter.value) return `分类：${catFilter.value}`
  return '全部资料'
})

async function loadMeta() {
  try {
    docs.value = await api.listDocs()
    const c = await api.categories()
    categories.value = c?.categories || []
  } catch (e) { /* ignore */ }
}

function toggleDoc(id) {
  const i = selectedDocIds.value.indexOf(id)
  if (i >= 0) selectedDocIds.value.splice(i, 1)
  else selectedDocIds.value.push(id)
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
  stopStream = streamPost('/chat/stream', {
    question,
    doc_ids: selectedDocIds.value,
    category: catFilter.value || null,
    top_k: topK.value
  }, {
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
    },
    onError: (err) => {
      target.pending = false
      target.content = `⚠️ ${err.message}`
      loading.value = false
      stopStream = null
    }
  })
}

function stop() {
  stopStream?.()
  stopStream = null
  loading.value = false
  const last = messages.value[messages.value.length - 1]
  if (last?.pending) last.pending = false
}

function newChat() {
  stop()
  messages.value = []
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    send()
  }
}

onMounted(async () => {
  await loadMeta()
  // 从城市档案页「就这座城提问」跳过来：自动带上问题
  const q = route.query.q
  if (q) send(String(q))
})
</script>

<template>
  <div class="page">
    <PageHero
      no="02"
      cn="漫步对话"
      en="DIALOGUE"
      lead="带着问题走进一条街：先在你的资料里找到证据，再让模型把它讲成一段话。每条回答都附来源原文，可以逐句回溯核对。"
      image="/cities/fuzhou.webp"
    />

    <div class="page-bar">
      <p class="bar-lead">检索范围 · 可随时限定到某一篇史料</p>
      <button class="btn small" @click="newChat">新建会话</button>
    </div>

    <section class="scope card">
      <div class="scope-row">
        <span class="scope-label">检索范围</span>
        <select v-model="catFilter" @change="selectedDocIds = []">
          <option value="">全部分类</option>
          <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
        </select>
        <span class="scope-label">参考片段</span>
        <select v-model.number="topK">
          <option :value="3">3 条</option>
          <option :value="5">5 条</option>
          <option :value="8">8 条</option>
        </select>
        <span class="scope-now">当前：{{ scopeText }}</span>
      </div>
      <div v-if="docs.length" class="doc-chips">
        <button
          v-for="d in docs"
          :key="d.id"
          class="chip"
          :class="{ on: selectedDocIds.includes(d.id) }"
          @click="toggleDoc(d.id)"
        >{{ d.name }}</button>
      </div>
      <p v-else class="scope-empty">知识库为空，先去「知识库」页上传史料吧。</p>
    </section>

    <section ref="scrollRef" class="stream card">
      <div v-if="!messages.length" class="welcome">
        <p class="w-title">想问哪条街、哪座楼、哪个传说？</p>
        <div class="chips">
          <button v-for="s in SUGGEST" :key="s" class="chip" @click="send(s)">{{ s }}</button>
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
    </section>

    <section class="composer card">
      <textarea
        ref="inputRef"
        v-model="input"
        rows="2"
        placeholder="输入地点或问题，例如：骑楼街的由来是什么？Enter 发送，Shift+Enter 换行"
        @keydown="onKeydown"
      ></textarea>
      <div class="composer-bar">
        <span class="tip">回答来自你的资料 + DeepSeek，资料未记载时会明确说明</span>
        <button v-if="!loading" class="btn primary" :disabled="!input.trim()" @click="send()">发送</button>
        <button v-else class="btn" @click="stop">停止生成</button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 20px;
  padding-bottom: 24px;
  margin-bottom: 40px;
  border-bottom: 1px solid var(--line);
}

.page-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin: 40px 0 18px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--line);
}

.bar-lead {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.24em;
  color: var(--muted-2);
}

.page-head h1 {
  font-family: var(--font-serif);
  font-size: 30px;
  letter-spacing: 0.18em;
  margin: 0 0 10px;
  font-weight: 500;
}

.page-head p {
  margin: 0;
  font-size: 13px;
  letter-spacing: 0.1em;
  color: var(--muted);
}

.scope {
  padding: 0 0 24px;
  border-bottom: 1px solid var(--line-soft);
  margin-bottom: 8px;
}

.scope-row {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.scope-label {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.22em;
  color: var(--muted);
}

.scope-now {
  margin-left: auto;
  font-size: 12px;
  letter-spacing: 0.1em;
  color: var(--jade);
}

.doc-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}

.chip {
  padding: 5px 13px;
  border: 1px solid var(--line);
  border-radius: 0;
  background: transparent;
  font-size: 12px;
  letter-spacing: 0.08em;
  color: var(--ink-soft);
  transition: all 0.3s var(--ease-soft);
}

.chip:hover {
  border-color: var(--seal);
  color: var(--seal);
}

.chip.on {
  background: var(--ink);
  border-color: var(--ink);
  color: var(--paper-light);
}

.scope-empty {
  margin: 10px 0 0;
  font-size: 12.5px;
  color: var(--muted);
}

.stream {
  flex: 1;
  min-height: 300px;
  max-height: 50vh;
  overflow-y: auto;
  padding: 28px 0;
  background: transparent;
}

.welcome {
  padding: 10px 0;
}

.w-title {
  font-family: var(--font-serif);
  font-size: 18px;
  letter-spacing: 0.1em;
  margin: 0 0 16px;
}

.welcome .chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.msg {
  display: flex;
  gap: 16px;
  margin-bottom: 30px;
}

.avatar {
  flex: none;
  width: 30px;
  height: 30px;
  border: 1px solid var(--line);
  border-radius: 0;
  font-family: var(--font-serif);
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: var(--ink-soft);
}

.msg.user {
  flex-direction: row-reverse;
}

.msg.user .avatar {
  background: var(--ink);
  border-color: var(--ink);
  color: var(--paper-light);
}

.bubble {
  max-width: 82%;
  padding: 0;
  border: 0;
  background: transparent;
  word-break: break-word;
}

.msg.user .bubble {
  background: transparent;
  color: var(--ink);
  text-align: right;
}

.plain {
  display: inline-block;
  font-family: var(--font-serif);
  font-size: 15.5px;
  letter-spacing: 0.05em;
  line-height: 1.9;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--line);
  text-align: left;
  white-space: pre-wrap;
}

.caret {
  display: inline-block;
  width: 7px;
  height: 15px;
  margin-left: 3px;
  background: var(--seal);
  vertical-align: -2px;
  animation: blink 1s steps(2) infinite;
}

@keyframes blink {
  50% { opacity: 0; }
}

.composer {
  padding: 22px 0 0;
  border-top: 1px solid var(--line);
  background: transparent;
}

.composer textarea {
  width: 100%;
  resize: none;
  border: 0;
  border-bottom: 1px solid var(--line);
  border-radius: 0;
  outline: none;
  padding: 10px 0;
  font-size: 14px;
  line-height: 1.8;
  background: transparent;
  max-height: 140px;
}

.composer textarea:focus {
  box-shadow: none;
  border-bottom-color: var(--seal);
}

.composer-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 16px;
}

.tip {
  font-size: 11.5px;
  letter-spacing: 0.08em;
  color: var(--muted);
}
</style>
