import { afterEach, describe, expect, it } from 'vitest'

import {
  APP_ROUTES,
  appViewForPath,
  isReservedAppPath,
  routeSessionId,
  setDesktopPluginPaths,
  shouldDeferUnknownRouteForDesktopPlugins
} from './routes'

describe('Desktop host routes', () => {
  afterEach(() => setDesktopPluginPaths([]))

  it('reserves every static host route and the legacy session route', () => {
    for (const route of APP_ROUTES) {
      expect(isReservedAppPath(route.path)).toBe(true)
      expect(routeSessionId(route.path)).toBeNull()
    }

    expect(isReservedAppPath('/sessions/example')).toBe(true)
    expect(routeSessionId('/sessions/example')).toBeNull()
  })

  it('keeps discovered plugin paths out of chat session routing', () => {
    setDesktopPluginPaths(['/product-creative'])

    expect(routeSessionId('/product-creative')).toBeNull()
    expect(appViewForPath('/product-creative')).toBe('desktop-plugin')
    expect(routeSessionId('/ordinary-session')).toBe('ordinary-session')
  })

  it('defers an unknown cold-start path until plugin discovery completes', () => {
    expect(shouldDeferUnknownRouteForDesktopPlugins('/example-plugin', true, false)).toBe(true)
    expect(shouldDeferUnknownRouteForDesktopPlugins('/settings', true, false)).toBe(false)
    expect(shouldDeferUnknownRouteForDesktopPlugins('/example-plugin', true, true)).toBe(false)
    expect(shouldDeferUnknownRouteForDesktopPlugins('/ordinary-session', false, false)).toBe(false)
  })
})
