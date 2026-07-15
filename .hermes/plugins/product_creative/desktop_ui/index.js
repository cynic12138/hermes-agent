(function () {
  'use strict'

  const API = '/api/plugins/product_creative/v1'
  const copy = {
    en: { overview: 'Overview', tasks: 'Tasks', review: 'Review queue', assets: 'Assets', learning: 'Learning', continueChat: 'Continue in chat', refresh: 'Refresh', noWorkspace: 'Open a workspace to use Product Creative.', noProducts: 'No Product Creative products in this workspace.', reason: 'Reason for this action', reasonRequired: 'A reason is required before confirmation.', confirm: 'Confirm', close: 'Close', accept: 'Accept', reject: 'Reject', rollback: 'Rollback', revoke: 'Revoke', retry: 'Retry', cancel: 'Cancel', providerRefresh: 'Refresh provider task', unavailable: 'Media unavailable' },
    zh: { overview: '概览', tasks: '任务', review: '审阅队列', assets: '素材与结果', learning: '学习', continueChat: '在聊天中继续', refresh: '刷新', noWorkspace: '请先打开一个工作区。', noProducts: '当前工作区没有 Product Creative 产品。', reason: '填写本次操作原因', reasonRequired: '确认前必须填写操作原因。', confirm: '确认', close: '取消', accept: '接受', reject: '拒绝', rollback: '回滚', revoke: '撤销规则', retry: '重试', cancel: '取消工作流', providerRefresh: '刷新 Provider 任务', unavailable: '媒体不可用' },
    'zh-hant': { overview: '概覽', tasks: '任務', review: '審閱佇列', assets: '素材與結果', learning: '學習', continueChat: '在聊天中繼續', refresh: '重新整理', noWorkspace: '請先開啟一個工作區。', noProducts: '目前工作區沒有 Product Creative 產品。', reason: '填寫本次操作原因', reasonRequired: '確認前必須填寫操作原因。', confirm: '確認', close: '取消', accept: '接受', reject: '拒絕', rollback: '回復', revoke: '撤銷規則', retry: '重試', cancel: '取消工作流程', providerRefresh: '重新整理 Provider 任務', unavailable: '媒體無法使用' },
    ja: { overview: '概要', tasks: 'タスク', review: 'レビュー', assets: 'アセット', learning: '学習', continueChat: 'チャットで続ける', refresh: '更新', noWorkspace: 'ワークスペースを開いてください。', noProducts: 'このワークスペースに製品がありません。', reason: '操作理由', reasonRequired: '確認する前に操作理由を入力してください。', confirm: '確認', close: 'キャンセル', accept: '承認', reject: '却下', rollback: 'ロールバック', revoke: 'ルール取消', retry: '再試行', cancel: '取消', providerRefresh: 'Provider タスク更新', unavailable: 'メディアを利用できません' }
  }

  const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char])
  const idOf = (item, ...keys) => keys.map(key => item?.[key]).find(Boolean) || ''
  const status = value => `<span class="pc-status">${escape(value || 'unknown')}</span>`
  const rows = (items, render) => items?.length ? `<div class="pc-rows">${items.map(render).join('')}</div>` : '<div class="pc-empty">No records</div>'

  function mount(root, host) {
    const locale = Object.prototype.hasOwnProperty.call(copy, host.locale) ? host.locale : 'en'
    const c = copy[locale]
    const state = { tab: 'overview', product: '', products: [], snapshot: null, workflows: [], workflow: null, review: null, assets: null, learning: null, error: '', loading: true, confirmation: null, stopped: false }
    let timer = 0

    root.innerHTML = `<style>
      [data-pc-root]{height:100%;display:flex;flex-direction:column;min-height:0;background:var(--ui-bg-primary,#111);color:var(--foreground,#eee);font:13px system-ui,sans-serif}
      .pc-head,.pc-tabs{display:flex;align-items:center;gap:8px;padding:9px 16px;border-bottom:1px solid var(--ui-stroke-secondary,#333)}
      .pc-head h1{font-size:14px;margin:0 8px 0 0}.pc-head select{min-width:190px}.pc-head .pc-spacer{flex:1}.pc-btn,select,input{border:1px solid var(--ui-stroke-secondary,#444);background:var(--ui-bg-secondary,#222);color:inherit;padding:5px 9px;border-radius:4px}.pc-btn{cursor:pointer}.pc-btn:hover{background:var(--ui-control-hover-background,#333)}.pc-primary{background:var(--button-primary-background,#2563eb);color:white}
      .pc-tabs button{border:0;border-bottom:2px solid transparent;background:none;color:var(--ui-text-secondary,#aaa);padding:7px 2px;cursor:pointer}.pc-tabs button[aria-selected=true]{border-color:var(--focus-border,#4f8cff);color:inherit}.pc-count{font-size:10px;margin-left:4px;color:var(--ui-text-tertiary,#888)}
      .pc-main{min-height:0;flex:1;overflow:auto;padding:14px 16px}.pc-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}.pc-split{display:grid;grid-template-columns:minmax(260px,.8fr) minmax(360px,1.2fr);gap:16px}.pc-section h2{font-size:11px;text-transform:uppercase;color:var(--ui-text-tertiary,#888);margin:0 0 8px}.pc-metric{font-size:22px;font-weight:600}.pc-muted{color:var(--ui-text-tertiary,#888);font-size:11px}.pc-rows{border-block:1px solid var(--ui-stroke-secondary,#333)}.pc-row{display:flex;align-items:center;gap:10px;padding:9px 4px;border-bottom:1px solid var(--ui-stroke-secondary,#333)}.pc-row:last-child{border:0}.pc-grow{flex:1;min-width:0}.pc-title{font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.pc-status{text-transform:uppercase;font-size:10px;color:var(--ui-text-tertiary,#888)}.pc-empty{min-height:130px;display:grid;place-items:center;color:var(--ui-text-tertiary,#888);border-block:1px solid var(--ui-stroke-secondary,#333)}
      .pc-error{padding:8px 16px;background:#7f1d1d55;color:#fecaca}.pc-json{white-space:pre-wrap;word-break:break-word;font:11px ui-monospace,monospace}.pc-media{width:64px;height:48px;object-fit:cover;background:#222}.pc-actions{display:flex;gap:5px;flex-wrap:wrap}.pc-dialog{position:fixed;inset:0;display:grid;place-items:center;background:#0008;z-index:100}.pc-dialog>div{width:min(440px,calc(100vw - 32px));background:var(--ui-bg-primary,#171717);border:1px solid var(--ui-stroke-secondary,#444);padding:16px}.pc-dialog input{box-sizing:border-box;width:100%;margin:12px 0}.pc-risk{padding:8px;background:#854d0e44;margin:8px 0}.pc-loading{height:100%;display:grid;place-items:center;color:var(--ui-text-tertiary,#888)}
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
        const base = [api(`/products/${product}/snapshot`), api(`/products/${product}/workflows`)]
        if (state.tab === 'review' || force) base.push(api(`/products/${product}/review-queue`).then(value => { state.review = value }))
        if (state.tab === 'assets' || force) base.push(api(`/products/${product}/assets`).then(value => { state.assets = value }))
        if (state.tab === 'learning' || force) base.push(api(`/products/${product}/learning`).then(value => { state.learning = value }))
        const [snapshotValue, workflowValue] = await Promise.all(base)
        state.snapshot = snapshotValue
        state.workflows = workflowValue.workflows || []
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
      const counts = { tasks: state.workflows.length, review: state.review?.proposals?.length || 0, assets: (state.assets?.artifacts?.length || 0) + (state.assets?.materials?.length || 0), learning: state.learning?.rules?.length || 0 }
      return `<div class="pc-head"><h1>Product Creative</h1><select data-change="product">${state.products.map(item => `<option value="${escape(item.product_id)}" ${item.product_id === state.product ? 'selected' : ''}>${escape(item.product_id)}</option>`).join('')}</select><span class="pc-status">v${escape(state.snapshot?.brain?.version || '-')}</span><span class="pc-spacer"></span><button class="pc-btn" data-action="refresh">${c.refresh}</button><button class="pc-btn" data-action="chat">${c.continueChat}</button></div><div class="pc-tabs">${['overview','tasks','review','assets','learning'].map(tab => `<button data-tab="${tab}" aria-selected="${state.tab === tab}">${c[tab]}${counts[tab] === undefined ? '' : `<span class="pc-count">${counts[tab]}</span>`}</button>`).join('')}</div>${state.error ? `<div class="pc-error">${escape(state.error)}</div>` : ''}`
    }

    function overview() {
      return `<div class="pc-grid"><section class="pc-section"><h2>Product Brain</h2><div class="pc-rows"><div class="pc-row"><div class="pc-grow"><div class="pc-metric">v${escape(state.snapshot?.brain?.version || '-')}</div><div class="pc-muted">${escape(state.snapshot?.brain?.state?.name || state.product)}</div></div></div></div></section><section class="pc-section"><h2>Attention</h2><div class="pc-grid pc-rows"><div class="pc-row"><div><div class="pc-metric">${state.snapshot?.attention?.open_workflows || 0}</div><div class="pc-muted">Open workflows</div></div></div><div class="pc-row"><div><div class="pc-metric">${state.snapshot?.attention?.pending_proposals || 0}</div><div class="pc-muted">Pending proposals</div></div></div></div></section></div>`
    }

    function tasks() {
      return `<div class="pc-split"><section>${rows(state.workflows, item => `<button class="pc-row pc-btn" style="width:100%;text-align:left" data-workflow="${escape(item.workflow_id)}"><span class="pc-grow"><span class="pc-title">${escape(item.definition)}</span><span class="pc-muted">${escape(item.workflow_id)}</span></span>${status(item.status)}</button>`)}</section><section class="pc-section"><h2>Workflow detail</h2>${state.workflow ? `<div class="pc-actions"><button class="pc-btn" data-command="retry" data-id="${escape(state.workflow.workflow?.workflow_id || '')}">${c.retry}</button><button class="pc-btn" data-command="cancel" data-id="${escape(state.workflow.workflow?.workflow_id || '')}">${c.cancel}</button>${(state.workflow.provider_tasks || []).map(task => `<button class="pc-btn" data-command="provider" data-id="${escape(task.provider_task_id)}">${c.providerRefresh}</button>`).join('')}</div><pre class="pc-json">${escape(JSON.stringify(state.workflow, null, 2))}</pre>` : '<div class="pc-empty">Select a workflow</div>'}</section></div>`
    }

    function assetRow(item) {
      const kind = String(item.type || '')
      const image = kind.includes('image')
      const video = kind.includes('video')
      return `<div class="pc-row">${image ? `<img class="pc-media" data-thumbnail="${escape(item.record_id)}" alt="">` : `<div class="pc-media pc-empty">${video ? 'VIDEO' : 'FILE'}</div>`}<div class="pc-grow"><div class="pc-title">${escape(item.record_id)}</div><div class="pc-muted">${escape(item.relative_path)}</div><div class="pc-muted">${escape(JSON.stringify(item.payload?.provenance || item.payload?.source || {}))}</div></div>${status(item.status || item.type)}<button class="pc-btn" data-media="${escape(item.record_id)}">Open</button></div>`
    }

    function review() {
      return `<section class="pc-section"><h2>Proposals</h2>${rows(state.review?.proposals, item => { const id = idOf(item, 'proposal_id', 'id'); return `<div class="pc-row"><div class="pc-grow"><div class="pc-title">${escape(id)}</div>${status(item.risk_level)}</div><button class="pc-btn" data-proposal="reject" data-id="${escape(id)}">${c.reject}</button><button class="pc-btn pc-primary" data-proposal="accept" data-id="${escape(id)}">${c.accept}</button></div>` })}</section><section class="pc-section" style="margin-top:20px"><h2>Recent results</h2>${rows(state.review?.results, assetRow)}</section>`
    }

    function assets() {
      return `<div class="pc-grid"><section class="pc-section"><h2>Artifacts</h2>${rows(state.assets?.artifacts, assetRow)}</section><section class="pc-section"><h2>Materials</h2>${rows(state.assets?.materials, assetRow)}</section></div>`
    }

    function learning() {
      const current = Number(state.snapshot?.brain?.version || 0)
      return `<div class="pc-grid"><section class="pc-section"><h2>Brain versions</h2>${rows(state.learning?.versions, item => `<div class="pc-row"><div class="pc-grow">Version ${escape(item.version)} ${status(item.change_kind)}</div>${Number(item.version) !== current ? `<button class="pc-btn" data-version="${escape(item.version)}">${c.rollback}</button>` : ''}</div>`)}</section><section class="pc-section"><h2>Rules</h2>${rows(state.learning?.rules, item => { const id = idOf(item, 'rule_id', 'id'); return `<div class="pc-row"><div class="pc-grow"><div class="pc-title">${escape(id)}</div>${status(item.status)}</div>${item.status !== 'revoked' ? `<button class="pc-btn" data-rule="${escape(id)}">${c.revoke}</button>` : ''}</div>` })}</section></div>`
    }

    function render() {
      if (!host.workspaceRoot) { shell.innerHTML = `<div class="pc-empty">${c.noWorkspace}</div>`; return }
      if (state.loading) return
      if (state.error && !state.products.length) { shell.innerHTML = `<div class="pc-error">${escape(state.error)}</div>`; return }
      if (!state.products.length) { shell.innerHTML = `<div class="pc-empty">${c.noProducts}</div>`; return }
      const views = { overview, tasks, review, assets, learning }
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

    async function loadThumbnails() {
      for (const image of shell.querySelectorAll('[data-thumbnail]')) {
        try { const value = await api(`/media/${encodeURIComponent(image.dataset.thumbnail)}/thumbnail`); image.src = value.data_url } catch { image.alt = c.unavailable }
      }
    }

    shell.addEventListener('change', event => {
      const target = event.target
      if (target?.dataset?.change === 'product') { state.product = target.value; state.workflow = null; localStorage.setItem(`product-creative:active:${host.workspaceRoot}`, state.product); void invalidate() }
      if (target?.dataset?.confirmReason !== undefined && state.confirmation) state.confirmation.reason = target.value
    })
    shell.addEventListener('input', event => { if (event.target?.dataset?.confirmReason !== undefined && state.confirmation) state.confirmation.reason = event.target.value })
    shell.addEventListener('click', event => {
      const target = event.target.closest('button')
      if (!target) return
      if (target.dataset.tab) { state.tab = target.dataset.tab; void invalidate() }
      if (target.dataset.action === 'refresh') void invalidate()
      if (target.dataset.action === 'chat') host.continueInChat(`针对产品 ${state.product}，继续审阅并处理当前 Product Creative 状态。`)
      if (target.dataset.action === 'close-confirm') { state.confirmation = null; render() }
      if (target.dataset.action === 'confirm' && state.confirmation) {
        if (!state.confirmation.reason.trim()) { state.error = c.reasonRequired; render() }
        else void mutate(state.confirmation.title, state.confirmation.path, state.confirmation.body, true)
      }
      if (target.dataset.workflow) void api(`/workflows/${encodeURIComponent(target.dataset.workflow)}`).then(value => { state.workflow = value; render() }).catch(cause => { state.error = String(cause); render() })
      const version = Number(state.snapshot?.brain?.version || 0)
      if (target.dataset.proposal) void mutate(target.dataset.proposal === 'accept' ? c.accept : c.reject, `/proposals/${encodeURIComponent(target.dataset.id)}/decision`, { product_id: state.product, decision: target.dataset.proposal, expected_version: version }, false)
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
