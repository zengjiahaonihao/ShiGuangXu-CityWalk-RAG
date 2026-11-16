<script setup>
import { computed, ref, watch } from 'vue'
import { getLLM, llmHeaders, setLLM } from '../api'

const props = defineProps({ open: { type: Boolean, default: false } })
const emit = defineEmits(['update:open', 'changed'])

const key = ref('')
const base = ref('https://api.deepseek.com')
const model = ref('deepseek-chat')
const saved = ref('')
const testing = ref(false)
const testMsg = ref('')

const hasKey = computed(() => Boolean(saved.value))

// 服务端 .env 是否配了 Key（不暴露内容，仅用于提示游客模式）
watch(() => props.open, async (v) => {
  if (!v) return
  const cfg = getLLM()
  key.value = cfg?.key || ''
  base.value = cfg?.base || 'https://api.deepseek.com'
  model.value = cfg?.model || 'deepseek-chat'
  saved.value = cfg?.key || ''
  testMsg.value = ''
})

function close() {
  emit('update:open', false)
}

function save() {
  const cfg = {
    key: key.value.trim(),
    base: base.value.trim() || 'https://api.deepseek.com',
    model: model.value.trim() || 'deepseek-chat'
  }
  setLLM(cfg.key ? cfg : null)
  saved.value = cfg.key
  emit('changed', Boolean(cfg.key))
  testMsg.value = cfg.key ? '已保存到本机浏览器，仅本次设备生效。' : '已清除，回到游客模式。'
}

function clear() {
  key.value = ''
  setLLM(null)
  saved.value = ''
  emit('changed', false)
  testMsg.value = '已清除，回到游客模式。'
}

async function testKey() {
  if (!key.value.trim()) {
    testMsg.value = '先填写 API Key。'
    return
  }
  testing.value = true
  testMsg.value = '正在测试…'
  try {
    const res = await fetch(`${base.value.replace(/\/$/, '')}/models`, {
      headers: { Authorization: `Bearer ${key.value.trim()}` }
    })
    testMsg.value = res.ok
      ? '连接成功，Key 可用。'
      : `连接失败（HTTP ${res.status}），请检查 Key 或服务地址。`
  } catch (e) {
    testMsg.value = '无法直连该地址（多为浏览器跨域限制）；保存后在问答中由后端代发即可。'
  } finally {
    testing.value = false
  }
}
</script>

<template>
  <transition name="fade">
    <div v-if="open" class="api-veil" @click.self="close">
      <section class="api-box">
        <header class="api-head">
          <div>
            <p class="kicker">MODEL ACCESS</p>
            <h2>接入你自己的大模型</h2>
          </div>
          <button class="x" aria-label="关闭" @click="close">×</button>
        </header>

        <p class="api-intro">
          绑定后，回答由你自己的 Key 生成；不填则进入<strong>游客模式</strong>——只返回资料原文，不调用任何模型。
          Key 只保存在本机浏览器，并随请求转发给你本地运行的后端。
        </p>

        <label class="field">
          <span>API Key</span>
          <input v-model="key" type="password" placeholder="sk-..." autocomplete="off" />
        </label>

        <div class="row">
          <label class="field">
            <span>服务地址（Base URL）</span>
            <input v-model="base" type="text" placeholder="https://api.deepseek.com" />
          </label>
          <label class="field">
            <span>模型名</span>
            <input v-model="model" type="text" placeholder="deepseek-chat" />
          </label>
        </div>

        <p class="api-hint">
          支持任何 OpenAI 兼容接口（DeepSeek、Moonshot、通义、本地 vLLM 等），把 Base URL 换成对应地址即可。
        </p>

        <div class="api-actions">
          <button class="btn primary" @click="save">保存</button>
          <button class="btn" :disabled="testing" @click="testKey">{{ testing ? '测试中…' : '测试连接' }}</button>
          <button class="btn" @click="clear">清除</button>
          <span class="state" :class="{ on: hasKey }">{{ hasKey ? '已绑定' : '游客模式' }}</span>
        </div>

        <p v-if="testMsg" class="api-msg">{{ testMsg }}</p>
      </section>
    </div>
  </transition>
</template>

<style scoped>
.api-veil {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(20, 15, 10, 0.55);
  backdrop-filter: blur(4px);
}

.api-box {
  width: min(560px, 96vw);
  max-height: 88vh;
  overflow-y: auto;
  padding: 28px 28px 24px;
  background: var(--paper-2);
  border: 1px solid var(--line);
  box-shadow: 0 28px 70px rgba(23, 20, 15, 0.28);
}

.api-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.kicker {
  margin: 0 0 6px;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.3em;
  color: var(--seal);
}

.api-head h2 {
  margin: 0;
  font-family: var(--font-serif);
  font-size: 24px;
  font-weight: 500;
  letter-spacing: 0.08em;
}

.x {
  border: 0;
  background: transparent;
  font-size: 24px;
  line-height: 1;
  color: var(--muted);
  cursor: pointer;
}

.api-intro {
  margin: 16px 0 20px;
  font-size: 12.5px;
  line-height: 1.95;
  color: var(--muted);
}

.api-intro strong {
  color: var(--ink);
  font-weight: 500;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.field span {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.18em;
  color: var(--muted-2);
}

.field input {
  padding: 10px 12px;
  border: 1px solid var(--line);
  background: var(--paper);
  font-size: 13px;
  color: var(--ink);
  outline: none;
  font-family: var(--font-mono);
}

.field input:focus {
  border-color: var(--seal-soft);
}

.row {
  display: flex;
  gap: 12px;
  margin-top: 14px;
}

.api-hint {
  margin: 12px 0 0;
  font-size: 11.5px;
  line-height: 1.8;
  color: var(--muted-2);
}

.api-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 20px;
}

.state {
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.16em;
  padding: 4px 10px;
  border: 1px solid var(--line);
  color: var(--muted-2);
}

.state.on {
  border-color: var(--seal-soft);
  color: var(--seal);
}

.api-msg {
  margin: 14px 0 0;
  font-size: 12px;
  color: var(--ink-soft);
  border-left: 2px solid var(--seal-soft);
  padding-left: 10px;
}

@media (max-width: 560px) {
  .row {
    flex-direction: column;
  }
}
</style>
