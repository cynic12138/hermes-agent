# M15 Fresh-install User-data 隔离修复记录

## 1. 结论

- 日期：2026-07-20（Asia/Shanghai）
- 分支：`product-creative-rebaseline-20260716`
- 验证时 HEAD：`93753c4d659480a81ee73f0246f692ef3cf70835`
- 实现提交：`f4c9807c1136a4cd7007e28b322511d901a9f880`
- 状态：`DONE_IN_PILOT_REF / UNPUBLISHED`
- 网络与外部调用：未联网；未调用 Provider、XHS、Douyin、DeepSeek 或生产 API。

M15 fresh-install 的 Electron `userData` 与 `HERMES_HOME` 隔离风险已经关闭。测试模式现在采用 fail-closed：只要缺少隔离根、Electron user-data 或 Hermes home，或者任一路径不在系统临时沙箱内，主进程就不会进入正常 Hermes 初始化。普通 Desktop 启动不受此规则影响。

真实打包壳正向验收中，临时沙箱产生 6 个运行写入，受保护的 37 个正式 Hermes 状态文件在启动前后哈希、长度和时间戳差异为 0；测试结束后残留测试进程为 0。

## 2. 问题与根因

旧 fresh-install harness 会传入 `HERMES_DESKTOP_USER_DATA_DIR` 和 `HERMES_HOME`，但 Electron 主进程只把它们当成可选覆盖项。测试人员直接启动 `win-unpacked/Hermes.exe`、环境变量在重启中丢失或路径填错时，程序可能回退到正式 `%APPDATA%\Hermes` 或 `%LOCALAPPDATA%\hermes`。

此前验收窗口内正式状态文件出现新时间戳。现有证据无法追溯具体是哪一次手工启动造成，因此历史因果仍是 `UNKNOWN`；本次不删除、不回滚、不覆盖这些文件。修复针对可确认的结构性缺口：测试模式过去没有强制隔离契约。

## 3. 实施细节

### Fail-closed 契约

`HERMES_DESKTOP_TEST_MODE=fresh-install` 时必须同时提供：

- `HERMES_DESKTOP_FRESH_SANDBOX_ROOT`
- `HERMES_DESKTOP_USER_DATA_DIR`
- `HERMES_HOME`

校验规则：

1. 三者必须是绝对路径。
2. sandbox root 必须位于当前系统临时目录下，目录名以 `hermes-desktop-fresh-install-` 开头。
3. Electron user-data 与 Hermes home 必须是 sandbox root 的严格子目录。
4. 两个写入目录必须彼此不同。
5. 任一条件失败即抛出可诊断错误，不读取 Windows 用户级 `HERMES_HOME`，也不回退到正式目录。

校验在 `require('electron')` 之前执行。通过后，主进程才调用 `app.setPath('userData', ...)`。fresh harness 同时给 Chromium 传入 `--user-data-dir=<sandbox path>`，形成环境变量校验和 Chromium 参数两层约束。

### 正常启动兼容

不处于 `fresh-install` 模式时，校验函数直接返回 `null`，原有用户级 Hermes home、profile 和 Desktop user-data 解析逻辑保持不变。本次没有修改业务 API、数据库结构、插件契约或 Product Creative 行为。

## 4. 修改文件

- `apps/desktop/electron/fresh-install-isolation.cjs`：纯路径校验与 fail-closed 契约。
- `apps/desktop/electron/fresh-install-isolation.test.cjs`：缺参、相对路径、越界路径、正常模式和合法沙箱测试。
- `apps/desktop/electron/main.cjs`：在加载 Electron 前执行校验，并使用已验证的 user-data 路径。
- `apps/desktop/scripts/test-desktop.mjs`：声明 sandbox root，并给 Chromium 传入显式 user-data 参数。
- `apps/desktop/package.json`：把隔离测试加入 Desktop platform suite。
- `tests/test_install_repository_override.py`：锁定 fresh harness 的 sandbox root、Playwright 和 Chromium user-data 参数。
- 本文及长期状态/交接/路线文档：记录结论和恢复方法。

## 5. 测试证据

### 自动化

- RED：新增测试首次因缺少 `fresh-install-isolation.cjs` 失败。
- GREEN：隔离单测 `5/5 passed`。
- 安装/fresh harness 静态契约：`5/5 passed`。
- Electron 主进程与新增模块语法检查：通过。
- 本次 Electron CJS 文件 ESLint：通过。
- Desktop production build：通过，`tsc -b`、Vite 和 dist assertion 均成功。
- `win-unpacked` 重新打包：通过。
- Desktop platform suite：298 项中 293 passed、2 skipped、3 failed。3 项是既有 Linux/bash relaunch 测试在原生 Windows 下的路径/bash 环境不兼容，与本次隔离代码无调用关系；未顺带修改。
- `git diff --check`：通过，仅有仓库既有 LF→CRLF 提示。

测试期间 Python 默认临时目录出现权限错误；改用仓库已有 `.test-tmp` 下的新 UUID 目录后，同一测试 5/5 通过。没有删除既有 `.t/` 或 `.test-tmp/`。

### 真实打包壳正向验收

- 可执行文件：仓库内 `apps/desktop/release/win-unpacked/Hermes.exe`。
- 复用沙箱：`C:\tmp\hermes-desktop-fresh-install-PFu67p`。
- 启动参数与环境均显式指向该沙箱；未使用正式 Hermes runtime。
- 实际启动 Electron 进程：5。
- 临时沙箱运行期新增/更新文件：6。
- 受保护正式状态文件：前 37、后 37、差异 0。
- 关闭后该测试可执行文件残留进程：0。

受保护范围包含正式 Hermes home 和 Electron user-data 的顶层持久文件，以及 Hermes `logs`、`cron`、`sessions`、`memories` 顶层状态文件；比较长度、UTC 时间戳和 SHA-256。

### 真实打包壳负向验收

故意只设置 `fresh-install`、删除 sandbox root 和 user-data 参数后，主进程进入诊断错误提示，未进入正常 Hermes。隐藏运行时错误提示等待人工关闭，因此 8 秒内没有自行退出；测试进程随后受控终止。正式关键状态文件差异仍为 0，残留测试进程为 0。

## 6. 恢复与复验

1. 先读 `AGENTS.md`、`docs/AI_HANDOFF.md`、`docs/PROJECT_STATE.md`、M15 实施记录、M15 打包验收记录和本文。
2. 运行 `git status --short`，保护用户现有修改和 `.t/`、`.test-tmp/`。
3. 运行隔离单测、安装契约测试和 Desktop production build。
4. 重新打包 `win-unpacked`，不要直接安装到正式 Hermes。
5. 确认正式 Hermes 进程未运行，记录正式状态文件的路径、长度、UTC 时间戳和 SHA-256。
6. 只用 `test:desktop:fresh` 产生的系统临时沙箱启动；不得手工删掉三项隔离环境变量。
7. 关闭所有本次测试进程后重复快照；任何差异都使验收失败，不自动回滚正式数据。

## 7. 已知限制与下一步

- 历史时间戳变化的具体来源不可追溯；本次结论是新构建在受控正/负向验证中实现零变化，不是声称历史变化从未发生。
- 错误参数的人工启动会显示诊断提示并等待关闭；这是可见的 fail-closed，不是静默继续。
- 当前修复提交 `f4c9807` 已推送到 `origin/product-creative-rebaseline-20260716`；尚未合并、tag 或发布。
- M15 下一门禁是内部运营人员完成 onboarding → 自然语言任务 → 三节点审阅 → 中断恢复 → 反馈/学习全链；M14 真实动态样片质量门禁继续独立保留。
