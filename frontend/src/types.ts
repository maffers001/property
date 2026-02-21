export interface DraftRow {
  tx_id: string
  Date: string
  Account: string
  Amount: number
  Subcategory: string
  Memo: string
  Property: string
  property_code: string
  Description: string
  Cat: string
  category: string
  Subcat: string
  subcategory: string
  counterparty?: string
  posted_date?: string
  confidence?: number | null
  needs_review: number
  rule_strength?: string
  reviewed_at?: string
}

export const DRAFT_COLUMN_KEYS = [
  'Date', 'Account', 'Amount', 'Memo', 'Property', 'Cat', 'Subcat',
  'confidence', 'needs_review', 'tx_id', 'Description', 'Subcategory', 'rule_strength', 'reviewed_at',
] as const

export type DraftColumnKey = (typeof DRAFT_COLUMN_KEYS)[number]

export interface DraftFilters {
  property: string[]
  category: string[]
  subcategory: string[]
  search: string
  date_from: string
  date_to: string
}
