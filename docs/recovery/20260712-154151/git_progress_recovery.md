# Git Progress Recovery

## 时间线

| 提交 | 状态 | 证据化结论 |
|---|---|---|
| `1d223d3` | CONFIRMED | 316 files、约 +50,270，M0–M8 durable runtime 汇总基线；tag `product-creative-durable-runtime-v1` |
| `f8bdb0c` | CONFIRMED | 48 files、约 +1,891/-48，M9 review/recovery 后端、6 个恢复命令和固定 Desktop 页面 |
| `822d879` | CONFIRMED | 2 files、+43/-2，Windows 插件 clone 只读文件删除修复 |
| 工作区 | PARTIAL | M9.1 通用 Desktop Plugin SDK + plugin-owned console 迁移，未提交 |

本地只看到 4 条提交，M0–M8 的阶段顺序主要来自文档，不能从 Git 逐阶段独立证明。

## 已完成

- **CONFIRMED** durable runtime、M9 review/recovery backend、6 个受控恢复命令。
- **INFERRED** M0–M8 多数契约链路曾通过脚本验证；当前环境是否仍全部通过需重新运行。

## 部分完成

- **PARTIAL** M9.1：工作区有连贯实现与局部测试，但未提交、未完整 build/E2E。
- **PARTIAL** production provider：真实路径存在，但依赖外部服务/凭据/开关/确认。

## 未开始

- **PLANNED** M10 guided generation launch controls。

## 被替换方向

- HEAD 的 Product Creative 专属 Desktop route/component 正被通用 Desktop Plugin SDK 替换；控制台不是被放弃，而是改变交付归属。
- M2 已冻结；M6 放弃“remote_url 优先”的旧理解。

## 高风险未提交内容

旧页面已删除，新 registry/page/bundle/test 未跟踪；若工作区丢失或只保存 tracked 文件，Desktop 会构建断裂且 M9.1 成果不可恢复。远端仅备份到 `822d879`。

## 自然衔接点

先确认 M9.1 方向和版本语义，保护全部新文件，完成无副作用测试、Desktop build 和隔离 E2E；再由用户决定提交/发布。M9.1 未收口前不进入 M10。
