# API 接口参考

## 通用约定

### 基础 URL

```
http://{host}:{port}/api/v1
```

### 认证方式

除标注为"公开"的接口外，所有接口均需在请求头中携带 JWT Token：

```
Authorization: Bearer <access_token>
```

### 分页参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | int | 1 | 页码 |
| page_size | int | 20 | 每页条数（最大 100） |

### 分页响应格式

```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

### 通用错误响应

```json
{
  "error_code": "NOT_FOUND",
  "message": "Resource not found",
  "detail": null
}
```

| HTTP 状态码 | error_code | 说明 |
|------------|------------|------|
| 400 | VALIDATION_ERROR | 请求参数校验失败 |
| 401 | AUTHENTICATION_ERROR | 未认证或 Token 过期 |
| 403 | AUTHORIZATION_ERROR | 无权限访问 |
| 404 | NOT_FOUND | 资源不存在 |
| 409 | CONFLICT | 资源冲突（唯一性约束） |
| 422 | VALIDATION_ERROR | 请求体校验失败 |
| 429 | RATE_LIMIT_EXCEEDED | 请求限流 |
| 502 | BMC_CONNECTION_ERROR | BMC 连接失败 |
| 502 | BMC_AUTH_ERROR | BMC 认证失败 |

---

## System 模块

前缀：`/api/v1/system`

### 认证

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/auth/login` | 公开 | 用户登录 |
| POST | `/auth/register` | 公开 | 用户注册 |
| POST | `/auth/refresh` | 公开 | 刷新 Token（Token 轮换） |
| GET | `/auth/me` | 登录 | 获取当前用户信息 |
| POST | `/auth/ws-ticket` | 登录 | 生成 WebSocket 连接票据（30 秒有效） |

#### POST /auth/login

请求：
```json
{
  "username": "admin",
  "password": "password123"
}
```

响应：
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "username": "admin",
    "email": "admin@example.com",
    "is_superuser": true,
    "roles": [...]
  }
}
```

#### POST /auth/register

请求：
```json
{
  "username": "newuser",
  "email": "user@example.com",
  "password": "password123",
  "full_name": "张三",
  "phone": "13800138000",
  "company": "某公司",
  "title": "运维工程师",
  "user_type": "provider"
}
```

#### POST /auth/refresh

请求：
```json
{
  "refresh_token": "eyJ..."
}
```

响应：
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

### 用户管理

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/users` | system:user:read | 用户列表（分页+搜索+过滤） |
| GET | `/users/{user_id}` | system:user:read | 用户详情 |
| POST | `/users` | system:user:write | 创建用户 |
| PUT | `/users/{user_id}` | system:user:write | 更新用户 |
| PUT | `/users/{user_id}/password` | 登录 | 修改密码（仅本人或超管） |
| DELETE | `/users/{user_id}` | system:user:write | 删除用户（不可删超管） |

### 角色管理

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/roles` | system:role:read | 角色列表 |
| GET | `/roles/{role_id}` | system:role:read | 角色详情 |
| POST | `/roles` | system:role:write | 创建角色 |
| PUT | `/roles/{role_id}` | system:role:write | 更新角色（不可修改内置角色） |
| DELETE | `/roles/{role_id}` | system:role:write | 删除角色（有用户时不可删） |

### 权限

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/permissions` | system:role:read | 权限列表 |

### 系统配置

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/configs` | system:config:read | 配置列表 |
| GET | `/configs/{config_id}` | system:config:read | 配置详情 |
| POST | `/configs` | system:config:write | 创建配置 |
| PUT | `/configs/{config_id}` | system:config:write | 更新配置 |
| DELETE | `/configs/{config_id}` | system:config:write | 删除配置 |

### 通知渠道

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/notification-channels` | system:channel:read | 渠道列表 |
| GET | `/notification-channels/{id}` | system:channel:read | 渠道详情 |
| POST | `/notification-channels` | system:channel:write | 创建渠道 |
| PUT | `/notification-channels/{id}` | system:channel:write | 更新渠道 |
| DELETE | `/notification-channels/{id}` | system:channel:write | 删除渠道 |

### 健康检查

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/health` | 公开 | 健康检查 |

---

## Knowledge 模块

前缀：`/api/v1/knowledge`

### 知识查询

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/query` | 登录 | 知识查询 |
| GET | `/sel-codes` | 登录 | SEL 事件码查询 |
| GET | `/firmware-matrix` | 登录 | 固件兼容矩阵查询 |

#### POST /query

请求：
```json
{
  "query": "Dell R750 CPU温度过高怎么处理？",
  "brand": "dell",
  "model": "R750",
  "category": "troubleshooting",
  "query_type": "hybrid",
  "conversation_id": "uuid",
  "top_k": 5
}
```

响应：
```json
{
  "answer": "当 Dell R750 CPU 温度过高时，建议按以下步骤处理...",
  "sources": [
    {
      "document_id": "doc_001",
      "title": "Dell PowerEdge R750 故障排除指南",
      "relevance_score": 0.95,
      "snippet": "..."
    }
  ],
  "conversation_id": "uuid",
  "query_type": "hybrid",
  "latency_ms": 1200
}
```

#### GET /sel-codes

参数：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| brand | string | 是 | 品牌 |
| event_code | string | 否 | 事件码 |
| severity | string | 否 | 严重级别（Critical/Warning/Info） |

#### GET /firmware-matrix

参数：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| brand | string | 是 | 品牌 |
| model | string | 否 | 型号 |
| component | string | 否 | 组件（BIOS/BMC/RAID/NIC/PSU） |

### 对话管理

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/conversations` | 登录 | 创建对话 |
| GET | `/conversations` | 登录 | 对话列表 |
| GET | `/conversations/{id}` | 登录 | 对话详情（含消息） |
| PATCH | `/conversations/{id}` | 登录 | 更新对话标题 |
| DELETE | `/conversations/{id}` | 登录 | 删除对话 |

### 收藏

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/favorites` | 登录 | 创建收藏 |
| GET | `/favorites` | 登录 | 收藏列表 |
| DELETE | `/favorites/{id}` | 登录 | 删除收藏（所有权校验） |

---

## Asset 模块

前缀：`/api/v1/asset`

### 数据中心

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/datacenters` | asset:datacenter:read | 数据中心列表 |
| GET | `/datacenters/{dc_id}` | asset:datacenter:read | 数据中心详情 |
| POST | `/datacenters` | asset:datacenter:write | 创建数据中心 |
| PUT | `/datacenters/{dc_id}` | asset:datacenter:write | 更新数据中心 |
| DELETE | `/datacenters/{dc_id}` | asset:datacenter:write | 删除数据中心 |

### 机柜

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/racks` | asset:datacenter:read | 机柜列表（可按数据中心过滤） |
| GET | `/racks/{rack_id}` | asset:datacenter:read | 机柜详情 |
| POST | `/racks` | asset:datacenter:write | 创建机柜 |
| PUT | `/racks/{rack_id}` | asset:datacenter:write | 更新机柜 |
| DELETE | `/racks/{rack_id}` | asset:datacenter:write | 删除机柜 |

### 服务器

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/servers` | asset:server:read | 服务器列表（多维度过滤） |
| GET | `/servers/{server_id}` | asset:server:read | 服务器详情 |
| POST | `/servers` | asset:server:write | 创建服务器（含 BMC 凭证） |
| POST | `/servers/bulk` | asset:server:write | 批量创建服务器 |
| PUT | `/servers/bulk` | asset:server:write | 批量更新服务器 |
| DELETE | `/servers/bulk` | asset:server:write | 批量删除服务器 |
| PUT | `/servers/{server_id}` | asset:server:write | 更新服务器 |
| DELETE | `/servers/{server_id}` | asset:server:write | 删除服务器 |

#### GET /servers 过滤参数

| 参数 | 类型 | 说明 |
|------|------|------|
| brand | string | 品牌过滤 |
| model | string | 型号过滤 |
| status | string | 状态过滤（active/inactive/maintenance/retired） |
| data_center_id | uuid | 数据中心过滤 |
| rack_id | uuid | 机柜过滤 |
| bmc_status | string | BMC 状态过滤（online/offline/unknown/error） |
| owner_id | uuid | 负责人过滤 |
| department | string | 部门过滤 |
| search | string | 搜索（名称/序列号） |

### BMC 凭据

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/servers/{server_id}/bmc-credential` | asset:server:read | 获取 BMC 凭据 |
| PUT | `/servers/{server_id}/bmc-credential` | asset:server:write | 创建/更新 BMC 凭据 |
| DELETE | `/bmc-credentials/{credential_id}` | asset:server:write | 删除 BMC 凭据 |

---

## Monitor 模块

前缀：`/api/v1/monitor`

### 仪表盘

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/dashboard` | monitor:metric:read | 仪表盘指标汇总 |

### 指标定义

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/definitions` | monitor:metric:write | 创建指标定义 |
| GET | `/definitions` | monitor:metric:read | 指标定义列表 |
| GET | `/definitions/{metric_id}` | monitor:metric:read | 指标定义详情 |
| PUT | `/definitions/{metric_id}` | monitor:metric:write | 更新指标定义 |
| DELETE | `/definitions/{metric_id}` | monitor:metric:write | 删除指标定义 |

### 指标数据

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/data` | monitor:metric:write | 写入单条指标数据 |
| POST | `/data/batch` | monitor:metric:write | 批量写入指标数据 |
| POST | `/data/query` | monitor:metric:read | 范围查询指标数据 |
| GET | `/data/latest/{metric_name}/{server_id}` | monitor:metric:read | 获取最新指标值 |
| DELETE | `/data/cleanup` | monitor:metric:write | 清理过期指标数据 |

### 采集与评估

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/collect` | monitor:collect:execute | 触发指标采集 |
| POST | `/evaluate` | monitor:collect:execute | 触发告警评估 |

### 告警规则

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/rules` | monitor:alert:write | 创建告警规则 |
| GET | `/rules` | monitor:alert:read | 告警规则列表 |
| GET | `/rules/{rule_id}` | monitor:alert:read | 规则详情 |
| PUT | `/rules/{rule_id}` | monitor:alert:write | 更新规则 |
| DELETE | `/rules/{rule_id}` | monitor:alert:write | 删除规则 |

### 告警事件

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/events` | monitor:alert:read | 告警事件列表 |
| GET | `/events/stats` | monitor:alert:read | 告警统计 |
| GET | `/events/{event_id}` | monitor:alert:read | 事件详情 |
| POST | `/events/acknowledge` | monitor:alert:execute | 确认告警 |
| POST | `/events/suppress` | monitor:alert:execute | 抑制告警 |

---

## Outband 模块

前缀：`/api/v1/outband`

### BMC 连接

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/test-connection` | outband:info:read | 测试 BMC 连接（不保存凭据） |

#### POST /test-connection

请求：
```json
{
  "host": "192.168.1.100",
  "username": "admin",
  "password": "password",
  "protocol": "redfish"
}
```

响应：
```json
{
  "success": true,
  "brand": "dell",
  "model": "PowerEdge R750",
  "manufacturer": "Dell Inc."
}
```

### 系统信息

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/servers/{server_id}/system-info` | outband:info:read | 获取系统信息 |
| GET | `/servers/{server_id}/hardware` | outband:info:read | 获取完整硬件详情 |

### 电源控制

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/servers/{server_id}/power` | outband:info:read | 获取电源状态 |
| POST | `/servers/{server_id}/power` | outband:power:execute | 执行电源操作 |
| POST | `/servers/bulk-power` | outband:power:execute | 批量电源操作 |

#### POST /servers/{server_id}/power

请求：
```json
{
  "action": "graceful_restart"
}
```

action 可选值：`on`, `off`, `graceful_off`, `force_off`, `restart`, `graceful_restart`, `force_restart`, `nmi`

### 传感器

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/servers/{server_id}/sensors` | outband:info:read | 获取传感器数据 |

### SEL 日志

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/sel-logs` | outband:sel:read | SEL 日志列表 |
| POST | `/sel-logs/acknowledge` | outband:sel:write | 确认 SEL 条目 |

### 固件

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/servers/{server_id}/firmware` | outband:info:read | 获取固件清单 |

### KVM

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/servers/{server_id}/kvm` | outband:kvm:execute | 启动 KVM 会话 |
| DELETE | `/kvm/{session_id}` | outband:kvm:execute | 终止 KVM 会话 |
| GET | `/kvm-sessions` | outband:kvm:execute | KVM 会话列表 |

#### POST /servers/{server_id}/kvm

请求：
```json
{
  "duration_minutes": 60
}
```

响应：
```json
{
  "session_id": "uuid",
  "proxy_token": "token_string",
  "proxy_url": "wss://host/kvm-proxy/...",
  "expires_at": "2026-04-26T12:00:00Z"
}
```

---

## AutoOps 模块

前缀：`/api/v1/autoops`

### 任务定义

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/tasks` | autoops:task:write | 创建任务定义 |
| GET | `/tasks` | autoops:task:read | 任务定义列表 |
| GET | `/tasks/{task_id}` | autoops:task:read | 任务定义详情 |
| PUT | `/tasks/{task_id}` | autoops:task:write | 更新任务定义 |
| DELETE | `/tasks/{task_id}` | autoops:task:write | 删除任务定义 |

### 任务实例

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/instances` | autoops:task:execute | 创建任务实例 |
| GET | `/instances` | autoops:task:read | 任务实例列表 |
| GET | `/instances/{instance_id}` | autoops:task:read | 实例详情 |
| POST | `/instances/{instance_id}/approve` | autoops:task:approve | 审批任务 |
| POST | `/instances/{instance_id}/cancel` | autoops:task:execute | 取消任务 |
| GET | `/instances/{instance_id}/steps` | autoops:task:read | 获取步骤日志 |

### 固件包

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/firmware` | autoops:task:write | 创建固件包 |
| GET | `/firmware` | autoops:task:read | 固件包列表 |
| GET | `/firmware/{pkg_id}` | autoops:task:read | 固件包详情 |
| DELETE | `/firmware/{pkg_id}` | autoops:task:write | 删除固件包 |

---

## Audit 模块

前缀：`/api/v1/audit`

### 审计日志

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/logs` | audit:log:read | 审计日志列表（多维度过滤） |
| GET | `/logs/stats` | audit:log:read | 审计统计 |
| GET | `/logs/export` | audit:log:read | 导出审计日志（CSV/JSON） |
| DELETE | `/logs/cleanup` | audit:log:write | 清理过期日志 |
| GET | `/logs/{log_id}` | audit:log:read | 日志详情 |

#### GET /logs 过滤参数

| 参数 | 类型 | 说明 |
|------|------|------|
| username | string | 用户名 |
| action | string | 操作类型（create/update/delete） |
| resource_type | string | 资源类型 |
| status | string | 状态（success/failure） |
| start_date | datetime | 开始时间 |
| end_date | datetime | 结束时间 |

### 通知记录

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/notifications/send` | audit:notification:execute | 发送通知 |
| GET | `/notifications` | audit:log:read | 通知日志列表 |
| GET | `/notifications/stats` | audit:log:read | 通知统计 |
| GET | `/notifications/{log_id}` | audit:log:read | 通知详情 |
| POST | `/notifications/retry` | audit:notification:execute | 重试失败通知 |

---

## Integrations 模块

前缀：`/api/v1/integrations/netbox`

所有端点需登录且检查 `NETBOX_SYNC_ENABLED` 配置。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/status` | NetBox 连接状态 |
| POST | `/sync/from-netbox` | 从 NetBox 导入设备 |
| POST | `/sync/to-netbox` | 推送服务器到 NetBox |
| POST | `/sync/sites` | 同步站点为数据中心 |
| GET | `/sites` | 列出 NetBox 站点 |
| GET | `/devices` | 列出 NetBox 设备 |

---

## 全局端点

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/` | 公开 | 应用信息 |
| GET | `/api/v1/health` | 公开 | 全局健康检查 |
