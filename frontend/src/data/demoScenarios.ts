import type { SearchFilters } from '../types'

export type DemoScenarioId = 'same_name' | 'fir_typo' | 'married_name' | 'hidden_bridge'

export interface DemoScenario {
  id: DemoScenarioId
  labelKey: DemoScenarioId
  descriptionKey: `${DemoScenarioId}Desc`
  filters: Pick<SearchFilters, 'nameQuery' | 'phoneQuery' | 'areaQuery' | 'roleFilter'>
}

export const demoScenarios: DemoScenario[] = [
  {
    id: 'same_name',
    labelKey: 'same_name',
    descriptionKey: 'same_nameDesc',
    filters: { nameQuery: 'Rahul', phoneQuery: '', areaQuery: '', roleFilter: 'all' },
  },
  {
    id: 'fir_typo',
    labelKey: 'fir_typo',
    descriptionKey: 'fir_typoDesc',
    filters: { nameQuery: 'Mukkherjee', phoneQuery: '', areaQuery: 'Mumbai', roleFilter: 'all' },
  },
  {
    id: 'married_name',
    labelKey: 'married_name',
    descriptionKey: 'married_nameDesc',
    filters: { nameQuery: 'Meera', phoneQuery: '', areaQuery: '', roleFilter: 'all' },
  },
  {
    id: 'hidden_bridge',
    labelKey: 'hidden_bridge',
    descriptionKey: 'hidden_bridgeDesc',
    filters: { nameQuery: 'Rahul', phoneQuery: '', areaQuery: 'Mumbai', roleFilter: 'all' },
  },
]
