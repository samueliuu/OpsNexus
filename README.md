# 衡驭OpsNexus智能服务器运维系统

[![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)](https://github.com/samueliuu/OpsNexus)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue-3.4+-brightgreen.svg)](https://vuejs.org/)
[![PrimeVue](https://img.shields.io/badge/PrimeVue-4.5+-orange.svg)](https://primevue.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

面向数据中心的智能服务器运维管理平台，集成 RAG 知识问答、多品牌 BMC 带外管理、资产全生命周期管理、监控告警与自动化运维。

## 核心功能

| 模块 | 功能 |
|------|------|
| 🤖 **知识助手** | RAG 知识问答（RAGFlow）、8 大品牌 SEL 事件码查询、固件兼容矩阵、对话历史与收藏 |
| 🔌 **带外管理** | 多品牌 BMC 适配（Redfish/IPMI）、健康检查、电源控制、SEL 日志、KVM 远程控制、固件清单 |
| 📊 **资产管理** | 数据中心/机柜/服务器层级管理、全生命周期跟踪、NetBox DCIM 集成 |
| 📈 **监控告警** | BMC 硬件指标采集、阈值告警规则、告警全流程管理、邮件/钉钉/企微通知 |
| ⚙️ **自动化运维** | 多步骤任务编排、审批流程、巡检策略、固件包管理 |
| 🔐 **系统管理** | RBAC 权限控制、用户/角色管理、全操作审计日志、运行时配置 |

## 支持的服务器品牌

| 品牌 | BMC 类型 | 支持程度 |
|------|---------|---------|
| Dell | iDRAC 9+ | ✅ 完整支持 |
| HPE | iLO 5/6 | ✅ 完整支持 |
| Lenovo | XCC/XCC3 | ✅ 完整支持 |
| Huawei | iBMC | ✅ 完整支持 |
| H3C | HDM/HDM2/HDM3 | ✅ 完整支持 |
| Inspur | OpenRMC/ISBMC | ✅ 完整支持 |
| Sugon | BMC | ✅ 基本支持 |
| xFusion | iBMC | ✅ 完整支持 |

## 技术栈

**后端** — Python 3.12 / FastAPI 0.115 / SQLAlchemy 2.0 (Async) / PostgreSQL (TimescaleDB) / Redis / RabbitMQ / MinIO / DMTF python-redfish-library / RAGFlow / Alembic

**前端** — Vue 3.4 / TypeScript 5.4 / PrimeVue 4 + Sakai / Tailwind CSS 4 / ECharts / Pinia / Vue Router 4 / Axios

**基础设施** — Docker Compose / Nginx / TimescaleDB

## 快速开始

### Docker Compose（推荐）

```bash
git clone https://github.com/samueliuu/OpsNexus.git
cd OpsNexus
docker-compose up -d
```

- 前端：http://localhost
- 后端 API 文档：http://localhost:8000/docs

### 本地开发

```bash
# 后端
cd backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # 编辑 .env 配置数据库、RAGFlow 等
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 前端
cd frontend
npm install
npm run dev

# 演示数据
cd backend && python seed_demo.py
# 默认管理员：admin / admin123
```

## 项目结构

```
OpsNexus/
├── backend/
│   ├── app/
│   │   ├── adapters/          # BMC 品牌适配器 (Dell/HPE/Lenovo/Huawei/H3C/Inspur/Sugon/xFusion)
│   │   ├── core/              # 核心模块 (config/database/security/cache/logging/ratelimit)
│   │   ├── modules/           # 业务模块 (system/asset/monitor/outband/knowledge/autoops/audit)
│   │   ├── integrations/      # 第三方集成 (NetBox)
│   │   └── main.py
│   ├── alembic/               # 数据库迁移
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/               # API 客户端
│   │   ├── layout/            # 布局组件 (Sakai)
│   │   ├── views/             # 页面 (knowledge/asset/monitor/outband/audit/system)
│   │   ├── stores/            # Pinia 状态管理
│   │   └── router/            # 路由配置
│   └── package.json
├── nginx/                     # Nginx 反向代理配置
├── docs/                      # 架构设计文档
└── docker-compose.yml
```

## 配置说明

主要环境变量（完整配置见 `.env.example`）：

| 变量 | 说明 | 示例 |
|------|------|------|
| `DATABASE_URL` | PostgreSQL 连接串 | `postgresql+asyncpg://user:pass@localhost:5432/opsnexus` |
| `REDIS_URL` | Redis 连接串 | `redis://localhost:6379/0` |
| `RAGFLOW_API_URL` | RAGFlow 知识引擎地址 | `http://localhost:9380` |
| `RAGFLOW_API_KEY` | RAGFlow API 密钥 | — |
| `JWT_SECRET_KEY` | JWT 签名密钥（≥32字符） | — |
| `NETBOX_API_URL` | NetBox DCIM 地址（可选） | — |

## 开发指南

**添加新品牌适配器**

1. 在 `backend/app/adapters/` 创建新目录
2. 继承 `ServerAdapter` 基类，实现 `get_system_info` / `get_power_state` / `get_sel_logs` 等抽象方法
3. 使用 `@register_adapter("brand")` 装饰器注册

**数据库迁移**

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

**代码检查**

```bash
cd backend && ruff check . --fix
cd frontend && npm run lint
```

## 许可证

[Apache License 2.0](LICENSE)

Copyright 2026 南京诚臻晶睿信息技术有限公司

## 联系方式

- 项目地址：https://github.com/samueliuu/OpsNexus
- 问题反馈：https://github.com/samueliuu/OpsNexus/issues
- 邮箱：support@pricenexus.cn
