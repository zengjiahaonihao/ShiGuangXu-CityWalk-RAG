<script setup>
defineProps({
  no: { type: String, default: '00' },
  cn: { type: String, required: true },
  en: { type: String, default: '' },
  lead: { type: String, default: '' },
  image: { type: String, default: '' },
  meta: { type: Array, default: () => [] }
})
</script>

<template>
  <header class="ph">
    <div class="ph-bg">
      <img v-if="image" :src="image" alt="" />
    </div>
    <div class="ph-scrim"></div>

    <div class="ph-inner">
      <p class="ph-no">
        <span class="ph-num">{{ no }}</span>
        <span class="ph-en">{{ en }}</span>
      </p>

      <h1 class="display ph-cn">{{ cn }}</h1>
      <hr class="rule ph-rule" />
      <p v-if="lead" class="ph-lead">{{ lead }}</p>

      <ul v-if="meta.length" class="ph-meta">
        <li v-for="m in meta" :key="m.k">
          <b>{{ m.v }}</b>
          <span>{{ m.k }}</span>
        </li>
      </ul>
    </div>

    <span class="ph-seal">拾</span>
  </header>
</template>

<style scoped>
.ph {
  position: relative;
  min-height: 46vh;
  display: flex;
  align-items: flex-end;
  overflow: hidden;
  background: #241a12;
  color: #f8f1e2;
  border-bottom: 1px solid var(--line);
}

.ph-bg {
  position: absolute;
  inset: 0;
}

.ph-bg img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  filter: saturate(0.82) contrast(1.05);
  transform: scale(1.04);
  animation: slowzoom 18s var(--ease-soft) forwards;
}

@keyframes slowzoom {
  from { transform: scale(1.06); }
  to { transform: scale(1); }
}

.ph-scrim {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, rgba(24, 17, 10, 0.86) 0%, rgba(24, 17, 10, 0.6) 40%, rgba(24, 17, 10, 0.28) 72%, rgba(24, 17, 10, 0.42) 100%),
    linear-gradient(180deg, rgba(24, 17, 10, 0.5) 0%, rgba(24, 17, 10, 0) 34%),
    linear-gradient(0deg, rgba(22, 16, 9, 0.7) 0%, rgba(22, 16, 9, 0) 56%);
}

.ph-inner {
  position: relative;
  z-index: 2;
  width: 100%;
  max-width: 1180px;
  margin: 0 auto;
  padding: 150px 48px 56px;
}

.ph-no {
  display: flex;
  align-items: baseline;
  gap: 16px;
  margin: 0 0 18px;
}

.ph-num {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.26em;
  color: var(--seal-soft);
}

.ph-en {
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.4em;
  color: rgba(248, 241, 226, 0.5);
}

.ph-cn {
  margin: 0;
  font-size: clamp(34px, 5.4vw, 66px);
  letter-spacing: 0.16em;
  font-weight: 500;
  color: #fdf8ec;
  text-shadow: 0 10px 40px rgba(18, 12, 7, 0.5);
  animation: rise 1s var(--ease-soft) both;
}

@keyframes rise {
  from { opacity: 0; transform: translateY(18px); }
  to { opacity: 1; transform: none; }
}

.ph-rule {
  width: 78px;
  margin: 22px 0;
  background: rgba(248, 241, 226, 0.45);
  animation: rise 1s 0.1s var(--ease-soft) both;
}

.ph-lead {
  margin: 0;
  max-width: 620px;
  font-size: 13.5px;
  line-height: 2.1;
  letter-spacing: 0.12em;
  color: rgba(248, 241, 226, 0.82);
  animation: rise 1s 0.18s var(--ease-soft) both;
}

.ph-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 40px;
  margin: 34px 0 0;
  padding: 0;
  list-style: none;
  animation: rise 1s 0.26s var(--ease-soft) both;
}

.ph-meta li {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ph-meta b {
  font-family: var(--font-serif);
  font-size: 22px;
  font-weight: 500;
  color: #fdf8ec;
}

.ph-meta span {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.3em;
  color: rgba(248, 241, 226, 0.55);
}

.ph-seal {
  position: absolute;
  right: 56px;
  bottom: 56px;
  z-index: 2;
  width: 54px;
  height: 54px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-serif);
  font-size: 24px;
  color: #fdf3e5;
  border: 1.5px solid rgba(178, 46, 38, 0.85);
  background: rgba(178, 46, 38, 0.28);
  letter-spacing: 0;
  transform: rotate(-3deg);
}

@media (max-width: 1024px) {
  .ph-inner { padding: 128px 28px 44px; }
  .ph-seal { right: 24px; bottom: 30px; width: 44px; height: 44px; font-size: 20px; }
}

@media (max-width: 640px) {
  .ph-meta { gap: 24px; }
  .ph-meta b { font-size: 18px; }
}
</style>
