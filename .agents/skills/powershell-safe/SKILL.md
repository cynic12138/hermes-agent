---
name: powershell-safe
description: 在 Windows 原生 PowerShell 环境执行命令、处理路径、运行 npm、Python、Git、文件读写、编码、删除、覆盖、移动或批量操作时使用，以保证命令语法、路径、编码和破坏性操作安全。
---

# PowerShell Safe

## 命令与路径

1. 使用 Windows 原生 PowerShell，不假定 Bash/WSL/POSIX 工具。
2. 使用 `Join-Path` 或完整路径；含空格路径必须引用。
3. 用户路径优先 `-LiteralPath`。
4. 优先 `npm.cmd`、`npx.cmd`。
5. 不混用 Linux/Windows 路径；环境变量用 `$env:NAME`。

## 禁止形式

- 禁止 `rm -rf`、`curl | bash`、Bash heredoc。

## 文件与编码

1. 文本明确使用 UTF-8。
2. 中文读取显式 UTF-8。
3. 删除、覆盖、移动或批量修改前列出目标并验证绝对范围。
4. 破坏性操作必须请求用户确认。

## 失败处理

先判断 PowerShell 语法、可执行文件、权限、路径或编码根因；不因一次失败切换高风险方案；报告失败命令、原因和安全下一步。
