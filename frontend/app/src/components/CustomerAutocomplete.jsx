import React, { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { authFetch } from '../utils/auth'

const MAX_RESULTS = 20

function formatCustomerLabel(customer) {
  return `${customer.ragione_sociale} (${customer.codice})`
}

function matchesCustomer(customer, query) {
  const q = query.trim().toLowerCase()
  if (!q) return true
  return (
    customer.ragione_sociale.toLowerCase().includes(q) ||
    String(customer.codice).toLowerCase().includes(q)
  )
}

export default function CustomerAutocomplete({
  name,
  value,
  onChange,
  placeholder = 'Cerca per nome o codice cliente',
  allowClear = false
}) {
  const [customers, setCustomers] = useState([])
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [listStyle, setListStyle] = useState({ top: 0, left: 0, width: 0 })

  const containerRef = useRef(null)
  const controlRef = useRef(null)
  const listRef = useRef(null)
  const inputRef = useRef(null)

  const selectedCustomer = useMemo(
    () => customers.find((customer) => customer.codice === value) ?? null,
    [customers, value]
  )

  const results = useMemo(() => {
    if (!open) return []
    return customers.filter((customer) => matchesCustomer(customer, query)).slice(0, MAX_RESULTS)
  }, [customers, query, open])

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
      width
    })
  }

  useEffect(() => {
    authFetch('/api/clienti')
      .then((res) => res.json())
      .then((resData) => {
        if (resData.data) setCustomers(resData.data)
      })
      .catch((err) => console.error('Error fetching customers:', err))
  }, [])

  useEffect(() => {
    if (isEditing) return
    if (selectedCustomer) {
      setQuery(formatCustomerLabel(selectedCustomer))
    } else {
      setQuery('')
    }
  }, [selectedCustomer, isEditing])

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
  }, [open, selectedCustomer])

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
    if (selectedCustomer) {
      setQuery(formatCustomerLabel(selectedCustomer))
    } else {
      setQuery('')
    }
  }

  const selectCustomer = (customer) => {
    emitChange(customer.codice)
    setQuery(formatCustomerLabel(customer))
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
    if (selectedCustomer) {
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
        <div className="customer-autocomplete__empty">Nessun cliente trovato</div>
      ) : (
        results.map((customer) => (
          <button
            key={customer.codice}
            type="button"
            role="option"
            aria-selected={customer.codice === value}
            className={`customer-autocomplete__option${customer.codice === value ? ' customer-autocomplete__option--selected' : ''}`}
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => selectCustomer(customer)}
          >
            <span className="customer-autocomplete__name">{customer.ragione_sociale}</span>
            <span className="customer-autocomplete__code">{customer.codice}</span>
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
            aria-label="Cancella cliente selezionato"
          >
            ×
          </button>
        )}
      </div>
      {dropdown && createPortal(dropdown, document.body)}
    </div>
  )
}
