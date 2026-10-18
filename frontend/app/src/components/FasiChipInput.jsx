import React, { useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { authFetch } from '../utils/auth'

const DEBOUNCE_MS = 250
const MIN_CHARS = 2

function buildSuggestUrl(query, exclude) {
  const search = new URLSearchParams()
  search.set('q', query)
  ;(exclude || []).forEach((chip) => {
    if (chip) search.append('exclude', chip)
  })
  return `/api/cicli/suggest/fasi?${search.toString()}`
}

/**
 * Chip-input fasi con autocomplete su ricerca_sinonimi.
 * Testo libero sempre valido: Invio senza selezione aggiunge la stringa digitata.
 */
export default function FasiChipInput({
  chips = [],
  onChange,
  draft = '',
  onDraftChange,
  placeholder = 'Parola chiave + Invio (es. mangiapelo, stone wash)...',
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
  const pickingRef = useRef(false)

  const emitChips = (next) => onChange(next)
  const emitDraft = (next) => onDraftChange(next)

  const addChip = (raw) => {
    const value = String(raw || '').trim()
    if (!value) return
    const exists = chips.some((c) => c.toLowerCase() === value.toLowerCase())
    if (!exists) emitChips([...chips, value])
    emitDraft('')
    setResults([])
    setHighlight(-1)
    setOpen(false)
  }

  const removeChip = (chip) => {
    emitChips(chips.filter((c) => c !== chip))
  }

  const updateListPosition = () => {
    if (!controlRef.current) return
    const rect = controlRef.current.getBoundingClientRect()
    const width = Math.max(rect.width, 280)
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
    if (query.trim().length < MIN_CHARS) {
      setResults([])
      setLoading(false)
      return
    }
    const controller = new AbortController()
    abortRef.current = controller
    setLoading(true)
    authFetch(buildSuggestUrl(query.trim(), chips), { signal: controller.signal })
      .then((res) => res.json())
      .then((resData) => {
        if (controller.signal.aborted) return
        setResults(Array.isArray(resData.data) ? resData.data : [])
        setHighlight(-1)
      })
      .catch((err) => {
        if (err?.name === 'AbortError') return
        console.error('Error fetching fasi suggestions:', err)
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
    const q = String(draft || '')
    if (q.trim().length < MIN_CHARS) {
      setResults([])
      setLoading(false)
      return undefined
    }
    debounceRef.current = setTimeout(() => fetchSuggestions(q), DEBOUNCE_MS)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
    // chips used only for exclude list in fetch
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft, open, chips.join('|')])

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
      if (abortRef.current) abortRef.current.abort()
    }
  }, [])

  const selectSuggestion = (item) => {
    pickingRef.current = true
    addChip(item?.value)
    inputRef.current?.focus()
    // Resta true oltre il timeout di onBlur (120ms)
    window.setTimeout(() => {
      pickingRef.current = false
    }, 180)
  }

  const handleKeyDown = (event) => {
    if (event.key === 'ArrowDown') {
      if (String(draft || '').trim().length >= MIN_CHARS) {
        event.preventDefault()
        setOpen(true)
        setHighlight((prev) => (results.length ? (prev + 1) % results.length : -1))
      }
      return
    }
    if (event.key === 'ArrowUp') {
      if (open && results.length) {
        event.preventDefault()
        setHighlight((prev) => (prev <= 0 ? results.length - 1 : prev - 1))
      }
      return
    }
    if (event.key === 'Enter') {
      event.preventDefault()
      if (open && highlight >= 0 && results[highlight]) {
        selectSuggestion(results[highlight])
      } else {
        addChip(draft)
      }
      return
    }
    if (event.key === 'Escape') {
      setOpen(false)
      setHighlight(-1)
      return
    }
    if (event.key === 'Backspace' && !draft && chips.length) {
      removeChip(chips[chips.length - 1])
    }
  }

  const handleBlur = () => {
    // Evita di creare il chip mentre si clicca un suggerimento
    window.setTimeout(() => {
      if (pickingRef.current) return
      if (listRef.current?.contains(document.activeElement)) return
      addChip(draft)
    }, 120)
  }

  const showList = open && String(draft || '').trim().length >= MIN_CHARS
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
        <div className="customer-autocomplete__empty">Nessun suggerimento — Invio per usare il testo</div>
      ) : (
        results.map((item, index) => (
          <button
            key={`${item.value}::${item.secondary || ''}::${index}`}
            type="button"
            role="option"
            aria-selected={index === highlight}
            className={`customer-autocomplete__option${
              index === highlight ? ' customer-autocomplete__option--selected' : ''
            }`}
            onMouseDown={(event) => {
              event.preventDefault()
              pickingRef.current = true
            }}
            onMouseEnter={() => setHighlight(index)}
            onClick={() => selectSuggestion(item)}
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
    <div ref={containerRef}>
      <div
        className={`chip-input${open ? ' chip-input--suggest-open' : ''}`}
        ref={controlRef}
        onClick={() => inputRef.current?.focus()}
      >
        {(chips || []).map((chip) => (
          <span key={chip} className="chip">
            {chip}
            <button
              type="button"
              className="chip__remove"
              onClick={(event) => {
                event.stopPropagation()
                removeChip(chip)
              }}
              aria-label={`Rimuovi ${chip}`}
            >
              ×
            </button>
          </span>
        ))}
        <input
          ref={inputRef}
          type="text"
          value={draft}
          onChange={(e) => {
            emitDraft(e.target.value)
            setOpen(true)
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
          onBlur={handleBlur}
          placeholder={chips.length ? '' : placeholder}
          autoComplete="off"
          spellCheck={false}
          role="combobox"
          aria-expanded={showList}
          aria-controls={listId}
          aria-autocomplete="list"
        />
      </div>
      {dropdown && createPortal(dropdown, document.body)}
    </div>
  )
}
