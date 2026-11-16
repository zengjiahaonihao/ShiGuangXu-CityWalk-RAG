<script setup>
/** 骑楼街景主视觉：纯 SVG 手绘，暖光晨雾 + 连续拱券廊道 + 颗粒质感。
 *  若 public/poster.jpg 存在，父组件会改用实景照片，本组件作为兜底底图。 */
const rnd = (i, s = 1) => {
  const v = Math.sin(i * 12.9898 * s) * 43758.5453
  return (v - Math.floor(v))
}

const COUNT = 11
const buildings = Array.from({ length: COUNT }, (_, i) => {
  const w = 118 + rnd(i) * 62
  const h = 250 + rnd(i, 2.3) * 190
  const rows = 2 + Math.floor(rnd(i, 5.1) * 2)
  const cols = 2 + Math.floor(rnd(i, 7.7) * 2)
  return { i, w, h, rows, cols, tone: rnd(i, 3.3) }
})

const GAP = 4
const BASE_Y = 720
let cursor = -60
const placed = buildings.map((b) => {
  const x = cursor
  cursor += b.w + GAP
  return { ...b, x }
})
const totalWidth = cursor
</script>

<template>
  <svg class="scene" viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <defs>
      <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#c9a679" />
        <stop offset="38%" stop-color="#e2c795" />
        <stop offset="72%" stop-color="#f2ddb6" />
        <stop offset="100%" stop-color="#f7ecd4" />
      </linearGradient>
      <radialGradient id="sunGlow" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stop-color="#fff6de" stop-opacity="0.95" />
        <stop offset="35%" stop-color="#f6d79a" stop-opacity="0.55" />
        <stop offset="100%" stop-color="#f0c46a" stop-opacity="0" />
      </radialGradient>
      <linearGradient id="mist" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#f7ecd4" stop-opacity="0" />
        <stop offset="100%" stop-color="#f9f0dc" stop-opacity="0.85" />
      </linearGradient>
      <linearGradient id="ground" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#8d7150" />
        <stop offset="100%" stop-color="#5c4630" />
      </linearGradient>
      <radialGradient id="vig" cx="50%" cy="45%" r="72%">
        <stop offset="55%" stop-color="#000" stop-opacity="0" />
        <stop offset="100%" stop-color="#2a1d10" stop-opacity="0.55" />
      </radialGradient>
      <filter id="grain">
        <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="3" stitchTiles="stitch" />
        <feColorMatrix type="saturate" values="0" />
      </filter>
    </defs>

    <!-- 天空 -->
    <rect width="1600" height="900" fill="url(#sky)" />

    <!-- 晨阳 -->
    <circle cx="1180" cy="330" r="300" fill="url(#sunGlow)" />
    <circle cx="1180" cy="330" r="74" fill="#fff3d8" opacity="0.9" />

    <!-- 远山 -->
    <path d="M0 620 L210 520 L360 585 L520 470 L700 575 L860 505 L1060 590 L1250 520 L1420 585 L1600 540 L1600 720 L0 720 Z"
      fill="#c3a67f" opacity="0.5" />
    <path d="M0 665 L180 605 L400 660 L640 600 L900 665 L1150 615 L1400 668 L1600 630 L1600 720 L0 720 Z"
      fill="#b08f6c" opacity="0.55" />

    <!-- 晨雾 -->
    <rect x="0" y="560" width="1600" height="180" fill="url(#mist)" />

    <!-- 骑楼群 -->
    <g>
      <g v-for="b in placed" :key="b.i">
        <!-- 楼体 -->
        <rect :x="b.x" :y="BASE_Y - b.h" :width="b.w" :height="b.h"
          :fill="b.tone > 0.5 ? '#b4946f' : '#a98864'" />
        <!-- 侧影 -->
        <rect :x="b.x + b.w - 12" :y="BASE_Y - b.h" width="12" :height="b.h" fill="#8f7050" opacity="0.5" />
        <!-- 女儿墙 -->
        <rect :x="b.x - 6" :y="BASE_Y - b.h - 22" :width="b.w + 12" height="22"
          :fill="b.tone > 0.5 ? '#c2a37c' : '#b08d68'" />
        <rect :x="b.x - 6" :y="BASE_Y - b.h - 22" :width="b.w + 12" height="3" fill="#7d6247" opacity="0.5" />
        <!-- 窗 -->
        <g v-for="r in b.rows" :key="'r' + r">
          <rect v-for="c in b.cols" :key="'c' + c"
            :x="b.x + 16 + (c - 1) * ((b.w - 32) / b.cols)"
            :y="BASE_Y - b.h + 42 + (r - 1) * 62"
            :width="Math.max(18, (b.w - 32) / b.cols - 16)" height="34"
            fill="#4d3a26" opacity="0.82" />
        </g>
        <!-- 拱券廊洞 -->
        <path
          :d="`M ${b.x + 14} ${BASE_Y} L ${b.x + 14} ${BASE_Y - 96} Q ${b.x + b.w / 2} ${BASE_Y - 152} ${b.x + b.w - 14} ${BASE_Y - 96} L ${b.x + b.w - 14} ${BASE_Y} Z`"
          fill="#2e2116" opacity="0.92" />
        <!-- 廊柱 -->
        <rect :x="b.x" :y="BASE_Y - 150" width="14" height="150" fill="#8a6b4c" />
        <rect :x="b.x + b.w - 14" :y="BASE_Y - 150" width="14" height="150" fill="#7a5e42" />
        <!-- 檐下阴影 -->
        <rect :x="b.x" :y="BASE_Y - 150" :width="b.w" height="10" fill="#2b1f14" opacity="0.6" />
      </g>
    </g>

    <!-- 街面 -->
    <rect x="0" y="720" width="1600" height="180" fill="url(#ground)" />
    <rect x="0" y="720" width="1600" height="3" fill="#3a2b1c" opacity="0.7" />
    <!-- 湿地面反光 -->
    <g opacity="0.32">
      <rect v-for="(b, i) in placed" :key="'f' + i"
        :x="b.x + 20" y="726" :width="b.w - 40" :height="120" fill="#f2ddb6" opacity="0.28" />
    </g>

    <!-- 电线与飞鸟 -->
    <path d="M0 268 Q 400 322 800 288 T 1600 300" stroke="#3b2c1d" stroke-width="1.4" fill="none" opacity="0.45" />
    <path d="M0 300 Q 420 350 860 316 T 1600 330" stroke="#3b2c1d" stroke-width="1.1" fill="none" opacity="0.3" />
    <g stroke="#3b2c1d" stroke-width="2" fill="none" opacity="0.5" stroke-linecap="round">
      <path d="M300 210 q10 -9 20 0 q10 -9 20 0" />
      <path d="M368 176 q8 -7 16 0 q8 -7 16 0" />
      <path d="M262 158 q7 -6 14 0 q7 -6 14 0" />
    </g>

    <!-- 暗角 + 颗粒 -->
    <rect width="1600" height="900" fill="url(#vig)" />
    <rect width="1600" height="900" filter="url(#grain)" opacity="0.14" style="mix-blend-mode: multiply" />
  </svg>
</template>

<style scoped>
.scene {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
}

/* 兜底：保证 totalWidth 参与计算不被摇树优化 */
</style>
