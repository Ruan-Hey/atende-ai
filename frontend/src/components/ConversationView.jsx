import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import apiService from '../services/api'
import LoadingSpinner from './LoadingSpinner'

const ConversationView = () => {
  const { empresa, clienteId } = useParams()
  const navigate = useNavigate()
  const [messages, setMessages] = useState([])
  const [hasMore, setHasMore] = useState(true)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [clienteName, setClienteName] = useState('')
  const [fetchingMore, setFetchingMore] = useState(false)
  const messagesContainerRef = useRef(null)
  const PAGE_SIZE = 20

  // Dados fake para demonstração
  const fakeMessages = [
    {
      id: 1,
      text: "Olá! Gostaria de saber mais sobre os serviços da TinyTeams. Vocês atendem empresas de todos os tamanhos?",
      timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 horas atrás
      is_bot: false
    },
    {
      id: 2,
      text: "Olá! Sim, atendemos empresas de todos os tamanhos. Nossos serviços incluem gestão de equipes, comunicação interna e ferramentas de produtividade. Como posso te ajudar?",
      timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000 + 5 * 60 * 1000).toISOString(), // 2h atrás + 5min
      is_bot: true
    },
    {
      id: 3,
      text: "Interessante! Vocês têm algum plano específico para startups? Estamos com 15 funcionários e precisamos organizar melhor nossa comunicação.",
      timestamp: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(), // 1 hora atrás
      is_bot: false
    },
    {
      id: 4,
      text: "Perfeito! Temos o plano Startup que é ideal para empresas com até 20 funcionários. Inclui chat em tempo real, compartilhamento de arquivos e integração com ferramentas populares. Quer que eu envie mais detalhes?",
      timestamp: new Date(Date.now() - 1 * 60 * 60 * 1000 + 3 * 60 * 1000).toISOString(), // 1h atrás + 3min
      is_bot: true
    },
    {
      id: 5,
      text: "Sim, por favor! E vocês fazem demonstração gratuita?",
      timestamp: new Date(Date.now() - 30 * 60 * 1000).toISOString(), // 30 min atrás
      is_bot: false
    },
    {
      id: 6,
      text: "Claro! Oferecemos uma demonstração gratuita de 14 dias sem compromisso. Vou te enviar um link para agendar. Qual seria o melhor horário para você?",
      timestamp: new Date(Date.now() - 30 * 60 * 1000 + 2 * 60 * 1000).toISOString(), // 30min atrás + 2min
      is_bot: true
    },
    {
      id: 7,
      text: "Perfeito! Pode ser amanhã às 14h?",
      timestamp: new Date(Date.now() - 15 * 60 * 1000).toISOString(), // 15 min atrás
      is_bot: false
    },
    {
      id: 8,
      text: "Perfeito! Agendei para amanhã às 14h. Vou enviar um convite por email com o link da reunião. Alguma dúvida específica que gostaria de abordar na demonstração?",
      timestamp: new Date(Date.now() - 15 * 60 * 1000 + 1 * 60 * 1000).toISOString(), // 15min atrás + 1min
      is_bot: true
    },
    {
      id: 9,
      text: "Gostaria de saber sobre a integração com Slack e como funciona a migração de dados. Obrigado!",
      timestamp: new Date(Date.now() - 5 * 60 * 1000).toISOString(), // 5 min atrás
      is_bot: false
    },
    {
      id: 10,
      text: "Ótimas perguntas! Temos integração nativa com Slack e um processo de migração muito simples. Vou preparar uma demonstração específica desses pontos. Até amanhã! 👋",
      timestamp: new Date(Date.now() - 2 * 60 * 1000).toISOString(), // 2 min atrás
      is_bot: true
    }
  ]

  useEffect(() => {
    setMessages([])
    setHasMore(true)
    setLoading(true)
    setError(null)
    setClienteName('')
    
    // Simular carregamento
    setTimeout(() => {
      setClienteName('João Silva')
      setMessages(fakeMessages)
      setLoading(false)
    }, 1000)
    
    // eslint-disable-next-line
  }, [empresa, clienteId])

  const fetchMessages = async (before = null, append = false) => {
    try {
      if (before) setFetchingMore(true)
      const data = await apiService.getConversation(empresa, clienteId, { limit: PAGE_SIZE, before })
      if (data?.context?.cliente_name) setClienteName(data.context.cliente_name)
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
    return date.toLocaleTimeString('pt-BR', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: true 
    })
  }

  const formatDate = (timestamp) => {
    if (!timestamp) return ''
    const date = new Date(timestamp)
    const today = new Date()
    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)
    
    if (date.toDateString() === today.toDateString()) {
      return 'Hoje'
    } else if (date.toDateString() === yesterday.toDateString()) {
      return 'Ontem'
    } else {
      return date.toLocaleDateString('pt-BR', { 
        day: '2-digit', 
        month: '2-digit', 
        year: 'numeric' 
      })
    }
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
    return <LoadingSpinner type="content" />
  }

  if (error) {
    return (
      <div className="conversation-container">
        <div className="conversation-header">
          <button onClick={() => navigate(-1)} className="back-btn">
            ←
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
        <div key={`date-${msgDate}-${idx}`} className="date-separator">
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
      {/* Header moderno */}
      <div className="conversation-header">
        <div className="header-left">
          <button onClick={() => navigate(-1)} className="back-btn">
            ←
          </button>
          <div className="contact-info">
            <div className="contact-avatar">
              {clienteName ? clienteName.charAt(0).toUpperCase() : 'U'}
            </div>
            <div className="contact-details">
              <h2>{clienteName || getEmpresaDisplayName(empresa)}</h2>
              <p className="contact-status">+{clienteId}</p>
            </div>
          </div>
        </div>
        <div className="header-actions">
          <button className="header-action-btn">
            <span className="action-icon">ℹ️</span>
          </button>
          <button className="header-action-btn">
            <span className="action-icon">⋮</span>
          </button>
        </div>
      </div>

      {/* Mensagens */}
      <div className="messages-container" ref={messagesContainerRef}>
        {renderedMessages.length > 0 ? (
          renderedMessages
        ) : (
          <div className="no-messages">
            <div className="no-messages-icon">💬</div>
            <p>Nenhuma mensagem encontrada</p>
            <small>Inicie uma conversa para ver as mensagens aqui</small>
          </div>
        )}
        {fetchingMore && (
          <div className="loading-more">
            <div className="loading-spinner"></div>
            <span>Carregando mais...</span>
          </div>
        )}
      </div>
    </div>
  )
}

export default ConversationView 