<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getLLM } from '../api'
import ApiKeyModal from './ApiKeyModal.vue'

const route = useRoute()
const scrolled = ref(false)
const menuOpen = ref(false)
const apiOpen = ref(false)
const hasKey = ref(Boolean(getLLM()))

function onKeyChanged(v) {
  hasKey.value = Boolean(v)
}

const items = [
  { to: '/', label: '首页', en: 'Index' },
  { to: '/knowledge', label: '知识库', en: 'Archive' },
  { to: '/chat', label: '漫步对话', en: 'Dialogue' },
  { to: '/route', label: '路线生成', en: 'Route' },
  { to: '/history', label: '历史记录', en: 'Record' }
]

function onScroll() {
  scrolled.value = window.scrollY > 40
}

onMounted(() => {
  window.addEventListener('scroll', onScroll, { passive: true })
  onScroll()
  // 便于分享/文档直达：/?api=1 直接打开接入面板
  if (new URLSearchParams(window.location.search).get('api') === '1') apiOpen.value = true
})

onUnmounted(() => window.removeEventListener('scroll', onScroll))

// 城市档案页属于「知识库」这条线，导航高亮跟随
function isActive(to) {
  if (route.path === to) return true
  return to === '/knowledge' && route.path.startsWith('/city')
}
</script>

<template>
  <header class="nav" :class="{ scrolled, open: menuOpen, 'on-top': !scrolled && !menuOpen }">
    <div class="nav-inner">
      <router-link to="/" class="brand" @click="menuOpen = false">
        <span class="brand-cn">拾光叙</span>
        <span class="brand-en">SHIGUANGXU</span>
      </router-link>

      <nav class="links">
        <router-link
          v-for="it in items"
          :key="it.to"
          :to="it.to"
          class="link"
          :class="{ active: isActive(it.to) }"
        >
          <span class="link-cn">{{ it.label }}</span>
          <span class="link-en">{{ it.en }}</span>
        </router-link>
      </nav>

      <button class="api-entry" :class="{ on: hasKey }" :title="hasKey ? '已绑定自己的 API Key' : '游客模式：未绑定 API Key'" @click="apiOpen = true">
        <span class="dot"></span>
        <span class="txt">API</span>
      </button>

      <button class="burger" :aria-label="menuOpen ? '关闭菜单' : '打开菜单'" @click="menuOpen = !menuOpen">
        <span :class="{ x: menuOpen }"></span>
        <span :class="{ x: menuOpen }"></span>
      </button>
    </div>

    <!-- 移动端全屏菜单 -->
    <transition name="fade">
      <div v-if="menuOpen" class="mobile-menu">
        <router-link
          v-for="(it, i) in items"
          :key="it.to"
          :to="it.to"
          class="mm-item"
          @click="menuOpen = false"
        >
          <span class="mm-no">0{{ i + 1 }}</span>
          <span class="mm-cn">{{ it.label }}</span>
          <span class="mm-en">{{ it.en }}</span>
        </router-link>
      </div>
    </transition>
  </header>

  <ApiKeyModal v-model:open="apiOpen" @changed="onKeyChanged" />
</template>

<style scoped>
.nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 800;
  background: transparent;
  transition: background 0.5s var(--ease-soft), border-color 0.5s, backdrop-filter 0.5s;
  border-bottom: 1px solid transparent;
}

.nav.scrolled {
  background: rgba(239, 232, 220, 0.82);
  backdrop-filter: blur(14px);
  border-bottom-color: var(--line-soft);
}

/* 顶部深色主视觉 / 页头上，导航转浅色 */
.nav.on-top .brand-cn {
  color: #fdf8ec;
}

.nav.on-top .brand-en {
  color: rgba(248, 241, 226, 0.58);
}

.nav.on-top .link {
  color: rgba(248, 241, 226, 0.82);
}

.nav.on-top .link:hover,
.nav.on-top .link.active {
  color: #fdf8ec;
}

.nav.on-top .link.active::after {
  background: var(--seal-soft);
}

.nav.on-top .link-en {
  color: rgba(248, 241, 226, 0.52);
}

.nav.on-top .burger span {
  background: #f8f1e2;
}

.nav.open {
  background: var(--paper);
}

.nav-inner {
  max-width: 1440px;
  margin: 0 auto;
  padding: 22px 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.brand {
  display: flex;
  flex-direction: column;
  line-height: 1.1;
}

.brand-cn {
  font-family: var(--font-serif);
  font-size: 21px;
  letter-spacing: 0.22em;
  color: var(--ink);
}

.brand-en {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.42em;
  color: var(--muted-2);
  margin-top: 3px;
}

.links {
  display: flex;
  align-items: center;
  gap: 34px;
}

.link {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding-bottom: 4px;
  color: var(--ink-soft);
  transition: color 0.3s;
}

.link-cn {
  font-size: 13.5px;
  letter-spacing: 0.14em;
}

.link-en {
  font-family: var(--font-mono);
  font-size: 8.5px;
  letter-spacing: 0.3em;
  color: var(--muted-2);
  opacity: 0;
  transform: translateY(-3px);
  transition: all 0.35s var(--ease-soft);
}

.link::after {
  content: "";
  position: absolute;
  left: 0;
  bottom: 0;
  width: 0;
  height: 1px;
  background: var(--seal);
  transition: width 0.4s var(--ease-soft);
}

.link:hover {
  color: var(--ink);
}

.link:hover .link-en {
  opacity: 1;
  transform: translateY(0);
}

.link:hover::after {
  width: 100%;
}

.link.active {
  color: var(--ink);
}

.link.active::after {
  width: 100%;
  background: var(--ink);
}

/* 汉堡 */
.api-entry {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-left: 18px;
  padding: 5px 10px;
  border: 1px solid var(--line);
  background: transparent;
  cursor: pointer;
  transition: all 0.3s var(--ease-soft);
}

.api-entry .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--muted-2);
}

.api-entry.on .dot {
  background: var(--seal);
  box-shadow: 0 0 0 3px rgba(178, 46, 38, 0.14);
}

.api-entry .txt {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.2em;
  color: var(--muted);
}

.api-entry:hover {
  border-color: var(--seal-soft);
}

.api-entry:hover .txt {
  color: var(--seal);
}

/* 首屏压在深色主视觉上时，改用浅色描边 */
.nav.on-top .api-entry {
  border-color: rgba(248, 241, 226, 0.32);
}

.nav.on-top .api-entry .txt {
  color: rgba(248, 241, 226, 0.72);
}

.nav.on-top .api-entry .dot {
  background: rgba(248, 241, 226, 0.45);
}

.nav.on-top .api-entry.on .dot {
  background: #c2604f;
  box-shadow: 0 0 0 3px rgba(194, 96, 79, 0.25);
}

.nav.on-top .api-entry:hover {
  border-color: rgba(248, 241, 226, 0.7);
}

.nav.on-top .api-entry:hover .txt {
  color: #f8f1e2;
}

.burger {
  display: none;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  width: 34px;
  height: 34px;
  background: none;
  border: 0;
  padding: 0;
}

.burger span {
  display: block;
  height: 1px;
  width: 100%;
  background: var(--ink);
  transition: transform 0.4s var(--ease-soft);
}

.burger span.x:first-child {
  transform: translateY(3px) rotate(45deg);
}

.burger span.x:last-child {
  transform: translateY(-3px) rotate(-45deg);
}

/* 移动端菜单 */
.mobile-menu {
  padding: 12px 32px 40px;
  border-top: 1px solid var(--line-soft);
}

.mm-item {
  display: flex;
  align-items: baseline;
  gap: 14px;
  padding: 16px 0;
  border-bottom: 1px solid var(--line-soft);
}

.mm-no {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--seal);
  letter-spacing: 0.2em;
}

.mm-cn {
  font-family: var(--font-serif);
  font-size: 22px;
  letter-spacing: 0.1em;
}

.mm-en {
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.3em;
  color: var(--muted-2);
}

@media (max-width: 1024px) {
  .nav-inner {
    padding: 18px 24px;
  }
  .links {
    gap: 22px;
  }
  .link-en {
    display: none;
  }
}

@media (max-width: 820px) {
  .links {
    display: none;
  }
  .burger {
    display: flex;
  }
}
</style>
