const API_BASE = '/api'

function getToken(): string | null {
  return localStorage.getItem('token')
}

export async function api<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken()
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers, credentials: 'include' })
  if (res.status === 401) {
    localStorage.removeItem('token')
    window.location.href = '/'
    throw new Error('Unauthorized')
  }
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  const contentType = res.headers.get('content-type')
  if (contentType && contentType.includes('application/json')) {
    return res.json()
  }
  return res.text() as unknown as T
}

export function login(password: string) {
  return api<{ access_token: string }>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ password }),
  })
}

const MONTH_NUM: Record<string, number> = {
  JAN: 1, FEB: 2, MAR: 3, APR: 4, MAY: 5, JUN: 6,
  JUL: 7, AUG: 8, SEP: 9, OCT: 10, NOV: 11, DEC: 12,
}

/** Calendar order: JAN2026, FEB2026, … (not string order APR, AUG, FEB). */
export function sortMonthsCalendar(months: string[]): string[] {
  const key = (m: string) => {
    const mon = MONTH_NUM[m.slice(0, 3).toUpperCase()] ?? 0
    const year = parseInt(m.slice(3), 10) || 0
    return year * 12 + mon
  }
  return [...months].sort((a, b) => key(a) - key(b))
}

/** Calendar month as YYYY-MM-DD inclusive range. SEP2026 -> 2026-09-01 .. 2026-09-30 */
export function monthToDateRange(month: string): { from: string; to: string } {
  const mon = MONTH_NUM[month.slice(0, 3).toUpperCase()] ?? 1
  const year = parseInt(month.slice(3), 10) || 1970
  const from = `${year}-${String(mon).padStart(2, '0')}-01`
  const last = new Date(year, mon, 0).getDate()
  const to = `${year}-${String(mon).padStart(2, '0')}-${String(last).padStart(2, '0')}`
  return { from, to }
}

export function getMonths() {
  return api<string[]>('/months').then(sortMonthsCalendar)
}

export function getLists() {
  return api<{ property_codes: string[]; categories: string[]; subcategories: string[] }>('/lists')
}

export function getDraft(month: string, params?: { property?: string; category?: string; subcategory?: string; search?: string; date_from?: string; date_to?: string; format?: string }) {
  const sp = new URLSearchParams({ month })
  if (params?.property) sp.set('property', params.property)
  if (params?.category) sp.set('category', params.category)
  if (params?.subcategory) sp.set('subcategory', params.subcategory)
  if (params?.search) sp.set('search', params.search)
  if (params?.date_from) sp.set('date_from', params.date_from)
  if (params?.date_to) sp.set('date_to', params.date_to)
  if (params?.format) sp.set('format', params.format)
  return fetch(`${API_BASE}/draft?${sp}`, {
    headers: { Authorization: `Bearer ${getToken()}` },
    credentials: 'include',
  }).then(async (res) => {
    if (res.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/'
      throw new Error('Unauthorized')
    }
    if (params?.format === 'csv') return res.text()
    return res.json()
  })
}

export function getReview(month: string, params?: { property?: string; category?: string; subcategory?: string; search?: string; date_from?: string; date_to?: string; format?: string; all?: boolean }) {
  const sp = new URLSearchParams({ month })
  if (params?.property) sp.set('property', params.property)
  if (params?.category) sp.set('category', params.category)
  if (params?.subcategory) sp.set('subcategory', params.subcategory)
  if (params?.search) sp.set('search', params.search)
  if (params?.date_from) sp.set('date_from', params.date_from)
  if (params?.date_to) sp.set('date_to', params.date_to)
  if (params?.format) sp.set('format', params.format)
  if (params?.all) sp.set('all', 'true')
  return fetch(`${API_BASE}/review?${sp}`, {
    headers: { Authorization: `Bearer ${getToken()}` },
    credentials: 'include',
  }).then(async (res) => {
    if (res.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/'
      throw new Error('Unauthorized')
    }
    if (params?.format === 'csv') return res.text()
    return res.json()
  })
}

export function reviewAdd(month: string, txIds: string[]) {
  return api<{ ok: boolean; count: number }>('/review/add', {
    method: 'POST',
    body: JSON.stringify({ month, tx_ids: txIds }),
  })
}

export function reviewRemove(month: string, txIds: string[]) {
  return api<{ ok: boolean; count: number }>('/review/remove', {
    method: 'POST',
    body: JSON.stringify({ month, tx_ids: txIds }),
  })
}

export function reviewCorrect(txId: string, propertyCode: string, category: string, subcategory: string) {
  return api<{ ok: boolean }>('/review/correct', {
    method: 'POST',
    body: JSON.stringify({ tx_id: txId, property_code: propertyCode, category, subcategory }),
  })
}

export function reviewComplete(month: string, txIds: string[]) {
  return api<{ ok: boolean; applied?: number; count?: number }>(
    `/review/submit?month=${encodeURIComponent(month)}`,
    { method: 'POST', body: JSON.stringify({ tx_ids: txIds }) },
  )
}

export function reviewSubmit(month: string) {
  return api<{ ok: boolean; applied: number }>(`/review/submit?month=${encodeURIComponent(month)}`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

export function finalizeMonth(month: string) {
  return api<{ ok: boolean; path?: string }>(`/finalize?month=${encodeURIComponent(month)}`, { method: 'POST' })
}

export interface ReportSummary {
  property_summary: Array<{ month: string; Mortgage?: number; PropertyExpense?: number; ServiceCharge?: number; OurRent?: number; BealsRent?: number; TotalRent?: number; NetProfit?: number }>
  outgoings: Array<Record<string, number | string>>
  personal_spending: Array<Record<string, number | string>>
}

export function getReportsSummary(params: { month?: string; from?: string; to?: string }) {
  const sp = new URLSearchParams()
  if (params.month) sp.set('month', params.month)
  if (params.from) sp.set('from', params.from)
  if (params.to) sp.set('to', params.to)
  return api<ReportSummary>(`/reports/summary?${sp}`)
}

export function addListProperty(value: string) {
  return api<{ ok: boolean; value: string }>('/lists/property', { method: 'POST', body: JSON.stringify({ value }) })
}
export function addListCategory(value: string) {
  return api<{ ok: boolean; value: string }>('/lists/category', { method: 'POST', body: JSON.stringify({ value }) })
}
export function addListSubcategory(value: string) {
  return api<{ ok: boolean; value: string }>('/lists/subcategory', { method: 'POST', body: JSON.stringify({ value }) })
}

export function reviewAddByRule(month: string, opts: { category?: string; property_empty?: boolean }) {
  return api<{ ok: boolean; count: number }>('/review/add-by-rule', {
    method: 'POST',
    body: JSON.stringify({ month, category: opts.category, property_empty: opts.property_empty ?? false }),
  })
}

export interface RuleRow {
  rule_id: string
  order_index: number
  phase: string
  pattern: string
  outputs_json: string
  property_code: string
  category: string
  subcategory: string
  strength: string
  apply_when_json: string | null
  enabled: number
  learned: boolean
  created_at?: string
  updated_at?: string
}

export function getRules() {
  return api<RuleRow[]>('/rules')
}

export function createRule(body: Partial<RuleRow> & { pattern: string; phase: string }) {
  return api<RuleRow>('/rules', { method: 'POST', body: JSON.stringify(body) })
}

export function updateRule(ruleId: string, body: Partial<RuleRow> & { pattern: string; phase: string }) {
  return api<RuleRow>(`/rules/${encodeURIComponent(ruleId)}`, { method: 'PUT', body: JSON.stringify(body) })
}

export function deleteRule(ruleId: string) {
  return api<{ ok: boolean; deleted?: boolean; disabled?: boolean }>(`/rules/${encodeURIComponent(ruleId)}`, { method: 'DELETE' })
}

export function saveRuleFromReview(body: {
  memo?: string
  counterparty?: string
  match_text?: string
  property_code?: string
  category?: string
  subcategory?: string
  pattern?: string
  phase?: string
  strength?: string
}) {
  return api<{ ok: boolean; pattern: string; rules: RuleRow[] }>('/rules/from-review', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function suggestRulePattern(memo: string, counterparty?: string, matchText?: string) {
  const sp = new URLSearchParams()
  if (memo) sp.set('memo', memo)
  if (counterparty) sp.set('counterparty', counterparty)
  if (matchText) sp.set('match_text', matchText)
  return api<{ pattern: string }>(`/rules/suggest-pattern?${sp}`)
}

export function testRulePattern(body: {
  pattern: string
  memo?: string
  counterparty?: string
  match_text?: string
  exclude_tx_id?: string
  exclude_tx_ids?: string[]
  samples?: string[]
  property_code?: string
  category?: string
  subcategory?: string
}) {
  return api<{
    ok: boolean
    matched: boolean
    sample: string
    error: string | null
    other_count?: number
    conflict_count?: number
    selected_count?: number
    selected_matched?: number
    selected_missed?: string[]
    others?: {
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
    }[]
  }>('/rules/test', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function suggestPatternFromSamples(samples: string[]) {
  return api<{ pattern: string }>('/rules/suggest-from-samples', {
    method: 'POST',
    body: JSON.stringify({ samples }),
  })
}

export function reviewCorrectBulk(
  txIds: string[],
  propertyCode: string,
  category: string,
  subcategory: string,
  pattern?: string,
) {
  return api<{ ok: boolean; count: number }>('/review/correct-bulk', {
    method: 'POST',
    body: JSON.stringify({
      tx_ids: txIds,
      property_code: propertyCode,
      category,
      subcategory,
      pattern: pattern || '',
    }),
  })
}
