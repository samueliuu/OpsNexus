<template>
  <div class="firmware-matrix">
    <el-card>
      <template #header>
        <div class="card-header"><span>固件兼容矩阵</span></div>
      </template>
      <el-form :inline="true" :model="query" @submit.prevent="handleQuery">
        <el-form-item label="品牌">
          <el-select v-model="query.brand" placeholder="选择品牌" style="width: 140px">
            <el-option v-for="b in brands" :key="b" :label="b" :value="b" />
          </el-select>
        </el-form-item>
        <el-form-item label="型号">
          <el-input v-model="query.model" placeholder="如 PowerEdge R750" clearable style="width: 180px" />
        </el-form-item>
        <el-form-item label="组件">
          <el-select v-model="query.component" placeholder="全部" clearable style="width: 120px">
            <el-option label="BIOS" value="BIOS" />
            <el-option label="BMC" value="BMC" />
            <el-option label="RAID" value="RAID" />
            <el-option label="NIC" value="NIC" />
            <el-option label="PSU" value="PSU" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleQuery" :loading="loading">查询</el-button>
        </el-form-item>
      </el-form>
      <el-table :data="results" stripe v-loading="loading" :empty-text="emptyText">
        <el-table-column prop="model" label="服务器型号" width="160" fixed />
        <el-table-column prop="component" label="组件" width="90" align="center" />
        <el-table-column prop="version" label="固件版本" width="130" />
        <el-table-column prop="criticality" label="重要性" width="120" align="center">
          <template #default="{ row }">
            <el-tag
              :type="criticalityTagType(row.criticality)"
              :color="criticalityColor(row.criticality)"
              :style="{ color: criticalityTextColor(row.criticality), borderColor: criticalityColor(row.criticality) }"
              size="small"
              effect="dark"
            >
              {{ criticalityLabel(row.criticality) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="release_date" label="发布日期" width="120">
          <template #default="{ row }">
            <span v-if="row.release_date">{{ formatDate(row.release_date) }}</span>
            <span v-else class="text-muted">--</span>
          </template>
        </el-table-column>
        <el-table-column prop="release_notes" label="发布说明" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.release_notes">{{ row.release_notes }}</span>
            <span v-else class="text-muted">暂无说明</span>
          </template>
        </el-table-column>
        <el-table-column label="下载" width="80" align="center">
          <template #default="{ row }">
            <el-link v-if="row.download_url" :href="row.download_url" target="_blank" type="primary" :underline="false">下载</el-link>
            <span v-else class="text-muted">--</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { knowledgeApi } from '@/api/knowledge'

const loading = ref(false)
const hasQueried = ref(false)
const results = ref<any[]>([])
const brands = ['Dell', 'HPE', 'Lenovo', 'Huawei', 'Inspur', 'H3C', 'Sugon', 'xFusion']

const query = reactive({ brand: '', model: '', component: '' })

const emptyText = computed(() => {
  if (!hasQueried.value) return '请选择品牌进行查询'
  return '未找到匹配的固件信息，请调整查询条件后重试'
})

const criticalityTagType = (c: string) => {
  if (c === 'critical') return 'danger'
  if (c === 'recommended') return 'warning'
  return 'info'
}

const criticalityColor = (c: string) => {
  if (c === 'critical') return '#f56c6c'
  if (c === 'recommended') return '#e6a23c'
  return '#909399'
}

const criticalityTextColor = (c: string) => {
  return '#ffffff'
}

const criticalityLabel = (c: string) => {
  if (c === 'critical') return 'Critical'
  if (c === 'recommended') return 'Recommended'
  if (c === 'optional') return 'Optional'
  return c
}

const formatDate = (d: string) => {
  if (!d) return ''
  return new Date(d).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

const handleQuery = async () => {
  if (!query.brand) return
  loading.value = true
  hasQueried.value = true
  try {
    const { data } = await knowledgeApi.getFirmwareMatrix({
      brand: query.brand,
      model: query.model || undefined,
      component: query.component || undefined,
    })
    results.value = data
  } catch {
    results.value = []
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.text-muted { color: #c0c4cc; font-style: italic; }
</style>
