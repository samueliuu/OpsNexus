<template>
  <div class="min-h-screen flex items-center justify-center bg-surface-50 dark:bg-surface-950 px-4">
    <div class="w-full max-w-sm">
      <div class="bg-surface-0 dark:bg-surface-900 p-8 rounded-border shadow-[0_2px_8px_rgba(0,0,0,0.08)] border border-surface-200 dark:border-surface-700">
        <div class="text-center mb-6">
          <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-4">
            <i class="pi pi-desktop text-primary text-3xl"></i>
          </div>
          <h1 class="text-2xl font-bold text-surface-900 dark:text-surface-0 mb-1">OpsNexus</h1>
          <p class="text-muted-color text-sm">衡驭智能服务器运维系统</p>
        </div>

        <form @submit.prevent="handleLogin">
          <div class="mb-5">
            <label for="username" class="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-2">用户名</label>
            <InputText
              id="username"
              v-model="form.username"
              placeholder="请输入用户名"
              class="w-full"
              :class="{ 'p-invalid': errors.username }"
            />
            <small v-if="errors.username" class="p-error">{{ errors.username }}</small>
          </div>

          <div class="mb-5">
            <label for="password" class="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-2">密码</label>
            <Password
              id="password"
              v-model="form.password"
              placeholder="请输入密码"
              :feedback="false"
              toggleMask
              class="w-full"
              :class="{ 'p-invalid': errors.password }"
              @keyup.enter="handleLogin"
            />
            <small v-if="errors.password" class="p-error">{{ errors.password }}</small>
          </div>

          <Button
            label="登 录"
            icon="pi pi-arrow-right"
            iconPos="right"
            :loading="loading"
            class="w-full"
            @click="handleLogin"
          />
        </form>

        <div class="mt-5 text-center">
          <span class="text-muted-color text-sm">还没有账号？</span>
          <router-link to="/register" class="text-primary font-medium text-sm hover:underline ml-1">立即注册</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToast } from 'primevue/usetoast'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Button from 'primevue/button'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const toast = useToast()
const loading = ref(false)
const errors = reactive({ username: '', password: '' })

const form = reactive({ username: '', password: '' })

function validate() {
  let valid = true
  errors.username = ''
  errors.password = ''
  if (!form.username) { errors.username = '请输入用户名'; valid = false }
  if (!form.password) { errors.password = '请输入密码'; valid = false }
  return valid
}

const handleLogin = async () => {
  if (!validate()) return
  loading.value = true
  try {
    await authStore.login(form.username, form.password)
    toast.add({ severity: 'success', summary: '成功', detail: '登录成功', life: 2000 })
    const redirect = (route.query.redirect as string) || '/knowledge/assistant'
    router.push(redirect)
  } catch {
    toast.add({ severity: 'error', summary: '失败', detail: '登录失败，请检查用户名和密码', life: 3000 })
  } finally {
    loading.value = false
  }
}
</script>
