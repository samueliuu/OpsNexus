<template>
  <div>
    <Card>
      <template #content>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
          <h3 style="margin:0">用户管理</h3>
          <Button @click="showDialog()">新增用户</Button>
        </div>
        <DataTable :value="tableData" striped :loading="loading">
          <Column field="username" header="用户名" style="width:120px" />
          <Column field="full_name" header="姓名" style="width:120px" />
          <Column field="email" header="邮箱" style="min-width:180px" />
          <Column field="department" header="部门" style="width:100px" />
          <Column header="角色" style="min-width:150px">
            <template #body="{ data }">
              <Tag v-for="role in (data.roles || [])" :key="role.id" style="font-size:12px;margin-right:4px">{{ role.name }}</Tag>
            </template>
          </Column>
          <Column header="状态" style="width:80px">
            <template #body="{ data }"><Tag :severity="data.is_active ? 'success' : 'danger'" style="font-size:12px">{{ data.is_active ? '启用' : '禁用' }}</Tag></template>
          </Column>
          <Column header="操作" style="width:180px">
            <template #body="{ data }">
              <div style="display:flex;gap:4px">
                <Button link size="small" @click="showDialog(data)">编辑</Button>
                <Button link size="small" :severity="data.is_active ? 'warning' : 'success'" @click="toggleActive(data)">{{ data.is_active ? '禁用' : '启用' }}</Button>
                <Button link severity="danger" size="small" @click="confirmDelete(data.id)">删除</Button>
              </div>
            </template>
          </Column>
        </DataTable>
      </template>
    </Card>
    <Dialog v-model:visible="dialogVisible" :header="editingId ? '编辑用户' : '新增用户'" :style="{ width: '550px' }" :modal="true">
      <div class="field">
        <label>用户名</label>
        <InputText v-model="form.username" :disabled="!!editingId" style="width:100%" />
        <small v-if="errors.username" class="p-error">{{ errors.username }}</small>
      </div>
      <div v-if="!editingId" class="field">
        <label>密码</label>
        <InputText v-model="form.password" type="password" style="width:100%" />
        <small v-if="errors.password" class="p-error">{{ errors.password }}</small>
      </div>
      <div class="field">
        <label>邮箱</label>
        <InputText v-model="form.email" style="width:100%" />
        <small v-if="errors.email" class="p-error">{{ errors.email }}</small>
      </div>
      <div class="field">
        <label>姓名</label>
        <InputText v-model="form.full_name" style="width:100%" />
      </div>
      <div class="field">
        <label>部门</label>
        <InputText v-model="form.department" style="width:100%" />
      </div>
      <div class="field">
        <label>角色</label>
        <MultiSelect v-model="form.role_ids" :options="roles" optionLabel="name" optionValue="id" placeholder="选择角色" style="width:100%" />
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
import { userApi, roleApi } from '@/api/system'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import MultiSelect from 'primevue/multiselect'
import ConfirmDialog from 'primevue/confirmdialog'

const toast = useToast()
const confirm = useConfirm()

const loading = ref(false)
const tableData = ref<any[]>([])
const roles = ref<any[]>([])
const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref('')
const form = ref<any>({ username: '', password: '', email: '', full_name: '', department: '', role_ids: [] })
const errors = ref<Record<string, string>>({})

onMounted(async () => { loadData(); try { const { data } = await roleApi.list({ limit: 100 }); roles.value = data.items || [] } catch { toast.add({ severity: 'error', summary: '错误', detail: '操作失败', life: 3000 }) } })

async function loadData() {
  loading.value = true
  try { const { data } = await userApi.list({ limit: 200 }); tableData.value = data.items || [] } catch { toast.add({ severity: 'error', summary: '错误', detail: '加载失败', life: 3000 }) } finally { loading.value = false }
}

function showDialog(row?: any) {
  editingId.value = row?.id || ''
  form.value = row ? { username: row.username, email: row.email, full_name: row.full_name, phone: row.phone, department: row.department, password: '', role_ids: (row.roles || []).map((r: any) => r.id) } : { username: '', password: '', email: '', full_name: '', department: '', role_ids: [] }
  errors.value = {}
  dialogVisible.value = true
}

function validate(): boolean {
  errors.value = {}
  if (!form.value.username) errors.value.username = '请输入'
  if (!editingId.value && (!form.value.password || form.value.password.length < 8)) errors.value.password = '至少8位'
  if (!form.value.email) errors.value.email = '请输入'
  return Object.keys(errors.value).length === 0
}

async function handleSubmit() {
  if (!validate()) return
  submitting.value = true
  try {
    const payload = { ...form.value }
    if (editingId.value) {
      delete payload.password
      await userApi.update(editingId.value, payload); toast.add({ severity: 'success', summary: '成功', detail: '更新成功', life: 3000 })
    }
    else { await userApi.create(payload); toast.add({ severity: 'success', summary: '成功', detail: '创建成功', life: 3000 }) }
    dialogVisible.value = false; loadData()
  } catch { toast.add({ severity: 'error', summary: '错误', detail: '操作失败', life: 3000 }) } finally { submitting.value = false }
}

async function toggleActive(row: any) {
  const prev = row.is_active
  try { await userApi.update(row.id, { is_active: !prev }); loadData() } catch { row.is_active = prev }
}

function confirmDelete(id: string) {
  confirm.require({
    message: '确认删除?',
    header: '删除确认',
    icon: 'pi pi-exclamation-triangle',
    acceptProps: { severity: 'danger' },
    accept: async () => {
      try { await userApi.delete(id); toast.add({ severity: 'success', summary: '成功', detail: '删除成功', life: 3000 }); loadData() } catch { toast.add({ severity: 'error', summary: '错误', detail: '删除失败', life: 3000 }) }
    },
  })
}
</script>
