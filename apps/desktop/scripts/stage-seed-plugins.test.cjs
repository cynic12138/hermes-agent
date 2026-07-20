'use strict'

const assert = require('node:assert/strict')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')
const test = require('node:test')

const {
  hashPayload,
  stageSeedPlugins
} = require('./stage-seed-plugins.cjs')

function makeSandbox() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-seed-stage-'))
  const desktopRoot = path.join(root, 'apps', 'desktop')
  fs.mkdirSync(desktopRoot, { recursive: true })
  return { root, desktopRoot }
}

function writeConfig(desktopRoot, overrides = {}) {
  const config = {
    schemaVersion: 1,
    plugins: [
      {
        name: 'fixture_plugin',
        version: '1.2.3',
        exporter: '../../fixture/export_distribution.py',
        ...overrides
      }
    ]
  }
  const configPath = path.join(desktopRoot, 'seed-plugins.json')
  fs.writeFileSync(configPath, JSON.stringify(config), 'utf8')
  return configPath
}

function successfulExporter({ outputDirectory, plugin }) {
  fs.mkdirSync(path.join(outputDirectory, 'dashboard', 'dist'), { recursive: true })
  fs.writeFileSync(
    path.join(outputDirectory, 'plugin.yaml'),
    `name: ${plugin.name}\nversion: ${plugin.version}\n`,
    'utf8'
  )
  fs.writeFileSync(path.join(outputDirectory, 'dashboard', 'dist', 'desktop.js'), 'bundle\n', 'utf8')
  const source = {
    source_repository: 'owner/repository',
    source_commit: 'a'.repeat(40),
    plugin_version: plugin.version,
    desktop_sdk_version: 1,
    desktop_bundle_sha256: 'unused-by-stager',
    payload_sha256: hashPayload(outputDirectory)
  }
  fs.writeFileSync(
    path.join(outputDirectory, 'SOURCE.json'),
    JSON.stringify(source),
    'utf8'
  )
}

test('payload hashing sorts by relative path and excludes SOURCE.json', () => {
  const { root } = makeSandbox()
  try {
    const payload = path.join(root, 'payload')
    fs.mkdirSync(path.join(payload, 'nested'), { recursive: true })
    fs.writeFileSync(path.join(payload, 'z.txt'), 'z', 'utf8')
    fs.writeFileSync(path.join(payload, 'nested', 'a.txt'), 'a', 'utf8')
    fs.writeFileSync(path.join(payload, 'SOURCE.json'), '{"ignored":true}', 'utf8')

    assert.equal(
      hashPayload(payload),
      'eae96be9b6c615fe5245d63b90a0e5adb829c59e538672ae03c7dc7199badb3b'
    )
  } finally {
    fs.rmSync(root, { recursive: true, force: true })
  }
})

test('stages a validated declarative plugin and writes the package manifest', () => {
  const { root, desktopRoot } = makeSandbox()
  try {
    const configPath = writeConfig(desktopRoot)
    const manifest = stageSeedPlugins({
      desktopRoot,
      repoRoot: root,
      configPath,
      runExporter: successfulExporter
    })

    assert.equal(manifest.schemaVersion, 1)
    assert.deepEqual(manifest.plugins, [
      {
        name: 'fixture_plugin',
        version: '1.2.3',
        path: 'fixture_plugin',
        payloadSha256: manifest.plugins[0].payloadSha256,
        desktopSdkVersion: 1,
        sourceRepository: 'owner/repository',
        sourceCommit: 'a'.repeat(40)
      }
    ])
    assert.equal(
      manifest.plugins[0].payloadSha256,
      hashPayload(path.join(desktopRoot, 'build', 'seed-plugins', 'fixture_plugin'))
    )
    assert.deepEqual(
      JSON.parse(
        fs.readFileSync(path.join(desktopRoot, 'build', 'seed-plugins', 'manifest.json'), 'utf8')
      ),
      manifest
    )
  } finally {
    fs.rmSync(root, { recursive: true, force: true })
  }
})

test('rejects unsafe plugin names and exporter paths before export', () => {
  for (const overrides of [
    { name: '../escape' },
    { exporter: '../../../outside.py' }
  ]) {
    const { root, desktopRoot } = makeSandbox()
    try {
      const configPath = writeConfig(desktopRoot, overrides)
      assert.throws(
        () => stageSeedPlugins({ desktopRoot, repoRoot: root, configPath, runExporter: successfulExporter }),
        /unsafe|outside/i
      )
    } finally {
      fs.rmSync(root, { recursive: true, force: true })
    }
  }
})

test('fails closed when exported identity or payload hash differs', () => {
  const cases = [
    ({ outputDirectory, plugin }) => {
      successfulExporter({ outputDirectory, plugin })
      fs.writeFileSync(path.join(outputDirectory, 'plugin.yaml'), 'name: another\nversion: 1.2.3\n')
    },
    ({ outputDirectory, plugin }) => {
      successfulExporter({ outputDirectory, plugin })
      fs.appendFileSync(path.join(outputDirectory, 'dashboard', 'dist', 'desktop.js'), 'tampered\n')
    }
  ]

  for (const runExporter of cases) {
    const { root, desktopRoot } = makeSandbox()
    try {
      const configPath = writeConfig(desktopRoot)
      assert.throws(
        () => stageSeedPlugins({ desktopRoot, repoRoot: root, configPath, runExporter }),
        /identity|hash/i
      )
    } finally {
      fs.rmSync(root, { recursive: true, force: true })
    }
  }
})

test('propagates exporter failure and does not write a package manifest', () => {
  const { root, desktopRoot } = makeSandbox()
  try {
    const configPath = writeConfig(desktopRoot)
    assert.throws(
      () => stageSeedPlugins({
        desktopRoot,
        repoRoot: root,
        configPath,
        runExporter: () => { throw new Error('export failed') }
      }),
      /export failed/
    )
    assert.equal(
      fs.existsSync(path.join(desktopRoot, 'build', 'seed-plugins', 'manifest.json')),
      false
    )
  } finally {
    fs.rmSync(root, { recursive: true, force: true })
  }
})
