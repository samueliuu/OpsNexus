# 衡驭OpsNexus智能服务器运维系统

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue-3.4+-brightgreen.svg)](https://vuejs.org/)
[![PrimeVue](https://img.shields.io/badge/PrimeVue-4.5+-orange.svg)](https://primevue.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-samueliuu/OpsNexus-lightgrey.svg)](https://github.com/samueliuu/OpsNexus)

面向数据中心的智能服务器运维管理平台，集成 RAG 知识问答、多品牌 BMC 带外管理、资产全生命周期管理、监控告警与自动化运维。

## 核心功能

### 🤖 知识助手
- **RAG 知识问答** — 基于 RAGFlow 的服务器运维知识库，支持故障排查、用户手册、API 参考等智能问答
- **SEL 事件码查询** — 支持 Dell / HPE / Lenovo / Huawei / H3C / Inspur / Sugon / xFusion 8 大品牌 SEL 事件码快速查询与故障诊断
- **固件兼容矩阵** — 服务器固件版本兼容性查询与升级建议
- **对话历史与收藏** — 知识问答对话记录、收藏管理

### 🔌 带外管理
- **多品牌 BMC 适配** — 统一 Redfish/IPMI 协议适配层，支持 8 大服务器品牌
- **服务器健康检查** — 实时 BMC 连接状态与硬件健康监测
- **电源控制** — 远程开关机、重启、强制关机等操作
- **SEL 日志管理** — 系统事件日志采集、查询与确认
- **KVM 远程控制** — 基于 HTML5 的远程控制台会话管理
- **固件清单** — 服务器固件版本查询与更新状态跟踪

### 📊 资产管理
- **数据中心管理** — 多数据中心、机房、机柜层级管理
- **服务器全生命周期** — 从上架、运行、维护到下架的完整管理
- **NetBox DCIM 集成** — 支持 NetBox 数据双向同步

### 📈 监控告警
- **指标采集** — 通过 BMC 采集 CPU 温度、功耗、风扇转速等硬件指标
- **告警规则** — 灵活的阈值告警规则配置
- **告警事件** — 告警触发、确认、恢复全流程管理
- **多渠道通知** — 邮件、钉钉、企业微信通知渠道

### ⚙️ 自动化运维
- **任务编排** — 可定义多步骤自动化运维任务
- **审批流程** — 危险操作需审批后执行
- **巡检策略** — 定期自动巡检与报告
- **固件包管理** — 固件升级包上传与版本管理

### 🔐 系统管理
- **用户管理** — 用户注册、角色分配、权限控制
- **RBAC 权限** — 基于角色的细粒度权限控制
- **审计日志** — 全操作审计追踪
- **系统配置** — 运行时参数配置管理

## 技术栈

**后端**
- Python 3.12+ / FastAPI 0.115
- SQLAlchemy 2.0 (Async) / PostgreSQL (TimescaleDB)
- Redis / RabbitMQ / MinIO
- DMTF python-redfish-library
- RAGFlow (知识引擎)
- Alembic (数据库迁移)

**前端**
- Vue 3.4 / TypeScript 5.4
- PrimeVue 4 + Sakai 布局
- Tailwind CSS 4
- ECharts / vue-echarts
- Pinia / Vue Router 4
- Axios / Day.js

**基础设施**
- Docker / Docker Compose
- Nginx 反向代理
- TimescaleDB (时序数据)

## 项目结构

```
OpsNexus/
├── backend/                        # 后端服务
│   ├── app/
│   │   ├── adapters/               # BMC 品牌适配器
│   │   │   ├── base/               # 适配器基类与 Redfish 通用实现
│   │   │   ├── dell/               # Dell iDRAC 适配器
│   │   │   ├── hpe/                # HPE iLO 适配器
│   │   │   ├── lenovo/             # Lenovo XCC 适配器
│   │   │   ├── huawei/             # Huawei iBMC 适配器
│   │   │   ├── h3c/                # H3C HDM 适配器
│   │   │   ├── inspur/             # Inspur ISBMC 适配器
│   │   │   ├── sugon/              # Sugon BMC 适配器
│   │   │   └── xfusion/            # xFusion iBMC 适配器
│   │   ├── core/                   # 核心模块
│   │   │   ├── config.py           # 配置管理
│   │   │   ├── database.py         # 数据库连接
│   │   │   ├── security.py         # JWT 认证与加密
│   │   │   ├── dependencies.py     # 依赖注入
│   │   │   ├── exceptions.py       # 异常定义
│   │   │   ├── middleware.py       # 限流中间件
│   │   │   ├── events.py           # 事件总线
│   │   │   ├── cache.py            # Redis 缓存
│   │   │   ├── logging.py          # 结构化日志
│   │   │   └── ratelimit.py        # 限流算法
│   │   ├── modules/                # 业务模块
│   │   │   ├── system/             # 用户/角色/权限/配置/通知渠道
│   │   │   ├── asset/              # 数据中心/机柜/服务器
│   │   │   ├── monitor/            # 指标/告警规则/告警事件
│   │   │   ├── outband/            # BMC管理/SEL/KVM/固件
│   │   │   ├── knowledge/          # RAG问答/SEL查询/固件矩阵/收藏
│   │   │   ├── autoops/            # 任务编排/巡检/固件包
│   │   │   └── audit/              # 审计日志/通知日志
│   │   ├── integrations/           # 第三方集成
│   │   │   ├── netbox_client.py    # NetBox API 客户端
│   │   │   └── netbox_sync.py      # NetBox 数据同步
│   │   └── main.py                 # 应用入口
│   ├── alembic/                    # 数据库迁移
│   ├── scripts/                    # 运维脚本
│   ├── seed_demo.py                # 演示种子数据
│   ├── ruff.toml                   # Ruff 配置
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                       # 前端应用
│   ├── src/
│   │   ├── api/                    # API 客户端
│   │   ├── layout/                 # 布局组件 (Sakai)
│   │   ├── layouts/                # 页面布局
│   │   ├── router/                 # 路由配置
│   │   ├── stores/                 # Pinia 状态管理
│   │   ├── views/                  # 页面视图
│   │   │   ├── knowledge/          # 知识助手/SEL查询/固件矩阵/对话/收藏
│   │   │   ├── asset/              # 数据中心/机柜/服务器
│   │   │   ├── monitor/            # 监控面板/告警规则/告警事件
│   │   │   ├── outband/            # 带外管理/SEL日志/KVM会话
│   │   │   ├── audit/              # 审计日志/通知日志
│   │   │   └── system/             # 用户/角色/配置/通知渠道
│   │   ├── App.vue
│   │   ├── main.ts
│   │   └── style.css
│   ├── .eslintrc.cjs
│   ├── Dockerfile
│   ├── vite.config.ts
│   └── package.json
├── nginx/                          # Nginx 配置
├── docs/                           # 架构文档
├── docker-compose.yml
└── README.md
```

## 支持的服务器品牌

| 品牌 | BMC 类型 | 适配器 | 支持程度 |
|------|---------|--------|---------|
| Dell | iDRAC 9+ | `adapters/dell` | ✅ 完整支持 |
| HPE | iLO 5/6 | `adapters/hpe` | ✅ 完整支持 |
| Lenovo | XCC/XCC3 | `adapters/lenovo` | ✅ 完整支持 |
| Huawei | iBMC | `adapters/huawei` | ✅ 完整支持 |
| H3C | HDM/HDM2/HDM3 | `adapters/h3c` | ✅ 完整支持 |
| Inspur | OpenRMC/ISBMC | `adapters/inspur` | ✅ 完整支持 |
| Sugon | BMC | `adapters/sugon` | ✅ 基本支持 |
| xFusion | iBMC | `adapters/xfusion` | ✅ 完整支持 |

## 快速开始

### 环境要求

- Python 3.12+
- PostgreSQL 15+ (推荐 TimescaleDB)
- Redis 7+
- Node.js 18+
- Docker & Docker Compose (可选)

### 方式一：Docker Compose（推荐）

```bash
git clone https://github.com/samueliuu/OpsNexus.git
cd OpsNexus
docker-compose up -d
```

启动后访问：
- 前端：http://localhost
- 后端 API 文档：http://localhost:8000/docs

### 方式二：本地开发

**后端**

```bash
cd backend

python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/Mac

pip install -r requirements.txt

cp .env.example .env
# 编辑 .env 配置数据库连接、RAGFlow API 等

alembic upgrade head

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**前端**

```bash
cd frontend

npm install

npm run dev
```

**演示数据**

```bash
cd backend
python seed_demo.py
```

默认管理员账号：`admin` / `admin123`

## API 文档

启动后端后访问 Swagger UI：http://localhost:8000/docs

### 主要 API 端点

```
# 认证
POST /api/v1/system/auth/login          # 登录
POST /api/v1/system/auth/register       # 注册
POST /api/v1/system/auth/refresh        # 刷新令牌

# 知识助手
GET  /api/v1/knowledge/query            # 知识问答
GET  /api/v1/knowledge/sel-codes        # SEL 事件码查询
GET  /api/v1/knowledge/firmware-matrix  # 固件兼容矩阵

# 资产管理
GET  /api/v1/asset/data-centers         # 数据中心列表
GET  /api/v1/asset/servers              # 服务器列表
GET  /api/v1/asset/servers/{id}         # 服务器详情

# 带外管理
GET  /api/v1/outband/servers            # BMC 服务器列表
POST /api/v1/outband/servers/{id}/power # 电源控制
GET  /api/v1/outband/servers/{id}/sel   # SEL 日志
GET  /api/v1/outband/servers/{id}/health # 健康检查

# 监控告警
GET  /api/v1/monitor/alert-rules        # 告警规则列表
GET  /api/v1/monitor/alert-events       # 告警事件列表

# 自动化运维
GET  /api/v1/autoops/tasks              # 自动化任务列表

# 系统管理
GET  /api/v1/system/users               # 用户列表
GET  /api/v1/system/roles               # 角色列表

# 第三方集成
POST /api/v1/integrations/netbox/sync/from-netbox  # NetBox 同步
```

## 配置说明

### 环境变量

```env
# 数据库
DATABASE_URL=postgresql+asyncpg://opsnexus:opsnexus_dev@localhost:5432/opsnexus
REDIS_URL=redis://localhost:6379/0

# RAGFlow 知识引擎
RAGFLOW_API_URL=http://localhost:9380
RAGFLOW_API_KEY=your-api-key

# NetBox DCIM (可选)
NETBOX_API_URL=https://netbox.example.com
NETBOX_API_TOKEN=your-token
NETBOX_SYNC_ENABLED=true

# JWT
JWT_SECRET_KEY=your-strong-random-key-at-least-32-chars
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

## 开发指南

### 添加新品牌适配器

1. 在 `backend/app/adapters/` 创建新目录
2. 继承 `ServerAdapter` 基类
3. 使用 `@register_adapter("brand")` 装饰器注册
4. 实现必要的抽象方法（`get_system_info`, `get_power_state`, `get_sel_logs` 等）

### 数据库迁移

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
```

### 代码检查

```bash
# 后端
cd backend && ruff check . --fix

# 前端
cd frontend && npm run lint
cd frontend && npx vue-tsc --noEmit
```

## 许可证

Apache License 2.0

## 联系方式

- 项目地址：https://github.com/samueliuu/OpsNexus
- 问题反馈：https://github.com/samueliuu/OpsNexus/issues
