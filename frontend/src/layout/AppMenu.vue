<script setup>
import { ref, computed } from 'vue';
import AppMenuItem from './AppMenuItem.vue';
import { useAuthStore } from '@/stores/auth';

const authStore = useAuthStore();

const model = computed(() => [
    {
        label: '知识助手',
        items: [
            {
                label: '知识助手',
                icon: 'pi pi-fw pi-comment',
                to: '/knowledge/assistant'
            }
        ]
    },
    {
        label: '知识库',
        icon: 'pi pi-fw pi-book',
        path: '/knowledge',
        items: [
            {
                label: 'SEL 事件码',
                icon: 'pi pi-fw pi-code',
                to: '/knowledge/sel-codes'
            },
            {
                label: '固件矩阵',
                icon: 'pi pi-fw pi-th-large',
                to: '/knowledge/firmware-matrix'
            },
            {
                label: '对话历史',
                icon: 'pi pi-fw pi-history',
                to: '/knowledge/conversations'
            },
            {
                label: '我的收藏',
                icon: 'pi pi-fw pi-heart',
                to: '/knowledge/favorites'
            }
        ]
    },
    {
        label: '资产管理',
        icon: 'pi pi-fw pi-box',
        path: '/asset',
        items: [
            {
                label: '数据中心',
                icon: 'pi pi-fw pi-building',
                to: '/asset/data-centers'
            },
            {
                label: '机柜管理',
                icon: 'pi pi-fw pi-arrows-alt',
                to: '/asset/racks'
            },
            {
                label: '服务器管理',
                icon: 'pi pi-fw pi-server',
                to: '/asset/servers'
            }
        ]
    },
    {
        label: '监控告警',
        icon: 'pi pi-fw pi-chart-line',
        path: '/monitor',
        items: [
            {
                label: '监控概览',
                icon: 'pi pi-fw pi-gauge',
                to: '/monitor/dashboard'
            },
            {
                label: '告警规则',
                icon: 'pi pi-fw pi-sliders-h',
                to: '/monitor/alert-rules'
            },
            {
                label: '告警事件',
                icon: 'pi pi-fw pi-exclamation-triangle',
                to: '/monitor/alert-events'
            }
        ]
    },
    {
        label: '带外管理',
        icon: 'pi pi-fw pi-microchip',
        path: '/outband',
        items: [
            {
                label: '服务器带外',
                icon: 'pi pi-fw pi-server',
                to: '/outband/servers'
            },
            {
                label: 'SEL 日志',
                icon: 'pi pi-fw pi-file-edit',
                to: '/outband/sel-logs'
            },
            {
                label: 'KVM 会话',
                icon: 'pi pi-fw pi-desktop',
                to: '/outband/kvm'
            }
        ]
    },
    {
        label: '审计日志',
        icon: 'pi pi-fw pi-file',
        path: '/audit',
        items: [
            {
                label: '操作日志',
                icon: 'pi pi-fw pi-list',
                to: '/audit/logs'
            },
            {
                label: '通知记录',
                icon: 'pi pi-fw pi-bell',
                to: '/audit/notifications'
            }
        ]
    },
    ...(authStore.isSuperAdmin || authStore.hasPermission('system', 'read')
        ? [{
            label: '系统管理',
            icon: 'pi pi-fw pi-cog',
            path: '/system',
            items: [
                {
                    label: '用户管理',
                    icon: 'pi pi-fw pi-user-edit',
                    to: '/system/users'
                },
                {
                    label: '角色管理',
                    icon: 'pi pi-fw pi-users',
                    to: '/system/roles'
                },
                {
                    label: '系统配置',
                    icon: 'pi pi-fw pi-wrench',
                    to: '/system/configs'
                },
                {
                    label: '通知渠道',
                    icon: 'pi pi-fw pi-send',
                    to: '/system/channels'
                }
            ]
        }]
        : [])
]);
</script>

<template>
    <ul class="layout-menu">
        <template v-for="(item, i) in model" :key="item">
            <app-menu-item v-if="!item.separator" :item="item" :index="i"></app-menu-item>
            <li v-if="item.separator" class="menu-separator"></li>
        </template>
    </ul>
</template>

<style lang="scss" scoped></style>
