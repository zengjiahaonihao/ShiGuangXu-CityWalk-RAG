<script setup>
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'

const props = defineProps({
  content: { type: String, default: '' }
})

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  typographer: false
})

const html = computed(() => {
  const text = props.content || ''
  // 把 [1] [2] 这类引用标记渲染成上标小章
  const marked = text.replace(/\[(\d+)\]/g, '<sup class="cite">[$1]</sup>')
  return md.render(marked)
})
</script>

<template>
  <div class="md-body" v-html="html"></div>
</template>

<style scoped>
.md-body :deep(.cite) {
  display: inline-block;
  min-width: 15px;
  padding: 0 3px;
  margin: 0 2px;
  font-family: var(--font-mono);
  font-size: 10px;
  line-height: 15px;
  text-align: center;
  color: var(--seal);
  border: 1px solid rgba(168, 59, 44, 0.35);
  border-radius: 0;
  vertical-align: super;
}
</style>
