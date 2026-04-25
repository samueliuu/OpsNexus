# 安全设计

## 安全架构总览

```
┌─────────────────────────────────────────────────────────┐
│                      安全边界                             │
│                                                         │
│  ┌───────────┐    ┌───────────┐    ┌───────────────┐   │
│  │   HTTPS   │───▶│   Nginx   │───▶│  Rate Limit   │   │
│  │  TLS 1.3  │    │  反向代理  │    │  60次/分钟    │   │
│  └───────────┘    └───────────┘    └───────┬───────┘   │
│                                            │            │
│                                   ┌────────▼────────┐   │
│                                   │  JWT 认证       │   │
│                                   │  Bearer Token   │   │
│                                   └────────┬────────┘   │
│                                            │            │
│                                   ┌────────▼────────┐   │
│                                   │  RBAC 授权      │   │
│                                   │  资源+操作权限   │   │
│                                   └────────┬────────┘   │
│                                            │            │
│                                   ┌────────▼────────┐   │
│                                   │  业务逻辑       │   │
│                                   │  数据隔离/审计   │   │
│                                   └─────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## 认证机制

### JWT Token 体系

| Token 类型 | 有效期 | 用途 |
|-----------|--------|------|
| Access Token | 15 分钟 | API 请求认证 |
| Refresh Token | 7 天 | 刷新 Access Token |
| WebSocket Ticket | 30 秒 | WebSocket 连接认证（一次性） |
| KVM Proxy Token | 5-480 分钟 | KVM 远程控制台代理认证 |

### Token 生成

- 算法：HS256
- Payload 包含：`sub`（用户 ID）、`exp`（过期时间）、`type`（token 类型）、`iat`（签发时间）、`username`、`is_superuser`
- 密钥：`JWT_SECRET_KEY`（生产环境强制修改，最少 32 字符）

### Token 刷新流程

```
1. 客户端请求 API，携带 access_token
2. 后端验证 access_token
   ├── 有效 → 正常处理请求
   └── 过期 → 返回 401
3. 客户端收到 401，使用 refresh_token 调用 /auth/refresh
4. 后端验证 refresh_token
   ├── 有效 → 返回新的 access_token + refresh_token（Token 轮换）
   └── 无效/过期 → 返回 401，客户端跳转登录页
5. 刷新期间其他请求排队等待（refreshSubscribers 队列机制）
```

### 前端认证流程

1. **登录**：`authStore.login()` → 存储 access_token / refresh_token / user 到 localStorage
2. **请求拦截**：自动添加 `Authorization: Bearer <token>` 头
3. **401 处理**：自动使用 refresh_token 刷新，刷新期间其他请求排队
4. **路由守卫**：未登录用户访问受保护页面时重定向到 `/login`
5. **Token 过期检测**：解析 JWT payload 的 `exp` 字段，与当前时间比较

## 授权机制

### RBAC 权限模型

```
User ──M:N──▶ Role ──M:N──▶ Permission
                                    │
                                    ├── resource（资源类型）
                                    └── action（操作类型）
```

### 权限编码规则

```
{module}:{resource}:{action}

示例：
  system:user:read       - 读取用户
  system:user:write      - 创建/更新/删除用户
  asset:server:read      - 读取服务器
  asset:server:write     - 创建/更新/删除服务器
  monitor:alert:execute  - 确认/抑制告警
  outband:power:execute  - 电源操作
  outband:kvm:execute    - KVM 远程控制
```

### 权限检查流程

1. `get_current_user()` 从 Bearer Token 解析当前用户
2. `get_current_active_user()` 确保用户处于激活状态
3. `PermissionChecker(resource, action)` 检查用户权限：
   - 超级管理员（`is_superuser=True`）：直接通过所有权限检查
   - 通配符权限（`system:*:read`）：匹配所有操作
   - 普通用户：遍历角色的 permissions 列表

### 预定义权限检查器

| 检查器 | 权限 |
|--------|------|
| `require_user_read` | system:user:read |
| `require_user_write` | system:user:write |
| `require_role_read` | system:role:read |
| `require_role_write` | system:role:write |
| `require_config_read` | system:config:read |
| `require_config_write` | system:config:write |

### 前端权限控制

- **菜单可见性**：系统管理菜单仅对 `super_admin` 或有 `system:read` 权限的用户可见
- **`hasPermission(resource, action)`**：组件级权限检查
- **路由守卫**：未登录用户重定向到登录页

## 数据安全

### 密码安全

| 项 | 实现 |
|----|------|
| 密码哈希 | bcrypt（passlib 封装） |
| 密码策略 | 最少 8 位（前端校验） |
| 密码修改 | 仅本人或超级管理员可操作 |

### BMC 凭据加密

| 项 | 实现 |
|----|------|
| 加密算法 | Fernet 对称加密 |
| 密钥派生 | PBKDF2-HMAC-SHA256，从 JWT_SECRET_KEY 派生 32 字节密钥 |
| 存储 | encrypted_password 字段，原文不落库 |
| 传输 | 仅在创建/更新时传输，查询时不返回明文 |

### 敏感配置

- `is_sensitive=True` 的系统配置，前端显示为 `******`
- 编辑敏感配置时留空表示不修改

## 网络安全

### CORS 配置

```python
CORSMiddleware(
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Correlation-ID"],
)
```

### 请求限流

| 配置 | 值 | 说明 |
|------|-----|------|
| 算法 | 固定窗口 | Redis INCR + EXPIRE |
| 每分钟请求 | 60 | 正常请求限制 |
| 突发请求 | 10 | 允许短时突发 |
| 限流键 | 客户端 IP | 按 IP 独立计数 |
| 超限响应 | 429 RATE_LIMIT_EXCEEDED | |

### BMC 网络安全

| 配置 | 说明 |
|------|------|
| `bmc_allowed_networks` | 限制可访问的 BMC 网络段 |
| `bmc_connect_timeout` | BMC 连接超时（默认 10 秒） |
| `bmc_read_timeout` | BMC 读取超时（默认 30 秒） |
| `verify_ssl=False` | 支持自签名证书（BMC 环境常见） |

## 操作安全

### 审计日志

审计中间件自动拦截所有写操作：

```python
AUDIT_ACTION_MAP = {
    "POST": "create",
    "PUT": "update",
    "PATCH": "update",
    "DELETE": "delete",
}

RESOURCE_TYPE_MAP = {
    "/api/v1/system/users": "user",
    "/api/v1/asset/servers": "server",
    "/api/v1/monitor/rules": "alert_rule",
    ...
}
```

记录内容：
- 操作用户（从 JWT 解析）
- 操作类型（create/update/delete）
- 资源类型和 ID
- 请求 IP 和 User-Agent
- 请求 ID（链路追踪）
- 操作结果（success/failure）

### 电源操作保护

- **分布式锁**：`DistributedLock` 基于 Redis `SET NX EX`，防止并发电源操作
- **确认弹窗**：前端所有电源操作需二次确认
- **批量操作**：逐台执行，单台失败不影响其他

### KVM 会话安全

- **Proxy Token**：一次性 Token，Redis 缓存，过期自动失效
- **会话管理**：启动新会话前终止已有会话
- **超时控制**：5-480 分钟可配置
- **审计记录**：记录操作用户、客户端 IP、起止时间

## 安全最佳实践

### 生产环境检查清单

- [ ] 修改 `JWT_SECRET_KEY` 为强随机字符串（≥32 字符）
- [ ] 生成 `ENCRYPTION_KEY` 用于 BMC 凭据加密
- [ ] 修改数据库、Redis、RabbitMQ、MinIO 默认密码
- [ ] 启用 HTTPS，配置 SSL 证书
- [ ] 限制 CORS 允许的源域名
- [ ] 配置 `bmc_allowed_networks` 限制 BMC 访问范围
- [ ] 启用请求限流（`RATE_LIMIT_ENABLED=True`）
- [ ] 配置日志级别为 INFO 或 WARNING
- [ ] 定期清理过期审计日志
- [ ] 定期轮换 JWT 密钥
