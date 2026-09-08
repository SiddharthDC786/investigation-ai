import type { ReactElement } from 'react'
import type { ViewId } from '../types'

export const viewIds: ViewId[] = ['search', 'network', 'timeline', 'risk', 'osint', 'audit']

export function IconSearch({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 20 20" fill="none" aria-hidden>
      <circle cx="8.5" cy="8.5" r="5" stroke={active ? '#d9a441' : '#5c7085'} strokeWidth="1.2" />
      <path d="M12.5 12.5L17 17" stroke={active ? '#5b8bb0' : '#3d4f63'} strokeWidth="1.2" />
    </svg>
  )
}

export function IconNetwork({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 20 20" fill="none" aria-hidden>
      <circle cx="10" cy="4" r="2" stroke={active ? '#d9a441' : '#5c7085'} strokeWidth="1.2" />
      <circle cx="4" cy="16" r="2" stroke={active ? '#d9a441' : '#5c7085'} strokeWidth="1.2" />
      <circle cx="16" cy="16" r="2" stroke={active ? '#d9a441' : '#5c7085'} strokeWidth="1.2" />
      <path d="M10 6L5 14M10 6l5 8M4 16h12" stroke={active ? '#5b8bb0' : '#3d4f63'} strokeWidth="1" />
    </svg>
  )
}

export function IconTimeline({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 20 20" fill="none" aria-hidden>
      <path d="M4 4v12M4 4h12M4 10h8M4 16h6" stroke={active ? '#d9a441' : '#5c7085'} strokeWidth="1.2" />
    </svg>
  )
}

export function IconRisk({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 20 20" fill="none" aria-hidden>
      <rect x="3" y="10" width="3" height="7" fill={active ? '#9e4a42' : '#3d4f63'} />
      <rect x="8.5" y="6" width="3" height="11" fill={active ? '#b8893a' : '#3d4f63'} />
      <rect x="14" y="3" width="3" height="14" fill={active ? '#d9a441' : '#3d4f63'} />
    </svg>
  )
}

export function IconOsint({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 20 20" fill="none" aria-hidden>
      <circle cx="9" cy="9" r="5" stroke={active ? '#d9a441' : '#5c7085'} strokeWidth="1.2" />
      <path d="M13 13l4 4" stroke={active ? '#5b8bb0' : '#3d4f63'} strokeWidth="1.2" />
    </svg>
  )
}

export function IconAudit({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 20 20" fill="none" aria-hidden>
      <rect x="4" y="3" width="12" height="14" stroke={active ? '#d9a441' : '#5c7085'} strokeWidth="1.2" />
      <path d="M7 7h6M7 10h6M7 13h4" stroke={active ? '#5b8bb0' : '#3d4f63'} strokeWidth="1" />
    </svg>
  )
}

export const navIcons: Record<ViewId, (props: { active: boolean }) => ReactElement> = {
  search: IconSearch,
  network: IconNetwork,
  timeline: IconTimeline,
  risk: IconRisk,
  osint: IconOsint,
  audit: IconAudit,
}
