/**
 * useDatePicker — 日期选择 composable
 *
 * 维护月/日联动逻辑，与 UI 无关。
 */

import { ref, watch, computed } from 'vue'

/** 每个月的天数（非闰年/闰年最大值） */
const DAYS_IN_MONTH = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

function getTodayMMDD() {
  const now = new Date()
  const mm = String(now.getMonth() + 1).padStart(2, '0')
  const dd = String(now.getDate()).padStart(2, '0')
  return `${mm}-${dd}`
}

export function useDatePicker(initialDate = '') {
  const [initMM, initDD] = initialDate ? initialDate.split('-') : ['', '']
  const selectedMonth = ref(initMM || '')
  const selectedDay = ref(initDD || '')

  const daysInMonth = computed(() => {
    if (!selectedMonth.value) return []
    const max = DAYS_IN_MONTH[parseInt(selectedMonth.value, 10) - 1] ?? 31
    return Array.from({ length: max }, (_, i) => String(i + 1).padStart(2, '0'))
  })

  watch(selectedMonth, () => {
    if (!daysInMonth.value.includes(selectedDay.value)) {
      selectedDay.value = ''
    }
  })

  /** 格式化后的 MM-DD，未选完则返回 null */
  const dateString = computed(() => {
    if (!selectedMonth.value || !selectedDay.value) return null
    return `${selectedMonth.value}-${selectedDay.value}`
  })

  function resetToToday() {
    const today = getTodayMMDD()
    const [mm, dd] = today.split('-')
    selectedMonth.value = mm
    selectedDay.value = dd
  }

  function clear() {
    selectedMonth.value = ''
    selectedDay.value = ''
  }

  return {
    selectedMonth,
    selectedDay,
    daysInMonth,
    dateString,
    resetToToday,
    clear,
  }
}
