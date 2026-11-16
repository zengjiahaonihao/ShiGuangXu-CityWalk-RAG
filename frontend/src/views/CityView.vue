<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'

const route = useRoute()
const router = useRouter()

const cities = ref([])
const detail = ref(null)
const loading = ref(true)
const failed = ref(false)

const city = computed(() => detail.value || cities.value.find((c) => c.id === route.params.id) || null)
const sections = computed(() => (detail.value?.sections || []).map((s) => ({
  ...s,
  title: s.h.replace(/^[一二三四五六七八九十]+、\s*/, '')
})))

const siblings = computed(() => {
  if (!city.value) return []
  return cities.value.filter((c) => c.region === city.value.region && c.id !== city.value.id).slice(0, 4)
})

const totalSpots = computed(() => city.value?.spots?.length || 0)

// 看点说明：档案摘要里没有逐条解释时，给一句「怎么读」的提示
const SPOT_HINTS = {
  塔: '看塔身的浮雕与仿木构斗栱，是判断年代的关键。',
  桥: '留意桥墩形制与石梁搭法，能看出水路运输的等级。',
  寺: '先看山门与主殿的轴线，再看梁架与彩画。',
  庙: '看屋顶脊饰与门楣题字，庙宇等级写在细节里。',
  街: '沿街看立面连续性与转角处理，能读出商业形态。',
  故居: '门屋、天井、正厅的进深关系，是身份与年代的线索。',
  骑楼: '抬头看柱头线脚与女儿墙风洞，那是南洋带回的做法。',
  牌坊: '数一数间数与柱数，牌坊的规格即家族的规格。',
  城墙: '看马面与垛口的间距，防御尺度一目了然。',
  石窟: '先看主尊的衣纹，再看两侧胁侍的排列。'
}

function spotNote(name) {
  for (const k in SPOT_HINTS) {
    if (name.includes(k)) return SPOT_HINTS[k]
  }
  return '资料中有专门段落记述，可在对话页追问细节。'
}

function hasCoord(name) {
  return (city.value?.spots || []).some((s) => s.name === name)
}

async function load() {
  loading.value = true
  failed.value = false
  detail.value = null
  try {
    // 先取完整档案（含正文章节），失败再退回列表项
    detail.value = await api.cityDetail(route.params.id)
  } catch (e) {
    detail.value = null
  }
  try {
    const d = await api.cities()
    cities.value = d?.cities || []
    failed.value = !detail.value && !cities.value.some((c) => c.id === route.params.id)
  } catch (e) {
    failed.value = !detail.value
  } finally {
    loading.value = false
  }
}

function goRoute() {
  if (!city.value) return
  router.push({ path: '/route', query: { city: city.value.city, doc: city.value.doc_id } })
}

function goAsk() {
  if (!city.value) return
  router.push({ path: '/chat', query: { q: `请介绍${city.value.city}${city.value.title}的历史与看点` } })
}

watch(() => route.params.id, load)
onMounted(load)
</script>

<template>
  <div class="page city-page">
    <div v-if="loading" class="state">正在翻开档案…</div>

    <div v-else-if="failed" class="state">
      <p>没有找到这座城的档案。</p>
      <router-link class="btn" to="/knowledge">回到知识库</router-link>
    </div>

    <template v-else-if="city">
      <header class="cp-hero">
        <img class="cp-bg" :src="city.image" :alt="city.city + city.title" />
        <div class="cp-scrim"></div>
        <div class="cp-inner">
          <router-link class="crumb" to="/knowledge">← 返回人文档案</router-link>
          <p class="cp-no">
            <span class="num">ARCHIVE</span>
            <span class="en">{{ city.region }} · {{ city.district }}</span>
          </p>
          <h1 class="cp-cn">{{ city.city }}<em>{{ city.title }}</em></h1>
          <p class="cp-sub">{{ city.subtitle }}</p>
          <div class="cp-actions">
            <button class="btn primary" @click="goRoute">生成这座城的路线</button>
            <button class="btn" @click="goAsk">就这座城提问</button>
          </div>
        </div>
        <span class="cp-seal">拾</span>
      </header>

      <section class="cp-body">
        <div class="cp-main">
          <p class="cp-lead">{{ city.summary }}</p>

          <div class="cp-tags">
            <span v-for="t in city.tags" :key="t">{{ t }}</span>
          </div>

          <h2 class="cp-h2">值得走到的几处</h2>
          <ol class="cp-spots">
            <li v-for="(h, i) in city.highlights" :key="h">
              <span class="no">{{ String(i + 1).padStart(2, '0') }}</span>
              <div>
                <b>{{ h }}</b>
                <p>{{ spotNote(h) }}</p>
              </div>
              <span v-if="hasCoord(h)" class="pin">已在地图上</span>
            </li>
          </ol>

          <template v-if="sections.length">
            <h2 class="cp-h2">档案正文</h2>
            <div class="cp-read">
              <section v-for="(sec, i) in sections" :key="i" class="cp-sec">
                <h3>
                  <span class="sec-no">{{ String(i + 1).padStart(2, '0') }}</span>
                  {{ sec.title }}
                </h3>
                <p v-for="(it, j) in sec.items" :key="j">{{ it }}</p>
              </section>
            </div>
          </template>

          <h2 class="cp-h2">漫步建议</h2>
          <div class="cp-walk">
            <div>
              <span class="k">建议时长</span>
              <b>{{ city.walk }}</b>
            </div>
            <div>
              <span class="k">档案规模</span>
              <b>{{ city.chunks }} 个片段</b>
            </div>
            <div>
              <span class="k">可定位看点</span>
              <b>{{ totalSpots }} 处</b>
            </div>
            <div>
              <span class="k">所属区域</span>
              <b>{{ city.region }}</b>
            </div>
          </div>

          <p class="cp-note">
            以上内容整理自公开的政府门户、官方景区与主流媒体报道，完整出处见对应档案篇末。
            配图取自 Pexels 免费商用图库，为氛围示意，非该街区实拍。
          </p>
        </div>

        <aside class="cp-side">
          <div class="side-card">
            <p class="side-en">QUICK ACTIONS</p>
            <button class="side-btn" @click="goRoute">用这座城生成路线 <span>→</span></button>
            <button class="side-btn" @click="goAsk">带着问题去对话 <span>→</span></button>
            <router-link class="side-btn" to="/knowledge">翻看其他档案 <span>→</span></router-link>
          </div>

          <div v-if="city.spots?.length" class="side-card">
            <p class="side-en">ON THE MAP</p>
            <ul class="side-spots">
              <li v-for="s in city.spots.slice(0, 5)" :key="s.name">
                <i></i>{{ s.name }}
              </li>
            </ul>
            <p class="side-hint">生成路线时会把这些点标在地图上。</p>
          </div>

          <div v-if="siblings.length" class="side-card">
            <p class="side-en">SAME REGION</p>
            <router-link v-for="s in siblings" :key="s.id" class="side-link" :to="`/city/${s.id}`">
              {{ s.city }} · {{ s.title }} <span>→</span>
            </router-link>
          </div>
        </aside>
      </section>
    </template>
  </div>
</template>

<script>
export default { name: 'CityView' }
</script>

<style scoped>

/* ---------- 档案正文 ---------- */
.cp-read {
  border-top: 1px solid var(--line);
}

.cp-sec {
  padding: 26px 0 22px;
  border-bottom: 1px solid var(--line-soft);
}

.cp-sec h3 {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin: 0 0 14px;
  font-family: var(--font-serif);
  font-size: 17.5px;
  font-weight: 500;
  letter-spacing: 0.08em;
  color: var(--ink);
}

.cp-sec .sec-no {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.16em;
  color: var(--seal);
}

.cp-sec p {
  margin: 0 0 10px;
  font-size: 13.5px;
  line-height: 2.05;
  letter-spacing: 0.02em;
  color: var(--ink-soft);
  text-align: justify;
}

.cp-sec p:last-child {
  margin-bottom: 0;
}

.city-page {
  padding: 0;
}

.state {
  padding: 160px 0;
  text-align: center;
  color: var(--muted);
  font-family: var(--font-serif);
  letter-spacing: 0.12em;
}

.cp-hero {
  position: relative;
  min-height: 62vh;
  display: flex;
  align-items: flex-end;
  overflow: hidden;
  background: #241a12;
  color: #f8f1e2;
}

.cp-bg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: saturate(0.85) contrast(1.04);
  transform: scale(1.03);
}

.cp-scrim {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, rgba(24, 17, 10, 0.88) 0%, rgba(24, 17, 10, 0.55) 45%, rgba(24, 17, 10, 0.25) 75%, rgba(24, 17, 10, 0.45) 100%),
    linear-gradient(180deg, rgba(24, 17, 10, 0.5) 0%, rgba(24, 17, 10, 0) 36%),
    linear-gradient(0deg, rgba(22, 16, 9, 0.72) 0%, rgba(22, 16, 9, 0) 60%);
}

.cp-inner {
  position: relative;
  z-index: 2;
  width: 100%;
  max-width: 1180px;
  margin: 0 auto;
  padding: 160px 48px 64px;
}

.crumb {
  display: inline-block;
  margin-bottom: 26px;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.2em;
  color: rgba(248, 241, 226, 0.66);
  border-bottom: 1px solid rgba(248, 241, 226, 0.24);
  padding-bottom: 4px;
  transition: color 0.3s;
}

.crumb:hover {
  color: #fdf8ec;
}

.cp-no {
  display: flex;
  align-items: baseline;
  gap: 16px;
  margin: 0 0 16px;
}

.cp-no .num {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.34em;
  color: var(--seal-soft);
}

.cp-no .en {
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.24em;
  color: rgba(248, 241, 226, 0.55);
}

.cp-cn {
  margin: 0;
  font-family: var(--font-serif);
  font-size: clamp(38px, 5.6vw, 70px);
  letter-spacing: 0.12em;
  font-weight: 500;
  color: #fdf8ec;
  text-shadow: 0 12px 44px rgba(18, 12, 7, 0.5);
}

.cp-cn em {
  display: block;
  font-style: normal;
  font-size: 0.32em;
  letter-spacing: 0.28em;
  color: rgba(248, 241, 226, 0.72);
  margin-top: 14px;
}

.cp-sub {
  margin: 18px 0 0;
  font-family: var(--font-serif);
  font-size: 15px;
  letter-spacing: 0.24em;
  color: rgba(248, 241, 226, 0.8);
}

.cp-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 34px;
}

.cp-actions .btn {
  border-color: rgba(248, 241, 226, 0.4);
  color: #f8f1e2;
}

.cp-actions .btn.primary {
  background: var(--seal);
  border-color: var(--seal);
  color: #fdf6ee;
}

.cp-seal {
  position: absolute;
  right: 56px;
  bottom: 60px;
  z-index: 2;
  width: 54px;
  height: 54px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-serif);
  font-size: 24px;
  color: #fdf3e5;
  border: 1.5px solid rgba(178, 46, 38, 0.85);
  background: rgba(178, 46, 38, 0.28);
  transform: rotate(-3deg);
}

.cp-body {
  max-width: 1180px;
  margin: 0 auto;
  padding: 80px 48px 130px;
  display: grid;
  grid-template-columns: 1.5fr 0.8fr;
  gap: 72px;
  align-items: start;
}

.cp-lead {
  margin: 0;
  font-family: var(--font-serif);
  font-size: 20px;
  line-height: 2.05;
  letter-spacing: 0.05em;
  color: var(--ink);
}

.cp-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 26px;
}

.cp-tags span {
  font-size: 11.5px;
  letter-spacing: 0.1em;
  padding: 5px 12px;
  border: 1px solid var(--line);
  color: var(--muted);
}

.cp-h2 {
  margin: 56px 0 22px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--line);
  font-family: var(--font-serif);
  font-size: 20px;
  letter-spacing: 0.18em;
  font-weight: 500;
}

.cp-spots {
  list-style: none;
  margin: 0;
  padding: 0;
}

.cp-spots li {
  display: grid;
  grid-template-columns: 44px 1fr auto;
  gap: 16px;
  align-items: baseline;
  padding: 18px 0;
  border-bottom: 1px solid var(--line-soft);
}

.cp-spots .no {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.18em;
  color: var(--seal);
}

.cp-spots b {
  font-family: var(--font-serif);
  font-size: 16px;
  font-weight: 500;
  letter-spacing: 0.06em;
}

.cp-spots p {
  margin: 6px 0 0;
  font-size: 12.5px;
  line-height: 1.95;
  color: var(--muted);
}

.cp-spots .pin {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.16em;
  color: var(--muted-2);
  border: 1px solid var(--line);
  padding: 3px 8px;
  white-space: nowrap;
}

.cp-walk {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1px;
  background: var(--line);
  border: 1px solid var(--line);
}

.cp-walk > div {
  background: var(--paper-2);
  padding: 18px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.cp-walk .k {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.2em;
  color: var(--muted-2);
}

.cp-walk b {
  font-family: var(--font-serif);
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.06em;
}

.cp-note {
  margin: 40px 0 0;
  font-family: var(--font-mono);
  font-size: 10.5px;
  line-height: 2;
  letter-spacing: 0.06em;
  color: var(--muted-2);
}

.cp-side {
  display: flex;
  flex-direction: column;
  gap: 20px;
  position: sticky;
  top: 110px;
}

.side-card {
  border: 1px solid var(--line);
  padding: 22px 22px 20px;
  background: var(--paper-2);
}

.side-en {
  margin: 0 0 16px;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.3em;
  color: var(--muted-2);
}

.side-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 11px 0;
  border: 0;
  border-bottom: 1px dashed var(--line);
  background: transparent;
  font-family: var(--font-serif);
  font-size: 13.5px;
  letter-spacing: 0.08em;
  color: var(--ink);
  cursor: pointer;
  text-align: left;
  text-decoration: none;
}

.side-btn:last-child {
  border-bottom: 0;
}

.side-btn span {
  color: var(--seal);
  transition: transform 0.3s var(--ease-soft);
}

.side-btn:hover span {
  transform: translateX(4px);
}

.side-spots {
  list-style: none;
  margin: 0;
  padding: 0;
}

.side-spots li {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 12.5px;
  color: var(--ink-soft);
  padding: 6px 0;
}

.side-spots i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--seal);
  flex: none;
}

.side-hint {
  margin: 12px 0 0;
  font-size: 11px;
  color: var(--muted-2);
  line-height: 1.8;
}

.side-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 9px 0;
  font-size: 12.5px;
  letter-spacing: 0.06em;
  color: var(--ink-soft);
  border-bottom: 1px dashed var(--line);
  text-decoration: none;
}

.side-link:last-child {
  border-bottom: 0;
}

.side-link:hover {
  color: var(--seal);
}

@media (max-width: 1024px) {
  .cp-inner {
    padding: 130px 28px 48px;
  }
  .cp-body {
    grid-template-columns: 1fr;
    gap: 40px;
    padding: 56px 28px 100px;
  }
  .cp-side {
    position: static;
  }
  .cp-seal {
    right: 24px;
    bottom: 30px;
    width: 44px;
    height: 44px;
    font-size: 20px;
  }
  .cp-walk {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .cp-spots li {
    grid-template-columns: 32px 1fr;
  }
  .cp-spots .pin {
    display: none;
  }
}
</style>
