// @vitest-environment jsdom

import { fireEvent, screen, waitFor } from '@testing-library/dom'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { DesktopPluginHost, DesktopPluginRegistration } from './registry'

const source = readFileSync(
  resolve(process.cwd(), '../../.hermes/plugins/product_creative/desktop_ui/index.js'),
  'utf8'
)

const product = 'demo-product'
let registration: DesktopPluginRegistration
let cleanupMount: (() => void) | undefined

type HostApi = (path: string, options?: { body?: unknown; method?: string }) => Promise<unknown>

const responseFor = (path: string) => {
  if (path.endsWith('/products')) return { products: [{ product_id: product }] }
  if (path.endsWith('/snapshot')) {
    return { brain: { version: 3, state: { name: 'Demo Product' } }, attention: { open_workflows: 1, pending_proposals: 1 } }
  }
  if (path.endsWith('/workflows')) return { workflows: [{ workflow_id: 'wf-1', definition: 'Create image', status: 'waiting_review' }] }
  if (path.endsWith('/creative-tasks')) {
    return {
      creative_tasks: [{
        task_id: 'task-1', status: 'NEEDS_INPUT', current_stage: 'UNDERSTANDING',
        request: { raw_message: 'Create today product video', autonomy_mode: 'adaptive' },
        readiness: { ready: false, blockers: ['Current packaging is missing'], questions: [{ field_key: 'current_packaging', prompt: 'Which packaging is current?' }] },
        plan: { artifact_gates: ['creative_task_brief', 'preflight_qa'], actions: [] }, result_descriptors: [], selected_materials: [],
        professional_artifact_status: 'complete',
        professional_summary: {
          grounding: { readiness_status: 'READY', blockers: [] },
          decision: { selected_candidate_id: 'candidate-stable', selection_reason: 'Stable route wins.' },
          qa: { gate_result: 'PASS', blockers: [], warnings: ['Offline research fallback'] },
          media: { dependency_status: 'READY', shots_completed: 1, shots_total: 2, current_failure: '', plan_id: 'media-plan-1', composite_manifest_id: '', qa_result: 'HUMAN_REVIEW', qa_report_id: 'media-qa-1', qa_failed_shot_ids: [], qa_hard_blockers: ['visual-continuity uncertain'] }
        }
      }]
    }
  }
  if (path.includes('/creative-tasks/task-1')) {
    return {
      task_id: 'task-1', status: 'NEEDS_INPUT', current_stage: 'UNDERSTANDING', blocked_reason: 'Current packaging is missing',
      request: { raw_message: 'Create today product video', autonomy_mode: 'adaptive' },
      readiness: { ready: false }, plan: { artifact_gates: ['creative_task_brief', 'product_grounding_pack', 'creative_candidates', 'creative_decision', 'story_package', 'production_bible', 'preflight_qa'], actions: [{ action: 'prepare_task_material_pack', stage: 'PREPARING_ASSETS', status: 'PENDING' }] },
      result_descriptors: [], selected_materials: [{ material_id: 'main-1', role: 'current_main_image' }],
      professional_artifact_status: 'complete',
      professional_artifacts: {
        creative_task_brief: 'brief-1', product_grounding_pack: 'grounding-1',
        creative_candidates: ['candidate-stable', 'candidate-variation', 'candidate-exploration'],
        creative_decision: 'decision-1', story_package: 'story-1',
        production_bible: 'bible-1', qa_report: 'qa-1',
        skill_executions: ['skill-exec-strategy', 'skill-exec-review'],
        media_dependency_report: 'media-deps-1', product_plate: 'plate-1',
        media_execution_plan: 'media-plan-1', media_shot_results: ['shot-result-1'],
        media_composite_manifest: 'manifest-1',
        media_qa_report: 'media-qa-1',
        media_repair_decision: 'media-repair-1'
      },
      professional_summary: {
        grounding: { readiness_status: 'READY', blockers: [] },
        decision: { selected_candidate_id: 'candidate-stable', selection_reason: 'Stable route wins.' },
        qa: { gate_result: 'PASS', blockers: [], warnings: ['Offline research fallback'] },
        media: { dependency_status: 'READY', shots_completed: 1, shots_total: 2, current_failure: '', plan_id: 'media-plan-1', composite_manifest_id: 'manifest-1', product_plate_id: 'plate-1', output_relative_path: 'artifacts/generated_videos/final.mp4', qa_result: 'HUMAN_REVIEW', qa_report_id: 'media-qa-1', qa_failed_shot_ids: [], qa_hard_blockers: ['visual-continuity uncertain'], repair_decision: 'HUMAN_REVIEW', repair_round: 1 }
      },
      professional_artifact_details: {
        creative_candidates: [
          { artifact_id: 'candidate-stable', direction: 'stable', one_liner: 'Stable route', hook: 'A concrete three-second hook.', historical_similarity: 0.21, novelty_strategy: 'Change the action mechanism.' },
          { artifact_id: 'candidate-variation', direction: 'variation', one_liner: 'Variation route', hook: 'Objects compete for the final bag slot.', historical_similarity: 0.38, novelty_strategy: 'Change the conflict owner.' },
          { artifact_id: 'candidate-exploration', direction: 'exploration', one_liner: 'Exploration route', hook: 'A message arrives from one minute later.', historical_similarity: 0.12, novelty_strategy: 'Use a time-loop structure.' }
        ],
        skill_executions: [
          { artifact_id: 'skill-exec-strategy', skill_name: 'creative-strategy', skill_version: '1.0.0', stage: 'creative_strategy', execution_mode: 'llm_structured', execution_status: 'COMPLETED', input_artifacts: [{ artifact_id: 'grounding-1' }] },
          { artifact_id: 'skill-exec-review', skill_name: 'creative-review', skill_version: '1.0.0', stage: 'creative_review', execution_mode: 'llm_structured', execution_status: 'COMPLETED', input_artifacts: [{ artifact_id: 'candidate-stable' }] }
        ],
        creative_decision: { selected_candidate_id: 'candidate-stable', selection_reason: 'Stable route wins.' },
        story_package: { premise: 'A complete product story.', hook_visual: 'The hand freezes at the door.', conflict: 'Time is running out.', turn: 'The product restores calm.', ending: 'Leave calmly.' },
        production_bible: { artifact_id: 'bible-1', packaging_strategy: 'exact-main-composite', shots: [{ shot_id: 'shot-01', duration_seconds: 2, action: 'The hand freezes at the door.' }] },
        qa_report: { gate_result: 'PASS', blockers: [], warnings: ['Offline research fallback'] },
        media_dependency_report: { artifact_id: 'media-deps-1', overall_status: 'READY', blockers: [], warnings: [] },
        product_plate: { artifact_id: 'plate-1', mask_mode: 'source_alpha', plate_relative_path: 'artifacts/product_plates/plate-1.png' },
        media_execution_plan: { artifact_id: 'media-plan-1', production_bible_id: 'bible-1', shots: [{ shot_id: 'shot-01', ordinal: 1 }, { shot_id: 'shot-02', ordinal: 2 }] },
        media_shot_results: [{ artifact_id: 'shot-result-1', shot_id: 'shot-01', execution_status: 'COMPLETED', output_relative_path: 'artifacts/media_shots/shot-01.mp4' }],
        media_composite_manifest: { artifact_id: 'manifest-1', plan_id: 'media-plan-1', output_relative_path: 'artifacts/generated_videos/final.mp4' },
        media_qa_report: { artifact_id: 'media-qa-1', overall_result: 'HUMAN_REVIEW', hard_blockers: ['visual-continuity uncertain'], warnings: [], failed_shot_ids: [], checks: [{ check_id: 'visual-continuity:shot-01:shot-02', shot_id: 'shot-02', scope: 'shot', status: 'UNKNOWN', severity: 'high', observed: { reason: 'no visual adapter' } }] },
        media_repair_decision: { artifact_id: 'media-repair-1', decision: 'HUMAN_REVIEW', repair_round: 1 }
      }
    }
  }
  if (path.endsWith('/review-queue')) return { proposals: [{ proposal_id: 'proposal-1', risk_level: 'high' }], results: [] }
  if (path.endsWith('/assets')) return { artifacts: [{ record_id: 'asset-1', relative_path: 'artifacts/a.png', type: 'file' }], materials: [] }
  if (path.endsWith('/learning')) return { versions: [{ version: 2, change_kind: 'proposal' }, { version: 3, change_kind: 'current' }], rules: [{ rule_id: 'rule-1', status: 'active' }] }
  if (path.endsWith('/diagnostics')) {
    return {
      schema_name: 'product_creative.desktop_diagnostics.v1',
      overall_status: 'ACTION_REQUIRED',
      checks: [
        { id: 'credential-doubao', category: 'model_credentials', label: 'Doubao / Volcengine Ark', status: 'READY', required: true, detail: 'DOUBAO_API_KEY is configured.', action: '', metadata: { configured: true } },
        { id: 'media-ffmpeg', category: 'media_runtime', label: 'ffmpeg', status: 'READY', required: true, detail: 'ffmpeg is available.', action: '', metadata: { available: true } },
        { id: 'sidecar-xhs', category: 'optional_sources', label: 'Xiaohongshu', status: 'OPTIONAL_OFFLINE', required: false, detail: 'Local sidecar is not running.', action: 'start_xhs_sidecar', metadata: { optional: true } },
        { id: 'sidecar-douyin', category: 'optional_sources', label: 'Douyin', status: 'OPTIONAL_OFFLINE', required: false, detail: 'Local sidecar is not running.', action: 'start_douyin_sidecar', metadata: { optional: true } }
      ]
    }
  }
  if (path.includes('/workflows/wf-1')) return { workflow: { workflow_id: 'wf-1', version: 2 }, provider_tasks: [] }

  throw new Error(`Unexpected API path: ${path}`)
}

const defaultApi: HostApi = async path => responseFor(path)

const createHost = (api: HostApi = defaultApi, locale = 'en'): DesktopPluginHost => ({
  api: api as DesktopPluginHost['api'],
  continueInChat: vi.fn(),
  locale,
  navigate: vi.fn(),
  notify: vi.fn(async () => true),
  previewMedia: vi.fn(async () => undefined),
  workspaceRoot: 'C:/workspace'
})

const mount = (host = createHost()) => {
  const root = document.createElement('div')
  document.body.appendChild(root)
  cleanupMount = registration.mount(root, host) || undefined

  return { host, root }
}

beforeEach(() => {
  window.localStorage.clear()
  window.__HERMES_DESKTOP_PLUGINS__ = {
    registerPage(value) {
      registration = value
    }
  }
  window.eval(source)
})

afterEach(() => {
  cleanupMount?.()
  cleanupMount = undefined
  document.body.innerHTML = ''
  vi.restoreAllMocks()
})

describe('Product Creative Desktop bundle', () => {
  it('registers the expected plugin identity and renders all five views', async () => {
    mount()

    expect(registration.apiVersion).toBe(1)
    expect(registration.name).toBe('product_creative')
    await screen.findByText('Product Brain')
    expect(screen.getByText('Product Readiness')).toBeTruthy()
    expect(screen.getByText('Media production')).toBeTruthy()
    expect(screen.getByText('Create today product video')).toBeTruthy()

    for (const [tab, heading] of [
      ['Tasks', 'Creative Tasks'],
      ['Review queue', 'Proposals'],
      ['Assets', 'Artifacts'],
      ['Learning', 'Brain versions'],
      ['Overview', 'Product Brain']
    ]) {
      fireEvent.click(screen.getByRole('button', { name: new RegExp(`^${tab}`) }))
      await screen.findByText(heading)
    }

    fireEvent.click(screen.getByRole('button', { name: /^Tasks/ }))
    await screen.findByText('Creative Tasks')
    fireEvent.click(screen.getByRole('button', { name: /Create today product video/ }))
    await screen.findByText('prepare_task_material_pack')
    expect(screen.getByText('Professional artifact gates')).toBeTruthy()
    expect(screen.getByText('Business Skill executions')).toBeTruthy()
    expect(screen.getByText('creative-strategy')).toBeTruthy()
    expect(screen.getByText('Shot production')).toBeTruthy()
    expect(screen.getByText(/1 \/ 2 shots/)).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /^Review queue/ }))
    await screen.findByText('Creative candidates')
    expect(screen.getByText('Stable route')).toBeTruthy()
    expect(screen.getByText(/History similarity: 0.21/)).toBeTruthy()
    expect(screen.getByText('Skill provenance')).toBeTruthy()
    expect(screen.getByText('Preflight QA')).toBeTruthy()
    expect(screen.getByText('Automatic Media QA')).toBeTruthy()
    expect(screen.getByText('Accept with warning')).toBeTruthy()
    expect(screen.getByText('Media provenance')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /^Assets/ }))
    await screen.findByText('Production Bible')
    expect(screen.getByText('exact-main-composite')).toBeTruthy()
    expect(screen.getByText('Product Plate')).toBeTruthy()
    expect(screen.getByText('Shot outputs')).toBeTruthy()
    expect(screen.getByText('Final composite')).toBeTruthy()
  })

  it('renders loading, empty, and API error states', async () => {
    let resolveProducts: (value: unknown) => void = () => undefined
    const pending = new Promise(resolve => {
      resolveProducts = resolve
    })
    const loadingApi = vi.fn(async (path: string) => (path.endsWith('/products') ? pending : responseFor(path)))
    mount(createHost(loadingApi))
    expect(screen.getByText(/Loading Product Creative/)).toBeTruthy()
    resolveProducts({ products: [] })
    await screen.findByText('Build your first product understanding')

    cleanupMount?.()
    document.body.innerHTML = ''
    const failingApi = vi.fn(async () => {
      throw new Error('backend unavailable')
    })
    mount(createHost(failingApi))
    await screen.findByText(/backend unavailable/)
  })

  it('does not mutate durable state until confirmation and a reason are supplied', async () => {
    const calls: Array<{ body?: unknown; method?: string; path: string }> = []
    const api = vi.fn(async (path: string, options?: { body?: unknown; method?: string }) => {
      calls.push({ path, ...options })
      if (path.includes('/proposals/proposal-1/decision')) {
        const body = options?.body as { confirmed?: boolean } | undefined
        if (!body?.confirmed) {
          throw new Error(JSON.stringify({ output: { confirmation_id: 'confirmation-1' } }))
        }

        return { ok: true, receipt: { event_id: 'event-1' } }
      }

      return responseFor(path)
    })
    mount(createHost(api))
    await screen.findByText('Product Brain')
    fireEvent.click(screen.getByRole('button', { name: /^Review queue/ }))
    await screen.findByText('proposal-1')
    fireEvent.click(screen.getByRole('button', { name: 'Accept' }))
    await waitFor(() => expect(document.querySelector('.pc-risk')?.textContent).toContain('Confirmation and audit are required.'))

    const mutations = () => calls.filter(call => call.path.includes('/proposals/proposal-1/decision'))
    expect(mutations()).toHaveLength(1)
    expect((mutations()[0].body as { confirmed?: boolean }).confirmed).toBeUndefined()

    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))
    expect(mutations()).toHaveLength(1)
    expect(screen.getByText(/reason is required/i)).toBeTruthy()

    fireEvent.input(screen.getByPlaceholderText('Reason for this action'), { target: { value: 'Reviewed by operator' } })
    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))

    await waitFor(() => expect(mutations()).toHaveLength(2))
    expect(mutations()[1].body).toMatchObject({
      actor: 'desktop-user',
      confirmation_id: 'confirmation-1',
      confirmed: true,
      reason: 'Reviewed by operator'
    })
  })

  it('onboards a first product instead of leaving an empty workspace dead-ended', async () => {
    let created = false
    const calls: Array<{ body?: unknown; method?: string; path: string }> = []
    const api = vi.fn(async (path: string, options?: { body?: unknown; method?: string }) => {
      calls.push({ path, ...options })
      if (path.endsWith('/products') && options?.method === 'POST') {
        created = true
        return { created: true, selected_product_id: 'new-product', ingest: { canonical_brain_changed: false } }
      }
      if (path.endsWith('/products')) return { products: created ? [{ product_id: 'new-product' }] : [] }
      if (created) {
        if (path.endsWith('/snapshot')) return { brain: { version: 1, state: { name: 'New Product' } }, attention: {} }
        if (path.endsWith('/workflows')) return { workflows: [] }
        if (path.endsWith('/creative-tasks')) return { creative_tasks: [] }
      }
      return responseFor(path)
    })
    mount(createHost(api, 'zh-CN'))

    await screen.findByText('建立第一个产品认知')
    fireEvent.input(screen.getByLabelText('产品名称'), { target: { value: '新产品' } })
    fireEvent.input(screen.getByLabelText('已有产品描述（可选）'), { target: { value: '这段资料只能先进入待确认理解。' } })
    fireEvent.click(screen.getByRole('button', { name: '创建产品' }))

    await screen.findByText('Product Brain')
    const mutation = calls.find(call => call.path.endsWith('/products') && call.method === 'POST')
    expect(mutation?.body).toMatchObject({ name: '新产品', description: '这段资料只能先进入待确认理解。' })
  })

  it('starts a natural-language goal with product context and no prompt engineering', async () => {
    const { host } = mount()

    await screen.findByText('Product Brain')
    fireEvent.input(screen.getByLabelText('What do you want to create?'), { target: { value: '帮我做一个今天能发的产品视频' } })
    fireEvent.click(screen.getByRole('button', { name: 'Start creative task' }))

    expect(host.continueInChat).toHaveBeenCalledTimes(1)
    expect(host.continueInChat).toHaveBeenCalledWith(expect.stringContaining('帮我做一个今天能发的产品视频'))
    expect(host.continueInChat).toHaveBeenCalledWith(expect.stringContaining('demo-product'))
  })

  it('continues an interrupted task without asking the operator to copy a task id', async () => {
    const { host } = mount()

    await screen.findByText('Product Brain')
    fireEvent.click(screen.getByRole('button', { name: /^Tasks/ }))
    fireEvent.click(await screen.findByRole('button', { name: /Create today product video/ }))
    const continueButton = await screen.findByRole('button', { name: 'Continue task' })
    expect(continueButton.textContent).not.toContain('task-1')
    fireEvent.click(continueButton)

    expect(host.continueInChat).toHaveBeenCalledWith(expect.stringContaining('task-1'))
    expect(host.continueInChat).toHaveBeenCalledWith(expect.stringContaining('continue'))
  })

  it('projects the three operator review checkpoints from existing durable artifacts', async () => {
    mount()

    await screen.findByText('Product truth')
    expect(screen.getByText('Creative direction')).toBeTruthy()
    expect(screen.getByText('Final quality')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /^Review queue/ }))
    await screen.findByText('1. Product truth')
    expect(screen.getByText('2. Creative direction')).toBeTruthy()
    expect(screen.getByText('3. Final quality')).toBeTruthy()
  })

  it('shows required runtime diagnostics while keeping platform sidecars optional', async () => {
    const { host } = mount()

    await screen.findByText('Product Brain')
    fireEvent.click(screen.getByRole('button', { name: /^Settings/ }))
    await screen.findByText('Provider and model credentials')
    expect(screen.getByText('Doubao / Volcengine Ark')).toBeTruthy()
    expect(screen.getByText('Media runtime')).toBeTruthy()
    expect(screen.getByText('Optional inspiration sources')).toBeTruthy()
    expect(screen.getAllByText('OPTIONAL_OFFLINE')).toHaveLength(2)

    fireEvent.click(screen.getByRole('button', { name: 'Open Hermes settings' }))
    expect(host.navigate).toHaveBeenCalledWith('/settings')
  })

  it('remounts against a different workspace without reusing product state', async () => {
    const workspaceApi = (productId: string, name: string): HostApi => async path => {
      if (path.endsWith('/products')) return { products: [{ product_id: productId }] }
      if (path.endsWith('/snapshot')) return { brain: { version: 1, state: { name } }, attention: {} }
      if (path.endsWith('/workflows')) return { workflows: [] }
      if (path.endsWith('/creative-tasks')) return { creative_tasks: [] }
      return responseFor(path)
    }

    const firstHost = { ...createHost(workspaceApi('product-a', 'Workspace A Product')), workspaceRoot: 'C:/workspace-a' }
    mount(firstHost)
    await screen.findByText('Workspace A Product')

    cleanupMount?.()
    cleanupMount = undefined
    document.body.innerHTML = ''

    const secondHost = { ...createHost(workspaceApi('product-b', 'Workspace B Product')), workspaceRoot: 'C:/workspace-b' }
    mount(secondHost)
    await screen.findByText('Workspace B Product')
    expect(screen.queryByText('Workspace A Product')).toBeNull()
    expect(window.localStorage.getItem('product-creative:active:C:/workspace-a')).toBe('product-a')
    expect(window.localStorage.getItem('product-creative:active:C:/workspace-b')).toBe('product-b')
  })

  it('normalizes the Desktop zh-CN locale for operator actions', async () => {
    mount(createHost(defaultApi, 'zh-CN'))

    await screen.findByText('产品事实')
    expect(screen.getByRole('button', { name: /^概览/ })).toBeTruthy()
    expect(screen.getByRole('button', { name: '制作今日产品视频' })).toBeTruthy()
    expect(screen.getByLabelText('你希望这次创作什么？')).toBeTruthy()
    expect(screen.getByRole('button', { name: /^设置/ })).toBeTruthy()
  })

  it('disables old timers and event handlers after mount cleanup', async () => {
    const clearTimeoutSpy = vi.spyOn(globalThis, 'clearTimeout')
    const { host, root } = mount()

    await screen.findByText('Product Brain')
    fireEvent.input(screen.getByLabelText('What do you want to create?'), { target: { value: 'Create a safe draft' } })
    const oldStartButton = screen.getByRole('button', { name: 'Start creative task' })

    cleanupMount?.()
    cleanupMount = undefined
    expect(root.innerHTML).toBe('')
    expect(clearTimeoutSpy).toHaveBeenCalled()

    fireEvent.click(oldStartButton)
    expect(host.continueInChat).not.toHaveBeenCalled()
  })
})
