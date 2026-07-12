# Hermes Desktop Product Creative Review

本文档用于 M4.9.6：验证 Hermes Desktop 是否能作为当前阶段的临时 UI / 对话审阅入口。

## 1. 当前边界

当前产品主验收顺序是：

```text
项目内 Hermes chat 对话入口
  -> product_creative 插件加载
  -> product_workspace_resolve / product_workflow_run 工具调用
  -> Product Brain / 素材库 / workflow guard 生效
  -> Desktop 审阅
```

Desktop 不是绕过前面三步的理由。只有 Desktop 能看到并调用同一套 `product_creative` 工具时，才算 Desktop 审阅通过。

## 2. 先验证运行时

在开发源码目录运行：

```powershell
.\.hermes\plugins\product_creative\scripts\diagnose_hermes_runtime.ps1 -UseTemporaryEnable
```

需要确认：

```text
imports_dev_source = true
probe.config.product_creative_enabled = true
probe.product_plugin.enabled = true
desktop_exe_exists = true
```

## 3. 先用项目内 Hermes chat 验证

```powershell
.\.hermes\plugins\product_creative\scripts\start_hermes_product_creative_dev.ps1 -Query "请先用 product_workspace_resolve 定位 demo-product，然后用 product_workflow_run 查看下一步。" -MaxTurns 4
```

通过标准：

```text
Hermes 不是直接自由回答。
Hermes 会调用 product_workspace_resolve 或 product_workflow_run。
回复中使用 user_next_message 引导用户继续。
不要求用户运行 product_creative.ps1。
```

## 4. Desktop 审阅标准

打开本机 Desktop：

```text
C:\Users\1\AppData\Local\hermes\hermes-agent\apps\desktop\release\win-unpacked\Hermes.exe
```

在 Desktop 对话中测试：

```text
帮我继续做 demo-product，查看这个产品下一步应该做什么。
```

通过标准：

```text
Desktop 能看到 product_creative 工具。
Desktop 能触发 product_workflow_run。
返回结果中出现 workflow_run_id / recommended_next_action / user_next_message。
外部 live 调用和 Product Brain 写入仍会停住等待确认。
```

## 5. 如果 Desktop 不通过

Desktop 不通过时，先不要改业务链路。优先确认：

```text
Desktop backend 是否从开发源码目录导入 hermes_cli。
HERMES_ENABLE_PROJECT_PLUGINS 是否对 Desktop backend 生效。
config.yaml 中 product_creative 是否启用。
Desktop 是否使用同一个 HERMES_HOME。
```

如果这些条件无法同时满足，M4.9 仍以项目内 Hermes chat 为主验收入口；Desktop 进入后续 UI / packaging 阶段处理。
