<template>
  <div>
    <el-card shadow="never">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
        <h3 style="margin:0">告警规则</h3>
        <el-button type="primary" @click="showDialog()">新增规则</el-button>
      </div>
      <el-table :data="tableData" stripe v-loading="loading">
        <el-table-column prop="name" label="规则名称" min-width="140" />
        <el-table-column prop="metric_name" label="指标" width="160" />
        <el-table-column label="条件" width="180">
          <template #default="{ row }">{{ row.metric_name }} {{ condMap[row.condition] || row.condition }} {{ row.threshold }} {{ row.duration > 0 ? `(持续${row.duration}s)` : '' }}</template>
        </el-table-column>
        <el-table-column label="严重级别" width="90">
          <template #default="{ row }"><el-tag :type="sevType(row.severity)" size="small">{{ row.severity }}</el-tag></template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }"><el-switch v-model="row.is_enabled" @change="toggleRule(row)" /></template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="showDialog(row)">编辑</el-button>
            <el-popconfirm title="确认删除?" @confirm="handleDelete(row.id)"><template #reference><el-button text type="danger" size="small">删除</el-button></template></el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑规则' : '新增规则'" width="550px" destroy-on-close>
      <el-form :model="form" :rules="formRules" ref="formRef" label-width="90px">
        <el-form-item label="规则名称" prop="name"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="指标" prop="metric_name"><el-input v-model="form.metric_name" placeholder="如 cpu_temperature_celsius" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="8"><el-form-item label="条件" prop="condition"><el-select v-model="form.condition" style="width:100%"><el-option v-for="(v,k) in condMap" :key="k" :label="v" :value="k" /></el-select></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="阈值" prop="threshold"><el-input-number v-model="form.threshold" style="width:100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="持续(s)"><el-input-number v-model="form.duration" :min="0" style="width:100%" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="严重级别" prop="severity"><el-select v-model="form.severity" style="width:100%"><el-option label="严重" value="critical" /><el-option label="警告" value="warning" /><el-option label="信息" value="info" /></el-select></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible=false">取消</el-button><el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { monitorApi } from '@/api/monitor'
import { ElMessage } from 'element-plus'

const condMap: Record<string, string> = { gt: '>', lt: '<', eq: '=', ne: '≠', ge: '≥', le: '≤' }
const loading = ref(false)
const tableData = ref<any[]>([])
const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref('')
const formRef = ref()
const form = ref<any>({ name: '', metric_name: '', condition: 'gt', threshold: 0, duration: 60, severity: 'warning', is_enabled: true })
const formRules = { name: [{ required: true, message: '请输入', trigger: 'blur' }], metric_name: [{ required: true, message: '请输入', trigger: 'blur' }], condition: [{ required: true }], threshold: [{ required: true }], severity: [{ required: true }] }

onMounted(() => loadData())

async function loadData() {
  loading.value = true
  try { const { data } = await monitorApi.alertRules.list({ limit: 200 }); tableData.value = data.items || [] } catch { ElMessage.error('加载失败') } finally { loading.value = false }
}

function sevType(s: string) { return { critical: 'danger', warning: 'warning', info: 'info' }[s] || 'info' }

function showDialog(row?: any) {
  editingId.value = row?.id || ''
  form.value = row ? { name: row.name, metric_name: row.metric_name, condition: row.condition, threshold: row.threshold, duration: row.duration, severity: row.severity, is_enabled: row.is_enabled } : { name: '', metric_name: '', condition: 'gt', threshold: 0, duration: 60, severity: 'warning', is_enabled: true }
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    if (editingId.value) { await monitorApi.alertRules.update(editingId.value, form.value); ElMessage.success('更新成功') }
    else { await monitorApi.alertRules.create(form.value); ElMessage.success('创建成功') }
    dialogVisible.value = false; loadData()
  } catch { ElMessage.error('操作失败') } finally { submitting.value = false }
}

async function toggleRule(row: any) {
  try { await monitorApi.alertRules.update(row.id, { is_enabled: row.is_enabled }) } catch { row.is_enabled = !row.is_enabled }
}

async function handleDelete(id: string) {
  try { await monitorApi.alertRules.delete(id); ElMessage.success('删除成功'); loadData() } catch { ElMessage.error('删除失败') }
}
</script>
