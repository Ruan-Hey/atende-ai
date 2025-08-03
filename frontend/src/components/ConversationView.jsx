import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import apiService from '../services/api'
import LoadingSpinner from './LoadingSpinner'

const ConversationView = () => {
  const { empresa, clienteId } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  
  // Estados para conversas
  const [conversations, setConversations] = useState([])
  const [selectedConversation, setSelectedConversation] = useState(null)
  const [loadingConversations, setLoadingConversations] = useState(true)
  
  // Estados para mensagens
  const [messages, setMessages] = useState([])
  const [hasMore, setHasMore] = useState(true)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [error, setError] = useState(null)
  const [fetchingMore, setFetchingMore] = useState(false)
  const messagesContainerRef = useRef(null)
  const PAGE_SIZE = 20

  // Estado para mobile tabs
  const [activeTab, setActiveTab] = useState('conversations') // 'conversations' ou 'messages'
  const [isMobile, setIsMobile] = useState(false)

  // Dados fake para demonstração - REMOVIDO, agora usando API real

  // Detectar se é mobile
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768)
    }
    
    checkMobile()
    window.addEventListener('resize', checkMobile)
    
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  // Carregar lista de conversas
  useEffect(() => {
    const loadConversations = async () => {
      setLoadingConversations(true)
      try {
        // Buscar dados reais da API
        const data = await apiService.getConversations(empresa)
        setConversations(data.clientes || [])
      } catch (err) {
        console.error('Erro ao carregar conversas:', err)
        setConversations([])
      } finally {
        setLoadingConversations(false)
      }
    }

    loadConversations()
  }, [empresa])

  // Selecionar conversa baseada no clienteId da URL
  useEffect(() => {
    if (clienteId && conversations.length > 0) {
      const conversation = conversations.find(c => c.cliente_id === clienteId)
      if (conversation) {
        setSelectedConversation(conversation)
        if (isMobile) {
          setActiveTab('messages')
        }
      }
    } else if (conversations.length > 0 && !selectedConversation) {
      // Se não há clienteId na URL e não há conversa selecionada, selecionar a primeira
      setSelectedConversation(conversations[0])
      if (isMobile) {
        setActiveTab('messages')
      }
    }
  }, [clienteId, conversations, isMobile, selectedConversation])

  // Carregar mensagens quando uma conversa é selecionada
  useEffect(() => {
    if (!selectedConversation) {
      setMessages([])
      return
    }

    const loadMessages = async () => {
      setLoadingMessages(true)
      setMessages([])
      setHasMore(true)
      setError(null)
      
      try {
        // Buscar dados reais da API
        const data = await apiService.getConversation(empresa, selectedConversation.cliente_id, { limit: PAGE_SIZE })
        
        // Verificar se há mensagens e se são válidas
        if (data && data.messages && Array.isArray(data.messages)) {
          setMessages(data.messages)
          setHasMore(data.messages.length === PAGE_SIZE)
        } else {
          setMessages([])
          setHasMore(false)
        }
      } catch (err) {
        setError('Erro ao carregar mensagens')
        console.error('Erro ao carregar mensagens:', err)
        setMessages([])
        setHasMore(false)
      } finally {
        setLoadingMessages(false)
      }
    }

    loadMessages()
  }, [selectedConversation, empresa])

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

  const fetchMessages = async (before = null, append = false) => {
    if (!selectedConversation) return
    
    try {
      if (before) setFetchingMore(true)
      
      // Buscar dados reais da API
      const data = await apiService.getConversation(empresa, selectedConversation.cliente_id, { limit: PAGE_SIZE, before })
      const newMessages = data.messages || []
      setHasMore(newMessages.length === PAGE_SIZE)
      setMessages(prev => append ? [...newMessages, ...prev] : newMessages)
    } catch (err) {
      setError('Erro ao carregar mais mensagens')
      console.error(err)
    } finally {
      setFetchingMore(false)
    }
  }

  const handleConversationSelect = (conversation) => {
    setSelectedConversation(conversation)
    navigate(`/conversation/${empresa}/${conversation.cliente_id}`)
    if (isMobile) {
      setActiveTab('messages')
    }
  }

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

  const formatLastActivity = (timestamp) => {
    if (!timestamp) return ''
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now - date
    const diffMins = Math.floor(diffMs / (1000 * 60))
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffMins < 1) return 'Agora'
    if (diffMins < 60) return `${diffMins}min`
    if (diffHours < 24) return `${diffHours}h`
    if (diffDays < 7) return `${diffDays}d`
    return formatDate(timestamp)
  }

  const getEmpresaDisplayName = (empresaSlug) => {
    const names = {
      'tinyteams': 'TinyTeams',
      'umas-e-ostras': 'Umas e Ostras',
      'pancia-piena': 'Pancia Piena'
    }
    return names[empresaSlug] || empresaSlug
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

  // Componente de lista de conversas
  const ConversationsList = () => (
    <div className="conversations-list">
      <div className="conversations-header">
        <h3>Conversas</h3>
        <div className="search-container">
          <input 
            type="text" 
            placeholder="Buscar conversas..." 
            className="search-input"
          />
        </div>
      </div>
      
      <div className="conversations-content">
        {loadingConversations ? (
          <div className="loading-conversations">
            <LoadingSpinner type="content" />
          </div>
        ) : conversations.length > 0 ? (
          conversations.map((conversation) => {
            // Determinar se há mensagens não lidas baseado na última atividade
            const hasUnread = conversation.total_mensagens > 0 && 
                             conversation.ultima_atividade && 
                             new Date(conversation.ultima_atividade) > new Date(Date.now() - 24 * 60 * 60 * 1000) // Últimas 24h
            
            return (
              <div
                key={conversation.cliente_id}
                className={`conversation-item ${selectedConversation?.cliente_id === conversation.cliente_id ? 'active' : ''}`}
                onClick={() => handleConversationSelect(conversation)}
              >
                <div className="conversation-avatar">
                  {conversation.nome ? conversation.nome.charAt(0).toUpperCase() : 'U'}
                  {hasUnread && <div className="unread-indicator"></div>}
                </div>
                <div className="conversation-info">
                  <div className="conversation-name">
                    {conversation.nome}
                    {hasUnread && <span className="unread-badge"></span>}
                  </div>
                  <div className="conversation-last-message">
                    {conversation.tipo_atividade === 'mensagem' ? 'Mensagem' : conversation.tipo_atividade}
                  </div>
                  <div className="conversation-time">
                    {formatLastActivity(conversation.ultima_atividade)}
                  </div>
                </div>
              </div>
            )
          })
        ) : (
          <div className="no-conversations">
            <div className="no-conversations-icon">💬</div>
            <p>Nenhuma conversa encontrada</p>
            <small>As conversas aparecerão aqui quando houver mensagens</small>
          </div>
        )}
      </div>
    </div>
  )

  // Componente de mensagens
  const MessagesView = () => (
    <div className="messages-view">
      {selectedConversation ? (
        <>
          {/* Header da conversa */}
          <div className="conversation-header">
            <div className="header-left">
              {isMobile && (
                <button 
                  onClick={() => setActiveTab('conversations')} 
                  className="back-btn"
                >
                  ←
                </button>
              )}
              <div className="contact-info">
                <div className="contact-avatar">
                  {selectedConversation.nome ? selectedConversation.nome.charAt(0).toUpperCase() : 'U'}
                </div>
                <div className="contact-details">
                  <h2>{selectedConversation.nome}</h2>
                  <p className="contact-status">+{selectedConversation.cliente_id}</p>
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
            {loadingMessages ? (
              <LoadingSpinner type="content" />
            ) : error ? (
              <div className="error-message">{error}</div>
            ) : renderedMessages.length > 0 ? (
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
        </>
      ) : (
        <div className="no-conversation-selected">
          <div className="no-conversation-icon">💬</div>
          <h3>Selecione uma conversa</h3>
          <p>Escolha uma conversa da lista para ver as mensagens</p>
        </div>
      )}
    </div>
  )

  // Componente de tabs para mobile
  const MobileTabs = () => (
    <div className="mobile-tabs">
      <button
        className={`tab-btn ${activeTab === 'conversations' ? 'active' : ''}`}
        onClick={() => setActiveTab('conversations')}
      >
        <span className="tab-icon">👥</span>
        <span className="tab-text">Conversas</span>
      </button>
      <button
        className={`tab-btn ${activeTab === 'messages' ? 'active' : ''}`}
        onClick={() => setActiveTab('messages')}
      >
        <span className="tab-icon">💬</span>
        <span className="tab-text">Mensagens</span>
      </button>
    </div>
  )

  if (loadingConversations) {
    return <LoadingSpinner type="content" />
  }

  return (
    <div className="conversation-view-container">
      {/* Tabs para mobile */}
      {isMobile && <MobileTabs />}
      
      <div className="conversation-layout">
        {/* Lista de conversas - sempre visível no desktop, condicional no mobile */}
        <div className={`conversations-sidebar ${isMobile && activeTab === 'conversations' ? 'active' : ''}`}>
          <ConversationsList />
        </div>
        
        {/* Área de mensagens - sempre visível no desktop, condicional no mobile */}
        <div className={`messages-area ${isMobile && activeTab === 'messages' ? 'active' : ''}`}>
          <MessagesView />
        </div>
      </div>
    </div>
  )
}

export default ConversationView 