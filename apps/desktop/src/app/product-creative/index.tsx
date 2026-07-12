import { useStore } from '@nanostores/react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { PageLoader } from '@/components/page-loader'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import { TextTab, TextTabMeta } from '@/components/ui/text-tab'
import { useI18n } from '@/i18n'
import { $currentCwd } from '@/store/session'

import { requestComposerInsert } from '../chat/composer/focus'
import { NEW_CHAT_ROUTE } from '../routes'

import { productCreativeApi, type ProductCreativeAsset, type ProductCreativeWorkflow } from './api'

type Tab = 'overview' | 'tasks' | 'review' | 'assets' | 'learning'
type PendingConfirmation = { title: string; path: string; body: Record<string, unknown>; confirmationId: string }

const COPY = {
  en: {
    title: 'Product Creative',
    overview: 'Overview',
    tasks: 'Tasks',
    review: 'Review queue',
    assets: 'Assets',
    learning: 'Learning',
    continueChat: 'Continue in chat',
    noWorkspace: 'Open a workspace to use Product Creative.',
    noProducts: 'No Product Creative products in this workspace.',
    confirm: 'Confirm recovery action',
    reason: 'Reason for this action',
    apply: 'Confirm',
    reject: 'Reject',
    rollback: 'Rollback',
    revoke: 'Revoke',
    cancel: 'Cancel workflow',
    retry: 'Retry workflow',
    refreshTask: 'Refresh provider task'
  },
  zh: {
    title: '产品创意',
    overview: '概览',
    tasks: '任务',
    review: '审阅队列',
    assets: '素材与结果',
    learning: '学习',
    continueChat: '在聊天中继续',
    noWorkspace: '请先打开一个工作区。',
    noProducts: '当前工作区没有 Product Creative 产品。',
    confirm: '确认恢复操作',
    reason: '填写本次操作原因',
    apply: '确认',
    reject: '拒绝',
    rollback: '回滚',
    revoke: '撤销规则',
    cancel: '取消工作流',
    retry: '重试工作流',
    refreshTask: '刷新 Provider 任务'
  },
  'zh-hant': {
    title: '產品創意',
    overview: '概覽',
    tasks: '任務',
    review: '審閱佇列',
    assets: '素材與結果',
    learning: '學習',
    continueChat: '在聊天中繼續',
    noWorkspace: '請先開啟一個工作區。',
    noProducts: '目前工作區沒有 Product Creative 產品。',
    confirm: '確認恢復操作',
    reason: '填寫本次操作原因',
    apply: '確認',
    reject: '拒絕',
    rollback: '回復',
    revoke: '撤銷規則',
    cancel: '取消工作流',
    retry: '重試工作流',
    refreshTask: '重新整理 Provider 任務'
  },
  ja: {
    title: 'Product Creative',
    overview: '概要',
    tasks: 'タスク',
    review: 'レビュー',
    assets: 'アセット',
    learning: '学習',
    continueChat: 'チャットで続ける',
    noWorkspace: 'ワークスペースを開いてください。',
    noProducts: 'このワークスペースに製品がありません。',
    confirm: '復旧操作を確認',
    reason: '操作理由',
    apply: '確認',
    reject: '却下',
    rollback: 'ロールバック',
    revoke: 'ルール取消',
    cancel: 'ワークフロー取消',
    retry: 'ワークフロー再試行',
    refreshTask: 'Provider タスク更新'
  }
} as const

const text = (value: unknown) => (value === undefined || value === null ? '' : String(value))

const idOf = (value: Record<string, unknown>, ...keys: string[]) =>
  keys.map(key => text(value[key])).find(Boolean) ?? ''

function Status({ value }: { value: unknown }) {
  return (
    <span className="text-[0.6875rem] font-medium uppercase text-(--ui-text-tertiary)">{text(value) || 'unknown'}</span>
  )
}

function Empty({ children }: { children: string }) {
  return (
    <div className="grid min-h-48 place-items-center border-y border-(--ui-stroke-secondary) text-sm text-(--ui-text-tertiary)">
      {children}
    </div>
  )
}

function AssetRows({ records }: { records: ProductCreativeAsset[] }) {
  if (!records.length) {
    return <Empty>No assets</Empty>
  }

  return (
    <div className="divide-y divide-(--ui-stroke-secondary)">
      {records.map(item => (
        <div
          className="grid grid-cols-[1.5rem_minmax(0,1fr)_auto] items-center gap-2 py-2"
          key={`${item.type}:${item.record_id}`}
        >
          <Codicon
            name={item.type.includes('video') ? 'play-circle' : item.type.includes('image') ? 'file-media' : 'file'}
          />
          <div className="min-w-0">
            <div className="truncate text-xs font-medium">{item.record_id}</div>
            <div className="truncate text-[0.6875rem] text-(--ui-text-tertiary)">{item.relative_path}</div>
          </div>
          <Status value={item.status ?? item.type} />
        </div>
      ))}
    </div>
  )
}

export function ProductCreativeView() {
  const { locale } = useI18n()
  const c = COPY[locale]
  const workspace = useStore($currentCwd).trim()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [tab, setTab] = useState<Tab>('overview')
  const [product, setProduct] = useState('')
  const [selectedWorkflow, setSelectedWorkflow] = useState('')
  const [pending, setPending] = useState<PendingConfirmation | null>(null)
  const [reason, setReason] = useState('')
  const [error, setError] = useState('')

  const products = useQuery({
    queryKey: ['product-creative', workspace, 'products'],
    queryFn: () => productCreativeApi.products(workspace),
    enabled: Boolean(workspace),
    refetchInterval: 10_000
  })

  useEffect(() => {
    const available = products.data?.products ?? []

    if (!available.length) {
      setProduct('')

      return
    }

    const remembered = localStorage.getItem(`product-creative:active:${workspace}`) ?? ''

    const next = available.some(item => item.product_id === product)
      ? product
      : available.some(item => item.product_id === remembered)
        ? remembered
        : available[0].product_id

    setProduct(next)
  }, [products.data, product, workspace])
  useEffect(() => {
    if (workspace && product) {
      localStorage.setItem(`product-creative:active:${workspace}`, product)
    }
  }, [workspace, product])

  const snapshot = useQuery({
    queryKey: ['product-creative', workspace, product, 'snapshot'],
    queryFn: () => productCreativeApi.snapshot(workspace, product),
    enabled: Boolean(product),
    refetchInterval: query => ((query.state.data?.attention.open_workflows ?? 0) > 0 ? 2_000 : 10_000)
  })

  const workflows = useQuery({
    queryKey: ['product-creative', workspace, product, 'workflows'],
    queryFn: () => productCreativeApi.workflows(workspace, product),
    enabled: Boolean(product),
    refetchInterval: 2_000
  })

  const review = useQuery({
    queryKey: ['product-creative', workspace, product, 'review'],
    queryFn: () => productCreativeApi.reviewQueue(workspace, product),
    enabled: Boolean(product),
    refetchInterval: 10_000
  })

  const assets = useQuery({
    queryKey: ['product-creative', workspace, product, 'assets'],
    queryFn: () => productCreativeApi.assets(workspace, product),
    enabled: Boolean(product),
    refetchInterval: 10_000
  })

  const learning = useQuery({
    queryKey: ['product-creative', workspace, product, 'learning'],
    queryFn: () => productCreativeApi.learning(workspace, product),
    enabled: Boolean(product),
    refetchInterval: 10_000
  })

  const workflowDetail = useQuery({
    queryKey: ['product-creative', workspace, selectedWorkflow],
    queryFn: () => productCreativeApi.workflow(workspace, selectedWorkflow),
    enabled: Boolean(selectedWorkflow),
    refetchInterval: 2_000
  })

  const loading = products.isLoading || (product && snapshot.isLoading)

  const currentBrainVersion = Number(snapshot.data?.brain.version ?? 0)

  const tabs: Array<[Tab, string, number?]> = [
    ['overview', c.overview],
    ['tasks', c.tasks, workflows.data?.workflows.length],
    ['review', c.review, review.data?.proposals.length],
    ['assets', c.assets, (assets.data?.artifacts.length ?? 0) + (assets.data?.materials.length ?? 0)],
    ['learning', c.learning, learning.data?.rules.length]
  ]

  const beginMutation = async (title: string, path: string, body: Record<string, unknown>) => {
    setError('')

    try {
      await productCreativeApi.mutate(workspace, path, body)
      await queryClient.invalidateQueries({ queryKey: ['product-creative', workspace] })
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : String(cause)

      try {
        const parsed = JSON.parse(message.slice(message.indexOf('{'))) as { output?: { confirmation_id?: string } }
        const confirmationId = parsed.output?.confirmation_id

        if (confirmationId) {
          setPending({ title, path, body, confirmationId })

          return
        }
      } catch {
        /* show original backend error */
      }

      setError(message)
    }
  }

  const confirmMutation = async () => {
    if (!pending) {
      return
    }

    try {
      await productCreativeApi.mutate(workspace, pending.path, {
        ...pending.body,
        confirmed: true,
        confirmation_id: pending.confirmationId,
        reason,
        actor: 'desktop-user'
      })
      setPending(null)
      setReason('')
      await queryClient.invalidateQueries({ queryKey: ['product-creative', workspace] })
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause))
      setPending(null)
    }
  }

  const continueInChat = () => {
    navigate(NEW_CHAT_ROUTE)
    window.setTimeout(() => requestComposerInsert(`针对产品 ${product}，继续审阅并处理当前 Product Creative 状态。`), 0)
  }

  if (!workspace) {
    return <Empty>{c.noWorkspace}</Empty>
  }

  if (loading) {
    return <PageLoader />
  }

  if (!products.data?.products.length) {
    return <Empty>{c.noProducts}</Empty>
  }

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden bg-(--ui-bg-primary)">
      <header className="flex flex-wrap items-center gap-2 border-b border-(--ui-stroke-secondary) px-4 py-2">
        <h1 className="mr-2 text-sm font-semibold">{c.title}</h1>
        <select
          aria-label="Product"
          className="min-w-48 border border-(--ui-stroke-secondary) bg-(--ui-bg-secondary) px-2 py-1 text-xs"
          onChange={event => setProduct(event.target.value)}
          value={product}
        >
          {products.data.products.map(item => (
            <option key={item.product_id}>{item.product_id}</option>
          ))}
        </select>
        <div className="ml-auto flex items-center gap-1">
          <Button
            aria-label="Refresh"
            onClick={() => void queryClient.invalidateQueries({ queryKey: ['product-creative', workspace] })}
            size="icon-xs"
            variant="ghost"
          >
            <Codicon name="refresh" />
          </Button>
          <Button onClick={continueInChat} size="sm" variant="secondary">
            <Codicon name="comment-discussion" />
            {c.continueChat}
          </Button>
        </div>
      </header>
      <nav className="flex gap-3 border-b border-(--ui-stroke-secondary) px-4">
        {tabs.map(([id, label, count]) => (
          <TextTab active={tab === id} key={id} onClick={() => setTab(id)}>
            {label}
            {count !== undefined ? <TextTabMeta>{count}</TextTabMeta> : null}
          </TextTab>
        ))}
      </nav>
      {error ? (
        <div className="border-b border-destructive/30 bg-destructive/10 px-4 py-2 text-xs text-destructive">
          {error}
        </div>
      ) : null}
      <main className="min-h-0 flex-1 overflow-auto px-4 py-3">
        {tab === 'overview' ? (
          <div className="grid gap-5 md:grid-cols-2">
            <section>
              <h2 className="mb-2 text-xs font-semibold uppercase text-(--ui-text-tertiary)">Product Brain</h2>
              <div className="border-y border-(--ui-stroke-secondary) py-3">
                <div className="text-xl font-semibold">v{currentBrainVersion || '-'}</div>
                <div className="mt-1 text-xs text-(--ui-text-tertiary)">
                  {text((snapshot.data?.brain.state as Record<string, unknown> | undefined)?.name) || product}
                </div>
              </div>
            </section>
            <section>
              <h2 className="mb-2 text-xs font-semibold uppercase text-(--ui-text-tertiary)">Attention</h2>
              <div className="grid grid-cols-2 border-y border-(--ui-stroke-secondary) py-3">
                <div>
                  <div className="text-xl font-semibold">{snapshot.data?.attention.open_workflows ?? 0}</div>
                  <div className="text-xs text-(--ui-text-tertiary)">Open workflows</div>
                </div>
                <div>
                  <div className="text-xl font-semibold">{snapshot.data?.attention.pending_proposals ?? 0}</div>
                  <div className="text-xs text-(--ui-text-tertiary)">Pending proposals</div>
                </div>
              </div>
            </section>
          </div>
        ) : null}
        {tab === 'tasks' ? (
          <div className="grid gap-4 lg:grid-cols-[minmax(16rem,0.8fr)_minmax(24rem,1.2fr)]">
            <div className="divide-y divide-(--ui-stroke-secondary) border-y border-(--ui-stroke-secondary)">
              {(workflows.data?.workflows ?? []).map((item: ProductCreativeWorkflow) => (
                <button
                  className="grid w-full grid-cols-[minmax(0,1fr)_auto] gap-2 px-2 py-2 text-left hover:bg-(--ui-bg-secondary)"
                  key={item.workflow_id}
                  onClick={() => setSelectedWorkflow(item.workflow_id)}
                >
                  <span className="min-w-0">
                    <span className="block truncate text-xs font-medium">{item.definition}</span>
                    <span className="block truncate text-[0.6875rem] text-(--ui-text-tertiary)">
                      {item.workflow_id}
                    </span>
                  </span>
                  <Status value={item.status} />
                </button>
              ))}
            </div>
            <WorkflowDetail copy={c} detail={workflowDetail.data} onAction={beginMutation} />
          </div>
        ) : null}
        {tab === 'review' ? (
          <div className="space-y-5">
            <section>
              <h2 className="mb-2 text-xs font-semibold uppercase text-(--ui-text-tertiary)">Proposals</h2>
              <div className="divide-y divide-(--ui-stroke-secondary) border-y border-(--ui-stroke-secondary)">
                {(review.data?.proposals ?? []).map(item => {
                  const id = idOf(item, 'proposal_id', 'id')

                  return (
                    <div className="flex items-center gap-3 py-2" key={id}>
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-xs font-medium">{id}</div>
                        <Status value={item.risk_level} />
                      </div>
                      <Button
                        onClick={() =>
                          void beginMutation(c.reject, `/proposals/${encodeURIComponent(id)}/decision`, {
                            product_id: product,
                            decision: 'reject',
                            expected_version: currentBrainVersion
                          })
                        }
                        size="xs"
                        variant="outline"
                      >
                        {c.reject}
                      </Button>
                      <Button
                        onClick={() =>
                          void beginMutation(c.apply, `/proposals/${encodeURIComponent(id)}/decision`, {
                            product_id: product,
                            decision: 'accept',
                            expected_version: currentBrainVersion
                          })
                        }
                        size="xs"
                      >
                        {c.apply}
                      </Button>
                    </div>
                  )
                })}
              </div>
            </section>
            <section>
              <h2 className="mb-2 text-xs font-semibold uppercase text-(--ui-text-tertiary)">Recent results</h2>
              <AssetRows records={review.data?.results ?? []} />
            </section>
          </div>
        ) : null}
        {tab === 'assets' ? (
          <div className="grid gap-5 lg:grid-cols-2">
            <section>
              <h2 className="mb-2 text-xs font-semibold uppercase text-(--ui-text-tertiary)">Artifacts</h2>
              <AssetRows records={assets.data?.artifacts ?? []} />
            </section>
            <section>
              <h2 className="mb-2 text-xs font-semibold uppercase text-(--ui-text-tertiary)">Materials</h2>
              <AssetRows records={assets.data?.materials ?? []} />
            </section>
          </div>
        ) : null}
        {tab === 'learning' ? (
          <div className="grid gap-5 lg:grid-cols-2">
            <section>
              <h2 className="mb-2 text-xs font-semibold uppercase text-(--ui-text-tertiary)">Brain versions</h2>
              <div className="divide-y divide-(--ui-stroke-secondary) border-y border-(--ui-stroke-secondary)">
                {(learning.data?.versions ?? []).map(item => (
                  <div className="flex items-center gap-2 py-2" key={text(item.brain_version_id)}>
                    <div className="flex-1 text-xs">
                      Version {text(item.version)} <Status value={item.change_kind} />
                    </div>
                    {Number(item.version) !== currentBrainVersion ? (
                      <Button
                        onClick={() =>
                          void beginMutation(c.rollback, `/products/${encodeURIComponent(product)}/brain/rollback`, {
                            target_version: Number(item.version),
                            expected_version: currentBrainVersion
                          })
                        }
                        size="xs"
                        variant="outline"
                      >
                        {c.rollback}
                      </Button>
                    ) : null}
                  </div>
                ))}
              </div>
            </section>
            <section>
              <h2 className="mb-2 text-xs font-semibold uppercase text-(--ui-text-tertiary)">Rules</h2>
              <div className="divide-y divide-(--ui-stroke-secondary) border-y border-(--ui-stroke-secondary)">
                {(learning.data?.rules ?? []).map(item => {
                  const id = idOf(item, 'rule_id', 'id')

                  return (
                    <div className="flex items-center gap-2 py-2" key={id}>
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-xs">{id}</div>
                        <Status value={item.status} />
                      </div>
                      {item.status !== 'revoked' ? (
                        <Button
                          onClick={() =>
                            void beginMutation(c.revoke, `/rules/${encodeURIComponent(id)}/revoke`, {
                              product_id: product
                            })
                          }
                          size="xs"
                          variant="outline"
                        >
                          {c.revoke}
                        </Button>
                      ) : null}
                    </div>
                  )
                })}
              </div>
            </section>
          </div>
        ) : null}
      </main>
      <Dialog
        onOpenChange={open => {
          if (!open) {
            setPending(null)
          }
        }}
        open={Boolean(pending)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{c.confirm}</DialogTitle>
            <DialogDescription>{pending?.title}</DialogDescription>
          </DialogHeader>
          <textarea
            className="min-h-20 resize-y border border-(--ui-stroke-secondary) bg-transparent p-2 text-xs"
            onChange={event => setReason(event.target.value)}
            placeholder={c.reason}
            value={reason}
          />
          <DialogFooter>
            <Button onClick={() => setPending(null)} variant="text">
              {c.cancel}
            </Button>
            <Button disabled={!reason.trim()} onClick={() => void confirmMutation()}>
              {c.apply}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function WorkflowDetail({
  detail,
  copy,
  onAction
}: {
  detail: Record<string, unknown> | undefined
  copy: (typeof COPY)[keyof typeof COPY]
  onAction: (title: string, path: string, body: Record<string, unknown>) => Promise<void>
}) {
  if (!detail) {
    return <Empty>Select a workflow</Empty>
  }

  const workflow = detail.workflow as Record<string, unknown>
  const steps = (detail.steps as Array<Record<string, unknown>>) ?? []
  const tasks = (detail.provider_tasks as Array<Record<string, unknown>>) ?? []

  const id = text(workflow.workflow_id),
    version = Number(workflow.version)

  return (
    <div>
      <div className="mb-3 flex items-center gap-2">
        <div className="min-w-0 flex-1">
          <div className="truncate text-xs font-semibold">{id}</div>
          <Status value={workflow.status} />
        </div>
        <Button
          onClick={() =>
            void onAction(copy.retry, `/workflows/${encodeURIComponent(id)}/retry`, { expected_version: version })
          }
          size="xs"
          variant="outline"
        >
          {copy.retry}
        </Button>
        <Button
          onClick={() =>
            void onAction(copy.cancel, `/workflows/${encodeURIComponent(id)}/cancel`, { expected_version: version })
          }
          size="xs"
          variant="outline"
        >
          {copy.cancel}
        </Button>
      </div>
      <div className="divide-y divide-(--ui-stroke-secondary) border-y border-(--ui-stroke-secondary)">
        {steps.map(step => (
          <div className="grid grid-cols-[2rem_minmax(0,1fr)_auto] gap-2 py-2" key={text(step.step_id)}>
            <span className="text-xs text-(--ui-text-tertiary)">{text(step.position)}</span>
            <span className="truncate text-xs">{text(step.action)}</span>
            <Status value={step.status} />
          </div>
        ))}
      </div>
      {tasks.map(task => (
        <div className="mt-3 flex items-center gap-2" key={text(task.provider_task_id)}>
          <div className="min-w-0 flex-1 text-xs">
            {text(task.provider)} · <Status value={task.status} />
          </div>
          <Button
            onClick={() =>
              void onAction(
                copy.refreshTask,
                `/provider-tasks/${encodeURIComponent(text(task.provider_task_id))}/refresh`,
                { product_id: text(workflow.product_id) }
              )
            }
            size="xs"
            variant="outline"
          >
            {copy.refreshTask}
          </Button>
        </div>
      ))}
    </div>
  )
}
