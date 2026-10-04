import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getMonths, getDraft } from '../api'
import './Home.css'

export default function Home() {
  const [months, setMonths] = useState<string[]>([])
  const [selectedMonth, setSelectedMonth] = useState('')
  const [reviewCounts, setReviewCounts] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    getMonths()
      .then((list) => {
        setMonths(list)
        if (list.length && !selectedMonth) setSelectedMonth(list[list.length - 1])
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!selectedMonth) return
    getDraft(selectedMonth)
      .then((data) => {
        if (Array.isArray(data)) {
          const n = data.filter((r: { needs_review?: number }) => r.needs_review === 1).length
          setReviewCounts((c) => ({ ...c, [selectedMonth]: n }))
        }
      })
      .catch(() => {})
  }, [selectedMonth])

  if (loading) return <p className="home-loading">Loading…</p>
  if (error) return <p className="home-error">{error}</p>

  const reviewCount = selectedMonth ? (reviewCounts[selectedMonth] ?? 0) : 0

  return (
    <div className="home">
      <h1>Property Review</h1>
      <div className="home-section">
        <label htmlFor="month">Month</label>
        <select
          id="month"
          value={selectedMonth}
          onChange={(e) => setSelectedMonth(e.target.value)}
        >
          {months.length === 0 && <option value="">No months available</option>}
          {months.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>
      <div className="home-actions">
        <Link to={`/review/${selectedMonth}`} className="home-btn home-btn-primary">
          Review {selectedMonth}{reviewCount > 0 ? ` (${reviewCount} need review)` : ''}
        </Link>
        <Link to="/reports" className="home-btn home-btn-secondary">
          Reports
        </Link>
        <Link to="/rules" className="home-btn home-btn-secondary">
          Rules
        </Link>
      </div>
    </div>
  )
}
