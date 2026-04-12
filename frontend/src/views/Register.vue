<template>
  <div class="register-container">
    <el-card class="register-card">
      <template #header>
        <h2>OpsNexus 注册</h2>
        <p class="subtitle">服务器运维知识助手平台</p>
      </template>
      <el-steps :active="step" align-center class="register-steps" finish-status="success">
        <el-step title="选择角色" />
        <el-step title="填写信息" />
        <el-step title="完成" />
      </el-steps>

      <div v-if="step === 0" class="step-content">
        <div class="role-select">
          <div
            class="role-card"
            :class="{ active: form.user_type === 'owner' }"
            @click="form.user_type = 'owner'"
          >
            <el-icon :size="48"><OfficeBuilding /></el-icon>
            <h3>甲方 · 数据中心管理员</h3>
            <p>管理数据中心，获取运维知识指导</p>
          </div>
          <div
            class="role-card"
            :class="{ active: form.user_type === 'provider' }"
            @click="form.user_type = 'provider'"
          >
            <el-icon :size="48"><User /></el-icon>
            <h3>乙方 · IT工程师</h3>
            <p>提供技术服务，获取技术资料支持</p>
          </div>
        </div>
        <el-button type="primary" size="large" style="width: 100%; margin-top: 24px" @click="step = 1">下一步</el-button>
      </div>

      <div v-if="step === 1" class="step-content">
        <el-form :model="form" :rules="rules" ref="formRef" label-position="top">
          <el-form-item label="用户名" prop="username">
            <el-input v-model="form.username" placeholder="3-64位，字母数字下划线" prefix-icon="User" size="large" />
          </el-form-item>
          <el-form-item label="邮箱" prop="email">
            <el-input v-model="form.email" placeholder="用于找回密码" prefix-icon="Message" size="large" />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input v-model="form.password" type="password" placeholder="至少8位" prefix-icon="Lock" size="large" show-password />
          </el-form-item>
          <el-form-item label="确认密码" prop="confirmPassword">
            <el-input v-model="form.confirmPassword" type="password" placeholder="再次输入密码" prefix-icon="Lock" size="large" show-password />
          </el-form-item>
          <el-form-item label="姓名" prop="full_name">
            <el-input v-model="form.full_name" placeholder="真实姓名（选填）" size="large" />
          </el-form-item>
          <el-form-item label="手机号" prop="phone">
            <el-input v-model="form.phone" placeholder="手机号（选填）" size="large" />
          </el-form-item>
          <el-form-item label="公司/单位" prop="company">
            <el-input v-model="form.company" placeholder="所在公司或单位（选填）" size="large" />
          </el-form-item>
          <el-form-item label="职位" prop="title">
            <el-input v-model="form.title" placeholder="职位（选填）" size="large" />
          </el-form-item>
          <div style="display: flex; gap: 12px; margin-top: 8px">
            <el-button size="large" style="flex: 1" @click="step = 0">上一步</el-button>
            <el-button type="primary" size="large" :loading="loading" style="flex: 2" @click="handleRegister">注册</el-button>
          </div>
        </el-form>
      </div>

      <div v-if="step === 2" class="step-content success-step">
        <el-result icon="success" title="注册成功" sub-title="欢迎加入 OpsNexus，现在可以登录了">
          <template #extra>
            <el-button type="primary" size="large" @click="$router.push('/login')">去登录</el-button>
          </template>
        </el-result>
      </div>

      <div v-if="step < 2" class="login-link">
        已有账号？<router-link to="/login">去登录</router-link>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { authApi } from '@/api/system'
import { ElMessage } from 'element-plus'
import { OfficeBuilding, User } from '@element-plus/icons-vue'
const formRef = ref()
const loading = ref(false)
const step = ref(0)

const form = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  full_name: '',
  phone: '',
  user_type: 'owner',
  company: '',
  title: '',
})

const validateConfirmPassword = (_rule: any, value: string, callback: Function) => {
  if (value !== form.password) {
    callback(new Error('两次输入密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 64, message: '3-64位字符', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]+$/, message: '只能包含字母、数字和下划线', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email' as const, message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, max: 128, message: '密码至少8位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' },
  ],
}

const handleRegister = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await authApi.register({
      username: form.username,
      email: form.email,
      password: form.password,
      full_name: form.full_name || undefined,
      phone: form.phone || undefined,
      user_type: form.user_type,
      company: form.company || undefined,
      title: form.title || undefined,
    })
    step.value = 2
    ElMessage.success('注册成功')
  } catch (err: any) {
    const msg = err?.response?.data?.detail || '注册失败，请稍后重试'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-container {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}
.register-card {
  width: 520px;
  max-width: 100%;
}
.register-card h2 {
  text-align: center;
  margin: 0;
  color: #303133;
}
.subtitle {
  text-align: center;
  color: #909399;
  margin: 8px 0 0;
  font-size: 14px;
}
.register-steps {
  margin: 20px 0;
}
.step-content {
  min-height: 200px;
}
.role-select {
  display: flex;
  gap: 16px;
  margin-top: 16px;
}
.role-card {
  flex: 1;
  border: 2px solid #e4e7ed;
  border-radius: 12px;
  padding: 24px 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
}
.role-card:hover {
  border-color: #409eff;
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.15);
}
.role-card.active {
  border-color: #409eff;
  background: #ecf5ff;
}
.role-card h3 {
  margin: 12px 0 8px;
  font-size: 16px;
  color: #303133;
}
.role-card p {
  margin: 0;
  font-size: 13px;
  color: #909399;
}
.success-step {
  display: flex;
  justify-content: center;
}
.login-link {
  text-align: center;
  margin-top: 16px;
  color: #909399;
  font-size: 14px;
}
.login-link a {
  color: #409eff;
  text-decoration: none;
}
</style>
