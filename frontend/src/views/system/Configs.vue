<template>
  <div>
    <Card>
      <template #content>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
          <h3 style="margin:0">系统配置</h3>
          <Button @click="showDialog()">新增配置</Button>
        </div>
        <DataTable :value="tableData" striped :loading="loading">
          <Column field="key" header="键" style="width:200px" />
          <Column header="值" style="min-width:200px">
            <template #body="{ data }"><span>{{ data.is_sensitive ? '******' : data.value }}</span></template>
          </Column>
          <Column field="value_type" header="类型" style="width:80px" />
          <Column field="description" header="描述" style="min-width:200px" />
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
    <Dialog v-model:visible="dialogVisible" :header="editingId ? '编辑配置' : '新增配置'" :style="{ width: '500px' }" :modal="true">
      <div class="field">
        <label>键</label>
        <InputText v-model="form.key" :disabled="!!editingId" style="width:100%" />
        <small v-if="errors.key" class="p-error">{{ errors.key }}</small>
      </div>
      <div class="field">
        <label>值</label>
        <Textarea v-model="form.value" :rows="3" :placeholder="editingId && form.is_sensitive ? '留空则不修改密码' : ''" style="width:100%" />
        <small v-if="errors.value" class="p-error">{{ errors.value }}</small>
      </div>
      <div class="field">
        <label>类型</label>
        <Select v-model="form.value_type" :options="valueTypeOptions" optionLabel="label" optionValue="value" style="width:100%" />
      </div>
      <div class="field">
        <label>描述</label>
        <InputText v-model="form.description" style="width:100%" />
      </div>
      <div class="field" style="display:flex;align-items:center;gap:8px">
        <label style="margin:0">敏感</label>
        <InputSwitch v-model="form.is_sensitive" />
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
import { ref, onMounted } from 'vue'
import { configApi } from '@/api/system'
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
const form = ref<any>({ key: '', value: '', value_type: 'string', description: '', is_sensitive: false })
const errors = ref<Record<string, string>>({})

const valueTypeOptions = [
  { label: '字符串', value: 'string' },
  { label: '整数', value: 'int' },
  { label: '布尔', value: 'bool' },
  { label: 'JSON', value: 'json' },
]

onMounted(() => loadData())

async function loadData() {
  loading.value = true
  try { const { data } = await configApi.list({ limit: 200 }); tableData.value = Array.isArray(data) ? data : (data.items || []) } catch { toast.add({ severity: 'error', summary: '错误', detail: '加载失败', life: 3000 }) } finally { loading.value = false }
}

function showDialog(row?: any) {
  editingId.value = row?.id || ''
  if (row) {
    form.value = {
      ...row,
      value: row.is_sensitive ? '' : row.value,
    }
  } else {
    form.value = { key: '', value: '', value_type: 'string', description: '', is_sensitive: false }
  }
  errors.value = {}
  dialogVisible.value = true
}

function validate(): boolean {
  errors.value = {}
  if (!form.value.key) errors.value.key = '请输入'
  if (!form.value.value && !(editingId.value && form.value.is_sensitive)) errors.value.value = '请输入'
  return Object.keys(errors.value).length === 0
}

async function handleSubmit() {
  if (!validate()) return
  submitting.value = true
  try {
    const payload: any = { ...form.value }
    if (editingId.value && form.value.is_sensitive && !form.value.value) {
      delete payload.value
    }
    if (editingId.value) { await configApi.update(editingId.value, payload); toast.add({ severity: 'success', summary: '成功', detail: '更新成功', life: 3000 }) }
    else { await configApi.create(payload); toast.add({ severity: 'success', summary: '成功', detail: '创建成功', life: 3000 }) }
    dialogVisible.value = false; loadData()
  } catch { toast.add({ severity: 'error', summary: '错误', detail: '操作失败', life: 3000 }) } finally { submitting.value = false }
}

function confirmDelete(id: string) {
  confirm.require({
    message: '确认删除?',
    header: '删除确认',
    icon: 'pi pi-exclamation-triangle',
    acceptProps: { severity: 'danger' },
    accept: async () => {
      try { await configApi.delete(id); toast.add({ severity: 'success', summary: '成功', detail: '删除成功', life: 3000 }); loadData() } catch { toast.add({ severity: 'error', summary: '错误', detail: '删除失败', life: 3000 }) }
    },
  })
}
</script>
