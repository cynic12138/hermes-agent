const os = require('node:os')
const path = require('node:path')

const FRESH_INSTALL_MODE = 'fresh-install'
const FRESH_SANDBOX_PREFIX = 'hermes-desktop-fresh-install-'

function isStrictChild(parent, candidate, pathModule) {
  const relative = pathModule.relative(parent, candidate)
  return Boolean(relative) && relative !== '..' && !relative.startsWith(`..${pathModule.sep}`) && !pathModule.isAbsolute(relative)
}

function requireAbsolutePath(env, key, pathModule) {
  const value = env?.[key]
  if (!value) {
    throw new Error(`[fresh-install isolation] ${key} is required in fresh-install mode`)
  }
  if (!pathModule.isAbsolute(value)) {
    throw new Error(`[fresh-install isolation] ${key} must be an absolute path`)
  }
  return pathModule.resolve(value)
}

function validateFreshInstallIsolation(
  env = process.env,
  { pathModule = path, tmpDir = os.tmpdir() } = {}
) {
  if (env?.HERMES_DESKTOP_TEST_MODE !== FRESH_INSTALL_MODE) return null

  const sandboxRoot = requireAbsolutePath(env, 'HERMES_DESKTOP_FRESH_SANDBOX_ROOT', pathModule)
  const userDataDir = requireAbsolutePath(env, 'HERMES_DESKTOP_USER_DATA_DIR', pathModule)
  const hermesHome = requireAbsolutePath(env, 'HERMES_HOME', pathModule)
  const resolvedTmpDir = pathModule.resolve(tmpDir)

  if (
    !isStrictChild(resolvedTmpDir, sandboxRoot, pathModule) ||
    !pathModule.basename(sandboxRoot).startsWith(FRESH_SANDBOX_PREFIX)
  ) {
    throw new Error(
      `[fresh-install isolation] HERMES_DESKTOP_FRESH_SANDBOX_ROOT must be a ${FRESH_SANDBOX_PREFIX}* directory inside the system temporary directory`
    )
  }

  for (const [key, candidate] of [
    ['HERMES_DESKTOP_USER_DATA_DIR', userDataDir],
    ['HERMES_HOME', hermesHome]
  ]) {
    if (!isStrictChild(sandboxRoot, candidate, pathModule)) {
      throw new Error(`[fresh-install isolation] ${key} must be inside the fresh-install sandbox root`)
    }
  }

  if (userDataDir === hermesHome) {
    throw new Error('[fresh-install isolation] HERMES_DESKTOP_USER_DATA_DIR and HERMES_HOME must be distinct')
  }

  return { sandboxRoot, userDataDir, hermesHome }
}

module.exports = {
  FRESH_INSTALL_MODE,
  FRESH_SANDBOX_PREFIX,
  validateFreshInstallIsolation
}
