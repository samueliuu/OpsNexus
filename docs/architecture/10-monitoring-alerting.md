# 监控告警

## 概述

监控告警模块提供从 BMC 实时采集服务器指标、基于规则引擎自动评估告警、多渠道通知的完整监控链路。

## 架构

```
┌──────────────────────────────────────────────────────────────────┐
│                        监控告警架构                                │
│                                                                  │
│  ┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │  指标采集    │───▶│   指标存储       │───▶│   告警评估      │  │
│  │  Collect    │    │   MetricData    │    │   Evaluate      │  │
│  │  Service    │    │   (TimescaleDB) │    │   Service       │  │
│  └──────┬──────┘    └─────────────────┘    └────────┬────────┘  │
│         │                                           │           │
│         │ BMC (Redfish)                    ┌────────▼────────┐  │
│         │                                  │   告警事件       │  │
│  ┌──────▼──────┐                           │   AlertEvent    │  │
│  │   Adapter   │                           └────────┬────────┘  │
│  │   适配器层   │                                    │           │
│  └─────────────┘                           ┌────────▼────────┐  │
│                                            │   事件总线       │  │
│                                            │   RabbitMQ      │  │
│                                            └────────┬────────┘  │
│                                                     │           │
│                                            ┌────────▼────────┐  │
│                                            │   通知服务       │  │
│                                            │   Notification   │  │
│                                            │   Service        │  │
│                                            └─────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

## 指标采集

### 采集流程

```
触发（定时/手动）
    │
    ▼
MetricCollectionService.collect()
    │
    ├── 查询所有有 BMC IP 的服务器
    │
    ├── Redis 分布式锁（防止重复采集）
    │   key: metric_collect:{server_id}
    │   TTL: collect_interval * 2
    │
    ├── 遍历服务器，逐台采集
    │   │
    │   ├── 获取 BMC 凭证 → 解密密码
    │   │
    │   ├── AdapterRegistry.create(brand, connection)
    │   │
    │   ├── adapter.get_sensor_data()
    │   │   ├── 温度传感器 → temperature_celsius__{sensor_name}
    │   │   ├── 风扇传感器 → fan_speed_rpm__{sensor_name}
    │   │   ├── 电压传感器 → voltage_volts__{sensor_name}
    │   │   ├── 功耗传感器 → power_watts__{sensor_name}
    │   │   └── 其他传感器 → {type}_{unit}__{sensor_name}
    │   │
    │   ├── adapter.get_power_state()
    │   │   └── power_state (on/off)
    │   │
    │   └── 批量写入 MetricData
    │
    └── 更新 Server.bmc_status
        ├── 采集成功 → online
        └── 采集失败 → offline/error
```

### 指标命名规则

```
{metric_type}_{unit}__{sensor_identifier}

示例：
  temperature_celsius__cpu1        - CPU1 温度
  temperature_celsius__inlet       - 进风口温度
  fan_speed_rpm__fan1              - 风扇1 转速
  voltage_volts__psu1_vin          - PSU1 输入电压
  power_watts__system              - 系统功耗
  power_watts__psu1                - PSU1 功耗
```

### 指标定义

每个指标对应 `metric_definitions` 表的一条记录：

| 字段 | 说明 | 示例 |
|------|------|------|
| name | 指标名称 | temperature_celsius__cpu1 |
| display_name | 显示名称 | CPU1 温度 |
| unit | 单位 | °C |
| metric_type | 类型 | gauge |
| data_type | 数据类型 | float |
| collection_method | 采集方式 | bmc |
| default_interval | 默认采集间隔 | 60 秒 |

### 采集触发

| 方式 | 说明 |
|------|------|
| 手动触发 | `POST /api/v1/monitor/collect` |
| 定时触发 | `METRIC_COLLECT_INTERVAL` 配置（默认 60 秒） |

## 指标存储

### TimescaleDB 超表

`metric_data` 表设计为 TimescaleDB 超表，按时间自动分区：

| 字段 | 类型 | 说明 |
|------|------|------|
| time | DateTime | 时间戳（分区键） |
| server_id | UUID | 服务器 ID |
| metric_name | String | 指标名称 |
| value | Float | 指标值 |
| labels | JSON | 标签 |

### 查询接口

| 接口 | 说明 |
|------|------|
| `POST /data/query` | 范围查询（指定时间范围、服务器、指标） |
| `GET /data/latest/{metric_name}/{server_id}` | 获取最新值 |
| `POST /data` | 写入单条数据 |
| `POST /data/batch` | 批量写入 |
| `DELETE /data/cleanup` | 清理过期数据 |

### 仪表盘

`GET /api/v1/monitor/dashboard` 返回汇总数据：

```json
{
  "total_servers": 50,
  "online_servers": 45,
  "alerting_servers": 3,
  "critical_alerts": 1,
  "server_metrics": [
    {
      "server_id": "uuid",
      "server_name": "web-server-01",
      "health_status": "warning",
      "cpu_temperature": 72.5,
      "cpu_usage": 85.3,
      "memory_usage": 78.2,
      "power_consumption": 350
    }
  ]
}
```

## 告警规则

### 规则定义

| 字段 | 说明 | 示例 |
|------|------|------|
| name | 规则名称 | CPU 温度过高告警 |
| metric_name | 监控指标 | temperature_celsius__cpu1 |
| condition | 比较条件 | gt（大于） |
| threshold | 阈值 | 80 |
| duration | 持续时间（秒） | 300（5 分钟） |
| severity | 严重级别 | critical |
| target_filter | 目标过滤 | {"brand": "dell"} |
| notification_channels | 通知渠道 | ["channel_id_1"] |
| is_enabled | 是否启用 | true |

### 条件类型

| 条件 | 含义 |
|------|------|
| gt | 大于 |
| lt | 小于 |
| eq | 等于 |
| ne | 不等于 |
| ge | 大于等于 |
| le | 小于等于 |

### 严重级别

| 级别 | 颜色 | 说明 |
|------|------|------|
| critical | 红色 | 需要立即处理 |
| warning | 黄色 | 需要关注 |
| info | 蓝色 | 信息通知 |

### 目标过滤

`target_filter` JSON 字段支持按以下维度过滤目标服务器：

```json
{
  "brand": "dell",
  "model": "R750",
  "server_ids": ["uuid1", "uuid2"],
  "data_center_id": "uuid",
  "department": "运维部"
}
```

## 告警评估

### 评估流程

```
触发（定时/手动）
    │
    ▼
AlertEvaluationService.evaluate()
    │
    ├── 遍历所有启用的告警规则
    │
    ├── 对每条规则：
    │   │
    │   ├── 解析 target_filter → 目标服务器列表
    │   │
    │   ├── 对每台目标服务器：
    │   │   │
    │   │   ├── 获取最新指标值
    │   │   │
    │   │   ├── 比较 threshold
    │   │   │   ├── 未超阈值 → 检查是否有活跃告警需解决
    │   │   │   └── 超阈值 → 检查持续时间
    │   │   │
    │   │   └── 持续时间检查
    │   │       ├── duration=0 → 立即触发
    │   │       └── duration>0 → 检查过去 N 秒内 80% 数据点超阈值
    │   │
    │   ├── 创建 AlertEvent（firing）
    │   │
    │   └── 发布 ALERT_TRIGGERED 事件
    │
    └── 解决已恢复的告警
        ├── 更新 AlertEvent.status → resolved
        └── 发布 ALERT_RESOLVED 事件
```

### 持续时间判断

当规则配置了 `duration > 0` 时，采用 80% 数据点策略：

1. 查询过去 `duration` 秒内的所有指标数据点
2. 计算超阈值的数据点比例
3. 比例 ≥ 80% → 触发告警
4. 比例 < 80% → 不触发（抖动容忍）

### 告警去重

- 同一规则 + 同一服务器，只保留一条 `firing` 状态的告警
- 已有 `firing` 告警时，不重复创建
- 指标恢复时，自动将 `firing` → `resolved`

## 告警事件管理

### 事件状态流转

```
firing ──▶ acknowledged ──▶ resolved
  │              │
  │              └── 仍可能自动 resolved
  │
  └──▶ suppressed（人工抑制，不再通知）
```

| 状态 | 说明 |
|------|------|
| firing | 告警触发中 |
| acknowledged | 已确认（人工确认已知悉） |
| resolved | 已恢复（指标回到正常） |
| suppressed | 已抑制（暂停通知） |

### 事件操作

| 操作 | 接口 | 说明 |
|------|------|------|
| 确认 | `POST /events/acknowledge` | 标记为已确认，记录确认人 |
| 抑制 | `POST /events/suppress` | 暂停通知 |
| 统计 | `GET /events/stats` | 按严重级别/状态统计 |

## 通知服务

### 通知渠道

| 渠道类型 | 实现方式 | 说明 |
|----------|----------|------|
| email | aiosmtplib | 异步 SMTP 邮件发送 |
| webhook | httpx | HTTP 请求（支持 GET/POST/PUT/PATCH/DELETE） |
| dingtalk | httpx | 钉钉机器人（HMAC 签名，text/markdown 格式） |
| wecom | httpx | 企业微信机器人（text/markdown 格式） |
| lark | httpx | 飞书机器人（签名验证，interactive 卡片格式） |

### 通知流程

```
告警事件触发
    │
    ▼
AlertEvent.notification_sent = false
    │
    ▼
查询关联的 notification_channels
    │
    ▼
逐渠道发送通知
    │
    ├── 成功 → NotificationLog.status = sent
    │
    └── 失败 → NotificationLog.status = failed
               NotificationLog.retry_count += 1
               │
               └── 可手动重试
                   POST /notifications/retry
```

### 通知重试

- 失败的通知记录 `retry_count`
- 手动触发重试：`POST /audit/notifications/retry`
- 批量重试：选中多条失败/重试中的记录

## 配置项

| 配置 | 环境变量 | 默认值 | 说明 |
|------|----------|--------|------|
| 采集间隔 | METRIC_COLLECT_INTERVAL | 60 | 指标采集间隔（秒） |
| BMC 连接超时 | BMC_CONNECT_TIMEOUT | 10 | BMC 连接超时（秒） |
| BMC 读取超时 | BMC_READ_TIMEOUT | 30 | BMC 读取超时（秒） |
| 功能开关 | FEATURE_MONITORING_ENABLED | true | 是否启用监控 |
