const test = require('node:test')
const assert = require('node:assert/strict')
const path = require('node:path')

const { validateFreshInstallIsolation } = require('./fresh-install-isolation.cjs')
const VALIDATION_OPTIONS = { pathModule: path.win32, tmpDir: 'C:\\tmp' }

function validWindowsEnv(overrides = {}) {
  return {
    HERMES_DESKTOP_TEST_MODE: 'fresh-install',
    HERMES_DESKTOP_FRESH_SANDBOX_ROOT: 'C:\\tmp\\hermes-desktop-fresh-install-123',
    HERMES_DESKTOP_USER_DATA_DIR: 'C:\\tmp\\hermes-desktop-fresh-install-123\\electron-user-data',
    HERMES_HOME: 'C:\\tmp\\hermes-desktop-fresh-install-123\\hermes-home',
    ...overrides
  }
}

test('normal desktop launches are unaffected by fresh-install isolation validation', () => {
  assert.equal(validateFreshInstallIsolation({}, VALIDATION_OPTIONS), null)
})

test('fresh-install mode fails closed when an isolation path is missing', () => {
  for (const key of [
    'HERMES_DESKTOP_FRESH_SANDBOX_ROOT',
    'HERMES_DESKTOP_USER_DATA_DIR',
    'HERMES_HOME'
  ]) {
    const env = validWindowsEnv()
    delete env[key]
    assert.throws(
      () => validateFreshInstallIsolation(env, VALIDATION_OPTIONS),
      new RegExp(key)
    )
  }
})

test('fresh-install mode rejects relative isolation paths', () => {
  assert.throws(
    () =>
      validateFreshInstallIsolation(
        validWindowsEnv({ HERMES_HOME: 'relative\\hermes-home' }),
        VALIDATION_OPTIONS
      ),
    /absolute path/
  )
})

test('fresh-install mode rejects userData or HERMES_HOME outside the sandbox root', () => {
  assert.throws(
    () =>
      validateFreshInstallIsolation(
        validWindowsEnv({ HERMES_HOME: 'C:\\Users\\test\\AppData\\Local\\hermes' }),
        VALIDATION_OPTIONS
      ),
    /must be inside/
  )

  assert.throws(
    () =>
      validateFreshInstallIsolation(
        validWindowsEnv({ HERMES_DESKTOP_USER_DATA_DIR: 'C:\\Users\\test\\AppData\\Roaming\\Hermes' }),
        VALIDATION_OPTIONS
      ),
    /must be inside/
  )
})

test('fresh-install mode accepts distinct absolute directories inside the sandbox root', () => {
  assert.deepEqual(validateFreshInstallIsolation(validWindowsEnv(), VALIDATION_OPTIONS), {
    sandboxRoot: 'C:\\tmp\\hermes-desktop-fresh-install-123',
    userDataDir: 'C:\\tmp\\hermes-desktop-fresh-install-123\\electron-user-data',
    hermesHome: 'C:\\tmp\\hermes-desktop-fresh-install-123\\hermes-home'
  })
})
