import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  createRule,
  deleteRule,
  getRules,
  updateRule,
  type RuleRow,
} from '../api'
import './Rules.css'

const PHASES = ['property', 'category', 'subcategory', 'override'] as const
const STRENGTHS = ['strong', 'medium', 'weak', 'catch_all'] as const

type SortKey =
  | 'rule_id'
  | 'phase'
  | 'pattern'
  | 'property_code'
  | 'category'
  | 'subcategory'
  | 'strength'
  | 'order_index'
  | 'enabled'
  | 'updated_at'

const SORT_COLUMNS: { key: SortKey; label: string }[] = [
  { key: 'rule_id', label: 'ID' },
  { key: 'updated_at', label: 'Edited' },
  { key: 'phase', label: 'Phase' },
  { key: 'pattern', label: 'Pattern' },
  { key: 'property_code', label: 'Property' },
  { key: 'category', label: 'Cat' },
  { key: 'subcategory', label: 'Subcat' },
  { key: 'strength', label: 'Str' },
  { key: 'order_index', label: 'Ord' },
  { key: 'enabled', label: 'On' },
]

function sortValue(r: RuleRow, key: SortKey): string | number {
  if (key === 'order_index' || key === 'enabled') return r[key]
  if (key === 'updated_at') return r.updated_at || ''
  return (r[key] || '').toString().toLowerCase()
}

function formatEdited(iso?: string) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(d)
}

const EMPTY_FORM = {
  phase: 'override',
  pattern: '',
  property_code: '',
  category: '',
  subcategory: '',
  strength: 'strong',
  order_index: -1,
  enabled: 1,
}

function toForm(r: RuleRow) {
  return {
    phase: r.phase,
    pattern: r.pattern,
    property_code: r.property_code,
    category: r.category,
    subcategory: r.subcategory,
    strength: r.strength,
    order_index: r.order_index,
    enabled: r.enabled,
  }
}

export default function Rules() {
  const [rules, setRules] = useState<RuleRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [filter, setFilter] = useState<'all' | 'learned' | 'disabled'>('all')
  const [search, setSearch] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [adding, setAdding] = useState(false)
  const [saving, setSaving] = useState(false)
  const [sortKey, setSortKey] = useState<SortKey>('updated_at')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  const load = useCallback(() => {
    getRules()
      .then((data) => setRules(Array.isArray(data) ? data : []))
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load rules'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir(key === 'updated_at' ? 'desc' : 'asc')
    }
  }

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase()
    const filtered = rules.filter((r) => {
      if (filter === 'learned' && !r.learned) return false
      if (filter === 'disabled' && r.enabled) return false
      if (!q) return true
      return (
        r.rule_id.toLowerCase().includes(q) ||
        r.pattern.toLowerCase().includes(q) ||
        r.property_code.toLowerCase().includes(q) ||
        r.category.toLowerCase().includes(q) ||
        r.subcategory.toLowerCase().includes(q)
      )
    })
    const dir = sortDir === 'asc' ? 1 : -1
    return [...filtered].sort((a, b) => {
      const av = sortValue(a, sortKey)
      const bv = sortValue(b, sortKey)
      if (!av && bv) return 1
      if (av && !bv) return -1
      if (av < bv) return -1 * dir
      if (av > bv) return 1 * dir
      return a.rule_id.localeCompare(b.rule_id) * dir
    })
  }, [rules, filter, search, sortKey, sortDir])

  const startEdit = (r: RuleRow) => {
    setAdding(false)
    setEditingId(r.rule_id)
    setForm(toForm(r))
    setError('')
    setMessage('')
  }

  const startAdd = () => {
    setEditingId(null)
    setAdding(true)
    setForm(EMPTY_FORM)
    setError('')
    setMessage('')
  }

  const cancel = () => {
    setEditingId(null)
    setAdding(false)
    setForm(EMPTY_FORM)
  }

  const persist = async (ruleId: string | null) => {
    setError('')
    setMessage('')
    if (!form.pattern.trim()) {
      setError('Pattern required')
      return
    }
    if (!form.property_code.trim() && !form.category.trim() && !form.subcategory.trim()) {
      setError('Set at least a property, category, or subcategory')
      return
    }
    setSaving(true)
    try {
      const body = {
        phase: form.phase,
        pattern: form.pattern.trim(),
        property_code: form.property_code,
        category: form.category,
        subcategory: form.subcategory,
        strength: form.strength,
        order_index: Number(form.order_index),
        enabled: Number(form.enabled),
      }
      if (ruleId) {
        const updated = await updateRule(ruleId, body)
        setRules((prev) => prev.map((r) => (r.rule_id === updated.rule_id ? { ...r, ...updated } : r)))
        setMessage(`Updated ${ruleId}`)
      } else {
        const created = await createRule(body)
        setRules((prev) => [created, ...prev])
        setMessage(`Created ${created.rule_id}`)
      }
      cancel()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (r: RuleRow) => {
    const ok = window.confirm(
      r.learned
        ? `Delete rule ${r.rule_id}?`
        : `Disable built-in rule ${r.rule_id}? It will stay in the seed list but will not match.`
    )
    if (!ok) return
    setError('')
    setMessage('')
    try {
      const res = await deleteRule(r.rule_id)
      setMessage(res.disabled ? `Disabled ${r.rule_id}` : `Deleted ${r.rule_id}`)
      if (editingId === r.rule_id) cancel()
      if (res.deleted) {
        setRules((prev) => prev.filter((x) => x.rule_id !== r.rule_id))
      } else {
        setRules((prev) =>
          prev.map((x) => (x.rule_id === r.rule_id ? { ...x, enabled: 0 } : x)),
        )
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Delete failed')
    }
  }

  const editor = (ruleId: string | null) => (
    <div className="rules-editor">
      <label>
        Phase
        <select
          value={form.phase}
          onChange={(e) => setForm({ ...form, phase: e.target.value })}
          aria-label="Phase"
        >
          {PHASES.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
      </label>
      <label className="rules-pattern">
        Regex pattern
        <input
          value={form.pattern}
          onChange={(e) => setForm({ ...form, pattern: e.target.value })}
          aria-label="Regex pattern"
        />
      </label>
      <label>
        Property
        <input
          value={form.property_code}
          onChange={(e) => setForm({ ...form, property_code: e.target.value })}
          aria-label="Property"
        />
      </label>
      <label>
        Category
        <input
          value={form.category}
          onChange={(e) => setForm({ ...form, category: e.target.value })}
          aria-label="Category"
        />
      </label>
      <label>
        Subcategory
        <input
          value={form.subcategory}
          onChange={(e) => setForm({ ...form, subcategory: e.target.value })}
          aria-label="Subcategory"
        />
      </label>
      <label>
        Strength
        <select
          value={form.strength}
          onChange={(e) => setForm({ ...form, strength: e.target.value })}
          aria-label="Strength"
        >
          {STRENGTHS.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </label>
      <label>
        Order
        <input
          type="number"
          value={form.order_index}
          onChange={(e) => setForm({ ...form, order_index: Number(e.target.value) })}
          aria-label="Order index"
        />
      </label>
      <label>
        Enabled
        <select
          value={String(form.enabled)}
          onChange={(e) => setForm({ ...form, enabled: Number(e.target.value) })}
          aria-label="Enabled"
        >
          <option value="1">yes</option>
          <option value="0">no</option>
        </select>
      </label>
      <div className="rules-editor-actions">
        <button type="button" className="btn-primary" onClick={() => persist(ruleId)} disabled={saving}>
          {saving ? 'Saving…' : ruleId ? 'Save' : 'Create'}
        </button>
        <button type="button" onClick={cancel}>Cancel</button>
      </div>
    </div>
  )

  if (loading && rules.length === 0) return <p>Loading rules…</p>

  return (
    <div className="rules-page">
      <h1>Rules</h1>
      <p className="muted">
        Matching uses Python <code>re.match</code> (case-insensitive) on the transaction match text.
        First match in each phase wins; lower order index runs first. User-learned rules are stored in{' '}
        <code>data/property/learned_rules.json</code> so they survive wipe and reseed. After changing rules,
        re-run the month so existing transactions pick up new matches.
      </p>
      {message && <p className="settings-message">{message}</p>}
      {error && <p className="error">{error}</p>}

      <div className="rules-toolbar">
        <label>
          Show
          <select value={filter} onChange={(e) => setFilter(e.target.value as typeof filter)} aria-label="Filter rules">
            <option value="all">all</option>
            <option value="learned">learned / edited</option>
            <option value="disabled">disabled</option>
          </select>
        </label>
        <input
          className="rules-search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search id, pattern, labels"
          aria-label="Search rules"
        />
        <button type="button" className="btn-primary" onClick={startAdd}>
          Add rule
        </button>
      </div>

      {adding && editor(null)}

      <div className="rules-table-wrap">
        <table className="rules-table">
          <thead>
            <tr>
              {SORT_COLUMNS.map((col) => {
                const active = sortKey === col.key
                const marker = active ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ''
                return (
                  <th key={col.key}>
                    <button
                      type="button"
                      className={`sort-th${active ? ' sort-active' : ''}`}
                      onClick={() => toggleSort(col.key)}
                      aria-label={`Sort by ${col.label}${active ? `, ${sortDir}ending` : ''}`}
                    >
                      {col.label}{marker}
                    </button>
                  </th>
                )
              })}
              <th></th>
            </tr>
          </thead>
          <tbody>
            {visible.map((r) => (
              <tr key={r.rule_id} className={!r.enabled ? 'rule-disabled' : ''}>
                <td className="rule-id">
                  {r.rule_id}
                  {r.learned && <span className="badge">learned</span>}
                </td>
                {editingId === r.rule_id ? (
                  <td colSpan={10}>{editor(r.rule_id)}</td>
                ) : (
                  <>
                    <td className="rule-edited" title={r.updated_at || undefined}>{formatEdited(r.updated_at)}</td>
                    <td>{r.phase}</td>
                    <td className="rule-pattern">{r.pattern}</td>
                    <td>{r.property_code}</td>
                    <td>{r.category}</td>
                    <td>{r.subcategory}</td>
                    <td>{r.strength}</td>
                    <td>{r.order_index}</td>
                    <td>{r.enabled ? 'yes' : 'no'}</td>
                    <td className="rule-actions">
                      <button type="button" onClick={() => startEdit(r)}>Edit</button>
                      <button type="button" onClick={() => handleDelete(r)}>
                        {r.learned ? 'Delete' : 'Disable'}
                      </button>
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {visible.length === 0 && <p className="muted">No rules match this filter.</p>}
    </div>
  )
}
