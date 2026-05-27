# LongAgent

> **一句话定位**：给小白的 AI 桌面助手——不只能聊天，还能动你的文件。

LongAgent 是面向 **"用过对话 AI 但没体验过本地 Agent 优势"** 的小白用户的桌面 Agent 产品。它在用户的本地电脑上跑，能读写文件、生成文档、批量处理资料，并将 Agent 执行过程**可视化**地呈现给用户。

## 产品定位三要素

- **Task-first 而非 Chat-first**：拖文件 + 选场景，不是对着对话框打字
- **本地优先 + 云端协同**：默认本地模型，复杂任务路由到云端国产模型
- **透明可控**：每一步都看得见，可中断、可撤销、可重做

## 当前状态

📋 **规划阶段 (SDD 文档体系)** — 等待 MVP 开发启动

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
| [ADR](docs/adr/) | 架构决策记录（不可变历史） |

## 核心决策速览

| 决策 | 选择 | ADR |
|---|---|---|
| 桌面框架 | Tauri 2.0 | [ADR-0001](docs/adr/0001-framework-tauri.md) |
| 后端架构 | Rust + Python sidecar | [ADR-0002](docs/adr/0002-python-sidecar.md) |
| 平台优先级 | Windows 优先，Mac 在 v1.5 | [ADR-0003](docs/adr/0003-windows-first.md) |
| 商业模式 | 三层用户（L1 免费/L2 订阅/L3 BYOK） | [ADR-0004](docs/adr/0004-three-tier-model.md) |
| 云端模型 | 火山方舟（主）+ DeepSeek 官方（备） | [ADR-0005](docs/adr/0005-volcano-engine-primary.md) |
| Browser/Computer Use | MVP 不做，v1.5 白名单场景再加 | [ADR-0006](docs/adr/0006-defer-browser-use.md) |

## 开发方法

本项目采用 **SDD (Spec-Driven Development)**：
- 所有产品/技术决策先落到文档，再写代码
- 重大决策走 ADR 流程，不可变历史
- 代码 PR 必须引用对应规格章节
