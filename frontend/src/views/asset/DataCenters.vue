<template>
  <div>
    <Card>
      <template #content>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
          <h3 style="margin:0">数据中心管理</h3>
          <Button label="新增数据中心" @click="showDialog()" />
        </div>
        <DataTable :value="tableData" stripedRows :loading="loading">
          <Column field="name" header="名称" style="min-width:120px" />
          <Column field="code" header="编码" style="width:100px" />
          <Column field="location" header="位置" style="min-width:150px" />
          <Column field="contact_name" header="联系人" style="width:100px" />
          <Column field="contact_phone" header="联系电话" style="width:130px" />
          <Column header="状态" style="width:80px">
            <template #body="{ data }"><Tag :severity="data.is_active ? 'success' : 'secondary'">{{ data.is_active ? '启用' : '停用' }}</Tag></template>
          </Column>
          <Column header="操作" style="width:150px">
            <template #body="{ data }">
              <Button label="编辑" link size="small" @click="showDialog(data)" />
              <Button label="删除" link severity="danger" size="small" @click="confirmDelete(data.id)" />
            </template>
          </Column>
        </DataTable>
      </template>
    </Card>
    <Dialog v-model:visible="dialogVisible" :header="editingId ? '编辑' : '新增'" :style="{ width: '500px' }" :modal="true">
      <div class="field">
        <label>名称</label>
        <InputText v-model="form.name" style="width:100%" />
      </div>
      <div class="field">
        <label>编码</label>
        <InputText v-model="form.code" style="width:100%" />
      </div>
      <div class="field">
        <label>位置</label>
        <InputText v-model="form.location" style="width:100%" />
      </div>
      <div class="field">
        <label>联系人</label>
        <InputText v-model="form.contact_name" style="width:100%" />
      </div>
      <div class="field">
        <label>联系电话</label>
        <InputText v-model="form.contact_phone" style="width:100%" />
      </div>
      <div class="field">
        <label>描述</label>
        <Textarea v-model="form.description" :rows="3" style="width:100%" />
      </div>
      <template #footer>
        <Button label="取消" severity="secondary" @click="dialogVisible=false" />
        <Button label="确定" :loading="submitting" @click="handleSubmit" />
      </template>
    </Dialog>
    <ConfirmDialog />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import ConfirmDialog from 'primevue/confirmdialog'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { dataCenterApi } from '@/api/asset'

const confirm = useConfirm()
const toast = useToast()

const loading = ref(false)
const tableData = ref<any[]>([])
const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref('')
const form = ref<any>({ name: '', code: '', location: '', contact_name: '', contact_phone: '', description: '' })

onMounted(() => loadData())

async function loadData() {
  loading.value = true
  try { const { data } = await dataCenterApi.list(); tableData.value = Array.isArray(data) ? data : (data.items || []) } catch { toast.add({ severity: 'error', summary: '错误', detail: '加载失败', life: 3000 }) } finally { loading.value = false }
}

function showDialog(row?: any) {
  editingId.value = row?.id || ''
  form.value = row ? { name: row.name, code: row.code, location: row.location, contact_name: row.contact_name, contact_phone: row.contact_phone, description: row.description } : { name: '', code: '', location: '', contact_name: '', contact_phone: '', description: '' }
  dialogVisible.value = true
}

function validateForm(): boolean {
  if (!form.value.name) { toast.add({ severity: 'warn', summary: '提示', detail: '请输入名称', life: 3000 }); return false }
  if (!form.value.code) { toast.add({ severity: 'warn', summary: '提示', detail: '请输入编码', life: 3000 }); return false }
  return true
}

async function handleSubmit() {
  if (!validateForm()) return
  submitting.value = true
  try {
    if (editingId.value) { await dataCenterApi.update(editingId.value, form.value); toast.add({ severity: 'success', summary: '成功', detail: '更新成功', life: 3000 }) }
    else { await dataCenterApi.create(form.value); toast.add({ severity: 'success', summary: '成功', detail: '创建成功', life: 3000 }) }
    dialogVisible.value = false; loadData()
  } catch { toast.add({ severity: 'error', summary: '错误', detail: '操作失败', life: 3000 }) } finally { submitting.value = false }
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
  try { await dataCenterApi.delete(id); toast.add({ severity: 'success', summary: '成功', detail: '删除成功', life: 3000 }); loadData() } catch { toast.add({ severity: 'error', summary: '错误', detail: '删除失败', life: 3000 }) }
}
</script>
