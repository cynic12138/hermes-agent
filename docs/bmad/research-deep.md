# Deep Research: M9/M9.1 Evidence Synthesis

- 日期：2026-07-12
- 方法：repository archaeology、Git diff、接口/数据/测试/UX 交叉验证

## 研究问题

1. M9.1 是新增功能还是架构迁移？
2. 迁移是否已完整接通？
3. 哪些“完成”仅是 mock/契约闭环？

## 结论

- **CONFIRMED** M9.1 是将 Product Creative 固定 Desktop 页面替换为通用 Desktop Plugin SDK + plugin-owned bundle 的横切迁移。
- **PARTIAL** 新宿主 API、bundle validator、registry/page、plugin UI、tests、release workflow 均存在，但大量未跟踪，完整 build/E2E 未证实。
- **CONFIRMED** `/api/desktop/plugins` 排除 project source，开发链必须验证导出/安装为 enabled user plugin。
- **CONFIRMED** durable data/API/recovery 闭环已实现；真实 provider/sidecar、ffmpeg、LLM 是条件能力，不能写成默认 production-ready。
- **CONFLICTED** README 工作区口径、HEAD 固定页面、旧 M4 Desktop 文档、旧 JSON runtime 文档属于四个时代。

## 风险排序

1. 未跟踪替代文件丢失或不完整提交。
2. 版本 `9.0.0` → `0.9.0-alpha.1` 升级语义。
3. 缺完整 Desktop/user-plugin E2E。
4. workspace header、absolute path descriptor、UI a11y/error handling。
5. 脚本式测试无统一 coverage。

## 建议

以 M9.1 收口为唯一工程衔接点；产品和 NFR 决策进入 product-brief/PRD 访谈，不从代码反推为已批准要求。

---

# Deep Research Addendum: 周十五蜂蜜露资料基座

- 日期：2026-07-14
- intent：`bmad:research-deep`
- 方法：官方店铺、设计案例、普通零售页、第三方目录、官方登记入口、仓库测试夹具和用户确认交叉验证
- 完整资料：`docs/product-bases/zhou-shiwu-honeydew/`

## 研究结论

- **CONFIRMED** “周十五蜂蜜露”作为首条真实产品验证线；当前交付重点为真实图片和 9:16、约 15 秒、每轮 3 版的短视频。
- **CONFIRMED** 包装、Logo、管体和包装文字保持原样，AI 只生成背景、场景、人物、装饰与剧情。
- **INFERRED** 多个相互独立的公开商品页把产品描述为外用蜂蜜露，但缺当前实物包装和正式说明书，不能升级为 Canonical Product Brain。
- **CONFLICTED** 仓库历史测试把该产品写成“清爽蜂蜜/果蜜饮品、夏季/办公室补水”，有污染真实产品认知的风险。
- **UNKNOWN** 最新包装、完整 SKU、成分、适用人群、品牌/生产主体、许可/备案/专利状态及可合法使用的功效宣称。
- **CONFIRMED** 来源采用字段级优先级；公开网页和社交平台只能先进入 evidence/inspiration/proposal，高影响 Product Brain 写入继续需要人工审批。
- **CONFIRMED** Product Brain 应支持从空白开始，由 Hermes 在自然语言对话中主动发现缺口、索要资料、复述理解并逐字段提案；本轮网络资料仅为 Evidence Inbox 研究快照。
- **PARTIAL** 当前代码有空白 Wiki、conversation adapter、通用 missing input 和写回门禁，但未证明真实自由对话的主动产品访谈已完成。

## 本轮边界

本轮只建立知识基座和冲突记录，不修改测试脚本、业务代码、数据库、接口或模型配置，也未调用付费生成模型。
