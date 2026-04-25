<template>
  <div class="firmware-matrix">
    <Card>
      <template #header>
        <div class="card-header"><span>固件兼容矩阵</span></div>
      </template>
      <template #content>
        <div class="form-inline" @submit.prevent="handleQuery">
          <div class="field">
            <label>品牌</label>
            <Select v-model="query.brand" :options="brandOptions" optionLabel="label" optionValue="value" placeholder="选择品牌" style="width: 140px" showClear />
          </div>
          <div class="field">
            <label>型号</label>
            <InputText v-model="query.model" placeholder="如 PowerEdge R750" style="width: 180px" />
          </div>
          <div class="field">
            <label>组件</label>
            <Select v-model="query.component" :options="componentOptions" optionLabel="label" optionValue="value" placeholder="全部" style="width: 120px" showClear />
          </div>
          <div class="field">
            <Button label="查询" :loading="loading" @click="handleQuery" />
          </div>
        </div>
        <DataTable :value="results" :loading="loading" stripedRows>
          <template #empty>
            <div class="empty-state">{{ emptyText }}</div>
          </template>
          <Column field="model" header="服务器型号" style="width: 160px" />
          <Column field="component" header="组件" style="width: 90px; text-align: center" />
          <Column field="version" header="固件版本" style="width: 130px" />
          <Column field="criticality" header="重要性" style="width: 120px; text-align: center">
            <template #body="{ data }">
              <Tag :severity="criticalitySeverity(data.criticality)" style="font-size: 12px">
                {{ criticalityLabel(data.criticality) }}
              </Tag>
            </template>
          </Column>
          <Column field="release_date" header="发布日期" style="width: 120px">
            <template #body="{ data }">
              <span v-if="data.release_date">{{ formatDate(data.release_date) }}</span>
              <span v-else class="text-muted">--</span>
            </template>
          </Column>
          <Column field="release_notes" header="发布说明" style="min-width: 220px">
            <template #body="{ data }">
              <span v-if="data.release_notes">{{ data.release_notes }}</span>
              <span v-else class="text-muted">暂无说明</span>
            </template>
          </Column>
          <Column header="下载" style="width: 80px; text-align: center">
            <template #body="{ data }">
              <Button v-if="data.download_url" link label="下载" @click="openUrl(data.download_url)" />
              <span v-else class="text-muted">--</span>
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

const componentOptions = [
  { label: 'BIOS', value: 'BIOS' },
  { label: 'BMC', value: 'BMC' },
  { label: 'RAID', value: 'RAID' },
  { label: 'NIC', value: 'NIC' },
  { label: 'PSU', value: 'PSU' },
]

const query = reactive({ brand: '', model: '', component: '' })

const emptyText = computed(() => {
  if (!hasQueried.value) return '请选择品牌进行查询'
  return '未找到匹配的固件信息，请调整查询条件后重试'
})

const criticalitySeverity = (c: string) => {
  if (c === 'critical') return 'danger'
  if (c === 'recommended') return 'warning'
  return 'secondary'
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

const openUrl = (url: string) => {
  window.open(url, '_blank')
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
.form-inline { display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-end; margin-bottom: 16px; }
.field { display: flex; flex-direction: column; gap: 4px; }
.field label { font-size: 13px; color: #606266; }
.empty-state { text-align: center; padding: 40px 0; color: #909399; }
</style>
