<template>
  <div>
    <el-card shadow="never">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
        <h3 style="margin:0">角色管理</h3>
        <el-button type="primary" @click="showDialog()">新增角色</el-button>
      </div>
      <el-table :data="tableData" stripe v-loading="loading">
        <el-table-column prop="name" label="角色名称" width="140" />
        <el-table-column prop="code" label="编码" width="140" />
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column label="权限数" width="80">
          <template #default="{ row }">{{ (row.permissions || []).length }}</template>
        </el-table-column>
        <el-table-column label="内置" width="70">
          <template #default="{ row }"><el-tag v-if="row.is_builtin" type="info" size="small">是</el-tag></template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="showDialog(row)">编辑</el-button>
            <el-popconfirm v-if="!row.is_builtin" title="确认删除?" @confirm="handleDelete(row.id)"><template #reference><el-button text type="danger" size="small">删除</el-button></template></el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑角色' : '新增角色'" width="550px" destroy-on-close>
      <el-form :model="form" :rules="formRules" ref="formRef" label-width="80px">
        <el-form-item label="名称" prop="name"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="编码" prop="code"><el-input v-model="form.code" :disabled="!!editingId" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="权限">
          <el-tree ref="permTreeRef" :data="permTree" show-checkbox node-key="id" :default-checked-keys="form.permission_ids" :props="{ label: 'name', children: 'children' }" />
        </el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible=false">取消</el-button><el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { roleApi, permissionApi } from '@/api/system'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const tableData = ref<any[]>([])
const allPerms = ref<any[]>([])
const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref('')
const formRef = ref()
const permTreeRef = ref()
const form = ref<any>({ name: '', code: '', description: '', permission_ids: [] })
const formRules = { name: [{ required: true, message: '请输入', trigger: 'blur' }], code: [{ required: true, message: '请输入', trigger: 'blur' }] }

const permTree = computed(() => {
  const groups: Record<string, any[]> = {}
  for (const p of allPerms.value) {
    if (!groups[p.resource]) groups[p.resource] = []
    groups[p.resource].push({ ...p, name: `${p.action} - ${p.name}` })
  }
  return Object.entries(groups).map(([resource, children]) => ({
    id: `group_${resource}`,
    name: resource,
    children,
  }))
})

onMounted(async () => { loadData(); try { const { data } = await permissionApi.list(); allPerms.value = Array.isArray(data) ? data : (data.items || []) } catch { ElMessage.error('操作失败') } })

async function loadData() {
  loading.value = true
  try { const { data } = await roleApi.list({ limit: 200 }); tableData.value = data.items || [] } catch { ElMessage.error('加载失败') } finally { loading.value = false }
}

function showDialog(row?: any) {
  editingId.value = row?.id || ''
  form.value = row ? { name: row.name, code: row.code, description: row.description, permission_ids: (row.permissions || []).map((p: any) => p.id) } : { name: '', code: '', description: '', permission_ids: [] }
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    const checkedKeys = permTreeRef.value?.getCheckedKeys(true) || []
    const payload = { name: form.value.name, code: form.value.code, description: form.value.description, permission_ids: checkedKeys }
    if (editingId.value) { await roleApi.update(editingId.value, payload); ElMessage.success('更新成功') }
    else { await roleApi.create(payload); ElMessage.success('创建成功') }
    dialogVisible.value = false; loadData()
  } catch { ElMessage.error('操作失败') } finally { submitting.value = false }
}

async function handleDelete(id: string) {
  try { await roleApi.delete(id); ElMessage.success('删除成功'); loadData() } catch { ElMessage.error('删除失败') }
}
</script>
