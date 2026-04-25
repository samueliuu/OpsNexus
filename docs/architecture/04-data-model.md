# 数据模型

## 模型总览

系统共 27 张数据表，按模块划分为 7 个领域：

```
┌─────────────────────────────────────────────────────────┐
│                    System 模块 (7 表)                     │
│  users, roles, permissions, user_roles, role_permissions │
│  system_configs, notification_channels                   │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│                    Asset 模块 (4 表)                      │
│  data_centers, racks, servers, bmc_credentials           │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│                   Monitor 模块 (4 表)                     │
│  metric_definitions, metric_data, alert_rules            │
│  alert_events                                            │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│                   Outband 模块 (3 表)                     │
│  sel_logs, firmware_inventory, kvm_sessions              │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│                   AutoOps 模块 (5 表)                     │
│  task_definitions, task_instances, task_step_logs        │
│  firmware_packages, inspection_policies                  │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│                   Audit 模块 (2 表)                       │
│  audit_logs, notification_logs                           │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│                  Knowledge 模块 (5 表)                    │
│  conversations, conversation_messages, knowledge_favorites│
│  sel_event_codes, firmware_compatibility                 │
└─────────────────────────────────────────────────────────┘
```

## System 模块

### users

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 用户 ID |
| username | String(64) | UNIQUE, NOT NULL | 用户名 |
| email | String(255) | UNIQUE, NOT NULL | 邮箱 |
| password_hash | String(255) | NOT NULL | bcrypt 密码哈希 |
| full_name | String(64) | | 姓名 |
| phone | String(20) | | 手机号 |
| department | String(64) | | 部门 |
| company | String(128) | | 公司 |
| title | String(64) | | 职位 |
| user_type | String(20) | | 用户类型（owner/provider） |
| is_active | Boolean | DEFAULT true | 是否启用 |
| is_superuser | Boolean | DEFAULT false | 是否超级管理员 |
| created_at | DateTime | | 创建时间 |
| updated_at | DateTime | | 更新时间 |

### roles

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 角色 ID |
| name | String(64) | NOT NULL | 角色名称 |
| code | String(64) | UNIQUE, NOT NULL | 角色编码 |
| description | Text | | 描述 |
| is_builtin | Boolean | DEFAULT false | 是否内置角色 |
| data_scope | String(20) | | 数据范围（all/data_center/department/custom） |
| created_at | DateTime | | 创建时间 |
| updated_at | DateTime | | 更新时间 |

### permissions

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 权限 ID |
| code | String(128) | UNIQUE, NOT NULL | 权限编码（如 system:user:read） |
| name | String(128) | NOT NULL | 权限名称 |
| resource | String(64) | NOT NULL | 资源类型 |
| action | String(20) | NOT NULL | 操作类型（read/write/execute/delete） |

### user_roles（关联表）

| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | UUID | FK → users.id |
| role_id | UUID | FK → roles.id |

### role_permissions（关联表）

| 字段 | 类型 | 说明 |
|------|------|------|
| role_id | UUID | FK → roles.id |
| permission_id | UUID | FK → permissions.id |

### system_configs

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 配置 ID |
| key | String(128) | UNIQUE, NOT NULL | 配置键 |
| value | Text | | 配置值 |
| value_type | String(20) | DEFAULT 'string' | 值类型（string/int/bool/json） |
| is_sensitive | Boolean | DEFAULT false | 是否敏感（前端显示为 ******） |
| description | Text | | 描述 |
| created_at | DateTime | | 创建时间 |
| updated_at | DateTime | | 更新时间 |

### notification_channels

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 渠道 ID |
| name | String(64) | NOT NULL | 渠道名称 |
| channel_type | String(20) | NOT NULL | 渠道类型（email/webhook/dingtalk/wecom/lark） |
| config | JSON | | 渠道配置 |
| is_enabled | Boolean | DEFAULT true | 是否启用 |
| created_at | DateTime | | 创建时间 |
| updated_at | DateTime | | 更新时间 |

## Asset 模块

### data_centers

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 数据中心 ID |
| name | String(128) | NOT NULL | 名称 |
| code | String(64) | UNIQUE, NOT NULL | 编码 |
| location | String(255) | | 位置 |
| contact_name | String(64) | | 联系人 |
| contact_phone | String(20) | | 联系电话 |
| description | Text | | 描述 |
| is_active | Boolean | DEFAULT true | 是否启用 |
| created_at | DateTime | | 创建时间 |
| updated_at | DateTime | | 更新时间 |

### racks

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 机柜 ID |
| data_center_id | UUID | FK → data_centers.id | 所属数据中心 |
| name | String(128) | NOT NULL | 名称 |
| code | String(64) | NOT NULL | 编码（联合唯一：data_center_id + code） |
| location | String(255) | | 位置 |
| u_height | Integer | DEFAULT 42 | U 高 |
| description | Text | | 描述 |
| is_active | Boolean | DEFAULT true | 是否启用 |
| created_at | DateTime | | 创建时间 |
| updated_at | DateTime | | 更新时间 |

### servers

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 服务器 ID |
| rack_id | UUID | FK → racks.id | 所属机柜 |
| name | String(128) | NOT NULL | 名称 |
| hostname | String(255) | UNIQUE | 主机名 |
| serial_number | String(128) | | 序列号 |
| asset_tag | String(128) | UNIQUE | 资产标签 |
| brand | String(64) | | 品牌（dell/hpe/lenovo/huawei/inspur/h3c/sugon/xfusion） |
| model | String(128) | | 型号 |
| status | String(20) | DEFAULT 'active' | 状态（active/inactive/maintenance/retired） |
| server_type | String(20) | DEFAULT 'physical' | 类型（physical/virtual/blade） |
| cpu_model | String(128) | | CPU 型号 |
| cpu_count | Integer | | CPU 数量 |
| cpu_cores_per_socket | Integer | | 每颗 CPU 核心数 |
| memory_gb | Integer | | 内存（GB） |
| disk_info | JSON | | 磁盘信息 |
| network_interfaces | JSON | | 网络接口信息 |
| os_name | String(128) | | 操作系统名称 |
| os_version | String(64) | | 操作系统版本 |
| bmc_ip | INET | UNIQUE | BMC IP 地址 |
| bmc_mac | String(17) | | BMC MAC 地址 |
| bmc_status | String(20) | DEFAULT 'unknown' | BMC 状态（online/offline/unknown/error） |
| bmc_unreachable | DateTime | | BMC 不可达时间 |
| rack_position | Integer | | 机柜 U 位 |
| rack_height | Integer | | 占用 U 数 |
| owner_id | UUID | FK → users.id | 负责人 |
| department | String(64) | | 部门 |
| metadata | JSON | | 扩展元数据 |
| created_at | DateTime | | 创建时间 |
| updated_at | DateTime | | 更新时间 |

### bmc_credentials

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 凭据 ID |
| server_id | UUID | UNIQUE, FK → servers.id | 关联服务器 |
| username | String(64) | NOT NULL | BMC 用户名 |
| encrypted_password | String(512) | NOT NULL | Fernet 加密密码 |
| encryption_key_id | String(64) | | 加密密钥标识 |
| protocol | String(20) | DEFAULT 'redfish' | 协议（redfish/ipmi/snmp） |
| port | Integer | | 端口 |
| is_default | Boolean | DEFAULT true | 是否默认凭据 |
| created_at | DateTime | | 创建时间 |
| updated_at | DateTime | | 更新时间 |

## Monitor 模块

### metric_definitions

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 指标 ID |
| name | String(128) | UNIQUE, NOT NULL | 指标名称（如 temperature_celsius__cpu1） |
| display_name | String(128) | | 显示名称 |
| unit | String(32) | | 单位（°C / % / W / RPM） |
| metric_type | String(20) | | 类型（gauge/counter/histogram） |
| data_type | String(20) | DEFAULT 'float' | 数据类型（float/int/bool） |
| labels | JSON | | 标签 |
| collection_method | String(20) | | 采集方式（bmc/snmp/agent） |
| default_interval | Integer | DEFAULT 60 | 默认采集间隔（秒） |
| is_active | Boolean | DEFAULT true | 是否启用 |
| created_at | DateTime | | 创建时间 |

### metric_data（TimescaleDB 超表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| time | DateTime | PK | 时间戳 |
| server_id | UUID | PK | 服务器 ID |
| metric_name | String(128) | PK | 指标名称 |
| value | Float | | 指标值 |
| labels | JSON | | 标签 |

### alert_rules

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 规则 ID |
| name | String(128) | NOT NULL | 规则名称 |
| metric_name | String(128) | NOT NULL | 监控指标 |
| condition | String(10) | NOT NULL | 条件（gt/lt/eq/ne/ge/le） |
| threshold | Float | NOT NULL | 阈值 |
| duration | Integer | DEFAULT 0 | 持续时间（秒） |
| severity | String(20) | DEFAULT 'warning' | 严重级别（critical/warning/info） |
| target_filter | JSON | | 目标服务器过滤 |
| notification_channels | JSON | | 通知渠道 |
| is_enabled | Boolean | DEFAULT true | 是否启用 |
| created_by | UUID | FK → users.id | 创建者 |
| created_at | DateTime | | 创建时间 |
| updated_at | DateTime | | 更新时间 |

### alert_events

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 事件 ID |
| rule_id | UUID | FK → alert_rules.id | 关联规则 |
| server_id | UUID | FK → servers.id | 关联服务器 |
| severity | String(20) | | 严重级别 |
| status | String(20) | DEFAULT 'firing' | 状态（firing/resolved/acknowledged/suppressed） |
| summary | Text | | 摘要 |
| metric_value | Float | | 触发时的指标值 |
| triggered_at | DateTime | | 触发时间 |
| resolved_at | DateTime | | 解决时间 |
| acknowledged_by | UUID | FK → users.id | 确认人 |
| notification_sent | Boolean | DEFAULT false | 是否已发送通知 |
| created_at | DateTime | | 创建时间 |

## Outband 模块

### sel_logs

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 日志 ID |
| server_id | UUID | FK → servers.id | 关联服务器 |
| record_id | Integer | | SEL 记录 ID |
| timestamp | DateTime | | 事件时间 |
| sensor_type | String(64) | | 传感器类型 |
| sensor_name | String(64) | | 传感器名称 |
| event_type | String(64) | | 事件类型 |
| severity | String(20) | | 严重级别 |
| description | Text | | 描述 |
| raw_data | JSON | | 原始数据 |
| is_acknowledged | Boolean | DEFAULT false | 是否已确认 |
| acknowledged_by | UUID | FK → users.id | 确认人 |
| created_at | DateTime | | 创建时间 |

### firmware_inventory

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 记录 ID |
| server_id | UUID | FK → servers.id | 关联服务器（联合唯一：server_id + component） |
| component | String(64) | | 组件名称（BIOS/BMC/RAID/NIC/PSU） |
| component_id | String(128) | | 组件标识 |
| current_version | String(64) | | 当前版本 |
| available_version | String(64) | | 可用版本 |
| update_status | String(20) | | 更新状态（up_to_date/update_available/updating/failed） |
| last_checked_at | DateTime | | 最后检查时间 |

### kvm_sessions

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 会话 ID |
| server_id | UUID | FK → servers.id | 关联服务器 |
| user_id | UUID | FK → users.id | 关联用户 |
| proxy_token | String(128) | UNIQUE | 代理 Token |
| status | String(20) | DEFAULT 'active' | 状态（active/expired/terminated） |
| started_at | DateTime | | 开始时间 |
| expires_at | DateTime | | 过期时间 |
| ended_at | DateTime | | 结束时间 |
| client_ip | INET | | 客户端 IP |

## AutoOps 模块

### task_definitions

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 任务定义 ID |
| name | String(128) | NOT NULL | 任务名称 |
| task_type | String(32) | NOT NULL | 类型（firmware_upgrade/inspection/config_deploy/custom） |
| target_filter | JSON | | 目标服务器过滤 |
| steps | JSON | | 任务步骤定义 |
| parameters | JSON | | 参数 |
| schedule | String(128) | | Cron 表达式 |
| is_scheduled | Boolean | DEFAULT false | 是否定时 |
| requires_approval | Boolean | DEFAULT false | 是否需要审批 |
| approver_roles | JSON | | 审批角色列表 |
| retry_policy | JSON | DEFAULT {"max_retries":3,"delay":60,"backoff":"exponential"} | 重试策略 |
| timeout_seconds | Integer | DEFAULT 3600 | 超时时间 |
| is_enabled | Boolean | DEFAULT true | 是否启用 |
| created_by | UUID | FK → users.id | 创建者 |
| created_at | DateTime | | 创建时间 |
| updated_at | DateTime | | 更新时间 |

### task_instances

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 实例 ID |
| task_def_id | UUID | FK → task_definitions.id | 关联任务定义 |
| status | String(20) | DEFAULT 'pending' | 状态（pending/approved/running/paused/completed/failed/cancelled） |
| trigger_type | String(20) | | 触发方式（manual/scheduled/api） |
| parameters | JSON | | 运行参数 |
| approved_by | UUID | FK → users.id | 审批人 |
| approved_at | DateTime | | 审批时间 |
| started_at | DateTime | | 开始时间 |
| completed_at | DateTime | | 完成时间 |
| summary | JSON | | 执行摘要 |
| created_by | UUID | FK → users.id | 创建者 |
| created_at | DateTime | | 创建时间 |

### task_step_logs

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 步骤日志 ID |
| task_instance_id | UUID | FK → task_instances.id | 关联任务实例 |
| server_id | UUID | FK → servers.id | 关联服务器 |
| step_number | Integer | | 步骤序号 |
| step_name | String(128) | | 步骤名称 |
| status | String(20) | DEFAULT 'pending' | 状态（pending/running/completed/failed/skipped） |
| started_at | DateTime | | 开始时间 |
| completed_at | DateTime | | 完成时间 |
| retry_count | Integer | DEFAULT 0 | 重试次数 |
| output | Text | | 输出 |
| error_message | Text | | 错误信息 |

### firmware_packages

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 固件包 ID |
| filename | String(255) | NOT NULL | 文件名 |
| brand | String(64) | NOT NULL | 品牌 |
| component | String(64) | NOT NULL | 组件 |
| version | String(64) | NOT NULL | 版本 |
| file_size | BigInteger | | 文件大小 |
| file_hash | String(128) | | 文件哈希 |
| minio_bucket | String(128) | | MinIO 桶名 |
| minio_key | String(512) | | MinIO 对象键 |
| upload_status | String(20) | DEFAULT 'pending' | 上传状态（pending/uploading/completed/verified/failed） |
| supported_models | JSON | | 支持型号列表 |
| release_notes | Text | | 发布说明 |
| uploaded_by | UUID | FK → users.id | 上传者 |
| created_at | DateTime | | 创建时间 |

### inspection_policies

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 策略 ID |
| task_def_id | UUID | UNIQUE, FK → task_definitions.id | 关联任务定义 |
| schedule | String(128) | | Cron 表达式 |
| target_filter | JSON | | 目标过滤 |
| check_items | JSON | | 检查项 |
| enabled | Boolean | DEFAULT true | 是否启用 |
| last_run_at | DateTime | | 上次运行时间 |
| next_run_at | DateTime | | 下次运行时间 |

## Audit 模块

### audit_logs

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 日志 ID |
| user_id | UUID | FK → users.id | 操作用户 |
| username | String(64) | | 用户名（冗余） |
| action | String(32) | NOT NULL | 操作类型（create/update/delete） |
| resource_type | String(64) | NOT NULL | 资源类型 |
| resource_id | String(128) | | 资源 ID |
| resource_name | String(255) | | 资源名称 |
| detail | JSON | | 操作详情 |
| ip_address | INET | | 请求 IP |
| user_agent | String(512) | | User-Agent |
| request_id | String(64) | | 请求 ID |
| status | String(20) | DEFAULT 'success' | 状态（success/failure） |
| error_message | Text | | 错误信息 |
| created_at | DateTime | | 创建时间 |

### notification_logs

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 通知 ID |
| channel_id | UUID | FK → notification_channels.id | 关联渠道 |
| channel_type | String(20) | | 渠道类型 |
| recipient | String(255) | | 收件人 |
| subject | String(255) | | 主题 |
| content | Text | | 内容 |
| status | String(20) | DEFAULT 'pending' | 状态（pending/sent/failed/retrying） |
| error_message | Text | | 错误信息 |
| sent_at | DateTime | | 发送时间 |
| retry_count | Integer | DEFAULT 0 | 重试次数 |
| related_alert_id | UUID | FK → alert_events.id | 关联告警 |
| created_at | DateTime | | 创建时间 |

## Knowledge 模块

### conversations

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 对话 ID |
| user_id | UUID | FK → users.id, INDEX | 所属用户 |
| title | String(255) | | 对话标题 |
| created_at | DateTime | | 创建时间 |
| updated_at | DateTime | | 更新时间 |

### conversation_messages

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 消息 ID |
| conversation_id | UUID | FK → conversations.id, INDEX | 所属对话 |
| role | String(20) | NOT NULL | 角色（user/assistant） |
| content | Text | NOT NULL | 消息内容 |
| sources | JSON | | 参考来源 |
| query_type | String(20) | | 查询类型（semantic/structured/hybrid） |
| brand | String(64) | | 品牌 |
| latency_ms | Integer | | 查询延迟（毫秒） |
| created_at | DateTime | | 创建时间 |

### knowledge_favorites

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 收藏 ID |
| user_id | UUID | FK → users.id, INDEX | 所属用户 |
| message_id | UUID | FK → conversation_messages.id | 关联消息 |
| title | String(255) | | 收藏标题 |
| content | Text | | 收藏内容 |
| source_type | String(32) | | 来源类型（qa/sel_code/firmware） |
| brand | String(64) | | 品牌 |
| created_at | DateTime | | 创建时间 |

### sel_event_codes

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 记录 ID |
| brand | String(64) | INDEX | 品牌 |
| event_code | String(32) | | 事件码 |
| sensor_type | String(64) | | 传感器类型 |
| severity | String(20) | | 严重级别 |
| description | Text | | 描述 |
| recommended_action | Text | | 建议处理 |
| source_document_id | String(128) | | 来源文档 ID |

索引：`ix_sel_event_codes_brand`, `ix_sel_event_codes_brand_code`

### firmware_compatibility

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 记录 ID |
| brand | String(64) | INDEX | 品牌 |
| model | String(128) | | 服务器型号 |
| component | String(64) | | 组件（BIOS/BMC/RAID/NIC/PSU） |
| version | String(64) | | 固件版本 |
| release_date | Date | | 发布日期 |
| criticality | String(20) | | 重要性（optional/recommended/critical） |
| release_notes | Text | | 发布说明 |
| download_url | String(512) | | 下载链接 |

索引：`ix_firmware_compatibility_brand`, `ix_firmware_compatibility_brand_model`

## 实体关系

```
DataCenter 1──N Rack 1──N Server
                           │
              ┌────────────┼────────────┬──────────────┐
              │            │            │              │
         BMCCredential  SELLog    FirmwareInventory  KVMSession
              │            │                              │
              │            │                         User (KVM操作者)
              │            │
         Adapter层      AlertEvent ── AlertRule
         (BMC通信)          │
                       MetricData ── MetricDefinition

User N──M Role N──M Permission
  │
  ├── Conversation 1──N ConversationMessage
  │                          │
  └── KnowledgeFavorite ─────┘

TaskDefinition 1──N TaskInstance 1──N TaskStepLog
  │                    │
  └── InspectionPolicy │
                  FirmwarePackage

AuditLog (自动记录写操作)
NotificationLog ── NotificationChannel ── AlertEvent
```
