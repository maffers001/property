import type { DraftColumnKey } from '../types'
import { DRAFT_COLUMN_KEYS } from '../types'

const COLUMN_LABELS: Record<string, string> = {
  Date: 'Date',
  Account: 'Account',
  Amount: 'Amount',
  Memo: 'Memo',
  Property: 'Property',
  Cat: 'Category',
  Subcat: 'Subcategory',
  confidence: 'Confidence',
  needs_review: 'In review',
  tx_id: 'Transaction ID',
  Description: 'Description',
  Subcategory: 'Subcategory (effective)',
  rule_strength: 'Rule strength',
  reviewed_at: 'Reviewed at',
}

type Props = {
  visible: DraftColumnKey[]
  onChange: (visible: DraftColumnKey[]) => void
  onClose: () => void
}

export default function ColumnPicker({ visible, onChange, onClose }: Props) {
  const toggle = (key: DraftColumnKey) => {
    if (visible.includes(key)) {
      onChange(visible.filter((k) => k !== key))
    } else {
      onChange([...visible, key])
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal column-picker" onClick={(e) => e.stopPropagation()}>
        <h3>Columns</h3>
        <div className="column-picker-list">
          {DRAFT_COLUMN_KEYS.map((key) => (
            <label key={key}>
              <input
                type="checkbox"
                checked={visible.includes(key)}
                onChange={() => toggle(key)}
              />
              {COLUMN_LABELS[key] ?? key}
            </label>
          ))}
        </div>
        <button type="button" onClick={onClose}>Done</button>
      </div>
    </div>
  )
}
