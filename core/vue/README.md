# Starfish Vue 前端

替换原 `core/static/` 下的纯 H5 实现，使用 Vue 3 + Element Plus。

## 目录结构

```
core/vue/
├── index.html              入口
├── package.json
├── vite.config.js
├── .gitignore              （node_modules / dist 不入库）
└── src/
    ├── main.js             Vue 入口 + Element Plus 注册
    ├── api.js              所有后端 API 的封装
    ├── App.vue             主界面（聊天 / 控制面板 / 头部按钮）
    ├── styles/main.css     全局样式
    └── components/
        ├── AppDialog.vue   通用弹窗壳：92vw / max 760px / max-height 70vh
        ├── SettingsDialog.vue
        ├── McpDialog.vue
        ├── SkillDialog.vue
        ├── AgentDialog.vue
        ├── PromptDialog.vue
        └── ToolsDialog.vue 内置工具秒开 + MCP 异步轮询
```

## 首次拉取代码后

```bash
cd core/vue
npm install        # 安装依赖（node_modules，已在 .gitignore）
npm run build      # 生成产物到 core/vue/dist/（已在 .gitignore）
```

随后即可启动后端 / 桌面：

```bash
# 项目根目录
python3 -m core.server    # 仅启动 Flask
# 或
starfish                  # 启动 PyQt 桌面应用
```

## 开发模式（热更新）

```bash
# 终端 1：启动后端
python3 -m core.server

# 终端 2：启动 Vite dev server
cd core/vue
npm run dev               # http://localhost:5173
# /api/* 自动代理到 http://127.0.0.1:8765
```

## 静态资源服务

Flask 的 `static_folder` 已指向 `core/vue/dist`，根路径 `/` 直接返回构建产物的 `index.html`。
`core/static/icon.png` 是 PyQt 桌面应用的窗口图标，与前端构建无关，保留在原位。

## 修复点

1. 工具列表首次加载慢：拆分 `/api/tools/builtin`（同步）与 `/api/tools/mcp`（后台异步），内置工具秒开，MCP 加载完再合并。
2. 工具描述太长：默认截断 80 字，长描述放折叠区。
3. 弹窗超出主窗：所有弹窗用 `AppDialog`，宽度 `92vw / max 760px`，内部 `max-height: 70vh` 自滚动。