<script setup>
/**
 * CharacterCard — 单个角色卡片组件
 *
 * Props:
 *   character: { character_id, name, chinese_name, birthday }
 */

const props = defineProps({
  character: {
    type: Object,
    required: true,
  },
})

const fallbackImg = 'https://dummyimage.com/120x160/eeeeee/999999&text=No+Image'

function onImgError(e) {
  e.target.src = fallbackImg
}
</script>

<template>
  <a
    :href="`https://bgm.tv/character/${character.character_id}`"
    target="_blank"
    rel="noopener noreferrer"
    class="character-card"
    :aria-label="`查看 ${character.chinese_name || character.name} 的 Bangumi 页面`"
  >
    <img
      :src="`https://api.bgm.tv/v0/characters/${character.character_id}/image?type=medium`"
      :alt="character.chinese_name || character.name"
      loading="lazy"
      @error="onImgError"
    />
    <div class="character-info">
      <div v-if="character.chinese_name?.trim()" class="chinese-name">
        {{ character.chinese_name.trim() }}
      </div>
      <div class="original-name">{{ character.name }}</div>
    </div>
  </a>
</template>

<style scoped>
.character-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 140px;
  min-height: 200px;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  text-decoration: none;
  color: inherit;
  padding: 12px 8px;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
  cursor: pointer;
}

.character-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.15);
}

.character-card img {
  width: 100%;
  max-height: 160px;
  object-fit: contain;
  border-radius: 6px;
  margin-bottom: 10px;
  background: #f5f5f5;
}

.character-info {
  width: 100%;
  text-align: center;
}

.chinese-name {
  font-weight: 600;
  font-size: 0.95rem;
  color: #222;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 2px;
}

.original-name {
  font-size: 0.82rem;
  color: #777;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

@media (max-width: 480px) {
  .character-card {
    width: calc(50% - 10px);
    min-height: 160px;
  }
}
</style>
