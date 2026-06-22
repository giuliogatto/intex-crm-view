import React, { useRef, useEffect, useState } from 'react'
import { authFetch } from '../utils/auth'
import { parseLlmJson } from '../utils/llm'

export default function ChatPanel({ onResponse, onClienteSelect }) {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([])
  const [chatId, setChatId] = useState(null)
  const [sending, setSending] = useState(false)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || sending) return

    setInput('')
    setMessages((prev) => [...prev, { role: 'user', text }])
    setSending(true)

    try {
      const payload = { message: text }
      if (chatId != null) payload.chat_id = chatId

      const res = await authFetch('/llmrequest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Errore nella richiesta LLM')

      if (data.chat_id != null) setChatId(data.chat_id)

      const parsed = parseLlmJson(data.response)
      const result = await onResponse(parsed, text)
      const messaggio = typeof result === 'string' ? result : result.messaggio

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: messaggio,
          disambiguation: result.disambiguation || null
        }
      ])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: `Errore: ${err.message}`, isError: true }
      ])
    } finally {
      setSending(false)
    }
  }

  const handleClienteChoice = (msgIndex, cliente, context) => {
    onClienteSelect(cliente.codice, context)
    const confirmation = `Cliente selezionato: ${cliente.ragione_sociale} (${cliente.codice})`
    setMessages((prev) =>
      prev.map((msg, idx) =>
        idx === msgIndex
          ? {
              ...msg,
              disambiguation: null,
              text: msg.text ? `${msg.text}\n\n${confirmation}` : confirmation
            }
          : msg
      )
    )
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="chat-panel">
      <div className="chat-panel__head">Assistente Intex</div>
      <div className="chat-panel__messages">
        {messages.length === 0 && !sending && (
          <div className="chat-panel__placeholder">
            Scrivi una richiesta in italiano, ad esempio: &ldquo;Mostrami le fatture di PRIMA SRL per il 2026&rdquo;
          </div>
        )}
        {messages.map((msg, idx) => (
          <div key={idx} className="chat-message-group">
            <div
              className={`chat-bubble chat-bubble--${msg.role}${msg.isError ? ' chat-bubble--error' : ''}`}
            >
              {msg.text}
            </div>
            {msg.disambiguation && (
              <div className="chat-disambiguation">
                <p className="chat-disambiguation__prompt">{msg.disambiguation.prompt}</p>
                <div className="chat-disambiguation__list">
                  {msg.disambiguation.candidates.map((cliente) => (
                    <button
                      key={cliente.codice}
                      type="button"
                      className="chat-cliente-btn"
                      onClick={() =>
                        handleClienteChoice(idx, cliente, msg.disambiguation.context)
                      }
                    >
                      <span className="chat-cliente-btn__name">{cliente.ragione_sociale}</span>
                      <span className="chat-cliente-btn__code">{cliente.codice}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
        {sending && (
          <div className="chat-bubble chat-bubble--assistant chat-bubble--loading">
            <div className="spinner" />
            <span>Elaborazione in corso...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <div className="chat-panel__input">
        <textarea
          className="chat-panel__textarea"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Scrivi la tua richiesta..."
          rows={3}
          disabled={sending}
        />
        <button
          type="button"
          className="btn btn--primary chat-panel__send"
          onClick={handleSend}
          disabled={sending || !input.trim()}
        >
          Invia
        </button>
      </div>
    </div>
  )
}
