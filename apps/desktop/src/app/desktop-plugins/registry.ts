import { useEffect, useSyncExternalStore } from 'react'

import { isReservedAppPath, setDesktopPluginPaths } from '../routes'

export const DESKTOP_PLUGIN_API_VERSION = 1

export interface DesktopPluginManifest {
  api_version: 1
  entry: string
  icon: string
  label: string
  name: string
  path: string
  position: string
  source: 'bundled' | 'user'
  version: string
}

export interface DesktopPluginHost {
  api: <T>(path: string, options?: { body?: unknown; method?: string }) => Promise<T>
  continueInChat: (text: string) => void
  locale: string
  navigate: (path: string) => void
  notify: (title: string, body: string) => Promise<boolean>
  previewMedia: (path: string) => Promise<void>
  workspaceRoot: string
}

export interface DesktopPluginRegistration {
  apiVersion: 1
  mount: (root: HTMLElement, host: DesktopPluginHost) => void | (() => void)
  name: string
}

interface RegistrySnapshot {
  errors: Record<string, string>
  loading: boolean
  manifests: DesktopPluginManifest[]
  statuses: Record<string, DesktopPluginStatus>
}

export type DesktopPluginStatus = 'error' | 'loading' | 'ready'

const registrations = new Map<string, DesktopPluginRegistration>()
const listeners = new Set<() => void>()
let snapshot: RegistrySnapshot = { errors: {}, loading: true, manifests: [], statuses: {} }
let initialization: Promise<void> | null = null
let activeRegistrationName: string | null = null
let pendingRegistration: DesktopPluginRegistration | null = null

const emit = (next: RegistrySnapshot) => {
  snapshot = next
  listeners.forEach(listener => listener())
}

const registerPage = (registration: DesktopPluginRegistration) => {
  if (
    registration?.apiVersion !== DESKTOP_PLUGIN_API_VERSION ||
    typeof registration.name !== 'string' ||
    typeof registration.mount !== 'function'
  ) {
    throw new Error('Invalid Desktop plugin registration')
  }

  if (!activeRegistrationName || registration.name !== activeRegistrationName) {
    throw new Error(`Desktop plugin bundle must register itself as ${activeRegistrationName ?? 'the active plugin'}`)
  }
  if (pendingRegistration || registrations.has(registration.name)) {
    throw new Error(`Desktop plugin ${registration.name} registered more than once`)
  }

  pendingRegistration = registration
}

window.__HERMES_DESKTOP_PLUGINS__ = Object.freeze({ registerPage })

const ordered = (items: DesktopPluginManifest[]) => {
  const result: DesktopPluginManifest[] = []
  const pending = [...items]

  while (pending.length) {
    const item = pending.shift()!
    const match = /^(before|after):(.+)$/.exec(item.position)
    const target = match?.[2]
    const index = target === 'artifacts' ? result.findIndex(entry => entry.name === 'artifacts') : -1

    if (index >= 0) {
      result.splice(index + (match?.[1] === 'after' ? 1 : 0), 0, item)
    } else {
      result.push(item)
    }
  }

  return result
}

export async function initializeDesktopPlugins() {
  if (initialization) {return initialization}

  initialization = (async () => {
    const errors: Record<string, string> = {}

    try {
      const response = await window.hermesDesktop.desktopPlugins.list()

      if (response.api_version !== DESKTOP_PLUGIN_API_VERSION) {
        throw new Error(`Unsupported Desktop plugin API ${response.api_version}`)
      }

      const paths = new Set<string>()

      const manifests = response.plugins.filter(manifest => {
        if (isReservedAppPath(manifest.path)) {
          errors[manifest.name] = `Reserved Desktop route: ${manifest.path}`

          return false
        }

        if (paths.has(manifest.path)) {
          errors[manifest.name] = `Duplicate Desktop plugin route: ${manifest.path}`

          return false
        }

        paths.add(manifest.path)

        return true
      })

      const orderedManifests = ordered(manifests)
      const statuses: Record<string, DesktopPluginStatus> = Object.fromEntries(
        orderedManifests.map(manifest => [manifest.name, 'loading'])
      )

      setDesktopPluginPaths(paths)
      emit({ errors: { ...errors }, loading: true, manifests: orderedManifests, statuses: { ...statuses } })

      for (const manifest of orderedManifests) {
        try {
          const bundle = await window.hermesDesktop.desktopPlugins.load(manifest.name)

          if (
            bundle.api_version !== DESKTOP_PLUGIN_API_VERSION ||
            bundle.name !== manifest.name ||
            bundle.entry !== manifest.entry ||
            bundle.version !== manifest.version
          ) {
            throw new Error('Desktop plugin bundle identity mismatch')
          }

          activeRegistrationName = manifest.name
          pendingRegistration = null

          try {
            const script = document.createElement('script')
            script.dataset.hermesDesktopPlugin = manifest.name
            script.text = `${bundle.source}\n//# sourceURL=hermes-desktop-plugin://${manifest.name}/${manifest.entry}`
            document.head.appendChild(script)
            script.remove()
          } finally {
            activeRegistrationName = null
          }

          const registration = pendingRegistration

          if (!registration) {
            throw new Error('Bundle did not register a Desktop page')
          }

          registrations.set(manifest.name, registration)
          statuses[manifest.name] = 'ready'
        } catch (cause) {
          pendingRegistration = null
          registrations.delete(manifest.name)
          errors[manifest.name] = cause instanceof Error ? cause.message : String(cause)
          statuses[manifest.name] = 'error'
        }

        emit({
          errors: { ...errors },
          loading: true,
          manifests: orderedManifests,
          statuses: { ...statuses }
        })
      }

      emit({ errors, loading: false, manifests: orderedManifests, statuses })
    } catch (cause) {
      setDesktopPluginPaths([])
      emit({
        errors: { host: cause instanceof Error ? cause.message : String(cause) },
        loading: false,
        manifests: [],
        statuses: {}
      })
    }
  })()

  return initialization
}

export function desktopPluginRegistration(name: string) {
  return registrations.get(name)
}

export function desktopPluginForPath(path: string) {
  return snapshot.manifests.find(manifest => manifest.path === path)
}

export function desktopPluginError(name: string) {
  return snapshot.errors[name]
}

export function desktopPluginStatusForPath(path: string) {
  const manifest = desktopPluginForPath(path)

  return manifest ? snapshot.statuses[manifest.name] : undefined
}

export function useDesktopPlugins() {
  const value = useSyncExternalStore(
    listener => {
      listeners.add(listener)

      return () => listeners.delete(listener)
    },
    () => snapshot
  )

  useEffect(() => {
    void initializeDesktopPlugins()
  }, [])

  return value
}

declare global {
  interface Window {
    __HERMES_DESKTOP_PLUGINS__: { registerPage: (registration: DesktopPluginRegistration) => void }
  }
}
