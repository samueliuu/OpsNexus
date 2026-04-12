<template>
  <div class="knowledge-favorites">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>我的收藏</span>
          <el-tag v-if="favorites.length" type="info" size="small">{{ favorites.length }} 条</el-tag>
        </div>
      </template>
      <div v-loading="loading">
        <div v-if="favorites.length" class="fav-grid">
          <div v-for="fav in favorites" :key="fav.id" class="fav-card">
            <div class="fav-card-header">
              <span class="fav-title">{{ fav.title }}</span>
              <el-button size="small" text type="danger" @click="removeFav(fav.id)" title="取消收藏">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
            <div class="fav-content">{{ fav.content }}</div>
            <div class="fav-footer">
              <div class="fav-tags">
                <el-tag
                  v-if="fav.brand"
                  size="small"
                  :color="brandColor(fav.brand)"
                  :style="{ color: '#ffffff', borderColor: brandColor(fav.brand) }"
                  effect="dark"
                >
                  {{ fav.brand }}
                </el-tag>
                <el-tag
                  size="small"
                  :type="sourceTypeTag(fav.source_type)"
                  effect="plain"
                >
                  {{ sourceTypeLabel(fav.source_type) }}
                </el-tag>
              </div>
              <span class="fav-time">{{ formatTime(fav.created_at) }}</span>
            </div>
          </div>
        </div>
        <el-empty v-if="!favorites.length && !loading" description="暂无收藏" :image-size="120">
          <template #description>
            <p class="empty-hint">在知识问答中收藏有价值的内容</p>
          </template>
        </el-empty>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { knowledgeApi } from '@/api/knowledge'
import { ElMessage } from 'element-plus'
import { Delete } from '@element-plus/icons-vue'

const loading = ref(false)
const favorites = ref<any[]>([])

const brandColorMap: Record<string, string> = {
  Dell: '#0076CE',
  HPE: '#01A982',
  Lenovo: '#E2231A',
  Huawei: '#CF0A2C',
  Inspur: '#005BAC',
  H3C: '#0066FF',
  Sugon: '#E60012',
  xFusion: '#FF6600',
}

const brandColor = (brand: string) => {
  return brandColorMap[brand] || '#909399'
}

const sourceTypeTag = (type: string) => {
  if (type === 'qa') return 'primary'
  if (type === 'sel') return 'danger'
  if (type === 'firmware') return 'warning'
  return 'info'
}

const sourceTypeLabel = (type: string) => {
  if (type === 'qa') return '问答'
  if (type === 'sel') return 'SEL码'
  if (type === 'firmware') return '固件'
  return type
}

const formatTime = (t: string) => {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN')
}

const loadFavorites = async () => {
  loading.value = true
  try {
    const { data } = await knowledgeApi.listFavorites({ limit: 50 })
    favorites.value = data.items || []
  } catch {} finally {
    loading.value = false
  }
}

const removeFav = async (id: string) => {
  try {
    await knowledgeApi.deleteFavorite(id)
    ElMessage.success('已取消收藏')
    loadFavorites()
  } catch {}
}

onMounted(loadFavorites)
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }

.fav-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.fav-card {
  padding: 16px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  transition: box-shadow 0.2s, border-color 0.2s;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.fav-card:hover {
  border-color: #d0d3d9;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.fav-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}
.fav-title {
  font-weight: 500;
  font-size: 15px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.fav-content {
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

.fav-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: auto;
}
.fav-tags { display: flex; gap: 6px; align-items: center; }
.fav-time { font-size: 12px; color: #909399; white-space: nowrap; }

.empty-hint { color: #909399; font-size: 13px; margin: 0; }
</style>
