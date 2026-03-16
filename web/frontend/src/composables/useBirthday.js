/**
 * useBirthday — 生日查询 composable
 *
 * 封装所有与 API 相关的状态和操作，使组件保持纯 UI。
 */

import { ref, computed } from 'vue'
import axios from 'axios'

/** @typedef {{ character_id: number, name: string, chinese_name: string, birthday: string|null }} Character */

// 节日映射（可扩展）
const HOLIDAY_MAP = {
  '01-01': '元旦',
  '02-14': '情人节',
  '03-08': '妇女节',
  '05-01': '劳动节',
  '05-20': '网络情人节',
  '06-01': '儿童节',
  '08-22': '七夕节',
  '10-01': '国庆节',
  '12-25': '圣诞节',
}

function getTodayMMDD() {
  const now = new Date()
  const mm = String(now.getMonth() + 1).padStart(2, '0')
  const dd = String(now.getDate()).padStart(2, '0')
  return `${mm}-${dd}`
}

export function useBirthday() {
  /** @type {import('vue').Ref<Character[]>} */
  const characters = ref([])
  const loading = ref(false)
  const error = ref(/** @type {string|null} */ (null))

  // 当前展示的日期（MM-DD）
  const currentDate = ref(getTodayMMDD())

  const titleText = computed(() => {
    const [mm, dd] = currentDate.value.split('-')
    const label = `${parseInt(mm)}月${parseInt(dd)}日`
    const holiday = HOLIDAY_MAP[currentDate.value]
    const count = characters.value.length

    let base = ''
    if (count === 0) base = `${label}今天没有角色过生日 😢`
    else if (count === 1) base = `${label}有 1 位角色过生日！🎉`
    else base = `${label}有 ${count} 位角色过生日！🎂`

    return holiday ? `${base}（${holiday}快乐！）` : base
  })

  /**
   * 获取全站某日期生日角色
   * @param {string} [dateStr] MM-DD，默认今日
   */
  async function fetchByDate(dateStr = getTodayMMDD()) {
    loading.value = true
    error.value = null
    currentDate.value = dateStr

    try {
      const url = dateStr === getTodayMMDD() ? '/api/today' : `/api/date/${dateStr}`
      const resp = await axios.get(url)
      characters.value = Array.isArray(resp.data) ? resp.data : []
    } catch (err) {
      error.value = '无法获取角色列表，请检查网络或后端服务'
      console.error(err)
    } finally {
      loading.value = false
    }
  }

  /**
   * 按用户收藏过滤查询
   * @param {string} userid Bangumi 用户名或 ID
   * @param {string} dateStr MM-DD
   */
  async function fetchByUser(userid, dateStr) {
    if (!userid || !dateStr) return
    loading.value = true
    error.value = null
    currentDate.value = dateStr

    try {
      const resp = await axios.get('/api/hbd2waifu', {
        params: { userid, date: dateStr },
      })
      const raw = Array.isArray(resp.data) ? resp.data : []
      // 去重
      const seen = new Set()
      characters.value = raw.filter((c) => {
        if (seen.has(c.character_id)) return false
        seen.add(c.character_id)
        return true
      })
    } catch (err) {
      if (err.response?.status === 404) {
        error.value = `用户 "${userid}" 不存在，请检查 Bangumi ID`
      } else {
        error.value = '查询失败，请检查网络或稍后重试'
      }
      console.error(err)
    } finally {
      loading.value = false
    }
  }

  /**
   * 随机跳转一个角色页面
   */
  function openRandomCharacter() {
    if (characters.value.length === 0) return
    const char = characters.value[Math.floor(Math.random() * characters.value.length)]
    window.open(`https://bgm.tv/character/${char.character_id}`, '_blank')
  }

  return {
    characters,
    loading,
    error,
    currentDate,
    titleText,
    fetchByDate,
    fetchByUser,
    openRandomCharacter,
  }
}
