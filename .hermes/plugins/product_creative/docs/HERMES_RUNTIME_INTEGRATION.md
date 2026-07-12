# Hermes Runtime Integration

本文件固定当前项目和本机 Hermes 运行时之间的关系，避免后续再次把“脚本能跑通”误判为“已经完成 Hermes 对话入口集成”。

## 1. 当前事实

当前机器上存在两个 Hermes 位置：

- 开发源码目录：`C:\data\work file\hermers-agent for me\hermes-agent`
- 本机安装目录：`C:\Users\1\AppData\Local\hermes\hermes-agent`

当前 Hermes 数据与配置目录：

- `HERMES_HOME=C:\Users\1\AppData\Local\hermes`
- 配置文件：`C:\Users\1\AppData\Local\hermes\config.yaml`

关键结论：

- 通过安装脚本安装的 Hermes 和 git 拉取的 Hermes 源码不是同一个目录。
- 二者可以读取同一个 `HERMES_HOME`，所以会共用同一份 `config.yaml`、模型配置、会话状态和插件启用配置。
- 当在开发源码目录中运行本机安装目录的 venv Python，并使用 `python -m hermes_cli.main` 时，Python 会优先从当前开发源码目录导入 `hermes_cli`。
- 直接运行 PATH 上的 `hermes.exe` 时，通常会走本机安装目录的入口；这不等同于正在验证开发源码目录。

## 2. 为什么之前能读取 DeepSeek 配置

DeepSeek 配置位于：

`C:\Users\1\AppData\Local\hermes\config.yaml`

Hermes 的默认行为是从当前 `HERMES_HOME` 读取配置。只要开发源码运行时仍使用同一个 `HERMES_HOME`，它就会读取本机已经配置好的 DeepSeek 模型。

这不是“两个源码目录自动互通”，而是“两个运行入口共用同一个 Hermes Home”。

## 3. 当前阶段的主验收入口

当前阶段不再把 `product_creative.ps1` 作为产品主入口。

主验收入口必须是：

1. 用户通过 Hermes chat / Agent 对话提出自然语言需求。
2. Hermes 能看到 `product_creative` 工具集。
3. Hermes 能主动或在协议引导下调用 `product_workflow_run`。
4. `product_workflow_run` 基于 Product Brain、素材库、状态机和 guard boundary 执行业务链路。
5. 遇到 Product Brain 写入、真实外部模型调用、确认型操作时必须停下来等待用户确认。

脚本仍然保留，但定位降级为：

- 运行时诊断
- 隔离回归测试
- 开发期兜底验证
- 失败定位

脚本能跑通，不代表产品体验已经跑通。

## 4. 开发态 Hermes CLI 对话验证方式

在开发源码目录中验证时，使用本机安装目录的 venv Python，但让当前工作目录指向开发源码：

```powershell
cd "C:\data\work file\hermers-agent for me\hermes-agent"
$env:HERMES_ENABLE_PROJECT_PLUGINS = "1"
& "C:\Users\1\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" -m hermes_cli.main chat `
  --toolsets product_creative,skills `
  --skills product_creative:product-creative-operator `
  --query "请使用 product_workflow_run，基于 demo-product 生成 3 个小红书种草文案草案。"
```

注意：

- `HERMES_ENABLE_PROJECT_PLUGINS=1` 只允许扫描当前项目的 `.hermes/plugins`。
- `plugins.enabled` 仍需要包含 `product_creative`，否则插件只会被发现但不会加载。
- 临时验证可以使用诊断脚本的 `-UseTemporaryEnable`，它会备份并恢复 `config.yaml`。

推荐使用封装后的开发态启动脚本：

```powershell
.\.hermes\plugins\product_creative\scripts\start_hermes_product_creative_dev.ps1
```

单次查询：

```powershell
.\.hermes\plugins\product_creative\scripts\start_hermes_product_creative_dev.ps1 -Query "请先用 product_workspace_resolve 定位 demo-product，然后用 product_workflow_run 查看下一步。" -MaxTurns 4
```

该脚本默认：

```text
临时启用 product_creative 插件。
设置 HERMES_ENABLE_PROJECT_PLUGINS=1。
启动项目内 Hermes chat。
退出后恢复 config.yaml 和环境变量。
```

如果用户只说产品名称而没有提供 `product_id`，Hermes 应先调用 `product_workspace_resolve`，再调用 `product_workflow_run`。

## 5. 诊断入口

运行只读诊断：

```powershell
.\.hermes\plugins\product_creative\scripts\diagnose_hermes_runtime.ps1
```

检查项目插件发现/加载状态：

```powershell
.\.hermes\plugins\product_creative\scripts\diagnose_hermes_runtime.ps1 -CheckPluginLoad
```

临时启用 `product_creative` 后检查，结束后会恢复配置：

```powershell
.\.hermes\plugins\product_creative\scripts\diagnose_hermes_runtime.ps1 -UseTemporaryEnable
```

不要并行运行多个会临时启用配置的验证进程。诊断脚本会加锁保护自身，但 Hermes Desktop 或其他手动改配置的进程不受这个锁约束。

## 6. Hermes Desktop 的关系

`Hermes.exe` 是桌面壳。它通常启动本机安装目录下的 Hermes backend。

在当前阶段：

- Hermes Desktop 可以作为后续 UI / 对话入口审阅工具。
- 但 M4 之后的核心验收应先在项目内 Hermes chat / Agent 对话入口跑通。
- Desktop 集成不是绕过对话能力验证的理由。

后续如果要让 Desktop 使用开发源码，需要单独验证 Desktop backend 的源码根、环境变量和插件启用方式，例如 `HERMES_DESKTOP_HERMES_ROOT`。

Desktop 审阅说明：

```text
.hermes/plugins/product_creative/docs/HERMES_DESKTOP_PRODUCT_CREATIVE_REVIEW.md
```

## 7. 后续封装给别人使用的方向

最终产品封装时，应把用户需要配置的内容分成三类：

- Hermes 运行配置：模型 provider、base_url、model、API key。
- Product Creative 插件配置：是否启用插件、工作区位置、默认 provider。
- 外部生成模型配置：图片生成、视频生成、多模态理解、联网搜索、素材抓取。

产品不应要求用户直接运行内部脚本来完成主流程。用户主入口应是自然语言对话，脚本只作为管理员/开发者诊断工具。
