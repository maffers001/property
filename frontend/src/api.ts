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

export function getMonths() {
  return api<string[]>('/months')
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

export function getReview(month: string, params?: { property?: string; category?: string; subcategory?: string; search?: string; date_from?: string; date_to?: string; format?: string }) {
  const sp = new URLSearchParams({ month })
  if (params?.property) sp.set('property', params.property)
  if (params?.category) sp.set('category', params.category)
  if (params?.subcategory) sp.set('subcategory', params.subcategory)
  if (params?.search) sp.set('search', params.search)
  if (params?.date_from) sp.set('date_from', params.date_from)
  if (params?.date_to) sp.set('date_to', params.date_to)
  if (params?.format) sp.set('format', params.format)
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

export function reviewSubmit(month: string) {
  return api<{ ok: boolean; applied: number }>(`/review/submit?month=${encodeURIComponent(month)}`, { method: 'POST' })
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
