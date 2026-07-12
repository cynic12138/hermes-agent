import { describe, expect, it } from 'vitest'

import { appViewForPath, PRODUCT_CREATIVE_ROUTE } from '../routes'

describe('Product Creative route', () => {
  it('is a reserved native Desktop page', () => {
    expect(PRODUCT_CREATIVE_ROUTE).toBe('/product-creative')
    expect(appViewForPath(PRODUCT_CREATIVE_ROUTE)).toBe('product-creative')
  })
})
