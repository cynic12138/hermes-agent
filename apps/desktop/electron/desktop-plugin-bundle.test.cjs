const assert = require('node:assert/strict')
const crypto = require('node:crypto')
const test = require('node:test')

const { MAX_DESKTOP_PLUGIN_BYTES, validateDesktopPluginBundle } = require('./desktop-plugin-bundle.cjs')

test('accepts a matching Desktop plugin bundle', () => {
  const source = 'window.example = true'
  const sha256 = crypto.createHash('sha256').update(source).digest('hex')
  assert.equal(validateDesktopPluginBundle('example', { api_version: 1, entry: 'dist/desktop.js', name: 'example', source, sha256, version: '1.0.0' }).source, source)
})

test('rejects unsafe or corrupted Desktop plugin bundles', () => {
  const hash = crypto.createHash('sha256').update('x').digest('hex')
  const bundle = { api_version: 1, entry: 'dist/desktop.js', name: 'good', source: 'x', sha256: hash, version: '1.0.0' }
  assert.throws(() => validateDesktopPluginBundle('../bad', { ...bundle, name: '../bad' }))
  assert.throws(() => validateDesktopPluginBundle('good', { ...bundle, api_version: 2 }))
  assert.throws(() => validateDesktopPluginBundle('good', { ...bundle, entry: '../desktop.js' }))
  assert.throws(() => validateDesktopPluginBundle('good', { ...bundle, entry: 'dist/desktop.txt' }))
  assert.throws(() => validateDesktopPluginBundle('good', { ...bundle, version: 'not-semver' }))
  assert.throws(() => validateDesktopPluginBundle('good', { ...bundle, name: 'other' }))
  assert.throws(() => validateDesktopPluginBundle('good', { ...bundle, sha256: 'bad' }))
  assert.throws(() => validateDesktopPluginBundle('good', { ...bundle, source: 'x'.repeat(MAX_DESKTOP_PLUGIN_BYTES + 1) }))
})
