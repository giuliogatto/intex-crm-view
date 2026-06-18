import React, { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

const MONTHS = [
  'Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
  'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre'
]

const WEEKDAYS = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']

function parseISO(str) {
  if (!str) return null
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(str)
  if (!match) return null
  const [, y, m, d] = match.map(Number)
  const date = new Date(y, m - 1, d)
  if (date.getFullYear() !== y || date.getMonth() !== m - 1 || date.getDate() !== d) {
    return null
  }
  return date
}

function toISO(date) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

function formatItalian(iso) {
  const date = parseISO(iso)
  if (!date) return ''
  const d = String(date.getDate()).padStart(2, '0')
  const m = String(date.getMonth() + 1).padStart(2, '0')
  return `${d}/${m}/${date.getFullYear()}`
}

function buildCalendarDays(viewDate) {
  const year = viewDate.getFullYear()
  const month = viewDate.getMonth()
  const firstDay = new Date(year, month, 1)
  const startOffset = (firstDay.getDay() + 6) % 7
  const daysInMonth = new Date(year, month + 1, 0).getDate()

  const days = []
  for (let i = 0; i < startOffset; i++) {
    days.push(null)
  }
  for (let day = 1; day <= daysInMonth; day++) {
    days.push(new Date(year, month, day))
  }
  return days
}

export default function DateInput({ name, value, onChange, placeholder = 'Seleziona data' }) {
  const [open, setOpen] = useState(false)
  const [viewDate, setViewDate] = useState(() => parseISO(value) || new Date())
  const [calendarStyle, setCalendarStyle] = useState({ top: 0, left: 0, width: 0 })
  const containerRef = useRef(null)
  const controlRef = useRef(null)
  const calendarRef = useRef(null)

  const updateCalendarPosition = () => {
    if (!controlRef.current) return
    const rect = controlRef.current.getBoundingClientRect()
    const width = Math.max(rect.width, 280)
    let left = rect.left
    const maxLeft = window.innerWidth - width - 12
    if (left > maxLeft) left = Math.max(12, maxLeft)

    setCalendarStyle({
      top: rect.bottom + 8,
      left,
      width
    })
  }

  useEffect(() => {
    if (value) {
      const parsed = parseISO(value)
      if (parsed) setViewDate(parsed)
    }
  }, [value])

  useEffect(() => {
    if (!open) return undefined

    updateCalendarPosition()

    const handleClickOutside = (event) => {
      const inField = containerRef.current?.contains(event.target)
      const inCalendar = calendarRef.current?.contains(event.target)
      if (!inField && !inCalendar) {
        setOpen(false)
      }
    }

    const handleEscape = (event) => {
      if (event.key === 'Escape') setOpen(false)
    }

    const handleReposition = () => updateCalendarPosition()

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

  const emitChange = (nextValue) => {
    onChange({ target: { name, value: nextValue } })
  }

  const selectDate = (date) => {
    emitChange(toISO(date))
    setOpen(false)
  }

  const clearDate = (event) => {
    event.stopPropagation()
    emitChange('')
  }

  const shiftMonth = (delta) => {
    setViewDate((prev) => new Date(prev.getFullYear(), prev.getMonth() + delta, 1))
  }

  const selectedDate = parseISO(value)
  const todayISO = toISO(new Date())
  const calendarDays = buildCalendarDays(viewDate)

  const calendar = open ? (
    <div
      ref={calendarRef}
      className="date-input__calendar"
      role="dialog"
      aria-label="Selettore data"
      style={{
        position: 'fixed',
        top: calendarStyle.top,
        left: calendarStyle.left,
        width: calendarStyle.width
      }}
    >
      <div className="date-input__header">
        <button type="button" className="date-input__nav" onClick={() => shiftMonth(-1)} aria-label="Mese precedente">
          ‹
        </button>
        <span className="date-input__title">
          {MONTHS[viewDate.getMonth()]} {viewDate.getFullYear()}
        </span>
        <button type="button" className="date-input__nav" onClick={() => shiftMonth(1)} aria-label="Mese successivo">
          ›
        </button>
      </div>

      <div className="date-input__weekdays">
        {WEEKDAYS.map((day) => (
          <span key={day} className="date-input__weekday">
            {day}
          </span>
        ))}
      </div>

      <div className="date-input__days">
        {calendarDays.map((date, index) => {
          if (!date) {
            return <span key={`empty-${index}`} className="date-input__day date-input__day--empty" aria-hidden="true" />
          }

          const iso = toISO(date)
          const isSelected = selectedDate && toISO(selectedDate) === iso
          const isToday = iso === todayISO

          return (
            <button
              key={iso}
              type="button"
              className={[
                'date-input__day',
                isSelected ? 'date-input__day--selected' : '',
                isToday ? 'date-input__day--today' : ''
              ].filter(Boolean).join(' ')}
              onClick={() => selectDate(date)}
            >
              {date.getDate()}
            </button>
          )
        })}
      </div>
    </div>
  ) : null

  return (
    <div className={`date-input${open ? ' date-input--open' : ''}`} ref={containerRef}>
      <div className="date-input__control" ref={controlRef}>
        <input
          type="text"
          readOnly
          value={formatItalian(value)}
          placeholder={placeholder}
          className="date-input__field"
          onClick={() => setOpen((prev) => !prev)}
        />
        {value && (
          <button
            type="button"
            className="date-input__clear"
            onClick={clearDate}
            aria-label="Cancella data"
          >
            ×
          </button>
        )}
        <button
          type="button"
          className="date-input__trigger"
          onClick={() => setOpen((prev) => !prev)}
          aria-label="Apri calendario"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M7 2a1 1 0 0 1 1 1v1h8V3a1 1 0 1 1 2 0v1h1a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h1V3a1 1 0 0 1 1-1zm12 8H5v10h14V10zM9 14h2v2H9v-2zm4 0h2v2h-2v-2z" />
          </svg>
        </button>
      </div>

      {calendar && createPortal(calendar, document.body)}
    </div>
  )
}
