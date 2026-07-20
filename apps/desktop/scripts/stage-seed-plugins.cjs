'use strict'

const crypto = require('node:crypto')
const fs = require('node:fs')
const path = require('node:path')
const { spawnSync } = require('node:child_process')

const NAME_RE = /^[a-z][a-z0-9_]{0,63}$/
const VERSION_RE = /^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$/
const HASH_RE = /^[0-9a-f]{64}$/
const COMMIT_RE = /^[0-9a-f]{7,40}$/i
const MAX_FILE_BYTES = 8 * 1024 * 1024

function walkFiles(root) {
  const files = []
  function visit(current) {
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const fullPath = path.join(current, entry.name)
      const stat = fs.lstatSync(fullPath)
      if (stat.isSymbolicLink()) {
        throw new Error(`Seed plugin contains unsafe symlink: ${path.relative(root, fullPath)}`)
      }
      if (stat.isDirectory()) {
        visit(fullPath)
      } else if (stat.isFile()) {
        if (stat.size > MAX_FILE_BYTES) {
          throw new Error(`Seed plugin contains oversized file: ${path.relative(root, fullPath)}`)
        }
        files.push(fullPath)
      } else {
        throw new Error(`Seed plugin contains unsupported file type: ${path.relative(root, fullPath)}`)
      }
    }
  }
  visit(root)
  return files
}

function hashPayload(root) {
  const absoluteRoot = path.resolve(root)
  const files = walkFiles(absoluteRoot)
    .filter(filePath => path.basename(filePath) !== 'SOURCE.json')
    .map(filePath => ({
      filePath,
      relative: path.relative(absoluteRoot, filePath).split(path.sep).join('/')
    }))
    .sort((left, right) => left.relative < right.relative ? -1 : left.relative > right.relative ? 1 : 0)
  const rows = files.map(({ filePath, relative }) => {
      const digest = crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex')
      return `${digest} ${relative}`
    })
  return crypto.createHash('sha256').update(rows.join('\n'), 'utf8').digest('hex')
}

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
  const manifestPath = path.join(pluginRoot, 'plugin.yaml')
  const text = fs.readFileSync(manifestPath, 'utf8')
  const name = text.match(/^name:\s*([^\s]+)\s*$/m)?.[1] || ''
  const version = text.match(/^version:\s*([^\s]+)\s*$/m)?.[1] || ''
  return { name, version }
}

function validatePluginConfig(plugin, repoRoot, desktopRoot) {
  if (!plugin || typeof plugin !== 'object') throw new Error('Seed plugin entry must be an object')
  if (!NAME_RE.test(plugin.name || '')) throw new Error(`Seed plugin has unsafe name: ${plugin.name || '<missing>'}`)
  if (!VERSION_RE.test(plugin.version || '')) throw new Error(`Seed plugin has unsafe version: ${plugin.version || '<missing>'}`)
  if (typeof plugin.exporter !== 'string' || !plugin.exporter) throw new Error(`Seed plugin ${plugin.name} has no exporter`)
  const exporterPath = path.resolve(desktopRoot, plugin.exporter)
  if (!isWithin(exporterPath, repoRoot)) throw new Error(`Seed plugin exporter is outside repository: ${plugin.name}`)
  return exporterPath
}

function defaultRunExporter({ exporterPath, outputDirectory, plugin, repoRoot }) {
  if (!fs.statSync(exporterPath).isFile()) throw new Error(`Seed plugin exporter is not a file: ${exporterPath}`)
  const python = process.env.PYTHON || 'python'
  const result = spawnSync(
    python,
    [
      exporterPath,
      '--output-directory',
      outputDirectory,
      '--expected-version',
      plugin.version,
      '--allow-output-root',
      path.dirname(outputDirectory)
    ],
    { cwd: repoRoot, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }
  )
  if (result.error) throw result.error
  if (result.status !== 0) {
    throw new Error(`Seed plugin exporter failed for ${plugin.name}: ${(result.stderr || result.stdout || '').trim()}`)
  }
}

function validateStagedPlugin(pluginRoot, plugin) {
  walkFiles(pluginRoot)
  const identity = readPluginIdentity(pluginRoot)
  if (identity.name !== plugin.name || identity.version !== plugin.version) {
    throw new Error(
      `Seed plugin identity mismatch for ${plugin.name}: got ${identity.name || '<missing>'}@${identity.version || '<missing>'}`
    )
  }
  const source = readJson(path.join(pluginRoot, 'SOURCE.json'), `${plugin.name} SOURCE`)
  if (source.plugin_version !== plugin.version) throw new Error(`Seed plugin metadata version mismatch: ${plugin.name}`)
  if (source.desktop_sdk_version !== 1) throw new Error(`Seed plugin Desktop SDK mismatch: ${plugin.name}`)
  if (!HASH_RE.test(source.payload_sha256 || '')) throw new Error(`Seed plugin payload hash is invalid: ${plugin.name}`)
  if (!COMMIT_RE.test(source.source_commit || '')) throw new Error(`Seed plugin source commit is invalid: ${plugin.name}`)
  if (typeof source.source_repository !== 'string' || !source.source_repository.includes('/')) {
    throw new Error(`Seed plugin source repository is invalid: ${plugin.name}`)
  }
  const actualHash = hashPayload(pluginRoot)
  if (actualHash !== source.payload_sha256) throw new Error(`Seed plugin payload hash mismatch: ${plugin.name}`)
  return {
    name: plugin.name,
    version: plugin.version,
    path: plugin.name,
    payloadSha256: actualHash,
    desktopSdkVersion: source.desktop_sdk_version,
    sourceRepository: source.source_repository,
    sourceCommit: source.source_commit
  }
}

function stageSeedPlugins(options = {}) {
  const desktopRoot = path.resolve(options.desktopRoot || path.join(__dirname, '..'))
  const repoRoot = path.resolve(options.repoRoot || path.join(desktopRoot, '..', '..'))
  const configPath = path.resolve(options.configPath || path.join(desktopRoot, 'seed-plugins.json'))
  const outputRoot = path.resolve(options.outputRoot || path.join(desktopRoot, 'build', 'seed-plugins'))
  const runExporter = options.runExporter || defaultRunExporter
  if (!isWithin(configPath, repoRoot) || !isWithin(outputRoot, desktopRoot)) {
    throw new Error('Seed plugin config or output path is outside the allowed root')
  }

  const config = readJson(configPath, 'seed plugin config')
  if (config.schemaVersion !== 1 || !Array.isArray(config.plugins) || config.plugins.length === 0) {
    throw new Error('Seed plugin config must use schemaVersion 1 with at least one plugin')
  }
  const names = new Set()
  const prepared = config.plugins.map(plugin => {
    const exporterPath = validatePluginConfig(plugin, repoRoot, desktopRoot)
    if (names.has(plugin.name)) throw new Error(`Duplicate seed plugin name: ${plugin.name}`)
    names.add(plugin.name)
    return { plugin, exporterPath }
  })

  fs.rmSync(outputRoot, { recursive: true, force: true })
  fs.mkdirSync(outputRoot, { recursive: true })
  const entries = []
  for (const { plugin, exporterPath } of prepared) {
    const outputDirectory = path.join(outputRoot, plugin.name)
    runExporter({ exporterPath, outputDirectory, plugin, repoRoot })
    if (!fs.statSync(outputDirectory).isDirectory()) throw new Error(`Seed exporter produced no directory: ${plugin.name}`)
    entries.push(validateStagedPlugin(outputDirectory, plugin))
  }

  const manifest = { schemaVersion: 1, plugins: entries }
  fs.writeFileSync(path.join(outputRoot, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n', 'utf8')
  return manifest
}

function main() {
  try {
    const manifest = stageSeedPlugins()
    console.log(`[stage-seed-plugins] staged ${manifest.plugins.length} plugin(s)`)
  } catch (error) {
    console.error(`[stage-seed-plugins] ERROR: ${error.message}`)
    process.exitCode = 1
  }
}

if (require.main === module) main()

module.exports = {
  hashPayload,
  stageSeedPlugins,
  validateStagedPlugin
}
