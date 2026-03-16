<script setup>
/**
 * HomeView — 主页视图
 *
 * 负责将各 composable 和组件组合在一起，处理 UI 交互。
 */

import { ref, onMounted } from 'vue'
import CharacterCard from '@/components/CharacterCard.vue'
import SearchBar from '@/components/SearchBar.vue'
import { useBirthday } from '@/composables/useBirthday'

const {
  characters,
  loading,
  error,
  titleText,
  fetchByDate,
  fetchByUser,
  openRandomCharacter,
} = useBirthday()

const canReset = ref(false)

onMounted(() => {
  fetchByDate()
})

function handleSearch({ userid, date }) {
  if (userid && date) {
    // 用户 + 日期：查用户收藏
    fetchByUser(userid, date)
    canReset.value = true
  } else if (date) {
    // 仅日期：查全站
    fetchByDate(date)
    canReset.value = true
  } else if (userid) {
    // 仅用户 ID，使用今天日期
    const today = new Date()
    const mm = String(today.getMonth() + 1).padStart(2, '0')
    const dd = String(today.getDate()).padStart(2, '0')
    fetchByUser(userid, `${mm}-${dd}`)
    canReset.value = true
  }
}

function handleReset() {
  canReset.value = false
  fetchByDate()
}
</script>

<template>
  <div class="home">
    <!-- 标题 -->
    <header class="page-header">
      <h1>{{ titleText }}</h1>
    </header>

    <!-- 使用说明 -->
    <section class="guide" aria-label="使用说明">
      <details>
        <summary>ℹ️ 使用说明</summary>
        <ul>
          <li>
            <strong>Bangumi 用户 ID</strong> 是你在
            <a href="https://bgm.tv" target="_blank" rel="noopener">Bangumi.tv</a>
            个人主页 URL 中的数字，例如
            <code>https://bgm.tv/user/12345</code> 中的 <code>12345</code>。
          </li>
          <li>
            输入 ID 并选择日期，可查看你收藏作品中在指定日期生日的角色。
          </li>
          <li>
            若不输入 ID，直接选日期，显示全站该日生日角色（默认今日）。
          </li>
        </ul>
      </details>
    </section>

    <!-- 搜索栏 -->
    <SearchBar
      :loading="loading"
      :can-reset="canReset"
      @search="handleSearch"
      @reset="handleReset"
    />

    <!-- 操作按钮组 -->
    <div class="action-bar" v-if="characters.length > 0">
      <button class="btn-random" @click="openRandomCharacter">
        🎲 随机角色
      </button>
      <span class="char-count">共 {{ characters.length }} 位</span>
    </div>

    <!-- 状态显示 -->
    <div v-if="loading" class="status-msg loading" role="status" aria-live="polite">
      <span class="spinner" aria-hidden="true">⏳</span> 加载中…
    </div>
    <div v-else-if="error" class="status-msg error" role="alert">
      ⚠️ {{ error }}
    </div>
    <div v-else-if="characters.length === 0" class="status-msg empty">
      😢 没有找到角色数据
    </div>

    <!-- 角色列表 -->
    <Transition name="fade">
      <div v-if="!loading && !error && characters.length > 0" class="character-list">
        <TransitionGroup name="list" tag="div" class="cards-grid">
          <CharacterCard
            v-for="char in characters"
            :key="char.character_id"
            :character="char"
          />
        </TransitionGroup>
      </div>
    </Transition>

    <!-- 页脚 -->
    <footer class="site-footer">
      <p>© {{ new Date().getFullYear() }} Stivine · 数据来源 <a href="https://bgm.tv" target="_blank" rel="noopener">Bangumi</a></p>
      <p>ICP 备案：冀ICP备2025121063号-1</p>
    </footer>
  </div>

  <!-- 右下角博客链接 -->
  <a
    href="https://stivine.github.io"
    target="_blank"
    rel="noopener noreferrer"
    class="blog-link"
    title="作者博客"
    aria-label="访问作者博客"
  >
    <img src="https://github.githubassets.com/favicons/favicon.svg" alt="" aria-hidden="true" />
    <span>Stivine's Blog</span>
  </a>
</template>

<style scoped>
.home {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans SC', sans-serif;
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 20px 60px;
  text-align: center;
  color: #333;
}

/* 标题 */
.page-header h1 {
  font-size: clamp(1.2rem, 3vw, 1.8rem);
  font-weight: 700;
  margin-bottom: 20px;
  color: #222;
  line-height: 1.4;
}

/* 使用说明 */
.guide {
  max-width: 680px;
  margin: 0 auto 24px;
  text-align: left;
}

.guide details {
  background: #f9fafb;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 14px 18px;
  font-size: 0.92rem;
  color: #555;
}

.guide summary {
  cursor: pointer;
  font-weight: 600;
  user-select: none;
  outline: none;
  color: #444;
}

.guide ul {
  margin: 12px 0 0;
  padding-left: 22px;
  line-height: 1.7;
}

.guide code {
  background: #eef2f7;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 0.88em;
  color: #d14;
}

.guide a {
  color: #4a90e2;
}

/* 操作按钮组 */
.action-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 20px;
}

.btn-random {
  padding: 7px 14px;
  border: none;
  background: #f0f0f0;
  color: #555;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.15s;
}

.btn-random:hover {
  background: #e0e0e0;
}

.char-count {
  font-size: 13px;
  color: #888;
}

/* 状态信息 */
.status-msg {
  margin: 48px auto;
  font-size: 1.1rem;
  max-width: 400px;
}

.loading { color: #4a90e2; }
.error   { color: #e05c5c; }
.empty   { color: #888; }

/* 角色列表 */
.cards-grid {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 16px;
  padding: 4px;
}

/* 动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.list-enter-active {
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}
.list-leave-active {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  position: absolute;
}
.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: scale(0.88);
}

/* 页脚 */
.site-footer {
  margin-top: 60px;
  padding-top: 20px;
  border-top: 1px solid #eee;
  font-size: 12px;
  color: #aaa;
  line-height: 1.8;
}

.site-footer a {
  color: #aaa;
  text-decoration: underline;
}

/* 博客链接（固定右下角） */
.blog-link {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 100;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(6px);
  border: 1px solid #e0e0e0;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
  color: #666;
  text-decoration: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: color 0.15s, box-shadow 0.15s;
}

.blog-link:hover {
  color: #4a90e2;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.blog-link img {
  width: 16px;
  height: 16px;
}

/* 移动端 */
@media (max-width: 480px) {
  .home {
    padding: 16px 12px 48px;
  }

  .cards-grid {
    gap: 10px;
  }

  .blog-link span {
    display: none;
  }
}
</style>
