import React, { useState, useEffect } from 'react'
import DateInput from './DateInput'
import CustomerAutocomplete from './CustomerAutocomplete'
import { authFetch } from '../utils/auth'

export default function Filters({ activeTab, onSearch, onExport, onExportPDF, filterValues }) {
  const [stagioni, setStagioni] = useState([])
  const [filters, setFilters] = useState({
    data_inizio: '',
    data_fine: '',
    codice_cliente: '',
    stagione: ''
  })

  useEffect(() => {
    if (filterValues) {
      setFilters(filterValues)
    }
  }, [filterValues])

  useEffect(() => {
    authFetch('/api/stagioni')
      .then((res) => res.json())
      .then((resData) => {
        if (resData.data) setStagioni(resData.data)
      })
      .catch((err) => console.error('Error fetching seasons:', err))
  }, [])

  const handleChange = (e) => {
    const { name, value } = e.target
    setFilters((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    onSearch(filters)
  }

  const handleReset = () => {
    const cleared = {
      data_inizio: '',
      data_fine: '',
      codice_cliente: '',
      stagione: ''
    }
    setFilters(cleared)
    onSearch(cleared)
  }

  return (
    <form onSubmit={handleSubmit} className="filters-form">
      <div className="filters-grid">
        <div className="field">
          <label>Data da</label>
          <DateInput
            name="data_inizio"
            value={filters.data_inizio}
            onChange={handleChange}
            placeholder="Seleziona data inizio"
          />
        </div>
        <div className="field">
          <label>Data a</label>
          <DateInput
            name="data_fine"
            value={filters.data_fine}
            onChange={handleChange}
            placeholder="Seleziona data fine"
          />
        </div>
        <div className="field">
          <label>Cliente</label>
          <CustomerAutocomplete
            name="codice_cliente"
            value={filters.codice_cliente}
            onChange={handleChange}
            placeholder="Cerca per nome o codice..."
            allowClear
          />
        </div>
        <div className="field">
          <label>Stagione</label>
          <select name="stagione" value={filters.stagione} onChange={handleChange}>
            <option value="">Tutte le stagioni</option>
            {stagioni.map((s) => (
              <option key={s.codice} value={s.codice}>
                {s.codice} — {s.descrizione}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="actions-bar">
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button type="submit" className="btn btn--primary">
            Cerca
          </button>
          <button type="button" onClick={handleReset} className="btn">
            Azzera filtri
          </button>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button type="button" onClick={onExport} className="btn">
            Esporta CSV
          </button>
          <button type="button" onClick={onExportPDF} className="btn">
            Esporta PDF
          </button>
        </div>
      </div>
    </form>
  )
}
