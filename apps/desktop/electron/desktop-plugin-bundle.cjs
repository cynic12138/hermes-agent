const crypto = require('node:crypto')

const MAX_DESKTOP_PLUGIN_BYTES = 2 * 1024 * 1024

function validateDesktopPluginBundle(name, bundle) {
  if (typeof name !== 'string' || !/^[A-Za-z0-9_-]+$/.test(name)) throw new Error('Invalid Desktop plugin name')
  if (bundle?.api_version !== 1) throw new Error('Unsupported Desktop plugin API version')
  if (
    typeof bundle?.entry !== 'string' ||
    !/^[A-Za-z0-9][A-Za-z0-9_./-]*\.m?js$/.test(bundle.entry) ||
    bundle.entry.includes('..') ||
    bundle.entry.includes('//')
  ) {
    throw new Error('Invalid Desktop plugin bundle entry')
  }
  if (typeof bundle?.version !== 'string' || !/^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$/.test(bundle.version)) {
    throw new Error('Invalid Desktop plugin bundle version')
  }
  const source = typeof bundle?.source === 'string' ? bundle.source : ''
  if (!source || Buffer.byteLength(source, 'utf8') > MAX_DESKTOP_PLUGIN_BYTES) {
    throw new Error('Invalid Desktop plugin bundle')
  }
  const digest = crypto.createHash('sha256').update(source, 'utf8').digest('hex')
  if (bundle?.name !== name || digest !== bundle?.sha256) {
    throw new Error('Desktop plugin bundle hash or identity mismatch')
  }
  return bundle
}

module.exports = { MAX_DESKTOP_PLUGIN_BYTES, validateDesktopPluginBundle }
