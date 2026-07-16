# M8 Product Review and Exact Main Image Video Architecture

状态：M8.0-M8.8 已完成 closeout 验证  
适用范围：`product_creative` 插件 M8 大版本开发

## 1. 主线定位

M8 不是新增平台抓取、模型 provider 或复杂 UI。M8 的目标是把 M0-M7 已有能力包装成用户能审阅、确认和复用的产品体验。

当前最高优先级：

```text
用户通过 Hermes 对话表达目标
  -> Product Creative 执行或推荐安全 workflow
  -> 系统把输入、Product Brain、素材、brief、provider/result、反馈和学习建议整理成可审阅包
  -> 对“主图不能变”的视频需求，使用确定性固定主图 composer，而不是依赖会重绘产品的视频模型
  -> 用户反馈
  -> proposal
  -> 人工确认后写回 Product Brain
```

## 2. M8 防偏原则

M8 必须满足：

```text
增强用户审阅闭环，而不是增加孤立脚本。
增强同一个产品的长期理解，而不是绑定测试产品。
所有 Product Brain 写入仍走 proposal / apply。
真实外部模型调用仍需要确认。
主图固定视频必须保持产品图层不被重绘、改字、换包装、裁剪或风格化。
脚本只作为开发回归入口；Hermes tools/workflow 是产品入口。
```

M8 不做：

```text
不开发完整视频编辑器。
不新增抖音/小红书抓取能力。
不新增视频大模型 provider。
不把 exact composer 结果自动判定为成功经验。
不让外部灵感或测试路径进入 Product Brain 事实。
```

## 3. M8.0-M8.8 版本范围

### M8.0 Architecture Lock

固定本文档与 `PRODUCT_MAINLINE_ROADMAP.md`，明确 M8 聚焦用户审阅和主图固定视频产品化。

### M8.1 Task Overview Package

新增 `task_overview_package`：

```text
Product Brain 摘要
当前主图
最新 workflow/result/brief/payload/feedback/evaluation/proposal
选中结果输出
主图锁定策略
下一步用户可做什么
```

目标：用户不用理解目录结构，也能看懂本次任务链路。

### M8.2 Video Result Review Enhancement

增强 `result-review-package`：

```text
当 result 带有 main_image_policy 时，审阅包必须展示主图锁定规则。
审阅清单必须包含包装、文字、图案、轮廓、颜色、吸嘴形态是否被改写。
```

### M8.3 Exact Main Image Composer

新增 `exact-main-image-composer`：

```text
输入：Product Brain、当前主图 material、主题/模板
输出：标准 generated video result artifact
执行：本地确定性合成，不调用外部视频模型
硬规则：主图作为固定图层；动漫角色、剧情字幕、动效只能发生在主图外部
```

适用场景：

```text
用户要求主图必须完全保持。
用户要求动漫/卡通/剧情推广，但产品包装不能被重绘。
外部视频模型多次重绘产品本体。
```

### M8.4 Video Story Templates

已增加少量模板：

```text
anime_story
summer_refresh
problem_solution
three_claims
festival_topic
```

### M8.5 Hermes Conversation Flow

用户说：

```text
用当前主图做一个动漫故事推广视频，主图不能变。
```

Hermes 已能选择：

```text
compose_exact_main_video
```

而不是默认走外部 `volcengine-ark-video` 图生视频。

### M8.6 Feedback to Preference

用户反馈：

```text
通过：主图固定，剧情围绕产品展开。
不通过：只是动效，没有故事。
```

系统记录为 result feedback，后续通过 result evaluation / proposal / apply 才能进入 Product Brain。

M8 closeout 已验证：

```text
result-feedback -> result-evaluate
evaluation 只生成 review_required 的 proposed_updates
不会直接修改 Product Brain
```

### M8.7 Minimal Review Surface

当前最小审阅面由 task-overview-package、result-review-package、preview gif/video path 组成。
后续可接 Hermes Desktop 或轻量 Web 审阅入口，但不是 M8 closeout 的前置条件。

### M8.8 Closeout

完整验证已通过：

```text
Hermes/tool 能生成 exact-main-video。
生成结果进入 generated_videos。
result-review-package 能展示主图锁定规则。
task-overview-package 能展示完整链路。
反馈和 proposal 边界仍然有效。
```

验证脚本：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m8_closeout.ps1 -ProductId <product-id>
```

## 4. 当前落地记录

M8.0-M8.8 已落地：

```text
module: .hermes/plugins/product_creative/m8_experience.py
cli:
  task-overview-package
  exact-main-video
tools:
  product_task_overview_package
  product_exact_main_video
workflow actions:
  create_task_overview_package
  compose_exact_main_video
templates:
  anime_story
  summer_refresh
  problem_solution
  three_claims
  festival_topic
validation:
  verify_m8_exact_main_video_loop.ps1
  verify_m8_closeout.ps1
```

## 5. 进入 M9 的条件

只有满足以下条件，才进入 M9：

```text
用户能通过 Hermes 对话触发 M8 任务总览和 exact-main-video。
用户能看到并审阅主图锁定策略。
exact composer 结果能进入 M7 反馈自迭代链路。
M8 没有把临时测试产品写成全局规则。
脚本仍只作为回归入口。
```
