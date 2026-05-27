# 06 · 数据模型

## 存储概览

| 数据类型 | 存储 | 位置 |
|---|---|---|
| 应用配置、用户设置 | SQLite | `%APPDATA%/LongAgent/db.sqlite` |
| 任务与会话历史 | SQLite | 同上 |
| 配额与计费日志 | SQLite | 同上 |
| 知识库元数据 | SQLite | 同上 |
| 知识库向量 | LanceDB | `%APPDATA%/LongAgent/vectors/` |
| API Key / 凭证 | OS Keychain | 系统密钥库 |
| 文件操作快照 | 文件系统 | `%APPDATA%/LongAgent/snapshots/` |
| 生成的产物 | 用户指定目录 | 默认 `桌面/LongAgent 产物/` |
| 缓存（embedding 等）| 文件系统 | `%APPDATA%/LongAgent/cache/` |
| 日志 | 文件 | `%APPDATA%/LongAgent/logs/` |

> Mac 路径：`~/Library/Application Support/LongAgent/`

## SQLite Schema

### `users` — 本地用户档案

```sql
CREATE TABLE users (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  uuid          TEXT NOT NULL UNIQUE,            -- 本地匿名 ID
  tier          TEXT NOT NULL DEFAULT 'L1',      -- L1 | L2 | L3
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  email         TEXT,                            -- 仅 L2/L3 登录后才有
  display_name  TEXT,
  
  -- L2 订阅信息
  subscription_status   TEXT,                    -- active | expired | none
  subscription_expires_at TIMESTAMP,
  
  -- 偏好
  preferred_language    TEXT DEFAULT 'zh-CN',
  default_save_dir      TEXT,                    -- 用户改过的默认保存目录
  privacy_mode_enabled  BOOLEAN DEFAULT 0,       -- 是否开启了"本地模式"
  
  updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### `tasks` — 任务（每个 Agent 会话）

```sql
CREATE TABLE tasks (
  id            TEXT PRIMARY KEY,                -- UUID
  user_id       INTEGER NOT NULL,
  title         TEXT NOT NULL,                   -- AI 自动生成
  description   TEXT,                            -- 用户原始 prompt
  status        TEXT NOT NULL DEFAULT 'pending', -- pending | running | completed | failed | aborted | undone
  
  -- 关联
  scenario_card TEXT,                            -- 来源场景卡片 ID（如 'pdf_summary'）
  
  -- 元数据
  input_files_json    TEXT,                      -- JSON 数组：用户拖入的文件路径
  artifact_files_json TEXT,                      -- JSON 数组：产物文件路径
  
  -- 模型使用统计
  total_tokens_input  INTEGER DEFAULT 0,
  total_tokens_output INTEGER DEFAULT 0,
  total_cost_cny      REAL DEFAULT 0,
  models_used_json    TEXT,                      -- JSON 数组：调用过的模型
  
  -- 时间戳
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  started_at    TIMESTAMP,
  completed_at  TIMESTAMP,
  
  -- 撤销支持
  snapshot_id   TEXT,                            -- 关联文件快照
  undone_at     TIMESTAMP,
  
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_tasks_user_created ON tasks(user_id, created_at DESC);
CREATE INDEX idx_tasks_status ON tasks(status);
```

### `task_steps` — 执行步骤（执行流的源数据）

```sql
CREATE TABLE task_steps (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id       TEXT NOT NULL,
  
  step_index    INTEGER NOT NULL,                -- 任务内序号
  step_type     TEXT NOT NULL,                   -- thinking | tool_call | tool_result | final
  
  -- 内容
  display_text  TEXT NOT NULL,                   -- UI 显示的一句话（如 "📖 正在读取报销单.xlsx"）
  detail_json   TEXT,                            -- 详细数据（工具入参、模型中间输出等）
  
  -- 工具调用
  tool_name     TEXT,
  tool_args_json TEXT,
  tool_result_json TEXT,
  tool_error    TEXT,
  
  -- 时间
  started_at    TIMESTAMP NOT NULL,
  completed_at  TIMESTAMP,
  duration_ms   INTEGER,
  
  FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX idx_steps_task ON task_steps(task_id, step_index);
```

### `messages` — 用户与 Agent 的对话消息

```sql
CREATE TABLE messages (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id       TEXT NOT NULL,
  
  role          TEXT NOT NULL,                   -- user | assistant | system
  content       TEXT NOT NULL,
  
  -- 关联
  step_id       INTEGER,                         -- 触发的 step（assistant 消息）
  
  -- 时间
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  
  FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX idx_messages_task ON messages(task_id, created_at);
```

### `model_calls` — 模型调用日志（成本追踪）

```sql
CREATE TABLE model_calls (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id       TEXT,
  
  -- 模型信息
  provider      TEXT NOT NULL,                   -- volcano | deepseek | aliyun | ollama
  model_name    TEXT NOT NULL,                   -- deepseek-v4-pro | qwen3-4b 等
  is_local      BOOLEAN NOT NULL,
  
  -- Token 使用
  tokens_input          INTEGER NOT NULL,
  tokens_input_cached   INTEGER DEFAULT 0,       -- 缓存命中部分
  tokens_output         INTEGER NOT NULL,
  
  -- 成本
  cost_cny      REAL DEFAULT 0,
  
  -- 性能
  latency_ms    INTEGER,
  
  -- 错误
  error         TEXT,
  
  -- 路由原因（调试用）
  routing_reason TEXT,                           -- 'simple_task' | 'complex_reasoning' | 'forced_local' | etc.
  
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  
  FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
);

CREATE INDEX idx_model_calls_created ON model_calls(created_at);
CREATE INDEX idx_model_calls_task ON model_calls(task_id);
```

### `quota_daily` — 每日配额状态

```sql
CREATE TABLE quota_daily (
  date          TEXT PRIMARY KEY,                -- YYYY-MM-DD
  cloud_calls_used      INTEGER DEFAULT 0,
  cloud_calls_limit     INTEGER NOT NULL,        -- L1 默认 20
  total_cost_cny        REAL DEFAULT 0,
  
  -- 触发情况
  hit_quota_at  TIMESTAMP,                       -- 第一次撞配额上限的时间
  
  updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### `knowledge_bases` — 本地知识库（P1）

```sql
CREATE TABLE knowledge_bases (
  id            TEXT PRIMARY KEY,                -- UUID
  user_id       INTEGER NOT NULL,
  
  name          TEXT NOT NULL,
  description   TEXT,
  
  -- 源目录
  source_dirs_json    TEXT NOT NULL,             -- JSON 数组
  
  -- 状态
  file_count    INTEGER DEFAULT 0,
  chunk_count   INTEGER DEFAULT 0,
  total_size_bytes INTEGER DEFAULT 0,
  
  index_status  TEXT NOT NULL DEFAULT 'pending', -- pending | indexing | ready | failed
  last_indexed_at TIMESTAMP,
  
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  
  FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### `kb_documents` — 知识库中的文档（P1）

```sql
CREATE TABLE kb_documents (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  kb_id         TEXT NOT NULL,
  
  file_path     TEXT NOT NULL,
  file_hash     TEXT NOT NULL,                   -- SHA-256
  file_size     INTEGER,
  modified_at   TIMESTAMP,
  
  chunk_count   INTEGER DEFAULT 0,
  
  -- 状态
  parse_status  TEXT NOT NULL,                   -- ok | failed | unsupported
  parse_error   TEXT,
  
  indexed_at    TIMESTAMP,
  
  FOREIGN KEY (kb_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE,
  UNIQUE(kb_id, file_path)
);

CREATE INDEX idx_kb_docs_kb ON kb_documents(kb_id);
CREATE INDEX idx_kb_docs_hash ON kb_documents(file_hash);
```

### `file_snapshots` — 撤销支持的文件快照

```sql
CREATE TABLE file_snapshots (
  id            TEXT PRIMARY KEY,                -- 快照 ID（UUID）
  task_id       TEXT NOT NULL,
  
  -- 操作清单（用于撤销时回滚）
  operations_json TEXT NOT NULL,                 -- JSON 数组：[{op, target_path, backup_path}, ...]
  
  -- 备份目录
  backup_dir    TEXT NOT NULL,                   -- $APPDATA/LongAgent/snapshots/{id}/
  total_size_bytes INTEGER DEFAULT 0,
  
  -- 清理策略
  expires_at    TIMESTAMP NOT NULL,              -- created + 7 days
  
  -- 状态
  status        TEXT NOT NULL DEFAULT 'active',  -- active | undone | expired | manually_cleared
  
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  undone_at     TIMESTAMP,
  
  FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE INDEX idx_snapshots_expires ON file_snapshots(expires_at);
CREATE INDEX idx_snapshots_task ON file_snapshots(task_id);
```

### `app_settings` — 键值对设置

```sql
CREATE TABLE app_settings (
  key           TEXT PRIMARY KEY,
  value         TEXT NOT NULL,                   -- JSON 序列化
  updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

典型键：
- `allowed_directories` → JSON 数组
- `current_local_model` → "qwen3-4b" / "qwen3-1.7b"
- `default_save_dir` → 路径
- `model_routing_overrides` → JSON 对象
- `last_active_at` → ISO 时间戳

## LanceDB Schema（向量库）

每个知识库一张 LanceDB 表 `kb_{kb_id}`：

```python
schema = {
  "id": "string",              # chunk UUID
  "document_id": "int64",      # 关联 kb_documents.id
  "chunk_index": "int32",      # 文档内顺序
  "text": "string",            # 原文片段
  "text_token_count": "int32",
  "embedding": "fixed_size_list[float32, 1024]",  # BGE-M3 维度
  "page_number": "int32",      # PDF 等带页码的文件
  "metadata_json": "string",   # 标题、章节等
}
```

## 文件系统结构

### App 工作目录

```
%APPDATA%/LongAgent/
├── db.sqlite                    # 主数据库
├── db.sqlite-wal                # SQLite WAL
├── db.sqlite-shm                # SQLite shared mem
│
├── vectors/                     # LanceDB 存储
│   └── kb_{uuid}/               # 每个知识库一目录
│
├── snapshots/                   # 文件操作快照
│   └── {snapshot_uuid}/
│       ├── manifest.json
│       └── backup_files/        # 原文件备份
│
├── cache/                       # 缓存
│   ├── embeddings/              # 嵌入缓存
│   ├── parsed_docs/             # 文档解析缓存
│   └── model_responses/         # 高频请求响应缓存
│
├── models/                      # 本地模型（用户下载的）
│   ├── qwen3-4b.gguf
│   ├── qwen3-0.6b.gguf
│   ├── bge-m3-small/
│   └── rapidocr/
│
├── logs/                        # 日志
│   ├── app.log
│   ├── sidecar.log
│   └── crash/
│
└── tmp/                         # 临时文件（任务运行时）
    └── task_{uuid}/
```

### 用户产物目录

```
~/Desktop/LongAgent 产物/        # 默认（用户可改）
├── 2026-05-27 PDF 摘要 - 财报分析.docx
├── 2026-05-27 截图分类/
│   ├── 工作截图/
│   ├── 学习截图/
│   └── 生活截图/
└── ...
```

文件名规则：`{YYYY-MM-DD} {场景类型} - {内容关键词}.{ext}`

## 数据生命周期

| 数据 | 保留策略 |
|---|---|
| 任务历史 | 永久保留（用户可手动删）|
| task_steps | 永久（与任务绑定）|
| 文件快照 | **7 天**后自动清理 |
| 缓存（cache/） | LRU，磁盘超 1GB 时清理 |
| 模型响应缓存 | 24 小时过期 |
| 日志 | 30 天滚动 |
| 临时文件（tmp/）| 任务结束清理；启动时清理过期 |
| 用户产物 | 用户管，不自动清理 |
| 知识库 | 用户管，不自动清理 |

## 数据迁移

- DB 升级用 sqlx migration（按版本号顺序）
- 每次启动自动跑迁移
- 迁移失败有回滚机制
- 用户卸载时弹窗询问是否清除数据（默认保留）

## 备份与导出

- 设置页 → "导出我的数据"：导出整个 `%APPDATA%/LongAgent/` 为 zip
- 暂不支持云同步（隐私定位）
- v1.x 考虑加：导入备份、跨机器迁移

## 性能与限制

| 维度 | 上限 | 应对 |
|---|---|---|
| 单任务步骤数 | 50 步 | 超出自动总结历史 |
| 单文件大小（解析）| 100MB | 超出提示用户分块 |
| 知识库单库文档数 | 10,000 | 超出建议拆分知识库 |
| 单库总大小 | 5GB | 超出提示用户精简 |
| 历史任务数 | 1,000（UI 显示）| 超出归档，可查找 |
| SQLite 数据库大小 | ~500MB | 超出自动清理快照与缓存 |
