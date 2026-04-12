<template>
  <div>
    <el-card shadow="never">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
        <h3 style="margin:0">数据中心管理</h3>
        <el-button type="primary" @click="showDialog()">新增数据中心</el-button>
      </div>
      <el-table :data="tableData" stripe v-loading="loading">
        <el-table-column prop="name" label="名称" min-width="120" />
        <el-table-column prop="code" label="编码" width="100" />
        <el-table-column prop="location" label="位置" min-width="150" />
        <el-table-column prop="contact_name" label="联系人" width="100" />
        <el-table-column prop="contact_phone" label="联系电话" width="130" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }"><el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '启用' : '停用' }}</el-tag></template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="showDialog(row)">编辑</el-button>
            <el-popconfirm title="确认删除?" @confirm="handleDelete(row.id)"><template #reference><el-button text type="danger" size="small">删除</el-button></template></el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑' : '新增'" width="500px" destroy-on-close>
      <el-form :model="form" :rules="formRules" ref="formRef" label-width="80px">
        <el-form-item label="名称" prop="name"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="编码" prop="code"><el-input v-model="form.code" /></el-form-item>
        <el-form-item label="位置"><el-input v-model="form.location" /></el-form-item>
        <el-form-item label="联系人"><el-input v-model="form.contact_name" /></el-form-item>
        <el-form-item label="联系电话"><el-input v-model="form.contact_phone" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible=false">取消</el-button><el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { dataCenterApi } from '@/api/asset'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const tableData = ref<any[]>([])
const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref('')
const formRef = ref()
const form = ref<any>({ name: '', code: '', location: '', contact_name: '', contact_phone: '', description: '' })
const formRules = { name: [{ required: true, message: '请输入名称', trigger: 'blur' }], code: [{ required: true, message: '请输入编码', trigger: 'blur' }] }

onMounted(() => loadData())

async function loadData() {
  loading.value = true
  try { const { data } = await dataCenterApi.list(); tableData.value = Array.isArray(data) ? data : (data.items || []) } catch { ElMessage.error('加载失败') } finally { loading.value = false }
}

function showDialog(row?: any) {
  editingId.value = row?.id || ''
  form.value = row ? { name: row.name, code: row.code, location: row.location, contact_name: row.contact_name, contact_phone: row.contact_phone, description: row.description } : { name: '', code: '', location: '', contact_name: '', contact_phone: '', description: '' }
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    if (editingId.value) { await dataCenterApi.update(editingId.value, form.value); ElMessage.success('更新成功') }
    else { await dataCenterApi.create(form.value); ElMessage.success('创建成功') }
    dialogVisible.value = false; loadData()
  } catch { ElMessage.error('操作失败') } finally { submitting.value = false }
}

async function handleDelete(id: string) {
  try { await dataCenterApi.delete(id); ElMessage.success('删除成功'); loadData() } catch { ElMessage.error('删除失败') }
}
</script>
