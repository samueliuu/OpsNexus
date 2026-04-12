<template>
  <div>
    <el-card shadow="never">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
        <h3 style="margin:0">服务器管理</h3>
        <div>
          <el-input v-model="search" placeholder="搜索名称/序列号" style="width:200px;margin-right:10px" clearable @clear="loadData" @keyup.enter="loadData" />
          <el-select v-model="filterBrand" placeholder="品牌" clearable style="width:120px;margin-right:10px" @change="page = 1; loadData()">
            <el-option v-for="b in brands" :key="b" :label="b" :value="b" />
          </el-select>
          <el-select v-model="filterStatus" placeholder="状态" clearable style="width:120px;margin-right:10px" @change="page = 1; loadData()">
            <el-option label="运行中" value="active" /><el-option label="维护中" value="maintenance" /><el-option label="已下线" value="retired" />
          </el-select>
          <el-button type="primary" @click="showDialog()">新增服务器</el-button>
        </div>
      </div>
      <el-table :data="tableData" stripe v-loading="loading" @row-click="(row: any) => $router.push(`/asset/servers/${row.id}`)" style="cursor:pointer">
        <el-table-column prop="name" label="名称" min-width="120" />
        <el-table-column prop="hostname" label="主机名" min-width="120" />
        <el-table-column prop="brand" label="品牌" width="100" />
        <el-table-column prop="model" label="型号" min-width="120" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : row.status === 'maintenance' ? 'warning' : 'info'" size="small">{{ statusMap[row.status] || row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="BMC" width="90">
          <template #default="{ row }">
            <el-tag :type="row.bmc_info?.bmc_status === 'online' ? 'success' : row.bmc_info?.bmc_status === 'offline' ? 'danger' : 'info'" size="small">{{ row.bmc_info?.bmc_status || '未知' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="BMC IP" width="140">
          <template #default="{ row }">{{ row.bmc_info?.bmc_ip || '-' }}</template>
        </el-table-column>
        <el-table-column label="CPU/内存" width="120">
          <template #default="{ row }">{{ row.hardware_info?.cpu_count ?? '-' }}C / {{ row.hardware_info?.memory_gb ?? '-' }}G</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click.stop="showDialog(row)">编辑</el-button>
            <el-popconfirm title="确认删除?" @confirm="handleDelete(row.id)">
              <template #reference><el-button text type="danger" size="small" @click.stop>删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" layout="total, sizes, prev, pager, next" :page-sizes="[20, 50, 100]" @change="loadData" style="margin-top:16px;justify-content:flex-end" />
    </el-card>
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑服务器' : '新增服务器'" width="700px" destroy-on-close>
      <el-form :model="form" :rules="formRules" ref="formRef" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="12"><el-form-item label="名称" prop="name"><el-input v-model="form.name" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="主机名" prop="hostname"><el-input v-model="form.hostname" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="品牌" prop="brand"><el-select v-model="form.brand" style="width:100%"><el-option v-for="b in brands" :key="b" :label="b" :value="b" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="型号" prop="model"><el-input v-model="form.model" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="BMC IP"><el-input v-model="form.bmc_info.bmc_ip" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="状态"><el-select v-model="form.status" style="width:100%"><el-option label="运行中" value="active" /><el-option label="维护中" value="maintenance" /><el-option label="已下线" value="retired" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="CPU型号"><el-input v-model="form.hardware_info.cpu_model" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="CPU数量"><el-input-number v-model="form.hardware_info.cpu_count" :min="0" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="内存(GB)"><el-input-number v-model="form.hardware_info.memory_gb" :min="0" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="序列号"><el-input v-model="form.serial_number" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="操作系统"><el-input v-model="form.software_info.os_name" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="部门"><el-input v-model="form.department" /></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { serverApi } from '@/api/asset'
import { ElMessage } from 'element-plus'

const brands = ['Dell', 'HPE', 'Lenovo', 'Huawei', 'Inspur', 'H3C', 'Sugon', 'xFusion']
const statusMap: Record<string, string> = { active: '运行中', inactive: '未激活', maintenance: '维护中', retired: '已下线' }

const loading = ref(false)
const tableData = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const search = ref('')
const filterBrand = ref('')
const filterStatus = ref('')

const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref('')
const formRef = ref()

function emptyForm() {
  return {
    name: '', hostname: '', brand: 'Dell', model: '', status: 'active',
    serial_number: '', department: '',
    bmc_info: { bmc_ip: '' },
    hardware_info: { cpu_model: '', cpu_count: 0, memory_gb: 0 },
    software_info: { os_name: '', os_version: '' },
  }
}

const form = ref<any>(emptyForm())
const formRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  brand: [{ required: true, message: '请选择品牌', trigger: 'change' }],
  model: [{ required: true, message: '请输入型号', trigger: 'blur' }],
}

onMounted(() => loadData())

async function loadData() {
  loading.value = true
  try {
    const params: any = { skip: (page.value - 1) * pageSize.value, limit: pageSize.value }
    if (search.value) params.search = search.value
    if (filterBrand.value) params.brand = filterBrand.value
    if (filterStatus.value) params.status = filterStatus.value
    const { data } = await serverApi.list(params)
    tableData.value = data.items || []
    total.value = data.total || 0
  } catch { ElMessage.error('加载服务器失败') } finally {
    loading.value = false
  }
}

function showDialog(row?: any) {
  if (row) {
    editingId.value = row.id
    form.value = {
      name: row.name, hostname: row.hostname, brand: row.brand, model: row.model,
      status: row.status, serial_number: row.serial_number, department: row.department,
      bmc_info: { bmc_ip: row.bmc_info?.bmc_ip || '' },
      hardware_info: {
        cpu_model: row.hardware_info?.cpu_model || '',
        cpu_count: row.hardware_info?.cpu_count ?? 0,
        memory_gb: row.hardware_info?.memory_gb ?? 0,
      },
      software_info: {
        os_name: row.software_info?.os_name || '',
        os_version: row.software_info?.os_version || '',
      },
    }
  } else {
    editingId.value = ''
    form.value = emptyForm()
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    if (editingId.value) {
      await serverApi.update(editingId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await serverApi.create(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } catch { ElMessage.error('操作失败') } finally {
    submitting.value = false
  }
}

async function handleDelete(id: string) {
  try {
    await serverApi.delete(id)
    ElMessage.success('删除成功')
    loadData()
  } catch { ElMessage.error('删除失败') }
}
</script>
