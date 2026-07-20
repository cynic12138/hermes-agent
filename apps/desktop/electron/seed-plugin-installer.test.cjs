'use strict'

const assert = require('node:assert/strict')
const crypto = require('node:crypto')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')
const test = require('node:test')

const { hashPayload } = require('../scripts/stage-seed-plugins.cjs')
const { installSeedPlugins } = require('./seed-plugin-installer.cjs')

function makeSandbox() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-seed-install-'))
  const seedRoot = path.join(root, 'resources', 'seed-plugins')
  const hermesHome = path.join(root, 'hermes-home')
  const activeRoot = path.join(hermesHome, 'hermes-agent')
  fs.mkdirSync(seedRoot, { recursive: true })
  fs.mkdirSync(activeRoot, { recursive: true })
  return { root, seedRoot, hermesHome, activeRoot }
}

function writeSeed(seedRoot, options = {}) {
  const name = options.name || 'fixture_plugin'
  const version = options.version || '1.2.3'
  const pluginRoot = path.join(seedRoot, name)
  const bundle = path.join(pluginRoot, 'dashboard', 'dist', 'desktop.js')
  fs.mkdirSync(path.dirname(bundle), { recursive: true })
  fs.writeFileSync(path.join(pluginRoot, 'plugin.yaml'), `name: ${name}\nversion: ${version}\n`, 'utf8')
  fs.writeFileSync(
    path.join(pluginRoot, 'dashboard', 'manifest.json'),
    JSON.stringify({ name, version }),
    'utf8'
  )
  fs.writeFileSync(bundle, 'window.fixture = true\n', 'utf8')
  const source = {
    source_repository: 'owner/repository',
    source_commit: 'b'.repeat(40),
    plugin_version: version,
    desktop_sdk_version: 1,
    desktop_bundle_sha256: crypto.createHash('sha256').update(fs.readFileSync(bundle)).digest('hex'),
    payload_sha256: hashPayload(pluginRoot)
  }
  fs.writeFileSync(path.join(pluginRoot, 'SOURCE.json'), JSON.stringify(source), 'utf8')
  const entry = {
    name,
    version,
    path: name,
    payloadSha256: source.payload_sha256,
    desktopSdkVersion: 1,
    sourceRepository: source.source_repository,
    sourceCommit: source.source_commit
  }
  fs.writeFileSync(
    path.join(seedRoot, 'manifest.json'),
    JSON.stringify({ schemaVersion: 1, plugins: [entry] }),
    'utf8'
  )
  return { pluginRoot, entry }
}

test('missing packaged seed manifest is a no-op', async () => {
  const { root, seedRoot, hermesHome, activeRoot } = makeSandbox()
  try {
    const result = await installSeedPlugins({ seedRoot, hermesHome, activeRoot })
    assert.deepEqual(result, { skipped: true, plugins: [] })
  } finally {
    fs.rmSync(root, { recursive: true, force: true })
  }
})

test('valid seed installs atomically, enables, and writes a non-secret receipt', async () => {
  const { root, seedRoot, hermesHome, activeRoot } = makeSandbox()
  try {
    const { entry } = writeSeed(seedRoot)
    const enabled = []
    const result = await installSeedPlugins({
      seedRoot,
      hermesHome,
      activeRoot,
      enablePlugin: async args => enabled.push(args.name)
    })

    assert.deepEqual(enabled, ['fixture_plugin'])
    assert.deepEqual(result.plugins, [{ name: 'fixture_plugin', state: 'installed' }])
    assert.equal(fs.existsSync(path.join(hermesHome, 'plugins', 'fixture_plugin', 'plugin.yaml')), true)
    const receipt = JSON.parse(
      fs.readFileSync(path.join(hermesHome, 'seed-plugin-receipts', 'fixture_plugin.json'), 'utf8')
    )
    assert.equal(receipt.name, 'fixture_plugin')
    assert.equal(receipt.version, '1.2.3')
    assert.equal(receipt.payloadSha256, entry.payloadSha256)
    assert.equal(receipt.sourceCommit, entry.sourceCommit)
    assert.deepEqual(Object.keys(receipt).sort(), [
      'installedAt', 'name', 'payloadSha256', 'sourceCommit', 'version'
    ])
  } finally {
    fs.rmSync(root, { recursive: true, force: true })
  }
})

test('exact existing payload is idempotent and is enabled again', async () => {
  const { root, seedRoot, hermesHome, activeRoot } = makeSandbox()
  try {
    writeSeed(seedRoot)
    const enabled = []
    const options = {
      seedRoot,
      hermesHome,
      activeRoot,
      enablePlugin: async args => enabled.push(args.name)
    }
    await installSeedPlugins(options)
    const result = await installSeedPlugins(options)

    assert.deepEqual(enabled, ['fixture_plugin', 'fixture_plugin'])
    assert.deepEqual(result.plugins, [{ name: 'fixture_plugin', state: 'existing' }])
  } finally {
    fs.rmSync(root, { recursive: true, force: true })
  }
})

test('different existing plugin is preserved and rejected', async () => {
  const { root, seedRoot, hermesHome, activeRoot } = makeSandbox()
  try {
    writeSeed(seedRoot)
    const existing = path.join(hermesHome, 'plugins', 'fixture_plugin')
    fs.mkdirSync(existing, { recursive: true })
    fs.writeFileSync(path.join(existing, 'user-file.txt'), 'preserve me', 'utf8')

    await assert.rejects(
      installSeedPlugins({ seedRoot, hermesHome, activeRoot, enablePlugin: async () => {} }),
      /different existing plugin/i
    )
    assert.equal(fs.readFileSync(path.join(existing, 'user-file.txt'), 'utf8'), 'preserve me')
  } finally {
    fs.rmSync(root, { recursive: true, force: true })
  }
})

test('enable failure rolls back only a newly installed seed', async () => {
  const { root, seedRoot, hermesHome, activeRoot } = makeSandbox()
  try {
    writeSeed(seedRoot)
    await assert.rejects(
      installSeedPlugins({
        seedRoot,
        hermesHome,
        activeRoot,
        enablePlugin: async () => { throw new Error('enable failed') }
      }),
      /enable failed/
    )
    assert.equal(fs.existsSync(path.join(hermesHome, 'plugins', 'fixture_plugin')), false)
  } finally {
    fs.rmSync(root, { recursive: true, force: true })
  }
})

test('unsafe manifest paths, payload tampering, and identity mismatch fail closed', async () => {
  const mutations = [
    ({ seedRoot }) => {
      const manifestPath = path.join(seedRoot, 'manifest.json')
      const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'))
      manifest.plugins[0].path = '../escape'
      fs.writeFileSync(manifestPath, JSON.stringify(manifest))
    },
    ({ pluginRoot }) => fs.appendFileSync(path.join(pluginRoot, 'dashboard', 'dist', 'desktop.js'), 'tampered'),
    ({ pluginRoot }) => fs.writeFileSync(path.join(pluginRoot, 'plugin.yaml'), 'name: other\nversion: 1.2.3\n')
  ]
  for (const mutate of mutations) {
    const { root, seedRoot, hermesHome, activeRoot } = makeSandbox()
    try {
      const seed = writeSeed(seedRoot)
      mutate({ seedRoot, ...seed })
      await assert.rejects(
        installSeedPlugins({ seedRoot, hermesHome, activeRoot, enablePlugin: async () => {} }),
        /path|hash|identity/i
      )
      assert.equal(fs.existsSync(path.join(hermesHome, 'plugins', 'fixture_plugin')), false)
    } finally {
      fs.rmSync(root, { recursive: true, force: true })
    }
  }
})

test('forbidden sensitive content and oversized payload files are rejected', async () => {
  const mutations = [
    ({ pluginRoot }) => fs.writeFileSync(path.join(pluginRoot, '.env'), 'API_KEY="not-a-real-secret-but-forbidden"\n'),
    ({ pluginRoot }) => fs.writeFileSync(path.join(pluginRoot, 'oversized.txt'), Buffer.alloc(8 * 1024 * 1024 + 1))
  ]
  for (const mutate of mutations) {
    const { root, seedRoot, hermesHome, activeRoot } = makeSandbox()
    try {
      const seed = writeSeed(seedRoot)
      mutate(seed)
      await assert.rejects(
        installSeedPlugins({ seedRoot, hermesHome, activeRoot, enablePlugin: async () => {} }),
        /forbidden|oversized/i
      )
    } finally {
      fs.rmSync(root, { recursive: true, force: true })
    }
  }
})

test('symlinked payload content is rejected before installation', async () => {
  const { root, seedRoot, hermesHome, activeRoot } = makeSandbox()
  try {
    const seed = writeSeed(seedRoot)
    const outside = path.join(root, 'outside')
    fs.mkdirSync(outside)
    fs.symlinkSync(
      outside,
      path.join(seed.pluginRoot, 'linked-directory'),
      process.platform === 'win32' ? 'junction' : 'dir'
    )

    await assert.rejects(
      installSeedPlugins({ seedRoot, hermesHome, activeRoot, enablePlugin: async () => {} }),
      /symlink/i
    )
    assert.equal(fs.existsSync(path.join(hermesHome, 'plugins', 'fixture_plugin')), false)
  } finally {
    fs.rmSync(root, { recursive: true, force: true })
  }
})

test('all packaged payloads validate before the first plugin is installed', async () => {
  const { root, seedRoot, hermesHome, activeRoot } = makeSandbox()
  try {
    const first = writeSeed(seedRoot, { name: 'first_plugin' })
    const second = writeSeed(seedRoot, { name: 'second_plugin' })
    fs.writeFileSync(
      path.join(seedRoot, 'manifest.json'),
      JSON.stringify({ schemaVersion: 1, plugins: [first.entry, second.entry] }),
      'utf8'
    )
    fs.appendFileSync(path.join(second.pluginRoot, 'dashboard', 'dist', 'desktop.js'), 'tampered')

    await assert.rejects(
      installSeedPlugins({ seedRoot, hermesHome, activeRoot, enablePlugin: async () => {} }),
      /hash/i
    )
    assert.equal(fs.existsSync(path.join(hermesHome, 'plugins', 'first_plugin')), false)
  } finally {
    fs.rmSync(root, { recursive: true, force: true })
  }
})
