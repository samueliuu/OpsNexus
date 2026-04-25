# 集成模块

## NetBox DCIM 集成

### 概述

OpsNexus 支持与 [NetBox](https://netbox.dev/) DCIM 系统双向同步，实现资产数据的统一管理。

**数据权威原则**：
- **NetBox** = 拓扑权威源（Source of Truth for Topology）：站点、机柜、设备位置
- **OpsNexus** = BMC/实时状态权威源：BMC 凭据、传感器数据、健康状态

### 架构

```
┌──────────────────┐                    ┌──────────────────┐
│    OpsNexus      │                    │     NetBox       │
│                  │                    │                  │
│  ┌────────────┐  │   NetBoxSync      │  ┌────────────┐  │
│  │  Server    │◀─┼───Service─────────┼─▶│  Device    │  │
│  │  DataCenter│  │                   │  │  Site      │  │
│  │  Rack      │  │                   │  │  Rack      │  │
│  └────────────┘  │                    │  └────────────┘  │
└──────────────────┘                    └──────────────────┘
```

### NetBoxClient

`NetBoxClient` 是异步 HTTP 客户端，封装 NetBox REST API：

| 方法 | API | 说明 |
|------|-----|------|
| `health_check()` | GET /api/status | 连接状态检查 |
| `get_sites()` | GET /api/dcim/sites | 获取站点列表 |
| `get_racks()` | GET /api/dcim/racks | 获取机柜列表 |
| `get_devices()` | GET /api/dcim/devices | 获取设备列表 |
| `get_device_by_name()` | GET /api/dcim/devices?name= | 按名称查询 |
| `get_device_by_serial()` | GET /api/dcim/devices?serial= | 按序列号查询 |
| `create_device()` | POST /api/dcim/devices | 创建设备 |
| `update_device()` | PATCH /api/dcim/devices/{id} | 更新设备 |
| `get_interfaces()` | GET /api/dcim/interfaces | 获取接口 |
| `get_ip_addresses()` | GET /api/ipam/ip-addresses | 获取 IP 地址 |

特性：
- 支持异步上下文管理器
- 自动分页查询（offset/limit）
- HTTP Token 认证

### 同步服务

#### NetBox → OpsNexus（`sync_from_netbox`）

导入 NetBox 设备为 OpsNexus 服务器：

```
1. 从 NetBox 获取所有设备
2. 遍历设备：
   ├── 按序列号匹配已有服务器 → 更新
   ├── 按主机名匹配已有服务器 → 更新
   └── 无匹配 → 创建新服务器
3. 映射字段：
   ├── NetBox.name → Server.name / Server.hostname
   ├── NetBox.serial → Server.serial_number
   ├── NetBox.device_type.model → Server.model
   ├── NetBox.manufacturer → Server.brand（通过 MANUFACTURER_MAP）
   ├── NetBox.site → DataCenter
   ├── NetBox.rack → Rack
   └── NetBox.primary_ip → Server.bmc_ip
```

#### OpsNexus → NetBox（`sync_to_netbox`）

推送 OpsNexus 服务器到 NetBox：

```
1. 获取所有 OpsNexus 服务器
2. 遍历服务器：
   ├── 按序列号匹配 NetBox 设备 → 更新
   ├── 按主机名匹配 NetBox 设备 → 更新
   └── 无匹配 → 创建新设备
3. 映射字段：
   ├── Server.name → NetBox.name
   ├── Server.serial_number → NetBox.serial
   ├── Server.brand → NetBox.manufacturer（通过反向映射）
   ├── Server.model → NetBox.device_type
   └── Server.bmc_ip → NetBox.primary_ip
```

#### 站点同步（`sync_sites_from_netbox`）

导入 NetBox 站点为 OpsNexus 数据中心：

```
1. 从 NetBox 获取所有站点
2. 遍历站点：
   ├── 按名称匹配已有数据中心 → 更新
   └── 无匹配 → 创建新数据中心
3. 映射字段：
   ├── NetBox.name → DataCenter.name
   ├── NetBox.slug → DataCenter.code
   ├── NetBox.physical_address → DataCenter.location
   └── NetBox.contact_name → DataCenter.contact_name
```

### 制造商映射

`MANUFACTURER_MAP` 将 NetBox 制造商名称映射到 OpsNexus 品牌键：

| NetBox 制造商 | OpsNexus 品牌 |
|--------------|---------------|
| Dell | dell |
| Dell EMC | dell |
| HPE | hpe |
| Hewlett Packard Enterprise | hpe |
| HP | hpe |
| Lenovo | lenovo |
| Huawei | huawei |
| Inspur | inspur |
| H3C | h3c |
| Sugon | sugon |
| xFusion | xfusion |

### API 端点

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

### 配置项

| 配置 | 环境变量 | 默认值 | 说明 |
|------|----------|--------|------|
| API 地址 | NETBOX_API_URL | | NetBox API 地址 |
| API Token | NETBOX_API_TOKEN | | NetBox API Token |
| 同步开关 | NETBOX_SYNC_ENABLED | false | 是否启用同步 |

## 事件总线集成

### RabbitMQ 配置

| 配置 | 环境变量 | 默认值 |
|------|----------|--------|
| 连接地址 | RABBITMQ_URL | amqp://opsnexus:opsnexus@rabbitmq:5672/ |
| Exchange | - | opsnexus.events（Topic 类型） |
| 消息持久化 | - | 是 |

### 事件发布

业务服务通过 `EventBus.publish()` 发布事件：

```python
await event_bus.publish(
    event_type=EventTypes.ALERT_TRIGGERED,
    payload={
        "event_id": str(event.id),
        "server_id": str(server.id),
        "severity": event.severity,
        "summary": event.summary,
    }
)
```

### 事件订阅

其他模块通过 `EventBus.subscribe()` 订阅事件：

```python
await event_bus.subscribe(
    event_type=EventTypes.ALERT_TRIGGERED,
    callback=handle_alert_triggered
)
```

### 事件类型

| 类别 | 事件 | 发布者 | 说明 |
|------|------|--------|------|
| Server | SERVER_CREATED | AssetService | 服务器创建 |
| Server | SERVER_UPDATED | AssetService | 服务器更新 |
| Server | SERVER_DELETED | AssetService | 服务器删除 |
| Server | SERVER_STATUS_CHANGED | AssetService | 服务器状态变更 |
| BMC | BMC_ONLINE | MetricCollectionService | BMC 上线 |
| BMC | BMC_OFFLINE | MetricCollectionService | BMC 下线 |
| BMC | BMC_ERROR | BMCService | BMC 错误 |
| Alert | ALERT_TRIGGERED | AlertEvaluationService | 告警触发 |
| Alert | ALERT_RESOLVED | AlertEvaluationService | 告警恢复 |
| Alert | ALERT_ACKNOWLEDGED | AlertEventService | 告警确认 |
| Task | TASK_CREATED | TaskInstanceService | 任务创建 |
| Task | TASK_STARTED | TaskInstanceService | 任务启动 |
| Task | TASK_COMPLETED | TaskInstanceService | 任务完成 |
| Task | TASK_FAILED | TaskInstanceService | 任务失败 |
| Task | TASK_CANCELLED | TaskInstanceService | 任务取消 |
