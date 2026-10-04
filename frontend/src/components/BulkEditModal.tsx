import { useEffect, useMemo, useState } from 'react'
import {
  reviewCorrectBulk,
  saveRuleFromReview,
  suggestPatternFromSamples,
  testRulePattern,
} from '../api'
import type { DraftRow } from '../types'
import './SaveRuleModal.css'

type OtherMatch = {
  tx_id: string
  month: string
  date: string
  amount: number
  memo: string
  property_code: string
  category: string
  subcategory: string
  conflict: boolean
}

type Props = {
  rows: DraftRow[]
  lists: { property_codes: string[]; categories: string[]; subcategories: string[] } | null
  onClose: () => void
  onSaved: (msg: string, meta?: { ruleIds: string[] }) => void
}

function sampleOf(r: DraftRow) {
  return (r.match_text || r.counterparty || r.Memo || '').trim()
}

function commonValue(values: string[]) {
  const first = values[0] || ''
  return values.every((v) => v === first) ? first : ''
}

export default function BulkEditModal({ rows, lists, onClose, onSaved }: Props) {
  const samples = useMemo(() => rows.map(sampleOf).filter(Boolean), [rows])
  const [prop, setProp] = useState(() =>
    commonValue(rows.map((r) => r.Property || r.property_code || '')),
  )
  const [cat, setCat] = useState(() => commonValue(rows.map((r) => r.Cat || r.category || '')))
  const [sub, setSub] = useState(() =>
    commonValue(rows.map((r) => r.Subcat || r.subcategory || '')),
  )
  const [pattern, setPattern] = useState('')
  const [saveRule, setSaveRule] = useState(true)
  const [applyAllMatches, setApplyAllMatches] = useState(true)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [selectedMatched, setSelectedMatched] = useState(0)
  const [selectedCount, setSelectedCount] = useState(rows.length)
  const [missed, setMissed] = useState<string[]>([])
  const [others, setOthers] = useState<OtherMatch[]>([])
  const [otherCount, setOtherCount] = useState(0)
  const [conflictCount, setConflictCount] = useState(0)
  const [testError, setTestError] = useState('')

  useEffect(() => {
    suggestPatternFromSamples(samples)
      .then((r) => setPattern(r.pattern))
      .catch(() => setPattern('.*'))
  }, [samples])

  useEffect(() => {
    if (!pattern.trim()) {
      setTestError('Pattern required')
      return
    }
    let cancelled = false
    setTesting(true)
    const t = window.setTimeout(() => {
      const first = rows[0]
      testRulePattern({
        pattern: pattern.trim(),
        memo: first?.Memo,
        match_text: first?.match_text || first?.Memo,
        exclude_tx_ids: rows.map((r) => r.tx_id),
        samples,
        property_code: prop,
        category: cat,
        subcategory: sub,
      })
        .then((res) => {
          if (cancelled) return
          setTestError(res.error || '')
          setSelectedMatched(res.selected_matched ?? 0)
          setSelectedCount(res.selected_count ?? samples.length)
          setMissed(res.selected_missed || [])
          setOthers(res.others || [])
          setOtherCount(res.other_count ?? 0)
          setConflictCount(res.conflict_count ?? 0)
        })
        .catch((e) => {
          if (cancelled) return
          setTestError(e instanceof Error ? e.message : 'Could not test pattern')
        })
        .finally(() => {
          if (!cancelled) setTesting(false)
        })
    }, 280)
    return () => {
      cancelled = true
      window.clearTimeout(t)
    }
  }, [pattern, samples, rows, prop, cat, sub])

  const allSelectedMatch = selectedCount > 0 && selectedMatched === selectedCount && !testError

  const handleApply = async () => {
    setError('')
    if (!prop.trim() && !cat.trim() && !sub.trim()) {
      setError('Set at least a property, category, or subcategory')
      return
    }
    if (saveRule && !allSelectedMatch) {
      setError('The suggested rule does not match every selected row. Widen the pattern or uncheck Save as rule.')
      return
    }
    setSaving(true)
    try {
      const applyPattern = saveRule && applyAllMatches ? pattern.trim() : ''
      const resBulk = await reviewCorrectBulk(
        rows.map((r) => r.tx_id),
        prop,
        cat,
        sub,
        applyPattern,
      )
      let msg = `Updated ${resBulk.count} row${resBulk.count === 1 ? '' : 's'}`
      let ruleIds: string[] = []
      if (saveRule) {
        const res = await saveRuleFromReview({
          memo: rows[0]?.Memo,
          match_text: rows[0]?.match_text || rows[0]?.Memo,
          property_code: prop,
          category: cat,
          subcategory: sub,
          pattern: pattern.trim(),
          phase: prop && !cat && !sub ? 'property' : 'override',
          strength: 'strong',
        })
        ruleIds = res.rules.map((r) => r.rule_id)
        msg += ` and saved ${res.rules.length} rule(s)`
      }
      onSaved(msg, ruleIds.length ? { ruleIds } : undefined)
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to apply')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div className="modal-card modal-card-wide" onClick={(e) => e.stopPropagation()} role="dialog">
        <h2>Edit {rows.length} selected rows</h2>
        <p className="muted">
          These labels are applied to every checked row. A rule is suggested from what the memos have in common so later months can match too.
        </p>
        <label>
          Property
          <select value={prop} onChange={(e) => setProp(e.target.value)} aria-label="Property">
            <option value="">—</option>
            {lists?.property_codes.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </label>
        <label>
          Category
          <select value={cat} onChange={(e) => setCat(e.target.value)} aria-label="Category">
            <option value="">—</option>
            {lists?.categories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </label>
        <label>
          Subcategory
          <select value={sub} onChange={(e) => setSub(e.target.value)} aria-label="Subcategory">
            <option value="">—</option>
            {lists?.subcategories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </label>
        <label>
          Suggested regex
          <input value={pattern} onChange={(e) => setPattern(e.target.value)} aria-label="Suggested regex" />
        </label>
        <p className={`match-status ${allSelectedMatch ? 'match-ok' : 'match-fail'}`} role="status">
          {testing && 'Testing…'}
          {!testing && testError && testError}
          {!testing && !testError && allSelectedMatch && `Matches all ${selectedCount} selected rows`}
          {!testing && !testError && !allSelectedMatch &&
            `Matches ${selectedMatched} of ${selectedCount} selected rows — edit the pattern so it covers them all`}
        </p>
        {missed.length > 0 && (
          <ul className="missed-samples">
            {missed.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        )}
        <label className="queue-all-months">
          <input type="checkbox" checked={saveRule} onChange={(e) => setSaveRule(e.target.checked)} />
          Also save as rule
        </label>
        {saveRule && (
          <label className="queue-all-months">
            <input
              type="checkbox"
              checked={applyAllMatches}
              onChange={(e) => setApplyAllMatches(e.target.checked)}
            />
            Also update all matching records
            {otherCount > 0 ? ` (${otherCount} besides the selection)` : ''}
          </label>
        )}
        {otherCount > 0 && (
          <p className={conflictCount ? 'match-fail' : 'muted'}>
            Would also match {otherCount} other imported row{otherCount === 1 ? '' : 's'}
            {conflictCount > 0 ? ` (${conflictCount} with different labels)` : ''}.
          </p>
        )}
        {others.length > 0 && (
          <div className="other-matches-wrap">
            <table className="other-matches-table">
              <thead>
                <tr>
                  <th>Month</th>
                  <th>Date</th>
                  <th>Memo</th>
                  <th>Cat</th>
                  <th>Subcat</th>
                </tr>
              </thead>
              <tbody>
                {others.map((m) => (
                  <tr key={m.tx_id} className={m.conflict ? 'row-conflict' : ''}>
                    <td>{m.month}</td>
                    <td>{m.date}</td>
                    <td className="memo">{m.memo}</td>
                    <td>{m.category || '—'}</td>
                    <td>{m.subcategory || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {error && <p className="error">{error}</p>}
        <div className="modal-actions">
          <button type="button" onClick={onClose}>Cancel</button>
          <button type="button" className="btn-primary" onClick={handleApply} disabled={saving || testing}>
            {saving ? 'Saving…' : saveRule ? 'Apply labels and save rule' : 'Apply labels'}
          </button>
        </div>
      </div>
    </div>
  )
}
