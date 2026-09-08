import { useLanguage } from '../i18n/LanguageContext'

export function SecurityBanner() {
  const { t, language } = useLanguage()

  return (
    <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-risk-high/30 bg-risk-high/10 px-4 py-2">
      <p className="text-xs sm:text-sm text-text-primary">
        <span className="font-semibold text-risk-high">CONFIDENTIAL</span>
        <span className="text-text-muted"> — </span>
        {t.security.confidential}
      </p>
      {language === 'hi' && t.security.confidentialHi && (
        <p className="text-[10px] text-accent-steel">{t.security.confidentialHi}</p>
      )}
    </div>
  )
}
