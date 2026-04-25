import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwind from '@tailwindcss/vite'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue(), tailwind()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  optimizeDeps: {
    include: [
      'primevue/message',
      'primevue/tree',
      'primevue/card',
      'primevue/button',
      'primevue/datatable',
      'primevue/column',
      'primevue/dialog',
      'primevue/tag',
      'primevue/inputtext',
      'primevue/password',
      'primevue/select',
      'primevue/textarea',
      'primevue/inputnumber',
      'primevue/inputswitch',
      'primevue/progressbar',
      'primevue/paginator',
      'primevue/accordion',
      'primevue/accordionpanel',
      'primevue/accordionheader',
      'primevue/accordioncontent',
      'primevue/avatar',
      'primevue/tabview',
      'primevue/tabpanel',
      'primevue/progressspinner',
      'primevue/confirmdialog',
      'primevue/iconfield',
      'primevue/inputicon',
      'primevue/toast',
      'primevue/menu',
      'primevue/selectbutton',
      'primevue/config',
      'primevue/toastservice',
      'primevue/confirmationservice',
      'primevue/usetoast',
      'primevue/useconfirm',
      'primevue/styleclass',
      'primevue/ripple',
    ],
  },
  server: {
    port: 3000,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor': ['vue', 'vue-router', 'pinia'],
          'primevue': ['primevue'],
          'echarts': ['echarts'],
        },
      },
    },
  },
})
