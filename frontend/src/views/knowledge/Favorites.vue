<template>
  <div class="knowledge-favorites">
    <Card>
      <template #header>
        <div class="card-header">
          <span>我的收藏</span>
          <Tag v-if="favorites.length" severity="secondary" style="font-size: 12px">{{ favorites.length }} 条</Tag>
        </div>
      </template>
      <template #content>
        <div class="loading-container" style="position: relative; min-height: 200px;">
          <div v-if="loading" class="loading-overlay">
            <ProgressSpinner style="width: 40px; height: 40px" />
          </div>
          <div v-if="favorites.length" class="fav-grid">
            <div v-for="fav in favorites" :key="fav.id" class="fav-card">
              <div class="fav-card-header">
                <span class="fav-title">{{ fav.title }}</span>
                <Button size="small" link severity="danger" @click="removeFav(fav.id)" title="取消收藏">
                  <i class="pi pi-trash"></i>
                </Button>
              </div>
              <div class="fav-content">{{ fav.content }}</div>
              <div class="fav-footer">
                <div class="fav-tags">
                  <Tag
                    v-if="fav.brand"
                    :style="{ background: brandColor(fav.brand), color: '#ffffff', borderColor: brandColor(fav.brand), fontSize: '12px' }"
                  >
                    {{ fav.brand }}
                  </Tag>
                  <Tag
                    :severity="sourceTypeSeverity(fav.source_type)"
                    style="font-size: 12px"
                  >
                    {{ sourceTypeLabel(fav.source_type) }}
                  </Tag>
                </div>
                <span class="fav-time">{{ formatTime(fav.created_at) }}</span>
              </div>
            </div>
          </div>
          <div v-if="!favorites.length && !loading" class="empty-state">
            <i class="pi pi-inbox" style="font-size: 48px; color: #c0c4cc"></i>
            <p>暂无收藏</p>
            <p class="empty-hint">在知识问答中收藏有价值的内容</p>
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import Card from 'primevue/card'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import { knowledgeApi } from '@/api/knowledge'

const toast = useToast()
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

const sourceTypeSeverity = (type: string) => {
  if (type === 'qa') return undefined
  if (type === 'sel') return 'danger'
  if (type === 'firmware') return 'warning'
  return 'secondary'
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
  } catch { /* ignore */ } finally {
    loading.value = false
  }
}

const removeFav = async (id: string) => {
  try {
    await knowledgeApi.deleteFavorite(id)
    toast.add({ severity: 'success', summary: '成功', detail: '已取消收藏', life: 3000 })
    loadFavorites()
  } catch { /* ignore */ }
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

.empty-state {
  text-align: center;
  padding: 40px 0;
  color: #909399;
}
.empty-state p {
  margin: 8px 0 0;
}
.empty-hint { color: #909399; font-size: 13px; margin: 0; }

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.7);
  z-index: 1;
}
</style>
