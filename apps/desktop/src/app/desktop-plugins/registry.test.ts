// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const manifest = (name: string, path = `/${name}`) => ({
  api_version: 1 as const,
  entry: 'dist/desktop.js',
  icon: 'extensions',
  label: name,
  name,
  path,
  position: 'end',
  source: 'user' as const,
  version: '1.0.0'
})

describe('Desktop plugin registry', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    Reflect.deleteProperty(window, 'hermesDesktop')
  })

  const evaluateBundles = () =>
    vi.spyOn(document.head, 'appendChild').mockImplementation(node => {
      window.eval((node as HTMLScriptElement).text)

      return node
    })

  it('loads an enabled plugin and registers its route', async () => {
    const plugin = manifest('example')

    evaluateBundles()

    ;(window as unknown as { hermesDesktop: unknown }).hermesDesktop = {
      desktopPlugins: {
        list: vi.fn().mockResolvedValue({ api_version: 1, plugins: [plugin] }),
        load: vi.fn().mockResolvedValue({
          api_version: 1,
          entry: plugin.entry,
          name: 'example',
          sha256: 'verified-in-main',
          source: "window.__HERMES_DESKTOP_PLUGINS__.registerPage({apiVersion:1,name:'example',mount:function(){}})",
          version: plugin.version
        })
      }
    }

    const registry = await import('./registry')
    await registry.initializeDesktopPlugins()

    expect(registry.desktopPluginForPath('/example')?.name).toBe('example')
    expect(registry.desktopPluginRegistration('example')).toBeDefined()
  })

  it('reserves discovered plugin paths while their bundles are still loading', async () => {
    const plugin = manifest('example')
    let resolveBundle!: (value: { api_version: number; entry: string; name: string; sha256: string; source: string; version: string }) => void
    const bundle = new Promise<{ api_version: number; entry: string; name: string; sha256: string; source: string; version: string }>(resolve => {
      resolveBundle = resolve
    })

    evaluateBundles()
    ;(window as unknown as { hermesDesktop: unknown }).hermesDesktop = {
      desktopPlugins: {
        list: vi.fn().mockResolvedValue({ api_version: 1, plugins: [plugin] }),
        load: vi.fn().mockReturnValue(bundle)
      }
    }

    const registry = await import('./registry')
    const initialization = registry.initializeDesktopPlugins()

    await vi.waitFor(() => expect(registry.desktopPluginForPath('/example')?.name).toBe('example'))
    expect(registry.desktopPluginStatusForPath('/example')).toBe('loading')

    resolveBundle({
      api_version: 1,
      entry: plugin.entry,
      name: 'example',
      sha256: 'verified-in-main',
      source: "window.__HERMES_DESKTOP_PLUGINS__.registerPage({apiVersion:1,name:'example',mount:function(){}})",
      version: plugin.version
    })
    await initialization
    expect(registry.desktopPluginStatusForPath('/example')).toBe('ready')
  })

  it('rejects every built-in route without loading the conflicting bundles', async () => {
    const plugins = [manifest('command', '/command-center'), manifest('starmap', '/starmap')]
    const load = vi.fn()

    ;(window as unknown as { hermesDesktop: unknown }).hermesDesktop = {
      desktopPlugins: {
        list: vi.fn().mockResolvedValue({ api_version: 1, plugins }),
        load
      }
    }

    const registry = await import('./registry')
    await registry.initializeDesktopPlugins()

    expect(load).not.toHaveBeenCalled()
    expect(registry.desktopPluginForPath('/command-center')).toBeUndefined()
    expect(registry.desktopPluginError('command')).toMatch(/reserved/i)
    expect(registry.desktopPluginError('starmap')).toMatch(/reserved/i)
  })

  it('keeps the first duplicate route and reports the rejected plugin', async () => {
    const first = manifest('first', '/same')
    const duplicate = manifest('duplicate', '/same')

    evaluateBundles()

    ;(window as unknown as { hermesDesktop: unknown }).hermesDesktop = {
      desktopPlugins: {
        list: vi.fn().mockResolvedValue({ api_version: 1, plugins: [first, duplicate] }),
        load: vi.fn().mockImplementation((name: string) =>
          Promise.resolve({
            api_version: 1,
            entry: first.entry,
            name,
            sha256: 'verified-in-main',
            source: `window.__HERMES_DESKTOP_PLUGINS__.registerPage({apiVersion:1,name:'${name}',mount:function(){}})`,
            version: first.version
          })
        )
      }
    }

    const registry = await import('./registry')
    await registry.initializeDesktopPlugins()

    expect(registry.desktopPluginForPath('/same')?.name).toBe('first')
    expect(registry.desktopPluginRegistration('first')).toBeDefined()
    expect(registry.desktopPluginRegistration('duplicate')).toBeUndefined()
    expect(registry.desktopPluginError('duplicate')).toContain('Duplicate')
  })

  it('isolates bundle failures and cross-name registrations', async () => {
    const broken = manifest('broken')
    const healthy = manifest('healthy')

    evaluateBundles()
    ;(window as unknown as { hermesDesktop: unknown }).hermesDesktop = {
      desktopPlugins: {
        list: vi.fn().mockResolvedValue({ api_version: 1, plugins: [broken, healthy] }),
        load: vi.fn().mockImplementation((name: string) =>
          Promise.resolve({
            api_version: 1,
            entry: broken.entry,
            name,
            sha256: 'verified-in-main',
            source:
              name === 'broken'
                ? "window.__HERMES_DESKTOP_PLUGINS__.registerPage({apiVersion:1,name:'healthy',mount:function(){}})"
                : "window.__HERMES_DESKTOP_PLUGINS__.registerPage({apiVersion:1,name:'healthy',mount:function(){}})",
            version: broken.version
          })
        )
      }
    }

    const registry = await import('./registry')
    await registry.initializeDesktopPlugins()

    expect(registry.desktopPluginRegistration('broken')).toBeUndefined()
    expect(registry.desktopPluginError('broken')).toContain('must register itself')
    expect(registry.desktopPluginRegistration('healthy')).toBeDefined()
    expect(registry.desktopPluginStatusForPath('/healthy')).toBe('ready')
  })
})
