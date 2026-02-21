import { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid } from 'recharts'
import { getMonths, getReportsSummary } from '../api'
import type { ReportSummary } from '../api'
import './Reports.css'

export default function Reports() {
  const [months, setMonths] = useState<string[]>([])
  const [monthFrom, setMonthFrom] = useState('')
  const [monthTo, setMonthTo] = useState('')
  const [singleMonth, setSingleMonth] = useState(true)
  const [data, setData] = useState<ReportSummary | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    getMonths().then((m) => {
      setMonths(m)
      if (m.length) {
        setMonthFrom((prev) => prev || m[0])
        setMonthTo((prev) => prev || m[0])
      }
    }).catch(() => {})
  }, [])

  const handleApply = () => {
    setError('')
    setLoading(true)
    const params = singleMonth
      ? { month: monthFrom }
      : { from: monthFrom, to: monthTo }
    getReportsSummary(params)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }

  const ptySummary = data?.property_summary ?? []
  const outgoings = data?.outgoings ?? []
  const personal = data?.personal_spending ?? []

  return (
    <div className="reports-page">
      <h1>Reports</h1>
      <div className="reports-controls">
        <label>
          <input type="radio" checked={singleMonth} onChange={() => setSingleMonth(true)} />
          Single month
        </label>
        <label>
          <input type="radio" checked={!singleMonth} onChange={() => setSingleMonth(false)} />
          Range
        </label>
        <select value={monthFrom} onChange={(e) => setMonthFrom(e.target.value)}>
          {months.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
        {!singleMonth && (
          <>
            <span>to</span>
            <select value={monthTo} onChange={(e) => setMonthTo(e.target.value)}>
              {months.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </>
        )}
        <button type="button" onClick={handleApply} disabled={loading}>
          {loading ? 'Loading…' : 'Apply'}
        </button>
      </div>
      {error && <p className="error">{error}</p>}

      {data && (
        <>
          <section className="report-section">
            <h2>Property summary</h2>
            {ptySummary.length > 0 ? (
              <>
                <div className="report-chart">
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={ptySummary} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="month" />
                      <YAxis />
                      <Tooltip formatter={(v: number | undefined) => (v != null && typeof v === 'number' ? v.toFixed(2) : String(v ?? ''))} />
                      <Legend />
                      <Bar dataKey="OurRent" fill="#2d5a27" name="Our Rent" stackId="income" />
                      <Bar dataKey="BealsRent" fill="#6b8e6b" name="Beals Rent" stackId="income" />
                      <Bar dataKey="Mortgage" fill="#8b0000" name="Mortgage" stackId="out" />
                      <Bar dataKey="PropertyExpense" fill="#1a4d8c" name="Property Expense" stackId="out" />
                      <Bar dataKey="ServiceCharge" fill="#c97600" name="Service Charge" stackId="out" />
                      <Bar dataKey="NetProfit" fill="#333" name="Net Profit" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <table className="report-table">
                  <thead>
                    <tr>
                      <th>Month</th>
                      <th>OurRent</th>
                      <th>BealsRent</th>
                      <th>TotalRent</th>
                      <th>Mortgage</th>
                      <th>PropertyExpense</th>
                      <th>ServiceCharge</th>
                      <th>NetProfit</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ptySummary.map((row) => (
                      <tr key={row.month}>
                        <td>{row.month}</td>
                        <td>{row.OurRent != null ? Number(row.OurRent).toFixed(2) : ''}</td>
                        <td>{row.BealsRent != null ? Number(row.BealsRent).toFixed(2) : ''}</td>
                        <td>{row.TotalRent != null ? Number(row.TotalRent).toFixed(2) : ''}</td>
                        <td>{row.Mortgage != null ? Number(row.Mortgage).toFixed(2) : ''}</td>
                        <td>{row.PropertyExpense != null ? Number(row.PropertyExpense).toFixed(2) : ''}</td>
                        <td>{row.ServiceCharge != null ? Number(row.ServiceCharge).toFixed(2) : ''}</td>
                        <td>{row.NetProfit != null ? Number(row.NetProfit).toFixed(2) : ''}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            ) : (
              <p className="muted">No data for selected range.</p>
            )}
          </section>

          <section className="report-section">
            <h2>Outgoings</h2>
            {outgoings.length > 0 ? (
              <table className="report-table">
                <thead>
                  <tr>
                    <th>Month</th>
                    {Object.keys(outgoings[0]).filter((k) => k !== 'month').map((k) => (
                      <th key={k}>{k}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {outgoings.map((row, i) => (
                    <tr key={row.month ?? i}>
                      <td>{row.month}</td>
                      {Object.entries(row).filter(([k]) => k !== 'month').map(([k, v]) => (
                        <td key={k}>{typeof v === 'number' ? v.toFixed(2) : String(v)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="muted">No data.</p>
            )}
          </section>

          <section className="report-section">
            <h2>Personal spending</h2>
            {personal.length > 0 ? (
              <table className="report-table">
                <thead>
                  <tr>
                    <th>Month</th>
                    {Object.keys(personal[0]).filter((k) => k !== 'month').map((k) => (
                      <th key={k}>{k}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {personal.map((row, i) => (
                    <tr key={row.month ?? i}>
                      <td>{row.month}</td>
                      {Object.entries(row).filter(([k]) => k !== 'month').map(([k, v]) => (
                        <td key={k}>{typeof v === 'number' ? v.toFixed(2) : String(v)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="muted">No data.</p>
            )}
          </section>
        </>
      )}
    </div>
  )
}
