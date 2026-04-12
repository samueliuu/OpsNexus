<template>
  <div>
    <el-card shadow="never">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
        <h3 style="margin:0">用户管理</h3>
        <el-button type="primary" @click="showDialog()">新增用户</el-button>
      </div>
      <el-table :data="tableData" stripe v-loading="loading">
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="full_name" label="姓名" width="120" />
        <el-table-column prop="email" label="邮箱" min-width="180" />
        <el-table-column prop="department" label="部门" width="100" />
        <el-table-column label="角色" min-width="150">
          <template #default="{ row }"><el-tag v-for="role in (row.roles || [])" :key="role.id" size="small" style="margin-right:4px">{{ role.name }}</el-tag></template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }"><el-tag :type="row.is_active ? 'success' : 'danger'" size="small">{{ row.is_active ? '启用' : '禁用' }}</el-tag></template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="showDialog(row)">编辑</el-button>
            <el-button text :type="row.is_active ? 'warning' : 'success'" size="small" @click="toggleActive(row)">{{ row.is_active ? '禁用' : '启用' }}</el-button>
            <el-popconfirm title="确认删除?" @confirm="handleDelete(row.id)"><template #reference><el-button text type="danger" size="small">删除</el-button></template></el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑用户' : '新增用户'" width="550px" destroy-on-close>
      <el-form :model="form" :rules="formRules" ref="formRef" label-width="80px">
        <el-form-item label="用户名" prop="username"><el-input v-model="form.username" :disabled="!!editingId" /></el-form-item>
        <el-form-item v-if="!editingId" label="密码" prop="password"><el-input v-model="form.password" type="password" show-password /></el-form-item>
        <el-form-item label="邮箱" prop="email"><el-input v-model="form.email" /></el-form-item>
        <el-form-item label="姓名"><el-input v-model="form.full_name" /></el-form-item>
        <el-form-item label="部门"><el-input v-model="form.department" /></el-form-item>
        <el-form-item label="角色"><el-select v-model="form.role_ids" multiple style="width:100%"><el-option v-for="r in roles" :key="r.id" :label="r.name" :value="r.id" /></el-select></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible=false">取消</el-button><el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { userApi, roleApi } from '@/api/system'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const tableData = ref<any[]>([])
const roles = ref<any[]>([])
const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref('')
const formRef = ref()
const form = ref<any>({ username: '', password: '', email: '', full_name: '', department: '', role_ids: [] })
const formRules = {
  username: [{ required: true, message: '请输入', trigger: 'blur' }],
  password: [{ required: true, min: 8, message: '至少8位', trigger: 'blur' }],
  email: [{ required: true, message: '请输入', trigger: 'blur' }],
}

onMounted(async () => { loadData(); try { const { data } = await roleApi.list({ limit: 100 }); roles.value = data.items || [] } catch { ElMessage.error('操作失败') } })

async function loadData() {
  loading.value = true
  try { const { data } = await userApi.list({ limit: 200 }); tableData.value = data.items || [] } catch { ElMessage.error('加载失败') } finally { loading.value = false }
}

function showDialog(row?: any) {
  editingId.value = row?.id || ''
  form.value = row ? { username: row.username, email: row.email, full_name: row.full_name, phone: row.phone, department: row.department, password: '', role_ids: (row.roles || []).map((r: any) => r.id) } : { username: '', password: '', email: '', full_name: '', department: '', role_ids: [] }
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    const payload = { ...form.value }
    if (editingId.value) {
      delete payload.password
      await userApi.update(editingId.value, payload); ElMessage.success('更新成功')
    }
    else { await userApi.create(payload); ElMessage.success('创建成功') }
    dialogVisible.value = false; loadData()
  } catch { ElMessage.error('操作失败') } finally { submitting.value = false }
}

async function toggleActive(row: any) {
  const prev = row.is_active
  try { await userApi.update(row.id, { is_active: !prev }); loadData() } catch { row.is_active = prev }
}

async function handleDelete(id: string) {
  try { await userApi.delete(id); ElMessage.success('删除成功'); loadData() } catch { ElMessage.error('删除失败') }
}
</script>
