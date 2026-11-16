<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { api } from '../api'
import PosterScene from '../components/PosterScene.vue'

const posterOk = ref(false)
const stats = ref(null)
const quote = ref('一条老街，半城烟火。')
const cities = ref([])
const region = ref('')

const regions = computed(() => [...new Set(cities.value.map((c) => c.region).filter(Boolean))])
const cityList = computed(() =>
  region.value ? cities.value.filter((c) => c.region === region.value) : cities.value
)

const capabilities = [
  {
    no: '01',
    cn: '私有人文知识库',
    en: 'PRIVATE ARCHIVE',
    desc: '上传老街史料、古建筑介绍、地方传说、非遗手记，自动切片建索引，按类目管理。'
  },
  {
    no: '02',
    cn: '有出处的回答',
    en: 'TRACEABLE ANSWERS',
    desc: '检索命中资料片段后再交给 DeepSeek 生成，每条回答附来源与原文，杜绝编造。'
  },
  {
    no: '03',
    cn: 'Citywalk 路线',
    en: 'WALKING ROUTE',
    desc: '按主题、时长与节奏生成人文漫步路线和打卡文案，地点全部来自你的资料。'
  },
  {
    no: '04',
    cn: '灵动岛随行向导',
    en: 'FLOATING GUIDE',
    desc: '页面常驻悬浮胶囊，常态一句人文短句，点击平滑舒展为对话面板，随时发问。'
  }
]

const videos = [
  { file: '/videos/dali.mp4', t: '大理 · 古城楼', en: 'DALI · YUNNAN', big: true },
  { file: '/videos/zhujiajiao.mp4', t: '朱家角 · 水巷', en: 'SHANGHAI · WATER TOWN', big: false },
  { file: '/videos/temple.mp4', t: '闽南 · 古寺门', en: 'MINNAN · TEMPLE', big: false },
  { file: '/videos/hangzhou.mp4', t: '杭州 · 夜市灯影', en: 'HANGZHOU · NIGHT MARKET', big: false },
  { file: '/videos/guangzhou.mp4', t: '广州 · 骑楼街', en: 'GUANGZHOU · MORNING', big: false }
]

const playing = ref(-1)

function videoOf(e) {
  return e.currentTarget.querySelector('video')
}

function playVid(i, e) {
  const v = videoOf(e)
  if (!v) return
  const p = v.play()
  if (p && p.catch) p.catch(() => {})
  playing.value = i
}

function pauseVid(i, e) {
  const v = videoOf(e)
  if (!v) return
  v.pause()
  if (playing.value === i) playing.value = -1
}

function toggleVid(i, e) {
  const v = videoOf(e)
  if (!v) return
  if (v.paused) playVid(i, e)
  else pauseVid(i, e)
}

let observer = null

// 切换区域后，新卡片不会触发 IntersectionObserver，这里直接补上入场状态
watch(region, async () => {
  await nextTick()
  document.querySelectorAll('.city-card.reveal').forEach((el) => el.classList.add('in'))
})

onMounted(() => {
  const probe = new Image()
  probe.onload = () => (posterOk.value = true)
  probe.src = '/poster.jpg'

  api.stats().then((s) => (stats.value = s)).catch(() => {})
  api.quotes(8).then((q) => { if (q?.quotes?.length) quote.value = q.quotes[0] }).catch(() => {})
  api.cities()
    .then((d) => {
      cities.value = (d?.cities || []).filter((c) => c.ingested)
      if (cities.value.length) {
        // 异步渲染后再补观察一次入场动画
        requestAnimationFrame(() => {
          document.querySelectorAll('.city-card.reveal').forEach((el) => observer?.observe(el))
        })
      }
    })
    .catch(() => {})

  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add('in')
          observer.unobserve(e.target)
        }
      })
    },
    { threshold: 0.14 }
  )
  document.querySelectorAll('.reveal').forEach((el) => observer.observe(el))
})

onUnmounted(() => observer?.disconnect())
</script>

<template>
  <div class="poster">
    <!-- ============ 01 · 主视觉 ============ -->
    <section class="hero">
      <div class="hero-img">
        <img v-if="posterOk" src="/poster.jpg" alt="老街晨光" />
        <PosterScene v-else />
      </div>
      <div class="hero-scrim"></div>

      <div class="hero-content">
        <div class="hero-top">
          <p class="eyebrow">City Humanities Walk · RAG Assistant</p>
          <span class="tag seal">传智杯 · RAG 知识问答赛道</span>
        </div>

        <div class="hero-title">
          <h1 class="display hero-cn">拾光叙</h1>
          <div class="hero-sub">
            <hr class="rule" />
            <p>城市人文漫步 · 知识问答助手</p>
          </div>
        </div>

        <div class="hero-bottom">
          <p class="hero-lead">
            把老街的砖、手艺人的手、老人的口述<br />
            收进一座可以检索的记忆库<span class="seal-dot">。</span>
          </p>
          <div v-if="stats" class="hero-meta">
            <span><b>{{ stats.doc_count }}</b> 篇资料</span>
            <span><b>{{ stats.chunk_count }}</b> 个片段</span>
            <span><b>{{ stats.vector_backend }}</b> 向量库</span>
          </div>
        </div>
      </div>

      <div class="hero-vertical">SHIGUANGXU — MEMORY OF STREETS</div>

      <div class="scroll-hint">
        <span>SCROLL</span>
        <i></i>
      </div>
    </section>

    <!-- ============ 02 · 序 ============ -->
    <section class="section prelude">
      <div class="wrap">
        <p class="eyebrow reveal">02 — Prelude</p>
        <h2 class="display quote reveal">
          走得慢一点，<br />才听得见旧事<span class="seal-dot">。</span>
        </h2>
        <div class="two-col reveal">
          <p>
            「拾光叙」为大学生的城市研学与 Citywalk 而生。你不只是路过一条街，
            而是带着问题走进它：这条巷子为什么叫这个名字，骑楼下的廊道为谁而建，
            那些还在营业的老铺子守着怎样的手艺。
          </p>
          <p>
            我们把答案的来源交还给你——所有解读都出自你上传的文史资料，
            附原文可核对。资料里没有的，它会明说「未记载」，
            而不是替城市编一个漂亮的故事。
          </p>
        </div>
      </div>
    </section>

    <!-- ============ 03 · 内置人文库 ============ -->
    <section class="section archive" id="archive">
      <div class="wrap">
        <header class="sec-head reveal">
          <p class="eyebrow">03 — Archive</p>
          <h2 class="display sec-title">全国人文档案，随项目自带</h2>
          <p class="sec-sub">
            不用先上传任何资料，也能立刻提问与生成路线：项目内置覆盖七大区域的名城古街文史档案，
            另有古建、非遗、运河、丝路等专题通识，全部整理自公开的政府门户、官方景区与主流媒体报道，并标注来源。
          </p>
        </header>

        <div v-if="cities.length" class="region-tabs reveal">
          <button class="btn small" :class="{ on: !region }" @click="region = ''">
            全部 · {{ cities.length }}
          </button>
          <button
            v-for="r in regions"
            :key="r"
            class="btn small"
            :class="{ on: region === r }"
            @click="region = region === r ? '' : r"
          >{{ r }}</button>
        </div>

        <div v-if="cityList.length" class="city-gallery">
          <router-link
            v-for="c in cityList"
            :key="c.id"
            class="city-card reveal"
            :to="`/city/${c.id}`"
          >
            <div class="cc-img">
              <img :src="c.image" :alt="c.city + c.title" loading="lazy" />
              <span class="cc-no">{{ c.district }}</span>
            </div>
            <div class="cc-body">
              <h3 class="display cc-city">{{ c.city }}<em>{{ c.title }}</em></h3>
              <p class="cc-sum">{{ c.summary }}</p>
              <ul class="cc-tags">
                <li v-for="t in c.tags.slice(0, 4)" :key="t">{{ t }}</li>
              </ul>
              <div class="cc-foot">
                <span>{{ c.chunks }} 片段 · {{ c.walk }}</span>
                <span class="cc-go">看简介 →</span>
              </div>
            </div>
          </router-link>
        </div>

        <p class="sec-note reveal">
          图片来自 Pexels 免费商用图库，仅作氛围示意；文字资料均为公开来源整理，
          涉及年代与数量的不同口径已在篇末并列说明。
        </p>
      </div>
    </section>

    <!-- ============ 04 · 影像 ============ -->
    <section class="section film">
      <div class="wrap">
        <header class="sec-head reveal">
          <p class="eyebrow">04 — Film</p>
          <h2 class="display sec-title">走一遍，才认得这座城</h2>
          <p class="sec-sub">四段街景，一镜到底。没有旁白，只有檐下的水声与灯笼的影子。</p>
        </header>

        <figure class="film-box reveal">
          <video src="/story.mp4" autoplay muted loop playsinline controls preload="metadata"></video>
          <figcaption>短片由项目内城市影像剪成，仅作氛围示意 · 无声循环</figcaption>
        </figure>
      </div>
    </section>

    <!-- ============ 04 · 能力 ============ -->
    <section class="section caps">
      <div class="wrap">
        <header class="sec-head reveal">
          <p class="eyebrow">05 — Capabilities</p>
          <h2 class="display sec-title">它能做什么</h2>
        </header>

        <div class="cap-list">
          <article v-for="c in capabilities" :key="c.no" class="cap reveal">
            <span class="cap-no">{{ c.no }}</span>
            <div class="cap-body">
              <h3 class="display cap-cn">{{ c.cn }}</h3>
              <p class="cap-en">{{ c.en }}</p>
              <p class="cap-desc">{{ c.desc }}</p>
            </div>
          </article>
        </div>
      </div>
    </section>

    <!-- ============ 06 · 影像 ============ -->
    <section class="section vids">
      <div class="wrap">
        <header class="sec-head reveal">
          <p class="eyebrow">06 — Moving Image</p>
          <h2 class="display sec-title">几段现场，替文字说话</h2>
          <p class="sec-sub">
            水乡的橹声、古寺檐下的光、夜市刚亮起的灯笼——有些东西写不出来，只能看一眼。
            悬停即播放，点击可暂停。
          </p>
        </header>

        <div class="vid-grid reveal">
          <figure
            v-for="(v, i) in videos"
            :key="v.file"
            class="vid-card"
            :class="{ big: v.big, playing: playing === i }"
            @mouseenter="playVid(i, $event)"
            @mouseleave="pauseVid(i, $event)"
            @click="toggleVid(i, $event)"
          >
            <video :src="v.file" muted loop playsinline preload="metadata" :autoplay="i === 0"></video>
            <span class="vid-play"></span>
            <figcaption class="vid-cap"><b>{{ v.t }}</b><span>{{ v.en }}</span></figcaption>
          </figure>
        </div>

        <p class="sec-note reveal">
          影像来自 Pexels 免费商用视频，为氛围示意，非对应城市实拍；已压缩并无声循环播放。
        </p>
      </div>
    </section>

    <!-- ============ 06 · 开始 ============ -->
    <section class="section cta">
      <div class="wrap cta-inner reveal">
        <p class="eyebrow">07 — Begin</p>
        <h2 class="display cta-title">从第一份史料开始</h2>
        <div class="cta-actions">
          <router-link class="btn primary" to="/knowledge">上传史料</router-link>
          <router-link class="btn" to="/chat">直接提问</router-link>
          <router-link class="btn" to="/route">生成路线</router-link>
        </div>
      </div>
    </section>

    <footer class="foot">
      <div class="wrap foot-inner">
        <span>拾光叙 · 城市人文漫步 RAG 助手</span>
        <span class="foot-quote">「{{ quote }}」</span>
        <span>Vue 3 · FastAPI · FAISS · DeepSeek</span>
      </div>
    </footer>
  </div>
</template>

<style scoped>

/* ---------- 影像志 ---------- */
.vid-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-top: 40px;
}

.vid-card {
  position: relative;
  margin: 0;
  overflow: hidden;
  border: 1px solid var(--line);
  background: #1b1510;
  min-height: 190px;
  cursor: pointer;
}

.vid-card video {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: saturate(0.9) contrast(1.03);
  transition: transform 0.8s var(--ease-soft);
}

.vid-card:hover video {
  transform: scale(1.04);
}

.vid-card.big {
  grid-column: span 2;
  grid-row: span 2;
  min-height: 394px;
}

.vid-cap {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 30px 18px 14px;
  background: linear-gradient(0deg, rgba(18, 13, 8, 0.86) 0%, rgba(18, 13, 8, 0) 100%);
  color: #f8f1e2;
  pointer-events: none;
}

.vid-cap b {
  display: block;
  font-family: var(--font-serif);
  font-size: 16px;
  font-weight: 500;
  letter-spacing: 0.1em;
}

.vid-cap span {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.2em;
  color: rgba(248, 241, 226, 0.62);
}

.vid-play {
  position: absolute;
  top: 14px;
  right: 14px;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 1px solid rgba(248, 241, 226, 0.5);
  background: rgba(18, 13, 8, 0.35);
  color: #f8f1e2;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  backdrop-filter: blur(6px);
}

.vid-play::after { content: '▶'; }
.vid-card.playing .vid-play { background: var(--seal); border-color: var(--seal); }
.vid-card.playing .vid-play::after { content: 'Ⅱ'; }

@media (max-width: 900px) {
  .vid-grid { grid-template-columns: repeat(2, 1fr); }
  .vid-card.big { grid-column: span 2; grid-row: auto; min-height: 220px; }
}

@media (max-width: 560px) {
  .vid-grid { grid-template-columns: 1fr; }
  .vid-card.big { grid-column: auto; }
}

/* ---------- 影像 ---------- */
.film-box {
  margin: 40px 0 0;
  border: 1px solid var(--line);
  background: var(--paper-3);
  overflow: hidden;
}

.film-box video {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  filter: saturate(0.92) contrast(1.02);
}

.film-box figcaption {
  padding: 11px 16px;
  border-top: 1px solid var(--line-soft);
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.16em;
  color: var(--muted-2);
}
.poster {
  position: relative;
  z-index: 1;
}

.wrap {
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 48px;
}

/* ---------- 主视觉 ---------- */
.hero {
  position: relative;
  min-height: 100vh;
  display: flex;
  overflow: hidden;
  background: #e4dbca;
}

.hero-img {
  position: absolute;
  inset: 0;
}

.hero-img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: 38% center;
  display: block;
}

.hero-scrim {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, rgba(26, 19, 12, 0.78) 0%, rgba(26, 19, 12, 0.52) 34%, rgba(26, 19, 12, 0.16) 62%, rgba(26, 19, 12, 0) 82%),
    linear-gradient(180deg, rgba(26, 19, 12, 0.45) 0%, rgba(26, 19, 12, 0) 26%),
    linear-gradient(0deg, rgba(24, 17, 10, 0.62) 0%, rgba(24, 17, 10, 0) 40%);
}

.hero-content {
  position: relative;
  z-index: 2;
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 128px 56px 92px;
  color: #f8f1e2;
}

.hero-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.hero-top .eyebrow {
  color: rgba(248, 241, 226, 0.72);
}

.hero-top .tag {
  border-color: rgba(248, 241, 226, 0.32);
  color: rgba(248, 241, 226, 0.92);
}

.hero-title {
  display: flex;
  flex-direction: column;
  gap: 26px;
}

.hero-cn {
  font-size: clamp(56px, 9.6vw, 134px);
  letter-spacing: 0.18em;
  color: #fdf8ec;
  text-shadow:
    0 1px 2px rgba(18, 12, 7, 0.55),
    0 12px 46px rgba(18, 12, 7, 0.5);
}

.hero-sub {
  display: flex;
  align-items: center;
  gap: 20px;
  max-width: 560px;
}

.hero-sub .rule {
  width: 64px;
  background: rgba(248, 241, 226, 0.5);
  flex: none;
}

.hero-sub p {
  margin: 0;
  font-size: 13.5px;
  letter-spacing: 0.32em;
  color: rgba(248, 241, 226, 0.86);
}

.hero-bottom {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 40px;
  flex-wrap: wrap;
}

.hero-lead {
  margin: 0;
  font-family: var(--font-serif);
  font-size: clamp(15px, 1.6vw, 20px);
  line-height: 2.1;
  letter-spacing: 0.08em;
  color: rgba(248, 241, 226, 0.92);
}

.seal-dot {
  color: var(--seal-soft);
}

.hero-meta {
  display: flex;
  gap: 26px;
  font-size: 11.5px;
  letter-spacing: 0.18em;
  color: rgba(248, 241, 226, 0.66);
}

.hero-meta b {
  font-size: 15px;
  color: #fdf8ec;
  margin-right: 4px;
}

.hero-vertical {
  position: absolute;
  right: 44px;
  top: 50%;
  transform: translateY(-50%);
  writing-mode: vertical-rl;
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.42em;
  color: rgba(248, 241, 226, 0.55);
  z-index: 2;
}

.scroll-hint {
  position: absolute;
  left: 50%;
  bottom: 32px;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  z-index: 2;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.34em;
  color: rgba(248, 241, 226, 0.6);
}

.scroll-hint i {
  width: 1px;
  height: 46px;
  background: linear-gradient(180deg, rgba(248, 241, 226, 0.7), rgba(248, 241, 226, 0));
  animation: drop 2.4s var(--ease-soft) infinite;
}

@keyframes drop {
  0% { transform: scaleY(0.2); transform-origin: top; opacity: 0; }
  40% { transform: scaleY(1); opacity: 1; }
  100% { transform: scaleY(1); opacity: 0; }
}

/* ---------- 章节通用 ---------- */
.section {
  padding: clamp(96px, 15vh, 170px) 0;
}

.sec-head {
  margin-bottom: 64px;
}

.sec-title {
  font-size: clamp(28px, 3.4vw, 44px);
  margin-top: 14px;
}

/* ---------- 序 ---------- */
.prelude {
  background: var(--paper-light);
}

.quote {
  font-size: clamp(28px, 4.6vw, 58px);
  line-height: 1.5;
  margin: 26px 0 52px;
  letter-spacing: 0.08em;
}

.two-col {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 52px;
  max-width: 880px;
  margin-left: auto;
  color: var(--ink-soft);
  font-size: 14px;
  line-height: 2.05;
}

.two-col p {
  margin: 0;
}

/* ---------- 能力 ---------- */
.cap-list {
  border-top: 1px solid var(--line);
}

.cap {
  display: grid;
  grid-template-columns: 90px 1fr;
  gap: 24px;
  padding: 40px 0;
  border-bottom: 1px solid var(--line);
  transition: background 0.5s var(--ease-soft);
}

.cap:hover {
  background: rgba(168, 59, 44, 0.035);
}

.cap-no {
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.2em;
  color: var(--seal);
  padding-top: 6px;
}

.cap-cn {
  font-size: clamp(20px, 2.2vw, 28px);
  margin: 0 0 6px;
}

.cap-en {
  margin: 0 0 12px;
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.3em;
  color: var(--muted-2);
}

.cap-desc {
  margin: 0;
  max-width: 620px;
  color: var(--ink-soft);
  font-size: 14px;
}

/* ---------- 步骤 ---------- */
.steps-sec {
  background: var(--paper-light);
}

.step-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 40px;
}

.step-no {
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--seal);
  letter-spacing: 0.2em;
}

.step .rule {
  margin: 14px 0 18px;
}

.step h4 {
  font-size: 19px;
  margin: 0 0 10px;
}

.step p {
  margin: 0;
  font-size: 13px;
  color: var(--ink-soft);
  line-height: 1.9;
}

/* ---------- 技术 ---------- */
.tech-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 80px;
  align-items: start;
}

.tech-note {
  margin-top: 22px;
  max-width: 460px;
  font-size: 13.5px;
  color: var(--ink-soft);
  line-height: 2;
}

.stack-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.stack-list li {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 16px 0;
  border-bottom: 1px solid var(--line-soft);
  font-size: 13.5px;
}

.stack-list .k {
  color: var(--muted);
  letter-spacing: 0.12em;
}

.stack-list .dots {
  flex: 1;
  height: 1px;
  background: repeating-linear-gradient(90deg, var(--line) 0 2px, transparent 2px 6px);
}

.stack-list .v {
  font-family: var(--font-serif);
  letter-spacing: 0.06em;
  color: var(--ink);
}

/* ---------- CTA ---------- */
.cta {
  background: var(--ink);
  color: var(--paper-light);
  text-align: center;
}

.cta .eyebrow {
  color: rgba(247, 242, 232, 0.5);
}

.cta-title {
  font-size: clamp(30px, 4.4vw, 56px);
  margin: 18px 0 44px;
  letter-spacing: 0.12em;
}

.cta-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  flex-wrap: wrap;
}

.cta .btn {
  border-color: rgba(247, 242, 232, 0.5);
  color: var(--paper-light);
}

.cta .btn:hover {
  background: var(--paper-light);
  color: var(--ink);
}

.cta .btn.primary {
  background: var(--seal);
  border-color: var(--seal);
  color: #fdf8ef;
}

.cta .btn.primary:hover {
  background: var(--paper-light);
  color: var(--ink);
}

/* ---------- 页脚 ---------- */
.foot {
  padding: 40px 0;
  border-top: 1px solid var(--line-soft);
}

.foot-inner {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  flex-wrap: wrap;
  font-size: 11px;
  letter-spacing: 0.16em;
  color: var(--muted);
}

.foot-quote {
  font-family: var(--font-serif);
  color: var(--ink-soft);
  letter-spacing: 0.08em;
}

/* ---------- 入场 ---------- */
.reveal {
  opacity: 0;
  transform: translateY(26px);
  transition: opacity 1s var(--ease-soft), transform 1s var(--ease-soft);
}

.reveal.in {
  opacity: 1;
  transform: none;
}

/* ---------- 03 · 内置人文库陈列 ---------- */
.archive {
  background: linear-gradient(180deg, var(--paper) 0%, var(--paper-2) 100%);
}

.sec-sub {
  max-width: 640px;
  margin: 18px 0 0;
  font-size: 13.5px;
  line-height: 2.1;
  color: var(--muted);
}

.region-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.city-gallery {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 34px 30px;
  margin-top: 64px;
}

.city-card {
  display: block;
  cursor: pointer;
  background: var(--paper-2);
  border: 1px solid var(--line);
  overflow: hidden;
  color: inherit;
  text-decoration: none;
}

.city-card .cc-img {
  position: relative;
  aspect-ratio: 4 / 3;
  overflow: hidden;
  background: var(--paper-3);
}

.city-card .cc-img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  filter: saturate(0.88) contrast(1.03);
  transition: transform 1.4s var(--ease-soft), filter 0.8s var(--ease-soft);
}

.city-card:hover .cc-img img {
  transform: scale(1.05);
  filter: saturate(1) contrast(1.05);
}

.cc-no {
  position: absolute;
  left: 0;
  top: 16px;
  padding: 4px 12px;
  background: rgba(24, 20, 14, 0.55);
  color: #f7f2e7;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.2em;
  backdrop-filter: blur(4px);
}

.cc-body {
  padding: 22px 22px 20px;
}

.cc-city {
  margin: 0 0 10px;
  font-family: var(--font-serif);
  font-size: 22px;
  letter-spacing: 0.14em;
  font-weight: 500;
}

.cc-city em {
  font-style: normal;
  font-size: 11.5px;
  letter-spacing: 0.18em;
  color: var(--muted-2);
  margin-left: 10px;
}

.cc-sum {
  margin: 0 0 14px;
  font-size: 13px;
  line-height: 2;
  color: var(--muted);
}

.cc-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0 0 16px;
  padding: 0;
  list-style: none;
}

.cc-tags li {
  font-size: 10px;
  letter-spacing: 0.12em;
  color: var(--muted-2);
  border: 1px solid var(--line);
  padding: 3px 8px;
}

.cc-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 14px;
  border-top: 1px solid var(--line-soft);
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.16em;
  color: var(--muted-2);
}

.cc-go {
  color: var(--seal);
}

.city-card:hover .cc-go {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.sec-note {
  margin: 44px 0 0;
  font-family: var(--font-mono);
  font-size: 10.5px;
  line-height: 2;
  letter-spacing: 0.08em;
  color: var(--muted-2);
}

@media (max-width: 1024px) {
  .wrap {
    padding: 0 28px;
  }
  .city-gallery {
    grid-template-columns: repeat(2, 1fr);
    gap: 26px 22px;
  }
  .hero-content {
    padding: 116px 28px 84px;
  }
  .hero-vertical {
    display: none;
  }
  .two-col,
  .tech-grid {
    grid-template-columns: 1fr;
    gap: 28px;
  }
  .step-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .cap {
    grid-template-columns: 1fr;
    gap: 8px;
  }
  .step-grid {
    grid-template-columns: 1fr;
  }
  .hero-meta {
    display: none;
  }
  .city-gallery {
    grid-template-columns: 1fr;
    gap: 24px;
  }
}
</style>
