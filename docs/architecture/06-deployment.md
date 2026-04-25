# 部署架构

## 部署总览

OpsNexus 使用 Docker Compose 进行容器化部署，包含以下服务：

```
┌──────────────────────────────────────────────────────────────┐
│                        Docker Compose                         │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  Nginx   │  │ Frontend │  │ Backend  │  │  Redis   │    │
│  │  :80/443 │  │  (构建)  │  │  :8000   │  │  :6379   │    │
│  └────┬─────┘  └──────────┘  └────┬─────┘  └──────────┘    │
│       │                            │                         │
│       │         ┌──────────┐  ┌────┴─────┐  ┌──────────┐    │
│       │         │ RabbitMQ │  │PostgreSQL│  │  MinIO   │    │
│       │         │  :5672   │  │  :5432   │  │  :9000   │    │
│       │         └──────────┘  └──────────┘  └──────────┘    │
│       │                                                     │
│       │         ┌──────────┐                                │
│       └────────▶│ RAGFlow  │                                │
│                 │  :9380   │                                │
│                 └──────────┘                                │
└──────────────────────────────────────────────────────────────┘
```

## 服务清单

| 服务 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| nginx | nginx:alpine | 80, 443 | 反向代理 + 静态资源 |
| backend | 自定义 Dockerfile | 8000 | FastAPI 应用 |
| frontend | 自定义 Dockerfile | 3000（开发） | Vue 3 应用 |
| postgres | postgres:15 | 5432 | 主数据库 |
| redis | redis:7-alpine | 6379 | 缓存/锁/限流 |
| rabbitmq | rabbitmq:3-management | 5672, 15672 | 消息队列 |
| minio | minio/minio | 9000, 9001 | 对象存储 |
| ragflow | ragflow | 9380 | AI 知识引擎 |

## Docker Compose 配置

### 网络架构

```
外部网络 (opsnexus-external)
  └── nginx (唯一对外暴露)

内部网络 (opsnexus-internal)
  ├── nginx
  ├── backend
  ├── postgres
  ├── redis
  ├── rabbitmq
  ├── minio
  └── ragflow
```

### 数据持久化

| 卷名 | 挂载点 | 说明 |
|------|--------|------|
| postgres_data | /var/lib/postgresql/data | 数据库数据 |
| redis_data | /data | Redis 持久化 |
| rabbitmq_data | /var/lib/rabbitmq | RabbitMQ 数据 |
| minio_data | /data | MinIO 对象存储 |
| backend_uploads | /app/uploads | 后端上传文件 |

## Nginx 配置

### 路由规则

| 路径 | 代理目标 | 说明 |
|------|----------|------|
| `/` | 前端静态资源 | Vue SPA |
| `/api/` | backend:8000 | API 请求 |
| `/ws/` | backend:8000 | WebSocket 连接 |

### 关键配置

```nginx
server {
    listen 80;

    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 后端 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 前端 Dockerfile

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY ../nginx/dev.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

## 环境变量配置

### 后端 (.env)

| 变量 | 默认值 | 说明 |
|------|--------|------|
| ENVIRONMENT | development | 运行环境 |
| DATABASE_URL | postgresql+asyncpg://opsnexus:opsnexus@postgres:5432/opsnexus | 数据库连接 |
| REDIS_URL | redis://redis:6379/0 | Redis 连接 |
| RABBITMQ_URL | amqp://opsnexus:opsnexus@rabbitmq:5672/ | RabbitMQ 连接 |
| MINIO_URL | minio:9000 | MinIO 地址 |
| MINIO_ACCESS_KEY | minioadmin | MinIO Access Key |
| MINIO_SECRET_KEY | minioadmin | MinIO Secret Key |
| MINIO_BUCKET | opsnexus | MinIO 桶名 |
| JWT_SECRET_KEY | change-me-in-production | JWT 签名密钥 |
| JWT_ACCESS_TOKEN_EXPIRE_MINUTES | 15 | Access Token 过期时间 |
| JWT_REFRESH_TOKEN_EXPIRE_DAYS | 7 | Refresh Token 过期时间 |
| ENCRYPTION_KEY | | Fernet 加密密钥 |
| BMC_CONNECT_TIMEOUT | 10 | BMC 连接超时（秒） |
| BMC_READ_TIMEOUT | 30 | BMC 读取超时（秒） |
| METRIC_COLLECT_INTERVAL | 60 | 指标采集间隔（秒） |
| RAGFLOW_API_URL | http://ragflow:9380 | RAGFlow API 地址 |
| RAGFLOW_API_KEY | | RAGFlow API Key |
| NETBOX_API_URL | | NetBox API 地址 |
| NETBOX_API_TOKEN | | NetBox API Token |
| NETBOX_SYNC_ENABLED | false | 是否启用 NetBox 同步 |
| RATE_LIMIT_ENABLED | true | 是否启用限流 |
| RATE_LIMIT_REQUESTS_PER_MINUTE | 60 | 每分钟请求限制 |
| RATE_LIMIT_BURST | 10 | 突发请求限制 |

### 前端

| 变量 | 默认值 | 说明 |
|------|--------|------|
| VITE_API_BASE_URL | /api | API 基础路径 |

## 数据库初始化

### 自动初始化

后端启动时通过 `init_db()` 自动创建表结构。

### 数据库迁移

```bash
cd backend
alembic upgrade head
```

### 种子数据

```bash
cd backend
python seed_demo.py
```

种子数据包含：
- 超级管理员账户（admin / admin123）
- 内置角色和权限
- 示例数据中心、机柜、服务器
- 示例告警规则
- SEL 事件码参考数据
- 固件兼容性数据

## 生产部署建议

### 安全加固

1. **修改默认密码**：数据库、Redis、RabbitMQ、MinIO、JWT 密钥
2. **启用 HTTPS**：配置 SSL 证书，Nginx 监听 443
3. **网络隔离**：仅 Nginx 对外暴露，后端服务在内网
4. **加密密钥**：生成 Fernet 加密密钥用于 BMC 凭据加密
5. **CORS 配置**：限制允许的源域名

### 性能优化

1. **PostgreSQL**：调整 shared_buffers、work_mem、连接池大小
2. **Redis**：启用持久化（AOF + RDB），调整 maxmemory-policy
3. **TimescaleDB**：配置压缩策略，自动清理过期数据
4. **Nginx**：启用 gzip、静态资源缓存、连接池

### 高可用

1. **数据库**：PostgreSQL 主从复制 + 自动故障转移
2. **Redis**：Sentinel 哨兵模式或 Cluster 集群
3. **RabbitMQ**：镜像队列 + 集群
4. **后端**：多实例 + 负载均衡
5. **MinIO**：分布式模式（4 节点起）

### 监控

1. **应用监控**：`/api/v1/health` 健康检查端点
2. **基础设施监控**：Prometheus + Grafana
3. **日志收集**：structlog JSON 输出 + ELK/Loki
