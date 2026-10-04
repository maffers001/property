import { useEffect, useState } from 'react'
import { saveRuleFromReview, suggestRulePattern, testRulePattern, reviewCorrectBulk } from '../api'
import type { DraftRow } from '../types'
import './SaveRuleModal.css'

type OtherMatch = {
  tx_id: string
  month: string
  date: string
  account: string
  amount: number
  memo: string
  property_code: string
  category: string
  subcategory: string
  conflict: boolean
}

type Props = {
  row: DraftRow
  onClose: () => void
  onSaved: (msg: string, meta?: { ruleIds: string[] }) => void
}

function money(n: number) {
  if (n == null || Number.isNaN(Number(n))) return ''
  return Number(n).toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function SaveRuleModal({ row, onClose, onSaved }: Props) {
  const property = row.Property ?? row.property_code ?? ''
  const category = row.Cat ?? row.category ?? ''
  const subcategory = row.Subcat ?? row.subcategory ?? ''
  const [pattern, setPattern] = useState('')
  const [phase, setPhase] = useState(property && !category && !subcategory ? 'property' : 'override')
  const [prop, setProp] = useState(property)
  const [cat, setCat] = useState(category)
  const [sub, setSub] = useState(subcategory)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [sample, setSample] = useState(row.match_text || row.counterparty || row.Memo || '')
  const [matched, setMatched] = useState<boolean | null>(null)
  const [testError, setTestError] = useState('')
  const [testing, setTesting] = useState(false)
  const [others, setOthers] = useState<OtherMatch[]>([])
  const [otherCount, setOtherCount] = useState(0)
  const [conflictCount, setConflictCount] = useState(0)
  const [applyAllMatches, setApplyAllMatches] = useState(true)

  useEffect(() => {
    suggestRulePattern(row.Memo || '', row.counterparty, row.match_text)
      .then((r) => setPattern(r.pattern))
      .catch(() => {
        const raw = (row.match_text || row.counterparty || row.Memo || '').trim()
        setPattern(raw ? `.*${raw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}.*` : '.*')
      })
  }, [row])

  useEffect(() => {
    if (!pattern.trim()) {
      setMatched(null)
      setTestError('Pattern required')
      setOthers([])
      setOtherCount(0)
      setConflictCount(0)
      return
    }
    let cancelled = false
    setTesting(true)
    const t = window.setTimeout(() => {
      testRulePattern({
        pattern: pattern.trim(),
        memo: row.Memo,
        counterparty: row.counterparty,
        match_text: row.match_text,
        exclude_tx_id: row.tx_id,
        property_code: prop,
        category: cat,
        subcategory: sub,
      })
        .then((res) => {
          if (cancelled) return
          setSample(res.sample || row.match_text || row.Memo || '')
          setMatched(res.matched)
          setTestError(res.error || '')
          setOthers(res.others || [])
          setOtherCount(res.other_count ?? 0)
          setConflictCount(res.conflict_count ?? 0)
        })
        .catch((e) => {
          if (cancelled) return
          setMatched(false)
          setTestError(e instanceof Error ? e.message : 'Could not test pattern')
          setOthers([])
          setOtherCount(0)
          setConflictCount(0)
        })
        .finally(() => {
          if (!cancelled) setTesting(false)
        })
    }, 280)
    return () => {
      cancelled = true
      window.clearTimeout(t)
    }
  }, [pattern, row, prop, cat, sub])

  const handleSave = async () => {
    setError('')
    if (!pattern.trim()) {
      setError('Pattern required')
      return
    }
    if (!prop.trim() && !cat.trim() && !sub.trim()) {
      setError('Set at least a property, category, or subcategory')
      return
    }
    if (testError) {
      setError(testError)
      return
    }
    if (matched !== true) {
      setError('Pattern does not match this transaction. Edit the regex until it matches.')
      return
    }
    setSaving(true)
    try {
      const res = await saveRuleFromReview({
        memo: row.Memo,
        counterparty: row.counterparty,
        match_text: row.match_text,
        property_code: prop,
        category: cat,
        subcategory: sub,
        pattern: pattern.trim(),
        phase,
        strength: 'strong',
      })
      let msg = `Saved ${res.rules.length} rule(s) with pattern ${res.pattern}`
      if (applyAllMatches) {
        const applied = await reviewCorrectBulk(
          [row.tx_id],
          prop,
          cat,
          sub,
          pattern.trim(),
        )
        msg += ` and updated ${applied.count} matching row${applied.count === 1 ? '' : 's'}`
      }
      onSaved(msg, { ruleIds: res.rules.map((r) => r.rule_id) })
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save rule')
    } finally {
      setSaving(false)
    }
  }

  const matchClass = matched === true ? 'match-ok' : matched === false ? 'match-fail' : ''

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div className="modal-card modal-card-wide" onClick={(e) => e.stopPropagation()} role="dialog" aria-labelledby="save-rule-title">
        <h2 id="save-rule-title">Save as rule</h2>
        <p className="muted">
          Optional. Matching transactions in later months will get these labels. Engine uses Python <code>re.match</code> (case-insensitive, from the start of the text).
        </p>
        <p className="muted"><strong>Memo:</strong> {row.Memo || '—'}</p>
        <p className="sample-text"><strong>Test text:</strong> {sample || '—'}</p>
        <label>
          Regex pattern
          <input value={pattern} onChange={(e) => setPattern(e.target.value)} aria-label="Regex pattern" />
        </label>
        <p className={`match-status ${matchClass}`} role="status">
          {testing && 'Testing…'}
          {!testing && testError && testError}
          {!testing && !testError && matched === true && 'Matches this transaction'}
          {!testing && !testError && matched === false && 'Does not match — edit the pattern before saving'}
        </p>
        <label>
          Phase
          <select value={phase} onChange={(e) => setPhase(e.target.value)} aria-label="Rule phase">
            <option value="override">override (category / subcategory)</option>
            <option value="property">property</option>
            <option value="category">category</option>
            <option value="subcategory">subcategory</option>
          </select>
        </label>
        <label>
          Property
          <input value={prop} onChange={(e) => setProp(e.target.value)} aria-label="Property output" />
        </label>
        <label>
          Category
          <input value={cat} onChange={(e) => setCat(e.target.value)} aria-label="Category output" />
        </label>
        <label>
          Subcategory
          <input value={sub} onChange={(e) => setSub(e.target.value)} aria-label="Subcategory output" />
        </label>

        <div className="other-matches">
          <h3>Other matching rows</h3>
          {!testing && otherCount === 0 && matched === true && (
            <p className="muted">No other imported transactions match this pattern.</p>
          )}
          {otherCount > 0 && (
            <p className={conflictCount ? 'match-fail' : 'muted'}>
              Would also match {otherCount} other row{otherCount === 1 ? '' : 's'}
              {conflictCount > 0
                ? ` — ${conflictCount} already ha${conflictCount === 1 ? 's' : 've'} different Property/Cat/Subcat`
                : ''}
              {otherCount > others.length ? ` (showing first ${others.length})` : ''}.
            </p>
          )}
          {others.length > 0 && (
            <div className="other-matches-wrap">
              <table className="other-matches-table">
                <thead>
                  <tr>
                    <th>Month</th>
                    <th>Date</th>
                    <th>Amount</th>
                    <th>Memo</th>
                    <th>Property</th>
                    <th>Cat</th>
                    <th>Subcat</th>
                  </tr>
                </thead>
                <tbody>
                  {others.map((m) => (
                    <tr key={m.tx_id} className={m.conflict ? 'row-conflict' : ''}>
                      <td>{m.month}</td>
                      <td>{m.date}</td>
                      <td className="num">{money(m.amount)}</td>
                      <td className="memo">{m.memo}</td>
                      <td>{m.property_code || '—'}</td>
                      <td>{m.category || '—'}</td>
                      <td>{m.subcategory || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <label className="queue-all-months">
          <input
            type="checkbox"
            checked={applyAllMatches}
            onChange={(e) => setApplyAllMatches(e.target.checked)}
          />
          Also update all matching records
          {otherCount > 0 ? ` (${otherCount} besides this one)` : ''}
        </label>

        {error && <p className="error">{error}</p>}
        <div className="modal-actions">
          <button type="button" onClick={onClose}>Cancel</button>
          <button
            type="button"
            className="btn-primary"
            onClick={handleSave}
            disabled={saving || testing || matched !== true}
          >
            {saving ? 'Saving…' : 'Save rule'}
          </button>
        </div>
      </div>
    </div>
  )
}
