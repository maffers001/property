import { useState } from 'react'
import { addListProperty, addListCategory, addListSubcategory } from '../api'
import './Settings.css'

export default function Settings() {
  const [property, setProperty] = useState('')
  const [category, setCategory] = useState('')
  const [subcategory, setSubcategory] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const handleAddProperty = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setMessage('')
    if (!property.trim()) return
    try {
      await addListProperty(property.trim())
      setMessage(`Added property: ${property.trim()}`)
      setProperty('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
    }
  }

  const handleAddCategory = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setMessage('')
    if (!category.trim()) return
    try {
      await addListCategory(category.trim())
      setMessage(`Added category: ${category.trim()}`)
      setCategory('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
    }
  }

  const handleAddSubcategory = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setMessage('')
    if (!subcategory.trim()) return
    try {
      await addListSubcategory(subcategory.trim())
      setMessage(`Added subcategory: ${subcategory.trim()}`)
      setSubcategory('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
    }
  }

  return (
    <div className="settings-page">
      <h1>Settings</h1>
      <p className="muted">Add new property codes, categories, or subcategories. They will appear in dropdowns when editing transactions.</p>
      {message && <p className="settings-message">{message}</p>}
      {error && <p className="error">{error}</p>}

      <section className="settings-section">
        <h2>Property code</h2>
        <form onSubmit={handleAddProperty}>
          <input
            type="text"
            value={property}
            onChange={(e) => setProperty(e.target.value)}
            placeholder="e.g. F161618ALH"
            aria-label="New property code"
          />
          <button type="submit">Add</button>
        </form>
      </section>

      <section className="settings-section">
        <h2>Category</h2>
        <form onSubmit={handleAddCategory}>
          <input
            type="text"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder="e.g. PropertyExpense"
            aria-label="New category"
          />
          <button type="submit">Add</button>
        </form>
      </section>

      <section className="settings-section">
        <h2>Subcategory</h2>
        <form onSubmit={handleAddSubcategory}>
          <input
            type="text"
            value={subcategory}
            onChange={(e) => setSubcategory(e.target.value)}
            placeholder="e.g. Other"
            aria-label="New subcategory"
          />
          <button type="submit">Add</button>
        </form>
      </section>
    </div>
  )
}
