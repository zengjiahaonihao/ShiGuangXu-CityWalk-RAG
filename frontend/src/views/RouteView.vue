<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api, streamPost } from '../api'
import MarkdownBlock from '../components/MarkdownBlock.vue'
import SourceList from '../components/SourceList.vue'
import PageHero from '../components/PageHero.vue'
import TripMapGl from '../map/TripMapGl.vue'

const route = useRoute()

const docs = ref([])
const cities = ref([])
const categories = ref([])
const catFilter = ref('')
const selectedDocIds = ref([])
const quickCity = ref('')

const form = ref({
  city: '',
  theme: '',
  duration: '半日',
  pace: '悠闲',
  transport: '步行为主',
  extra: ''
})

const THEMES = ['老街烟火', '古建寻踪', '非遗手艺', '市井味道', '红色记忆', '江河水岸']
const DURATIONS = ['2 小时', '半日', '一日']
const PACES = ['悠闲', '适中', '紧凑']

const content = ref('')
const sources = ref([])
const loading = ref(false)
const historyId = ref('')
let stopStream = null

const canGenerate = computed(() => !loading.value)

/* ---------------- 路线地图 ---------------- */
const mapRef = ref(null)
const mapStops = ref([])
const highlight = ref(null)

const citySpots = computed(() => {
  const kw = (form.value.city || '').trim()
  if (!kw) return []
  const c = cities.value.find((x) => x.city === kw || kw.includes(x.city) || x.city.includes(kw))
  return c?.spots || []
})

const mapPlan = computed(() =>
  mapStops.value.length
    ? { days: [{ day: 1, activities: mapStops.value.map((s, i) => ({ ...s, time: String(i + 1).padStart(2, '0') })) }] }
    : null
)

const norm = (t) => String(t || '').replace(/[\s·、，,。.（）()《》「」—\-–|]/g, '')

function extractTitles(text) {
  const out = []
  text.split('\n').forEach((line) => {
    const m = line.match(/^#{3,4}\s*([①-⑳0-9]+)?[.、．]?\s*(.+)$/)
    if (!m) return
    const raw = m[2].split(/——|——|—|\s-\s/)[0].replace(/^[·、\s]+/, '').trim()
    if (raw && raw.length <= 30) out.push(raw)
  })
  return out
}

function buildMap() {
  if (!content.value) {
    mapStops.value = []
    return
  }
  const titles = extractTitles(content.value)
  const pool = citySpots.value
  const picked = []
  titles.forEach((t) => {
    const nt = norm(t)
    const hit = pool.find((s) => {
      const ns = norm(s.name)
      return ns && (ns.includes(nt) || nt.includes(ns))
    })
    if (hit && !picked.some((p) => p.name === hit.name)) picked.push({ ...hit, title: t })
  })
  if (picked.length < 2) {
    picked.length = 0
    pool.slice(0, 5).forEach((s) => picked.push({ ...s, title: s.name }))
  }
  mapStops.value = picked.map((s) => ({ title: s.title, lat: s.lat, lng: s.lng }))
  highlight.value = null
}

function onPickStop({ index }) {
  highlight.value = { day: 1, index }
  mapRef.value?.flyTo(1, index)
}

function flyToStop(i) {
  highlight.value = { day: 1, index: i }
  mapRef.value?.flyTo(1, i)
}


async function loadMeta() {
  try {
    docs.value = await api.listDocs()
    const c = await api.categories()
    categories.value = c?.categories || []
    cities.value = (await api.cities()).cities || []
  } catch (e) { /* ignore */ }

  // 从知识库页「生成路线」跳转过来：带上城市与对应文档
  const qCity = route.query.city
  const qDoc = route.query.doc
  if (qCity) {
    form.value.city = String(qCity)
    quickCity.value = String(qCity)
  }
  if (qDoc) selectedDocIds.value = [String(qDoc)]

  // 从城市档案页跳过来：先把这座城的看点铺到地图上
  const hit = cities.value.find((x) => x.city === form.value.city)
  if (hit?.spots?.length) {
    mapStops.value = hit.spots.slice(0, 5).map((s) => ({ title: s.name, lat: s.lat, lng: s.lng }))
  }
}

function pickCity(city) {
  const on = quickCity.value === city.city
  quickCity.value = on ? '' : city.city
  form.value.city = quickCity.value
  selectedDocIds.value = on ? [] : [city.doc_id]
  if (!on && !form.value.theme) form.value.theme = city.tags?.[0] || ''
  // 立即把这座城可定位的看点铺到地图上，先把方位感给出来
  mapStops.value = on
    ? []
    : (city.spots || []).slice(0, 5).map((s) => ({ title: s.name, lat: s.lat, lng: s.lng }))
  highlight.value = null
}

function toggleDoc(id) {
  const i = selectedDocIds.value.indexOf(id)
  if (i >= 0) selectedDocIds.value.splice(i, 1)
  else selectedDocIds.value.push(id)
}

function generate() {
  if (loading.value) return
  content.value = ''
  sources.value = []
  historyId.value = ''
  loading.value = true
  stopStream = streamPost('/route/stream', {
    ...form.value,
    doc_ids: selectedDocIds.value,
    category: catFilter.value || null,
    top_k: 8
  }, {
    onSources: (s) => (sources.value = s),
    onDelta: (t) => (content.value += t),
    onDone: (data) => {
      loading.value = false
      historyId.value = data?.history_id || ''
      buildMap()
    },
    onError: (err) => {
      loading.value = false
      content.value = `⚠️ ${err.message}`
    }
  })
}

function stop() {
  stopStream?.()
  stopStream = null
  loading.value = false
}

async function copyText() {
  try {
    await navigator.clipboard.writeText(content.value)
    alert('已复制到剪贴板')
  } catch (e) {
    alert('复制失败，请手动选择文本')
  }
}

function download() {
  const title = `${form.value.city || 'Citywalk'}·${form.value.theme || '人文漫步'}路线`
  const srcText = sources.value.length
    ? '\n\n---\n\n## 资料来源\n\n' +
      sources.value.map((s, i) => `[${i + 1}] 《${s.doc_name}》\n${s.text}`).join('\n\n')
    : ''
  const blob = new Blob([`# ${title}\n\n${content.value}${srcText}`], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${title}.md`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(loadMeta)
</script>

<template>
  <div class="page">
    <PageHero
      no="03"
      cn="路线生成"
      en="ROUTE"
      lead="先选一座城或一个主题，再挑几篇史料——路线里的每一个落脚点、每一段典故，都出自资料本身，文末附来源可核对。"
      image="/cities/pingyao.webp"
    />

    <div class="page-bar">
      <p class="bar-lead">漫步设定 · 地点全部来自知识库</p>
      <span v-if="historyId" class="tag seal">已自动存入历史记录</span>
    </div>

    <section class="map-sec">
      <div class="map-head">
        <div>
          <h2>路线地图</h2>
          <p>落脚点按漫步顺序编号；先选一座内置城市，或生成路线后自动把地点标上来。</p>
        </div>
        <span class="map-meta" v-if="mapStops.length">{{ mapStops.length }} 个落脚点 · 点击编号定位</span>
      </div>

      <div class="map-shell">
        <div v-if="mapPlan" class="map-canvas">
          <TripMapGl
            ref="mapRef"
            :plan="mapPlan"
            :active-day="1"
            :pad-right="28"
            theme="light"
            @select="onPickStop"
          />
        </div>
        <div v-else class="map-empty">
          <p>地图待命</p>
          <span>在上方选一座城，或点击「生成路线」，地点会按顺序编号落到地图上。</span>
        </div>
      </div>

      <div v-if="mapStops.length" class="map-stops">
        <button
          v-for="(s, i) in mapStops"
          :key="s.title + i"
          class="map-stop"
          :class="{ on: highlight?.index === i }"
          @click="flyToStop(i)"
        >
          <span class="ms-no">{{ String(i + 1).padStart(2, '0') }}</span>
          <span class="ms-t">{{ s.title }}</span>
        </button>
        <p class="map-note">底图 © 高德地图 · 数据 © OpenStreetMap contributors</p>
      </div>
    </section>

    <div class="grid">
      <section class="card form-card">
        <h2>漫步设定</h2>

        <div v-if="cities.length" class="field">
          <label>从内置人文库选一座城</label>
          <div class="city-pick">
            <button
              v-for="c in cities"
              :key="c.id"
              class="city-pill"
              :class="{ on: quickCity === c.city }"
              @click="pickCity(c)"
            >
              <img :src="c.image" :alt="c.city" loading="lazy" />
              <span>{{ c.city }}<em>{{ c.title }}</em></span>
            </button>
          </div>
          <p class="hint">选中后自动把该城的文史档案作为资料来源；也可清空后自己填写城市。</p>
        </div>

        <div class="field">
          <label>城市 / 街区</label>
          <input v-model="form.city" type="text" placeholder="如：泉州古城、上下杭" />
        </div>

        <div class="field">
          <label>主题偏好</label>
          <div class="chips">
            <button
              v-for="t in THEMES"
              :key="t"
              class="chip"
              :class="{ on: form.theme === t }"
              @click="form.theme = form.theme === t ? '' : t"
            >{{ t }}</button>
          </div>
        </div>

        <div class="row">
          <div class="field">
            <label>时长</label>
            <select v-model="form.duration">
              <option v-for="d in DURATIONS" :key="d" :value="d">{{ d }}</option>
            </select>
          </div>
          <div class="field">
            <label>节奏</label>
            <select v-model="form.pace">
              <option v-for="p in PACES" :key="p" :value="p">{{ p }}</option>
            </select>
          </div>
          <div class="field">
            <label>交通</label>
            <select v-model="form.transport">
              <option>步行为主</option>
              <option>步行 + 公交</option>
              <option>步行 + 骑行</option>
            </select>
          </div>
        </div>

        <div class="field">
          <label>资料范围</label>
          <select v-model="catFilter" @change="selectedDocIds = []">
            <option value="">全部分类</option>
            <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
          </select>
          <div v-if="docs.length" class="doc-chips">
            <button
              v-for="d in docs"
              :key="d.id"
              class="chip"
              :class="{ on: selectedDocIds.includes(d.id) }"
              @click="toggleDoc(d.id)"
            >{{ d.name }}</button>
          </div>
          <p v-else class="hint">尚未上传资料，仍可生成，但引用来源会为空。</p>
        </div>

        <div class="field">
          <label>补充说明</label>
          <textarea v-model="form.extra" rows="3" placeholder="如：想多安排手艺人访谈、避开陡坡"></textarea>
        </div>

        <div class="actions">
          <button v-if="!loading" class="btn primary" :disabled="!canGenerate" @click="generate">生成路线</button>
          <button v-else class="btn" @click="stop">停止生成</button>
        </div>
      </section>

      <section class="card result-card">
        <div class="result-head">
          <h2>漫步方案</h2>
          <div v-if="content" class="tools">
            <button class="btn small" @click="copyText">复制</button>
            <button class="btn small" @click="download">导出 MD</button>
          </div>
        </div>

        <div class="result-body">
          <div v-if="!content && !loading" class="empty">
            设定好条件后点击「生成路线」，方案会在这里流式呈现。
          </div>
          <div v-else class="result-scroll">
            <MarkdownBlock :content="content" />
            <span v-if="loading" class="caret"></span>
            <SourceList v-if="!loading && sources.length" :sources="sources" />
          </div>
        </div>
      </section>
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

.page-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin: 40px 0 24px;
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

.grid {
  display: grid;
  grid-template-columns: 0.85fr 1.15fr;
  gap: 0;
  align-items: start;
}

.form-card {
  padding: 0 40px 0 0;
  border-right: 1px solid var(--line);
  background: transparent;
  box-shadow: none;
}

.result-card {
  padding: 0 0 0 40px;
  background: transparent;
  box-shadow: none;
}

h2 {
  font-family: var(--font-serif);
  font-size: 20px;
  letter-spacing: 0.16em;
  font-weight: 500;
  margin: 0 0 28px;
}

.field {
  margin-bottom: 26px;
}

.field label {
  display: block;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.22em;
  color: var(--muted);
  margin-bottom: 8px;
}

.row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.chips,
.doc-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

/* 三十篇档案全列出来太长，给个可滚动的框，别把地图顶到很远 */
.doc-chips {
  max-height: 128px;
  overflow-y: auto;
  padding-right: 6px;
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

.hint {
  margin: 10px 0 0;
  font-size: 12px;
  color: var(--muted);
}

.actions {
  margin-top: 10px;
}

.result-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 14px;
  margin-bottom: 22px;
  border-bottom: 1px solid var(--line);
}

.result-head h2 {
  margin: 0;
}

.tools {
  display: flex;
  gap: 8px;
}

.result-body {
  min-height: 380px;
}

.result-scroll {
  max-height: 56vh;
  overflow-y: auto;
  padding-right: 6px;
}

.caret {
  display: inline-block;
  width: 7px;
  height: 15px;
  background: var(--seal);
  animation: blink 1s steps(2) infinite;
}

@keyframes blink {
  50% { opacity: 0; }
}

@media (max-width: 1100px) {
  .grid {
    grid-template-columns: 1fr;
  }
  .form-card {
    padding: 0 0 40px;
    border-right: 0;
    border-bottom: 1px solid var(--line);
  }
  .result-card {
    padding: 40px 0 0;
  }
}

/* ---------- 内置城市快选 ---------- */
.city-pick {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.city-pill {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 10px 7px 7px;
  border: 1px solid var(--line);
  background: var(--paper-2);
  cursor: pointer;
  text-align: left;
  transition: border-color 0.3s var(--ease-soft), transform 0.3s var(--ease-soft);
}

.city-pill:hover {
  border-color: var(--seal-soft);
  transform: translateY(-2px);
}

.city-pill.on {
  border-color: var(--seal);
  background: rgba(178, 46, 38, 0.06);
}

.city-pill img {
  flex: none;
  width: 40px;
  height: 40px;
  object-fit: cover;
  display: block;
}

.city-pill span {
  font-family: var(--font-serif);
  font-size: 13px;
  letter-spacing: 0.1em;
  line-height: 1.3;
}

.city-pill span em {
  display: block;
  font-style: normal;
  font-size: 9.5px;
  letter-spacing: 0.14em;
  color: var(--muted-2);
  margin-top: 2px;
}

.hint {
  margin: 8px 0 0;
  font-size: 11.5px;
  color: var(--muted-2);
}

@media (max-width: 1180px) {
  .city-pick { grid-template-columns: repeat(2, 1fr); }
}

/* ---------- 路线地图 ---------- */
.map-sec {
  margin: 8px 0 56px;
  padding-bottom: 44px;
  border-bottom: 1px solid var(--line);
}

.map-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 22px;
}

.map-head h2 {
  margin: 0 0 8px;
}

.map-head p {
  margin: 0;
  font-size: 12.5px;
  letter-spacing: 0.06em;
  color: var(--muted);
}

.map-meta {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.18em;
  color: var(--muted-2);
  white-space: nowrap;
}

.map-shell {
  position: relative;
  height: 480px;
  border: 1px solid var(--line);
  background: var(--paper-3);
  overflow: hidden;
}

.map-canvas {
  position: absolute;
  inset: 0;
}

.map-empty {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background:
    repeating-linear-gradient(0deg, rgba(23, 20, 15, 0.04) 0 1px, transparent 1px 32px),
    repeating-linear-gradient(90deg, rgba(23, 20, 15, 0.04) 0 1px, transparent 1px 32px),
    var(--paper-2);
}

.map-empty p {
  margin: 0;
  font-family: var(--font-serif);
  font-size: 22px;
  letter-spacing: 0.3em;
  color: var(--muted);
}

.map-empty span {
  font-size: 12px;
  color: var(--muted-2);
  letter-spacing: 0.06em;
}

.map-stops {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}

.map-stop {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  border: 1px solid var(--line);
  background: var(--paper-2);
  cursor: pointer;
  transition: all 0.3s var(--ease-soft);
}

.map-stop:hover {
  border-color: var(--seal-soft);
}

.map-stop.on {
  border-color: var(--seal);
  background: rgba(178, 46, 38, 0.06);
}

.ms-no {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.14em;
  color: var(--seal);
}

.ms-t {
  font-size: 12.5px;
  letter-spacing: 0.06em;
  color: var(--ink-soft);
}

.map-note {
  width: 100%;
  margin: 10px 0 0;
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.14em;
  color: var(--muted-2);
}

@media (max-width: 720px) {
  .map-shell { height: 340px; }
  .map-head { flex-direction: column; align-items: flex-start; gap: 8px; }
}
</style>
