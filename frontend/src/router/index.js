import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'

const routes = [
  { path: '/', name: 'home', component: HomeView, meta: { title: '首页' } },
  { path: '/knowledge', name: 'knowledge', component: () => import('../views/KnowledgeView.vue'), meta: { title: '知识库' } },
  { path: '/chat', name: 'chat', component: () => import('../views/ChatView.vue'), meta: { title: '漫步对话' } },
  { path: '/route', name: 'route', component: () => import('../views/RouteView.vue'), meta: { title: '路线生成' } },
  { path: '/history', name: 'history', component: () => import('../views/HistoryView.vue'), meta: { title: '历史记录' } },
  { path: '/city/:id', name: 'city', component: () => import('../views/CityView.vue'), meta: { title: '城市档案' } }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

router.afterEach((to) => {
  document.title = `${to.meta.title || ''} · 拾光叙`
})

export default router
