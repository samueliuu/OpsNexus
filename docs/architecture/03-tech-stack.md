# 技术栈

## 后端技术栈

| 类别 | 技术 | 版本 | 说明 |
|------|------|------|------|
| Web 框架 | FastAPI | - | 高性能异步 Python Web 框架 |
| ASGI 服务器 | Uvicorn | - | 基于 uvloop 的 ASGI 服务器 |
| ORM | SQLAlchemy | 2.0 | 异步引擎，mapped_column 声明式映射 |
| 数据库 | PostgreSQL | - | 主数据库，asyncpg 异步驱动 |
| 时序扩展 | TimescaleDB | - | metric_data 超表，高效时序数据存储 |
| 缓存 | Redis | - | aioredis 异步客户端，缓存/锁/限流 |
| 消息队列 | RabbitMQ | - | aio_pika 异步客户端，Topic Exchange |
| 对象存储 | MinIO | - | 固件包等大文件存储 |
| 认证 | JWT | - | python-jose，HS256 签名 |
| 密码哈希 | bcrypt | - | passlib 封装 |
| 加密 | Fernet | - | cryptography 库，BMC 凭证加密 |
| BMC 通信 | Redfish | - | DMTF python-redfish-library + httpx 异步 |
| AI 知识 | RAGFlow | - | 语义检索引擎，REST API 集成 |
| HTTP 客户端 | httpx | - | 异步 HTTP 客户端，BMC/Webhook 通信 |
| 数据库迁移 | Alembic | - | SQLAlchemy 迁移工具 |
| 配置管理 | pydantic-settings | - | BaseSettings + .env 文件 |
| 日志 | structlog | - | 结构化日志，JSON/Console 双模式 |
| 数据校验 | Pydantic | 2.x | 请求/响应 Schema 定义 |
| 邮件发送 | aiosmtplib | - | 异步 SMTP 客户端 |
| DCIM 集成 | NetBox | - | REST API 双向同步 |

## 前端技术栈

| 类别 | 技术 | 版本 | 说明 |
|------|------|------|------|
| 框架 | Vue | 3.4 | Composition API + TypeScript |
| 构建工具 | Vite | 5.2 | 快速开发服务器和构建 |
| 状态管理 | Pinia | 2.1 | Vue 3 官方状态管理 |
| 路由 | Vue Router | 4.3 | History 模式，嵌套路由 |
| UI 组件库 | PrimeVue | 4.5 | Aura 主题，暗色模式支持 |
| CSS | Tailwind CSS | 4.2 | 原子化 CSS + tailwindcss-primeui |
| HTTP 客户端 | Axios | 1.6 | 请求/响应拦截器，Token 自动刷新 |
| 图表 | ECharts | 5.5 | vue-echarts 6.6 封装 |
| 日期处理 | dayjs | 1.11 | 轻量日期库 |
| 进度条 | NProgress | 0.2 | 路由切换进度指示 |

## 基础设施

| 组件 | 说明 |
|------|------|
| Nginx | 反向代理，静态资源托管，WebSocket 代理 |
| Docker | 容器化部署，docker-compose 编排 |
| PostgreSQL | 主数据存储 + TimescaleDB 时序扩展 |
| Redis | 缓存、分布式锁、限流计数器、WebSocket 票据 |
| RabbitMQ | 事件总线，模块间异步通信 |
| MinIO | S3 兼容对象存储，固件包管理 |
| RAGFlow | AI 语义检索引擎，知识库问答 |

## 技术选型理由

### FastAPI

- 原生 async/await 支持，适合 BMC 高延迟 I/O 操作
- 自动 OpenAPI 文档生成
- Pydantic 数据校验与类型安全
- 依赖注入系统天然支持权限检查

### SQLAlchemy 2.0 异步

- mapped_column 声明式映射，类型安全
- asyncpg 驱动，与 FastAPI 异步模型一致
- 连接池管理（pool_size=20, max_overflow=10）

### Vue 3 + PrimeVue 4

- Composition API 逻辑复用性强
- PrimeVue 4 企业级组件丰富（DataTable, TreeSelect, Toast 等）
- 内置暗色模式支持
- Tailwind CSS 原子化样式灵活定制

### RabbitMQ 事件总线

- Topic Exchange 灵活路由
- 消息持久化保证可靠投递
- 解耦模块间通信（监控→告警→通知链路）

### TimescaleDB

- 自动分区和压缩时序数据
- 与 PostgreSQL 无缝集成
- 适合监控指标的高吞吐写入和范围查询
