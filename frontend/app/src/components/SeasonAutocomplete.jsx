import React, { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { authFetch } from '../utils/auth'

const MAX_RESULTS = 30

function formatSeasonLabel(season) {
  if (season.descrizione) {
    return `${season.codice} — ${season.descrizione}`
  }
  return season.codice
}

function matchesSeason(season, query) {
  const q = query.trim().toLowerCase()
  if (!q) return true
  return (
    String(season.codice).toLowerCase().includes(q) ||
    String(season.descrizione || '').toLowerCase().includes(q)
  )
}

export default function SeasonAutocomplete({
  name,
  value,
  onChange,
  placeholder = 'Cerca stagione...',
  allowClear = false,
  endpoint = '/api/cicli/stagioni',
}) {
  const [seasons, setSeasons] = useState([])
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [listStyle, setListStyle] = useState({ top: 0, left: 0, width: 0 })

  const containerRef = useRef(null)
  const controlRef = useRef(null)
  const listRef = useRef(null)
  const inputRef = useRef(null)

  const selectedSeason = useMemo(
    () => seasons.find((season) => season.codice === value) ?? null,
    [seasons, value]
  )

  const results = useMemo(() => {
    if (!open) return []
    return seasons.filter((season) => matchesSeason(season, query)).slice(0, MAX_RESULTS)
  }, [seasons, query, open])

  const updateListPosition = () => {
    if (!controlRef.current) return
    const rect = controlRef.current.getBoundingClientRect()
    const width = Math.max(rect.width, 240)
    let left = rect.left
    const maxLeft = window.innerWidth - width - 12
    if (left > maxLeft) left = Math.max(12, maxLeft)

    setListStyle({
      top: rect.bottom + 8,
      left,
      width
    })
  }

  useEffect(() => {
    authFetch(endpoint)
      .then((res) => res.json())
      .then((resData) => {
        if (resData.data) setSeasons(resData.data)
      })
      .catch((err) => console.error('Error fetching seasons:', err))
  }, [endpoint])

  useEffect(() => {
    if (isEditing) return
    if (selectedSeason) {
      setQuery(formatSeasonLabel(selectedSeason))
    } else {
      setQuery('')
    }
  }, [selectedSeason, isEditing])

  useEffect(() => {
    if (!open) return undefined

    updateListPosition()

    const handleClickOutside = (event) => {
      const inField = containerRef.current?.contains(event.target)
      const inList = listRef.current?.contains(event.target)
      if (!inField && !inList) {
        closeList()
      }
    }

    const handleEscape = (event) => {
      if (event.key === 'Escape') closeList()
    }

    const handleReposition = () => updateListPosition()

    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleEscape)
    window.addEventListener('resize', handleReposition)
    window.addEventListener('scroll', handleReposition, true)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleEscape)
      window.removeEventListener('resize', handleReposition)
      window.removeEventListener('scroll', handleReposition, true)
    }
  }, [open, selectedSeason])

  const emitChange = (codice) => {
    if (name) {
      onChange({ target: { name, value: codice } })
    } else {
      onChange(codice)
    }
  }

  const closeList = () => {
    setOpen(false)
    setIsEditing(false)
    if (selectedSeason) {
      setQuery(formatSeasonLabel(selectedSeason))
    } else {
      setQuery('')
    }
  }

  const selectSeason = (season) => {
    emitChange(season.codice)
    setQuery(formatSeasonLabel(season))
    setIsEditing(false)
    setOpen(false)
    inputRef.current?.blur()
  }

  const clearSelection = () => {
    emitChange('')
    setQuery('')
    setIsEditing(false)
    setOpen(false)
    inputRef.current?.focus()
  }

  const handleInputChange = (event) => {
    const nextQuery = event.target.value
    setQuery(nextQuery)
    setIsEditing(true)
    setOpen(true)

    if (!nextQuery.trim()) {
      emitChange('')
    }
  }

  const handleFocus = () => {
    setIsEditing(true)
    setOpen(true)
    if (selectedSeason) {
      setQuery('')
    }
  }

  const dropdown = open ? (
    <div
      ref={listRef}
      className="customer-autocomplete__list"
      role="listbox"
      style={{
        position: 'fixed',
        top: listStyle.top,
        left: listStyle.left,
        width: listStyle.width
      }}
    >
      {results.length === 0 ? (
        <div className="customer-autocomplete__empty">Nessuna stagione trovata</div>
      ) : (
        results.map((season) => (
          <button
            key={season.codice}
            type="button"
            role="option"
            aria-selected={season.codice === value}
            className={`customer-autocomplete__option${season.codice === value ? ' customer-autocomplete__option--selected' : ''}`}
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => selectSeason(season)}
          >
            <span className="customer-autocomplete__name">{formatSeasonLabel(season)}</span>
            <span className="customer-autocomplete__code">{season.codice}</span>
          </button>
        ))
      )}
    </div>
  ) : null

  return (
    <div className={`customer-autocomplete${open ? ' customer-autocomplete--open' : ''}`} ref={containerRef}>
      <div className="customer-autocomplete__control" ref={controlRef}>
        <input
          ref={inputRef}
          type="text"
          className="customer-autocomplete__field"
          value={query}
          onChange={handleInputChange}
          onFocus={handleFocus}
          placeholder={placeholder}
          autoComplete="off"
          spellCheck={false}
        />
        {allowClear && value && (
          <button
            type="button"
            className="customer-autocomplete__clear"
            onClick={clearSelection}
            aria-label="Cancella stagione selezionata"
          >
            ×
          </button>
        )}
      </div>
      {dropdown && createPortal(dropdown, document.body)}
    </div>
  )
}
