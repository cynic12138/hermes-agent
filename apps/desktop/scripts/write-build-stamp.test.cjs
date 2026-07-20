const assert = require('node:assert/strict')
const test = require('node:test')
const fs = require('node:fs')
const path = require('node:path')
const { spawnSync } = require('node:child_process')

const desktopRoot = path.resolve(__dirname, '..')
const stampPath = path.join(desktopRoot, 'build', 'install-stamp.json')

test('build stamp records the validated source repository', () => {
  const previous = fs.existsSync(stampPath) ? fs.readFileSync(stampPath) : null
  try {
    const result = spawnSync(process.execPath, [path.join(__dirname, 'write-build-stamp.cjs')], {
      cwd: desktopRoot,
      env: {
        ...process.env,
        HERMES_DESKTOP_SOURCE_REPOSITORY: 'cynic12138/hermes-agent'
      },
      encoding: 'utf8'
    })
    assert.equal(result.status, 0, result.stderr || result.stdout)
    const stamp = JSON.parse(fs.readFileSync(stampPath, 'utf8'))
    assert.equal(stamp.repository, 'cynic12138/hermes-agent')
  } finally {
    if (previous) {
      fs.writeFileSync(stampPath, previous)
    } else {
      fs.rmSync(stampPath, { force: true })
    }
  }
})

test('build stamp rejects a repository URL instead of treating it as a slug', () => {
  const result = spawnSync(process.execPath, [path.join(__dirname, 'write-build-stamp.cjs')], {
    cwd: desktopRoot,
    env: {
      ...process.env,
      HERMES_DESKTOP_SOURCE_REPOSITORY: 'https://evil.example/repo'
    },
    encoding: 'utf8'
  })

  assert.notEqual(result.status, 0)
  assert.match(result.stderr, /repository/i)
})
