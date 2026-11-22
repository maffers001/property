import { useMemo, useState } from 'react'
import { reviewSplitTenancy } from '../api'
import type { DraftRow } from '../types'
import './SaveRuleModal.css'

type Props = {
  row: DraftRow
  lists: { property_codes: string[]; categories: string[]; subcategories: string[] } | null
  onClose: () => void
  onSaved: (msg: string, meta: { parentTxId: string; reminder: string }) => void
}

function money(n: number) {
  return n.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const MONTHS: Record<string, number> = {
  jan: 1, january: 1,
  feb: 2, february: 2,
  mar: 3, march: 3,
  apr: 4, april: 4,
  may: 5,
  jun: 6, june: 6,
  jul: 7, july: 7,
  aug: 8, august: 8,
  sep: 9, sept: 9, september: 9,
  oct: 10, october: 10,
  nov: 11, november: 11,
  dec: 12, december: 12,
}

function pad2(n: number) {
  return String(n).padStart(2, '0')
}

function formatDdMmYy(d: Date) {
  const yy = String(d.getFullYear()).slice(-2)
  return `${pad2(d.getDate())}/${pad2(d.getMonth() + 1)}/${yy}`
}

/** First rent period: move-in day through day-before same date next month. */
function firstRentPeriodEnd(start: Date) {
  return new Date(start.getFullYear(), start.getMonth() + 1, start.getDate() - 1)
}

/**
 * Convert Sequence tenancy paste, e.g.
 * "Mr Arman Kibria, Ms Fatema Kubra Feb 26 2026 to Feb 25 2027 (T5261…)"
 * → "Rent for period 26/02/26-25/03/26 Mr Arman Kibria, Ms Fatema Kubra"
 */
export function formatRentMemoFromTenancyPaste(raw: string): string | null {
  const cleaned = raw
    .replace(/\([^)]*\)/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  if (!cleaned) return null

  const re =
    /\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2})\s+(\d{4})\s+to\b/i
  const m = cleaned.match(re)
  if (!m || m.index == null) return null

  const mon = MONTHS[m[1].toLowerCase()]
  const day = Number(m[2])
  const year = Number(m[3])
  if (!mon || !day || !year) return null

  const start = new Date(year, mon - 1, day)
  if (start.getFullYear() !== year || start.getMonth() !== mon - 1 || start.getDate() !== day) {
    return null
  }
  const end = firstRentPeriodEnd(start)
  const names = cleaned.slice(0, m.index).trim().replace(/[,\s]+$/, '')
  if (!names) return null

  return `Rent for period ${formatDdMmYy(start)}-${formatDdMmYy(end)} ${names}`
}

export default function SplitTenancyModal({ row, lists, onClose, onSaved }: Props) {
  const net = Number(row.Amount) || 0
  const [property, setProperty] = useState(row.Property || row.property_code || '')
  const [rentAmount, setRentAmount] = useState('')
  const [feeAmount, setFeeAmount] = useState('')
  const [feeTouched, setFeeTouched] = useState(false)
  const [rentMemo, setRentMemo] = useState('')
  const [feeMemo, setFeeMemo] = useState('Fox & Sons')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const rent = Number(rentAmount)
  const feeAuto = Number.isFinite(rent) && rentAmount.trim() !== '' ? Math.round((rent - net) * 100) / 100 : NaN
  const fee =
    feeTouched && feeAmount.trim() !== ''
      ? Number(feeAmount)
      : feeAuto

  const previewOk = useMemo(() => {
    if (!Number.isFinite(rent) || rent <= 0) return false
    if (!Number.isFinite(fee) || fee < 0) return false
    return Math.abs(rent - fee - net) < 0.015
  }, [rent, fee, net])

  const handleRentChange = (v: string) => {
    setRentAmount(v)
    if (!feeTouched) setFeeAmount('')
  }

  const handleSave = async () => {
    setError('')
    if (!property.trim()) {
      setError('Property required')
      return
    }
    if (!Number.isFinite(rent) || rent <= 0) {
      setError('Enter gross rent (positive)')
      return
    }
    if (!Number.isFinite(fee) || fee < 0) {
      setError('Agent fees must be zero or positive')
      return
    }
    if (!previewOk) {
      setError(`Rent − fees must equal net £${money(net)}`)
      return
    }
    setSaving(true)
    try {
      const res = await reviewSplitTenancy({
        tx_id: row.tx_id,
        property_code: property.trim(),
        rent_amount: rent,
        fee_amount: fee,
        rent_memo: rentMemo.trim(),
        fee_memo: feeMemo.trim() || 'Fox & Sons',
      })
      onSaved(
        `New tenancy: OurRent £${money(res.rent_amount)} and PropertyExpense £${money(Math.abs(res.fee_amount))}`,
        { parentTxId: res.parent_tx_id, reminder: res.reminder },
      )
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Split failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="modal-card"
        role="dialog"
        aria-label="New tenancy"
        onClick={(e) => e.stopPropagation()}
      >
        <h2>New tenancy</h2>
        <p className="muted">
          Replace this net agent payment with gross rent (OurRent) and letting-agent fees
          (PropertyExpense). Both rows stay in review. Update <code>all_tenancies.xls</code> after.
        </p>
        <p className="muted">
          {row.Date} · {row.Memo || '—'} · net <strong>£{money(net)}</strong>
        </p>

        <label>
          Property
          <select
            value={property}
            onChange={(e) => setProperty(e.target.value)}
            aria-label="Property"
          >
            <option value="">—</option>
            {(lists?.property_codes || []).map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </label>

        <label>
          Gross rent (£)
          <input
            type="number"
            step="0.01"
            min="0"
            value={rentAmount}
            onChange={(e) => handleRentChange(e.target.value)}
            placeholder="e.g. 825.00"
            aria-label="Gross rent"
          />
        </label>

        <label>
          Agent fees (£)
          <input
            type="number"
            step="0.01"
            min="0"
            value={feeTouched ? feeAmount : (Number.isFinite(feeAuto) ? String(feeAuto) : '')}
            onChange={(e) => {
              setFeeTouched(true)
              setFeeAmount(e.target.value)
            }}
            placeholder="auto = rent − net"
            aria-label="Agent fees"
          />
        </label>

        <label>
          Rent memo
          <input
            value={rentMemo}
            onChange={(e) => setRentMemo(e.target.value)}
            placeholder="Paste tenant line, or Rent for period …"
            aria-label="Rent memo"
          />
        </label>
        <div className="memo-format-row">
          <button
            type="button"
            className="btn-quiet"
            disabled={!rentMemo.trim()}
            onClick={() => {
              const formatted = formatRentMemoFromTenancyPaste(rentMemo)
              if (!formatted) {
                setError(
                  'Could not parse tenancy paste. Expected e.g. “Mr … Feb 26 2026 to Feb 25 2027 (ref)”',
                )
                return
              }
              setError('')
              setRentMemo(formatted)
            }}
            title="Convert Sequence tenancy line to Rent for period DD/MM/YY-DD/MM/YY …"
          >
            Format from tenancy paste
          </button>
        </div>

        <label>
          Fee memo
          <input
            value={feeMemo}
            onChange={(e) => setFeeMemo(e.target.value)}
            aria-label="Fee memo"
          />
        </label>

        <p className={previewOk ? 'match-ok' : 'match-fail'} role="status">
          {Number.isFinite(rent) && Number.isFinite(fee)
            ? `Preview: OurRent +£${money(rent)} · PropertyExpense −£${money(fee)} · net £${money(rent - fee)}`
            : 'Enter gross rent to preview the split'}
          {Number.isFinite(rent) && Number.isFinite(fee) && !previewOk
            ? ` (must equal £${money(net)})`
            : ''}
        </p>

        {error && <p className="error">{error}</p>}
        <div className="modal-actions">
          <button type="button" onClick={onClose}>Cancel</button>
          <button type="button" className="btn-primary" onClick={handleSave} disabled={saving || !previewOk}>
            {saving ? 'Saving…' : 'Create rows'}
          </button>
        </div>
      </div>
    </div>
  )
}
