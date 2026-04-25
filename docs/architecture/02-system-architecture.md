# 系统架构设计

## 架构总览

OpsNexus 采用前后端分离的微服务友好架构，后端基于 FastAPI 异步框架，前端基于 Vue 3 + PrimeVue 组件库。

```
┌─────────────────────────────────────────────────────────────┐
│                        用户浏览器                            │
│              Vue 3 + PrimeVue 4 + Tailwind CSS              │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP / WebSocket
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      Nginx 反向代理                          │
│              静态资源托管 + API 转发 + WebSocket              │
└──────────────────────────┬──────────────────────────────────┘
                           │
            ┌──────────────┴──────────────┐
            ▼                             ▼
┌─────────────────────┐       ┌─────────────────────────────┐
│   前端静态资源        │       │      FastAPI 后端            │
│   (Vite 构建)        │       │                             │
└─────────────────────┘       │  ┌───────────────────────┐  │
                              │  │     中间件栈            │  │
                              │  │  CORS → 限流 → 日志    │  │
                              │  │      → 审计             │  │
                              │  └───────────┬───────────┘  │
                              │              │               │
                              │  ┌───────────▼───────────┐  │
                              │  │     业务模块层          │  │
                              │  │  System │ Knowledge    │  │
                              │  │  Asset  │ Monitor      │  │
                              │  │  Outband│ AutoOps      │  │
                              │  │  Audit  │ Integrations │  │
                              │  └───────────┬───────────┘  │
                              │              │               │
                              │  ┌───────────▼───────────┐  │
                              │  │     基础设施层          │  │
                              │  │  适配器 │ 缓存 │ 事件   │  │
                              │  │  安全   │ 数据库 │ 限流  │  │
                              │  └───────────────────────┘  │
                              └──────────────┬──────────────┘
                                             │
                  ┌──────────────┬────────────┼────────────┬──────────────┐
                  ▼              ▼            ▼            ▼              ▼
           ┌──────────┐  ┌──────────┐  ┌──────────┐ ┌──────────┐ ┌──────────┐
           │PostgreSQL│  │  Redis   │  │ RabbitMQ │ │  MinIO   │ │ RAGFlow  │
           │+Timescale│  │  缓存/锁 │  │ 事件总线 │ │ 对象存储 │ │ 知识引擎 │
           └──────────┘  └──────────┘  └──────────┘ └──────────┘ └──────────┘
```

## 分层架构

### 后端分层

```
Router (路由层)
  │  请求校验、权限检查、响应格式化
  │
  ▼
Service (服务层)
  │  业务逻辑编排、事务管理、事件发布
  │
  ▼
Repository (数据访问层)
  │  ORM 查询封装、数据映射
  │
  ▼
Model (数据模型层)
     SQLAlchemy 模型定义、表结构映射
```

### 前端分层

```
Views (页面组件)
  │  页面布局、用户交互、数据展示
  │
  ▼
API (接口层)
  │  HTTP 请求封装、响应处理
  │
  ▼
Stores (状态层)
  │  全局状态管理（Pinia）、认证状态
  │
  ▼
Router (路由层)
     路由配置、导航守卫、权限控制
```

## 模块划分

### 后端模块

| 模块 | 前缀 | 职责 |
|------|------|------|
| system | `/api/v1/system` | 认证、用户、角色、权限、配置、通知渠道 |
| knowledge | `/api/v1/knowledge` | AI 知识问答、SEL 查询、固件矩阵、对话、收藏 |
| asset | `/api/v1/asset` | 数据中心、机柜、服务器、BMC 凭据 |
| monitor | `/api/v1/monitor` | 指标定义、指标数据、告警规则、告警事件、仪表盘 |
| outband | `/api/v1/outband` | BMC 连接、电源控制、传感器、SEL、固件、KVM |
| autoops | `/api/v1/autoops` | 任务定义、任务实例、固件包、巡检策略 |
| audit | `/api/v1/audit` | 审计日志、通知记录 |
| integrations | `/api/v1/integrations/netbox` | NetBox DCIM 双向同步 |

### 前端页面模块

| 模块 | 路由前缀 | 页面 |
|------|----------|------|
| 知识库 | `/knowledge` | 知识助手、SEL 查询、固件矩阵、对话历史、收藏 |
| 资产 | `/asset` | 数据中心、机柜、服务器列表、服务器详情 |
| 监控 | `/monitor` | 监控仪表盘、告警规则、告警事件 |
| 带外 | `/outband` | 带外管理、SEL 日志、KVM 会话 |
| 审计 | `/audit` | 操作日志、通知记录 |
| 系统 | `/system` | 用户、角色、配置、通知渠道 |

## 中间件栈

请求按 LIFO 顺序经过以下中间件（最后注册的最先执行）：

```
请求 → AuditMiddleware → LoggingMiddleware → RateLimitMiddleware → CORSMiddleware → 路由处理
```

| 中间件 | 职责 |
|--------|------|
| CORSMiddleware | 跨域资源共享，允许前端开发服务器访问 |
| RateLimitMiddleware | 基于 Redis 的固定窗口限流（60 次/分钟 + 10 次突发） |
| LoggingMiddleware | 注入 request_id/correlation_id，记录请求耗时 |
| AuditMiddleware | 自动拦截写操作，解析 JWT 记录审计日志 |

## 事件驱动架构

系统通过 RabbitMQ 事件总线实现模块间解耦通信：

```
┌──────────┐  publish   ┌──────────────┐  subscribe  ┌──────────┐
│ Monitor  │───────────▶│   RabbitMQ   │───────────▶│  Audit   │
│ Service  │            │ Topic        │            │ Service  │
└──────────┘            │ Exchange     │            └──────────┘
                        │              │
┌──────────┐  publish   │ opsnexus.    │  subscribe  ┌──────────┐
│ AutoOps  │───────────▶│ events       │───────────▶│ Notifi-  │
│ Service  │            │              │            │ cation   │
└──────────┘            └──────────────┘            └──────────┘
```

### 事件类型

| 类别 | 事件 | 说明 |
|------|------|------|
| Server | SERVER_CREATED / SERVER_UPDATED / SERVER_DELETED / SERVER_STATUS_CHANGED | 服务器生命周期 |
| BMC | BMC_ONLINE / BMC_OFFLINE / BMC_ERROR | BMC 状态变更 |
| Alert | ALERT_TRIGGERED / ALERT_RESOLVED / ALERT_ACKNOWLEDGED | 告警状态流转 |
| Task | TASK_CREATED / TASK_STARTED / TASK_COMPLETED / TASK_FAILED / TASK_CANCELLED | 任务执行状态 |

## 数据流

### BMC 数据采集流

```
定时触发/手动触发
       │
       ▼
MetricCollectionService.collect()
       │
       ├── 解析目标服务器列表
       │
       ├── Redis 分布式锁防重复采集
       │
       ├── Adapter.get_sensor_data()  ──▶  BMC (Redfish API)
       │
       ├── 映射为标准指标名
       │
       ├── 批量写入 MetricData
       │
       └── 更新 Server.bmc_status
```

### 告警评估流

```
定时触发/手动触发
       │
       ▼
AlertEvaluationService.evaluate()
       │
       ├── 遍历启用的告警规则
       │
       ├── 解析目标服务器
       │
       ├── 获取最新指标值
       │
       ├── 阈值比较 + 持续时长判断（80% 数据点超阈值）
       │
       ├── 创建/解决 AlertEvent
       │
       └── 发布 ALERT_TRIGGERED/ALERT_RESOLVED 事件
```

### 知识查询流

```
用户提问
    │
    ▼
KnowledgeService.query()
    │
    ├── query_type = semantic
    │   ├── Redis 缓存查询
    │   ├── RAGFlow API 语义检索
    │   └── 降级到本地关键词匹配
    │
    ├── query_type = structured
    │   ├── SEL 事件码表查询
    │   └── 固件兼容性表查询
    │
    └── query_type = hybrid
        ├── 合并 semantic + structured 结果
        └── 去重排序
```
