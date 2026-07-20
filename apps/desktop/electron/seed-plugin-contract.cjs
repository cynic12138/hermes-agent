'use strict'

const crypto = require('node:crypto')
const fs = require('node:fs')
const path = require('node:path')

const MAX_FILE_BYTES = 8 * 1024 * 1024
const FORBIDDEN_PARTS = new Set([
  '__pycache__',
  '.pytest_cache',
  '.env',
  'artifacts',
  'cookies',
  'products',
  'prompts',
  'raw',
  'runtime_data',
  'secrets'
])
const FORBIDDEN_SUFFIXES = new Set([
  '.db', '.gif', '.jpeg', '.jpg', '.log', '.mov', '.mp4', '.png', '.pyc',
  '.shm', '.sqlite', '.sqlite3', '.wal', '.webp'
])
const CONTENT_RULES = [
  ['private-key', /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/],
  ['provider-key', /\b(?:sk|ak)-[A-Za-z0-9_-]{16,}\b/],
  ['jwt', /\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b/],
  ['literal-secret', /\b(?:api[_-]?key|access[_-]?token|cookie|password|secret)\b\s*[:=]\s*['"][^'"\r\n]{8,}['"]/i],
  ['personal-home', /(?:[A-Z]:\\Users\\[^\\\s]+|\/(?:Users|home)\/[^/\s]+)/i],
  ['email', /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/],
  ['cn-id', /(^|\D)\d{17}[0-9Xx](?!\d)/]
]

function walkFiles(root) {
  const absoluteRoot = path.resolve(root)
  const files = []
  function visit(current) {
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const fullPath = path.join(current, entry.name)
      const stat = fs.lstatSync(fullPath)
      if (stat.isSymbolicLink()) {
        throw new Error(`Seed plugin contains unsafe symlink: ${path.relative(absoluteRoot, fullPath)}`)
      }
      if (stat.isDirectory()) {
        visit(fullPath)
      } else if (stat.isFile()) {
        if (stat.size > MAX_FILE_BYTES) {
          throw new Error(`Seed plugin contains oversized file: ${path.relative(absoluteRoot, fullPath)}`)
        }
        files.push(fullPath)
      } else {
        throw new Error(`Seed plugin contains unsupported file type: ${path.relative(absoluteRoot, fullPath)}`)
      }
    }
  }
  visit(absoluteRoot)
  return files
}

function relativePosix(root, filePath) {
  return path.relative(path.resolve(root), filePath).split(path.sep).join('/')
}

function hashPayload(root) {
  const absoluteRoot = path.resolve(root)
  const files = walkFiles(absoluteRoot)
    .filter(filePath => path.basename(filePath) !== 'SOURCE.json')
    .map(filePath => ({ filePath, relative: relativePosix(absoluteRoot, filePath) }))
    .sort((left, right) => left.relative < right.relative ? -1 : left.relative > right.relative ? 1 : 0)
  const rows = files.map(({ filePath, relative }) => {
    const digest = crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex')
    return `${digest} ${relative}`
  })
  return crypto.createHash('sha256').update(rows.join('\n'), 'utf8').digest('hex')
}

function validatePayloadSafety(root) {
  const absoluteRoot = path.resolve(root)
  for (const filePath of walkFiles(absoluteRoot)) {
    const relative = relativePosix(absoluteRoot, filePath)
    const parts = relative.toLowerCase().split('/')
    const suffix = path.extname(filePath).toLowerCase()
    const basename = path.basename(filePath).toLowerCase()
    if (parts.some(part => FORBIDDEN_PARTS.has(part)) || FORBIDDEN_SUFFIXES.has(suffix) || basename.endsWith('-wal') || basename.endsWith('-shm')) {
      throw new Error(`Seed plugin contains forbidden path: ${relative}`)
    }
    const bytes = fs.readFileSync(filePath)
    const text = bytes.toString('utf8')
    if (Buffer.from(text, 'utf8').compare(bytes) !== 0) {
      throw new Error(`Seed plugin contains unsupported binary file: ${relative}`)
    }
    for (const [rule, expression] of CONTENT_RULES) {
      const lines = text.split(/\r?\n/)
      for (let index = 0; index < lines.length; index += 1) {
        if (expression.test(lines[index])) {
          throw new Error(`Seed plugin contains forbidden ${rule}: ${relative}:${index + 1}`)
        }
      }
    }
  }
}

module.exports = {
  hashPayload,
  validatePayloadSafety,
  walkFiles
}
