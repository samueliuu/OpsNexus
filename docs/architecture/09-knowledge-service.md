# 知识服务

## 概述

知识服务是 OpsNexus 的核心差异化功能，通过 AI 语义检索和结构化数据查询，为运维人员提供智能问答、SEL 事件码解读和固件兼容性查询。

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                     KnowledgeService                         │
│                    （查询路由 + 结果聚合）                     │
│                                                             │
│         ┌───────────────────┬───────────────────┐          │
│         │                   │                   │          │
│    ┌────▼─────┐      ┌─────▼─────┐      ┌─────▼─────┐    │
│    │ semantic │      │structured │      │  hybrid   │    │
│    │ 语义查询  │      │ 结构化查询 │      │  混合查询  │    │
│    └────┬─────┘      └─────┬─────┘      └─────┬─────┘    │
│         │                   │                   │          │
│    ┌────▼─────┐      ┌─────▼─────┐      ┌─────▼─────┐    │
│    │RAGQuery  │      │Structured │      │ 合并去重   │    │
│    │Service   │      │QuerySvc   │      │ 排序返回   │    │
│    └────┬─────┘      └─────┬─────┘      └───────────┘    │
│         │                   │                              │
└─────────┼───────────────────┼──────────────────────────────┘
          │                   │
    ┌─────▼─────┐      ┌─────▼─────┐
    │  RAGFlow  │      │PostgreSQL │
    │  语义引擎  │      │ 结构化表   │
    │  (外部)   │      │  (本地)   │
    └───────────┘      └───────────┘
          │
    ┌─────▼─────┐
    │   Redis   │
    │  查询缓存  │
    └───────────┘
```

## 查询模式

### 语义查询（semantic）

自然语言问答，通过 RAGFlow 语义检索引擎获取答案。

**流程**：
1. 检查 Redis 缓存（相同查询 + 品牌 + 类别的缓存结果）
2. 缓存命中 → 直接返回
3. 缓存未命中 → 调用 RAGFlow API
4. RAGFlow 可用 → 返回语义检索结果
5. RAGFlow 不可用 → 降级到本地关键词匹配

**RAGFlow 数据集映射**：

```
brand:category → dataset_id

dell:troubleshooting     → Dell 故障排除数据集
dell:maintenance         → Dell 维护手册数据集
hpe:troubleshooting      → HPE 故障排除数据集
hpe:maintenance          → HPE 维护手册数据集
...
```

**RAGFlow API 调用**：

```
POST http://{ragflow_host}:9380/api/v1/retrieval
Headers: Authorization: Bearer {api_key}
Body: {
    "question": "Dell R750 CPU温度过高怎么处理？",
    "dataset_ids": ["dataset_id_1", "dataset_id_2"],
    "top_k": 5
}
```

### 结构化查询（structured）

直接查询 PostgreSQL 中的结构化参考数据表。

| 查询类型 | 数据源 | 说明 |
|----------|--------|------|
| SEL 事件码 | sel_event_codes 表 | 按品牌、事件码、严重级别查询 |
| 固件兼容性 | firmware_compatibility 表 | 按品牌、型号、组件查询 |

### 混合查询（hybrid）

组合语义查询和结构化查询的结果：

1. 并行执行 semantic 和 structured 查询
2. 合并结果列表
3. 去重（按内容相似度）
4. 按相关性排序
5. 返回统一结果

## 对话管理

### 对话生命周期

```
创建对话 → 发送消息 → AI 回复 → 继续对话 → 编辑标题 → 删除对话
    │           │          │
    │           │          └── 持久化到 conversation_messages
    │           └── 自动创建对话（首次发送时）
    └── 手动创建空对话
```

### 消息持久化

每次查询自动保存两条消息：
1. **用户消息**：role=user, content=查询内容, brand, query_type
2. **助手消息**：role=assistant, content=回答内容, sources（参考来源）, latency_ms

### 对话上下文

- 每次查询可携带 `conversation_id`，将消息关联到对话
- 对话标题可手动编辑
- 对话列表按更新时间倒序排列

## 收藏功能

用户可收藏助手回答的消息：

| 字段 | 说明 |
|------|------|
| title | 收藏标题（从消息内容提取） |
| content | 收藏内容 |
| source_type | 来源类型（qa/sel_code/firmware） |
| brand | 品牌标签 |

前端展示：
- 卡片网格布局，自适应列数
- 品牌用不同颜色 Tag 标识
- 来源类型用 Tag 标识

## SEL 事件码查询

### 数据来源

`sel_event_codes` 表存储各品牌的 SEL 事件码参考数据：

| 字段 | 说明 |
|------|------|
| brand | 品牌（dell/hpe/lenovo/...） |
| event_code | 事件码 |
| sensor_type | 传感器类型 |
| severity | 严重级别（Critical/Warning/Info） |
| description | 事件描述 |
| recommended_action | 建议处理方式 |

### 查询接口

```
GET /api/v1/knowledge/sel-codes?brand=dell&event_code=0x8001&severity=Critical
```

### 前端交互

1. 选择品牌（必选）
2. 输入事件码（可选）
3. 选择严重级别（可选）
4. 结果表格展示：事件码、传感器类型、严重级别、描述、建议处理

## 固件兼容矩阵

### 数据来源

`firmware_compatibility` 表存储各品牌服务器的固件版本兼容性数据：

| 字段 | 说明 |
|------|------|
| brand | 品牌 |
| model | 服务器型号 |
| component | 组件（BIOS/BMC/RAID/NIC/PSU） |
| version | 固件版本 |
| release_date | 发布日期 |
| criticality | 重要性（optional/recommended/critical） |
| release_notes | 发布说明 |
| download_url | 下载链接 |

### 查询接口

```
GET /api/v1/knowledge/firmware-matrix?brand=dell&model=R750&component=BMC
```

### 前端交互

1. 选择品牌（必选）
2. 选择/输入型号（可选）
3. 选择组件类型（可选）
4. 结果表格展示：型号、组件、版本、重要性（颜色 Tag）、发布日期、发布说明、下载链接

## 缓存策略

| 缓存键 | TTL | 说明 |
|--------|-----|------|
| `knowledge:query:{hash}` | 1 小时 | 语义查询结果缓存 |
| 键组成 | - | query + brand + category + query_type 的哈希 |

缓存逻辑：
1. 查询前检查 Redis 缓存
2. 缓存命中 → 直接返回（跳过 RAGFlow 调用）
3. 缓存未命中 → 调用 RAGFlow，结果写入缓存
4. 结构化查询不缓存（直接查数据库，响应快）

## 降级策略

```
RAGFlow 可用
  └── 语义查询 → RAGFlow API → 返回结果

RAGFlow 不可用
  └── 语义查询 → 本地关键词匹配
                    ├── sel_event_codes 表关键词搜索
                    └── firmware_compatibility 表关键词搜索
```

降级匹配逻辑：
1. 将查询文本分词
2. 在 sel_event_codes 的 description 和 recommended_action 字段中搜索
3. 在 firmware_compatibility 的 release_notes 字段中搜索
4. 合并结果返回

## 配置项

| 配置 | 环境变量 | 默认值 | 说明 |
|------|----------|--------|------|
| RAGFlow API 地址 | RAGFLOW_API_URL | http://localhost:9380 | RAGFlow 服务地址 |
| RAGFlow API Key | RAGFLOW_API_KEY | | API 认证密钥 |
| RAGFlow 超时 | RAGFLOW_TIMEOUT | 30 | 请求超时（秒） |
| 知识服务开关 | KNOWLEDGE_SERVICE_ENABLED | true | 是否启用知识服务 |
