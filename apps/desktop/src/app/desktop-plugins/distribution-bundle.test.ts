// @vitest-environment jsdom

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { afterEach, expect, it, vi } from 'vitest'

afterEach(() => {
  document.body.innerHTML = ''
  vi.restoreAllMocks()
  vi.resetModules()
  Reflect.deleteProperty(window, 'hermesDesktop')
})

it('loads the release bundle through registry, route, mount, and API host boundaries', async () => {
  const distribution = process.env.PRODUCT_CREATIVE_DISTRIBUTION
  const root = distribution ? resolve(distribution) : resolve(process.cwd(), '../../.hermes/plugins/product_creative')
  const dashboard = JSON.parse(readFileSync(resolve(root, 'dashboard/manifest.json'), 'utf8'))
  const source = readFileSync(
    distribution ? resolve(root, 'dashboard/dist/desktop.js') : resolve(root, 'desktop_ui/index.js'),
    'utf8'
  )
  const plugin = {
    ...dashboard.desktop,
    name: dashboard.name,
    source: 'user' as const,
    version: dashboard.version
  }

  vi.spyOn(document.head, 'appendChild').mockImplementation(node => {
    window.eval((node as HTMLScriptElement).text)
    return node
  })
  const api = vi.fn(async ({ path }: { path: string }) => {
    if (path.endsWith('/products')) return { products: [] }
    throw new Error(`Unexpected API path: ${path}`)
  })
  ;(window as unknown as { hermesDesktop: unknown }).hermesDesktop = {
    api,
    desktopPlugins: {
      list: vi.fn(async () => ({ api_version: 1, plugins: [plugin] })),
      load: vi.fn(async () => ({
        api_version: 1,
        entry: plugin.entry,
        name: plugin.name,
        sha256: 'validated-by-main-process',
        source,
        version: plugin.version
      }))
    },
    normalizePreviewTarget: vi.fn(),
    notify: vi.fn()
  }

  const registry = await import('./registry')
  await registry.initializeDesktopPlugins()
  expect(registry.desktopPluginForPath('/product-creative')?.name).toBe('product_creative')
  expect(registry.desktopPluginStatusForPath('/product-creative')).toBe('ready')

  const rootElement = document.createElement('div')
  document.body.appendChild(rootElement)
  const cleanup = registry.desktopPluginRegistration('product_creative')?.mount(rootElement, {
    api: async <T,>(path: string, options?: { body?: unknown; method?: string }) =>
      (await api({ path, ...options })) as T,
    continueInChat: vi.fn(),
    locale: 'en',
    navigate: vi.fn(),
    notify: vi.fn(async () => true),
    previewMedia: vi.fn(async () => undefined),
    workspaceRoot: 'C:/offline-workspace'
  })
  await vi.waitFor(() => expect(rootElement.textContent).toContain('Build your first product understanding'))
  expect(api).toHaveBeenCalledWith(expect.objectContaining({ path: '/api/plugins/product_creative/v1/products' }))
  if (typeof cleanup === 'function') cleanup()
  expect(rootElement.innerHTML).toBe('')
})
