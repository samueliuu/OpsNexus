<template>
  <div>
    <el-card shadow="never">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
        <h3 style="margin:0">机柜管理</h3>
        <el-button type="primary" @click="showDialog()">新增机柜</el-button>
      </div>
      <el-table :data="tableData" stripe v-loading="loading">
        <el-table-column prop="name" label="名称" min-width="120" />
        <el-table-column prop="code" label="编码" width="100" />
        <el-table-column prop="location" label="位置" min-width="120" />
        <el-table-column prop="u_height" label="U高" width="80" />
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
        <el-form-item label="数据中心" prop="data_center_id"><el-select v-model="form.data_center_id" style="width:100%"><el-option v-for="dc in dataCenters" :key="dc.id" :label="dc.name" :value="dc.id" /></el-select></el-form-item>
        <el-form-item label="位置"><el-input v-model="form.location" /></el-form-item>
        <el-form-item label="U高"><el-input-number v-model="form.u_height" :min="1" :max="52" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible=false">取消</el-button><el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { rackApi, dataCenterApi } from '@/api/asset'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const tableData = ref<any[]>([])
const dataCenters = ref<any[]>([])
const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref('')
const formRef = ref()
const form = ref<any>({ name: '', code: '', data_center_id: '', location: '', u_height: 42, description: '' })
const formRules = { name: [{ required: true, message: '请输入名称', trigger: 'blur' }], code: [{ required: true, message: '请输入编码', trigger: 'blur' }], data_center_id: [{ required: true, message: '请选择数据中心', trigger: 'change' }] }

onMounted(async () => { loadData(); try { const { data } = await dataCenterApi.list(); dataCenters.value = Array.isArray(data) ? data : (data.items || []) } catch { ElMessage.error('操作失败') } })

async function loadData() {
  loading.value = true
  try { const { data } = await rackApi.list(); tableData.value = Array.isArray(data) ? data : (data.items || []) } catch { ElMessage.error('加载失败') } finally { loading.value = false }
}

function showDialog(row?: any) {
  editingId.value = row?.id || ''
  form.value = row ? { name: row.name, code: row.code, data_center_id: row.data_center_id, location: row.location, u_height: row.u_height, description: row.description } : { name: '', code: '', data_center_id: '', location: '', u_height: 42, description: '' }
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    if (editingId.value) { await rackApi.update(editingId.value, form.value); ElMessage.success('更新成功') }
    else { await rackApi.create(form.value); ElMessage.success('创建成功') }
    dialogVisible.value = false; loadData()
  } catch { ElMessage.error('操作失败') } finally { submitting.value = false }
}

async function handleDelete(id: string) {
  try { await rackApi.delete(id); ElMessage.success('删除成功'); loadData() } catch { ElMessage.error('删除失败') }
}
</script>
