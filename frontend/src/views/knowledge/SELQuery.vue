<template>
  <div class="sel-query">
    <Card>
      <template #header>
        <div class="card-header">
          <span>SEL 事件码查询</span>
        </div>
      </template>
      <template #content>
        <div class="form-inline" @submit.prevent="handleQuery">
          <div class="field">
            <label>品牌</label>
            <Select v-model="query.brand" :options="brandOptions" optionLabel="label" optionValue="value" placeholder="选择品牌" style="width: 140px" showClear />
          </div>
          <div class="field">
            <label>事件码</label>
            <InputText v-model="query.event_code" placeholder="如 0x2001" style="width: 140px" />
          </div>
          <div class="field">
            <label>严重级别</label>
            <Select v-model="query.severity" :options="severityOptions" optionLabel="label" optionValue="value" placeholder="全部" style="width: 120px" showClear />
          </div>
          <div class="field">
            <Button label="查询" :loading="loading" @click="handleQuery" />
          </div>
        </div>
        <DataTable :value="results" :loading="loading" stripedRows>
          <template #empty>
            <div class="empty-state">{{ emptyText }}</div>
          </template>
          <Column field="event_code" header="事件码" style="width: 120px" />
          <Column field="sensor_type" header="传感器类型" style="width: 140px" />
          <Column field="severity" header="严重级别" style="width: 110px; text-align: center">
            <template #body="{ data }">
              <Tag :severity="severityTagSeverity(data.severity)" style="font-size: 12px">
                {{ severityLabel(data.severity) }}
              </Tag>
            </template>
          </Column>
          <Column field="description" header="描述" style="min-width: 240px">
            <template #body="{ data }">
              <span v-if="data.description">{{ data.description }}</span>
              <span v-else class="text-muted">暂无</span>
            </template>
          </Column>
          <Column field="recommended_action" header="建议处理" style="min-width: 240px">
            <template #body="{ data }">
              <span v-if="data.recommended_action">{{ data.recommended_action }}</span>
              <span v-else class="text-muted">暂无建议</span>
            </template>
          </Column>
        </DataTable>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import Card from 'primevue/card'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import { knowledgeApi } from '@/api/knowledge'

const loading = ref(false)
const hasQueried = ref(false)
const results = ref<any[]>([])

const brandOptions = [
  { label: 'Dell', value: 'Dell' },
  { label: 'HPE', value: 'HPE' },
  { label: 'Lenovo', value: 'Lenovo' },
  { label: 'Huawei', value: 'Huawei' },
  { label: 'Inspur', value: 'Inspur' },
  { label: 'H3C', value: 'H3C' },
  { label: 'Sugon', value: 'Sugon' },
  { label: 'xFusion', value: 'xFusion' },
]

const severityOptions = [
  { label: 'Critical', value: 'critical' },
  { label: 'Warning', value: 'warning' },
  { label: 'Info', value: 'info' },
]

const query = reactive({ brand: '', event_code: '', severity: '' })

const emptyText = computed(() => {
  if (!hasQueried.value) return '请选择品牌进行查询'
  return '未找到匹配的 SEL 事件码，请调整查询条件后重试'
})

const severityTagSeverity = (s: string) => {
  if (s === 'critical') return 'danger'
  if (s === 'warning') return 'warning'
  return 'secondary'
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
.form-inline { display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-end; margin-bottom: 16px; }
.field { display: flex; flex-direction: column; gap: 4px; }
.field label { font-size: 13px; color: #606266; }
.empty-state { text-align: center; padding: 40px 0; color: #909399; }
</style>
