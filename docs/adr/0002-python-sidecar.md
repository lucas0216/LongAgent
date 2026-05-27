# ADR-0002 · Agent 层用 Python sidecar 而不是纯 Rust

**状态**：✅ Accepted
**日期**：2026-05-27
**决策者**：产品负责人

## 背景

Tauri Core 是 Rust。Agent / 模型 / 文档解析逻辑放在哪里？候选：

1. **Python sidecar**：另起 Python 子进程，通过本地 HTTP/IPC 通信
2. **Rust 原生**：所有逻辑用 Rust 写
3. **Node.js sidecar**：用 Node 而不是 Python
4. **WebAssembly**：把 Python 编译到 wasm 跑

## 决策

**用 Python sidecar，FastAPI + uvicorn**。

## 理由

### 生态决定性

我们要做的事大量依赖成熟 Python 库：

| 需求 | Python 库 | Rust 替代 |
|---|---|---|
| PDF 解析 | pdfplumber, unstructured | 弱、不全 |
| Word/Excel/PPT | python-docx, openpyxl, python-pptx | 几乎没有 |
| OCR | RapidOCR, PaddleOCR | 不成熟 |
| 向量数据库 | LanceDB（有 Python 绑定）| 有 Rust SDK |
| LLM 客户端 | openai, anthropic SDK | 有但社区小 |
| 嵌入模型 | sentence-transformers, FastEmbed | 几乎没有 |

**结论**：Rust 重写以上能力等于自己造 5-10 个库的轮子，半年都搞不定。

### Agent 层迭代要快

Prompt 工程、路由策略、缓存优化都需要**几小时级别**的修改和测试。Python 的 REPL、热加载、轻量发布机制远胜 Rust。

### 业界主流做法

大量 AI 应用走"原生壳 + Python AI 引擎"路线：
- Pinokio（AI 应用启动器）
- LM Studio
- 部分 Cursor 后台服务

### Rust 留在它最擅长的地方

| 职责 | 语言 |
|---|---|
| 系统调用、文件 I/O、IPC、进程管理、安全 | Rust ✅ |
| AI 业务逻辑、文档处理、模型调用 | Python ✅ |

明确分工，各取所长。

## 权衡（接受的代价）

| 代价 | 影响 | 缓解 |
|---|---|---|
| 安装包 +60-100MB | 总包 100-200MB | 接受（核心还是 Tauri 轻量优势）|
| 启动慢 +200-500ms | 首次启动稍慢 | sidecar 后台启动，UI 先渲染 |
| Mac 签名 / 公证流程更复杂 | M0 投入 1 周 | 一次性成本 |
| Windows 杀软误报 | 用户被劝退 | 标准代码签名证书必备 |
| 进程间通信复杂度 | 调试稍麻烦 | FastAPI 接口标准化 |
| 调试需要双语言切换 | 心智负担 | 明确分工边界减少跨语言改动 |

## 不选其他方案的理由

### 不选纯 Rust

理由见上："5-10 个库的轮子"。

### 不选 Node.js sidecar

- 比 Python 多花 100MB 包大小（Node runtime）
- 且少了几乎所有文档解析库
- 唯一优势是 npm 生态，但 AI 这块 npm 远不如 pypi

### 不选 WebAssembly

- Python on wasm（Pyodide）启动慢、IO 受限
- 不适合做文件操作密集的工作
- 工程复杂度爆炸

## 通信协议

**HTTP localhost**（绑随机端口）：
- 简单，OpenAI SDK / OpenAPI 工具直接用
- 流式响应用 SSE
- 安全：仅监听 127.0.0.1 + 进程间共享 token 鉴权

## 打包方案

**PyInstaller --onedir** 模式：
- 比 --onefile 启动快
- 容易调试
- Mac 上签名相对容易（一组文件 vs 单个二进制）

后续可评估迁移到 Nuitka（更快、更小，但工具链较新）。

## 后果

### 正面

- AI 能力开发速度快 3-5 倍
- 复用社区成熟方案
- 易于招聘（Python 工程师人多）

### 负面

- 总包大小被推高
- 跨进程边界要明确（避免逻辑错乱）
- 双语言团队配合

## 验证计划

**M0 第 1 周** PoC 必须验证：

- [ ] Python sidecar 启动 < 500ms
- [ ] Win/Mac 都能正常打包 + 启动
- [ ] HTTP IPC 跑通
- [ ] Mac 公证流程跑通

## 相关

- [05 技术架构](../05-tech-architecture.md)
- [ADR-0001 Tauri](0001-framework-tauri.md)
