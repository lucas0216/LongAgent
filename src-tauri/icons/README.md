# 应用图标

本目录在 PoC 阶段为空。**Tauri dev 模式不需要图标**，但 `tauri build` 打包时必须。

## 首次生成图标

准备一张正方形 PNG（建议 1024×1024 或更大），然后在项目根目录执行：

```bash
npx @tauri-apps/cli icon path/to/your-source.png
```

Tauri CLI 会自动生成本目录下需要的所有平台图标：
- `32x32.png`
- `128x128.png`
- `128x128@2x.png`
- `icon.icns`（macOS）
- `icon.ico`（Windows）

## 设计要求

- 圆角或方形均可（系统会按平台规范处理）
- 建议留 10-15% 边距，避免 macOS 圆角裁切
- 主色与品牌一致
