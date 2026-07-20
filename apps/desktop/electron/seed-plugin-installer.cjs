'use strict'

const crypto = require('node:crypto')
const fs = require('node:fs')
const path = require('node:path')
const { spawnSync } = require('node:child_process')
const { hashPayload, validatePayloadSafety } = require('./seed-plugin-contract.cjs')

const NAME_RE = /^[a-z][a-z0-9_]{0,63}$/
const VERSION_RE = /^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$/
const HASH_RE = /^[0-9a-f]{64}$/
const COMMIT_RE = /^[0-9a-f]{7,40}$/i

function isWithin(candidate, parent) {
  const relative = path.relative(path.resolve(parent), path.resolve(candidate))
  return relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative))
}

function readJson(filePath, label) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'))
  } catch (error) {
    throw new Error(`Invalid ${label} JSON at ${filePath}: ${error.message}`)
  }
}

function readPluginIdentity(pluginRoot) {
  const text = fs.readFileSync(path.join(pluginRoot, 'plugin.yaml'), 'utf8')
  return {
    name: text.match(/^name:\s*([^\s]+)\s*$/m)?.[1] || '',
    version: text.match(/^version:\s*([^\s]+)\s*$/m)?.[1] || ''
  }
}

function validateEntry(entry) {
  if (!entry || typeof entry !== 'object') throw new Error('Seed manifest plugin entry must be an object')
  if (!NAME_RE.test(entry.name || '')) throw new Error(`Seed plugin has unsafe name: ${entry.name || '<missing>'}`)
  if (!VERSION_RE.test(entry.version || '')) throw new Error(`Seed plugin has unsafe version: ${entry.version || '<missing>'}`)
  if (entry.path !== entry.name) throw new Error(`Seed plugin has unsafe path: ${entry.name}`)
  if (!HASH_RE.test(entry.payloadSha256 || '')) throw new Error(`Seed plugin has invalid payload hash: ${entry.name}`)
  if (entry.desktopSdkVersion !== 1) throw new Error(`Seed plugin has unsupported Desktop SDK: ${entry.name}`)
  if (!COMMIT_RE.test(entry.sourceCommit || '')) throw new Error(`Seed plugin has invalid source commit: ${entry.name}`)
  if (typeof entry.sourceRepository !== 'string' || !/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(entry.sourceRepository)) {
    throw new Error(`Seed plugin has invalid source repository: ${entry.name}`)
  }
}

function validatePayload(seedRoot, entry) {
  validateEntry(entry)
  const pluginRoot = path.resolve(seedRoot, entry.path)
  if (!isWithin(pluginRoot, seedRoot) || pluginRoot === path.resolve(seedRoot)) {
    throw new Error(`Seed plugin path escapes package root: ${entry.name}`)
  }
  const rootStat = fs.lstatSync(pluginRoot)
  if (!rootStat.isDirectory() || rootStat.isSymbolicLink()) throw new Error(`Seed plugin path is not a safe directory: ${entry.name}`)
  validatePayloadSafety(pluginRoot)

  const identity = readPluginIdentity(pluginRoot)
  if (identity.name !== entry.name || identity.version !== entry.version) {
    throw new Error(`Seed plugin identity mismatch: ${entry.name}`)
  }
  const dashboard = readJson(path.join(pluginRoot, 'dashboard', 'manifest.json'), `${entry.name} dashboard manifest`)
  if (dashboard.name !== entry.name || dashboard.version !== entry.version) {
    throw new Error(`Seed plugin dashboard identity mismatch: ${entry.name}`)
  }
  const source = readJson(path.join(pluginRoot, 'SOURCE.json'), `${entry.name} SOURCE`)
  if (
    source.plugin_version !== entry.version ||
    source.desktop_sdk_version !== entry.desktopSdkVersion ||
    source.source_repository !== entry.sourceRepository ||
    source.source_commit !== entry.sourceCommit ||
    source.payload_sha256 !== entry.payloadSha256
  ) {
    throw new Error(`Seed plugin source identity mismatch: ${entry.name}`)
  }
  const actualPayloadHash = hashPayload(pluginRoot)
  if (actualPayloadHash !== entry.payloadSha256) throw new Error(`Seed plugin payload hash mismatch: ${entry.name}`)
  const bundlePath = path.join(pluginRoot, 'dashboard', 'dist', 'desktop.js')
  const bundleHash = crypto.createHash('sha256').update(fs.readFileSync(bundlePath)).digest('hex')
  if (bundleHash !== source.desktop_bundle_sha256) throw new Error(`Seed plugin Desktop bundle hash mismatch: ${entry.name}`)
  return pluginRoot
}

async function defaultEnablePlugin({ name, activeRoot, hermesHome }) {
  const python = path.join(
    activeRoot,
    'venv',
    process.platform === 'win32' ? path.join('Scripts', 'python.exe') : path.join('bin', 'python')
  )
  if (!fs.existsSync(python)) throw new Error(`Hermes runtime Python is missing: ${python}`)
  const existingPythonPath = process.env.PYTHONPATH
  const env = {
    ...process.env,
    HERMES_HOME: hermesHome,
    PYTHONPATH: existingPythonPath ? `${activeRoot}${path.delimiter}${existingPythonPath}` : activeRoot
  }
  const result = spawnSync(
    python,
    ['-m', 'hermes_cli.main', 'plugins', 'enable', name, '--no-allow-tool-override'],
    { cwd: activeRoot, env, encoding: 'utf8', windowsHide: process.platform === 'win32' }
  )
  if (result.error) throw result.error
  if (result.status !== 0) {
    throw new Error(`Hermes failed to enable seed plugin ${name}: ${(result.stderr || result.stdout || '').trim()}`)
  }
}

function writeReceipt(hermesHome, entry) {
  const receiptRoot = path.join(hermesHome, 'seed-plugin-receipts')
  fs.mkdirSync(receiptRoot, { recursive: true })
  const payload = {
    name: entry.name,
    version: entry.version,
    payloadSha256: entry.payloadSha256,
    sourceCommit: entry.sourceCommit,
    installedAt: new Date().toISOString()
  }
  fs.writeFileSync(path.join(receiptRoot, `${entry.name}.json`), JSON.stringify(payload, null, 2) + '\n', 'utf8')
}

async function installSeedPlugins(options) {
  const { seedRoot, hermesHome, activeRoot } = options
  const enablePlugin = options.enablePlugin || defaultEnablePlugin
  const emit = typeof options.emit === 'function' ? options.emit : () => {}
  const validated = validatePackagedSeedPlugins(seedRoot, { required: false })
  if (!validated) return { skipped: true, plugins: [] }

  const { plugins: validatedPlugins } = validated
  const pluginRoot = path.join(hermesHome, 'plugins')
  fs.mkdirSync(pluginRoot, { recursive: true })
  const results = []
  for (const { entry, packagedRoot } of validatedPlugins) {
    emit({ type: 'log', stage: 'desktop-seed-plugins', line: `[seed-plugin] validating ${entry.name}@${entry.version}` })
    const destination = path.join(pluginRoot, entry.name)
    let installedNow = false
    if (fs.existsSync(destination)) {
      let existingHash = null
      try {
        existingHash = hashPayload(destination)
      } catch {
        existingHash = null
      }
      if (existingHash !== entry.payloadSha256) {
        throw new Error(`Refusing to overwrite different existing plugin: ${entry.name}`)
      }
    } else {
      const temp = path.join(pluginRoot, `.${entry.name}.seed-${process.pid}-${crypto.randomBytes(6).toString('hex')}`)
      try {
        fs.cpSync(packagedRoot, temp, { recursive: true, dereference: false, errorOnExist: true, force: false })
        if (hashPayload(temp) !== entry.payloadSha256) throw new Error(`Copied seed plugin hash mismatch: ${entry.name}`)
        fs.renameSync(temp, destination)
        installedNow = true
      } finally {
        if (fs.existsSync(temp)) fs.rmSync(temp, { recursive: true, force: true })
      }
    }

    try {
      await enablePlugin({ name: entry.name, activeRoot, hermesHome })
    } catch (error) {
      if (installedNow && fs.existsSync(destination)) fs.rmSync(destination, { recursive: true, force: true })
      throw error
    }
    writeReceipt(hermesHome, entry)
    const state = installedNow ? 'installed' : 'existing'
    results.push({ name: entry.name, state })
    emit({ type: 'log', stage: 'desktop-seed-plugins', line: `[seed-plugin] ${state} and enabled ${entry.name}@${entry.version}` })
  }
  return { skipped: false, plugins: results }
}

function validatePackagedSeedPlugins(seedRoot, options = {}) {
  const manifestPath = path.join(seedRoot, 'manifest.json')
  if (!fs.existsSync(manifestPath)) {
    if (options.required !== false) throw new Error(`Packaged seed plugin manifest is missing: ${manifestPath}`)
    return null
  }

  const manifest = readJson(manifestPath, 'seed plugin manifest')
  if (manifest.schemaVersion !== 1 || !Array.isArray(manifest.plugins) || manifest.plugins.length === 0) {
    throw new Error('Seed plugin manifest must use schemaVersion 1 with at least one plugin')
  }
  const names = new Set()
  for (const entry of manifest.plugins) {
    validateEntry(entry)
    if (names.has(entry.name)) throw new Error(`Duplicate seed plugin name: ${entry.name}`)
    names.add(entry.name)
  }

  const validatedPlugins = manifest.plugins.map(entry => ({
    entry,
    packagedRoot: validatePayload(seedRoot, entry)
  }))
  return { manifest, plugins: validatedPlugins }
}

module.exports = {
  defaultEnablePlugin,
  installSeedPlugins,
  validatePackagedSeedPlugins,
  validatePayload
}
