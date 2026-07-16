# M10.1 Live Provider 与灵感数据源接入基线

> 日期：2026-07-16
> 状态：`LIVE_TECHNICAL_DONE / CREATIVE_QUALITY_REJECTED`
> 原始验收分支：`product-creative-runtime`；当前重建分支：`product-creative-rebaseline-20260716`
> 源码真源：`.hermes/plugins/product_creative/`

2026-07-16 用户审阅结论：exact-main 样片只有固定主图、通用字幕和装饰，不构成有效剧情；普通 Seedance 样片包装小字发生生成式乱码。本文证明外部技术链路，不证明产品创作质量完成。后续方向见 `docs/PRODUCT_AGENT_DIRECTION.md`。

## 1. 本阶段解决什么

本阶段不新建抓取器或 Provider，而是把已有能力接入 M10 Creative Task：

```text
Hermes 自然语言任务
→ Product Creative 任务授权
→ Web / XHS / Douyin 灵感研究
→ 外部结果保存为 not_product_fact
→ 素材与创意编排
→ 豆包图片理解 / 图片生成 / 异步视频生成
→ 可恢复轮询与交付
```

外部来源只能进入 Evidence Inbox、Inspiration 或 Proposal；不得直接修改 Canonical Product Brain。

## 2. Provider 固定配置

不得在仓库中保存 API Key 值，只保存环境变量名称、端点和模型。

### 2.1 密钥解析

豆包/火山方舟统一按以下顺序解析：

1. `DOUBAO_API_KEY`（最高优先级）；
2. `PRODUCT_CREATIVE_ARK_API_KEY`（旧版兼容）；
3. `ARK_API_KEY`（旧版兼容）。

Windows 下先读取当前进程，再读取当前用户环境变量，最后读取机器级环境变量。新启动的 Hermes/sidecar 通常会直接继承机器级变量；已有进程需要重启。

抖音 sidecar 的其他密钥：

- SiliconFlow 转录：`SILICONFLOW_API_KEY`，旧兼容 `API_KEY`；
- DeepSeek 文字钩子/口播拆解：`DEEPSEEK_API_KEY`；
- 前 5 秒多模态分析：`DOUBAO_API_KEY`，旧兼容 `ARK_API_KEY`。

### 2.2 豆包多模态理解

- Provider：`volcengine-ark-vlm`
- Endpoint：`https://ark.cn-beijing.volces.com/api/v3/responses`
- Model：`doubao-seed-2-1-pro-260628`
- 用途：产品图片理解、包装可见内容候选、抖音前 5 秒画面钩子分析。
- 约束：不可把模糊 OCR、功效、人群或包装推断写成产品事实。

### 2.3 豆包视频生成

- Provider：`volcengine-ark-video`
- Submit：`https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks`
- Status：`https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/{task_id}`
- Model：`doubao-seedance-2-0-260128`
- 默认：`9:16`、10 秒、生成音频、无水印；最终任务规格由 Creative Task 决定。
- 行为：异步提交，保存远端 task ID，之后轮询并导入结果；状态查询不得重复消耗生成次数。
- 真实调用上限：单次任务图片 5 次、视频 5 次；费用不作为当前硬上限，但仍须记录调用次数。

### 2.4 豆包图片生成

- Provider：`volcengine-ark-image`
- 密钥：只读取 `DOUBAO_API_KEY` 等已记录兼容变量，不保存值。
- 当前 Live 结论：真实提交、下载和 workspace 导入已通过；产物带 Provider 的“AI生成”水印，因此可证明调用链和交付链，不作为无水印商业终稿。
- 包装保真：普通生成模型不能证明逐像素保持包装。要求“包装不得重绘/保持原始像素”时，Goal Planner 必须改走已有 exact-main compositor，而不是把生成式产品重绘冒充保真。

## 3. 三类灵感来源的职责

### 3.1 通用 Web

用于官方页面、节日/新闻/热点、公开事实、梗的时间背景和可核验来源。优先复用 Hermes `web_search` / `web_extract`，清洗后导入 external source snapshot。它不负责证明未核验的产品功效。

### 3.2 小红书

外部项目：`C:\data\work file\小红书数据自动抓取系统`。

用于发现消费者语言、场景、痛点/顾虑、标题与评论表达、审美和图片/视频创意线索；本项目不把“小红书文案”作为最终交付物。

接入方式：本地 sidecar，默认 `http://127.0.0.1:8787/api`：

- `GET /health`
- `POST /auth/browser`
- `POST /search-jobs`
- `GET /search-jobs/{id}`
- `GET /notes?jobId=...`
- `GET /analytics/{jobId}`

底层 Express 实际挂载 `/api`，当前 Product Creative adapter 路径一致。真实调用仍依赖服务启动、浏览器登录/Cookie、平台风控和限流；2026-07-16 已完成一次 Live 验收，但不能据此保证未来账号权限和平台风控始终可用。

### 3.3 抖音

外部项目：`C:\data\work file\抖音爆款视频抓取`。

用于发现爆款视频结构、前 3–5 秒视觉钩子、口播文字钩子、节奏、镜头、转场和可复用剧情模式。它不是产品事实来源。

接入方式：本地 FastAPI sidecar，默认 `http://127.0.0.1:8000`：

- `GET /api/health`
- `POST /api/search`
- `POST /api/video/transcribe-online`
- `POST /api/video/analyze-first5`

Product Creative 当前处理：

1. 搜索候选视频；
2. 对授权数量内的视频下载并使用 SiliconFlow 转录；
3. 使用 DeepSeek 拆解开场文字钩子、痛点、卖点、信任和 CTA；失败时降级本地规则并标记来源；
4. 使用豆包多模态分析前 5 秒画面；原生视频输入失败时，sidecar 可降级为逐秒抽帧 + 可选 ASR；
5. 只保存清洗后的灵感字段，临时视频分析目录由 sidecar 清理。

`transcribe_limit` 和 `analyze_first5_limit` 均允许 0–5。某一项失败只记录单项错误，不应抹掉其他可用视频或使 Product Brain 发生变化。

## 4. 运行环境分工

- 仓库 Hermes：源码开发、离线单测、适配器契约和分发验证的事实来源。
- 已安装 Hermes `0.18.2`：最终真实自然语言验收入口；已配置的 DeepSeek 对话模型由该运行时使用。
- Desktop：查看 Tasks/Review/Assets/Learning 和恢复；不作为第二套业务编排器。
- XHS/Douyin sidecar：独立本地进程和本地登录状态；Product Creative 只调用其受控 HTTP API。

仓库代码通过后，必须将当前插件以 enabled user plugin 方式安装到已安装 Hermes，再从真实自然语言输入验收。不能只用 Python 函数或 PowerShell 参数脚本替代。

## 5. 2026-07-15 Live 验收记录

本节区分“真实调用成功”“产物仅供审计”“尚被外部条件阻塞”。任何 ID 都是本地审计标识，不包含密钥、Cookie 或带签名下载 URL。

### 5.1 真实 Hermes 与产品摄入

- 用户入口：本机已安装 Hermes `0.18.2`，不是用底层 Python 函数替代；插件目录通过 junction 指向本仓库源码真源。
- 会话：`20260715_153658_1659aa`。
- 产品 workspace：`.hermes/product_creative/products/zhoushiwu`。
- 当前主图素材：`material-20260715-153738-fd6735a1`，已登记为 `current_main_image`。
- 已确认 Canonical Brain 仅保存经确认的低风险事实和禁用表述；外部研究没有直接写回 Brain。两个早期格式异常 proposal 保留为待审计记录，没有静默删除。

### 5.2 真实多模态图片理解

- Provider/model：`volcengine-ark-vlm` / `doubao-seed-2-1-pro-260628`。
- Analysis：`image-analysis-20260715-171314-fd6735a1`，耗时约 103.8 秒，13 个结构化字段，confidence `0.98`。
- Alignment：`visual-align-20260715-171404-fd6735a1`。
- 结论：真实远端响应、结构化解析和素材对齐通过；结果停留在 evidence/draft，没有自动修改 Canonical Brain。

### 5.3 真实 Web、抖音与小红书

- Web：`source-snapshot-20260715-170017` 为真实在线抓取；另有人工整理的可追溯 snapshot `source-snapshot-20260715-164716`。抓取页面是动态 Next.js HTML，文本质量有限，但联网与 snapshot 链路真实成立。
- Douyin：`source-snapshot-20260715-162114` 包含 3 个真实候选视频；SiliconFlow 转录与 DeepSeek 钩子分析成功。修复 sidecar 的长耗时限制后，豆包前 5 秒多模态分析真实成功，随后保存为 `source-snapshot-20260715-164309`。单次前 5 秒分析约 847.9 秒，说明该能力必须按异步长任务对待。
- XHS 首次验收：8787 sidecar 健康、Cookie 已配置、`/api/auth/verify` 成功，但旧账号的真实单页任务 `job_mrlx20rp_3039gi` 被平台返回 `-104 您当前登录的账号没有权限访问`。
- XHS 复验（2026-07-16）：用户在项目专用 Edge 隔离配置中登录并手动确认搜索页可用；重新捕获 Cookie 后，`job_mrmuvr0j_irzs8j` 成功播种 20 条真实候选，没有 `-104`、network error 或 breaker。
- 安装版 Hermes 自然语言 E2E：用户输入语义为“为周十五益生菌蜂蜜露从小红书真实搜索‘便秘好物’，最多 3 条，只作消费者语言/场景灵感，不修改 Brain、不生成媒体”。Hermes 经 Product Creative 创建 `job_mrmv97i7_mb1901`，落盘 `source-snapshot-20260716-100618`，保存 3 条真实笔记并生成 3 个 inspiration candidates。
- 独立核验：snapshot `status=completed`、`provider=xiaohongshu-sidecar`、`external_collection_performed=true`、3/3 item 均为 `not_product_fact=true`、`mutates_product_brain=false`。Canonical `structured/product_state.json` 最后更新时间仍为 2026-07-15 16:58:34（SHA-256 `7CB1D4DB97B8574848FD6D83CAE992E563EE8CF4C4565AB8683D060B19A71F85`），本次只更新 Wiki 索引/日志，没有写产品事实。
- 为避免继续消耗平台读取，两个 job 在取得证据后被显式停止：第一条 13 done / 87 pending，Hermes E2E 4 done / 96 pending；均为 `paused / 用户手动停止`。snapshot 已保存，不受停止影响。
- 第一次安装版 Hermes E2E 因沙箱拒绝写入用户级 `logs/.__agent.lock` 而 300 秒超时，未创建 job/snapshot；以获准权限原样重跑后 156.8 秒成功。该失败是本地权限，不是 XHS 网络问题。
- Hermes 进一步尝试 LLM 深度摘要包时暴露 `ctx.llm` 桥接限制；原始 snapshot 和规则候选完整保存。该限制不影响 XHS 数据源与 Product Brain 隔离验收，但影响“深度 LLM 灵感包”体验。

### 5.4 真实图片生成

- Creative Task：`task-ad015ab8e7354118877ed4d9d32b2a5d`。
- Provider task：`provider-task-b4c7a0169bea46bb9097157d7922df51`。
- Result：`image-result-20260715-173453`。
- 文件：`.hermes/product_creative/products/zhoushiwu/artifacts/generated_images/image-output-20260715-173453.jpg`。
- 结论：授权 → Provider → 下载 → artifact → review/recovery 真实通过；输出是安全的背景/场景图，但带 Provider 水印，只作为 Live 链路验收产物。

### 5.5 真实 Seedance 视频与包装保真判定

- Creative Task：`task-339731944a1e42b79cb8a7865643e11c`。
- Local/remote task：`video-task-20260715-172533` / `cgt-20260715172533-pkkjs`。
- Result：`video-result-20260715-174019`。
- 文件：`.hermes/product_creative/products/zhoushiwu/artifacts/generated_videos/video-output-20260715-174019.mp4`。
- 元数据：Seedance 2.0、10 秒、720p、9:16、24fps、带音频；SHA-256 `785D981C0FD17D2CF35ECC4D5E5C53FDDA2889217FB4E4CAA624BDC90C8174B4`。
- 判定：真实异步提交、长轮询、下载、导入、恢复和交付通过；模型重绘了产品包装，因此不满足“原始包装逐像素不变”。该视频是 Provider 链路审计样本，不是包装保真终稿。
- 更早的 `task-86ae59...` 使用了不安全的使用/食饮式模板，永久只保留审计，不得作为交付样本。对应模板已改为中性展示并增加回归测试。

### 5.6 exact-main 安全视频路线

- 统一 Creative Task：`task-99ae5975bb374579aacf529dcdd27827`。
- Result：`video-result-20260715-175851`；Review：`result-review-package-20260715-175931`。
- 文件：`.hermes/product_creative/products/zhoushiwu/artifacts/generated_videos/exact-main-video-20260715-175851/video-output-20260715-175924-exact-main-anime_story.mp4`。
- 计划阶段 `prepare_task_material_pack → compose_exact_main_video → create_task_overview_package → review_generated_result` 均产生 durable 结果，任务进入 `AWAITING_FEEDBACK`，没有 Provider 授权和付费调用。
- 判定：主图作为完整固定画面卡片，只做整体缩放/位移；背景、角色、字幕位于其外部，满足当前开发验收中的“不重绘包装”。视觉质量仍是基础样片，不等同于商业成片。
- 当前 composer 依赖本机外部 ffmpeg（本次使用影刀自带二进制）；插件尚未提供独立 ffmpeg 发现/安装机制，这是可复现性限制。

### 5.7 安全与恢复修复

- 远端视频结果 URL 只在下载时短暂使用完整签名；持久化 provider 响应和返回描述符会移除 query/fragment，防止凭据进入 workspace、日志和文档。
- exact-packaging 同义表达（“不得重绘”“原始像素”“逐帧保持”等）会触发已有 exact-main 路线。
- 已扣费/已提交步骤完成后，失败在 review/delivery 的任务可以离线恢复，禁止重复提交 Provider。
- 任务因旧计划请求 Provider 授权而阻塞后，用户追加更严格包装保真要求时可以重规划到无 Provider 的 exact-main 路线，无需批准旧授权。

## 6. 验证矩阵

- M10 Python：35 passed。
- Live adapter：10 passed。
- Douyin 多模态：12 passed（1 个 Starlette `TestClient` deprecation warning）。
- M9 review/recovery：25/25。
- Public surface：84 tools / 84 CLI，golden hash `06050b3...` 匹配。
- Desktop bundle：2 passed；相关 routes/registry/page/Product Creative UI：17 passed；TypeScript typecheck 与 production build passed。build 只出现 dirty stamp、既有 CSS token 和大 chunk warning。
- XHS sidecar：18 files / 106 tests passed，TypeScript client/server typecheck passed。首次 Vitest 因沙箱拒绝写 `node_modules/.vite-temp` 未启动；以获准权限原样重跑后 exit 0。
- `git diff --check`：exit 0，仅报告 Windows LF→CRLF 提示。
- 可发布源码/文档敏感扫描：0 hits。保留的未跟踪 `pytest-of-unknown/` 测试分发副本有 2 个假凭据 fixture 命中，不属于源码真源或发布内容，未删除。
- 媒体重新核验：图片 211,207 bytes / SHA-256 `DE572ACEA4B6520A55E3754B20A8748F0A093921062D7F1359DAC467533DE8B9`；Seedance 视频 3,559,910 bytes / SHA-256 `785D...B4`；exact-main 视频 2,761,851 bytes / SHA-256 `F47F...FE6F`。
- 真实 VLM、图片、Seedance 视频、Web、Douyin 均有远端/平台结果证据。
- XHS 真实登录、搜索、Product Creative snapshot、候选生成和 Brain 隔离已通过；旧账号 `-104` 记录保留为恢复审计，不再是当前阻塞。

文档交叉引用检查的 9 个必读文件全部存在。XHS 成功后的最终门禁已重新执行；技术 Live 门禁与用户产品验收必须分开标记。

## 7. 当前限制与剩余验收

1. **用户验收**：需要用户亲自查看一次 Product Brain 认知流程、真实图片、真实 Seedance 审计样本和 exact-main 安全样片，并给出接受/修改意见。
2. **LLM inspiration bridge**：自然语言 XHS E2E 的 snapshot 与规则候选通过，但 `ctx.llm` 不可用导致深度摘要包未生成；若后续体验要求自动深度归纳，应作为窄范围修复，不重建灵感系统。
3. **包装与合规资料**：背标、说明书、公司批准可用/禁用宣称仍不完整；在确认前继续禁止功效、孕妇适用、治疗、安全保证等高风险表述。
4. **可复现视频工具链**：exact-main composer 的 ffmpeg 发现/配置尚未产品化；不影响本机样片证据，但影响其他机器直接安装运行。

M10.1 技术 Live 要求已经覆盖真实 Provider、图片、视频、Web、XHS 和 Douyin，最终离线门禁也已通过；M10 总里程碑仍须用户完成两项核心验收后才能标记 DONE。
