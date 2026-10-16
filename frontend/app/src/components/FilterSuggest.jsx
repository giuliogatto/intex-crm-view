import React, { useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { authFetch } from '../utils/auth'

const DEBOUNCE_MS = 250

function buildUrl(endpoint, query, params) {
  const search = new URLSearchParams()
  search.set('q', query)
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value != null && String(value).trim() !== '') {
      search.set(key, String(value))
    }
  })
  const base = endpoint.includes('?') ? endpoint.split('?')[0] : endpoint
  return `${base}?${search.toString()}`
}

function optionKey(item, index) {
  return `${item.value}::${item.secondary || ''}::${index}`
}

/**
 * Autocomplete con testo libero: il valore del filtro è sempre la stringa digitata.
 * I suggerimenti sono case-insensitive (ILIKE lato server) e opzionali.
 */
export default function FilterSuggest({
  name,
  value = '',
  onChange,
  endpoint,
  placeholder = 'Cerca…',
  minChars = 2,
  params = {},
  allowClear = true,
  emptyLabel = 'Nessun suggerimento',
}) {
  const listId = useId()
  const [open, setOpen] = useState(false)
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [highlight, setHighlight] = useState(-1)
  const [listStyle, setListStyle] = useState({ top: 0, left: 0, width: 0 })

  const containerRef = useRef(null)
  const controlRef = useRef(null)
  const listRef = useRef(null)
  const inputRef = useRef(null)
  const debounceRef = useRef(null)
  const abortRef = useRef(null)
  const paramsKey = JSON.stringify(params || {})

  const emitChange = (next) => {
    if (name) {
      onChange({ target: { name, value: next } })
    } else {
      onChange(next)
    }
  }

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
      width,
    })
  }

  const fetchSuggestions = (query) => {
    if (abortRef.current) abortRef.current.abort()
    if (!endpoint || query.trim().length < minChars) {
      setResults([])
      setLoading(false)
      return
    }

    const controller = new AbortController()
    abortRef.current = controller
    setLoading(true)

    authFetch(buildUrl(endpoint, query.trim(), params), { signal: controller.signal })
      .then((res) => res.json())
      .then((resData) => {
        if (controller.signal.aborted) return
        setResults(Array.isArray(resData.data) ? resData.data : [])
        setHighlight(-1)
      })
      .catch((err) => {
        if (err?.name === 'AbortError') return
        console.error('Error fetching suggestions:', err)
        setResults([])
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
  }

  useEffect(() => {
    if (!open) return undefined

    updateListPosition()

    const handleClickOutside = (event) => {
      const inField = containerRef.current?.contains(event.target)
      const inList = listRef.current?.contains(event.target)
      if (!inField && !inList) setOpen(false)
    }
    const handleEscape = (event) => {
      if (event.key === 'Escape') setOpen(false)
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
  }, [open])

  useEffect(() => {
    if (!open) return undefined
    if (debounceRef.current) clearTimeout(debounceRef.current)

    const q = String(value || '')
    if (q.trim().length < minChars) {
      setResults([])
      setLoading(false)
      return undefined
    }

    debounceRef.current = setTimeout(() => fetchSuggestions(q), DEBOUNCE_MS)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
    // paramsKey tracks params object identity without deep compare noise
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, open, endpoint, minChars, paramsKey])

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
      if (abortRef.current) abortRef.current.abort()
    }
  }, [])

  const selectItem = (item) => {
    const next = item?.value != null ? String(item.value) : ''
    emitChange(next)
    setOpen(false)
    setHighlight(-1)
    inputRef.current?.blur()
  }

  const clearValue = () => {
    emitChange('')
    setResults([])
    setOpen(false)
    setHighlight(-1)
    inputRef.current?.focus()
  }

  const handleInputChange = (event) => {
    emitChange(event.target.value)
    setOpen(true)
  }

  const handleFocus = () => {
    setOpen(true)
  }

  const handleKeyDown = (event) => {
    if (!open && (event.key === 'ArrowDown' || event.key === 'ArrowUp')) {
      setOpen(true)
      return
    }
    if (!open) return

    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setHighlight((prev) => (results.length ? (prev + 1) % results.length : -1))
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setHighlight((prev) =>
        results.length ? (prev <= 0 ? results.length - 1 : prev - 1) : -1
      )
    } else if (event.key === 'Enter' && highlight >= 0 && results[highlight]) {
      event.preventDefault()
      selectItem(results[highlight])
    } else if (event.key === 'Escape') {
      setOpen(false)
    }
  }

  const showList = open && String(value || '').trim().length >= minChars
  const dropdown = showList ? (
    <div
      ref={listRef}
      id={listId}
      className="customer-autocomplete__list"
      role="listbox"
      style={{
        position: 'fixed',
        top: listStyle.top,
        left: listStyle.left,
        width: listStyle.width,
      }}
    >
      {loading && results.length === 0 ? (
        <div className="customer-autocomplete__empty">Ricerca…</div>
      ) : results.length === 0 ? (
        <div className="customer-autocomplete__empty">{emptyLabel}</div>
      ) : (
        results.map((item, index) => (
          <button
            key={optionKey(item, index)}
            type="button"
            role="option"
            aria-selected={index === highlight || item.value === value}
            className={`customer-autocomplete__option${
              index === highlight || item.value === value
                ? ' customer-autocomplete__option--selected'
                : ''
            }`}
            onMouseDown={(event) => event.preventDefault()}
            onMouseEnter={() => setHighlight(index)}
            onClick={() => selectItem(item)}
          >
            <span className="customer-autocomplete__name">{item.label || item.value}</span>
            {item.secondary ? (
              <span className="customer-autocomplete__code">{item.secondary}</span>
            ) : null}
          </button>
        ))
      )}
    </div>
  ) : null

  return (
    <div
      className={`customer-autocomplete${open ? ' customer-autocomplete--open' : ''}`}
      ref={containerRef}
    >
      <div className="customer-autocomplete__control" ref={controlRef}>
        <input
          ref={inputRef}
          type="text"
          className="customer-autocomplete__field"
          name={name}
          value={value}
          onChange={handleInputChange}
          onFocus={handleFocus}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          autoComplete="off"
          spellCheck={false}
          role="combobox"
          aria-expanded={showList}
          aria-controls={listId}
          aria-autocomplete="list"
        />
        {allowClear && value ? (
          <button
            type="button"
            className="customer-autocomplete__clear"
            onClick={clearValue}
            aria-label="Cancella"
          >
            ×
          </button>
        ) : null}
      </div>
      {dropdown && createPortal(dropdown, document.body)}
    </div>
  )
}
