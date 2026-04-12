<template>
  <div>
    <el-card shadow="never">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
        <h3 style="margin:0">系统配置</h3>
        <el-button type="primary" @click="showDialog()">新增配置</el-button>
      </div>
      <el-table :data="tableData" stripe v-loading="loading">
        <el-table-column prop="key" label="键" width="200" />
        <el-table-column label="值" min-width="200">
          <template #default="{ row }"><span>{{ row.is_sensitive ? '******' : row.value }}</span></template>
        </el-table-column>
        <el-table-column prop="value_type" label="类型" width="80" />
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="showDialog(row)">编辑</el-button>
            <el-popconfirm title="确认删除?" @confirm="handleDelete(row.id)"><template #reference><el-button text type="danger" size="small">删除</el-button></template></el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑配置' : '新增配置'" width="500px" destroy-on-close>
      <el-form :model="form" :rules="formRules" ref="formRef" label-width="80px">
        <el-form-item label="键" prop="key"><el-input v-model="form.key" :disabled="!!editingId" /></el-form-item>
        <el-form-item label="值" prop="value"><el-input v-model="form.value" type="textarea" :rows="3" :placeholder="editingId && form.is_sensitive ? '留空则不修改密码' : ''" /></el-form-item>
        <el-form-item label="类型"><el-select v-model="form.value_type" style="width:100%"><el-option label="字符串" value="string" /><el-option label="整数" value="int" /><el-option label="布尔" value="bool" /><el-option label="JSON" value="json" /></el-select></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" /></el-form-item>
        <el-form-item label="敏感"><el-switch v-model="form.is_sensitive" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible=false">取消</el-button><el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { configApi } from '@/api/system'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const tableData = ref<any[]>([])
const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref('')
const formRef = ref()
const form = ref<any>({ key: '', value: '', value_type: 'string', description: '', is_sensitive: false })
const formRules = { key: [{ required: true, message: '请输入', trigger: 'blur' }], value: [{ required: true, message: '请输入', trigger: 'blur' }] }

onMounted(() => loadData())

async function loadData() {
  loading.value = true
  try { const { data } = await configApi.list({ limit: 200 }); tableData.value = Array.isArray(data) ? data : (data.items || []) } catch { ElMessage.error('加载失败') } finally { loading.value = false }
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
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    const payload: any = { ...form.value }
    if (editingId.value && form.value.is_sensitive && !form.value.value) {
      delete payload.value
    }
    if (editingId.value) { await configApi.update(editingId.value, payload); ElMessage.success('更新成功') }
    else { await configApi.create(payload); ElMessage.success('创建成功') }
    dialogVisible.value = false; loadData()
  } catch { ElMessage.error('操作失败') } finally { submitting.value = false }
}

async function handleDelete(id: string) {
  try { await configApi.delete(id); ElMessage.success('删除成功'); loadData() } catch { ElMessage.error('删除失败') }
}
</script>
