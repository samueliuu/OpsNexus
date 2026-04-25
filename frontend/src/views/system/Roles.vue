<template>
  <div>
    <Card>
      <template #content>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
          <h3 style="margin:0">角色管理</h3>
          <Button @click="showDialog()">新增角色</Button>
        </div>
        <DataTable :value="tableData" striped :loading="loading">
          <Column field="name" header="角色名称" style="width:140px" />
          <Column field="code" header="编码" style="width:140px" />
          <Column field="description" header="描述" style="min-width:200px" />
          <Column header="权限数" style="width:80px">
            <template #body="{ data }">{{ (data.permissions || []).length }}</template>
          </Column>
          <Column header="内置" style="width:70px">
            <template #body="{ data }"><Tag v-if="data.is_builtin" severity="secondary" style="font-size:12px">是</Tag></template>
          </Column>
          <Column header="操作" style="width:150px">
            <template #body="{ data }">
              <div style="display:flex;gap:4px">
                <Button link size="small" @click="showDialog(data)">编辑</Button>
                <Button v-if="!data.is_builtin" link severity="danger" size="small" @click="confirmDelete(data.id)">删除</Button>
              </div>
            </template>
          </Column>
        </DataTable>
      </template>
    </Card>
    <Dialog v-model:visible="dialogVisible" :header="editingId ? '编辑角色' : '新增角色'" :style="{ width: '550px' }" :modal="true">
      <div class="field">
        <label>名称</label>
        <InputText v-model="form.name" style="width:100%" />
        <small v-if="errors.name" class="p-error">{{ errors.name }}</small>
      </div>
      <div class="field">
        <label>编码</label>
        <InputText v-model="form.code" :disabled="!!editingId" style="width:100%" />
        <small v-if="errors.code" class="p-error">{{ errors.code }}</small>
      </div>
      <div class="field">
        <label>描述</label>
        <Textarea v-model="form.description" :rows="2" style="width:100%" />
      </div>
      <div class="field">
        <label>权限</label>
        <Tree v-model:selectionKeys="selectedPermKeys" :value="permTree" selectionMode="checkbox" :metaKeySelection="false" />
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
import { ref, computed, onMounted, watch } from 'vue'
import { roleApi, permissionApi } from '@/api/system'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Tree from 'primevue/tree'
import ConfirmDialog from 'primevue/confirmdialog'

const toast = useToast()
const confirm = useConfirm()

const loading = ref(false)
const tableData = ref<any[]>([])
const allPerms = ref<any[]>([])
const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref('')
const form = ref<any>({ name: '', code: '', description: '', permission_ids: [] })
const errors = ref<Record<string, string>>({})
const selectedPermKeys = ref<Record<string, boolean>>({})

const permTree = computed(() => {
  const groups: Record<string, any[]> = {}
  for (const p of allPerms.value) {
    if (!groups[p.resource]) groups[p.resource] = []
    groups[p.resource].push({
      key: p.id,
      label: `${p.action} - ${p.name}`,
    })
  }
  return Object.entries(groups).map(([resource, children]) => ({
    key: `group_${resource}`,
    label: resource,
    children,
  }))
})

watch(dialogVisible, (val) => {
  if (val) {
    const keys: Record<string, boolean> = {}
    for (const pid of form.value.permission_ids) {
      keys[pid] = true
    }
    selectedPermKeys.value = keys
  }
})

onMounted(async () => { loadData(); try { const { data } = await permissionApi.list(); allPerms.value = Array.isArray(data) ? data : (data.items || []) } catch { toast.add({ severity: 'error', summary: '错误', detail: '操作失败', life: 3000 }) } })

async function loadData() {
  loading.value = true
  try { const { data } = await roleApi.list({ limit: 200 }); tableData.value = data.items || [] } catch { toast.add({ severity: 'error', summary: '错误', detail: '加载失败', life: 3000 }) } finally { loading.value = false }
}

function showDialog(row?: any) {
  editingId.value = row?.id || ''
  form.value = row ? { name: row.name, code: row.code, description: row.description, permission_ids: (row.permissions || []).map((p: any) => p.id) } : { name: '', code: '', description: '', permission_ids: [] }
  errors.value = {}
  dialogVisible.value = true
}

function validate(): boolean {
  errors.value = {}
  if (!form.value.name) errors.value.name = '请输入'
  if (!form.value.code) errors.value.code = '请输入'
  return Object.keys(errors.value).length === 0
}

async function handleSubmit() {
  if (!validate()) return
  submitting.value = true
  try {
    const checkedKeys = Object.keys(selectedPermKeys.value).filter(k => !k.startsWith('group_'))
    const payload = { name: form.value.name, code: form.value.code, description: form.value.description, permission_ids: checkedKeys }
    if (editingId.value) { await roleApi.update(editingId.value, payload); toast.add({ severity: 'success', summary: '成功', detail: '更新成功', life: 3000 }) }
    else { await roleApi.create(payload); toast.add({ severity: 'success', summary: '成功', detail: '创建成功', life: 3000 }) }
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
      try { await roleApi.delete(id); toast.add({ severity: 'success', summary: '成功', detail: '删除成功', life: 3000 }); loadData() } catch { toast.add({ severity: 'error', summary: '错误', detail: '删除失败', life: 3000 }) }
    },
  })
}
</script>
