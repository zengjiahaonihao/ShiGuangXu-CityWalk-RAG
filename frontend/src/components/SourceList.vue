<script setup>
import { ref } from 'vue'

const props = defineProps({
  sources: { type: Array, default: () => [] }
})

const openIndex = ref(-1)
const toggle = (i) => {
  openIndex.value = openIndex.value === i ? -1 : i
}
</script>

<template>
  <div v-if="sources && sources.length" class="sources">
    <div class="src-head">
      <span class="dot"></span>
      资料来源 · {{ sources.length }} 条（点击展开原文）
    </div>
    <div
      v-for="(s, i) in sources"
      :key="s.doc_id + '-' + s.chunk_id"
      class="src-item"
      :class="{ open: openIndex === i }"
      @click="toggle(i)"
    >
      <div class="src-title">
        <span class="idx">[{{ i + 1 }}]</span>
        <span class="name">《{{ s.doc_name }}》</span>
        <span class="score">相关度 {{ (s.score * 100).toFixed(0) }}%</span>
        <span class="arrow">{{ openIndex === i ? '收起' : '展开' }}</span>
      </div>
      <div v-show="openIndex === i" class="src-text">{{ s.text }}</div>
    </div>
  </div>
</template>

<style scoped>
.sources {
  margin-top: 20px;
  padding: 16px 18px;
  background: transparent;
  border-top: 1px solid var(--line);
}

.src-head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--ink-3);
  margin-bottom: 6px;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--jade);
}

.src-item {
  padding: 8px 0;
  border-radius: 0;
  cursor: pointer;
  transition: background 0.3s var(--ease-soft);
}

.src-item:hover {
  background: rgba(168, 59, 44, 0.03);
}

.src-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  color: var(--ink-2);
  flex-wrap: wrap;
}

.idx {
  color: var(--seal);
  font-weight: 700;
}

.name {
  color: var(--ink);
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}

.score {
  color: var(--ink-3);
}

.arrow {
  margin-left: auto;
  color: var(--jade);
  font-size: 12px;
}

.src-text {
  margin-top: 8px;
  padding: 12px 16px;
  background: rgba(30, 26, 22, 0.03);
  border-left: 1px solid var(--gold);
  border-radius: 0;
  font-size: 12.5px;
  line-height: 1.9;
  color: var(--ink-soft);
  white-space: pre-wrap;
}
</style>
