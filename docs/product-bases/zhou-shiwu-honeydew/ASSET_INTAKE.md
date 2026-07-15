# 正式资料与素材入库清单

## 需要优先补齐的资料

### P0：开始真实生成前必须有

- 当前要验证的具体 SKU 名称和规格。
- 当前在售包装正面、背面、两侧、顶部/底部和单支管体高清照片。
- 官方透明底商品 PNG 或可用于抠图的原始摄影图。
- 包装/说明书完整文字。
- 用户确认“这是当前最新/本次采用版本”的记录。
- 允许用于内部 AI 生成的素材授权确认。

### P1：允许形成正式 Product Brain 前必须有

- 公司产品说明/培训资料及版本号。
- 成分、使用方法、适用和禁用人群的正式口径。
- 品牌/运营主体、生产主体和授权关系。
- 当前有效的许可、备案、检测或专利资料（如需宣传）。
- 品牌视觉规范、禁用词和渠道发布审核规则。

### P2：质量迭代使用

- 历史高质量商品图和短视频源文件。
- 运营人员喜欢/不喜欢的案例及原因。
- 已确认的场景、人群、道具和视觉风格偏好。
- 后续小红书/抖音抓取 sidecar 的样本和可用范围。

## 建议目录

正式资料不应和公开网页下载物混放：

```text
products/zhou-shiwu-honeydew/
  raw/product-inputs/company-approved/
  raw/product-images/current-packaging/
  raw/product-inputs/instructions/
  raw/product-inputs/compliance/
  raw/hot-topic-snapshots/
  raw/competitor-content/
  assets/images/product-source/
```

本恢复目录只存知识索引，不复制第三方图片。正式素材应通过 Product Creative 的 asset ingest 进入产品工作区，并记录 hash、来源、版本和审核状态。

## 推荐命名

```text
20260714_<sku>_package_front_v1.png
20260714_<sku>_package_back_v1.png
20260714_<sku>_tube_front_v1.png
20260714_<sku>_tube_back_v1.png
20260714_<sku>_instructions_v1.pdf
20260714_<sku>_official_cutout_v1.png
```

不要在文件名中写入手机号、身份证号、订单号、Cookie、Token 或其他敏感信息。
