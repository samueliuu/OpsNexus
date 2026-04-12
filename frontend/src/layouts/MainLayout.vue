<template>
  <el-container class="app-layout">
    <el-aside :width="isCollapsed ? '64px' : '220px'" class="app-aside">
      <div class="logo" @click="$router.push('/')">
        <el-icon :size="28" color="#409eff"><Monitor /></el-icon>
        <span v-show="!isCollapsed" class="logo-text">OpsNexus</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapsed"
        router
        background-color="#001529"
        text-color="#ffffffa6"
        active-text-color="#409eff"
      >
        <el-menu-item index="/knowledge/assistant">
          <el-icon><ChatDotRound /></el-icon>
          <template #title>知识助手</template>
        </el-menu-item>
        <el-sub-menu index="knowledge">
          <template #title>
            <el-icon><Collection /></el-icon>
            <span>知识库</span>
          </template>
          <el-menu-item index="/knowledge/sel-codes">SEL 事件码</el-menu-item>
          <el-menu-item index="/knowledge/firmware-matrix">固件矩阵</el-menu-item>
          <el-menu-item index="/knowledge/conversations">对话历史</el-menu-item>
          <el-menu-item index="/knowledge/favorites">我的收藏</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="asset">
          <template #title>
            <el-icon><Box /></el-icon>
            <span>资产管理</span>
          </template>
          <el-menu-item index="/asset/data-centers">数据中心</el-menu-item>
          <el-menu-item index="/asset/racks">机柜管理</el-menu-item>
          <el-menu-item index="/asset/servers">服务器管理</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="monitor">
          <template #title>
            <el-icon><TrendCharts /></el-icon>
            <span>监控告警</span>
          </template>
          <el-menu-item index="/monitor/dashboard">监控概览</el-menu-item>
          <el-menu-item index="/monitor/alert-rules">告警规则</el-menu-item>
          <el-menu-item index="/monitor/alert-events">告警事件</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="outband">
          <template #title>
            <el-icon><Cpu /></el-icon>
            <span>带外管理</span>
          </template>
          <el-menu-item index="/outband/servers">服务器带外</el-menu-item>
          <el-menu-item index="/outband/sel-logs">SEL 日志</el-menu-item>
          <el-menu-item index="/outband/kvm">KVM 会话</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="audit">
          <template #title>
            <el-icon><Document /></el-icon>
            <span>审计日志</span>
          </template>
          <el-menu-item index="/audit/logs">操作日志</el-menu-item>
          <el-menu-item index="/audit/notifications">通知记录</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="system" v-if="authStore.isSuperAdmin || authStore.hasPermission('system', 'read')">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>系统管理</span>
          </template>
          <el-menu-item index="/system/users">用户管理</el-menu-item>
          <el-menu-item index="/system/roles">角色管理</el-menu-item>
          <el-menu-item index="/system/configs">系统配置</el-menu-item>
          <el-menu-item index="/system/channels">通知渠道</el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="app-header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="isCollapsed = !isCollapsed" :size="20">
            <Fold v-if="!isCollapsed" />
            <Expand v-else />
          </el-icon>
        </div>
        <div class="header-right">
          <el-badge :value="alertCount" :hidden="alertCount === 0" :max="99" class="alert-badge">
            <el-icon :size="20" class="header-icon" @click="$router.push('/monitor/alert-events')">
              <Bell />
            </el-icon>
          </el-badge>
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-icon><UserFilled /></el-icon>
              {{ authStore.username }}
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="password">修改密码</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
    <el-dialog v-model="passwordDialogVisible" title="修改密码" width="400px">
      <el-form :model="passwordForm" :rules="passwordRules" ref="passwordFormRef" label-width="80px">
        <el-form-item label="旧密码" prop="old_password">
          <el-input v-model="passwordForm.old_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="passwordForm.new_password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="passwordLoading" @click="handleChangePassword">确定</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api/system'
import { monitorApi } from '@/api/monitor'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const isCollapsed = ref(false)
const alertCount = ref(0)

const activeMenu = computed(() => route.path)

const passwordDialogVisible = ref(false)
const passwordLoading = ref(false)
const passwordFormRef = ref()
const passwordForm = ref({ old_password: '', new_password: '' })
const passwordRules = {
  old_password: [{ required: true, message: '请输入旧密码', trigger: 'blur' }],
  new_password: [{ required: true, min: 8, message: '密码至少8位', trigger: 'blur' }],
}

onMounted(async () => {
  if (authStore.isLoggedIn && !authStore.user) {
    await authStore.fetchUser()
  }
  try {
    const { data } = await monitorApi.alertEvents.stats()
    alertCount.value = (data as any).firing || 0
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.error?.message || e?.message || '获取告警统计失败')
  }
})

function handleCommand(command: string) {
  if (command === 'logout') {
    authStore.logout()
    router.push('/login')
  } else if (command === 'password') {
    passwordForm.value = { old_password: '', new_password: '' }
    passwordDialogVisible.value = true
  }
}

async function handleChangePassword() {
  const valid = await passwordFormRef.value?.validate().catch(() => false)
  if (!valid) return
  if (!authStore.user) { ElMessage.error('用户信息未加载'); return }
  passwordLoading.value = true
  try {
    await authApi.changePassword(authStore.user.id, passwordForm.value)
    ElMessage.success('密码修改成功，请重新登录')
    passwordDialogVisible.value = false
    authStore.logout()
    router.push('/login')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.error?.message || e?.message || '密码修改失败')
  } finally {
    passwordLoading.value = false
  }
}
</script>

<style scoped>
.app-layout { height: 100vh; }
.app-aside {
  background: #001529;
  transition: width 0.3s;
  overflow: hidden;
}
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  cursor: pointer;
  border-bottom: 1px solid #ffffff1a;
}
.logo-text {
  color: #fff;
  font-size: 18px;
  font-weight: 700;
  white-space: nowrap;
}
.app-header {
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 60px;
}
.header-left { display: flex; align-items: center; }
.collapse-btn { cursor: pointer; color: #333; }
.header-right { display: flex; align-items: center; gap: 20px; }
.header-icon { cursor: pointer; color: #666; }
.alert-badge { line-height: 1; }
.user-info {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: #333;
  font-size: 14px;
}
.app-main {
  background: #f0f2f5;
  overflow-y: auto;
  padding: 20px;
}
.el-menu { border-right: none; }
</style>
