import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import apiService from '../services/api'

const ConversationView = () => {
  const { empresa, clienteId } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const [messages, setMessages] = useState([])
  const [hasMore, setHasMore] = useState(true)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [clienteName, setClienteName] = useState('')
  const [context, setContext] = useState(null)
  const [fetchingMore, setFetchingMore] = useState(false)
  const messagesContainerRef = useRef(null)
  const PAGE_SIZE = 20

  useEffect(() => {
    setMessages([])
    setHasMore(true)
    setLoading(true)
    setError(null)
    setContext(null)
    setClienteName('')
    fetchMessages()
    // eslint-disable-next-line
  }, [empresa, clienteId])

  const fetchMessages = async (before = null, append = false) => {
    try {
      if (before) setFetchingMore(true)
      const data = await apiService.getConversation(empresa, clienteId, { limit: PAGE_SIZE, before })
      if (data?.context?.cliente_name) setClienteName(data.context.cliente_name)
      setContext(data.context)
      const newMessages = data.messages || []
      setHasMore(newMessages.length === PAGE_SIZE)
      setMessages(prev => append ? [...newMessages, ...prev] : newMessages)
    } catch (err) {
      setError('Erro ao carregar conversa')
      console.error(err)
    } finally {
      setLoading(false)
      setFetchingMore(false)
    }
  }

  // Infinite scroll reverso
  useEffect(() => {
    const container = messagesContainerRef.current
    if (!container) return
    const handleScroll = () => {
      if (container.scrollTop === 0 && hasMore && !fetchingMore && messages.length > 0) {
        const oldest = messages[0]
        if (oldest && oldest.timestamp) {
          fetchMessages(oldest.timestamp, true)
        }
      }
    }
    container.addEventListener('scroll', handleScroll)
    return () => container.removeEventListener('scroll', handleScroll)
  }, [messages, hasMore, fetchingMore])

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return ''
    const date = new Date(timestamp)
    return date.toLocaleString('pt-BR')
  }

  const formatDate = (timestamp) => {
    if (!timestamp) return ''
    const date = new Date(timestamp)
    return date.toLocaleDateString('pt-BR')
  }

  const getEmpresaDisplayName = (empresaSlug) => {
    const names = {
      'tinyteams': 'TinyTeams',
      'umas-e-ostras': 'Umas e Ostras',
      'pancia-piena': 'Pancia Piena'
    }
    return names[empresaSlug] || empresaSlug
  }

  if (loading) {
    return (
      <div className="conversation-container">
        <div className="conversation-header">
          <button onClick={() => navigate(-1)} className="back-btn">
            ← Voltar
          </button>
          <h2>Carregando...</h2>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="conversation-container">
        <div className="conversation-header">
          <button onClick={() => navigate(-1)} className="back-btn">
            ← Voltar
          </button>
          <h2>Erro</h2>
        </div>
        <div className="error-message">{error}</div>
      </div>
    )
  }

  // Renderizar mensagens com quebra de data
  let lastDate = null
  const renderedMessages = []
  messages.forEach((message, idx) => {
    const msgDate = formatDate(message.timestamp)
    if (msgDate !== lastDate) {
      renderedMessages.push(
        <div key={`date-${msgDate}-${idx}`} className="date-separator" style={{ textAlign: 'center', margin: '16px 0', color: '#888', fontWeight: 500 }}>
          {msgDate}
        </div>
      )
      lastDate = msgDate
    }
    renderedMessages.push(
      <div
        key={idx}
        className={`message ${message.is_bot ? 'bot' : 'user'}`}
      >
        <div className="message-content">
          <p>{message.text}</p>
          <span className="message-time">
            {formatTimestamp(message.timestamp)}
          </span>
        </div>
      </div>
    )
  })

  return (
    <div className="conversation-container">
      {/* Header */}
      <div className="conversation-header">
        <button onClick={() => navigate(-1)} className="back-btn">
          ← Voltar
        </button>
        <div className="conversation-info">
          <h2>{getEmpresaDisplayName(empresa)}</h2>
          <p>{clienteName ? clienteName : `+${clienteId}`}</p>
          {clienteName && <small>+{clienteId}</small>}
        </div>
      </div>

      {/* Mensagens */}
      <div className="messages-container" ref={messagesContainerRef} style={{ overflowY: 'auto', maxHeight: '70vh', minHeight: 300 }}>
        {renderedMessages.length > 0 ? (
          renderedMessages
        ) : (
          <div className="no-messages">
            <p>Nenhuma mensagem encontrada</p>
          </div>
        )}
        {fetchingMore && (
          <div style={{ textAlign: 'center', color: '#888', margin: 8 }}>Carregando mais...</div>
        )}
      </div>
    </div>
  )
}

export default ConversationView 