<template>
  <div>
    <Card>
      <template #content>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
          <h3 style="margin:0">通知渠道</h3>
          <Button @click="showDialog()">新增渠道</Button>
        </div>
        <DataTable :value="tableData" striped :loading="loading">
          <Column field="name" header="名称" style="width:140px" />
          <Column field="channel_type" header="类型" style="width:100px" />
          <Column header="启用" style="width:80px">
            <template #body="{ data }"><InputSwitch v-model="data.is_enabled" @change="toggleChannel(data)" /></template>
          </Column>
          <Column header="操作" style="width:150px">
            <template #body="{ data }">
              <div style="display:flex;gap:4px">
                <Button link size="small" @click="showDialog(data)">编辑</Button>
                <Button link severity="danger" size="small" @click="confirmDelete(data.id)">删除</Button>
              </div>
            </template>
          </Column>
        </DataTable>
      </template>
    </Card>
    <Dialog v-model:visible="dialogVisible" :header="editingId ? '编辑渠道' : '新增渠道'" :style="{ width: '600px' }" :modal="true">
      <div class="field">
        <label>名称</label>
        <InputText v-model="form.name" style="width:100%" />
        <small v-if="errors.name" class="p-error">{{ errors.name }}</small>
      </div>
      <div class="field">
        <label>类型</label>
        <Select v-model="form.channel_type" :options="channelTypeOptions" optionLabel="label" optionValue="value" style="width:100%" />
        <small v-if="errors.channel_type" class="p-error">{{ errors.channel_type }}</small>
      </div>
      <div class="field">
        <label>配置</label>
        <Textarea v-model="configJson" :rows="8" placeholder="JSON 配置" style="width:100%" />
      </div>
      <div class="field" style="display:flex;align-items:center;gap:8px">
        <label style="margin:0">启用</label>
        <InputSwitch v-model="form.is_enabled" />
      </div>
      <template #footer>
        <Button label="取消" @click="dialogVisible = false" />
        <Button label="确定" :loading="submitting" @click="handleSubmit" />
      </template>
    </Dialog>
    <ConfirmDialog />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { channelApi } from '@/api/system'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'
import InputSwitch from 'primevue/inputswitch'
import ConfirmDialog from 'primevue/confirmdialog'

const toast = useToast()
const confirm = useConfirm()

const loading = ref(false)
const tableData = ref<any[]>([])
const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref('')
const form = ref<any>({ name: '', channel_type: 'email', config: {}, is_enabled: true })
const errors = ref<Record<string, string>>({})

const channelTypeOptions = [
  { label: '邮件', value: 'email' },
  { label: 'Webhook', value: 'webhook' },
  { label: '钉钉', value: 'dingtalk' },
  { label: '企业微信', value: 'wecom' },
  { label: '飞书', value: 'lark' },
]

const configJson = computed({
  get: () => JSON.stringify(form.value.config, null, 2),
  set: (v: string) => { try { form.value.config = JSON.parse(v) } catch { toast.add({ severity: 'warn', summary: '警告', detail: 'JSON 格式无效', life: 3000 }) } },
})

onMounted(() => loadData())

async function loadData() {
  loading.value = true
  try { const { data } = await channelApi.list({ limit: 200 }); tableData.value = Array.isArray(data) ? data : (data.items || []) } catch { toast.add({ severity: 'error', summary: '错误', detail: '加载失败', life: 3000 }) } finally { loading.value = false }
}

function showDialog(row?: any) {
  editingId.value = row?.id || ''
  form.value = row ? { name: row.name, channel_type: row.channel_type, config: row.config, is_enabled: row.is_enabled } : { name: '', channel_type: 'email', config: {}, is_enabled: true }
  errors.value = {}
  dialogVisible.value = true
}

function validate(): boolean {
  errors.value = {}
  if (!form.value.name) errors.value.name = '请输入'
  if (!form.value.channel_type) errors.value.channel_type = '请选择'
  return Object.keys(errors.value).length === 0
}

async function handleSubmit() {
  if (!validate()) return
  submitting.value = true
  try {
    if (editingId.value) { await channelApi.update(editingId.value, form.value); toast.add({ severity: 'success', summary: '成功', detail: '更新成功', life: 3000 }) }
    else { await channelApi.create(form.value); toast.add({ severity: 'success', summary: '成功', detail: '创建成功', life: 3000 }) }
    dialogVisible.value = false; loadData()
  } catch { toast.add({ severity: 'error', summary: '错误', detail: '操作失败', life: 3000 }) } finally { submitting.value = false }
}

async function toggleChannel(row: any) {
  try { await channelApi.update(row.id, { is_enabled: row.is_enabled }) } catch { row.is_enabled = !row.is_enabled }
}

function confirmDelete(id: string) {
  confirm.require({
    message: '确认删除?',
    header: '删除确认',
    icon: 'pi pi-exclamation-triangle',
    acceptProps: { severity: 'danger' },
    accept: async () => {
      try { await channelApi.delete(id); toast.add({ severity: 'success', summary: '成功', detail: '删除成功', life: 3000 }); loadData() } catch { toast.add({ severity: 'error', summary: '错误', detail: '删除失败', life: 3000 }) }
    },
  })
}
</script>
