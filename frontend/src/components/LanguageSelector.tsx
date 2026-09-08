import { useLanguage } from '../i18n/LanguageContext'
import type { Language } from '../i18n/translations'

interface LanguageSelectorProps {
  compact?: boolean
}

export function LanguageSelector({ compact = false }: LanguageSelectorProps) {
  const { language, setLanguage, t } = useLanguage()

  return (
    <div
      className={`flex items-center gap-1 border border-console-border-strong bg-console-bg ${
        compact ? 'p-0.5' : 'p-1'
      }`}
      role="group"
      aria-label={t.language.choose}
    >
      {(['en', 'hi'] as Language[]).map((code) => {
        const active = language === code
        const label = code === 'en' ? t.language.english : t.language.hindi
        return (
          <button
            key={code}
            type="button"
            onClick={() => setLanguage(code)}
            className={`min-h-[36px] font-medium transition-colors ${
              compact ? 'px-2.5 text-xs' : 'px-3 text-sm'
            } ${
              active
                ? 'bg-accent-amber/20 text-accent-amber'
                : 'text-text-secondary hover:bg-console-raised hover:text-text-primary'
            }`}
            aria-pressed={active}
          >
            {label}
          </button>
        )
      })}
    </div>
  )
}
