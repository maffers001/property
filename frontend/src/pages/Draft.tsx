import { useParams, Link } from 'react-router-dom'
import { useEffect, useState, useCallback, useMemo, useRef } from 'react'
import { getDraft, getLists, reviewAdd, reviewRemove, reviewCorrect, reviewComplete, reviewSubmit, reviewAddByRule, deleteRule } from '../api'
import type { DraftRow, DraftColumnKey, DraftFilters } from '../types'
import { DRAFT_COLUMN_KEYS } from '../types'
import Filters, { DEFAULT_FILTERS } from '../components/Filters'
import ColumnPicker from '../components/ColumnPicker'
import DraftTable from '../components/DraftTable'
import SaveRuleModal from '../components/SaveRuleModal'
import BulkEditModal from '../components/BulkEditModal'
import './Draft.css'

const COLUMNS_STORAGE_KEY = 'draftColumns'
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

function rowSearchText(r: DraftRow) {
  return [
    r.Memo, r.match_text, r.counterparty, r.Description,
    r.Account, r.Date, r.Cat, r.Subcat, r.Property, r.property_code,
  ].map((x) => String(x ?? '')).join(' ').toLowerCase()
}

function applyDraftFilters(
  rows: DraftRow[],
  filters: DraftFilters,
  lists: { property_codes: string[]; categories: string[]; subcategories: string[] } | null,
  needsReviewOnly: boolean,
) {
  let out = rows
  if (needsReviewOnly) out = out.filter((r) => r.needs_review === 1)
  const propSel = filters.property
  if (propSel.length && !(lists && propSel.length === lists.property_codes.length)) {
    const allow = new Set(propSel)
    out = out.filter((r) => allow.has(r.Property || r.property_code || ''))
  }
  const catSel = filters.category
  if (catSel.length && !(lists && catSel.length === lists.categories.length)) {
    const allow = new Set(catSel)
    out = out.filter((r) => allow.has(r.Cat || r.category || ''))
  }
  const subSel = filters.subcategory
  if (subSel.length && !(lists && subSel.length === lists.subcategories.length)) {
    const allow = new Set(subSel)
    out = out.filter((r) => allow.has(r.Subcat || r.subcategory || ''))
  }
  const q = filters.search.trim().toLowerCase()
  if (q) out = out.filter((r) => rowSearchText(r).includes(q))
  const from = filters.date_from
  const to = filters.date_to
  if (from || to) {
    out = out.filter((r) => {
      const d = (r.Date || '').slice(0, 10)
      if (!d) return true
      if (from && d < from) return false
      if (to && d > to) return false
      return true
    })
  }
  return out
}

export default function Draft() {
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
  const [ruleRow, setRuleRow] = useState<DraftRow | null>(null)
  const [ruleMessage, setRuleMessage] = useState('')
  const [needsReviewOnly, setNeedsReviewOnly] = useState(true)
  const [bulkOpen, setBulkOpen] = useState(false)
  const [undo, setUndo] = useState<{ label: string; run: () => Promise<void> } | null>(null)
  const undoTimer = useRef<number | null>(null)

  const offerUndo = useCallback((label: string, run: () => Promise<void>) => {
    if (undoTimer.current) window.clearTimeout(undoTimer.current)
    setUndo({ label, run })
    undoTimer.current = window.setTimeout(() => setUndo(null), 12000)
  }, [])

  useEffect(() => () => {
    if (undoTimer.current) window.clearTimeout(undoTimer.current)
  }, [])

  const fetchDraft = useCallback(() => {
    if (!month) return
    getDraft(month)
      .then((data) => setRows(Array.isArray(data) ? data : []))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [month])

  useEffect(() => {
    if (!month) return
    getLists().then(setLists).catch(() => {})
  }, [month])

  useEffect(() => {
    fetchDraft()
  }, [fetchDraft])

  const handleCorrect = (row: DraftRow, updates: { property_code: string; category: string; subcategory: string }) => {
    reviewCorrect(row.tx_id, updates.property_code, updates.category, updates.subcategory)
      .then(() => fetchDraft())
      .catch((e) => setError(e.message))
  }

  const handleAddToReview = () => {
    if (!month || selectedTxIds.size === 0) return
    setSubmitting(true)
    reviewAdd(month, [...selectedTxIds])
      .then(() => { setSelectedTxIds(new Set()); fetchDraft() })
      .catch((e) => setError(e.message))
      .finally(() => setSubmitting(false))
  }

  const handleRemoveFromReview = () => {
    if (!month || selectedTxIds.size === 0) return
    setSubmitting(true)
    reviewRemove(month, [...selectedTxIds])
      .then(() => { setSelectedTxIds(new Set()); fetchDraft() })
      .catch((e) => setError(e.message))
      .finally(() => setSubmitting(false))
  }

  const handleSubmitReview = () => {
    if (!month) return
    setSubmitting(true)
    reviewSubmit(month)
      .then(() => fetchDraft())
      .catch((e) => setError(e.message))
      .finally(() => setSubmitting(false))
  }

  const handleColumnsChange = (cols: DraftColumnKey[]) => {
    setVisibleColumns(cols)
    saveVisibleColumns(cols)
  }

  const inReview = rows.filter((r) => r.needs_review === 1).length
  const visibleRows = useMemo(
    () => applyDraftFilters(rows, filters, lists, needsReviewOnly),
    [rows, filters, lists, needsReviewOnly],
  )
  const selectedRows = useMemo(
    () => visibleRows.filter((r) => selectedTxIds.has(r.tx_id)),
    [visibleRows, selectedTxIds],
  )
  const sumAmount = visibleRows.reduce((s, r) => s + (Number(r.Amount) || 0), 0)
  const formatSum = (n: number) =>
    new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', minimumFractionDigits: 2 }).format(n)

  if (!month) return <p>Missing month</p>
  if (loading && rows.length === 0) return <p>Loading…</p>
  if (error) return <p className="error">{error}</p>

  return (
    <div className="draft-page">
      <nav className="breadcrumb">
        <Link to="/home">Home</Link>
        <span> / </span>
        <span>{month}</span>
      </nav>
      <h1>Review – {month}</h1>
      <p className="queue-scope">
        {needsReviewOnly
          ? `Showing ${visibleRows.length} of ${rows.length} rows that need review. Switch to all transactions to fix anything else.`
          : `Showing ${visibleRows.length} of ${rows.length} transactions. ${inReview} still flagged for review.`}
      </p>

      <label className="queue-all-months">
        <input
          type="checkbox"
          checked={needsReviewOnly}
          onChange={(e) => setNeedsReviewOnly(e.target.checked)}
        />
        Needs review only
      </label>

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
        <span>{visibleRows.length} shown. {inReview} need review. {selectedTxIds.size} selected.</span>
        <span className="draft-sum">Sum: {formatSum(sumAmount)}</span>
        <div className="draft-bulk-btns">
          <button
            type="button"
            className="btn-primary"
            onClick={() => setBulkOpen(true)}
            disabled={selectedRows.length === 0 || submitting}
          >
            Edit selected
          </button>
          <button type="button" onClick={handleAddToReview} disabled={selectedTxIds.size === 0 || submitting}>
            Add selected to review
          </button>
          <button type="button" onClick={handleRemoveFromReview} disabled={selectedTxIds.size === 0 || submitting}>
            Remove from review
          </button>
          <button
            type="button"
            onClick={() => {
              setSubmitting(true)
              reviewAddByRule(month, { property_empty: true })
                .then(() => fetchDraft())
                .catch((e) => setError(e.message))
                .finally(() => setSubmitting(false))
            }}
            disabled={submitting}
            title="Add all rows where category is OurRent/Mortgage/PropertyExpense/BealsRent and property is empty"
          >
            Add to review (no property where required)
          </button>
          <button
            type="button"
            onClick={() => {
              const cols = ['Date', 'Account', 'Amount', 'Memo', 'Property', 'Cat', 'Subcat', 'confidence', 'needs_review', 'tx_id']
              const esc = (v: unknown) => `"${String(v ?? '').replace(/"/g, '""')}"`
              const header = cols.join(',')
              const lines = visibleRows.map((r) =>
                cols.map((c) => esc((r as Record<string, unknown>)[c])).join(','),
              )
              const csv = [header, ...lines].join('\n')
              const blob = new Blob([csv], { type: 'text/csv' })
              const url = URL.createObjectURL(blob)
              const a = document.createElement('a')
              a.href = url
              a.download = needsReviewOnly ? `review_${month}_needs_review.csv` : `review_${month}.csv`
              a.click()
              URL.revokeObjectURL(url)
            }}
          >
            Download CSV
          </button>
        </div>
      </div>

      <DraftTable
        rows={visibleRows}
        visibleColumns={visibleColumns}
        selectedTxIds={selectedTxIds}
        onSelect={(ids) => setSelectedTxIds(new Set(ids))}
        onCorrect={handleCorrect}
        onComplete={(row) => {
          if (!month) return
          reviewComplete(month, [row.tx_id])
            .then(() => {
              fetchDraft()
              offerUndo('Marked as reviewed', async () => {
                await reviewAdd(month, [row.tx_id])
                fetchDraft()
              })
            })
            .catch((e) => setError(e instanceof Error ? e.message : 'Failed'))
        }}
        onSaveRule={setRuleRow}
        lists={lists}
      />

      <footer className="draft-footer">
        <button type="button" className="btn-primary" onClick={handleSubmitReview} disabled={inReview === 0 || submitting}>
          Done reviewing
        </button>
        <span>{inReview} still flagged — edit labels as needed, then Mark reviewed or Done reviewing. Then finalize the month.</span>
      </footer>

      {undo && (
        <div className="undo-bar" role="status">
          <span>{undo.label}</span>
          <button
            type="button"
            onClick={() => {
              const action = undo
              if (undoTimer.current) window.clearTimeout(undoTimer.current)
              setUndo(null)
              action.run().catch((e) => setError(e instanceof Error ? e.message : 'Undo failed'))
            }}
          >
            Undo
          </button>
        </div>
      )}
      {ruleMessage && !undo && <p className="muted">{ruleMessage}</p>}
      {ruleRow && (
        <SaveRuleModal
          row={ruleRow}
          onClose={() => setRuleRow(null)}
          onSaved={(msg, meta) => {
            setRuleMessage(msg)
            if (meta?.ruleIds?.length) {
              offerUndo('Saved as rule', async () => {
                for (const id of meta.ruleIds) {
                  await deleteRule(id)
                }
                setRuleMessage('Rule save undone')
              })
            }
          }}
        />
      )}
      {bulkOpen && selectedRows.length > 0 && (
        <BulkEditModal
          rows={selectedRows}
          lists={lists}
          onClose={() => setBulkOpen(false)}
          onSaved={(msg, meta) => {
            setRuleMessage(msg)
            setSelectedTxIds(new Set())
            fetchDraft()
            if (meta?.ruleIds?.length) {
              offerUndo('Saved as rule', async () => {
                for (const id of meta.ruleIds) {
                  await deleteRule(id)
                }
                setRuleMessage('Rule save undone')
              })
            }
          }}
        />
      )}
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
