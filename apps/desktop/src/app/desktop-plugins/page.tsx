import { useStore } from '@nanostores/react'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useI18n } from '@/i18n'
import { $currentCwd } from '@/store/session'

import { requestComposerInsert } from '../chat/composer/focus'
import { NEW_CHAT_ROUTE } from '../routes'

import { type DesktopPluginManifest, desktopPluginRegistration } from './registry'

interface DesktopPluginPageProps {
  error?: string
  manifest: DesktopPluginManifest
  status: 'error' | 'loading' | 'ready'
}

const message = (cause: unknown) => (cause instanceof Error ? cause.message : String(cause))

export function DesktopPluginPage({ error, manifest, status }: DesktopPluginPageProps) {
  const rootRef = useRef<HTMLDivElement>(null)
  const [mountError, setMountError] = useState<string>()
  const workspaceRoot = useStore($currentCwd).trim()
  const { locale } = useI18n()
  const navigate = useNavigate()

  useEffect(() => {
    const root = rootRef.current

    if (status !== 'ready' || !root) {return}

    const registration = desktopPluginRegistration(manifest.name)

    if (!registration) {return}

    try {
      const cleanup = registration.mount(root, {
        api: (path, options) =>
          window.hermesDesktop.api({
            path,
            method: options?.method,
            body: options?.body,
            headers: { 'X-Hermes-Workspace-Root': workspaceRoot }
          }),
        continueInChat: text => {
          navigate(NEW_CHAT_ROUTE)
          requestComposerInsert(text)
        },
        locale,
        navigate,
        notify: (title, body) => window.hermesDesktop.notify({ title, body }),
        previewMedia: async path => {
          const target = await window.hermesDesktop.normalizePreviewTarget(path, workspaceRoot)

          if (!target) {throw new Error('Media is unavailable')}
          await window.hermesDesktop.openPreviewInBrowser?.(target.url)
        },
        workspaceRoot
      })

      setMountError(undefined)

      if (typeof cleanup === 'function') {
        return () => {
          try {
            cleanup()
          } catch (cause) {
            setMountError(`Desktop plugin cleanup failed: ${message(cause)}`)
          }
        }
      }
    } catch (cause) {
      setMountError(`Desktop plugin mount failed: ${message(cause)}`)
    }
  }, [locale, manifest.name, navigate, status, workspaceRoot])

  if (status === 'loading') {
    return (
      <div className="flex h-full items-center justify-center p-6 text-sm" role="status">
        Loading {manifest.label}…
      </div>
    )
  }

  const diagnostic = error || mountError

  if (status === 'error' || diagnostic) {
    return (
      <div className="flex h-full items-center justify-center p-6" role="alert">
        <div className="max-w-xl rounded border border-(--ui-stroke-secondary) p-4">
          <div className="font-medium">{manifest.label} could not be opened</div>
          <div className="mt-2 break-words text-sm opacity-80">{diagnostic || 'Unknown Desktop plugin error'}</div>
        </div>
      </div>
    )
  }

  return <div className="h-full min-h-0" data-desktop-plugin={manifest.name} ref={rootRef} />
}
