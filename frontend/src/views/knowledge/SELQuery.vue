<template>
  <div class="sel-query">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>SEL 事件码查询</span>
        </div>
      </template>
      <el-form :inline="true" :model="query" @submit.prevent="handleQuery">
        <el-form-item label="品牌">
          <el-select v-model="query.brand" placeholder="选择品牌" style="width: 140px">
            <el-option v-for="b in brands" :key="b" :label="b" :value="b" />
          </el-select>
        </el-form-item>
        <el-form-item label="事件码">
          <el-input v-model="query.event_code" placeholder="如 0x2001" clearable style="width: 140px" />
        </el-form-item>
        <el-form-item label="严重级别">
          <el-select v-model="query.severity" placeholder="全部" clearable style="width: 120px">
            <el-option label="Critical" value="critical" />
            <el-option label="Warning" value="warning" />
            <el-option label="Info" value="info" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleQuery" :loading="loading">查询</el-button>
        </el-form-item>
      </el-form>
      <el-table :data="results" stripe v-loading="loading" :empty-text="emptyText">
        <el-table-column prop="event_code" label="事件码" width="120" fixed />
        <el-table-column prop="sensor_type" label="传感器类型" width="140" />
        <el-table-column prop="severity" label="严重级别" width="110" align="center">
          <template #default="{ row }">
            <el-tag
              :type="severityTagType(row.severity)"
              :color="severityColor(row.severity)"
              :style="{ color: severityTextColor(row.severity), borderColor: severityColor(row.severity) }"
              size="small"
              effect="dark"
            >
              {{ severityLabel(row.severity) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="240" show-overflow-tooltip />
        <el-table-column prop="recommended_action" label="建议处理" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.recommended_action">{{ row.recommended_action }}</span>
            <span v-else class="text-muted">暂无建议</span>
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

const query = reactive({ brand: '', event_code: '', severity: '' })

const emptyText = computed(() => {
  if (!hasQueried.value) return '请选择品牌进行查询'
  return '未找到匹配的 SEL 事件码，请调整查询条件后重试'
})

const severityTagType = (s: string) => {
  if (s === 'critical') return 'danger'
  if (s === 'warning') return 'warning'
  return 'info'
}

const severityColor = (s: string) => {
  if (s === 'critical') return '#f56c6c'
  if (s === 'warning') return '#e6a23c'
  return '#409eff'
}

const severityTextColor = (s: string) => {
  return '#ffffff'
}

const severityLabel = (s: string) => {
  if (s === 'critical') return 'Critical'
  if (s === 'warning') return 'Warning'
  if (s === 'info') return 'Info'
  return s
}

const handleQuery = async () => {
  if (!query.brand) return
  loading.value = true
  hasQueried.value = true
  try {
    const { data } = await knowledgeApi.getSelCodes({
      brand: query.brand,
      event_code: query.event_code || undefined,
      severity: query.severity || undefined,
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
