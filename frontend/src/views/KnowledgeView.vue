<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import PageHero from '../components/PageHero.vue'

const emit = defineEmits(['stats-change'])

const docs = ref([])
const cities = ref([])
const tab = ref('builtin')
const categories = ref(['老街史料', '古建筑', '地方传说', '非遗手记', '人物口述', '其他'])
const filter = ref('')
const catFilter = ref('')
const category = ref('老街史料')
const uploading = ref(false)
const progress = ref('')
const dragging = ref(false)
const stats = ref(null)
const fileInput = ref(null)
const syncing = ref(false)

const region = ref('')

const builtinDocs = computed(() => docs.value.filter((d) => d.origin === 'builtin'))
const mineDocs = computed(() => docs.value.filter((d) => d.origin !== 'builtin'))

const regions = computed(() => [...new Set(cities.value.map((c) => c.region).filter(Boolean))])
const cityList = computed(() =>
  region.value ? cities.value.filter((c) => c.region === region.value) : cities.value
)

const heroMeta = computed(() =>
  stats.value
    ? [
        { k: 'DOCUMENTS', v: stats.value.doc_count },
        { k: 'CHUNKS', v: stats.value.chunk_count },
        { k: 'VECTOR', v: stats.value.vector_backend }
      ]
    : []
)

const filtered = computed(() => {
  let list = tab.value === 'builtin' ? builtinDocs.value : mineDocs.value
  if (catFilter.value) {
    list = list.filter((d) => d.category === catFilter.value)
  }
  if (filter.value) {
    const kw = filter.value.toLowerCase()
    list = list.filter((d) => (d.name + d.category).toLowerCase().includes(kw))
  }
  return list
})

async function load() {
  docs.value = await api.listDocs()
  stats.value = await api.stats()
  try {
    cities.value = (await api.cities()).cities || []
  } catch (e) { /* ignore */ }
}

async function resync() {
  syncing.value = true
  try {
    await api.syncBuiltin(true)
    await load()
    emit('stats-change')
  } catch (e) {
    progress.value = `重建失败：${e.message}`
  }
  syncing.value = false
}

async function loadCategories() {
  try {
    const d = await api.categories()
    if (d?.categories?.length) categories.value = d.categories
  } catch (e) { /* ignore */ }
}

async function uploadFiles(fileList) {
  if (!fileList?.length) return
  uploading.value = true
  let ok = 0
  for (const file of fileList) {
    progress.value = `正在解析《${file.name}》…`
    try {
      await api.uploadDoc(file, category.value)
      ok += 1
    } catch (e) {
      progress.value = `《${file.name}》失败：${e.message}`
      await new Promise((r) => setTimeout(r, 1400))
    }
  }
  progress.value = ok ? `完成 ${ok} 篇入库` : ''
  uploading.value = false
  await load()
  emit('stats-change')
  setTimeout(() => (progress.value = ''), 2600)
}

function onPick(e) {
  uploadFiles(Array.from(e.target.files || []))
  e.target.value = ''
}

function onDrop(e) {
  dragging.value = false
  uploadFiles(Array.from(e.dataTransfer?.files || []))
}

async function changeCategory(doc) {
  await api.updateDoc(doc.id, { category: doc.category })
  await load()
}

async function remove(doc) {
  if (!window.confirm(`确定删除《${doc.name}》？该文档的向量片段会一并移除。`)) return
  await api.deleteDoc(doc.id)
  await load()
  emit('stats-change')
}

async function clearAll() {
  if (!window.confirm('确定清空整个知识库？此操作不可恢复。')) return
  await api.clearDocs()
  await load()
  emit('stats-change')
}

function sizeText(n) {
  if (!n) return '-'
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

onMounted(async () => {
  await loadCategories()
  await load()
})
</script>

<template>
  <div class="page">
    <PageHero
      no="01"
      cn="知识库"
      en="ARCHIVE"
      lead="内置全国人文档案常驻可用：三十余座名城古街、十余篇专题通识，开箱即可提问。你也可以上传自己的老街史料、古建筑介绍、地方传说与非遗手记，与内置库一起参与检索。"
      image="/cities/quanzhou.webp"
      :meta="heroMeta"
    />

    <!-- 内置人文库：全国档案陈列 -->
    <section class="builtin">
      <div class="bi-head">
        <h2>内置人文档案</h2>
        <span class="bi-sub">{{ cities.length }} 座名城古街 · 公开资料整理</span>
        <button class="btn small ghost" :disabled="syncing" @click="resync">
          {{ syncing ? '重建中…' : '重建索引' }}
        </button>
      </div>

      <div class="region-tabs">
        <button
          class="btn small"
          :class="{ on: !region }"
          @click="region = ''"
        >全部 · {{ cities.length }}</button>
        <button
          v-for="r in regions"
          :key="r"
          class="btn small"
          :class="{ on: region === r }"
          @click="region = region === r ? '' : r"
        >{{ r }}</button>
      </div>

      <div v-if="cityList.length" class="city-grid">
        <router-link
          v-for="c in cityList"
          :key="c.id"
          class="city-card"
          :class="{ off: !c.ingested }"
          :to="`/city/${c.id}`"
        >
          <div class="city-img">
            <img :src="c.image" :alt="c.city + c.title" loading="lazy" />
            <span class="city-tag">{{ c.district }}</span>
          </div>
          <div class="city-body">
            <h3>{{ c.city }}<em>{{ c.title }}</em></h3>
            <p class="city-sum">{{ c.summary }}</p>
            <ul class="city-tags">
              <li v-for="t in c.tags.slice(0, 3)" :key="t">{{ t }}</li>
            </ul>
            <div class="city-foot">
              <span>{{ c.chunks }} 片段 · {{ c.walk }}</span>
              <span class="go">看简介 →</span>
            </div>
          </div>
        </router-link>
      </div>
      <div v-else class="bi-empty">正在载入内置人文库…</div>

      <p class="bi-note">
        文史档案整理自各地政府门户、官方景区与主流媒体报道，篇末均标注出处；
        配图取自 Pexels 免费商用图库，为区域氛围示意图，非对应街区的实拍。
      </p>
    </section>

    <section
      class="drop card"
      :class="{ dragging, busy: uploading }"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="onDrop"
      @click="fileInput?.click()"
    >
      <div class="drop-icon">＋</div>
      <div class="drop-text">
        <b>拖入文件或点击选择</b>
        <span>支持 txt / md / pdf / docx，单文件不超过 20MB</span>
      </div>
      <div class="drop-cat" @click.stop>
        <label>归类为</label>
        <select v-model="category">
          <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
        </select>
      </div>
      <input ref="fileInput" type="file" multiple hidden accept=".txt,.md,.markdown,.pdf,.docx" @change="onPick" />
    </section>

    <p v-if="progress" class="progress">{{ progress }}</p>

    <section class="list-head">
      <div class="filters">
        <button class="btn small" :class="{ on: tab === 'builtin' }" @click="tab = 'builtin'; catFilter = ''">
          内置 · {{ builtinDocs.length }}
        </button>
        <button class="btn small" :class="{ on: tab === 'mine' }" @click="tab = 'mine'; catFilter = ''">
          我的上传 · {{ mineDocs.length }}
        </button>
        <span class="sep"></span>
        <button class="btn small" :class="{ on: !catFilter }" @click="catFilter = ''">全部分类</button>
        <button
          v-for="c in categories"
          :key="c"
          class="btn small"
          :class="{ on: catFilter === c }"
          @click="catFilter = catFilter === c ? '' : c"
        >{{ c }}</button>
      </div>
      <div class="list-tools">
        <input v-model="filter" type="search" placeholder="搜索文档名" />
        <button v-if="tab === 'mine'" class="btn small danger" @click="clearAll">清空上传</button>
      </div>
    </section>

    <section v-if="filtered.length" class="doc-list">
      <article v-for="d in filtered" :key="d.id" class="doc card" :class="{ bi: d.origin === 'builtin' }">
        <div class="doc-main">
          <div class="doc-title">
            <span class="ext">{{ (d.ext || '').replace('.', '').toUpperCase() || 'DOC' }}</span>
            <b>{{ d.name }}</b>
            <span v-if="d.origin === 'builtin'" class="badge">内置</span>
            <span v-if="d.city" class="badge city">{{ d.city }}</span>
          </div>
          <p class="preview">{{ d.preview || '（无预览）' }}</p>
          <div class="doc-meta">
            <span>{{ sizeText(d.size) }}</span>
            <span>{{ d.chunks }} 个片段</span>
            <span>{{ d.created_at }}</span>
            <span v-if="d.source" class="src">{{ d.source }}</span>
          </div>
        </div>
        <div class="doc-side">
          <select v-model="d.category" @change="changeCategory(d)">
            <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
          </select>
          <button class="btn small danger" @click="remove(d)">删除</button>
        </div>
      </article>
    </section>
    <div v-else class="empty">
      {{ tab === 'builtin' ? '内置人文库为空，点上方「重建索引」导入。' : '还没有上传资料。上传第一篇史料，开始搭建你的城市记忆库。' }}
    </div>
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

.drop {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 30px 34px;
  margin-bottom: 10px;
  border: 1px dashed var(--line);
  background: transparent;
  cursor: pointer;
  transition: all 0.4s var(--ease-soft);
}

.drop:hover,
.drop.dragging {
  border-color: var(--seal);
  background: rgba(168, 59, 44, 0.04);
}

.drop.busy {
  opacity: 0.6;
  pointer-events: none;
}

.drop-icon {
  flex: none;
  width: 46px;
  height: 46px;
  border: 1px solid var(--line);
  color: var(--seal);
  font-size: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.drop-text {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.drop-text b {
  font-family: var(--font-serif);
  font-size: 15px;
  letter-spacing: 0.06em;
}

.drop-text span {
  font-size: 12.5px;
  color: var(--muted);
}

.drop-cat {
  display: flex;
  align-items: center;
  gap: 10px;
}

.drop-cat label {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.22em;
  color: var(--muted);
}

.head-stats {
  display: flex;
  gap: 34px;
  text-align: right;
}

.head-stats b {
  display: block;
  font-family: var(--font-serif);
  font-size: 24px;
  font-weight: 500;
}

.head-stats span {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.3em;
  color: var(--muted-2);
}

.progress {
  margin: 0 0 18px;
  font-size: 12.5px;
  letter-spacing: 0.1em;
  color: var(--jade);
}

.list-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin: 44px 0 4px;
}

.filters {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.list-tools {
  display: flex;
  gap: 12px;
  align-items: center;
}

.list-tools input {
  width: 200px;
}

.doc-list {
  border-top: 1px solid var(--line);
}

.doc {
  display: flex;
  gap: 24px;
  align-items: center;
  padding: 26px 0;
  border-bottom: 1px solid var(--line);
  background: transparent;
  box-shadow: none;
  transition: background 0.4s var(--ease-soft);
}

.doc:hover {
  background: rgba(168, 59, 44, 0.03);
}

.doc-main {
  flex: 1;
  min-width: 0;
}

.doc-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.doc-title b {
  font-family: var(--font-serif);
  font-size: 17px;
  letter-spacing: 0.04em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ext {
  flex: none;
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.18em;
  padding: 3px 8px;
  border: 1px solid var(--line);
  color: var(--muted);
}

.preview {
  margin: 8px 0;
  font-size: 12.5px;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-meta {
  display: flex;
  gap: 20px;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.14em;
  color: var(--muted-2);
}

.doc-side {
  flex: none;
  display: flex;
  gap: 10px;
  align-items: center;
}

.empty {
  padding: 80px 0;
}

/* ---------- 内置人文库：六城陈列 ---------- */
.builtin {
  margin-bottom: 72px;
}

.bi-head {
  display: flex;
  align-items: baseline;
  gap: 14px;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 32px;
}

.bi-head h2 {
  margin: 0;
  font-family: var(--font-serif);
  font-size: 26px;
  letter-spacing: 0.14em;
  font-weight: 500;
}

.bi-sub {
  flex: 1;
  font-size: 12px;
  letter-spacing: 0.16em;
  color: var(--muted-2);
}

.btn.ghost {
  background: transparent;
  border-color: var(--line);
  color: var(--muted);
}

.btn.ghost:hover {
  border-color: var(--seal-soft);
  color: var(--seal);
}

.region-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 28px;
}

.city-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 28px;
}

.city-card {
  display: block;
  color: inherit;
  text-decoration: none;
  border: 1px solid var(--line);
  background: var(--paper-2);
  cursor: pointer;
  overflow: hidden;
  transition: transform 0.5s var(--ease-soft), box-shadow 0.5s var(--ease-soft);
}

.city-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 20px 46px rgba(23, 20, 15, 0.13);
}

.city-card.off {
  opacity: 0.45;
  pointer-events: none;
}

.city-img {
  position: relative;
  aspect-ratio: 4 / 3;
  overflow: hidden;
  background: var(--paper-3);
}

.city-img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  filter: saturate(0.9) contrast(1.02);
  transition: transform 1.2s var(--ease-soft);
}

.city-card:hover .city-img img {
  transform: scale(1.04);
}

.city-tag {
  position: absolute;
  left: 14px;
  bottom: 12px;
  padding: 3px 9px;
  background: rgba(24, 20, 14, 0.62);
  color: #f6f1e6;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.18em;
  backdrop-filter: blur(4px);
}

.city-body {
  padding: 20px 20px 18px;
}

.city-body h3 {
  margin: 0 0 8px;
  font-family: var(--font-serif);
  font-size: 19px;
  letter-spacing: 0.12em;
  font-weight: 500;
}

.city-body h3 em {
  font-style: normal;
  font-size: 12px;
  letter-spacing: 0.16em;
  color: var(--muted);
  margin-left: 10px;
}

.city-sum {
  margin: 0 0 12px;
  font-size: 12.5px;
  line-height: 1.9;
  color: var(--muted);
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.city-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0 0 14px;
  padding: 0;
  list-style: none;
}

.city-tags li {
  font-size: 10px;
  letter-spacing: 0.1em;
  color: var(--muted-2);
  border: 1px solid var(--line);
  padding: 2px 7px;
}

.city-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.14em;
  color: var(--muted-2);
}

.city-foot .go {
  color: var(--seal);
}

.bi-empty {
  padding: 40px 0;
  color: var(--muted-2);
  font-size: 13px;
}

.bi-note {
  margin: 24px 0 0;
  font-family: var(--font-mono);
  font-size: 10px;
  line-height: 2;
  letter-spacing: 0.06em;
  color: var(--muted-2);
}

/* 文档条目 */
.doc.bi {
  background: linear-gradient(90deg, rgba(178, 46, 38, 0.035), transparent 40%);
}

.badge {
  flex: none;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.16em;
  padding: 2px 7px;
  border: 1px solid var(--seal-soft);
  color: var(--seal);
}

.badge.city {
  border-color: var(--line);
  color: var(--muted-2);
}

.sep {
  width: 1px;
  height: 14px;
  background: var(--line);
  align-self: center;
  margin: 0 4px;
}

@media (max-width: 1080px) {
  .city-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 720px) {
  .city-grid { grid-template-columns: 1fr; gap: 20px; }
  .bi-head { flex-wrap: wrap; }
}
</style>
