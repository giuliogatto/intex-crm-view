import React, { useState, useEffect } from 'react'
import { authFetch } from '../utils/auth'
import { useAuth } from '../context/AuthContext'

const CHATS_PAGE_SIZE = 20
const MESSAGES_PAGE_SIZE = 50

function Pagination({ page, pages, total, onPageChange, label }) {
  if (pages <= 1) return null

  return (
    <div className="pagination">
      <span className="pagination__info">
        {label}: pagina {page} di {pages} ({total} totali)
      </span>
      <div className="pagination__controls">
        <button
          type="button"
          className="btn"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          Precedente
        </button>
        <button
          type="button"
          className="btn"
          disabled={page >= pages}
          onClick={() => onPageChange(page + 1)}
        >
          Successiva
        </button>
      </div>
    </div>
  )
}

function roleLabel(role, chat) {
  if (role === 'user') return chat?.user_id || 'Utente'
  if (role === 'assistant') return chat?.model || 'Assistente'
  return role
}

const COLLAPSE_THRESHOLD = 400

function ArchiveMessage({ msg, chatDetail }) {
  const isLong = msg.content.length > COLLAPSE_THRESHOLD
  const [expanded, setExpanded] = useState(true)

  return (
    <div
      className={`chat-archive-message chat-archive-message--${msg.role}${isLong && !expanded ? ' is-collapsed' : ''}`}
    >
      <div className="chat-archive-message__header">
        <span className="chat-archive-message__sender">
          {roleLabel(msg.role, chatDetail)}
        </span>
        <span className="chat-archive-message__meta">
          {msg.created_at}
          {msg.provider_message_id && (
            <span className="chat-archive-message__provider" title={msg.provider_message_id}>
              · {msg.provider_message_id.length > 12
                ? `${msg.provider_message_id.slice(0, 12)}…`
                : msg.provider_message_id}
            </span>
          )}
        </span>
      </div>
      <pre className="chat-archive-message__content">{msg.content}</pre>
      {isLong && (
        <button
          type="button"
          className="btn chat-archive-message__toggle"
          onClick={() => setExpanded((prev) => !prev)}
        >
          {expanded ? 'Comprimi' : 'Espandi messaggio'}
        </button>
      )}
    </div>
  )
}

export default function ChatsPage() {
  const { user, logout } = useAuth()
  const [chats, setChats] = useState([])
  const [chatsPage, setChatsPage] = useState(1)
  const [chatsPages, setChatsPages] = useState(1)
  const [chatsTotal, setChatsTotal] = useState(0)
  const [chatsLoading, setChatsLoading] = useState(true)

  const [selectedChatId, setSelectedChatId] = useState(null)
  const [chatDetail, setChatDetail] = useState(null)
  const [messages, setMessages] = useState([])
  const [messagesPage, setMessagesPage] = useState(1)
  const [messagesPages, setMessagesPages] = useState(1)
  const [messagesTotal, setMessagesTotal] = useState(0)
  const [messagesLoading, setMessagesLoading] = useState(false)

  useEffect(() => {
    setChatsLoading(true)
    authFetch(`/api/chats?page=${chatsPage}&limit=${CHATS_PAGE_SIZE}`)
      .then((res) => res.json())
      .then((data) => {
        if (data.data) {
          setChats(data.data)
          setChatsPages(data.pages || 1)
          setChatsTotal(data.total || 0)
        }
        setChatsLoading(false)
      })
      .catch((err) => {
        console.error('Error fetching chats:', err)
        setChatsLoading(false)
      })
  }, [chatsPage])

  useEffect(() => {
    if (!selectedChatId) {
      setChatDetail(null)
      setMessages([])
      return
    }

    setMessagesLoading(true)
    authFetch(
      `/api/chats/${selectedChatId}/messages?page=${messagesPage}&limit=${MESSAGES_PAGE_SIZE}`
    )
      .then((res) => res.json())
      .then((data) => {
        if (data.chat) {
          setChatDetail(data.chat)
          setMessages(data.data || [])
          setMessagesPages(data.pages || 1)
          setMessagesTotal(data.total || 0)
        }
        setMessagesLoading(false)
      })
      .catch((err) => {
        console.error('Error fetching messages:', err)
        setMessagesLoading(false)
      })
  }, [selectedChatId, messagesPage])

  const handleSelectChat = (chatId) => {
    setSelectedChatId(chatId)
    setMessagesPage(1)
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="app-title-group">
          <img src="/logo.webp" alt="Intex" className="app-logo" />
          <span className="badge-mock">Archivio Conversazioni</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span className="badge-user">
            {user?.username}
          </span>
          <a href="/" className="btn">
            ← Torna alla consultazione
          </a>
          <button type="button" className="btn" onClick={logout}>Esci</button>
        </div>
      </header>

      <div className="chats-layout">
        <div className="panel chats-list-panel">
          <div className="panel__head">
            <span>Conversazioni ({chatsTotal})</span>
          </div>
          <div className="panel__body panel__body--compact">
            {chatsLoading ? (
              <div className="loading-indicator">
                <div className="spinner" />
                <span>Caricamento chat...</span>
              </div>
            ) : chats.length === 0 ? (
              <p className="chats-empty">Nessuna conversazione salvata.</p>
            ) : (
              <>
                <div className="table-wrap">
                  <table className="data chats-table">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Utente</th>
                        <th>Modello</th>
                        <th>Messaggi</th>
                        <th>Creato il</th>
                      </tr>
                    </thead>
                    <tbody>
                      {chats.map((chat) => (
                        <tr
                          key={chat.id}
                          className={`chats-table__row${selectedChatId === chat.id ? ' is-selected' : ''}`}
                          onClick={() => handleSelectChat(chat.id)}
                        >
                          <td>{chat.id}</td>
                          <td>{chat.user_id}</td>
                          <td><code className="chats-code">{chat.model}</code></td>
                          <td>{chat.message_count}</td>
                          <td>{chat.created_at}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <Pagination
                  page={chatsPage}
                  pages={chatsPages}
                  total={chatsTotal}
                  onPageChange={setChatsPage}
                  label="Chat"
                />
              </>
            )}
          </div>
        </div>

        <div className="panel chats-detail-panel">
          <div className="panel__head">
            <span>
              {selectedChatId
                ? `Messaggi — Chat #${selectedChatId}`
                : 'Seleziona una conversazione'}
            </span>
          </div>
          <div className="panel__body">
            {!selectedChatId ? (
              <p className="chats-empty">Clicca su una riga per visualizzare i messaggi.</p>
            ) : messagesLoading ? (
              <div className="loading-indicator">
                <div className="spinner" />
                <span>Caricamento messaggi...</span>
              </div>
            ) : (
              <>
                {chatDetail && (
                  <div className="detail-header-info chats-detail-meta">
                    <div className="detail-info-item">
                      <span className="detail-info-item__label">Utente</span>
                      <span className="detail-info-item__value">{chatDetail.user_id}</span>
                    </div>
                    <div className="detail-info-item">
                      <span className="detail-info-item__label">Modello</span>
                      <span className="detail-info-item__value">
                        <code className="chats-code">{chatDetail.model}</code>
                      </span>
                    </div>
                    <div className="detail-info-item">
                      <span className="detail-info-item__label">Creato il</span>
                      <span className="detail-info-item__value">{chatDetail.created_at}</span>
                    </div>
                    <div className="detail-info-item">
                      <span className="detail-info-item__label">Messaggi</span>
                      <span className="detail-info-item__value">{messagesTotal}</span>
                    </div>
                  </div>
                )}

                <div className="chats-messages">
                  {messages.map((msg) => (
                    <ArchiveMessage key={msg.id} msg={msg} chatDetail={chatDetail} />
                  ))}
                </div>

                <Pagination
                  page={messagesPage}
                  pages={messagesPages}
                  total={messagesTotal}
                  onPageChange={setMessagesPage}
                  label="Messaggi"
                />
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
