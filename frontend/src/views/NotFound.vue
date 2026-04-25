<template>
  <div class="not-found">
    <i class="pi pi-exclamation-circle" style="font-size: 5rem; color: #9ca3af"></i>
    <h1>404</h1>
    <p>页面未找到</p>
    <Button label="返回首页" icon="pi pi-home" @click="$router.push('/')" />
  </div>
</template>

<script setup lang="ts">
import Button from 'primevue/button'
</script>

<style scoped>
.not-found {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 60vh;
  gap: 8px;
}
.not-found h1 {
  font-size: 72px;
  color: #9ca3af;
  margin: 0;
}
.not-found p {
  font-size: 18px;
  color: #9ca3af;
  margin: 0 0 16px;
}
</style>
