<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'

const quote = ref('一条老街，半城烟火。')
const year = new Date().getFullYear()

onMounted(() => {
  api.quotes(8).then((q) => { if (q?.quotes?.length) quote.value = q.quotes[0] }).catch(() => {})
})
</script>

<template>
  <footer class="foot">
    <div class="foot-inner">
      <div class="foot-col">
        <span class="foot-brand">拾光叙</span>
        <span class="foot-en">SHIGUANGXU · MEMORY OF STREETS</span>
      </div>
      <p class="foot-quote">「{{ quote }}」</p>
      <div class="foot-col right">
        <span>Vue 3 · FastAPI · FAISS · DeepSeek</span>
        <span class="foot-en">© {{ year }} 传智杯 RAG 赛道</span>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.foot {
  padding: 46px 0 54px;
  border-top: 1px solid var(--line-soft);
  background: var(--paper-light);
}

.foot-inner {
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
}

.foot-col {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.foot-col.right {
  text-align: right;
}

.foot-brand {
  font-family: var(--font-serif);
  font-size: 18px;
  letter-spacing: 0.22em;
  color: var(--ink);
}

.foot-en {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.3em;
  color: var(--muted-2);
}

.foot-quote {
  margin: 0;
  font-family: var(--font-serif);
  font-size: 13px;
  letter-spacing: 0.1em;
  color: var(--ink-soft);
}

@media (max-width: 1024px) {
  .foot-inner { padding: 0 28px; }
}

@media (max-width: 640px) {
  .foot-inner { flex-direction: column; align-items: flex-start; }
  .foot-col.right { text-align: left; }
}
</style>
