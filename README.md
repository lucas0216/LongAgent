# LongAgent

> **一句话定位**：给小白的 AI 桌面助手——不只能聊天，还能动你的文件。

LongAgent 是面向 **"用过对话 AI 但没体验过本地 Agent 优势"** 的小白用户的桌面 Agent 产品。它在用户的本地电脑上跑，能读写文件、生成文档、批量处理资料，并将 Agent 执行过程**可视化**地呈现给用户。

## 产品定位三要素

- **Task-first 而非 Chat-first**：拖文件 + 选场景，不是对着对话框打字
- **本地优先 + 云端协同**：默认本地模型，复杂任务路由到云端国产模型
- **透明可控**：每一步都看得见，可中断、可撤销、可重做

## 当前状态

🔨 **M0/M1 Sprint 1.1 PoC** — Tauri ↔ Python Sidecar 通信脚手架

## 快速开始

### 前置依赖

| 工具 | 版本 | 说明 |
|---|---|---|
| Node.js | 20+ | UI 构建 |
| Rust | 1.77+ | Tauri 核心（[rustup.rs](https://rustup.rs)）|
| Python | 3.10+ | Sidecar 运行时 |
| WebView2 | — | 仅 Windows，Win 11 已预装 |

### 安装

```bash
# 1. 前端依赖
npm install

# 2. Python sidecar 依赖（建议用虚拟环境）
cd sidecar
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd ..

# 3.（仅打包时需要）生成应用图标
#    准备任意正方形 PNG（建议 1024x1024），然后：
npx @tauri-apps/cli icon path/to/your-icon.png
```

### 开发模式

```bash
# 可选：让 Tauri 用 venv 里的 Python（默认 python3 / python）
export LONGAGENT_PYTHON="$(pwd)/sidecar/.venv/bin/python"
# Windows PowerShell:
# $env:LONGAGENT_PYTHON="$(Get-Location)\sidecar\.venv\Scripts\python.exe"

# 一键启动（前端 + Tauri 编译 + Sidecar）
npm run tauri:dev
```

**期望结果**：窗口打开后约 2 秒看到 **"✅ Sidecar 已连接"**，下方显示 Port / PID / Version。

### 故障排查

| 现象 | 原因 | 解决 |
|---|---|---|
| ❌ Sidecar 未连接 + "未找到 sidecar/main.py" | 工作目录不对 | 确认在项目根目录执行 `npm run tauri:dev` |
| ❌ Sidecar 未连接 + "spawn" 报错 | Python 不在 PATH | 设置 `LONGAGENT_PYTHON` 指向具体路径 |
| ❌ Sidecar 未连接 + "did not become ready" | 依赖未装 | 进 `sidecar/` 跑 `pip install -r requirements.txt` |
| Tauri 编译慢（首次）| Rust 依赖编译 | 正常，首次 5-15 分钟，之后增量秒级 |

## 项目结构

```
LongAgent/
├── src/               # React UI (TypeScript + Tailwind)
├── src-tauri/         # Tauri Core (Rust)
│   ├── src/           # commands, sidecar lifecycle
│   └── capabilities/  # Tauri 2 权限
├── sidecar/           # Python FastAPI (Agent / 模型 / 工具)
├── docs/              # SDD 规格文档
└── package.json
```

## 文档导航

| 文档 | 内容 |
|---|---|
| [00 产品愿景](docs/00-product-vision.md) | 我们要做什么、为什么、不做什么 |
| [01 目标用户](docs/01-target-users.md) | 用户画像、场景、痛点 |
| [02 竞品分析](docs/02-competitive-analysis.md) | Marvis / 豆包 / Cherry Studio / 元宝 差异化 |
| [03 MVP 范围](docs/03-mvp-scope.md) | P0/P1/P2 功能清单与验收标准 |
| [04 用户流程](docs/04-user-flows.md) | Aha Moment 设计、核心流程 |
| [05 技术架构](docs/05-tech-architecture.md) | 分层架构、组件、技术选型 |
| [06 数据模型](docs/06-data-model.md) | SQLite + LanceDB + 文件系统 |
| [07 模型路由与成本](docs/07-model-routing-cost.md) | 缓存、路由、token 成本控制 |
| [08 商业模式](docs/08-business-model.md) | 三层用户模型、单元经济 |
| [09 路线图](docs/09-roadmap.md) | 4 个月 MVP 节奏 |
| [10 风险登记](docs/10-risk-register.md) | 已知风险与缓解策略 |
| [ADR](docs/adr/) | 架构决策记录（不可变历史）|

## 核心决策速览

| 决策 | 选择 | ADR |
|---|---|---|
| 桌面框架 | Tauri 2.0 | [ADR-0001](docs/adr/0001-framework-tauri.md) |
| 后端架构 | Rust + Python sidecar | [ADR-0002](docs/adr/0002-python-sidecar.md) |
| 平台优先级 | Windows 优先，Mac 在 v1.5 | [ADR-0003](docs/adr/0003-windows-first.md) |
| 商业模式 | 三层用户（L1 免费/L2 订阅/L3 BYOK）| [ADR-0004](docs/adr/0004-three-tier-model.md) |
| 云端模型 | 火山方舟（主）+ DeepSeek 官方（备）| [ADR-0005](docs/adr/0005-volcano-engine-primary.md) |
| Browser/Computer Use | MVP 不做，v1.5 白名单场景再加 | [ADR-0006](docs/adr/0006-defer-browser-use.md) |

## 开发方法

本项目采用 **SDD (Spec-Driven Development)**：
- 所有产品/技术决策先落到文档，再写代码
- 重大决策走 ADR 流程，不可变历史
- 代码 PR 必须引用对应规格章节

## 路线图（简）

| 阶段 | 时间 | 里程碑 |
|---|---|---|
| M0 启动准备 | 第 0 周 | 资质 / API / 证书就位 |
| **M1 核心骨架** | **第 1-4 周** | **当前阶段** · Tauri + Sidecar + Ollama + 端到端 demo |
| M2 Aha 功能 | 第 5-8 周 | 拖拽、文件解析、执行流可视化、撤销 |
| M3 闭环 | 第 9-12 周 | 路由、配额、隐私、性能 |
| M4 打磨上线 | 第 13-16 周 | 内测、修反馈、签名、首发 |

详见 [docs/09-roadmap.md](docs/09-roadmap.md)。
