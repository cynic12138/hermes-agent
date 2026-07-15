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
  if (path.endsWith('/review-queue')) return { proposals: [{ proposal_id: 'proposal-1', risk_level: 'high' }], results: [] }
  if (path.endsWith('/assets')) return { artifacts: [{ record_id: 'asset-1', relative_path: 'artifacts/a.png', type: 'file' }], materials: [] }
  if (path.endsWith('/learning')) return { versions: [{ version: 2, change_kind: 'proposal' }, { version: 3, change_kind: 'current' }], rules: [{ rule_id: 'rule-1', status: 'active' }] }
  if (path.includes('/workflows/wf-1')) return { workflow: { workflow_id: 'wf-1', version: 2 }, provider_tasks: [] }

  throw new Error(`Unexpected API path: ${path}`)
}

const defaultApi: HostApi = async path => responseFor(path)

const createHost = (api: HostApi = defaultApi): DesktopPluginHost => ({
  api: api as DesktopPluginHost['api'],
  continueInChat: vi.fn(),
  locale: 'en',
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

    for (const [tab, heading] of [
      ['Tasks', 'Workflow detail'],
      ['Review queue', 'Proposals'],
      ['Assets', 'Artifacts'],
      ['Learning', 'Brain versions'],
      ['Overview', 'Product Brain']
    ]) {
      fireEvent.click(screen.getByRole('button', { name: new RegExp(`^${tab}`) }))
      await screen.findByText(heading)
    }
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
    await screen.findByText('No Product Creative products in this workspace.')

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
})
