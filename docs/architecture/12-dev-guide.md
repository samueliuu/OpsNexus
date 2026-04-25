# 开发指南

## 环境准备

### 前置依赖

| 工具 | 版本 | 说明 |
|------|------|------|
| Python | 3.11+ | 后端运行时 |
| Node.js | 20+ | 前端构建 |
| Docker | 24+ | 容器化部署 |
| Docker Compose | 2.20+ | 服务编排 |
| Git | 2.40+ | 版本控制 |

### 本地开发环境

#### 1. 克隆仓库

```bash
git clone https://github.com/samueliuu/OpsNexus.git
cd OpsNexus
```

#### 2. 启动基础设施

```bash
docker compose up -d postgres redis rabbitmq minio
```

#### 3. 后端设置

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填写数据库、Redis、RabbitMQ 连接信息

# 数据库迁移
alembic upgrade head

# 初始化种子数据
python seed_demo.py

# 启动开发服务器
uvicorn app.main:app --reload --port 8000
```

#### 4. 前端设置

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
# 访问 http://localhost:3000
```

## 项目结构

```
OpsNexus/
├── backend/
│   ├── alembic/                  # 数据库迁移
│   │   ├── versions/             # 迁移脚本
│   │   ├── env.py
│   │   └── script.py.mako
│   ├── app/
│   │   ├── adapters/             # BMC 适配器
│   │   │   ├── base/             # 基类和注册表
│   │   │   ├── dell/             # Dell iDRAC
│   │   │   ├── hpe/              # HPE iLO
│   │   │   ├── lenovo/           # Lenovo XCC
│   │   │   ├── huawei/           # 华为 iBMC
│   │   │   ├── inspur/           # 浪潮 OpenRMC
│   │   │   ├── h3c/              # H3C HDM
│   │   │   ├── sugon/            # 曙光
│   │   │   └── xfusion/          # 超聚变
│   │   ├── core/                 # 核心基础设施
│   │   │   ├── cache.py          # Redis 缓存/分布式锁
│   │   │   ├── compat.py         # 跨数据库兼容类型
│   │   │   ├── config.py         # 配置管理
│   │   │   ├── database.py       # 数据库引擎
│   │   │   ├── dependencies.py   # 依赖注入
│   │   │   ├── events.py         # 事件总线
│   │   │   ├── exceptions.py     # 异常体系
│   │   │   ├── logging.py        # 结构化日志
│   │   │   ├── middleware.py      # 限流中间件
│   │   │   ├── ratelimit.py      # 限流器
│   │   │   └── security.py       # 安全（JWT/加密）
│   │   ├── integrations/         # 外部集成
│   │   │   ├── netbox_client.py  # NetBox 客户端
│   │   │   ├── netbox_sync.py    # NetBox 同步
│   │   │   └── router.py         # 集成路由
│   │   ├── modules/              # 业务模块
│   │   │   ├── asset/            # 资产管理
│   │   │   ├── audit/            # 审计日志
│   │   │   ├── autoops/          # 自动化运维
│   │   │   ├── knowledge/        # 知识服务
│   │   │   ├── monitor/          # 监控告警
│   │   │   ├── outband/          # 带外管理
│   │   │   └── system/           # 系统管理
│   │   └── main.py               # 应用入口
│   ├── scripts/
│   │   └── init_db.py            # 数据库初始化脚本
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── ruff.toml
│   └── seed_demo.py              # 种子数据
├── frontend/
│   ├── src/
│   │   ├── api/                  # API 调用层
│   │   │   ├── asset.ts
│   │   │   ├── knowledge.ts
│   │   │   ├── monitor.ts
│   │   │   ├── outband-audit.ts
│   │   │   ├── request.ts        # Axios 实例
│   │   │   └── system.ts
│   │   ├── layout/               # 布局组件
│   │   │   ├── composables/
│   │   │   ├── AppFooter.vue
│   │   │   ├── AppLayout.vue
│   │   │   ├── AppMenu.vue
│   │   │   ├── AppMenuItem.vue
│   │   │   ├── AppSidebar.vue
│   │   │   ├── AppTopbar.vue
│   │   │   └── AppConfigurator.vue
│   │   ├── layouts/
│   │   │   └── MainLayout.vue
│   │   ├── router/
│   │   │   └── index.ts
│   │   ├── stores/
│   │   │   └── auth.ts
│   │   ├── views/                # 页面组件
│   │   │   ├── asset/
│   │   │   ├── audit/
│   │   │   ├── knowledge/
│   │   │   ├── monitor/
│   │   │   ├── outband/
│   │   │   ├── system/
│   │   │   ├── Dashboard.vue
│   │   │   ├── Home.vue
│   │   │   ├── Login.vue
│   │   │   ├── Register.vue
│   │   │   └── NotFound.vue
│   │   ├── App.vue
│   │   ├── env.d.ts
│   │   ├── main.ts
│   │   └── style.css
│   ├── Dockerfile
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── nginx/
│   └── dev.conf
├── docs/
│   └── architecture/             # 架构文档
├── docker-compose.yml
├── LICENSE
└── README.md
```

## 开发规范

### 后端模块结构

每个业务模块遵循统一结构：

```
modules/{module_name}/
├── __init__.py
├── models.py        # SQLAlchemy 模型
├── schemas.py       # Pydantic Schema（请求/响应）
├── repository.py    # 数据访问层
├── service.py       # 业务逻辑层
└── router.py        # 路由定义
```

#### 添加新模块步骤

1. 在 `modules/` 下创建模块目录
2. 定义 `models.py`（SQLAlchemy 模型）
3. 定义 `schemas.py`（Pydantic 请求/响应模型）
4. 实现 `repository.py`（数据访问）
5. 实现 `service.py`（业务逻辑）
6. 定义 `router.py`（API 路由）
7. 在 `main.py` 中注册路由
8. 创建 Alembic 迁移脚本

### 前端页面结构

每个页面组件遵循统一模式：

```vue
<template>
  <!-- 页面布局 -->
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { apiName } from '@/api/module'

const data = ref([])
const loading = ref(false)

const loadData = async () => {
  loading.value = true
  try {
    const response = await apiName.list()
    data.value = response.data.items
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>
```

### 代码风格

#### 后端

- 使用 Ruff 进行代码检查和格式化
- 配置文件：`backend/ruff.toml`
- 异步优先：所有 I/O 操作使用 async/await
- 类型注解：所有函数参数和返回值

#### 前端

- ESLint + TypeScript 严格模式
- Composition API + `<script setup>`
- PrimeVue 组件优先

### Git 工作流

```
main (master)
  │
  ├── feature/xxx    功能分支
  ├── fix/xxx        修复分支
  └── docs/xxx       文档分支
```

Commit 消息格式：

```
type(scope): subject

type: feat/fix/docs/style/refactor/test/chore
scope: backend/frontend/docs
```

## 数据库迁移

### 创建迁移

```bash
cd backend
alembic revision --autogenerate -m "描述"
```

### 执行迁移

```bash
alembic upgrade head
```

### 回滚

```bash
alembic downgrade -1    # 回滚一个版本
alembic downgrade base  # 回滚到初始状态
```

## 测试

### 后端测试

```bash
cd backend
pytest
```

### 前端测试

```bash
cd frontend
npm run test
```

### 类型检查

```bash
cd frontend
npm run type-check
```

## 常用命令

### Docker

```bash
# 启动所有服务
docker compose up -d

# 查看日志
docker compose logs -f backend

# 重建并启动
docker compose up -d --build

# 停止所有服务
docker compose down

# 清理数据卷
docker compose down -v
```

### 后端

```bash
# 启动开发服务器
uvicorn app.main:app --reload --port 8000

# 数据库迁移
alembic upgrade head

# 种子数据
python seed_demo.py

# 代码检查
ruff check .

# 格式化
ruff format .
```

### 前端

```bash
# 安装依赖
npm install

# 开发服务器
npm run dev

# 构建
npm run build

# 预览构建结果
npm run preview

# 代码检查
npm run lint

# 类型检查
npm run type-check
```

## 故障排查

### 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 后端启动失败 | 数据库未启动 | `docker compose up -d postgres` |
| BMC 连接超时 | 网络不通或超时太短 | 检查 BMC 网络连通性，调整 `BMC_CONNECT_TIMEOUT` |
| Token 刷新失败 | Refresh Token 过期 | 重新登录 |
| Redis 连接失败 | Redis 未启动 | `docker compose up -d redis` |
| 前端代理 502 | 后端未启动 | 启动后端开发服务器 |
| 限流 429 | 请求过于频繁 | 等待限流窗口重置，或调整 `RATE_LIMIT_REQUESTS_PER_MINUTE` |

### 日志查看

```bash
# 后端日志
docker compose logs -f backend

# 特定服务日志
docker compose logs -f postgres
docker compose logs -f redis
```

### 健康检查

```bash
# 后端健康检查
curl http://localhost:8000/api/v1/health

# 各模块健康检查
curl http://localhost:8000/api/v1/system/health
curl http://localhost:8000/api/v1/asset/health
curl http://localhost:8000/api/v1/monitor/health
```
