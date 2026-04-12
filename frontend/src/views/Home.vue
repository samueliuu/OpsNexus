<template>
  <div class="home">
    <el-container>
      <el-header>
        <h1>OpsNexus</h1>
        <p>统一服务器运维平台</p>
      </el-header>
      <el-main>
        <el-row :gutter="20">
          <el-col :span="8" v-for="module in modules" :key="module.name">
            <el-card class="module-card">
              <template #header>
                <div class="card-header">
                  <el-icon :size="24">
                    <component :is="module.icon" />
                  </el-icon>
                  <span>{{ module.name }}</span>
                </div>
              </template>
              <p>{{ module.description }}</p>
              <el-button type="primary" @click="navigateTo(module.path)">
                进入
              </el-button>
            </el-card>
          </el-col>
        </el-row>
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const modules = [
  {
    name: '系统管理',
    description: '用户、角色、权限管理',
    icon: 'Setting',
    path: '/system/users',
  },
  {
    name: '资产管理',
    description: '数据中心、机架、服务器管理',
    icon: 'Box',
    path: '/asset/servers',
  },
  {
    name: '监控告警',
    description: '指标监控、告警规则、告警事件',
    icon: 'TrendCharts',
    path: '/monitor/dashboard',
  },
  {
    name: '带外管理',
    description: 'BMC 管理、电源控制、KVM',
    icon: 'Monitor',
    path: '/outband/servers',
  },
  {
    name: '自动化运维',
    description: '任务编排、固件升级、巡检',
    icon: 'Tools',
    path: '/autoops/tasks',
  },
  {
    name: '审计日志',
    description: '操作审计、通知记录',
    icon: 'Document',
    path: '/audit/logs',
  },
]

const navigateTo = (path: string) => {
  router.push(path)
}
</script>

<style scoped>
.home {
  min-height: 100vh;
  background: #f5f7fa;
}

.el-header {
  background: #409eff;
  color: white;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 20px;
}

.el-header h1 {
  margin: 0;
  font-size: 32px;
}

.el-header p {
  margin: 10px 0 0;
  font-size: 16px;
  opacity: 0.9;
}

.el-main {
  padding: 40px;
}

.module-card {
  margin-bottom: 20px;
  cursor: pointer;
  transition: transform 0.2s;
}

.module-card:hover {
  transform: translateY(-5px);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: bold;
}
</style>
