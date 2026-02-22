import type { DraftRow, DraftColumnKey } from '../types'

type Props = {
  rows: DraftRow[]
  visibleColumns: DraftColumnKey[]
  selectedTxIds: Set<string>
  onSelect: (txIds: string[]) => void
  onCorrect: (row: DraftRow, updates: { property_code: string; category: string; subcategory: string }) => void
  lists: { property_codes: string[]; categories: string[]; subcategories: string[] } | null
}

export default function DraftTable({ rows, visibleColumns, selectedTxIds, onSelect, onCorrect, lists }: Props) {
  const toggleSelect = (txId: string) => {
    const next = new Set(selectedTxIds)
    if (next.has(txId)) next.delete(txId)
    else next.add(txId)
    onSelect([...next])
  }

  const selectAll = () => {
    if (selectedTxIds.size === rows.length) onSelect([])
    else onSelect(rows.map((r) => r.tx_id))
  }

  const applyCorrect = (
    row: DraftRow,
    update: { property_code?: string; category?: string; subcategory?: string }
  ) => {
    onCorrect(row, {
      property_code: update.property_code ?? row.property_code ?? row.Property ?? '',
      category: update.category ?? row.category ?? row.Cat ?? '',
      subcategory: update.subcategory ?? row.subcategory ?? row.Subcat ?? '',
    })
  }

  const cellValue = (row: DraftRow, key: DraftColumnKey): string | number => {
    const v = row[key as keyof DraftRow]
    if (key === 'needs_review') return row.needs_review ? 'Yes' : ''
    if (v === undefined || v === null) return ''
    return typeof v === 'number' ? (key === 'Amount' ? (v as number).toFixed(2) : v) : String(v)
  }

  const renderCell = (row: DraftRow, key: DraftColumnKey) => {
    if (key === 'Property' && lists) {
      const val = row.Property ?? row.property_code ?? ''
      return (
        <select
          className="draft-cell-select"
          value={val}
          onChange={(e) => applyCorrect(row, { property_code: e.target.value })}
          onClick={(e) => e.stopPropagation()}
          aria-label="Property"
        >
          <option value="">—</option>
          {lists.property_codes.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      )
    }
    if (key === 'Cat' && lists) {
      const val = row.Cat ?? row.category ?? ''
      return (
        <select
          className="draft-cell-select"
          value={val}
          onChange={(e) => applyCorrect(row, { category: e.target.value })}
          onClick={(e) => e.stopPropagation()}
          aria-label="Category"
        >
          <option value="">—</option>
          {lists.categories.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      )
    }
    if (key === 'Subcat' && lists) {
      const val = row.Subcat ?? row.subcategory ?? ''
      return (
        <select
          className="draft-cell-select"
          value={val}
          onChange={(e) => applyCorrect(row, { subcategory: e.target.value })}
          onClick={(e) => e.stopPropagation()}
          aria-label="Subcategory"
        >
          <option value="">—</option>
          {lists.subcategories.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      )
    }
    return cellValue(row, key)
  }

  return (
    <div className="draft-table-wrap">
      <div className="table-scroll">
        <table className="draft-table">
          <thead>
            <tr>
              <th>
                <input
                  type="checkbox"
                  checked={rows.length > 0 && selectedTxIds.size === rows.length}
                  onChange={selectAll}
                  title="Select all"
                />
              </th>
              {visibleColumns.map((key) => (
                <th key={key} className={key === 'Cat' ? 'col-cat' : key === 'Property' ? 'col-property' : key === 'Subcat' ? 'col-subcat' : ''}>
                  {key === 'needs_review' ? 'In review' : key}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.tx_id}
                className={[
                  row.needs_review ? 'in-review' : '',
                  (row.confidence != null && row.confidence < 0.85) || row.rule_strength === 'catch_all' ? 'best-guess' : '',
                  ['OurRent', 'Mortgage', 'PropertyExpense', 'BealsRent'].includes(row.Cat || row.category || '') && !(row.Property || row.property_code || '').trim() ? 'unusual' : '',
                ].filter(Boolean).join(' ')}
              >
                <td>
                  <input
                    type="checkbox"
                    checked={selectedTxIds.has(row.tx_id)}
                    onChange={() => toggleSelect(row.tx_id)}
                  />
                </td>
                {visibleColumns.map((key) => (
                  <td key={key} className={key === 'Cat' ? 'col-cat' : key === 'Property' ? 'col-property' : key === 'Subcat' ? 'col-subcat' : ''}>
                    {renderCell(row, key)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
