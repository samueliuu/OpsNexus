# OpsNexus - 服务器运维知识助手平台

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-samueliuu/OpsNexus-lightgrey.svg)](https://github.com/samueliuu/OpsNexus)

## 项目简介

OpsNexus 是一个面向数据中心运维的**服务器运维知识助手平台**，集成了 RAG 知识问答、带外管理（BMC）、资产管理和自动化运维功能。

### 核心功能

- 🤖 **RAG 知识助手** - 基于 RAGFlow 的服务器运维知识库，支持故障排查、用户手册、API 参考
- 🔌 **多品牌 BMC 管理** - 支持 Dell/HPE/Lenovo/Huawei/H3C/Inspur/Sugon/xFusion 8 大品牌
- 📊 **资产管理** - 服务器全生命周期管理，支持 NetBox DCIM 集成
- 🔍 **SEL 码查询** - 8 大品牌服务器 SEL 事件码快速查询和故障诊断
- 📦 **固件兼容矩阵** - 服务器固件版本兼容性查询
- 🌐 **带外管理** - Redfish/IPMI 协议的服务器远程管理
- 📈 **监控告警** - 服务器健康状态监控和告警

### 技术栈

**后端**
- FastAPI + SQLAlchemy (Async)
- PostgreSQL + Redis
- DMTF python-redfish-library
- RAGFlow (知识引擎)

**前端**
- Vue 3 + Vite
- Element Plus
- TypeScript

**运维**
- Docker + Docker Compose
- Alembic (数据库迁移)

## 快速开始

### 环境要求

- Python 3.12+
- PostgreSQL 15+
- Redis 7+
- Node.js 18+
- Docker & Docker Compose (可选)

### 后端启动

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件配置数据库连接、RAGFlow API 等

# 运行数据库迁移
alembic upgrade head

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### Docker 部署

```bash
docker-compose up -d
```

## 项目结构

```
OpsNexus/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── adapters/          # BMC 品牌适配器
│   │   ├── core/              # 核心模块
│   │   ├── modules/           # 业务模块
│   │   └── integrations/      # 第三方集成
│   ├── alembic/               # 数据库迁移
│   └── requirements.txt
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── api/               # API 客户端
│   │   ├── components/        # 组件
│   │   └── views/             # 页面
│   └── package.json
├── docs/                       # 文档
├── docker-compose.yml
└── README.md
```

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

## API 文档

启动后端后访问：http://localhost:8000/docs

### 主要 API 端点

```
GET  /api/v1/outband/servers          # 服务器列表
POST /api/v1/outband/servers          # 添加服务器
GET  /api/v1/outband/servers/{id}/health  # 健康检查
POST /api/v1/outband/servers/{id}/power   # 电源控制
GET  /api/v1/outband/servers/{id}/sel     # SEL 日志
GET  /api/v1/knowledge/query          # 知识问答
POST /api/v1/integrations/netbox/sync/from-netbox  # NetBox 同步
```

## 配置说明

### 环境变量

```env
# 数据库
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/opsnexus
REDIS_URL=redis://localhost:6379/0

# RAGFlow
RAGFLOW_API_URL=http://localhost:9380
RAGFLOW_API_KEY=your-api-key

# NetBox (可选)
NETBOX_API_URL=https://netbox.example.com
NETBOX_API_TOKEN=your-token
NETBOX_SYNC_ENABLED=true
```

## 开发指南

### 添加新品牌适配器

1. 在 `backend/app/adapters/` 创建新目录
2. 继承 `ServerAdapter` 基类
3. 使用 `@register_adapter("brand")` 装饰器
4. 实现必要的查询方法

### 数据库迁移

```bash
# 创建新迁移
alembic revision --autogenerate -m "Add new table"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License

## 联系方式

- 项目地址：https://github.com/your-username/OpsNexus
- 问题反馈：https://github.com/your-username/OpsNexus/issues
