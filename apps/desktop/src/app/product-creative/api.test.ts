// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { productCreativeApi } from './api'

describe('Product Creative Desktop API adapter', () => {
  const api = vi.fn().mockResolvedValue({ products: [] })

  beforeEach(() => {
    Object.defineProperty(window, 'hermesDesktop', { configurable: true, value: { api } })
    api.mockClear()
  })

  afterEach(() => Reflect.deleteProperty(window, 'hermesDesktop'))

  it('scopes every request to the active workspace header', async () => {
    await productCreativeApi.products('C:\\workspace')

    expect(api).toHaveBeenCalledWith(
      expect.objectContaining({
        headers: { 'X-Hermes-Workspace-Root': 'C:\\workspace' },
        path: '/api/plugins/product_creative/v1/products'
      })
    )
  })

  it('sends recovery mutations only to typed endpoints', async () => {
    await productCreativeApi.mutate('C:\\workspace', '/workflows/wf-1/retry', {
      confirmed: true,
      expected_version: 3
    })

    expect(api).toHaveBeenCalledWith(
      expect.objectContaining({
        body: { confirmed: true, expected_version: 3 },
        method: 'POST',
        path: '/api/plugins/product_creative/v1/workflows/wf-1/retry'
      })
    )
  })
})
