<template>
  <div>
    <Card>
      <template #content>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
          <h3 style="margin:0">告警规则</h3>
          <Button label="新增规则" @click="showDialog()" />
        </div>
        <DataTable :value="tableData" stripedRows :loading="loading">
          <Column field="name" header="规则名称" style="min-width:140px" />
          <Column field="metric_name" header="指标" style="width:160px" />
          <Column header="条件" style="width:180px">
            <template #body="{ data }">{{ data.metric_name }} {{ condMap[data.condition] || data.condition }} {{ data.threshold }} {{ data.duration > 0 ? `(持续${data.duration}s)` : '' }}</template>
          </Column>
          <Column header="严重级别" style="width:90px">
            <template #body="{ data }">
              <Tag :severity="sevSeverity(data.severity)">{{ data.severity }}</Tag>
            </template>
          </Column>
          <Column header="状态" style="width:80px">
            <template #body="{ data }">
              <InputSwitch v-model="data.is_enabled" @change="toggleRule(data)" />
            </template>
          </Column>
          <Column header="操作" style="width:150px" frozen alignFrozen="right">
            <template #body="{ data }">
              <Button label="编辑" link size="small" @click="showDialog(data)" />
              <Button label="删除" link severity="danger" size="small" @click="confirmDelete(data.id)" />
            </template>
          </Column>
        </DataTable>
      </template>
    </Card>
    <Dialog v-model:visible="dialogVisible" :header="editingId ? '编辑规则' : '新增规则'" :style="{ width: '550px' }" :modal="true">
      <div class="form-grid">
        <div class="field">
          <label>规则名称</label>
          <InputText v-model="form.name" class="w-full" :class="{ 'p-invalid': errors.name }" />
          <small v-if="errors.name" class="p-error">{{ errors.name }}</small>
        </div>
        <div class="field">
          <label>指标</label>
          <InputText v-model="form.metric_name" placeholder="如 cpu_temperature_celsius" class="w-full" :class="{ 'p-invalid': errors.metric_name }" />
          <small v-if="errors.metric_name" class="p-error">{{ errors.metric_name }}</small>
        </div>
        <div class="condition-row">
          <div class="field">
            <label>条件</label>
            <Select v-model="form.condition" :options="condOptions" optionLabel="label" optionValue="value" class="w-full" />
          </div>
          <div class="field">
            <label>阈值</label>
            <InputNumber v-model="form.threshold" class="w-full" />
          </div>
          <div class="field">
            <label>持续(s)</label>
            <InputNumber v-model="form.duration" :min="0" class="w-full" />
          </div>
        </div>
        <div class="field">
          <label>严重级别</label>
          <Select v-model="form.severity" :options="severityOptions" optionLabel="label" optionValue="value" class="w-full" />
        </div>
      </div>
      <template #footer>
        <Button label="取消" severity="secondary" @click="dialogVisible = false" />
        <Button label="确定" :loading="submitting" @click="handleSubmit" />
      </template>
    </Dialog>
    <ConfirmDialog />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import InputSwitch from 'primevue/inputswitch'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import ConfirmDialog from 'primevue/confirmdialog'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { monitorApi } from '@/api/monitor'

const toast = useToast()
const confirm = useConfirm()

const condMap: Record<string, string> = { gt: '>', lt: '<', eq: '=', ne: '≠', ge: '≥', le: '≤' }
const condOptions = Object.entries(condMap).map(([value, label]) => ({ label, value }))
const severityOptions = [
  { label: '严重', value: 'critical' },
  { label: '警告', value: 'warning' },
  { label: '信息', value: 'info' },
]

const loading = ref(false)
const tableData = ref<any[]>([])
const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref('')
const form = ref<any>({ name: '', metric_name: '', condition: 'gt', threshold: 0, duration: 60, severity: 'warning', is_enabled: true })
const errors = ref<Record<string, string>>({})

onMounted(() => loadData())

async function loadData() {
  loading.value = true
  try {
    const { data } = await monitorApi.alertRules.list({ limit: 200 })
    tableData.value = data.items || []
  } catch {
    toast.add({ severity: 'error', summary: '错误', detail: '加载失败', life: 3000 })
  } finally {
    loading.value = false
  }
}

function sevSeverity(s: string) {
  return { critical: 'danger', warning: 'warning', info: 'secondary' }[s] || 'secondary'
}

function showDialog(row?: any) {
  editingId.value = row?.id || ''
  form.value = row
    ? { name: row.name, metric_name: row.metric_name, condition: row.condition, threshold: row.threshold, duration: row.duration, severity: row.severity, is_enabled: row.is_enabled }
    : { name: '', metric_name: '', condition: 'gt', threshold: 0, duration: 60, severity: 'warning', is_enabled: true }
  errors.value = {}
  dialogVisible.value = true
}

function validateForm(): boolean {
  errors.value = {}
  if (!form.value.name) errors.value.name = '请输入'
  if (!form.value.metric_name) errors.value.metric_name = '请输入'
  return Object.keys(errors.value).length === 0
}

async function handleSubmit() {
  if (!validateForm()) return
  submitting.value = true
  try {
    if (editingId.value) {
      await monitorApi.alertRules.update(editingId.value, form.value)
      toast.add({ severity: 'success', summary: '成功', detail: '更新成功', life: 3000 })
    } else {
      await monitorApi.alertRules.create(form.value)
      toast.add({ severity: 'success', summary: '成功', detail: '创建成功', life: 3000 })
    }
    dialogVisible.value = false
    loadData()
  } catch {
    toast.add({ severity: 'error', summary: '错误', detail: '操作失败', life: 3000 })
  } finally {
    submitting.value = false
  }
}

async function toggleRule(row: any) {
  try {
    await monitorApi.alertRules.update(row.id, { is_enabled: row.is_enabled })
  } catch {
    row.is_enabled = !row.is_enabled
  }
}

function confirmDelete(id: string) {
  confirm.require({
    message: '确认删除?',
    header: '确认',
    icon: 'pi pi-exclamation-triangle',
    accept: () => handleDelete(id)
  })
}

async function handleDelete(id: string) {
  try {
    await monitorApi.alertRules.delete(id)
    toast.add({ severity: 'success', summary: '成功', detail: '删除成功', life: 3000 })
    loadData()
  } catch {
    toast.add({ severity: 'error', summary: '错误', detail: '删除失败', life: 3000 })
  }
}
</script>

<style scoped>
.form-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.condition-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.field label {
  font-size: 14px;
  font-weight: 500;
}
.w-full {
  width: 100%;
}
</style>
