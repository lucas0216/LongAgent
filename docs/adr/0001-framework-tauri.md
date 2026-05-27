# ADR-0001 · 选用 Tauri 2.0 作为桌面框架

**状态**：✅ Accepted
**日期**：2026-05-27
**决策者**：产品负责人

## 背景

我们需要选择一个跨平台（Windows + Mac）桌面应用框架。候选项：

1. **Tauri 2.0**（Rust + 系统 WebView）
2. **Electron**（打包 Chromium + Node.js）
3. **Wails**（Go + 系统 WebView）
4. **Flutter Desktop**
5. **原生开发**（WinUI + SwiftUI）

目标用户是"用过对话 AI 但没体验过本地 Agent 优势的小白"，他们的电脑往往是 8-16GB 内存的办公本，对应用的**启动速度、安装包大小、内存占用**很敏感。

## 决策

**采用 Tauri 2.0。**

## 理由

### 与产品定位强匹配

| 产品诉求 | Tauri 表现 | Electron 表现 |
|---|---|---|
| 安装包小（< 100MB）| ✅ 15-30MB | ❌ 100-150MB |
| 内存占用低（老电脑能跑）| ✅ 80-200MB | ❌ 300-500MB |
| 启动快 | ✅ < 1s | ⚠️ 2-3s |
| 性能（文件操作密集）| ✅ Rust 后端 | ⚠️ Node.js |

### 已有先例（降低不确定性）

- **腾讯元宝桌面端**用 Tauri 2.0（2025/3 上线，技术决策已公开拆解）
- 我们能直接参考它解决的问题：中文 IME 输入法、国内更新源、Win/Mac 签名

### "轻"是核心差异化卖点

Marvis 要求 16GB 内存才稳，豆包桌面版 130MB+。我们用 Tauri 能讲：
> "和腾讯元宝同款框架，安装包 < 30MB，老笔记本也能跑顺。"

如果选 Electron，这个卖点就丢了。

## 权衡（接受的代价）

| 代价 | 缓解 |
|---|---|
| 双 WebView 不一致（Win Chromium / Mac WebKit）| MVP 仅 Windows；UI 避开 bleeding edge CSS；早期 CI 接入 macOS runner |
| Tauri 生态比 Electron 年轻 | 大部分需求有解；遇坑参考腾讯元宝 |
| Python sidecar 集成文档少 | M0 投入 1 周做 PoC 验证 |
| Mac 签名/公证流程复杂 | M0 注册 Apple Developer，CI 配通 |
| WebView2 在老 Windows 不预装 | Tauri Bundler 自动检测和引导安装 |

## 不选其他方案的理由

### 不选 Electron

- 安装包/内存远超目标
- 失去"轻量"差异化
- 虽然生态最成熟，但代价太大

### 不选 Wails

- Go 的 AI 生态比 Python 弱（我们要用 Python sidecar 跑 LangChain/解析库）
- 不如 Tauri 受关注，参考资料少

### 不选 Flutter Desktop

- UI 范式（widget）不适合 Web-like 富交互
- 桌面端生态弱，AI 库几乎没有

### 不选原生

- 双端两套代码，开发成本 2-3 倍
- UI 迭代速度慢
- 我们的 UI 是 Web 风格（聊天 + 卡片），不需要原生

## 后果

### 正面

- 性能、体积、内存全面占优
- 与产品定位高度一致
- 长期跟随 Rust 生态发展，安全性好

### 负面

- 双端 UI 兼容性要持续投入测试
- 团队需要至少一个会 Rust 的成员（或一个愿意学的）
- 比 Electron 更容易踩"边缘"坑

## 验证计划

**M0 第 1 周**强制完成以下 PoC：

- [ ] Tauri 项目跑通 Win + Mac
- [ ] Python sidecar 集成 + IPC 通信
- [ ] 拖文件 + 系统 API 验证
- [ ] 双端打包成功（Win MSI + Mac DMG）

如果 PoC 失败 → 升级到 ADR-0001-v2，重新评估（最差回退到 Electron）。

## 相关

- [05 技术架构](../05-tech-architecture.md)
- [ADR-0002 Python sidecar](0002-python-sidecar.md)
- [ADR-0003 Windows 优先](0003-windows-first.md)
