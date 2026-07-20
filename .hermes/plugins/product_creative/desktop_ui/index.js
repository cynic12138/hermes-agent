(function () {
  'use strict'

  const API = '/api/plugins/product_creative/v1'
  const copy = {
    en: { overview: 'Overview', tasks: 'Tasks', review: 'Review queue', assets: 'Assets', learning: 'Learning', settings: 'Settings', continueChat: 'Continue in chat', refresh: 'Refresh', noWorkspace: 'Open a workspace to use Product Creative.', noProducts: 'No Product Creative products in this workspace.', reason: 'Reason for this action', reasonRequired: 'A reason is required before confirmation.', confirm: 'Confirm', close: 'Close', accept: 'Accept', reject: 'Reject', rollback: 'Rollback', revoke: 'Revoke', retry: 'Retry', cancel: 'Cancel', providerRefresh: 'Refresh provider task', unavailable: 'Media unavailable', onboardingTitle: 'Build your first product understanding', productName: 'Product name', productId: 'Product ID (optional)', productDescription: 'Existing product description (optional)', createProduct: 'Create product', creatingProduct: 'Creating product…', onboardingHelp: 'Descriptions enter Evidence and Draft Understanding first. They do not become confirmed Product Brain facts.', addMaterial: 'Add product material or main image in chat', goalLabel: 'What do you want to create?', startTask: 'Start creative task', taskVideo: 'Today product video', taskImage: 'Product image', taskLearn: 'Help Hermes understand this product', continueTask: 'Continue task', productTruth: 'Product truth', creativeDirection: 'Creative direction', finalQuality: 'Final quality', credentials: 'Provider and model credentials', mediaRuntime: 'Media runtime', optionalSources: 'Optional inspiration sources', diagnosticsRefresh: 'Refresh diagnostics', openSettings: 'Open Hermes settings' },
    zh: { overview: '概览', tasks: '任务', review: '审阅队列', assets: '素材与结果', learning: '学习', settings: '设置', continueChat: '在聊天中继续', refresh: '刷新', noWorkspace: '请先打开一个工作区。', noProducts: '当前工作区没有 Product Creative 产品。', reason: '填写本次操作原因', reasonRequired: '确认前必须填写操作原因。', confirm: '确认', close: '取消', accept: '接受', reject: '拒绝', rollback: '回滚', revoke: '撤销规则', retry: '重试', cancel: '取消工作流', providerRefresh: '刷新 Provider 任务', unavailable: '媒体不可用', onboardingTitle: '建立第一个产品认知', productName: '产品名称', productId: '产品 ID（可选）', productDescription: '已有产品描述（可选）', createProduct: '创建产品', creatingProduct: '正在创建产品…', onboardingHelp: '描述只会先进入证据箱和待确认理解，不会自动成为 Product Brain 已确认事实。', addMaterial: '在聊天中补充产品资料或主图', goalLabel: '你希望这次创作什么？', startTask: '开始创作任务', taskVideo: '制作今日产品视频', taskImage: '制作产品图片', taskLearn: '让 Hermes 继续了解产品', continueTask: '继续任务', productTruth: '产品事实', creativeDirection: '创意方向', finalQuality: '成片质量', credentials: '模型与 Provider 凭据', mediaRuntime: '媒体运行环境', optionalSources: '可选灵感来源', diagnosticsRefresh: '刷新诊断', openSettings: '打开 Hermes 设置' },
    'zh-hant': { overview: '概覽', tasks: '任務', review: '審閱佇列', assets: '素材與結果', learning: '學習', continueChat: '在聊天中繼續', refresh: '重新整理', noWorkspace: '請先開啟一個工作區。', noProducts: '目前工作區沒有 Product Creative 產品。', reason: '填寫本次操作原因', reasonRequired: '確認前必須填寫操作原因。', confirm: '確認', close: '取消', accept: '接受', reject: '拒絕', rollback: '回復', revoke: '撤銷規則', retry: '重試', cancel: '取消工作流程', providerRefresh: '重新整理 Provider 任務', unavailable: '媒體無法使用' },
    ja: { overview: '概要', tasks: 'タスク', review: 'レビュー', assets: 'アセット', learning: '学習', continueChat: 'チャットで続ける', refresh: '更新', noWorkspace: 'ワークスペースを開いてください。', noProducts: 'このワークスペースに製品がありません。', reason: '操作理由', reasonRequired: '確認する前に操作理由を入力してください。', confirm: '確認', close: 'キャンセル', accept: '承認', reject: '却下', rollback: 'ロールバック', revoke: 'ルール取消', retry: '再試行', cancel: '取消', providerRefresh: 'Provider タスク更新', unavailable: 'メディアを利用できません' }
  }

  const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char])
  const idOf = (item, ...keys) => keys.map(key => item?.[key]).find(Boolean) || ''
  const status = value => `<span class="pc-status">${escape(value || 'unknown')}</span>`
  const rows = (items, render) => items?.length ? `<div class="pc-rows">${items.map(render).join('')}</div>` : '<div class="pc-empty">No records</div>'

  function mount(root, host) {
    const requestedLocale = String(host.locale || '').toLowerCase()
    const locale = Object.prototype.hasOwnProperty.call(copy, host.locale) ? host.locale : requestedLocale.startsWith('zh') ? 'zh' : 'en'
    const c = { ...copy.en, ...copy[locale] }
    const state = { tab: 'overview', product: '', products: [], snapshot: null, workflows: [], workflow: null, creativeTasks: [], creativeTask: null, review: null, assets: null, learning: null, diagnostics: null, error: '', loading: true, confirmation: null, stopped: false, goal: '', onboarding: { name: '', productId: '', description: '', submitting: false } }
    let timer = 0

    root.innerHTML = `<style>
      [data-pc-root]{height:100%;display:flex;flex-direction:column;min-height:0;background:var(--ui-bg-primary,#111);color:var(--foreground,#eee);font:13px system-ui,sans-serif}
      .pc-head,.pc-tabs{display:flex;align-items:center;gap:8px;padding:9px 16px;border-bottom:1px solid var(--ui-stroke-secondary,#333)}
      .pc-head h1{font-size:14px;margin:0 8px 0 0}.pc-head select{min-width:190px}.pc-head .pc-spacer{flex:1}.pc-btn,select,input,textarea{border:1px solid var(--ui-stroke-secondary,#444);background:var(--ui-bg-secondary,#222);color:inherit;padding:7px 9px;border-radius:4px}.pc-btn{cursor:pointer}.pc-btn:hover{background:var(--ui-control-hover-background,#333)}.pc-primary{background:var(--button-primary-background,#2563eb);color:white}.pc-primary:disabled{cursor:not-allowed;opacity:.6}
      .pc-tabs button{border:0;border-bottom:2px solid transparent;background:none;color:var(--ui-text-secondary,#aaa);padding:7px 2px;cursor:pointer}.pc-tabs button[aria-selected=true]{border-color:var(--focus-border,#4f8cff);color:inherit}.pc-count{font-size:10px;margin-left:4px;color:var(--ui-text-tertiary,#888)}
      .pc-main{min-height:0;flex:1;overflow:auto;padding:14px 16px}.pc-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}.pc-split{display:grid;grid-template-columns:minmax(260px,.8fr) minmax(360px,1.2fr);gap:16px}.pc-section h2{font-size:11px;text-transform:uppercase;color:var(--ui-text-tertiary,#888);margin:0 0 8px}.pc-metric{font-size:22px;font-weight:600}.pc-muted{color:var(--ui-text-tertiary,#888);font-size:11px}.pc-rows{border-block:1px solid var(--ui-stroke-secondary,#333)}.pc-row{display:flex;align-items:center;gap:10px;padding:9px 4px;border-bottom:1px solid var(--ui-stroke-secondary,#333)}.pc-row:last-child{border:0}.pc-grow{flex:1;min-width:0}.pc-title{font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.pc-status{text-transform:uppercase;font-size:10px;color:var(--ui-text-tertiary,#888)}.pc-empty{min-height:130px;display:grid;place-items:center;color:var(--ui-text-tertiary,#888);border-block:1px solid var(--ui-stroke-secondary,#333)}
      .pc-error{padding:8px 16px;background:#7f1d1d55;color:#fecaca}.pc-json{white-space:pre-wrap;word-break:break-word;font:11px ui-monospace,monospace}.pc-media{width:64px;height:48px;object-fit:cover;background:#222}.pc-actions{display:flex;gap:5px;flex-wrap:wrap}.pc-dialog{position:fixed;inset:0;display:grid;place-items:center;background:#0008;z-index:100}.pc-dialog>div{width:min(440px,calc(100vw - 32px));background:var(--ui-bg-primary,#171717);border:1px solid var(--ui-stroke-secondary,#444);padding:16px}.pc-dialog input{box-sizing:border-box;width:100%;margin:12px 0}.pc-risk{padding:8px;background:#854d0e44;margin:8px 0}.pc-loading{height:100%;display:grid;place-items:center;color:var(--ui-text-tertiary,#888)}.pc-form{width:min(680px,calc(100% - 32px));margin:auto;padding:32px}.pc-form h2{font-size:20px;margin:0 0 8px}.pc-field{display:grid;gap:6px;margin:14px 0}.pc-field input,.pc-field textarea{box-sizing:border-box;width:100%}.pc-field textarea{min-height:92px;resize:vertical}.pc-composer{grid-column:1/-1}.pc-preset{font-size:11px}.pc-checkpoint{border-left:3px solid var(--ui-stroke-secondary,#444);padding-left:10px}.pc-diagnostic-group{display:grid;gap:8px}.pc-diagnostic-note{font-size:11px;color:var(--ui-text-tertiary,#888)}
      @media(max-width:800px){.pc-grid,.pc-split{grid-template-columns:1fr}.pc-head{flex-wrap:wrap}.pc-head .pc-spacer{display:none}}
    </style><div data-pc-root><div class="pc-loading">Loading Product Creative…</div></div>`
    const shell = root.querySelector('[data-pc-root]')

    const api = (path, options) => host.api(`${API}${path}`, options)
    const invalidate = async () => { await refresh(true); render() }

    async function loadProducts() {
      if (!host.workspaceRoot) return
      const result = await api('/products')
      state.products = result.products || []
      const remembered = localStorage.getItem(`product-creative:active:${host.workspaceRoot}`)
      if (!state.products.some(item => item.product_id === state.product)) {
        state.product = state.products.some(item => item.product_id === remembered) ? remembered : state.products[0]?.product_id || ''
      }
      if (state.product) localStorage.setItem(`product-creative:active:${host.workspaceRoot}`, state.product)
    }

    async function refresh(force) {
      if (state.stopped || !host.workspaceRoot) return
      try {
        if (force || !state.products.length) await loadProducts()
        if (!state.product) { state.loading = false; return }
        const product = encodeURIComponent(state.product)
        const base = [api(`/products/${product}/snapshot`), api(`/products/${product}/workflows`), api(`/products/${product}/creative-tasks`)]
        if (state.tab === 'review' || force) base.push(api(`/products/${product}/review-queue`).then(value => { state.review = value }))
        if (state.tab === 'assets' || force) base.push(api(`/products/${product}/assets`).then(value => { state.assets = value }))
        if (state.tab === 'learning' || force) base.push(api(`/products/${product}/learning`).then(value => { state.learning = value }))
        if (state.tab === 'settings') base.push(api('/diagnostics').then(value => { state.diagnostics = value }))
        const [snapshotValue, workflowValue, creativeTaskValue] = await Promise.all(base)
        state.snapshot = snapshotValue
        state.workflows = workflowValue.workflows || []
        state.creativeTasks = creativeTaskValue.creative_tasks || []
        state.error = ''
      } catch (cause) {
        state.error = cause instanceof Error ? cause.message : String(cause)
      } finally {
        state.loading = false
        clearTimeout(timer)
        if (!state.stopped) timer = setTimeout(tick, state.snapshot?.attention?.open_workflows > 0 ? 2000 : 10000)
      }
    }

    async function tick() { await refresh(false); if (!state.stopped) render() }

    function header() {
      const counts = { tasks: state.workflows.length + state.creativeTasks.length, review: (state.review?.proposals?.length || 0) + state.creativeTasks.filter(item => item.current_stage === 'QUALITY_REVIEW').length, assets: (state.assets?.artifacts?.length || 0) + (state.assets?.materials?.length || 0), learning: state.learning?.rules?.length || 0, settings: state.diagnostics?.overall_status ? 1 : 0 }
      return `<div class="pc-head"><h1>Product Creative</h1><select data-change="product">${state.products.map(item => `<option value="${escape(item.product_id)}" ${item.product_id === state.product ? 'selected' : ''}>${escape(item.product_id)}</option>`).join('')}</select><span class="pc-status">v${escape(state.snapshot?.brain?.version || '-')}</span><span class="pc-spacer"></span><button class="pc-btn" data-action="refresh">${c.refresh}</button><button class="pc-btn" data-action="chat">${c.continueChat}</button></div><div class="pc-tabs">${['overview','tasks','review','assets','learning','settings'].map(tab => `<button data-tab="${tab}" aria-selected="${state.tab === tab}">${c[tab]}${counts[tab] === undefined ? '' : `<span class="pc-count">${counts[tab]}</span>`}</button>`).join('')}</div>${state.error ? `<div class="pc-error">${escape(state.error)}</div>` : ''}`
    }

    function onboarding() {
      const form = state.onboarding
      return `<div class="pc-form"><h2>${escape(c.onboardingTitle)}</h2><p class="pc-muted">${escape(c.onboardingHelp)}</p>${state.error ? `<div class="pc-error">${escape(state.error)}</div>` : ''}<label class="pc-field"><span>${escape(c.productName)}</span><input data-onboarding="name" value="${escape(form.name)}"></label><label class="pc-field"><span>${escape(c.productId)}</span><input data-onboarding="productId" value="${escape(form.productId)}"></label><label class="pc-field"><span>${escape(c.productDescription)}</span><textarea data-onboarding="description">${escape(form.description)}</textarea></label><div class="pc-actions"><button class="pc-btn pc-primary" data-action="create-product" ${form.submitting ? 'disabled' : ''}>${escape(form.submitting ? c.creatingProduct : c.createProduct)}</button><button class="pc-btn" data-action="onboarding-material">${escape(c.addMaterial)}</button><button class="pc-btn" data-action="open-settings">${escape(c.openSettings)}</button></div></div>`
    }

    function creativeComposer() {
      return `<section class="pc-section pc-composer"><h2>${escape(c.startTask)}</h2><div class="pc-actions"><button class="pc-btn pc-preset" data-preset="video">${escape(c.taskVideo)}</button><button class="pc-btn pc-preset" data-preset="image">${escape(c.taskImage)}</button><button class="pc-btn pc-preset" data-preset="learn">${escape(c.taskLearn)}</button></div><label class="pc-field"><span>${escape(c.goalLabel)}</span><textarea data-goal>${escape(state.goal)}</textarea></label><button class="pc-btn pc-primary" data-action="start-task">${escape(c.startTask)}</button></section>`
    }

    function reviewCheckpoints(latest, professional, media) {
      const readiness = latest?.readiness || {}
      const productStatus = latest ? (readiness.ready ? 'READY' : (readiness.blockers?.length || readiness.questions?.length) ? 'ATTENTION' : 'PENDING') : 'SETUP'
      const creativeStatus = professional?.decision?.selected_candidate_id ? 'READY' : latest ? 'PENDING' : 'SETUP'
      const qualityStatus = media?.human_decision || media?.qa_result || (media?.composite_manifest_id ? 'QUALITY_REVIEW' : 'PENDING')
      return `<section class="pc-section pc-composer"><h2>Operator checkpoints</h2><div class="pc-grid"><div class="pc-checkpoint"><div class="pc-title">${escape(c.productTruth)}</div><div class="pc-muted">${escape((readiness.blockers || []).join(' · ') || (readiness.questions || []).map(item => item.prompt).join(' · ') || 'Product facts are ready for this task.')}</div>${status(productStatus)}</div><div class="pc-checkpoint"><div class="pc-title">${escape(c.creativeDirection)}</div><div class="pc-muted">${escape(professional?.decision?.selection_reason || 'Creative candidates and decision are pending.')}</div>${status(creativeStatus)}</div><div class="pc-checkpoint"><div class="pc-title">${escape(c.finalQuality)}</div><div class="pc-muted">${escape((media?.qa_hard_blockers || []).join(' · ') || (media?.qa_warnings || []).join(' · ') || 'Media QA has not completed.')}</div>${status(qualityStatus)}</div></div></section>`
    }

    function overview() {
      const latest = state.creativeTasks[0]
      const readiness = latest?.readiness || {}
      const professional = latest?.professional_summary || {}
      const media = professional.media || {}
      return `<div class="pc-grid">${creativeComposer()}${reviewCheckpoints(latest, professional, media)}<section class="pc-section"><h2>Product Brain</h2><div class="pc-rows"><div class="pc-row"><div class="pc-grow"><div class="pc-metric">v${escape(state.snapshot?.brain?.version || '-')}</div><div class="pc-muted">${escape(state.snapshot?.brain?.state?.name || state.product)}</div></div></div></div></section><section class="pc-section"><h2>Product Readiness</h2>${latest ? `<div class="pc-rows"><div class="pc-row"><div class="pc-grow"><div class="pc-title">${escape(latest.request?.raw_message || latest.task_id)}</div><div class="pc-muted">${escape((readiness.blockers || []).join(' · ') || 'No product blocker')}</div></div>${status(readiness.ready ? 'ready' : latest.status)}</div>${rows(readiness.questions, item => `<div class="pc-row"><div class="pc-grow">${escape(item.prompt)}</div>${status(item.field_key)}</div>`)}</div>` : '<div class="pc-empty">No Creative Task readiness yet</div>'}</section><section class="pc-section"><h2>Professional readiness</h2>${latest ? `<div class="pc-rows"><div class="pc-row"><div class="pc-grow"><div class="pc-title">Grounding</div><div class="pc-muted">${escape((professional.grounding?.blockers || []).join(' · ') || 'Product grounding ready')}</div></div>${status(professional.grounding?.readiness_status || latest.professional_artifact_status)}</div><div class="pc-row"><div class="pc-grow"><div class="pc-title">Preflight QA</div><div class="pc-muted">${escape((professional.qa?.blockers || professional.qa?.warnings || []).join(' · ') || 'No professional blocker')}</div></div>${status(professional.qa?.gate_result || latest.professional_artifact_status)}</div></div>` : '<div class="pc-empty">No professional creative pack yet</div>'}</section><section class="pc-section"><h2>Media production</h2>${latest ? `<div class="pc-rows"><div class="pc-row"><div class="pc-grow"><div class="pc-title">${escape(`${media.shots_completed || 0} / ${media.shots_total || 0} shots`)}</div><div class="pc-muted">${escape(media.current_failure || (media.dependency_blockers || []).join(' · ') || (media.dependency_warnings || []).join(' · ') || media.plan_id || 'Media plan not prepared')}</div></div>${status(media.qa_result || (media.composite_manifest_id ? 'quality_review' : media.dependency_status || 'pending'))}</div><div class="pc-row"><div class="pc-grow"><div class="pc-title">Automatic Media QA</div><div class="pc-muted">${escape((media.qa_hard_blockers || []).join(' · ') || (media.qa_failed_shot_ids || []).join(', ') || media.qa_report_id || 'Not run')}</div></div>${status(media.human_decision || media.qa_result || 'pending')}</div></div>` : '<div class="pc-empty">No media production state</div>'}</section><section class="pc-section"><h2>Attention</h2><div class="pc-grid pc-rows"><div class="pc-row"><div><div class="pc-metric">${state.snapshot?.attention?.open_workflows || 0}</div><div class="pc-muted">Open workflows</div></div></div><div class="pc-row"><div><div class="pc-metric">${state.snapshot?.attention?.pending_proposals || 0}</div><div class="pc-muted">Pending proposals</div></div></div></div></section></div>`
    }

    function tasks() {
      const artifactPointers = state.creativeTask?.professional_artifacts || {}
      const skillExecutions = state.creativeTask?.professional_artifact_details?.skill_executions || []
      const media = state.creativeTask?.professional_summary?.media || {}
      const shotResults = state.creativeTask?.professional_artifact_details?.media_shot_results || []
      const creativeDetail = state.creativeTask ? `<div class="pc-rows"><div class="pc-row"><div class="pc-grow"><div class="pc-title">${escape(state.creativeTask.request?.raw_message || state.creativeTask.task_id)}</div><div class="pc-muted">Stage: ${escape(state.creativeTask.current_stage)} · Skill: ${escape(state.creativeTask.professional_summary?.skills?.latest_skill || 'not started')} · ${escape(state.creativeTask.blocked_reason || 'No blocker')}</div></div>${status(state.creativeTask.status)}</div></div><div class="pc-actions" style="margin-top:10px"><button class="pc-btn pc-primary" data-continue-task="${escape(state.creativeTask.task_id)}">${escape(c.continueTask)}</button></div><h2 style="margin-top:16px">Professional artifact gates</h2>${rows(state.creativeTask.plan?.artifact_gates, gate => { const key = gate === 'preflight_qa' ? 'qa_report' : gate; const value = artifactPointers[key]; return `<div class="pc-row"><div class="pc-grow"><div class="pc-title">${escape(gate)}</div><div class="pc-muted">${escape(Array.isArray(value) ? value.join(', ') : value || 'Not produced')}</div></div>${status(value ? 'ready' : 'pending')}</div>` })}<h2 style="margin-top:16px">Business Skill executions</h2>${rows(skillExecutions, item => `<div class="pc-row"><div class="pc-grow"><div class="pc-title">${escape(item.skill_name || item.artifact_id)}</div><div class="pc-muted">v${escape(item.skill_version || '?')} · ${escape(item.stage || '')} · ${escape(item.execution_mode || '')}</div></div>${status(item.execution_status || item.status)}</div>`)}<h2 style="margin-top:16px">Shot production</h2><div class="pc-rows"><div class="pc-row"><div class="pc-grow"><div class="pc-title">${escape(`${media.shots_completed || 0} / ${media.shots_total || 0} shots`)}</div><div class="pc-muted">${escape(media.current_failure || media.plan_id || 'Not prepared')}</div></div>${status(media.qa_result || (media.composite_manifest_id ? 'quality_review' : media.dependency_status || 'pending'))}</div><div class="pc-row"><div class="pc-grow"><div class="pc-title">QA / Repair</div><div class="pc-muted">${escape(`${media.qa_report_id || 'not run'} · repair ${media.repair_round || 0}: ${media.repair_decision || 'none'}`)}</div></div>${status(media.human_decision || media.qa_result || 'pending')}</div></div>${rows(shotResults, item => `<div class="pc-row"><div class="pc-grow"><div class="pc-title">${escape(item.shot_id || item.artifact_id)}</div><div class="pc-muted">${escape(item.error_detail || item.output_relative_path || `Attempt ${item.attempt || 0}`)}</div></div>${status(item.execution_status || item.status)}</div>`)}<h2 style="margin-top:16px">Plan stages</h2>${rows(state.creativeTask.plan?.actions, item => `<div class="pc-row"><div class="pc-grow"><div class="pc-title">${escape(item.action)}</div><div class="pc-muted">${escape(item.stage)}</div></div>${status(item.status)}</div>`)}<h2 style="margin-top:16px">Authorization and delivery</h2><pre class="pc-json">${escape(JSON.stringify({ professional_status: state.creativeTask.professional_artifact_status, authorization_request_id: state.creativeTask.authorization_request_id, authorization_id: state.creativeTask.authorization_id, selected_materials: state.creativeTask.selected_materials, selected_idea: state.creativeTask.selected_idea, results: state.creativeTask.result_descriptors }, null, 2))}</pre>` : '<div class="pc-empty">Select a Creative Task</div>'
      return `<div class="pc-split"><section class="pc-section"><h2>Creative Tasks</h2>${rows(state.creativeTasks, item => `<button class="pc-row pc-btn" style="width:100%;text-align:left" data-creative-task="${escape(item.task_id)}"><span class="pc-grow"><span class="pc-title">${escape(item.request?.raw_message || item.task_id)}</span><span class="pc-muted">${escape(item.current_stage || '')}</span></span>${status(item.status)}</button>`)}<h2 style="margin-top:16px">Durable workflows</h2>${rows(state.workflows, item => `<button class="pc-row pc-btn" style="width:100%;text-align:left" data-workflow="${escape(item.workflow_id)}"><span class="pc-grow"><span class="pc-title">${escape(item.definition)}</span><span class="pc-muted">${escape(item.workflow_id)}</span></span>${status(item.status)}</button>`)}</section><section><section class="pc-section"><h2>Creative Task detail</h2>${creativeDetail}</section><section class="pc-section" style="margin-top:20px"><h2>Workflow detail</h2>${state.workflow ? `<div class="pc-actions"><button class="pc-btn" data-command="retry" data-id="${escape(state.workflow.workflow?.workflow_id || '')}">${c.retry}</button><button class="pc-btn" data-command="cancel" data-id="${escape(state.workflow.workflow?.workflow_id || '')}">${c.cancel}</button>${(state.workflow.provider_tasks || []).map(task => `<button class="pc-btn" data-command="provider" data-id="${escape(task.provider_task_id)}">${c.providerRefresh}</button>`).join('')}</div><pre class="pc-json">${escape(JSON.stringify(state.workflow, null, 2))}</pre>` : '<div class="pc-empty">Select a workflow</div>'}</section></section></div>`
    }

    function assetRow(item) {
      const kind = String(item.type || '')
      const image = kind.includes('image')
      const video = kind.includes('video')
      return `<div class="pc-row">${image ? `<img class="pc-media" data-thumbnail="${escape(item.record_id)}" alt="">` : `<div class="pc-media pc-empty">${video ? 'VIDEO' : 'FILE'}</div>`}<div class="pc-grow"><div class="pc-title">${escape(item.record_id)}</div><div class="pc-muted">${escape(item.relative_path)}</div><div class="pc-muted">${escape(JSON.stringify(item.payload?.provenance || item.payload?.source || {}))}</div></div>${status(item.status || item.type)}<button class="pc-btn" data-media="${escape(item.record_id)}">Open</button></div>`
    }

    function review() {
      const taskReviews = state.creativeTasks.filter(item => item.pending_proposal_id || item.status === 'NEEDS_INPUT' || item.request?.autonomy_mode === 'preview_first')
      const details = state.creativeTask?.professional_artifact_details || {}
      const candidates = details.creative_candidates || []
      const decision = details.creative_decision || {}
      const story = details.story_package || {}
      const qa = details.qa_report || {}
      const mediaPlan = details.media_execution_plan || {}
      const manifest = details.media_composite_manifest || {}
      const mediaQa = details.media_qa_report || {}
      const mediaRepair = details.media_repair_decision || {}
      const mediaOverride = details.media_human_override || {}
      const skillExecutions = details.skill_executions || []
      const checkpointTask = state.creativeTask || state.creativeTasks[0] || {}
      const checkpointDecision = decision.selected_candidate_id ? decision : checkpointTask.professional_summary?.decision || {}
      const checkpointMedia = checkpointTask.professional_summary?.media || {}
      const checkpointReview = `<section class="pc-section"><h2>1. ${escape(c.productTruth)}</h2><div class="pc-rows"><div class="pc-row"><div class="pc-grow"><div class="pc-title">${escape(checkpointTask.request?.raw_message || 'No active task')}</div><div class="pc-muted">${escape(checkpointTask.blocked_reason || (checkpointTask.readiness?.blockers || []).join(' · ') || 'Product facts are ready for this task.')}</div></div>${status(checkpointTask.readiness?.ready ? 'READY' : checkpointTask.status || 'PENDING')}</div></div></section><section class="pc-section"><h2>2. ${escape(c.creativeDirection)}</h2><div class="pc-rows"><div class="pc-row"><div class="pc-grow"><div class="pc-title">${escape(checkpointDecision.selected_candidate_id || 'Direction pending')}</div><div class="pc-muted">${escape(checkpointDecision.selection_reason || 'Review the creative candidates and story package below.')}</div></div>${status(checkpointDecision.selected_candidate_id ? 'READY' : 'PENDING')}</div></div></section><section class="pc-section"><h2>3. ${escape(c.finalQuality)}</h2><div class="pc-rows"><div class="pc-row"><div class="pc-grow"><div class="pc-title">${escape(mediaQa.overall_result || checkpointMedia.qa_result || qa.gate_result || 'Quality review pending')}</div><div class="pc-muted">${escape([...(mediaQa.hard_blockers || []), ...(mediaQa.warnings || []), ...(checkpointMedia.qa_hard_blockers || []), ...(qa.blockers || [])].join(' · ') || 'Review preflight and media QA evidence below.')}</div></div>${status(mediaOverride.decision || mediaQa.overall_result || checkpointMedia.qa_result || qa.gate_result || 'PENDING')}</div></div></section>`
      const mediaQaReview = mediaQa.artifact_id ? `<section class="pc-section"><h2>Automatic Media QA</h2><div class="pc-rows"><div class="pc-row"><div class="pc-grow"><div class="pc-title">${escape(mediaQa.overall_result)}</div><div class="pc-muted">${escape([...(mediaQa.hard_blockers || []), ...(mediaQa.warnings || [])].join(' · ') || 'No blocker')}</div></div>${status(mediaOverride.decision || mediaQa.overall_result)}</div>${rows(mediaQa.checks, item => `<div class="pc-row"><div class="pc-grow"><div class="pc-title">${escape(item.check_id)}</div><div class="pc-muted">${escape(`${item.shot_id || item.scope} · ${JSON.stringify(item.observed || {})}`)}</div></div>${status(`${item.status}/${item.severity}`)}</div>`)}</div>${mediaOverride.artifact_id ? `<div class="pc-muted">Human decision: ${escape(mediaOverride.decision)} · ${escape(mediaOverride.reason)}</div>` : `<div class="pc-actions"><button class="pc-btn" data-media-qa="reject" data-id="${escape(mediaQa.artifact_id)}">${c.reject}</button><button class="pc-btn" data-media-qa="accept_with_warning" data-id="${escape(mediaQa.artifact_id)}">Accept with warning</button><button class="pc-btn pc-primary" data-media-qa="approve" data-id="${escape(mediaQa.artifact_id)}">${c.accept}</button></div>`}<pre class="pc-json">${escape(JSON.stringify({ failed_shot_ids: mediaQa.failed_shot_ids, repair: mediaRepair }, null, 2))}</pre></section>` : ''
      const professionalReview = state.creativeTask ? `<section class="pc-section"><h2>Creative candidates</h2>${rows(candidates, item => `<div class="pc-row"><div class="pc-grow"><div class="pc-title">${escape(item.one_liner || item.artifact_id)}</div><div class="pc-muted">${escape(item.hook || '')}</div><div class="pc-muted">History similarity: ${escape(item.historical_similarity ?? 0)} · ${escape(item.novelty_strategy || item.historical_difference || 'No novelty note')}</div></div>${status(item.direction)}</div>`)}</section><section class="pc-section"><h2>Creative Decision</h2><div class="pc-rows"><div class="pc-row"><div class="pc-grow"><div class="pc-title">${escape(decision.selected_candidate_id || 'No decision')}</div><div class="pc-muted">${escape(decision.selection_reason || '')}</div></div>${status(decision.selected_candidate_id ? 'selected' : 'pending')}</div></div></section><section class="pc-section"><h2>Skill provenance</h2>${rows(skillExecutions, item => `<div class="pc-row"><div class="pc-grow"><div class="pc-title">${escape(item.skill_name || item.artifact_id)} v${escape(item.skill_version || '?')}</div><div class="pc-muted">${escape((item.input_artifacts || []).map(ref => ref.artifact_id).join(', ') || 'No professional input artifact')}</div></div>${status(item.execution_status || item.status)}</div>`)}</section><section class="pc-section"><h2>Story Package</h2><pre class="pc-json">${escape(JSON.stringify({ premise: story.premise, hook_visual: story.hook_visual, conflict: story.conflict, turn: story.turn, ending: story.ending }, null, 2))}</pre></section><section class="pc-section"><h2>Preflight QA</h2><div class="pc-rows"><div class="pc-row"><div class="pc-grow"><div class="pc-title">${escape(qa.gate_result || 'Not run')}</div><div class="pc-muted">${escape([...(qa.blockers || []), ...(qa.warnings || [])].join(' · ') || 'No blocker')}</div></div>${status(qa.gate_result || 'pending')}</div></div></section>${mediaQaReview}<section class="pc-section"><h2>Media provenance</h2><pre class="pc-json">${escape(JSON.stringify({ production_bible_id: mediaPlan.production_bible_id, media_plan_id: mediaPlan.artifact_id, product_plate_id: mediaPlan.product_plate_id, composite_manifest_id: manifest.artifact_id, output: manifest.output_relative_path }, null, 2))}</pre></section>` : '<section class="pc-section"><div class="pc-empty">Select a Creative Task in Tasks to review its professional pack</div></section>'
      return `<div class="pc-grid">${checkpointReview}${professionalReview}</div><section class="pc-section" style="margin-top:20px"><h2>Creative Task review</h2>${rows(taskReviews, item => `<div class="pc-row"><div class="pc-grow"><div class="pc-title">${escape(item.request?.raw_message || item.task_id)}</div><div class="pc-muted">${escape(item.blocked_reason || item.pending_proposal_kind || 'Preview requested')}</div></div>${status(item.status)}</div>`)}</section><section class="pc-section" style="margin-top:20px"><h2>Proposals</h2>${rows(state.review?.proposals, item => { const id = idOf(item, 'proposal_id', 'id'); return `<div class="pc-row"><div class="pc-grow"><div class="pc-title">${escape(id)}</div>${status(item.risk_level)}</div><button class="pc-btn" data-proposal="reject" data-id="${escape(id)}">${c.reject}</button><button class="pc-btn pc-primary" data-proposal="accept" data-id="${escape(id)}">${c.accept}</button></div>` })}</section><section class="pc-section" style="margin-top:20px"><h2>Recent results</h2>${rows(state.review?.results, assetRow)}</section>`
    }

    function assets() {
      const taskAssets = state.creativeTasks.flatMap(task => (task.selected_materials || []).map(item => ({ ...item, task_id: task.task_id })))
      const details = state.creativeTask?.professional_artifact_details || {}
      const bible = details.production_bible || {}
      const plate = details.product_plate || {}
      const shotResults = details.media_shot_results || []
      const manifest = details.media_composite_manifest || {}
      return `<div class="pc-grid"><section class="pc-section"><h2>Task-selected inputs</h2>${rows(taskAssets, item => `<div class="pc-row"><div class="pc-grow"><div class="pc-title">${escape(item.material_id || item.role)}</div><div class="pc-muted">${escape(item.role || '')} · ${escape(item.task_id)}</div></div>${status('selected')}</div>`)}</section><section class="pc-section"><h2>Production Bible</h2>${bible.artifact_id ? `<div class="pc-rows"><div class="pc-row"><div class="pc-grow"><div class="pc-title">${escape(bible.artifact_id)}</div><div class="pc-muted">${escape(bible.packaging_strategy)}</div></div>${status(`${bible.shots?.length || 0} shots`)}</div></div><pre class="pc-json">${escape(JSON.stringify(bible.shots || [], null, 2))}</pre>` : '<div class="pc-empty">Select a Creative Task with a Production Bible</div>'}</section><section class="pc-section"><h2>Product Plate</h2>${plate.artifact_id ? `<div class="pc-rows"><div class="pc-row"><div class="pc-grow"><div class="pc-title">${escape(plate.artifact_id)}</div><div class="pc-muted">${escape(plate.plate_relative_path || '')}</div></div>${status(plate.mask_mode)}</div></div>` : '<div class="pc-empty">No product plate</div>'}</section><section class="pc-section"><h2>Shot outputs</h2>${rows(shotResults, item => `<div class="pc-row"><div class="pc-grow"><div class="pc-title">${escape(item.shot_id || item.artifact_id)}</div><div class="pc-muted">${escape(item.output_relative_path || item.error_detail || '')}</div></div>${status(item.execution_status || item.status)}</div>`)}</section><section class="pc-section"><h2>Final composite</h2>${manifest.artifact_id ? `<div class="pc-rows"><div class="pc-row"><div class="pc-grow"><div class="pc-title">${escape(manifest.artifact_id)}</div><div class="pc-muted">${escape(manifest.output_relative_path || '')}</div></div>${status(manifest.codec || 'ready')}</div></div>` : '<div class="pc-empty">No final composite</div>'}</section><section class="pc-section"><h2>Artifacts</h2>${rows(state.assets?.artifacts, assetRow)}</section><section class="pc-section"><h2>Materials</h2>${rows(state.assets?.materials, assetRow)}</section></div>`
    }

    function learning() {
      const current = Number(state.snapshot?.brain?.version || 0)
      const taskLearning = state.creativeTasks.flatMap(task => (task.result_descriptors || []).filter(item => ['task_revision', 'product_brain_learning_confirmation', 'media_qa_human_decision', 'media_qa_learning_evidence'].includes(item.type)).map(item => ({ ...item, task_id: task.task_id })))
      return `<div class="pc-grid"><section class="pc-section"><h2>Task feedback impact</h2>${rows(taskLearning, item => `<div class="pc-row"><div class="pc-grow"><div class="pc-title">${escape(item.message || item.proposal_id || item.type)}</div><div class="pc-muted">${escape(item.task_id)} · Brain writeback: ${escape(item.product_brain_writeback ?? item.status)}</div></div>${status(item.scope || item.status)}</div>`)}</section><section class="pc-section"><h2>Brain versions</h2>${rows(state.learning?.versions, item => `<div class="pc-row"><div class="pc-grow">Version ${escape(item.version)} ${status(item.change_kind)}</div>${Number(item.version) !== current ? `<button class="pc-btn" data-version="${escape(item.version)}">${c.rollback}</button>` : ''}</div>`)}</section><section class="pc-section"><h2>Rules</h2>${rows(state.learning?.rules, item => { const id = idOf(item, 'rule_id', 'id'); return `<div class="pc-row"><div class="pc-grow"><div class="pc-title">${escape(id)}</div>${status(item.status)}</div>${item.status !== 'revoked' ? `<button class="pc-btn" data-rule="${escape(id)}">${c.revoke}</button>` : ''}</div>` })}</section></div>`
    }

    function diagnosticRows(category) {
      const checks = (state.diagnostics?.checks || []).filter(item => item.category === category)
      return rows(checks, item => `<div class="pc-row"><div class="pc-grow"><div class="pc-title">${escape(item.label)}</div><div class="pc-muted">${escape(item.detail)}</div>${item.required ? '' : '<div class="pc-diagnostic-note">Optional: normal creation can continue without this source.</div>'}</div>${status(item.status)}</div>`)
    }

    function settings() {
      return `<div class="pc-grid"><section class="pc-section pc-composer"><div class="pc-actions"><button class="pc-btn" data-action="refresh-diagnostics">${escape(c.diagnosticsRefresh)}</button><button class="pc-btn" data-action="open-settings">${escape(c.openSettings)}</button></div><p class="pc-muted">Product Creative ${status(state.diagnostics?.overall_status || 'LOADING')} · Secret values are never returned by this page.</p></section><section class="pc-section"><h2>${escape(c.credentials)}</h2><div class="pc-diagnostic-group">${diagnosticRows('model_credentials')}${diagnosticRows('provider_runtime')}</div></section><section class="pc-section"><h2>${escape(c.mediaRuntime)}</h2>${diagnosticRows('media_runtime')}</section><section class="pc-section"><h2>${escape(c.optionalSources)}</h2>${diagnosticRows('optional_sources')}</section></div>`
    }

    function render() {
      if (!host.workspaceRoot) { shell.innerHTML = `<div class="pc-empty">${c.noWorkspace}</div>`; return }
      if (state.loading) return
      if (!state.products.length) { shell.innerHTML = onboarding(); return }
      const views = { overview, tasks, review, assets, learning, settings }
      shell.innerHTML = `${header()}<main class="pc-main">${views[state.tab]()}</main>${confirmation()}`
      loadThumbnails()
    }

    function confirmation() {
      const pending = state.confirmation
      if (!pending) return ''
      return `<div class="pc-dialog"><div><h2>${escape(pending.title)}</h2><div class="pc-risk">${escape(pending.risk || 'This action changes durable Product Creative state.')}<br>Expected Product Brain version: ${escape(pending.body.expected_version ?? '-')}</div><input data-confirm-reason placeholder="${c.reason}" value="${escape(pending.reason || '')}"><div class="pc-actions"><button class="pc-btn" data-action="close-confirm">${c.close}</button><button class="pc-btn pc-primary" data-action="confirm">${c.confirm}</button></div></div></div>`
    }

    function confirmationId(cause) {
      const message = cause instanceof Error ? cause.message : String(cause)
      const start = message.indexOf('{')
      if (start < 0) return ''
      try { const parsed = JSON.parse(message.slice(start)); return parsed.output?.confirmation_id || parsed.detail?.output?.confirmation_id || '' } catch { return '' }
    }

    async function mutate(title, path, body, confirmed) {
      try {
        await api(path, { method: 'POST', body: confirmed ? { ...body, confirmed: true, confirmation_id: state.confirmation.confirmationId, reason: state.confirmation.reason, actor: 'desktop-user' } : body })
        state.confirmation = null
        await invalidate()
      } catch (cause) {
        const id = confirmationId(cause)
        if (!confirmed && id) state.confirmation = { title, path, body, confirmationId: id, reason: '', risk: 'Confirmation and audit are required.' }
        else { state.confirmation = null; state.error = cause instanceof Error ? cause.message : String(cause) }
        render()
      }
    }

    async function createProduct() {
      const name = state.onboarding.name.trim()
      if (!name) { state.error = `${c.productName} is required.`; render(); return }
      state.onboarding.submitting = true
      state.error = ''
      render()
      try {
        const result = await api('/products', { method: 'POST', body: { name, product_id: state.onboarding.productId.trim(), description: state.onboarding.description.trim() } })
        state.product = result.selected_product_id || ''
        state.onboarding = { name: '', productId: '', description: '', submitting: false }
        state.loading = true
        await refresh(true)
      } catch (cause) {
        state.onboarding.submitting = false
        state.loading = false
        state.error = cause instanceof Error ? cause.message : String(cause)
      }
      render()
    }

    function startCreativeTask() {
      const goal = state.goal.trim()
      if (!goal) { state.error = `${c.goalLabel} is required.`; render(); return }
      const productName = state.snapshot?.brain?.state?.name || state.product
      host.continueInChat(`Current Product Creative context: ${productName} (product_id: ${state.product}). User goal: ${goal}`)
    }

    async function loadThumbnails() {
      for (const image of shell.querySelectorAll('[data-thumbnail]')) {
        try { const value = await api(`/media/${encodeURIComponent(image.dataset.thumbnail)}/thumbnail`); image.src = value.data_url } catch { image.alt = c.unavailable }
      }
    }

    shell.addEventListener('change', event => {
      if (state.stopped) return
      const target = event.target
      if (target?.dataset?.change === 'product') { state.product = target.value; state.workflow = null; state.creativeTask = null; state.diagnostics = null; localStorage.setItem(`product-creative:active:${host.workspaceRoot}`, state.product); void invalidate() }
      if (target?.dataset?.confirmReason !== undefined && state.confirmation) state.confirmation.reason = target.value
    })
    shell.addEventListener('input', event => {
      if (state.stopped) return
      const target = event.target
      if (target?.dataset?.confirmReason !== undefined && state.confirmation) state.confirmation.reason = target.value
      if (target?.dataset?.onboarding) state.onboarding[target.dataset.onboarding] = target.value
      if (target?.dataset?.goal !== undefined) state.goal = target.value
    })
    shell.addEventListener('click', event => {
      if (state.stopped) return
      const target = event.target.closest('button')
      if (!target) return
      if (target.dataset.tab) { state.tab = target.dataset.tab; void invalidate() }
      if (target.dataset.action === 'refresh') void invalidate()
      if (target.dataset.action === 'refresh-diagnostics') void invalidate()
      if (target.dataset.action === 'open-settings') host.navigate('/settings')
      if (target.dataset.action === 'create-product') void createProduct()
      if (target.dataset.action === 'onboarding-material') host.continueInChat('I am onboarding a new Product Creative product. Please ask for the product name, description, and current main image; keep unconfirmed information in Evidence and Draft Understanding.')
      if (target.dataset.action === 'start-task') startCreativeTask()
      if (target.dataset.preset) {
        const presets = locale === 'zh' ? { video: '帮我做一个今天能发的产品视频', image: '帮我制作一张产品图片', learn: '继续了解这个产品，并告诉我最需要补充的三个信息' } : { video: 'Create a product video I can publish today', image: 'Create a product image', learn: 'Continue learning this product and ask for the three highest-value missing details' }
        state.goal = presets[target.dataset.preset] || ''
        render()
      }
      if (target.dataset.continueTask) host.continueInChat(`continue Product Creative task ${target.dataset.continueTask} for product ${state.product}; resume from durable state without repeating completed paid work.`)
      if (target.dataset.action === 'chat') host.continueInChat(`针对产品 ${state.product}，继续审阅并处理当前 Product Creative 状态。`)
      if (target.dataset.action === 'close-confirm') { state.confirmation = null; render() }
      if (target.dataset.action === 'confirm' && state.confirmation) {
        if (!state.confirmation.reason.trim()) { state.error = c.reasonRequired; render() }
        else void mutate(state.confirmation.title, state.confirmation.path, state.confirmation.body, true)
      }
      if (target.dataset.workflow) void api(`/workflows/${encodeURIComponent(target.dataset.workflow)}`).then(value => { state.workflow = value; render() }).catch(cause => { state.error = String(cause); render() })
      if (target.dataset.creativeTask) void api(`/products/${encodeURIComponent(state.product)}/creative-tasks/${encodeURIComponent(target.dataset.creativeTask)}`).then(value => { state.creativeTask = value; render() }).catch(cause => { state.error = String(cause); render() })
      const version = Number(state.snapshot?.brain?.version || 0)
      if (target.dataset.proposal) void mutate(target.dataset.proposal === 'accept' ? c.accept : c.reject, `/proposals/${encodeURIComponent(target.dataset.id)}/decision`, { product_id: state.product, decision: target.dataset.proposal, expected_version: version }, false)
      if (target.dataset.mediaQa) void mutate('Media QA decision', `/products/${encodeURIComponent(state.product)}/media-qa/${encodeURIComponent(target.dataset.id)}/decision`, { decision: target.dataset.mediaQa }, false)
      if (target.dataset.version) void mutate(c.rollback, `/products/${encodeURIComponent(state.product)}/brain/rollback`, { target_version: Number(target.dataset.version), expected_version: version }, false)
      if (target.dataset.rule) void mutate(c.revoke, `/rules/${encodeURIComponent(target.dataset.rule)}/revoke`, { product_id: state.product, expected_version: version }, false)
      if (target.dataset.command === 'retry' || target.dataset.command === 'cancel') void mutate(target.dataset.command === 'retry' ? c.retry : c.cancel, `/workflows/${encodeURIComponent(target.dataset.id)}/${target.dataset.command}`, { expected_version: Number(state.workflow?.workflow?.version || 0) }, false)
      if (target.dataset.command === 'provider') void mutate(c.providerRefresh, `/provider-tasks/${encodeURIComponent(target.dataset.id)}/refresh`, { product_id: state.product }, false)
      if (target.dataset.media) void api(`/media/${encodeURIComponent(target.dataset.media)}/descriptor`).then(value => host.previewMedia(value.path)).catch(cause => { state.error = String(cause); render() })
    })

    void refresh(true).then(() => { if (!state.stopped) render() })
    return () => { state.stopped = true; clearTimeout(timer); root.innerHTML = '' }
  }

  window.__HERMES_DESKTOP_PLUGINS__.registerPage({ apiVersion: 1, name: 'product_creative', mount })
})()
