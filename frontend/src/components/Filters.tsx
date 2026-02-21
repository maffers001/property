import type { DraftFilters as FiltersType } from '../types'

type Props = {
  filters: FiltersType
  onChange: (f: FiltersType) => void
  lists: { property_codes: string[]; categories: string[]; subcategories: string[] } | null
  collapsed?: boolean
  onToggleCollapsed?: () => void
}

const DEFAULT_FILTERS: FiltersType = {
  property: [],
  category: [],
  subcategory: [],
  search: '',
  date_from: '',
  date_to: '',
}

export default function Filters({ filters, onChange, lists, collapsed, onToggleCollapsed }: Props) {
  const update = (key: keyof FiltersType, value: string | string[]) => {
    onChange({ ...filters, [key]: value })
  }

  return (
    <div className="filters-panel">
      {onToggleCollapsed && (
        <button type="button" className="filters-toggle" onClick={onToggleCollapsed}>
          {collapsed ? 'Show filters' : 'Hide filters'}
        </button>
      )}
      {(!onToggleCollapsed || !collapsed) && (
        <div className="filters-inner">
          <div className="filter-group">
            <label>Search (memo)</label>
            <input
              type="text"
              value={filters.search}
              onChange={(e) => update('search', e.target.value)}
              placeholder="Search…"
              aria-label="Search memo"
            />
          </div>
          <div className="filter-group">
            <label>Date from</label>
            <input
              type="date"
              value={filters.date_from}
              onChange={(e) => update('date_from', e.target.value)}
              aria-label="Date from"
            />
          </div>
          <div className="filter-group">
            <label>Date to</label>
            <input
              type="date"
              value={filters.date_to}
              onChange={(e) => update('date_to', e.target.value)}
              aria-label="Date to"
            />
          </div>
          {lists && (
            <>
              <div className="filter-group filter-group-multi">
                <label>Property</label>
                <div className="filter-checkboxes">
                  {lists.property_codes.map((c) => (
                    <label key={c} className="filter-checkbox">
                      <input
                        type="checkbox"
                        checked={filters.property.includes(c)}
                        onChange={() => {
                          const next = filters.property.includes(c)
                            ? filters.property.filter((x) => x !== c)
                            : [...filters.property, c]
                          update('property', next)
                        }}
                      />
                      <span>{c}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div className="filter-group filter-group-multi">
                <label>Category</label>
                <div className="filter-checkboxes">
                  {lists.categories.map((c) => (
                    <label key={c} className="filter-checkbox">
                      <input
                        type="checkbox"
                        checked={filters.category.includes(c)}
                        onChange={() => {
                          const next = filters.category.includes(c)
                            ? filters.category.filter((x) => x !== c)
                            : [...filters.category, c]
                          update('category', next)
                        }}
                      />
                      <span>{c}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div className="filter-group filter-group-multi">
                <label>Subcategory</label>
                <div className="filter-checkboxes">
                  {lists.subcategories.map((c) => (
                    <label key={c} className="filter-checkbox">
                      <input
                        type="checkbox"
                        checked={filters.subcategory.includes(c)}
                        onChange={() => {
                          const next = filters.subcategory.includes(c)
                            ? filters.subcategory.filter((x) => x !== c)
                            : [...filters.subcategory, c]
                          update('subcategory', next)
                        }}
                      />
                      <span>{c}</span>
                    </label>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}

export { DEFAULT_FILTERS }
