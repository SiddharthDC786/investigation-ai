import { demoScenarios, type DemoScenarioId } from '../data/demoScenarios'
import { useLanguage } from '../i18n/LanguageContext'
import type { SearchFilters } from '../types'

interface DemoScenarioChipsProps {
  onRun: (filters: SearchFilters) => void
  disabled?: boolean
}

export function DemoScenarioChips({ onRun, disabled }: DemoScenarioChipsProps) {
  const { t } = useLanguage()

  function runScenario(id: DemoScenarioId) {
    const scenario = demoScenarios.find((s) => s.id === id)
    if (!scenario) return
    onRun({
      ...scenario.filters,
      genderQuery: '',
      ageQuery: '',
      fatherNameQuery: '',
      faceMatchPersonId: null,
      selectedPersonId: null,
    })
  }

  return (
    <div className="mb-4 border border-accent-steel/30 bg-accent-steel/5 p-3">
      <p className="text-sm font-semibold text-text-primary">{t.demo.title}</p>
      <p className="mt-0.5 text-xs text-text-muted">{t.demo.subtitle}</p>
      <div className="mt-3 flex flex-col gap-2">
        {demoScenarios.map((scenario) => (
          <button
            key={scenario.id}
            type="button"
            disabled={disabled}
            onClick={() => runScenario(scenario.id)}
            className="min-h-[48px] border border-console-border-strong bg-console-bg px-3 py-2.5 text-left transition-colors hover:border-accent-amber/50 hover:bg-accent-amber/5 disabled:opacity-50 presentation-mode:min-h-[56px]"
          >
            <span className="block text-sm font-medium text-accent-amber">
              {t.demo[scenario.labelKey]}
            </span>
            <span className="mt-0.5 block text-xs text-text-muted">
              {t.demo[scenario.descriptionKey]}
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}
