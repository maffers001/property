import { useParams, Link } from 'react-router-dom'
import { useEffect, useState, useCallback } from 'react'
import { getReview, getLists, reviewRemove, reviewCorrect, reviewSubmit } from '../api'
import type { DraftRow, DraftColumnKey, DraftFilters } from '../types'
import { DRAFT_COLUMN_KEYS } from '../types'
import Filters, { DEFAULT_FILTERS } from '../components/Filters'
import ColumnPicker from '../components/ColumnPicker'
import DraftTable from '../components/DraftTable'
import './Draft.css'

const COLUMNS_STORAGE_KEY = 'queueColumns'
const DEFAULT_VISIBLE: DraftColumnKey[] = ['Date', 'Account', 'Amount', 'Memo', 'Property', 'Cat', 'Subcat', 'confidence', 'needs_review']

function loadVisibleColumns(): DraftColumnKey[] {
  try {
    const s = localStorage.getItem(COLUMNS_STORAGE_KEY)
    if (s) {
      const arr = JSON.parse(s) as string[]
      if (Array.isArray(arr) && arr.every((k) => DRAFT_COLUMN_KEYS.includes(k as DraftColumnKey))) return arr as DraftColumnKey[]
    }
  } catch (_) {}
  return DEFAULT_VISIBLE
}

function saveVisibleColumns(cols: DraftColumnKey[]) {
  localStorage.setItem(COLUMNS_STORAGE_KEY, JSON.stringify(cols))
}

export default function Queue() {
  const { month } = useParams<{ month: string }>()
  const [rows, setRows] = useState<DraftRow[]>([])
  const [lists, setLists] = useState<{ property_codes: string[]; categories: string[]; subcategories: string[] } | null>(null)
  const [filters, setFilters] = useState<DraftFilters>(DEFAULT_FILTERS)
  const [visibleColumns, setVisibleColumns] = useState<DraftColumnKey[]>(loadVisibleColumns)
  const [selectedTxIds, setSelectedTxIds] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [showColumnPicker, setShowColumnPicker] = useState(false)
  const [filtersCollapsed, setFiltersCollapsed] = useState(false)

  const fetchQueue = useCallback(() => {
    if (!month) return
    setLoading(true)
    getReview(month, {
      property: filters.property.length ? filters.property.join(',') : undefined,
      category: filters.category.length ? filters.category.join(',') : undefined,
      subcategory: filters.subcategory.length ? filters.subcategory.join(',') : undefined,
      search: filters.search.trim() || undefined,
      date_from: filters.date_from || undefined,
      date_to: filters.date_to || undefined,
    })
      .then((data) => setRows(Array.isArray(data) ? data : []))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [month, filters.property.join(','), filters.category.join(','), filters.subcategory.join(','), filters.search, filters.date_from, filters.date_to])

  useEffect(() => {
    if (!month) return
    getLists().then(setLists).catch(() => {})
  }, [month])

  useEffect(() => {
    fetchQueue()
  }, [fetchQueue])

  const handleCorrect = (row: DraftRow, updates: { property_code: string; category: string; subcategory: string }) => {
    reviewCorrect(row.tx_id, updates.property_code, updates.category, updates.subcategory)
      .then(() => fetchQueue())
      .catch((e) => setError(e.message))
  }

  const handleRemoveFromReview = () => {
    if (!month || selectedTxIds.size === 0) return
    setSubmitting(true)
    reviewRemove(month, [...selectedTxIds])
      .then(() => { setSelectedTxIds(new Set()); fetchQueue() })
      .catch((e) => setError(e.message))
      .finally(() => setSubmitting(false))
  }

  const handleSubmitReview = () => {
    if (!month) return
    setSubmitting(true)
    reviewSubmit(month)
      .then(() => fetchQueue())
      .catch((e) => setError(e.message))
      .finally(() => setSubmitting(false))
  }

  const handleColumnsChange = (cols: DraftColumnKey[]) => {
    setVisibleColumns(cols)
    saveVisibleColumns(cols)
  }

  if (!month) return <p>Missing month</p>
  if (loading && rows.length === 0) return <p>Loading…</p>
  if (error) return <p className="error">{error}</p>

  const sumAmount = rows.reduce((s, r) => s + (Number(r.Amount) || 0), 0)
  const formatSum = (n: number) =>
    new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', minimumFractionDigits: 2 }).format(n)

  return (
    <div className="draft-page">
      <nav className="breadcrumb">
        <Link to="/home">Home</Link>
        <span> / </span>
        <Link to={`/review/${month}`}>{month}</Link>
        <span> / Queue</span>
      </nav>
      <h1>Review queue – {month}</h1>

      <div className="draft-toolbar">
        <Filters
          filters={filters}
          onChange={setFilters}
          lists={lists}
          collapsed={filtersCollapsed}
          onToggleCollapsed={() => setFiltersCollapsed((c) => !c)}
        />
        <button type="button" onClick={() => setShowColumnPicker(true)}>Columns</button>
      </div>

      <div className="draft-bulk">
        <span>{rows.length} rows in queue. {selectedTxIds.size} selected.</span>
        <span className="draft-sum">Sum: {formatSum(sumAmount)}</span>
        <div className="draft-bulk-btns">
          <button type="button" onClick={handleRemoveFromReview} disabled={selectedTxIds.size === 0 || submitting}>
            Remove from review
          </button>
          <button
            type="button"
            onClick={async () => {
              try {
                const csv = await getReview(month, {
                  property: filters.property.length ? filters.property.join(',') : undefined,
                  category: filters.category.length ? filters.category.join(',') : undefined,
                  subcategory: filters.subcategory.length ? filters.subcategory.join(',') : undefined,
                  search: filters.search.trim() || undefined,
                  date_from: filters.date_from || undefined,
                  date_to: filters.date_to || undefined,
                  format: 'csv',
                }) as string
                const blob = new Blob([csv], { type: 'text/csv' })
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = `review_queue_${month}.csv`
                a.click()
                URL.revokeObjectURL(url)
              } catch (e) {
                setError(e instanceof Error ? e.message : 'Download failed')
              }
            }}
          >
            Download CSV
          </button>
        </div>
      </div>

      <DraftTable
        rows={rows}
        visibleColumns={visibleColumns}
        selectedTxIds={selectedTxIds}
        onSelect={(ids) => setSelectedTxIds(new Set(ids))}
        onCorrect={handleCorrect}
        lists={lists}
      />

      <footer className="draft-footer">
        <button type="button" className="btn-primary" onClick={handleSubmitReview} disabled={rows.length === 0 || submitting}>
          Submit review
        </button>
        <span>{rows.length} in queue</span>
      </footer>

      {showColumnPicker && (
        <ColumnPicker
          visible={visibleColumns}
          onChange={handleColumnsChange}
          onClose={() => setShowColumnPicker(false)}
        />
      )}
    </div>
  )
}
