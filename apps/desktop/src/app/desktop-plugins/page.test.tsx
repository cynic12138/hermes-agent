// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { DesktopPluginManifest, DesktopPluginRegistration } from './registry'

let locale = 'en'
let workspaceRoot = 'C:/workspace/one'
const navigate = vi.fn()
const registration = vi.fn<() => DesktopPluginRegistration | undefined>()

vi.mock('@nanostores/react', () => ({ useStore: () => workspaceRoot }))
vi.mock('@/i18n', () => ({ useI18n: () => ({ locale }) }))
vi.mock('react-router-dom', () => ({ useNavigate: () => navigate }))
vi.mock('./registry', () => ({ desktopPluginRegistration: () => registration() }))

import { DesktopPluginPage } from './page'

const manifest: DesktopPluginManifest = {
  api_version: 1,
  entry: 'dist/desktop.js',
  icon: 'extensions',
  label: 'Product Creative',
  name: 'product_creative',
  path: '/product-creative',
  position: 'after:artifacts',
  source: 'bundled',
  version: '9.1.0-alpha.1'
}

describe('DesktopPluginPage', () => {
  afterEach(() => {
    cleanup()
    locale = 'en'
    workspaceRoot = 'C:/workspace/one'
    navigate.mockReset()
    registration.mockReset()
  })

  it('shows loading and bundle diagnostics without mounting', () => {
    render(<DesktopPluginPage manifest={manifest} status="loading" />)
    expect(screen.getByRole('status').textContent).toMatch(/loading/i)
    expect(registration).not.toHaveBeenCalled()

    cleanup()
    render(<DesktopPluginPage error="Bundle identity mismatch" manifest={manifest} status="error" />)
    expect(screen.getByRole('alert').textContent).toContain('Bundle identity mismatch')
    expect(registration).not.toHaveBeenCalled()
  })

  it('isolates mount failures as a diagnostic error', () => {
    registration.mockReturnValue({
      apiVersion: 1,
      mount: () => {
        throw new Error('mount exploded')
      },
      name: manifest.name
    })

    render(<DesktopPluginPage manifest={manifest} status="ready" />)

    expect(screen.getByRole('alert').textContent).toContain('mount exploded')
  })

  it('cleans up before remounting for locale or workspace changes', () => {
    const cleanupMount = vi.fn()
    const mount = vi.fn(() => cleanupMount)
    registration.mockReturnValue({ apiVersion: 1, mount, name: manifest.name })

    const rendered = render(<DesktopPluginPage manifest={manifest} status="ready" />)
    expect(mount).toHaveBeenLastCalledWith(
      expect.any(HTMLElement),
      expect.objectContaining({ locale: 'en', workspaceRoot: 'C:/workspace/one' })
    )

    locale = 'zh-CN'
    workspaceRoot = 'C:/workspace/two'
    rendered.rerender(<DesktopPluginPage manifest={{ ...manifest }} status="ready" />)

    expect(cleanupMount).toHaveBeenCalledTimes(1)
    expect(mount).toHaveBeenLastCalledWith(
      expect.any(HTMLElement),
      expect.objectContaining({ locale: 'zh-CN', workspaceRoot: 'C:/workspace/two' })
    )
  })

  it('binds API calls to the current workspace after a switch', async () => {
    const api = vi.fn<(request: { headers?: Record<string, string> }) => Promise<unknown>>(async () => ({ ok: true }))
    ;(window as unknown as { hermesDesktop: unknown }).hermesDesktop = {
      api,
      normalizePreviewTarget: vi.fn(),
      notify: vi.fn()
    }
    const hosts: Array<{ api: (path: string) => Promise<unknown> }> = []
    registration.mockReturnValue({
      apiVersion: 1,
      mount: (_root, host) => {
        hosts.push(host)
      },
      name: manifest.name
    })

    const rendered = render(<DesktopPluginPage manifest={manifest} status="ready" />)
    await hosts[0].api('/api/plugins/product_creative/v1/products')

    workspaceRoot = 'C:/workspace/two'
    rendered.rerender(<DesktopPluginPage manifest={{ ...manifest }} status="ready" />)
    await hosts[1].api('/api/plugins/product_creative/v1/products')

    expect(api.mock.calls[0][0]).toMatchObject({ headers: { 'X-Hermes-Workspace-Root': 'C:/workspace/one' } })
    expect(api.mock.calls[1][0]).toMatchObject({ headers: { 'X-Hermes-Workspace-Root': 'C:/workspace/two' } })
  })

  it('contains cleanup failures inside the plugin page', () => {
    registration.mockReturnValue({
      apiVersion: 1,
      mount: () => () => {
        throw new Error('cleanup exploded')
      },
      name: manifest.name
    })

    const rendered = render(<DesktopPluginPage manifest={manifest} status="ready" />)
    expect(() => rendered.unmount()).not.toThrow()
  })
})
