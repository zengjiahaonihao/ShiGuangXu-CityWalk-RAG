const BASE = '/api'
export const LLM_STORE_KEY = 'sgx_llm_v1'

export function getLLM() {
  try {
    const raw = localStorage.getItem(LLM_STORE_KEY)
    if (!raw) return null
    const cfg = JSON.parse(raw)
    return cfg && cfg.key ? cfg : null
  } catch (e) {
    return null
  }
}

export function setLLM(cfg) {
  if (!cfg || !cfg.key) localStorage.removeItem(LLM_STORE_KEY)
  else localStorage.setItem(LLM_STORE_KEY, JSON.stringify(cfg))
}

export function llmHeaders() {
  const cfg = getLLM()
  if (!cfg) return {}
  return {
    'X-LLM-Key': cfg.key,
    ...(cfg.base ? { 'X-LLM-Base': cfg.base } : {}),
    ...(cfg.model ? { 'X-LLM-Model': cfg.model } : {})
  }
}

async function request(path, options = {}) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json', ...llmHeaders() },
    ...options
  })
  if (!res.ok) {
    let msg = `请求失败 (${res.status})`
    try {
      const data = await res.json()
      msg = data.detail || data.message || msg
    } catch (e) { /* ignore */ }
    throw new Error(msg)
  }
  return res.json()
}

export const api = {
  health: () => request('/health'),
  quotes: (n = 8) => request(`/quotes?n=${n}`),

  stats: () => request('/knowledge/stats'),
  categories: () => request('/knowledge/categories'),
  listDocs: (category, origin) => request('/knowledge/docs'
    + (category || origin
      ? `?${new URLSearchParams({ ...(category ? { category } : {}), ...(origin ? { origin } : {}) }).toString()}`
      : '')),
  cities: () => request('/knowledge/cities'),
  cityDetail: (id) => request('/knowledge/cities/' + encodeURIComponent(id)),
  syncBuiltin: (force = false) => request(`/knowledge/builtin/sync?force=${force}`, { method: 'POST' }),
  uploadDoc: async (file, category) => {
    const form = new FormData()
    form.append('file', file)
    form.append('category', category)
    const res = await fetch(`${BASE}/knowledge/upload`, { method: 'POST', body: form })
    if (!res.ok) {
      let msg = `上传失败 (${res.status})`
      try {
        const d = await res.json()
        msg = d.detail || msg
      } catch (e) { /* ignore */ }
      throw new Error(msg)
    }
    return res.json()
  },
  updateDoc: (id, payload) => request(`/knowledge/docs/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  }),
  deleteDoc: (id) => request(`/knowledge/docs/${id}`, { method: 'DELETE' }),
  clearDocs: () => request('/knowledge/clear', { method: 'DELETE' }),

  listHistory: (type, keyword) => {
    const params = new URLSearchParams()
    if (type) params.set('type', type)
    if (keyword) params.set('keyword', keyword)
    return request('/history?' + params.toString())
  },
  deleteHistory: (id) => request(`/history/${id}`, { method: 'DELETE' }),
  clearHistory: () => request('/history', { method: 'DELETE' })
}

/**
 * SSE 流式请求。
 * @param {string} path /chat/stream 或 /route/stream
 * @param {object} body 请求体
 * @param {{onSources?:Function,onDelta?:Function,onDone?:Function,onError?:Function}} handlers
 */
export function streamPost(path, body, handlers = {}) {
  const controller = new AbortController()
  const run = async () => {
    try {
      const res = await fetch(BASE + path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...llmHeaders() },
        body: JSON.stringify(body),
        signal: controller.signal
      })
      if (!res.ok) {
        let msg = `请求失败 (${res.status})`
        try {
          const d = await res.json()
          msg = d.detail || msg
        } catch (e) { /* ignore */ }
        handlers.onError?.(new Error(msg))
        return
      }
      const reader = res.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const blocks = buffer.split('\n\n')
        buffer = blocks.pop() || ''
        for (const block of blocks) {
          const eventLine = block.split('\n').find((l) => l.startsWith('event:'))
          const dataLine = block.split('\n').find((l) => l.startsWith('data:'))
          if (!eventLine || !dataLine) continue
          const event = eventLine.slice(6).trim()
          let data = {}
          try {
            data = JSON.parse(dataLine.slice(5).trim())
          } catch (e) {
            continue
          }
          if (event === 'sources') handlers.onSources?.(data.sources || [])
          else if (event === 'delta') handlers.onDelta?.(data.text || '')
          else if (event === 'done') handlers.onDone?.(data)
          else if (event === 'error') handlers.onError?.(new Error(data.message || '生成失败'))
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') handlers.onError?.(err)
    }
  }
  run()
  return () => controller.abort()
}
