# M6 Material Resolver and Inspiration Gateway Architecture

状态：M6.1-M6.10 已完成；凭据配置后小红书/抖音 sidecar 小样本真实验证已跑通  
创建日期：2026-07-08  
本次修订：2026-07-08  
适用范围：`product_creative` 插件 M6 大版本开发  

本文档替代早版 `M6 Asset Hosting and External Inspiration Architecture`。早版把 M6 过多描述成 `remote_url` 和“外部搜索/竞品灵感”，本版按用户最新澄清重新定锚：

```text
M6 = 素材执行输入解析层 + 外部灵感采集闸门层
```

M6 的目的不是做一个爬虫工具，也不是做素材 CDN，更不是把热点直接塞进 Product Brain。M6 的目的，是让 Hermes 能安全地把“本地素材”和“外部灵感”带入文案、图片、视频生成闭环，并继续保持 Product Brain 的确认门禁。

---

## 1. 本版核心结论

### 1.1 M6 的主线修正

M6 不应再被理解为：

```text
先做 remote_url，再做竞品搜索。
```

应修正为：

```text
先做 MaterialResolver，让本地素材、远程 URL、data URL、后续对象存储 URL 都能统一变成外部模型可用输入。
再做 Inspiration Gateway，让小红书、抖音、通用搜索、手动资料都能统一变成可审计灵感，而不是直接污染产品事实。
```

### 1.2 灵感不是竞品信息

本项目中的“灵感”不是专指竞品。

灵感包括：

```text
热点话题
平台爆款结构
热门梗
情绪场景
画面题材
视频节奏
评论痛点
标题钩子
用户说法
竞品表达
行业趋势
节日/时令
科幻、搞笑、情感、高级感等创意方向
```

这些内容的作用是帮助 Hermes 生成更贴近渠道和当下语境的文案、图片 brief、视频分镜和 prompt。它们不是产品事实，不能直接写入 Product Brain。

### 1.3 remote_url 不是唯一方案

豆包 Ark 视频生成接口不是 multipart 文件上传接口，也不能直接读取用户电脑本地路径。它接收 JSON `content[]`。

根据官方文档调研：

```text
图片：可用公开 URL、Base64 data URL、asset://<ASSET_ID>
音频：可用公开 URL、Base64 data URL、asset://<ASSET_ID>
视频：官方主要支持视频 URL、asset://<ASSET_ID>
本地文件路径：不能直接传给云端模型
```

因此 M6 不能写成“所有素材必须上传云端”。正确策略是：

```text
本地素材永远是 canonical material。
小图片 / 小音频可以优先转 data URL。
视频 / 大素材 / 需要复用的素材使用对象存储或预签名 URL。
remote_url 只是 provider execution handle，不是素材真相。
```

---

## 2. M6 与最终产品目标的关系

最终产品目标仍然是：

```text
围绕一个产品或一个目标持续认知、持续生成、持续反馈、持续变得更懂产品。
```

M6 对这个目标的贡献是：

```text
让 Hermes 能使用用户已有本地素材，而不是要求用户理解外部模型 URL 规则。
让 Hermes 能从小红书、抖音、网络、手动资料中获得创意输入。
让 Hermes 能判断哪些外部资料和当前产品有关。
让 Hermes 能把外部资料挖掘成灵感候选。
让灵感参与文案、图片、视频生成，但不越权成为产品事实。
让用户选择、反馈、确认后，才把有效灵感沉淀为渠道 playbook 或 Product Brain proposal。
```

一句话：

```text
M6 让系统从“只基于已有 Product Brain 生成”升级为“基于 Product Brain + 本地素材 + 外部灵感生成”，但仍保持自迭代的安全边界。
```

---

## 3. 当前调研结论

### 3.1 Hermes 原生搜索能力

Hermes 本身已有通用网络搜索和网页抽取工具能力，当前源码中能看到：

```text
tools/web_tools.py
plugins/web/*
```

它适合做：

```text
通用网页搜索
公开网页摘要
行业信息搜索
普通热点资料收集
GEO / SEO 资料收集
```

但它不等价于：

```text
小红书专项搜索
抖音热门视频抓取
平台评论/笔记/视频转写
平台爆款结构拆解
```

所以 M6 的设计应是：

```text
通用 Web：优先复用 Hermes 原生 web_search / web_extract。
小红书 / 抖音：封装为 product_creative 的 external source provider。
```

### 3.2 小红书项目调研结论

本地项目：

```text
C:\data\work file\小红书数据自动抓取系统
```

它的核心能力是：

```text
浏览器 Cookie 登录态
关键词搜索小红书笔记
笔记详情补全
评论抓取
作者资料 / 作者作品补全
本地爆款分析
AI 报告和导出
```

关键模块：

```text
src/server/services/redbookService.ts
src/server/services/jobService.ts
src/server/services/browserAuthService.ts
src/server/services/authState.ts
src/server/services/queryService.ts
src/server/services/normalizers.ts
src/server/storage/localStore.ts
browser-extension/xhs-bridge/*
```

最值得吸收的是：

```text
只读 source provider 思路
任务队列 / 限速 / 风险暂停
平台字段归一化
标题钩子、评论主题、热度分等灵感指标
浏览器插件同步 Cookie 的用户授权模式
```

不应照搬的是：

```text
整套 React 工作台 UI
Cookie 持久化细节
平台原始 raw 数据长期进入 product_creative
评论回复、点赞、收藏、删除等平台写操作
让抓取流程隐式触发而不经过用户确认
```

建议封装为：

```text
xhs_local_research_provider
```

第一阶段通过本机 sidecar HTTP API 或导出 JSON 接入，不把整个 Node/TS 项目迁进 Python 插件。

长期选择性内化锚点：

```text
M6 MVP：外部 sidecar 调用。
M7/M8 后：只把字段归一化、脱敏、热度/钩子/评论主题分析、snapshot sanitizer 等稳定逻辑选择性重写进 product_creative。
不内化或谨慎内化：Cookie 获取、浏览器插件、底层平台请求、风控规避相关代码。
```

### 3.3 抖音项目调研结论

本地项目：

```text
C:\data\work file\抖音爆款视频抓取
```

它的核心能力是：

```text
关键词搜索抖音候选视频
Cookie / cURL 方式增强登录态
requests 搜索失败时使用本机 Edge + Playwright 捕获搜索响应
下载或临时下载视频
抽取音频
调用硅基流动 ASR 转写
调用 DeepSeek 或本地规则拆解文案钩子
```

关键模块：

```text
app/main.py
app/douyin.py
app/browser_search.py
app/transcription.py
app/deepseek_analysis.py
app/copy_analysis.py
```

最值得吸收的是：

```text
搜索候选 -> 转写 -> 钩子拆解 -> inspiration candidate
在线转写后删除临时视频，只保留 transcript / analysis 的轻量模式
用启发式评分做第一层筛选
用 DeepSeek / Hermes 中枢模型做第二层结构化拆解
```

不应照搬的是：

```text
把 A-Bogus / X-Bogus 细节变成主产品强依赖
默认下载大量真实视频
把平台原始响应长期写入 Product Brain
把疑似广告/购物评分当成确定事实
把 Cookie 明文写入 artifact
```

建议封装为：

```text
douyin_local_research_provider
```

默认模式应是：

```text
transcript-only / summary-only
```

只有用户明确确认时，才保存外部视频文件。

长期选择性内化锚点：

```text
M6 MVP：外部 sidecar 调用。
M7/M8 后：优先内化 transcript/copy_analysis 导入、文案钩子拆解 prompt、搜索结果归一化、轻量本地规则分析。
不优先内化：A-Bogus/X-Bogus、平台反爬细节、浏览器响应捕获、Cookie 长期管理。
```

### 3.4 豆包 Ark 视频模型素材输入调研结论

官方资料显示，Ark `contents/generations/tasks` 是 JSON 请求，不是 multipart 文件上传。素材在 `content[]` 内传入。

M6 的正确抽象不是“remote_url provider”，而是：

```text
MaterialResolver
```

MaterialResolver 负责把以下输入：

```text
本地图片
本地音频
本地视频
已有远程 URL
已生成图片 / 视频
用户上传素材
小红书 / 抖音 / 网络下载素材
```

解析为目标 provider 可接受的执行输入：

```text
data:image/...;base64,...
data:audio/...;base64,...
https://... 预签名 URL
asset://<ASSET_ID>
手动绑定 URL
```

官方参考资料：

```text
https://docs.byteplus.com/en/docs/ModelArk/1520757
https://www.volcengine.com/docs/82379/1520757
https://docs.byteplus.com/en/docs/ModelArk/2291680
https://docs.byteplus.com/en/docs/modelark/2551760
```

---

## 4. M6 不做什么

M6 不做：

```text
不做完整爬虫平台。
不做平台自动发布。
不做平台写操作。
不绕过验证码或平台安全机制。
不把 Cookie/API Key 写入 Product Brain 或 artifact。
不把外部热点直接写入 Product Brain。
不把竞品事实当成当前产品事实。
不做重型向量数据库，除非文件读取方案已成为瓶颈。
不做复杂 UI。
不默认上传用户本地素材到云端。
不默认下载和保存大量外部视频。
```

M6 可以接入本地已有项目的能力，但只能抽取核心 provider 能力，不应把它们原样并入当前产品。

---

## 5. 总体架构

```text
User Intent
  -> Hermes Agent Workflow
  -> Product Workspace Resolve
  -> Product Brain / Product State
  -> Material Library
  -> Inspiration Gateway
       -> Generic Web Provider
       -> XHS Local Research Provider
       -> Douyin Local Research Provider
       -> Manual Import Provider
  -> Source Snapshot
  -> Inspiration Signal
  -> Product Relevance Gate
  -> Inspiration Candidate
  -> Inspiration Pack
  -> Copy / Image / Video Brief
  -> MaterialResolver
       -> data-url
       -> manual URL
       -> object storage signed URL
       -> asset:// id
  -> Provider Payload
  -> Image / Video Generation
  -> Generated Artifact
  -> User Feedback
  -> Proposal
  -> Human Apply
  -> Product Brain / Channel Playbook
```

核心原则：

```text
Product Brain 是事实锚点。
Material Library 是本地素材真相。
External Source Snapshot 是外部证据快照。
Inspiration Candidate 是创意输入，不是产品事实。
MaterialResolver 是外部模型执行输入适配层。
Proposal / Human Apply 是自迭代写入边界。
```

---

## 6. 核心数据对象

### 6.1 External Source Snapshot

用于保存外部资料采集结果。

建议字段：

```json
{
  "snapshot_id": "source-snapshot-...",
  "product_id": "zhou15-honeydew",
  "provider": "xiaohongshu | douyin | generic-web | manual-import",
  "query": "蜂蜜露 夏天 种草",
  "channel": "xiaohongshu",
  "captured_at": "2026-07-08T00:00:00Z",
  "items": [],
  "summary": "",
  "source_urls": [],
  "raw_ref_path": "",
  "credential_ref": "local-session-only",
  "sanitization": {
    "cookie_saved": false,
    "raw_private_fields_removed": true,
    "author_anonymized": true
  },
  "risk_flags": [],
  "not_product_fact": true
}
```

### 6.2 Inspiration Signal

用于从 source snapshot 中提取可复用模式。

建议字段：

```json
{
  "signal_id": "inspiration-signal-...",
  "snapshot_id": "source-snapshot-...",
  "signal_type": "hook | scene | meme | trend | visual_style | rhythm | pain_point | comment_insight",
  "text": "",
  "evidence": "",
  "channel": "douyin",
  "confidence": 0.72,
  "not_product_fact": true
}
```

### 6.3 Inspiration Candidate

用于把外部灵感转成当前产品可使用的生成方向。

建议字段：

```json
{
  "candidate_id": "inspiration-candidate-...",
  "product_id": "zhou15-honeydew",
  "source_snapshot_ids": [],
  "signal_ids": [],
  "usable_for": ["copy", "image_brief", "video_brief"],
  "angle": "",
  "hook": "",
  "scene": "",
  "visual_direction": "",
  "script_structure": "",
  "product_fit_reason": "",
  "risks": [],
  "confidence": 0.75,
  "not_product_fact": true,
  "requires_confirmation_for_playbook": true
}
```

### 6.4 Inspiration Pack

用于一次生成任务的灵感输入包。

建议字段：

```json
{
  "pack_id": "inspiration-pack-...",
  "product_id": "zhou15-honeydew",
  "goal": "今日抖音短视频",
  "selected_candidate_ids": [],
  "excluded_candidate_ids": [],
  "brief_context": "",
  "created_at": ""
}
```

### 6.5 Material Execution Input

用于统一记录某个素材如何进入外部模型。

建议字段：

```json
{
  "execution_input_id": "material-input-...",
  "product_id": "zhou15-honeydew",
  "material_id": "material-...",
  "provider": "volcengine-ark-video",
  "role": "reference_image | reference_video | reference_audio",
  "input_kind": "data_url | remote_url | asset_id | manual_url",
  "value_ref": "redacted-or-path",
  "mime_type": "image/png",
  "size_bytes": 123456,
  "expires_at": "",
  "created_at": "",
  "confirmed": true,
  "not_canonical_source": true
}
```

---

## 7. MaterialResolver 设计

### 7.1 职责

MaterialResolver 负责回答一个问题：

```text
这个本地素材，要给这个 provider 做这件事时，应该用什么输入形式？
```

它不是素材库本身，也不是云存储系统。

### 7.2 决策顺序

```text
1. 如果已有 provider-specific remote link 且未过期，优先使用。
2. 如果 provider 支持 data URL，且素材是小图片或小音频，转成 data URL。
3. 如果 provider 支持 asset:// 并且素材已在该 provider 资产库，使用 asset id。
4. 如果素材是视频、大图片、大音频，或 data URL 超出限制，进入对象存储/预签名 URL 流程。
5. 如果没有对象存储配置，停下请求用户绑定 URL 或确认上传配置。
```

### 7.3 对豆包 Ark 的默认策略

```text
图片参考：小图优先 data URL；已有 URL 时可用 URL；后续支持 asset://。
音频参考：小音频可 data URL；大音频走对象存储 URL。
视频参考：走 URL 或 asset://；不设计视频 Base64 默认路径。
本地路径：不能直接给 Ark。
```

### 7.4 与 M2/M3/M4/M5 的关系

```text
M2 图片理解：继续保存 image analysis artifact。
M3 素材库：继续保存本地 canonical material 和 material card。
M4 生图：payload 构建前调用 MaterialResolver。
M5 生视频：payload 构建前调用 MaterialResolver。
M6：补齐统一执行输入和缺失输入时的对话停顿。
```

---

## 8. External Source Provider 设计

### 8.1 Provider Contract

所有外部来源统一成：

```text
collect -> normalize -> snapshot -> mine -> candidate -> pack
```

Provider 输入：

```json
{
  "product_id": "",
  "goal": "",
  "channel": "",
  "queries": [],
  "limits": {
    "items": 20,
    "comments": 50,
    "videos_to_transcribe": 3
  },
  "auth_mode": "none | user_cookie | browser_session | sidecar",
  "consent": {
    "user_confirmed_external_collection": true
  }
}
```

Provider 输出：

```json
{
  "snapshot_id": "",
  "provider": "",
  "items_count": 0,
  "risk_flags": [],
  "artifact_paths": []
}
```

### 8.2 Generic Web Provider

实现方式：

```text
复用 Hermes web_search / web_extract。
保存搜索词、结果 URL、摘要、抓取时间。
适合公开网页、行业资料、新闻、平台外热点、GEO/SEO。
```

### 8.3 XHS Local Research Provider

实现方式建议：

```text
M6 初期：通过 sidecar HTTP API 或导出 JSON 接入现有小红书项目。
后续：如稳定，再抽取最小 Node adapter 或 provider wrapper。
```

输入：

```text
keywords
note_type
sort
pages
include_comments
limit
```

输出：

```text
笔记标题 / 描述 / 互动指标 / 评论主题 / 图片或视频 URL 摘要 / 来源 URL
```

安全边界：

```text
用户必须主动登录或授权 Cookie。
Cookie 不进入 product_creative artifact。
原始 raw 默认不长期保存。
评论作者可匿名化。
遇到验证码、风控、登录失效时停下。
```

### 8.4 Douyin Local Research Provider

实现方式建议：

```text
M6 初期：通过 sidecar FastAPI 或导出 transcript JSON 接入现有抖音项目。
默认 transcript-only，不默认保存视频文件。
```

输入：

```text
keyword
sort / time / duration filters
max_videos
transcribe_limit
cookie_or_browser_session
```

输出：

```text
视频标题 / 作者摘要 / 互动指标 / share_url / transcript / hook analysis / rhythm / selling-point structure
```

安全边界：

```text
Cookie 只作为用户显式授权的本地会话。
不绕过验证码。
不做自动发布、点赞、评论。
真实视频下载需用户确认。
ASR key 和 DeepSeek key 不写入 artifact。
能复用 Hermes 当前主模型时，优先让 Hermes 中枢做钩子拆解；硅基流动只作为 ASR provider。
```

---

## 9. Inspiration Mining 设计

外部资料进入系统后，必须经过四层处理。

### 9.1 相关性判断

Hermes 需要根据 Product Brain 判断：

```text
这个外部资料是否和当前产品有关？
它是产品同类、场景相关、用户情绪相关，还是只是热门但不适合？
它适合文案、图片、视频，还是只适合观察？
```

输出字段：

```text
product_relevance_score
fit_reason
misfit_reason
risk_flags
```

### 9.2 灵感点挖掘

提取：

```text
钩子
冲突
痛点
场景
情绪
视觉题材
镜头节奏
话术结构
评论洞察
可复用公式
```

### 9.3 产品化改写

把灵感改写为当前产品可用方向。

例：

```text
外部灵感：最近饮品视频常用“第一口表情反差”。
产品化候选：周十五蜂蜜露可以做“第一口不是甜腻，是清爽回甘”的 3 秒开场。
```

### 9.4 写入边界

```text
Inspiration Candidate 可以进入 brief。
Inspiration Candidate 不可以直接进入 Product Brain。
用户反馈“这个方向有效”后，只能生成 channel playbook proposal。
proposal apply 必须人工确认。
```

---

## 10. Hermes 对话体验目标

### 10.1 用户说“帮我做今天的小红书种草”

Hermes 应执行：

```text
1. resolve product workspace。
2. 读取 Product Brain 和已有 material cards。
3. 判断是否需要外部灵感。
4. 如果用户允许，调用 generic web 或 xhs provider 收集 source snapshot。
5. 生成 inspiration candidates。
6. 选择最适合当前产品的 inspiration pack。
7. 生成小红书文案 brief / variants。
8. 用户反馈后生成 proposal，但不自动 apply。
```

### 10.2 用户说“参考最近抖音爆款，给我做一个视频”

Hermes 应执行：

```text
1. 读取 Product Brain。
2. 读取当前产品主图/素材。
3. 调用 douyin provider 获取 transcript / hook patterns。
4. 生成 inspiration candidates。
5. 生成视频分镜脚本和 provider-ready prompt。
6. 调用 MaterialResolver 检查参考图/音频/视频输入是否可用于豆包。
7. 如果素材输入未就绪，停下说明需要 data-url、绑定 URL 或对象存储配置。
8. 用户确认后进入 M5 视频任务提交。
```

### 10.3 用户上传一张主图，要求图生视频

Hermes 应执行：

```text
1. 注册本地图片为 material。
2. 调用 M2 多模态理解，生成 image analysis。
3. visual-align 检查是否符合当前产品。
4. 生成或更新 material card。
5. 生成 video brief。
6. MaterialResolver 为豆包 video provider 准备 reference_image 输入。
7. 小图可用 data URL；大图或需要复用时请求绑定/上传。
8. 用户确认 brief 和真实调用后，进入 M5。
```

---

## 11. M6 小版本计划

### M6.1 Schema and Boundary Refresh

目标：

```text
建立 source snapshot、inspiration signal、inspiration candidate、inspiration pack、material execution input 的数据契约。
```

开发范围：

```text
新增 artifact/index schema。
补充 Product Brain 写入边界。
更新 roadmap 和 conversation protocol。
```

验收：

```text
外部资料、灵感、产品事实、执行输入四者边界清楚。
默认不调用外部平台。
```

### M6.2 MaterialResolver MVP

目标：

```text
让本地素材能按 provider 能力解析为 data URL、已有 remote URL、manual URL 或待上传状态。
```

开发范围：

```text
provider capability matrix。
material execution input artifact。
图片/音频 data URL 小文件路径。
视频/大文件阻断并给出用户下一步。
```

验收：

```text
Hermes 不再简单说“缺 remote_url”，而能解释为什么可用 data URL、为什么需要 URL、为什么需要对象存储。
```

### M6.3 Generic Web and Manual Import Source Provider

目标：

```text
先用低风险来源跑通 external source snapshot 到 inspiration candidate 的链路。
```

开发范围：

```text
manual import provider。
generic web snapshot adapter。
snapshot sanitizer。
inspiration candidate generator。
```

验收：

```text
一段手动粘贴热点资料或公开网页摘要，可以生成 inspiration candidates。
不写 Product Brain。
```

### M6.4 XHS Local Research Provider Adapter

目标：

```text
把本地小红书项目能力接成只读 source provider。
```

开发范围：

```text
sidecar health check。
export/import snapshot path。
XHS note normalization。
评论主题 / 标题钩子 / 热度分摘要。
Cookie 风险边界说明。
```

验收：

```text
不读取或打印 Cookie。
不复制整套 UI。
能把小红书笔记集合转成 external source snapshot。
允许通过用户已授权的本地浏览器登录态或 sidecar 自动读取浏览器 Cookie，但必须有风控状态、失败停顿和日志脱敏。
```

### M6.5 Douyin Local Research Provider Adapter

目标：

```text
把本地抖音项目能力接成 transcript-first source provider。
```

开发范围：

```text
sidecar health check。
search result import。
transcript / copy analysis import。
ASR / DeepSeek 使用边界。
```

验收：

```text
默认不保存外部视频文件。
能把 transcript 和钩子拆解转成 inspiration candidates。
少量真实抓取测试必须跑通：搜索候选、选择少量视频、转写或导入已有 transcript、提取爆款文案结构。
Cookie/API Key 不进入 product_creative artifact。
```

### M6.6 Product Relevance and Inspiration Mining

目标：

```text
让 Hermes 判断外部资料是否适合当前产品，并挖掘灵感点。
```

开发范围：

```text
product_relevance_score。
fit_reason / misfit_reason。
signal extraction。
candidate productization。
```

验收：

```text
热门但不适合的素材不会进入 inspiration pack。
候选能解释为什么适合当前产品。
```

### M6.7 Inspiration Pack to Brief Integration

目标：

```text
让文案、图片 brief、视频 brief 能读取被选中的 inspiration pack。
```

开发范围：

```text
copy generate context。
image brief context。
video brief/storyboard context。
artifact provenance。
```

验收：

```text
生成结果能追溯到 Product Brain、素材、inspiration candidate。
灵感影响表达角度，不覆盖产品事实。
```

### M6.8 MaterialResolver to Image/Video Payload Integration

目标：

```text
让 M4/M5 payload 构建统一调用 MaterialResolver。
```

开发范围：

```text
image provider payload input resolution。
video provider payload input resolution。
data URL redaction in artifacts。
manual bind compatibility。
```

验收：

```text
小图片无需手动 remote_url 也可进入支持 data URL 的 provider payload。
视频参考素材仍能正确提示需要 URL/asset。
```

### M6.9 Hermes Conversational End-to-End Validation

目标：

```text
以 Hermes 对话方式验证完整链路，而不是只用脚本。
```

开发范围：

```text
workflow-run actions。
user_next_message。
需要确认时的停顿原因。
```

验收：

```text
用户能用自然语言触发：收集灵感 -> 生成候选 -> 生成 brief -> 解析素材输入。
脚本只作为回归验证。
```

### M6.10 M6 Closeout

目标：

```text
确认 M6 没有跑偏，并定义进入 M7 的条件。
```

验收：

```text
MaterialResolver 已接入生成链路。
外部灵感已接入 brief 链路。
外部资料不会直接污染 Product Brain。
真实平台抓取、真实上传、真实模型调用都有确认边界。
Hermes 对话入口能解释当前流程卡点。
```

---

## 12. 验证策略

### 12.1 默认回归

默认回归默认不做：

```text
不调用真实生图/生视频模型。
不上传真实素材到对象存储。
不抓取需要 Cookie 的平台数据。
不写 Product Brain。
```

默认验证：

```text
使用手动导入资料或 fixture。
使用已有本地素材。
检查 artifact 和 index。
检查 Hermes workflow 的 user_next_message。
检查 proposal/apply 边界。
```

### 12.2 小红书 / 抖音专项 live 验证

用户已确认 M6 全流程完成后必须进行少量真实数据验证。执行边界：

```text
启动 sidecar 项目。
使用用户登录态或 Cookie。
进行少量真实搜索。
调用硅基流动 ASR。
调用 DeepSeek / Hermes 主模型做结构化拆解。
抓取数量必须小：小红书 1 个关键词、1 页、少量笔记；抖音 1 个关键词、少量候选、1-2 条转写。
```

验证后必须记录：

```text
external_collection_performed
provider
query
captured_at
items_count
cookie_saved=false
raw_private_fields_removed=true
```

### 12.3 豆包素材输入验证

默认使用 dry-run payload。

可选 live 验证：

```text
小图片 data URL provider payload。
已有公网 URL provider payload。
视频 URL provider payload。
对象存储预签名 URL provider payload。
```

真实调用必须由用户确认。

---

## 13. 安全与合规边界

### 13.1 Cookie

```text
Cookie 只能作为用户显式授权的本地会话凭据。
用户已确认允许 Hermes/sidecar 自动读取本机浏览器 Cookie，以降低使用门槛。
自动读取必须优先通过 sidecar 已有能力执行，并且遇到验证码、风控、登录失效时停止。
不能写入 Product Brain。
不能写入 artifact。
不能出现在日志和测试输出。
能用 credential_ref 表示“使用了某种本地授权方式”。
```

### 13.2 外部平台数据

```text
只读采集。
不做平台写操作。
遇到验证码、风控、登录失效必须停下。
不把个人敏感信息作为长期知识沉淀。
评论作者默认匿名化。
```

### 13.3 外部模型输入

```text
本地素材上传外部存储前必须确认。
data URL 在 artifact 中必须脱敏。
预签名 URL 日志中不打印完整 query。
provider payload 保存必要追溯信息，不保存秘密。
M6 现阶段视频素材 URL/对象存储不是主攻方向；优先服务前置文案、图片 brief、视频脚本/分镜和图像素材生成。
```

---

## 13.4 Sidecar 到内置能力的演化规则

M6 MVP 的集成方式已经确认：

```text
当前：通过 sidecar provider 外部调用两个本地项目。
后续：链路跑通且边界稳定后，再把必要功能选择性提取重写进当前项目。
```

选择性内化的判断标准：

```text
该能力是否稳定，不频繁受平台反爬变化影响？
该能力是否与 Product Brain / brief / inspiration schema 强相关？
该能力是否可以脱离 Cookie 和登录态独立运行？
该能力是否能减少用户负担，而不是扩大维护成本？
该能力是否不会把平台 raw data、账号信息或秘密带入 product_creative？
```

优先内化：

```text
字段归一化 normalizer
snapshot sanitizer
inspiration signal 提取
product relevance scoring
hook / scene / rhythm / comment insight 轻量分析
transcript/copy_analysis 导入和格式转换
```

继续隔离在 sidecar：

```text
浏览器插件
平台 Cookie 获取
真实平台请求与反爬适配
Edge/Playwright 响应捕获
大批量抓取队列
平台账号登录状态管理
```

---

## 14. 进入 M7 的条件

只有满足以下条件，才进入 M7 数据反馈与内容实验飞轮：

```text
Hermes 能通过对话触发 M6 核心链路。
MaterialResolver 能解释并生成 provider execution input。
小图/小音频 data URL 策略可用。
视频/大素材能明确提示需要 URL/asset/object storage。
外部资料能进入 source snapshot。
外部资料能被挖掘成 inspiration candidate。
inspiration pack 能进入文案、图片 brief、视频 brief。
Product Brain 写入仍必须 proposal + human apply。
小红书/抖音专项能力已作为 sidecar provider 接入或完成可验证设计。
默认验证不依赖真实 Cookie、真实上传、真实付费模型调用。
```

禁止进入 M7 的情况：

```text
用户仍需要手动理解 provider image_url/video_url 规则。
外部资料可以绕过 proposal 写入 Product Brain。
小红书/抖音能力只是散落脚本，未进入 Hermes workflow。
M6 只能靠 product_creative.ps1 命令使用，不能通过 Hermes 对话解释下一步。
Cookie/API Key 有进入 artifact 的风险。
```

---

## 15. 用户确认记录

确认结果：

```text
1. 确认 M6 定锚为 Material Resolver and Inspiration Gateway。
2. 确认 M6 必须打通两个外部工具，并在全流程完成后做少量真实平台抓取测试。
3. 确认小红书和抖音先以 sidecar provider 接入；后续再选择性提取重写必要功能，并在本文档 13.4 固定。
4. 确认允许 Hermes/sidecar 自动读取浏览器 Cookie，但必须保留风控、失败停顿和脱敏边界。
5. 确认 M6 现阶段不把视频素材 URL/对象存储作为主攻方向；优先围绕文案、图片 brief、视频脚本/分镜和前置图像素材生成。
6. 确认默认验证可以不调用真实外部平台/模型，但整体开发完成后必须跑一次小样本真实数据和模型链路验证最终结果。
```

---

## 15.1 M6.1-M6.10 开发落地记录

落地日期：2026-07-08

已完成能力：

```text
M6.1 Schema and Boundary Refresh：新增 provider capability、material execution input、external source snapshot、inspiration candidate、inspiration pack schema。
M6.2 MaterialResolver MVP：本地图片可解析为 provider-ready data URL，artifact 只保存脱敏 value_ref。
M6.3 Generic Web and Manual Import：支持 manual / manual-import / generic-web source snapshot。
M6.4 XHS Sidecar Adapter：接入本地小红书 sidecar，支持 health、browser-cookie attempt、search job、notes、analytics。
M6.5 Douyin Sidecar Adapter：接入本地抖音 sidecar，支持 health、search、少量 transcribe-online。
M6.6 Product Relevance and Inspiration Mining：外部素材转 inspiration signal / inspiration candidate，统一 not_product_fact。
M6.7 Inspiration Pack to Brief：latest inspiration pack 已进入文案生成、图片 brief、视频 brief 的 generation context。
M6.8 MaterialResolver to Payload：视频 provider payload 已优先通过 MaterialResolver 使用 provider-ready handle。
M6.9 Hermes Workflow：product_workflow_run 已能识别并执行 M6 action。
M6.10 Closeout：新增离线验证脚本和 sidecar live 小样本验证脚本。
```

新增验证脚本：

```text
.hermes/plugins/product_creative/scripts/verify_m6_material_inspiration_loop.ps1
.hermes/plugins/product_creative/scripts/verify_m6_sidecar_live_small.ps1
```

离线主链路验证结果：

```text
command: .\.hermes\plugins\product_creative\scripts\verify_m6_material_inspiration_loop.ps1
status: passed
product_id: m6-material-inspiration-test
material_input_kind: data_url
source_snapshot_id: source-snapshot-20260708-163354
inspiration_candidates: 1
inspiration_pack_id: inspiration-pack-20260708-163357
workflow_run_id: workflow-run-20260708-163359
external_call_performed: false
```

Workflow 自动续跑边界：

```text
M6 动作只允许在同一条 M6 链路内自动续跑。
collect_external_source_snapshot -> create_inspiration_candidates -> create_inspiration_pack 可以自动推进。
collect_external_source_snapshot -> create_llm_inspiration_pack 可以在用户明确要求 LLM 深度总结时推进。
create_inspiration_pack 完成后以 requested_m6_step_completed 停止，不继续跳到素材卡片、图片、视频或反馈动作。
create_llm_inspiration_pack 完成后必须停下给用户审阅。
confirm_inspiration_library_entry 必须由用户显式确认，不允许自动续跑。
```

真实 sidecar 小样本验证结果：

```text
initial_command: .\.hermes\plugins\product_creative\scripts\verify_m6_sidecar_live_small.ps1 -RunLive -ProductId m6-sidecar-live-test -Query "蜂蜜饮品" -Limit 2 -WaitSeconds 120
initial_status: sidecar reached, platform data blocked by credentials/session

credentialed_command: .\.hermes\plugins\product_creative\scripts\verify_m6_sidecar_live_small.ps1 -RunLive -RequireItems -ProductId m6-sidecar-live-test -Query "蜂蜜饮品" -Limit 2 -WaitSeconds 180
credentialed_status: passed
xhs_health: true
xhs_snapshot_id: source-snapshot-20260708-170931
xhs_status: completed
xhs_items_count: 2
xhs_inspiration_pack_id: inspiration-pack-20260708-171004
douyin_health: true
douyin_snapshot_id: source-snapshot-20260708-170008
douyin_status: completed
douyin_items_count: 2
douyin_inspiration_pack_id: inspiration-pack-20260708-170010
external_call_performed: true
credential_policy: Product Creative artifacts did not save cookies or API keys
```

结论：

```text
M6 代码链路已经接到真实本地 sidecar。
凭据配置后，M6 已经取得真实小红书与抖音平台条目，并完成 source snapshot -> inspiration candidate -> inspiration pack 写回。
Product Creative artifact 不保存 Cookie 或 API Key；凭据仍只存在于 sidecar/session 运行边界。
真实平台内容仍必须标记 not_product_fact，不能直接写入 Product Brain；后续只能通过人工确认后的 proposal/playbook 进入长期认知。
小红书自动浏览器 Cookie 刷新失败但已有有效条目时，状态归类应为 completed_partial 或 completed，不应误报为完全 blocked。
```

LLM 深度灵感总结测试结果：

```text
status: passed
llm_provider: deepseek
llm_model: deepseek-v4-pro

xhs_command: .\.hermes\plugins\product_creative\scripts\product_creative.ps1 llm-inspiration-pack --id m6-sidecar-live-test --snapshot source-snapshot-20260708-170931 --target xiaohongshu-seeding-note --channel xiaohongshu --max-items 2
xhs_llm_pack_id: llm-inspiration-pack-20260708-174559
xhs_status: review_required

douyin_command: .\.hermes\plugins\product_creative\scripts\product_creative.ps1 llm-inspiration-pack --id m6-sidecar-live-test --snapshot source-snapshot-20260708-170008 --target douyin-short-video-script --channel douyin --max-items 2
douyin_llm_pack_id: llm-inspiration-pack-20260708-174714
douyin_status: review_required

confirmation_guard: inspiration-library-confirm without --confirmed returns review_required and does not write artifacts/inspiration_library.
content_boundary: LLM pack is saved as not_product_fact and mutates_product_brain=false.
```

LLM 深度总结结论：

```text
LLM 总结比规则抽取更适合提炼渠道表达、内容结构、视觉/分镜方向和可复用 prompt addition。
规则抽取仍可作为低成本 fallback；默认产品体验应优先走 LLM 总结，再经用户确认沉淀。
测试产品 m6-sidecar-live-test 不是蜂蜜饮品，LLM 正确识别为 format_only / low-fit，因此本次只验证链路与总结质量，不代表真实产品最终效果。
后续真实产品测试必须使用真实 Product Brain，否则模型会把外部灵感错误桥接到测试产品名。
```

M6.11-M6.15 收口结果：

```text
M6.11 LLM Inspiration Formalization：
- llm-inspiration-pack 固定为 review_required。
- artifact 明确记录 summary_type、status_reason、review_contract。
- llm.call_mode 记录 structured_json_mode 或 text_json_fallback。
- 规则抽取仍保留为 fallback，不作为默认优先体验。

M6.12 Channel Selection and Dedup：
- inspiration-pack 会从 target 推导 target_channel。
- xiaohongshu-seeding-note 优先选择 xiaohongshu 候选。
- douyin-short-video-script 优先选择 douyin 候选。
- 不足时才补 secondary_reference，并写入 selection_warnings。
- 候选按 normalized hook/angle/title 去重，避免同一灵感重复进入 brief context。

M6.13 Real Product Validation：
- 新增 verify_m6_13_real_product_inspiration.ps1。
- 默认用真实产品 workspace（周十五蜂蜜露测试 workspace）验证 Product Brain -> source snapshot -> candidates/pack -> context。
- 产品样例只存在于验证脚本参数和测试 workspace，不进入核心代码。
- 可用 -RunLive 接平台 sidecar；可用 -RunLlm 接 Hermes DeepSeek 做真实 LLM 总结。

M6.14 Inspiration Library Confirmation：
- 新增 verify_m6_14_inspiration_library_confirm.ps1。
- 未带 -Confirmed 时，inspiration-library-confirm 只返回 review_required，不写 artifacts/inspiration_library。
- 带 -Confirmed 后写入 active inspiration_library entry。
- 后续 generate 会从 material_context.inspiration_context.source=inspiration_library 读取已确认灵感。

M6.15 Hermes Chat Validation：
- 新增 verify_m6_15_hermes_chat_inspiration.ps1。
- 默认验证 conversation-adapter 和 Hermes chat 命令入口。
- -RunChat 已验证可从 Hermes CLI chat 入口触发 product_llm_inspiration_pack。
- chat 生成后停在 review_required，不自动沉淀灵感库。
```

M6.11-M6.15 验证记录：

```text
syntax_check: passed
python_compile: inspiration.py, workflow.py, cli.py
powershell_parse: verify_m6_11_12, verify_m6_13, verify_m6_14, verify_m6_15

verify_m6_11_12_offline: passed
script: .hermes/plugins/product_creative/scripts/verify_m6_11_12_llm_inspiration_selection.ps1
xhs_pack_channel: xiaohongshu
douyin_pack_channel: douyin
external_call_performed: false

verify_m6_11_real_llm: passed
script: .hermes/plugins/product_creative/scripts/verify_m6_11_12_llm_inspiration_selection.ps1 -RunLlm
llm_pack_id: llm-inspiration-pack-20260709-101157
llm_called: true
external_call_performed: false

verify_m6_13_real_product_workspace: passed
script: .hermes/plugins/product_creative/scripts/verify_m6_13_real_product_inspiration.ps1
product_id: zhou15-honeydew-m6-real-test
snapshots: source-snapshot-20260709-100758, source-snapshot-20260709-100759
external_call_performed: false

verify_m6_14_guard: passed
script: .hermes/plugins/product_creative/scripts/verify_m6_14_inspiration_library_confirm.ps1 -CreateFixture
guard_status: review_required
library_write_without_confirmation: false

verify_m6_14_confirmed_context: passed
script: .hermes/plugins/product_creative/scripts/verify_m6_14_inspiration_library_confirm.ps1 -CreateFixture -Confirmed -GenerateAfterConfirm
entry_id: inspiration-library-entry-20260709-100845
generated_artifact_id: xiaohongshu-note-20260709-100914
generation_used_inspiration_library: true

verify_m6_15_adapter: passed
script: .hermes/plugins/product_creative/scripts/verify_m6_15_hermes_chat_inspiration.ps1
inferred_llm_action: create_llm_inspiration_pack
inferred_confirm_action: confirm_inspiration_library_entry

verify_m6_15_chat: passed
script: .hermes/plugins/product_creative/scripts/verify_m6_15_hermes_chat_inspiration.ps1 -RunChat -MaxTurns 6
chat_session_id: 20260709_101320_338235
chat_llm_pack_id: llm-inspiration-pack-20260709-101440
chat_exit_code: 0
```

M6 收口边界：

```text
M6 完成的是“外部灵感进入 Hermes 中枢”的基础闭环。
闭环停止点是 review_required 或 explicit confirmed library entry。
M6 不负责自动判断某个灵感长期有效，不负责偏好升级，也不直接更新 Product Brain。
进入 M7 前，应把重点转向：用户反馈、版本对比、成功模式识别、proposal 生成与人工确认后的自迭代更新。
```

---

## 16. 防偏检查

M6 每个小版本完成后必须回答：

```text
它是否让 Hermes 更懂当前产品，而不是只新增工具？
它是否减少用户把素材用于外部模型的理解负担？
它是否把外部资料变成灵感候选，而不是产品事实？
它是否把小红书/抖音能力接回 Product Brain -> Brief -> Artifact -> Feedback -> Proposal 闭环？
它是否通过 Hermes workflow / 对话入口可触发？
它是否避免 Cookie、API Key、外部 raw 数据污染产品知识库？
它是否为文案、图片、视频三个方向共同服务？
```

如果答案不能成立，该功能不进入 M6。
