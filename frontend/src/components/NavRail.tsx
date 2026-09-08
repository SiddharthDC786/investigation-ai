import { useLanguage } from '../i18n/LanguageContext'
import type { ViewId } from '../types'
import { navIcons, viewIds } from './navConfig'

interface NavRailProps {
  active: ViewId
  onChange: (view: ViewId) => void
}

export function NavRail({ active, onChange }: NavRailProps) {
  const { t } = useLanguage()

  return (
    <nav className="flex w-[188px] shrink-0 flex-col border-r border-console-border bg-console-surface py-3">
      <p className="px-3 pb-2 text-[11px] font-semibold text-text-secondary">{t.nav.mainMenu}</p>
      <ul className="flex flex-1 flex-col gap-1 px-2">
        {viewIds.map((id) => {
          const Icon = navIcons[id]
          const isActive = active === id
          const copy = t.views[id]
          return (
            <li key={id}>
              <button
                type="button"
                onClick={() => onChange(id)}
                className={`flex w-full min-h-[52px] items-center gap-2.5 border px-2.5 py-2.5 text-left transition-colors ${
                  isActive
                    ? 'border-accent-amber/50 bg-accent-amber/10'
                    : 'border-transparent hover:border-console-border hover:bg-console-raised'
                }`}
              >
                <Icon active={isActive} />
                <span className="min-w-0">
                  <span className={`block text-sm leading-tight ${isActive ? 'text-text-primary' : 'text-text-secondary'}`}>
                    {copy.title}
                  </span>
                  <span className="block text-[10px] text-text-muted">{copy.hint}</span>
                </span>
              </button>
            </li>
          )
        })}
      </ul>
      <p className="px-3 pt-3 text-[10px] leading-relaxed text-text-muted">{t.nav.navHint}</p>
    </nav>
  )
}
