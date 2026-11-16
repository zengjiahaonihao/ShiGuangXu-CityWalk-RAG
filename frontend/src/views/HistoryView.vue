<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../api'
import MarkdownBlock from '../components/MarkdownBlock.vue'
import SourceList from '../components/SourceList.vue'
import PageHero from '../components/PageHero.vue'

const items = ref([])
const typeFilter = ref('')
const keyword = ref('')
const openId = ref('')

const filtered = computed(() => items.value)

const stats = computed(() => {
  const chats = items.value.filter((i) => i.type === 'chat').length
  const routes = items.value.filter((i) => i.type === 'route').length
  const cited = items.value.reduce((n, i) => n + (i.sources?.length || 0), 0)
  const cities = new Set(
    items.value
      .map((i) => (i.title || '').split(/[·\-—]/)[0].trim())
      .filter((t) => t && t.length <= 8)
  )
  return { chats, routes, cited, cities: cities.size }
})

function exportAll() {
  if (!items.value.length) return
  const body = items.value
    .map((it) => {
      const src = it.sources?.length
        ? '\n\n### 资料来源\n\n' + it.sources.map((s, i) => `[${i + 1}] 《${s.doc_name}》\n${s.text}`).join('\n\n')
        : ''
      return `# ${it.title}\n\n> ${it.type === 'route' ? '路线' : '对话'} · ${it.created_at}\n\n${it.content}${src}`
    })
    .join('\n\n---\n\n')
  const blob = new Blob([`# 拾光叙 · 漫步档案\n\n共 ${items.value.length} 条\n\n---\n\n${body}`], {
    type: 'text/markdown;charset=utf-8'
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = '拾光叙-漫步档案.md'
  a.click()
  URL.revokeObjectURL(url)
}

async function load() {
  items.value = await api.listHistory(typeFilter.value || null, keyword.value)
}

function toggle(id) {
  openId.value = openId.value === id ? '' : id
}

function plain(text) {
  return (text || '')
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/[#>*`_|~-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

async function copy(item) {
  try {
    await navigator.clipboard.writeText(item.content)
    alert('已复制到剪贴板')
  } catch (e) {
    alert('复制失败，请手动选择文本')
  }
}

function download(item) {
  const srcText = item.sources?.length
    ? '\n\n---\n\n## 资料来源\n\n' +
      item.sources.map((s, i) => `[${i + 1}] 《${s.doc_name}》\n${s.text}`).join('\n\n')
    : ''
  const blob = new Blob([`# ${item.title}\n\n> ${item.created_at}\n\n${item.content}${srcText}`], {
    type: 'text/markdown;charset=utf-8'
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${item.title.replace(/[\\/:*?"<>|]/g, '_')}.md`
  a.click()
  URL.revokeObjectURL(url)
}

async function remove(item) {
  if (!window.confirm('删除这条记录？')) return
  await api.deleteHistory(item.id)
  await load()
}

async function clearAll() {
  if (!window.confirm('清空全部历史记录？此操作不可恢复。')) return
  await api.clearHistory()
  await load()
}

let timer = null
watch(keyword, () => {
  window.clearTimeout(timer)
  timer = window.setTimeout(load, 280)
})
watch(typeFilter, load)

onMounted(load)
</script>

<template>
  <div class="page">
    <PageHero
      no="04"
      cn="历史记录"
      en="RECORD"
      lead="每一次提问、每一条路线都自动落档。展开可以回看当时的来源原文，也可以一键复制或导出成 Markdown 带走。"
      image="/cities/suzhou.webp"
    />

    <div class="page-bar">
      <p class="bar-lead">共 {{ items.length }} 条 · 按时间倒序</p>
      <div class="bar-tools">
        <button class="btn small" :disabled="!items.length" @click="exportAll">导出全部</button>
        <button class="btn small" @click="clearAll">清空</button>
      </div>
    </div>

    <section class="stats card">
      <div><b>{{ stats.chats }}</b><span>次提问</span></div>
      <div><b>{{ stats.routes }}</b><span>条路线</span></div>
      <div><b>{{ stats.cited }}</b><span>条引用片段</span></div>
      <div><b>{{ stats.cities }}</b><span>座城 / 主题</span></div>
    </section>

    <section class="filters card">
      <div class="tabs">
        <button class="btn small" :class="{ on: !typeFilter }" @click="typeFilter = ''">全部</button>
        <button class="btn small" :class="{ on: typeFilter === 'chat' }" @click="typeFilter = 'chat'">对话</button>
        <button class="btn small" :class="{ on: typeFilter === 'route' }" @click="typeFilter = 'route'">路线</button>
      </div>
      <input v-model="keyword" type="search" placeholder="搜索标题或内容" />
      <span class="count">共 {{ filtered.length }} 条</span>
    </section>

    <section v-if="filtered.length" class="list">
      <article v-for="item in filtered" :key="item.id" class="item card" :class="{ open: openId === item.id }">
        <div class="item-head" @click="toggle(item.id)">
          <span class="type" :class="item.type">{{ item.type === 'route' ? '路线' : '对话' }}</span>
          <b class="title">{{ item.title }}</b>
          <span class="time">{{ item.created_at }}</span>
          <span class="arrow">{{ openId === item.id ? '收起' : '展开' }}</span>
        </div>

        <div v-show="openId === item.id" class="item-body">
          <MarkdownBlock :content="item.content" />
          <SourceList v-if="item.sources?.length" :sources="item.sources" />
          <div class="item-tools">
            <button class="btn small" @click="copy(item)">复制</button>
            <button class="btn small" @click="download(item)">导出 MD</button>
            <button class="btn small danger" @click="remove(item)">删除</button>
          </div>
        </div>

        <p v-show="openId !== item.id" class="brief">{{ plain(item.content).slice(0, 88) }}…</p>
      </article>
    </section>
    <div v-else class="empty">还没有记录。去提问或生成一条路线，结果会自动保存在这里。</div>
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
  margin: 40px 0 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--line);
}

.bar-tools {
  display: flex;
  gap: 8px;
}

.stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1px;
  padding: 0;
  margin-bottom: 24px;
  background: var(--line);
  border: 1px solid var(--line);
  overflow: hidden;
}

.stats > div {
  background: var(--paper-2);
  padding: 20px 22px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.stats b {
  font-family: var(--font-serif);
  font-size: 26px;
  font-weight: 500;
  color: var(--ink);
}

.stats span {
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.2em;
  color: var(--muted-2);
}

@media (max-width: 720px) {
  .stats {
    grid-template-columns: repeat(2, 1fr);
  }
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

.filters {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 0 20px;
  margin-bottom: 6px;
  border-bottom: 1px solid var(--line);
  background: transparent;
  box-shadow: none;
}

.tabs {
  display: flex;
  gap: 8px;
}

.count {
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: 10.5px;
  letter-spacing: 0.2em;
  color: var(--muted);
}

.list {
  display: grid;
  gap: 0;
}

.item {
  padding: 26px 0;
  border-bottom: 1px solid var(--line);
  background: transparent;
  box-shadow: none;
}

.item:hover {
  background: rgba(168, 59, 44, 0.025);
}

.item-head {
  display: flex;
  align-items: center;
  gap: 14px;
  cursor: pointer;
}

.type {
  flex: none;
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.18em;
  padding: 3px 9px;
  border: 1px solid var(--line);
  color: var(--jade);
  border-radius: 0;
}

.type.route {
  border-color: rgba(168, 59, 44, 0.4);
  color: var(--seal);
  background: transparent;
}

.title {
  font-family: var(--font-serif);
  font-size: 16.5px;
  letter-spacing: 0.06em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.time {
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.14em;
  color: var(--muted-2);
}

.arrow {
  flex: none;
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.16em;
  color: var(--jade);
}

.brief {
  margin: 8px 0 0;
  font-size: 12.5px;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-body {
  margin-top: 22px;
  padding-top: 22px;
  border-top: 1px dashed var(--line);
}

.item-tools {
  display: flex;
  gap: 10px;
  margin-top: 22px;
}

.empty {
  padding: 90px 0;
}
</style>
