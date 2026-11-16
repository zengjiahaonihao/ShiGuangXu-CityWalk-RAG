<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { wgs84ToGcj02 } from './coords'

/** 推荐条目的稳定标识：重新请求后是新对象，只能靠 id / 名字配对 */
const recId = (p) => (p ? String(p.id ?? p.name ?? '') : '')

const props = defineProps({
  plan: { type: Object, default: null },
  activeDay: { type: Number, default: 0 },
  // 右侧浮层展开时地图留出的空间（px）
  padRight: { type: Number, default: 60 },
  // 当前天的附近推荐：{ hotels: {items}, foods: {items} }
  recommendations: { type: Object, default: null },
  // 当前选中的站点 { day, index }：来自地图点击或右侧列表点击，用来做双向联动的强调
  highlight: { type: Object, default: null },
  // 当前选中的附近推荐 { kind: 'hotels'|'foods', id }：与右侧推荐条目双向联动
  recFocus: { type: Object, default: null },
  // 'dark' | 'light'：暗色靠 CSS invert 滤镜实现（高德只有亮色瓦片）
  theme: { type: String, default: 'dark' },
  // 失败态文案（原项目走 i18n，这里暴露成 prop，接入方自己给）
  failedText: { type: String, default: '地图加载失败' },
  retryText: { type: String, default: '重试' },
})
const emit = defineEmits(['select', 'select-place', 'ready'])

const theme = computed(() => props.theme)

// 按天配色（DOM 标记用，直接显示在页面上，不经过 canvas 滤镜）
const PALETTE = {
  dark: ['#ffb340', '#7cc0ff', '#c084fc', '#4ade80', '#f472b6', '#facc15', '#38bdf8'],
  light: ['#b45309', '#1d4ed8', '#7e22ce', '#15803d', '#be185d', '#a16207', '#0369a1'],
}
const dayColor = (i) =>
  (theme.value === 'light' ? PALETTE.light : PALETTE.dark)[i % PALETTE.dark.length]

/* 走线画在 MapLibre canvas 里。暗色主题会给整张 canvas 套
   invert(1) hue-rotate(180deg) brightness(.92) contrast(.95)，
   亮色输入会被翻成深色——所以这里预先反解成「过滤后正好是亮色」的输入值。
   数值按 Chrome 的 sRGB 逐级 clamp 实测得出。 */
const LEG_PALETTE_DARK = [
  '#7e2700', '#004189', '#833ec8', '#006000', '#ce3987', '#592500', '#0065a9',
]
const LEG_PALETTE_LIGHT = PALETTE.light
const legColor = (i) =>
  (theme.value === 'light' ? LEG_PALETTE_LIGHT : LEG_PALETTE_DARK)[
    i % LEG_PALETTE_LIGHT.length
  ]
// 描边：亮色底图用深色描边；暗色底图下滤镜会把纯黑翻成近白（#e5e5e5），
// 于是走线得到一圈亮色轮廓，在湖泊/地铁/绿地等杂色底图上也能一眼认出
const casingColor = () => (theme.value === 'light' ? '#0b0d12' : '#000000')

/* 推荐点位：酒店 / 餐厅用更小的 emoji 圆点，与编号站点区分。
   这些是 DOM 标记，不经过 canvas 的暗色滤镜，直接用亮色。 */
const REC_META = {
  hotels: { icon: '🏨', dark: '#c084fc', light: '#7e22ce' },
  foods: { icon: '🍜', dark: '#ffb340', light: '#b45309' },
}
const fmtDist = (m) =>
  m == null ? '' : m >= 1000 ? `${(m / 1000).toFixed(1)} km` : `${Math.round(m)} m`

const el = ref(null)
let map = null
let styleReady = false
let markers = []
let recMarkers = []
const failed = ref(false)
let resizeObserver = null
let fitRaf = 0
let didFit = false
let bailTimer = null
let failTimer = null

/* 底图：高德栅格瓦片（国内实测可达；CARTO / OSM 官方瓦片在国内不可达）
   注意：高德为 GCJ-02 坐标系，因此所有 WGS84 数据点显示前需转 GCJ-02 */
const buildStyle = () => ({
  version: 8,
  sources: {
    basemap: {
      type: 'raster',
      tiles: [1, 2, 3, 4].map(
        (i) =>
          `https://webrd0${i}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}`,
      ),
      tileSize: 256,
      maxzoom: 18,
      attribution: '© 高德地图 © OpenStreetMap contributors',
    },
  },
  layers: [{ id: 'basemap', type: 'raster', source: 'basemap' }],
})

/* WGS84 → GCJ-02：点位与走线都要转，才能和高德底图对齐 */
const toGcj = (lng, lat) => wgs84ToGcj02(lng, lat)

const shownDays = () => {
  const days = props.plan?.days || []
  return props.activeDay === 0 ? days : days.filter((d) => d.day === props.activeDay)
}

/* 走线：后台已算好真实路网几何（activity.leg.geometry）
   铁路/航班没有可跟随的道路几何，统一画虚线与其他交通区分 */
const DASHED_MODES = new Set(['rail', 'flight'])
const DASH_PATTERN = [2.5, 2]

/* 出发地 → 第一站：只在总览或第 1 天显示，避免切到后面天数时把视口拉回出发地 */
function arrivalFeature() {
  const arr = props.plan?.arrival
  const firstDay = props.plan?.days?.[0]?.day
  if (!arr?.leg || (arr.leg.geometry?.length || 0) < 2) return null
  if (props.activeDay !== 0 && props.activeDay !== firstDay) return null
  const mode = arr.leg.mode || ''
  return {
    type: 'Feature',
    geometry: {
      type: 'LineString',
      coordinates: arr.leg.geometry.map((c) => toGcj(c[0], c[1])),
    },
    properties: {
      color: legColor(0),
      casing: casingColor(),
      mode,
      dashed: DASHED_MODES.has(mode) ? 1 : 0,
    },
  }
}

function legData() {
  const fc = { type: 'FeatureCollection', features: [] }
  shownDays().forEach((d) => {
    const acts = d.activities || []
    acts.forEach((a, i) => {
      // 有后台几何就用几何；缺失时退化为到下一站的两点虚线，
      // 保证旧缓存/路径服务失败时也一定能看到站间连线
      let coords = null
      if (a.leg?.geometry?.length >= 2) {
        coords = a.leg.geometry
      } else {
        const next = acts[i + 1]
        if (a.lat == null || a.lng == null || next?.lat == null || next?.lng == null) return
        coords = [[a.lng, a.lat], [next.lng, next.lat]]
      }
      const mode = a.leg?.mode || ''
      fc.features.push({
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates: coords.map((c) => toGcj(c[0], c[1])),
        },
        properties: {
          color: legColor(d.day - 1),
          casing: casingColor(),
          mode,
          dashed: a.leg?.geometry?.length >= 2 && !DASHED_MODES.has(mode) ? 0 : 1,
        },
      })
    })
  })
  const arrival = arrivalFeature()
  if (arrival) fc.features.push(arrival)
  return fc
}

/** 站点名来自模型输出，拼进 innerHTML 前必须转义 */
const esc = (v) =>
  String(v ?? '').replace(/[&<>"]/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]))

/* 点位：DOM 标记（数字压在点上，不依赖 WebGL 图层） */
function drawMarkers() {
  const ml = window.maplibregl || maplibregl
  if (!ml || !map) return
  markers.forEach((m) => m.remove())
  markers = []
  shownDays().forEach((d) => {
    (d.activities || []).forEach((a, i) => {
      if (a.lat == null || a.lng == null) return
      const c = dayColor(d.day - 1)
      const node = document.createElement('div')
      node.className = 'poi-marker'
      node.innerHTML =
        `<div class="pm-in" style="--pc:${c}">` +
        `<span class="pm-glow"></span><span class="pm-dot"></span>` +
        `<span class="pm-num">${i + 1}</span></div>` +
        `<span class="pm-tip">${esc(a.title)}</span>`
      node.title = `D${d.day} · ${a.time || ''} ${a.title}`
      node.dataset.day = String(d.day)
      node.dataset.index = String(i)
      node.addEventListener('click', () => emit('select', { day: d.day, index: i }))
      markers.push(
        new ml.Marker({ element: node, anchor: 'center' })
          .setLngLat(toGcj(a.lng, a.lat))
          .addTo(map),
      )
    })
  })
  applyHighlight()
}

/**
 * 只切换标记的选中样式，不重绘 —— 重排/删点时才会走 drawMarkers。
 * 右侧列表点某行、或地图上点某个点，都会走到这里。
 */
function applyHighlight() {
  const h = props.highlight
  markers.forEach((m) => {
    const el = m.getElement?.()
    if (!el) return
    const on = !!h && Number(el.dataset.day) === h.day && Number(el.dataset.index) === h.index
    el.classList.toggle('is-on', on)
  })
}

/* 附近推荐点位：只画当前天返回的酒店/餐厅（坐标是 WGS84） */
function drawRecMarkers() {
  const ml = window.maplibregl || maplibregl
  if (!ml || !map) return
  recMarkers.forEach((m) => m.remove())
  recMarkers = []

  const r = props.recommendations
  for (const key of Object.keys(REC_META)) {
    const meta = REC_META[key]
    const items = r?.[key]?.items || []
    items.forEach((p) => {
      if (p?.lat == null || p?.lng == null) return
      const color = theme.value === 'light' ? meta.light : meta.dark
      const node = document.createElement('div')
      node.className = `rec-marker rec-${key}`
      node.dataset.kind = key
      node.dataset.recId = recId(p)
      // 有中文译名时标记上也用译名，避免地图是英文、列表是中文
      const shown = p.name_zh || p.name
      node.innerHTML =
        `<span class="rm-dot" style="--rc:${color}">${meta.icon}</span>` +
        `<span class="pm-tip">${esc(shown)}</span>`
      node.title = [shown, fmtDist(p.distance_m), p.address].filter(Boolean).join(' · ')
      node.addEventListener('click', () => {
        // 与站点标记一致：点的是正在看的那个点，不再飞视野，交给右侧列表定位
        emit('select-place', { kind: key, item: p })
      })
      recMarkers.push(
        new ml.Marker({ element: node, anchor: 'center' })
          .setLngLat(toGcj(p.lng, p.lat))
          .addTo(map),
      )
    })
  }
  applyRecHighlight()
}

/** 推荐标记的选中态：只切 class，不重绘，避免点击时闪一下 */
function applyRecHighlight() {
  const f = props.recFocus
  recMarkers.forEach((m) => {
    const el = m.getElement?.()
    if (!el) return
    el.classList.toggle('is-on', !!f && el.dataset.kind === f.kind && el.dataset.recId === f.id)
  })
}

function addLayers() {
  if (!map || map.getSource('legs')) return
  map.addSource('legs', { type: 'geojson', data: legData() })
  // 道路/步行/地铁：外发光 → 高对比描边 → 纯色主线
  // 底图（尤其暗色下的湖泊/地铁/绿地）颜色很杂，只有「亮轮廓 + 粗主线」才压得住
  map.addLayer({
    id: 'leg-glow', type: 'line', source: 'legs',
    filter: ['==', ['get', 'dashed'], 0],
    paint: {
      'line-color': ['get', 'color'], 'line-width': 14, 'line-opacity': 0.22,
      'line-blur': 6,
    },
  })
  map.addLayer({
    id: 'leg-casing', type: 'line', source: 'legs',
    filter: ['==', ['get', 'dashed'], 0],
    paint: { 'line-color': ['get', 'casing'], 'line-width': 9, 'line-opacity': 0.9 },
  })
  map.addLayer({
    id: 'leg-line', type: 'line', source: 'legs',
    filter: ['==', ['get', 'dashed'], 0],
    paint: { 'line-color': ['get', 'color'], 'line-width': 4.5, 'line-opacity': 1 },
  })
  // 铁路/航班：纯色虚线（MapLibre 的 line-dasharray 不支持按要素取值，故用 filter 分层）
  // 只用高对比色：暗色主题下是白线，亮色主题下是深色线，不再叠加彩色芯线和发光
  map.addLayer({
    id: 'leg-dash', type: 'line', source: 'legs',
    filter: ['==', ['get', 'dashed'], 1],
    paint: {
      'line-color': ['get', 'casing'], 'line-width': 4, 'line-opacity': 1,
      'line-dasharray': DASH_PATTERN,
    },
  })
}

function hasSize() {
  return !!el.value && el.value.clientWidth > 0 && el.value.clientHeight > 0
}

function fit(retry = 0) {
  if (!map) return
  // 合并进 Vue 后容器可能在布局切换前是 0×0，此时 fitBounds 会被 MapLibre 静默忽略
  if (!hasSize()) {
    if (retry < 10) {
      cancelAnimationFrame(fitRaf)
      fitRaf = requestAnimationFrame(() => fit(retry + 1))
    }
    return
  }
  const pts = []
  shownDays().forEach((d) =>
    (d.activities || []).forEach((a) => {
      if (a.lat != null && a.lng != null) pts.push(toGcj(a.lng, a.lat))
    }),
  )
  // 城际段可见时，把出发地也纳入取景
  const arr = props.plan?.arrival
  const firstDay = props.plan?.days?.[0]?.day
  if (
    arr?.leg &&
    (props.activeDay === 0 || props.activeDay === firstDay) &&
    arr.origin_lat != null &&
    arr.origin_lng != null
  ) {
    pts.push(toGcj(arr.origin_lng, arr.origin_lat))
  }
  if (!pts.length) return
  const lngs = pts.map((p) => p[0])
  const lats = pts.map((p) => p[1])
  map.resize()
  map.fitBounds(
    [[Math.min(...lngs), Math.min(...lats)], [Math.max(...lngs), Math.max(...lats)]],
    {
      padding: { top: 60, bottom: 60, left: 60, right: props.padRight },
      duration: 700,
      maxZoom: 13.2,
    },
  )
  didFit = true
}

function refresh() {
  if (!styleReady || !map) return
  map.getSource('legs')?.setData(legData())
  drawMarkers()
  drawRecMarkers()
  fit()
}

function init() {
  const ml = window.maplibregl || maplibregl
  if (!ml || !el.value) { emit('ready'); return }
  try {
    map = new ml.Map({
      container: el.value,
      style: buildStyle(),
      center: [104.06, 30.66],
      zoom: 9,
      attributionControl: false,
    })
  } catch (err) {
    console.warn('[map] 初始化失败', err)
    failed.value = true
    clearTimeout(bailTimer)
    emit('ready')
    return
  }
  map.addControl(new ml.ScaleControl({ maxWidth: 100, unit: 'metric' }), 'bottom-right')
  map.addControl(new ml.AttributionControl({ compact: true }), 'bottom-right')
  map.addControl(new ml.NavigationControl({ visualizePitch: true, showCompass: true }), 'bottom-right')
  // 鼠标右键 = 复位正北与倾斜（与罗盘按钮同功能）
  map.on('contextmenu', (e) => {
    e.preventDefault()
    map.easeTo({ bearing: 0, pitch: 0, duration: 500 })
  })
  // 样式解析完就建走线图层：底图瓦片加载慢时也不会拖到 load 之后才出现连线
  map.on('style.load', () => {
    addLayers()
    map.getSource('legs')?.setData(legData())
  })
  map.on('load', () => {
    styleReady = true
    clearTimeout(bailTimer)
    if (failTimer) clearTimeout(failTimer)
    addLayers()
    map.resize()
    refresh()
    failed.value = false
    emit('ready')          // 通知外层：地图已就绪，可以切到工作区布局
  })
  // 瓦片偶发失败只记录，不弹提示：慢网络下误报比真失败更常见
  map.on('error', (e) => {
    console.warn('[map] tile error', e?.error?.message || e)
  })

  // 布局切换、窗口缩放、行程单开合都会改变容器尺寸
  if (typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => {
      if (!map || !hasSize()) return
      map.resize()
      if (!didFit) fit()
    })
    resizeObserver.observe(el.value)
  }
}

function retry() {
  failed.value = false
  if (!map) {
    init()
    return
  }
  styleReady = false
  didFit = false
  map.setStyle(buildStyle())
  map.once('styledata', () => {
    styleReady = true
    addLayers()
    map.resize()
    refresh()
  })
  failTimer = setTimeout(() => {
    if (!styleReady) failed.value = true
  }, 6000)
}

onMounted(init)
onUnmounted(() => {
  if (bailTimer) clearTimeout(bailTimer)
  if (failTimer) clearTimeout(failTimer)
  cancelAnimationFrame(fitRaf)
  resizeObserver?.disconnect()
  resizeObserver = null
  markers.forEach((m) => m.remove())
  recMarkers.forEach((m) => m.remove())
  map?.remove()
  map = null
})

// 深度监听：重排/删除会原地修改 activities，浅监听感知不到
watch(
  [() => props.activeDay, () => props.padRight, () => props.plan, () => props.recommendations],
  refresh,
  { deep: true },
)
// 选中变化只切样式，不重建标记
watch(() => props.highlight, applyHighlight, { deep: true })
// 右侧点了某家酒店/餐厅：只切样式，视野由父组件显式调用 flyToPlace 控制
watch(() => props.recFocus, applyRecHighlight, { deep: true })
// 底图始终是同一套亮色瓦片，暗色由 CSS filter 完成，无需重建 style
watch(theme, () => {
  if (!map || !styleReady) return
  drawMarkers()
  drawRecMarkers()
  map.getSource('legs')?.setData(legData())
})

/** 飞到某个 WGS84 点位。右侧浮层展开时向右留白，别把目标压在浮层底下 */
function flyToPoint(lng, lat, zoom) {
  if (lng == null || lat == null || !map) return
  map.flyTo({
    center: toGcj(lng, lat),
    zoom,
    duration: 900,
    padding: { top: 80, bottom: 80, left: 80, right: props.padRight },
  })
}

defineExpose({
  flyTo(day, index) {
    const d = (props.plan?.days || []).find((x) => x.day === day)
    const a = d?.activities?.[index]
    if (a) flyToPoint(a.lng, a.lat, 14.5)
  },
  /** 飞到某家推荐的酒店/餐厅（右侧列表点击时用） */
  flyToPlace(kind, item) {
    void kind
    if (item) flyToPoint(item.lng, item.lat, 16)
  },
  /** 只强调不移动视野：地图上点标记时用，避免用户刚点完画面又飞走 */
  focus() {
    applyHighlight()
  },
  refresh,
})
</script>

<template>
  <div ref="el" class="mapgl" :class="{ 'map-dark': theme === 'dark' }">
    <div v-if="failed" class="map-fallback" role="alert">
      <span>{{ failedText }}</span>
      <button type="button" class="map-retry mono" @click="retry">{{ retryText }}</button>
    </div>
  </div>
</template>

<style scoped>
.mapgl { position: absolute; inset: 0; background: #ece5d8; }
/* 高德只有亮色瓦片：暗色主题用滤镜反转得到暗底（同 Window Seat 观感） */
.mapgl.map-dark :deep(canvas) {
  filter: invert(1) hue-rotate(180deg) brightness(0.92) contrast(0.95);
}
/* 错误提示：顶部紧凑横幅，不遮挡整张地图 */
.map-fallback {
  position: absolute; z-index: 5; top: 12px; left: 50%; transform: translateX(-50%);
  display: flex; align-items: center; gap: 10px;
  max-width: calc(100% - 24px); padding: 8px 12px; border-radius: 999px;
  color: #1d1a16; font-size: 12px; line-height: 1.4;
  background: rgba(246,241,230,.94); border: 1px solid rgba(23,20,15,.16);
  backdrop-filter: blur(14px) saturate(150%);
}
.map-retry {
  border: 1px solid rgba(23,20,15,.16); border-radius: 999px;
  background: transparent; color: #b22e26;
  font-size: 10px; padding: 4px 10px; cursor: pointer;
}
.map-retry:hover { border-color: #b22e26; }

/* 附近推荐点位：emoji 圆点，比站点编号小一圈 */
:deep(.rec-marker) { width: 20px; height: 20px; cursor: pointer; }
:deep(.rm-dot) {
  display: grid; place-items: center; width: 20px; height: 20px; border-radius: 50%;
  background: var(--rc); border: 1.5px solid #fff; font-size: 10px; line-height: 1;
  box-shadow: 0 0 8px color-mix(in srgb, var(--rc) 75%, transparent), 0 1px 3px rgba(0, 0, 0, 0.5);
  transition: transform 0.25s cubic-bezier(.2,.9,.2,1);
}
:deep(.rec-marker:hover .rm-dot) { transform: scale(1.3); }
:deep(.rec-foods .rm-dot) { border-radius: 7px; }
/* 右侧列表点了某家酒店/餐厅：放大 + 白环，并在上方浮出名字 */
:deep(.rec-marker.is-on) { z-index: 5; }
:deep(.rec-marker.is-on .rm-dot) {
  transform: scale(1.5);
  border-color: #fff;
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--rc) 45%, transparent), 0 0 20px var(--rc);
}
:deep(.rec-marker.is-on .pm-tip) {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}

/* 点位标记：数字与圆点同心 */
:deep(.poi-marker) { width: 22px; height: 22px; cursor: pointer; }
/* 选中时在标记上方显示站点名（不受 .pm-in 缩放影响，所以挂在 marker 上） */
:deep(.pm-tip) {
  position: absolute; bottom: calc(100% + 7px); left: 50%;
  transform: translateX(-50%) translateY(4px);
  padding: 3px 8px; border-radius: 8px; white-space: nowrap;
  font-size: 10.5px; line-height: 1.4; letter-spacing: 0.02em;
  color: #fff; background: rgba(10, 12, 16, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.16);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.45);
  opacity: 0; pointer-events: none;
  transition: opacity 0.25s cubic-bezier(.2,.9,.2,1), transform 0.25s cubic-bezier(.2,.9,.2,1);
}
:deep(.poi-marker.is-on .pm-tip) {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}
:deep(.pm-in) {
  position: relative; width: 22px; height: 22px;
  display: grid; place-items: center;
  transition: transform 0.3s cubic-bezier(.2,.9,.2,1);
}
:deep(.pm-glow) {
  position: absolute; width: 40px; height: 40px; border-radius: 50%;
  background: var(--pc); opacity: 0.2; filter: blur(2px);
}
:deep(.pm-dot) {
  width: 22px; height: 22px; border-radius: 50%;
  background: var(--pc); border: 2px solid #fff;
  box-shadow: 0 0 14px var(--pc); transition: transform 0.25s cubic-bezier(.2,.9,.2,1);
}
:deep(.pm-num) {
  position: absolute; inset: 0; display: grid; place-items: center;
  font-size: 9.5px; font-weight: 700; color: #fff;
  font-family: var(--font-mono); text-shadow: 0 1px 2px rgba(0, 0, 0, 0.65);
}
:deep(.poi-marker:hover .pm-dot) { transform: scale(1.25); }

/* 选中态：来自地图点击或右侧列表点击 —— 放大 + 亮圈 + 光晕扩散，一眼能认出是哪一个 */
:deep(.poi-marker.is-on) { z-index: 6; }
:deep(.poi-marker.is-on .pm-in) { transform: scale(1.22); }
:deep(.poi-marker.is-on .pm-dot) {
  border-color: #fff;
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--pc) 45%, transparent), 0 0 22px var(--pc);
}
:deep(.poi-marker.is-on .pm-glow) {
  opacity: 0.55;
  animation: pm-ping 1.6s cubic-bezier(.2,.9,.2,1) infinite;
}
:deep(.poi-marker.is-on .pm-num) { font-size: 10.5px; }
@keyframes pm-ping {
  0% { transform: scale(0.9); opacity: 0.55; }
  70% { transform: scale(1.9); opacity: 0; }
  100% { transform: scale(1.9); opacity: 0; }
}

/* 控件：同排 [刻度线] [归属] [缩放+罗盘] */
:deep(.maplibregl-ctrl-bottom-right) {
  flex-direction: row !important; align-items: flex-end !important; gap: 10px;
  transition: transform 0.5s cubic-bezier(.2,.9,.2,1);
}
:deep(.maplibregl-ctrl-scale) {
  background: transparent !important; border: none !important; border-radius: 0 !important;
  color: #fff !important; font-size: 11px !important; font-weight: 600;
  padding: 0 0 3px !important; margin: 0 0 10px !important;
  border-bottom: 2.5px solid #fff !important; box-shadow: none !important;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.9);
}
:deep(.maplibregl-ctrl-attrib) {
  font-size: 10px !important; background: rgba(0, 0, 0, 0.35) !important;
  border-radius: 8px !important;
}
:deep(.maplibregl-ctrl-attrib a) { color: #bbb !important; }
:deep(.maplibregl-ctrl-group) {
  background: rgba(246,241,230,.94) !important; border: 1px solid rgba(23,20,15,.16) !important;
}
</style>
