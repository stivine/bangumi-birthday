<script setup>
/**
 * SearchBar — 搜索/筛选栏组件
 *
 * Emits:
 *   search({ userid, date }): 触发搜索
 *   reset(): 重置到今日视图
 */

import { ref, computed } from 'vue'
import { useDatePicker } from '@/composables/useDatePicker'

const emit = defineEmits(['search', 'reset'])

const props = defineProps({
  loading: Boolean,
  canReset: Boolean,
})

const userid = ref('')
const { selectedMonth, selectedDay, daysInMonth, dateString, clear } = useDatePicker()

const canSearch = computed(() => {
  // 需要至少输入 userid，或者同时选了月份+日期
  return userid.value.trim() || dateString.value
})

function handleSearch() {
  if (!canSearch.value) return
  emit('search', {
    userid: userid.value.trim(),
    date: dateString.value,
  })
}

function handleReset() {
  userid.value = ''
  clear()
  emit('reset')
}

function handleKeydown(e) {
  if (e.key === 'Enter') handleSearch()
}
</script>

<template>
  <div class="search-bar" role="search">
    <input
      v-model="userid"
      type="text"
      placeholder="Bangumi 用户 ID（可选）"
      aria-label="Bangumi 用户 ID"
      @keydown="handleKeydown"
    />

    <select v-model="selectedMonth" aria-label="选择月份">
      <option value="">月份</option>
      <option v-for="m in 12" :key="m" :value="String(m).padStart(2, '0')">
        {{ m }} 月
      </option>
    </select>

    <select v-model="selectedDay" :disabled="!selectedMonth" aria-label="选择日期">
      <option value="">日期</option>
      <option v-for="d in daysInMonth" :key="d" :value="d">
        {{ parseInt(d, 10) }} 日
      </option>
    </select>

    <button
      :disabled="loading || !canSearch"
      class="btn btn-primary"
      @click="handleSearch"
    >
      {{ loading ? '查询中…' : '🔍 搜索' }}
    </button>

    <button
      :disabled="!canReset"
      class="btn btn-secondary"
      @click="handleReset"
    >
      🔄 重置
    </button>
  </div>
</template>

<style scoped>
.search-bar {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  align-items: center;
  gap: 10px;
  margin-bottom: 28px;
}

.search-bar input,
.search-bar select {
  padding: 8px 12px;
  min-width: 140px;
  border: 1px solid #d0d0d0;
  border-radius: 6px;
  font-size: 14px;
  background: #fff;
  color: #333;
  transition: border-color 0.15s;
}

.search-bar input:focus,
.search-bar select:focus {
  outline: none;
  border-color: #4a90e2;
  box-shadow: 0 0 0 3px rgba(74, 144, 226, 0.15);
}

.search-bar select:disabled {
  background: #f5f5f5;
  color: #aaa;
  cursor: not-allowed;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.15s, opacity 0.15s;
  white-space: nowrap;
}

.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.btn-primary {
  background: #4a90e2;
  color: #fff;
}

.btn-primary:not(:disabled):hover {
  background: #357abd;
}

.btn-secondary {
  background: #f0f0f0;
  color: #555;
}

.btn-secondary:not(:disabled):hover {
  background: #e0e0e0;
}

@media (max-width: 480px) {
  .search-bar input,
  .search-bar select,
  .btn {
    flex: 1 1 calc(50% - 10px);
    min-width: 0;
  }
}
</style>
