# Frontend Recovery

## 信息架构

HEAD M9 与工作区 M9.1 均提供五区：Overview、Tasks、Review queue、Assets、Learning；顶栏含产品选择、刷新和“在聊天中继续”。

- HEAD：`apps/desktop/src/app/product-creative/index.tsx` 固定 React 页面。
- 工作区：`.hermes/plugins/product_creative/desktop_ui/index.js` 插件 bundle + `apps/desktop/src/app/desktop-plugins/` 通用宿主。

## 已接通流程

- workspace → product 列表 → snapshot/workflows/review/assets/learning。
- workflow detail、retry/cancel/provider refresh。
- proposal accept/reject、Brain rollback、rule revoke，均有两阶段确认。
- 选择产品按 workspace 保存在 localStorage。
- 工作区新增 thumbnail/preview；有活动 workflow 时加快轮询。

控制台没有写死业务假数据，但可能显示后端 mock provider 记录。

## 未接通/边界

- 无产品创建、摄入、上传或启动新生成 UI；当前必须回到 Hermes chat。
- M10 guided launch 是 PLANNED。
- M9.1 project plugin 会被 Desktop plugin 列表过滤，需 user-plugin 安装验证。

## 体验断点

- 首次 API 失败被误显示成“无产品”。
- mutation 无 loading/防重复提交/明确成功反馈。
- M9.1 workflow detail 退化为 raw JSON。
- M9.1 原生 DOM dialog/tabs 缺焦点管理、ARIA、Escape、键盘切换，弱于 HEAD Radix UI。
- i18n 不完整；多个主要标签硬编码英文。
- bundle 加载失败可能只表现为入口消失。

## 重复/取舍

M9.1 为独立分发重新实现 Button/Empty/Status/Tabs/Dialog/CSS，与宿主组件重复。这是插件边界的代价，但带来可访问性、视觉一致性和主题兼容风险。
