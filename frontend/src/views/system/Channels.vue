<template>
  <div>
    <el-card shadow="never">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
        <h3 style="margin:0">通知渠道</h3>
        <el-button type="primary" @click="showDialog()">新增渠道</el-button>
      </div>
      <el-table :data="tableData" stripe v-loading="loading">
        <el-table-column prop="name" label="名称" width="140" />
        <el-table-column prop="channel_type" label="类型" width="100" />
        <el-table-column label="启用" width="80">
          <template #default="{ row }"><el-switch v-model="row.is_enabled" @change="toggleChannel(row)" /></template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="showDialog(row)">编辑</el-button>
            <el-popconfirm title="确认删除?" @confirm="handleDelete(row.id)"><template #reference><el-button text type="danger" size="small">删除</el-button></template></el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑渠道' : '新增渠道'" width="600px" destroy-on-close>
      <el-form :model="form" :rules="formRules" ref="formRef" label-width="80px">
        <el-form-item label="名称" prop="name"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="类型" prop="channel_type">
          <el-select v-model="form.channel_type" style="width:100%">
            <el-option label="邮件" value="email" /><el-option label="Webhook" value="webhook" /><el-option label="钉钉" value="dingtalk" /><el-option label="企业微信" value="wecom" /><el-option label="飞书" value="lark" />
          </el-select>
        </el-form-item>
        <el-form-item label="配置" prop="config">
          <el-input v-model="configJson" type="textarea" :rows="8" placeholder="JSON 配置" />
        </el-form-item>
        <el-form-item label="启用"><el-switch v-model="form.is_enabled" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible=false">取消</el-button><el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { channelApi } from '@/api/system'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const tableData = ref<any[]>([])
const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref('')
const formRef = ref()
const form = ref<any>({ name: '', channel_type: 'email', config: {}, is_enabled: true })
const formRules = { name: [{ required: true, message: '请输入', trigger: 'blur' }], channel_type: [{ required: true }] }

const configJson = computed({
  get: () => JSON.stringify(form.value.config, null, 2),
  set: (v: string) => { try { form.value.config = JSON.parse(v) } catch { ElMessage.warning('JSON 格式无效') } },
})

onMounted(() => loadData())

async function loadData() {
  loading.value = true
  try { const { data } = await channelApi.list({ limit: 200 }); tableData.value = Array.isArray(data) ? data : (data.items || []) } catch { ElMessage.error('加载失败') } finally { loading.value = false }
}

function showDialog(row?: any) {
  editingId.value = row?.id || ''
  form.value = row ? { name: row.name, channel_type: row.channel_type, config: row.config, is_enabled: row.is_enabled } : { name: '', channel_type: 'email', config: {}, is_enabled: true }
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    if (editingId.value) { await channelApi.update(editingId.value, form.value); ElMessage.success('更新成功') }
    else { await channelApi.create(form.value); ElMessage.success('创建成功') }
    dialogVisible.value = false; loadData()
  } catch { ElMessage.error('操作失败') } finally { submitting.value = false }
}

async function toggleChannel(row: any) {
  try { await channelApi.update(row.id, { is_enabled: row.is_enabled }) } catch { row.is_enabled = !row.is_enabled }
}

async function handleDelete(id: string) {
  try { await channelApi.delete(id); ElMessage.success('删除成功'); loadData() } catch { ElMessage.error('删除失败') }
}
</script>
