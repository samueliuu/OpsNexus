<template>
  <div class="min-h-screen flex items-center justify-center bg-surface-50 dark:bg-surface-950 px-4 py-8">
    <div class="w-full max-w-md">
      <div class="bg-surface-0 dark:bg-surface-900 p-8 rounded-border shadow-[0_2px_8px_rgba(0,0,0,0.08)] border border-surface-200 dark:border-surface-700">
        <div class="text-center mb-6">
          <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-4">
            <i class="pi pi-desktop text-primary text-3xl"></i>
          </div>
          <h1 class="text-2xl font-bold text-surface-900 dark:text-surface-0 mb-1">创建账号</h1>
          <p class="text-muted-color text-sm">注册以开始使用运维平台</p>
        </div>

        <div v-if="step === 0" class="role-select-section">
          <label class="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-3">选择角色</label>
          <div class="grid grid-cols-2 gap-4 mb-5">
            <div
              class="role-card cursor-pointer p-4 rounded-border border-2 transition-all"
              :class="form.user_type === 'owner' ? 'border-primary bg-primary/5' : 'border-surface-200 dark:border-surface-700 hover:border-primary/50'"
              @click="form.user_type = 'owner'"
            >
              <i class="pi pi-building text-2xl mb-2 block" :class="form.user_type === 'owner' ? 'text-primary' : 'text-muted-color'"></i>
              <h3 class="font-semibold text-sm text-surface-900 dark:text-surface-0">甲方 · 数据中心管理员</h3>
              <p class="text-xs text-muted-color mt-1">管理数据中心，获取运维知识指导</p>
            </div>
            <div
              class="role-card cursor-pointer p-4 rounded-border border-2 transition-all"
              :class="form.user_type === 'provider' ? 'border-primary bg-primary/5' : 'border-surface-200 dark:border-surface-700 hover:border-primary/50'"
              @click="form.user_type = 'provider'"
            >
              <i class="pi pi-user text-2xl mb-2 block" :class="form.user_type === 'provider' ? 'text-primary' : 'text-muted-color'"></i>
              <h3 class="font-semibold text-sm text-surface-900 dark:text-surface-0">乙方 · IT工程师</h3>
              <p class="text-xs text-muted-color mt-1">提供技术服务，获取技术资料支持</p>
            </div>
          </div>
          <Button label="下一步" icon="pi pi-arrow-right" iconPos="right" class="w-full" @click="step = 1" />
        </div>

        <form v-if="step === 1" @submit.prevent="handleRegister">
          <div class="mb-4">
            <label for="username" class="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-2">
              用户名 <span class="text-red-500">*</span>
            </label>
            <InputText id="username" v-model="form.username" placeholder="3-64位，字母数字下划线" class="w-full" />
          </div>

          <div class="mb-4">
            <label for="email" class="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-2">
              邮箱 <span class="text-red-500">*</span>
            </label>
            <InputText id="email" v-model="form.email" type="email" placeholder="用于找回密码" class="w-full" />
          </div>

          <div class="mb-4">
            <label for="password" class="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-2">
              密码 <span class="text-red-500">*</span>
            </label>
            <Password id="password" v-model="form.password" toggleMask placeholder="至少8位" class="w-full" />
          </div>

          <div class="mb-4">
            <label for="confirmPassword" class="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-2">
              确认密码 <span class="text-red-500">*</span>
            </label>
            <Password id="confirmPassword" v-model="form.confirmPassword" :feedback="false" toggleMask placeholder="再次输入密码" class="w-full" />
          </div>

          <div class="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label for="fullName" class="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-2">姓名</label>
              <InputText id="fullName" v-model="form.full_name" placeholder="选填" class="w-full" />
            </div>
            <div>
              <label for="phone" class="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-2">手机号</label>
              <InputText id="phone" v-model="form.phone" placeholder="选填" class="w-full" />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4 mb-5">
            <div>
              <label for="company" class="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-2">公司/单位</label>
              <InputText id="company" v-model="form.company" placeholder="选填" class="w-full" />
            </div>
            <div>
              <label for="title" class="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-2">职位</label>
              <InputText id="title" v-model="form.title" placeholder="选填" class="w-full" />
            </div>
          </div>

          <div class="flex gap-3">
            <Button label="上一步" severity="secondary" outlined @click="step = 0" />
            <Button label="注 册" :loading="loading" class="flex-1" @click="handleRegister" />
          </div>
        </form>

        <div v-if="step === 2" class="success-step text-center py-6">
          <i class="pi pi-check-circle text-success text-5xl mb-4 block"></i>
          <h2 class="text-xl font-bold text-surface-900 dark:text-surface-0 mb-2">注册成功</h2>
          <p class="text-muted-color text-sm mb-5">欢迎加入 OpsNexus，现在可以登录了</p>
          <Button label="去登录" icon="pi pi-sign-in" @click="$router.push('/login')" />
        </div>

        <div v-if="step < 2" class="mt-5 text-center">
          <span class="text-muted-color text-sm">已有账号？</span>
          <router-link to="/login" class="text-primary font-medium text-sm hover:underline ml-1">去登录</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { authApi } from '@/api/system'
import { useToast } from 'primevue/usetoast'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Button from 'primevue/button'

const toast = useToast()
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

const handleRegister = async () => {
  if (!form.username || !form.email || !form.password || !form.confirmPassword) {
    toast.add({ severity: 'warn', summary: '提示', detail: '请填写必填项', life: 3000 })
    return
  }
  if (form.username.length < 3 || form.username.length > 64) {
    toast.add({ severity: 'warn', summary: '提示', detail: '用户名需3-64位字符', life: 3000 })
    return
  }
  if (!/^[a-zA-Z0-9_]+$/.test(form.username)) {
    toast.add({ severity: 'warn', summary: '提示', detail: '用户名只能包含字母、数字和下划线', life: 3000 })
    return
  }
  if (form.password.length < 8) {
    toast.add({ severity: 'warn', summary: '提示', detail: '密码至少8位', life: 3000 })
    return
  }
  if (form.confirmPassword !== form.password) {
    toast.add({ severity: 'warn', summary: '提示', detail: '两次输入密码不一致', life: 3000 })
    return
  }
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
    toast.add({ severity: 'success', summary: '成功', detail: '注册成功', life: 3000 })
  } catch (err: any) {
    const msg = err?.response?.data?.detail || '注册失败，请稍后重试'
    toast.add({ severity: 'error', summary: '失败', detail: msg, life: 3000 })
  } finally {
    loading.value = false
  }
}
</script>
