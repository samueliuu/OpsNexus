<script setup>
import { useLayout } from '@/layout/composables/layout'
import AppConfigurator from './AppConfigurator.vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { ref } from 'vue'

const { toggleMenu, toggleDarkMode, isDarkTheme } = useLayout()
const authStore = useAuthStore()
const router = useRouter()
const userMenu = ref()

const userMenuItems = [
    { label: '修改密码', icon: 'pi pi-key', command: () => {} },
    { separator: true },
    { label: '退出登录', icon: 'pi pi-sign-out', command: handleLogout }
]

function handleLogout() {
    authStore.logout()
}

function toggleUserMenu(event) {
    userMenu.value.toggle(event)
}
</script>

<template>
    <div class="layout-topbar">
        <div class="layout-topbar-logo-container">
            <button class="layout-menu-button layout-topbar-action" @click="toggleMenu">
                <i class="pi pi-bars"></i>
            </button>
            <router-link to="/" class="layout-topbar-logo">
                <div>
                    <span class="text-xl font-bold">OpsNexus</span>
                    <small class="block text-xs opacity-60" style="margin-top: -2px;">衡驭智能服务器运维系统</small>
                </div>
            </router-link>
        </div>

        <div class="layout-topbar-actions">
            <div class="layout-config-menu">
                <button type="button" class="layout-topbar-action" @click="toggleDarkMode">
                    <i :class="['pi', { 'pi-moon': isDarkTheme, 'pi-sun': !isDarkTheme }]"></i>
                </button>
                <div class="relative">
                    <button
                        v-styleclass="{ selector: '@next', enterFromClass: 'hidden', enterActiveClass: 'p-anchored-overlay-enter-active', leaveToClass: 'hidden', leaveActiveClass: 'p-anchored-overlay-leave-active', hideOnOutsideClick: true }"
                        type="button"
                        class="layout-topbar-action layout-topbar-action-highlight"
                    >
                        <i class="pi pi-palette"></i>
                    </button>
                    <AppConfigurator />
                </div>
            </div>

            <button
                class="layout-topbar-menu-button layout-topbar-action"
                v-styleclass="{ selector: '@next', enterFromClass: 'hidden', enterActiveClass: 'p-anchored-overlay-enter-active', leaveToClass: 'hidden', leaveActiveClass: 'p-anchored-overlay-leave-active', hideOnOutsideClick: true }"
            >
                <i class="pi pi-ellipsis-v"></i>
            </button>

            <div class="layout-topbar-menu hidden lg:block">
                <div class="layout-topbar-menu-content">
                    <AppMenu ref="userMenu" :model="userMenuItems" :popup="true">
                        <template #item="{ item, props }">
                            <a v-ripple class="flex items-center px-4 py-2 cursor-pointer hover:bg-surface-100 dark:hover:bg-surface-800 rounded-none border-none bg-transparent text-surface-700 dark:text-surface-0 w-full" v-bind="props.action" @click="item.command">
                                <i :class="item.icon" class="mr-2"></i>
                                <span>{{ item.label }}</span>
                            </a>
                        </template>
                    </AppMenu>
                    <button type="button" class="layout-topbar-action">
                        <i class="pi pi-user"></i>
                        <span>{{ authStore.username || '用户' }}</span>
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>
