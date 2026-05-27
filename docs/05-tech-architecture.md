# 05 · 技术架构规格

## 设计目标

| 指标 | 目标值 |
|---|---|
| 安装包大小 | < 100MB（不含模型）|
| 首次启动后总占用 | < 4GB（含模型）|
| 闲时内存 | < 200MB（不含本地推理）|
| 任务执行时内存峰值 | < 1GB（含本地推理）|
| 冷启动时间 | < 2 秒 |
| 简单任务端到端延迟 | < 5 秒 |
| 双端一致性 | Windows + Mac，UI 行为一致 |

## 整体架构（分层视图）

```
┌─────────────────────────────────────────────────────────────────┐
│                    🖼  UI 层 (Tauri WebView)                     │
│  React + TypeScript + Tailwind + shadcn/ui                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │首页场景墙│ │任务对话页│ │知识库面板│ │设置/账户 │            │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘            │
│       └────────────┴────┬───────┴────────────┘                  │
│                         │ Tauri IPC (invoke/event)              │
└─────────────────────────┼───────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│         🦀 应用核心层 (Rust / Tauri Core)                        │
│  • 文件系统沙箱  • 系统托盘/通知  • 权限管理  • Keychain         │
│  • 任务工作目录  • 自动更新       • 进程管理  • IPC 桥           │
│                                                                 │
│                       Sidecar 子进程管理                         │
└────────────────────────────┬────────────────────────────────────┘
                             ▼ 本地 HTTP / IPC
┌─────────────────────────────────────────────────────────────────┐
│       🧠 Agent 编排层 (Python sidecar / FastAPI)                 │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  Agent Loop (Plan → Act → Observe → Loop/Finalize)   │      │
│  └──────────────────────────────────────────────────────┘      │
│  ┌───────────────┐ ┌──────────────┐ ┌──────────────┐           │
│  │ 上下文管理    │ │ 工具调度     │ │ 配额守门     │           │
│  └───────────────┘ └──────────────┘ └──────────────┘           │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  💰 Cache Layer（成本优化核心）                       │      │
│  │  - System prompt 前缀稳定化                          │      │
│  │  - 历史对话摘要压缩                                  │      │
│  │  - 工具结果缓存                                      │      │
│  └──────────────────────────────────────────────────────┘      │
└───────┬─────────────────┬─────────────────┬─────────────────────┘
        ▼                 ▼                 ▼
┌───────────────┐ ┌─────────────────┐ ┌─────────────────────────┐
│ 🛠 工具层      │ │ 🎯 模型路由层    │ │ 💾 存储层               │
│              │ │                 │ │                         │
│• 文件读写     │ │┌───────────────┐│ │ • SQLite (会话/配额/设置)│
│• PDF 解析     │ ││ 意图分类器    ││ │ • LanceDB (本地向量)    │
│• DOCX/XLSX/PPT││ │(本地 0.6B)    ││ │ • 文件系统 (任务工作区) │
│• 图片 OCR     │ │└───────┬───────┘│ │ • OS Keychain (凭证)    │
│• 文档生成     │ │        ▼        │ │ • 文件快照 (撤销支持)   │
│• 向量检索     │ │┌───────────────┐│ └─────────────────────────┘
│• 命令执行     │ ││ 路由决策       ││
│• 定时任务     │ ││(规则+复杂度)   ││
└──────────────┘ │└───┬───┬───┬───┘│
                 │    ▼   ▼   ▼    │
                 │ Local Flash Pro │
                 └────────┬────────┘
                          │
       ┌──────────────────┼──────────────────────┐
       ▼                  ▼                      ▼
┌─────────────┐  ┌──────────────────┐  ┌──────────────────────┐
│🤖 本地推理   │  │ ☁ 云端 API       │  │ 🔄 多供应商兜底       │
│             │  │                  │  │                      │
│ Ollama      │  │ Primary:         │  │ 失败链:              │
│ - Qwen3-4B  │  │   火山方舟        │  │ 火山→DeepSeek→本地  │
│ - Embedding │  │                  │  │                      │
│   BGE-M3    │  │ Backup:          │  │ 健康度监控           │
│ - 意图分类  │  │   DeepSeek 官方   │  │ 自动 failover        │
│   Qwen 0.6B │  │   阿里云百炼      │  │                      │
└─────────────┘  └──────────────────┘  └──────────────────────┘
```

## 技术栈最终决策

### 桌面框架

**Tauri 2.0** — 详见 [ADR-0001](adr/0001-framework-tauri.md)

| 子组件 | 选择 |
|---|---|
| Bundler | Tauri Bundler（自动检测 WebView2 安装） |
| WebView | WebView2 (Win) / WKWebView (Mac) |
| Native API | Tauri Plugin（FS, Dialog, Notification, Clipboard, Tray） |
| 自动更新 | Tauri Updater |

### 前端

| 子组件 | 选择 | 备选 |
|---|---|---|
| 框架 | React 18 + TypeScript | — |
| 样式 | Tailwind CSS + shadcn/ui | — |
| 状态 | Zustand | Jotai |
| 动画 | Framer Motion | — |
| 图标 | Lucide React | — |
| Markdown | react-markdown + rehype-highlight + shiki | — |
| PDF 预览 | react-pdf (PDF.js) | — |
| 表格 | TanStack Table | — |
| 路由 | 不用 React Router，简单组件切换 | — |
| 表单 | react-hook-form + zod | — |

### 后端（Tauri Core - Rust）

| 模块 | 用途 |
|---|---|
| `commands/` | IPC 命令处理 |
| `fs_sandbox/` | 文件系统访问 + 权限沙箱 |
| `keychain/` | OS 密钥库集成 |
| `sidecar/` | Python 子进程生命周期管理 |
| `snapshot/` | 文件操作快照（撤销支持）|
| `updater/` | 自动更新 |
| `tray/` | 系统托盘 |

### Agent 层（Python sidecar）— 详见 [ADR-0002](adr/0002-python-sidecar.md)

| 子组件 | 选择 |
|---|---|
| Web 框架 | FastAPI |
| 通信 | HTTP localhost（启动时随机端口）|
| LLM 客户端 | OpenAI SDK（DeepSeek/火山兼容） + Ollama Python |
| Agent 框架 | 自研轻量框架（参考 Claude Code 范式）|
| 异步 | asyncio |
| 打包 | PyInstaller --onedir |

### 模型 / 推理

| 用途 | 模型 | 大小 |
|---|---|---|
| 本地主模型（推荐配置 16GB+）| Qwen3-4B Q4_K_M | ~2.5GB |
| 本地兜底（8GB 内存）| Qwen3-1.7B Q4 | ~1GB |
| 意图分类 | Qwen3-0.6B Q4 | ~400MB |
| 嵌入 | BGE-M3 small | ~200MB |
| OCR | RapidOCR (PaddleOCR) | ~100MB |
| 推理引擎 | Ollama 内嵌 | ~50MB |
| **总计** | | **~4GB** |

模型分发策略：
- **不打包进安装包**（控制安装包 < 100MB）
- 首次启动按硬件自动选择并下载
- 用 CDN 加速（火山引擎对象存储 / 七牛云）

### 云端模型 — 详见 [ADR-0005](adr/0005-volcano-engine-primary.md)

| 优先级 | 供应商 | 模型 |
|---|---|---|
| 主 | 火山方舟 | DeepSeek V4 Pro, V4 Flash |
| 备 | DeepSeek 官方 | V4 Pro, V4 Flash |
| 备 | 阿里云百炼 | DeepSeek V4 系列 |

### 存储

| 用途 | 选择 |
|---|---|
| 关系数据（会话、配额、设置）| SQLite (sqlx) |
| 向量数据（知识库）| LanceDB（嵌入式、零运维）|
| 文件系统 | 用户授权目录 + App 工作目录 |
| 凭证 | OS Keychain（Win Credential Manager / Mac Keychain）|
| 文件快照 | 工作目录下的 `.snapshots/` |

## 模块边界与职责

### Tauri Core（Rust）的职责

✅ **只做的事**：
- 系统调用（文件、剪贴板、通知、托盘）
- 权限管理与沙箱
- Sidecar 进程管理
- 自动更新
- 凭证存储

❌ **不做的事**：
- 任何 AI 相关逻辑
- 业务规则
- 文档解析（除了简单文件元信息）

### Python sidecar 的职责

✅ **只做的事**：
- LLM 调用
- Agent loop
- 文档解析与生成
- 向量索引与搜索
- 工具调用编排
- 缓存优化

❌ **不做的事**：
- 直接操作系统级资源（通过 Tauri 提供的 API）
- UI 渲染
- 长期持久化（数据存到 SQLite，让 Tauri 管）

### UI（React）的职责

✅ **只做的事**：
- 渲染与交互
- 通过 IPC 调用 Tauri Core
- 不直接调 Python sidecar（除了流式响应通过 SSE/WebSocket）

❌ **不做的事**：
- 任何业务逻辑
- 直接调用文件系统 API
- 直接调云端 API

## 跨进程通信协议

### UI ↔ Tauri Core (IPC)

用 Tauri 标准 invoke / event 机制：

```typescript
// UI 调用 Core
const result = await invoke('create_task', { 
  files: [...],
  prompt: '...'
});

// UI 监听 Core 推送
import { listen } from '@tauri-apps/api/event';
await listen('task:step_completed', (event) => {
  // 更新执行流
});
```

### Tauri Core ↔ Python sidecar (HTTP)

```
POST   /tasks                创建任务
GET    /tasks/{id}/stream    SSE 实时流（执行步骤）
POST   /tasks/{id}/abort     中断任务
POST   /tools/parse-pdf      工具调用
POST   /chat                 简单聊天
GET    /health               健康检查
```

### 流式协议

Python sidecar 用 SSE 推送 Agent 执行步骤：

```
event: step
data: {"type": "tool_call", "name": "read_file", "args": {...}}

event: step
data: {"type": "tool_result", "data": "..."}

event: step  
data: {"type": "thinking", "content": "..."}

event: final
data: {"answer": "...", "artifacts": [...]}
```

## 安全模型

### 文件系统访问

- **白名单目录**：用户启动时主动选择允许访问的目录
- **默认目录**：桌面、下载、文档（用户可关闭任何一个）
- **临时访问**：拖入的文件自动获得访问权（仅限本次会话）
- **沙箱**：所有文件操作通过 Tauri Core 走，Python sidecar 不能直接访问

### 凭证管理

- API Key（L3 模式）**必须**存 OS Keychain
- 永远不能写入配置文件
- 内存中只在用 API 时短暂解密
- 用户卸载时一并清除

### 网络访问

- 默认全部走 HTTPS
- 证书校验严格
- L1 用户 token 通过我们的 CDN 转发到 DeepSeek/火山（**节流和成本控制**）
- L3 用户直连各家 API（不经过我们的服务）

### 隐私承诺

- **不收集**：用户文件内容、对话内容、行为日志
- **匿名上报**（用户可关）：崩溃日志、性能指标、功能使用次数（**不含内容**）
- 上报数据有完整字段清单可查（设置页 → 隐私 → 上报内容）

## 性能预算

| 操作 | 预算 |
|---|---|
| UI 帧率 | 60 fps |
| IPC round-trip | < 50ms |
| HTTP 到 sidecar | < 20ms |
| 简单云端调用 | < 3s（含缓存命中）|
| 简单本地调用 | < 2s（Qwen3-4B Q4 在 CPU）|
| 复杂任务（多工具）| < 30s |
| PDF 解析（10 页文本）| < 5s |
| PDF OCR（10 页扫描）| < 60s |
| 向量索引建立（100 文件）| < 5 分钟 |

## 跨平台差异处理

| 维度 | Windows | Mac |
|---|---|---|
| WebView | WebView2 (Chromium) | WKWebView (WebKit) |
| 文件路径 | 反斜杠（Rust 自动处理）| 正斜杠 |
| 权限模型 | UAC | TCC（弹窗多）|
| 签名 | 标准代码签名证书 | Apple Developer + Notarization |
| 安装器 | MSI / NSIS | DMG |
| 托盘 | 系统托盘 | Menu Bar |
| 快捷键 | Ctrl | Cmd |
| Ollama 加速 | DirectML / CUDA | Metal |
| 字体渲染 | Cleartype（细）| 系统级（粗）|

**MVP 阶段只做 Windows**，详见 [ADR-0003](adr/0003-windows-first.md)。

## 项目目录结构

```
LongAgent/
├── src-tauri/                  # Rust / Tauri 核心
│   ├── src/
│   │   ├── main.rs
│   │   ├── commands/           # IPC 命令
│   │   ├── fs_sandbox/         # 文件系统沙箱
│   │   ├── keychain/           # 凭证管理
│   │   ├── sidecar/            # Python 子进程
│   │   ├── snapshot/           # 操作快照
│   │   └── lib.rs
│   ├── Cargo.toml
│   └── tauri.conf.json
│
├── src/                        # React UI
│   ├── pages/
│   ├── components/
│   │   ├── ExecutionStream.tsx # 关键：执行流可视化
│   │   ├── FileDrop.tsx
│   │   ├── ArtifactCard.tsx
│   │   └── ...
│   ├── stores/                 # Zustand
│   ├── lib/
│   │   ├── tauri.ts            # Tauri API 封装
│   │   └── ipc.ts              # IPC 协议类型
│   └── App.tsx
│
├── sidecar/                    # Python Agent
│   ├── main.py                 # FastAPI 入口
│   ├── agent/
│   │   ├── loop.py
│   │   ├── classifier.py
│   │   ├── router.py
│   │   ├── cache.py
│   │   └── quota.py
│   ├── tools/
│   │   ├── file_ops.py
│   │   ├── doc_parsers.py
│   │   ├── doc_generators.py
│   │   ├── vector_search.py
│   │   └── ocr.py
│   ├── llm/
│   │   ├── local.py            # Ollama
│   │   ├── cloud.py            # OpenAI-compatible
│   │   └── providers.py        # 多供应商兜底
│   ├── storage/
│   │   ├── db.py               # SQLite
│   │   └── vector.py           # LanceDB
│   └── pyproject.toml
│
├── resources/
│   ├── models/                 # 首启动后下载到这里
│   └── prompts/                # System prompts
│
├── docs/                       # 本目录 (SDD specs)
│
├── scripts/
│   ├── build.sh
│   ├── bundle-ollama.sh
│   └── bundle-sidecar.sh
│
├── .github/workflows/          # CI
│   ├── build-windows.yml
│   └── build-mac.yml (v1.5)
│
└── package.json
```

## 技术债清单（已知妥协）

| 项目 | 描述 | 偿还计划 |
|---|---|---|
| 自研 Agent 框架 | 用 LangGraph 太重，自研可控 | 长期维护，可拆库 |
| PyInstaller 打包 | 包大 + 启动慢 | v1.x 评估 Nuitka 替换 |
| 没有完整的 e2e 测试 | MVP 阶段靠手测 + 截图回归 | v1.1 引入 Playwright + Tauri 集成测试 |
| 单一后端语言（Python）| 想用 Rust 但生态弱 | 长期保留 sidecar 架构 |
| 模型路由用规则引擎 | 没用学习方法 | 用户量上来后考虑训练路由器 |
