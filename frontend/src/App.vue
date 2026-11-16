<script setup>
import { watch } from 'vue'
import { useRoute } from 'vue-router'
import PosterNav from './components/PosterNav.vue'
import FloatingCapsule from './components/FloatingCapsule.vue'
import SiteFooter from './components/SiteFooter.vue'

const route = useRoute()

// 每次切换页面回到顶部（除首页保留首屏冲顶体验）
watch(
  () => route.fullPath,
  () => {
    window.scrollTo({ top: 0, behavior: 'auto' })
  }
)
</script>

<template>
  <PosterNav />

  <!-- 真正的路由页面：点哪个导航就切换到哪个页面 -->
  <main class="app-main">
    <router-view v-slot="{ Component }">
      <transition name="page" mode="out-in">
        <component :is="Component" :key="route.path" />
      </transition>
    </router-view>
  </main>

  <SiteFooter />
  <FloatingCapsule />
</template>

<style scoped>
.app-main {
  position: relative;
  z-index: 1;
  min-height: 60vh;
}

.page-enter-active,
.page-leave-active {
  transition: opacity 0.45s var(--ease-soft), transform 0.45s var(--ease-soft);
}

.page-enter-from {
  opacity: 0;
  transform: translateY(14px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
