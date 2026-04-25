<template>
  <div class="home">
    <div class="home-hero">
      <div class="hero-content">
        <div class="hero-icon">
          <i class="pi pi-desktop"></i>
        </div>
        <h1>OpsNexus</h1>
        <p>统一服务器运维平台</p>
      </div>
    </div>
    <div class="home-content">
      <div class="content-grid-3">
        <Card v-for="mod in modules" :key="mod.name" class="module-card" @click="navigateTo(mod.path)">
          <template #content>
            <div class="module-icon" :style="{ background: mod.bg }">
              <i :class="mod.icon" :style="{ color: mod.color }"></i>
            </div>
            <h3>{{ mod.name }}</h3>
            <p>{{ mod.description }}</p>
            <Button label="进入" link icon="pi pi-arrow-right" iconPos="right" class="module-link" />
          </template>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import Card from 'primevue/card'
import Button from 'primevue/button'

const router = useRouter()

const modules = [
  { name: '系统管理', description: '用户、角色、权限管理', icon: 'pi pi-cog', color: 'var(--brand-primary)', bg: 'rgba(37,99,235,0.08)', path: '/system/users' },
  { name: '资产管理', description: '数据中心、机架、服务器管理', icon: 'pi pi-box', color: 'var(--brand-accent)', bg: 'rgba(6,182,212,0.08)', path: '/asset/servers' },
  { name: '监控告警', description: '指标监控、告警规则、告警事件', icon: 'pi pi-chart-line', color: 'var(--warning)', bg: 'rgba(245,158,11,0.08)', path: '/monitor/dashboard' },
  { name: '带外管理', description: 'BMC 管理、电源控制、KVM', icon: 'pi pi-desktop', color: 'var(--success)', bg: 'rgba(16,185,129,0.08)', path: '/outband/servers' },
  { name: '知识助手', description: 'AI 运维知识问答', icon: 'pi pi-comment', color: 'var(--p-purple-500)', bg: 'rgba(139,92,246,0.08)', path: '/knowledge/assistant' },
  { name: '审计日志', description: '操作审计、通知记录', icon: 'pi pi-file', color: 'var(--text-secondary)', bg: 'rgba(71,85,105,0.08)', path: '/audit/logs' },
]

const navigateTo = (path: string) => {
  router.push(path)
}
</script>

<style scoped>
.home { min-height: 100vh; background: var(--main-bg); }
.home-hero {
  background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #1d4ed8 100%);
  padding: 3rem 2rem;
  display: flex;
  justify-content: center;
}
.hero-content {
  text-align: center;
  color: var(--text-inverse);
}
.hero-icon {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-xl);
  background: rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1rem;
}
.hero-icon i {
  font-size: 1.5rem;
  color: var(--brand-accent);
}
.hero-content h1 {
  font-size: 2rem;
  font-weight: 700;
  margin: 0 0 0.25rem;
  letter-spacing: -0.02em;
}
.hero-content p {
  font-size: 1rem;
  opacity: 0.7;
  margin: 0;
}
.home-content { padding: 2rem; }
.module-card {
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}
.module-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg) !important;
}
.module-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 0.75rem;
}
.module-icon i {
  font-size: 1.25rem;
}
.module-card h3 {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 0.25rem;
}
.module-card p {
  font-size: 0.8125rem;
  color: var(--text-muted);
  margin: 0 0 0.75rem;
}
.module-link {
  padding: 0 !important;
  font-size: 0.8125rem !important;
}
</style>
