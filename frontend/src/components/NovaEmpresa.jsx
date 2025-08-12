import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'
import './NovaEmpresa.css'

const SENSITIVE_FIELDS = [
  { name: 'openai_key', label: 'OpenAI Key' },
  { name: 'twilio_token', label: 'Twilio Token' }
]

const NovaEmpresa = () => {
  const [form, setForm] = useState({
    nome: '',
    whatsapp_number: '',
    google_sheets_id: '',
    openai_key: '',
    twilio_sid: '',
    twilio_token: '',
    twilio_number: '',
    usar_buffer: true,
    mensagem_quebrada: false,
    prompt: '',
    calendar_expanded: false,
    sheets_expanded: false,
    openai_expanded: false,
    trinks_expanded: false,
    knowledge_json: { items: [] }
  })
  
  // Estado separado para controlar accordions
  const [expandedAccordions, setExpandedAccordions] = useState({
    sheets: false,
    openai: false,
    calendar: false,
    trinks: false
  })
  const [apis, setApis] = useState([])
  const [selectedAPIs, setSelectedAPIs] = useState([])
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')
  const [tokenHints, setTokenHints] = useState({})
  const [focusField, setFocusField] = useState('')
  const [activeSection, setActiveSection] = useState('dados-empresa')
  const navigate = useNavigate()

  // Função para lidar com quebras de linha nos campos textarea
  const handleTextareaKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      const cursorPosition = e.target.selectionStart
      const value = e.target.value
      const newValue = value.slice(0, cursorPosition) + '\n' + value.slice(cursorPosition)
      
      // Atualizar o valor do campo
      const { name } = e.target
      if (name) {
        setForm(prev => ({ ...prev, [name]: newValue }))
      }
      
      // Manter o cursor na posição correta após a quebra de linha
      setTimeout(() => {
        const newCursorPosition = cursorPosition + 1
        e.target.setSelectionRange(newCursorPosition, newCursorPosition)
      }, 0)
    }
  }

  // Função para lidar com quebras de linha nos campos de conhecimento
  const handleKnowledgeTextareaKeyDown = (e, index, field) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      const cursorPosition = e.target.selectionStart
      const value = e.target.value
      const newValue = value.slice(0, cursorPosition) + '\n' + value.slice(cursorPosition)
      
      // Atualizar o valor do campo de conhecimento
      handleKnowledgeChange(index, field, newValue)
      
      // Manter o cursor na posição correta após a quebra de linha
      setTimeout(() => {
        const newCursorPosition = cursorPosition + 1
        e.target.setSelectionRange(newCursorPosition, newCursorPosition)
      }, 0)
    }
  }

  const handleNextSection = () => {
    const currentIndex = sections.findIndex(section => section.id === activeSection)
    if (currentIndex < sections.length - 1) {
      setActiveSection(sections[currentIndex + 1].id)
    }
  }

  const handlePreviousSection = () => {
    const currentIndex = sections.findIndex(section => section.id === activeSection)
    if (currentIndex > 0) {
      setActiveSection(sections[currentIndex - 1].id)
    }
  }

  // Gerar slug automaticamente baseado no nome da empresa
  const generateSlug = (nome) => {
    return nome
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9\s-]/g, '')
      .replace(/\s+/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-+|-+$/g, '')
  }

  const webhookUrl = form.nome ? `https://api.tinyteams.app/webhook/${generateSlug(form.nome)}` : ''

  useEffect(() => {
    // Buscar empresas e tokens já cadastrados para sugestões camufladas
    Promise.all([
      api.listEmpresas(),
      api.getAPIs()
    ])
      .then(([empresasData, apisData]) => {
        const hints = {}
        const empresas = empresasData.empresas || [];
        if (Array.isArray(empresas)) {
          SENSITIVE_FIELDS.forEach(field => {
            const map = {}
            empresas.forEach(e => {
              const val = e[field.name]
              if (val) {
                if (!map[val]) map[val] = []
                map[val].push(e.nome)
              }
            })
            hints[field.name] = Object.entries(map).map(([token, empresas]) => ({
              token: '•'.repeat(8),
              empresas: empresas.join(', ')
            }))
          })
        }
        setTokenHints(hints)
        setApis(apisData.apis || [])
      })
      .catch(err => {
        console.error('Erro ao buscar dados:', err)
      })
  }, [])

  const handleChange = e => {
    const { name, value, type, checked } = e.target
    setForm(f => ({ ...f, [name]: type === 'checkbox' ? checked : value }))
  }

  const handleKnowledgeChange = (index, field, value) => {
    setForm(prev => {
      const kj = prev.knowledge_json || { items: [] }
      const items = Array.isArray(kj.items) ? [...kj.items] : []
      items[index] = { ...items[index], [field]: value }
      return { ...prev, knowledge_json: { ...kj, items } }
    })
  }

  const handleAddKnowledgeItem = () => {
    setForm(prev => {
      const kj = prev.knowledge_json || { items: [] }
      const items = Array.isArray(kj.items) ? [...kj.items] : []
      items.push({ key: '', title: '', description: '', active: true })
      return { ...prev, knowledge_json: { ...kj, items } }
    })
  }

  const handleRemoveKnowledgeItem = (index) => {
    setForm(prev => {
      const kj = prev.knowledge_json || { items: [] }
      const items = Array.isArray(kj.items) ? [...kj.items] : []
      items.splice(index, 1)
      return { ...prev, knowledge_json: { ...kj, items } }
    })
  }

  const slugify = (text) => {
    return (text || '')
      .toString()
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9\s-]/g, '')
      .trim()
      .replace(/\s+/g, '-')
      .replace(/-+/g, '-')
  }

  const ensureKeyForItem = (index) => {
    setForm(prev => {
      const kj = prev.knowledge_json || { items: [] }
      const items = Array.isArray(kj.items) ? [...kj.items] : []
      const item = items[index] || {}
      if (!item.key && item.title) {
        item.key = slugify(item.title)
        items[index] = item
      }
      return { ...prev, knowledge_json: { ...kj, items } }
    })
  }

  const handleAPISelection = (apiId) => {
    setSelectedAPIs(prev => 
      prev.includes(apiId) 
        ? prev.filter(id => id !== apiId)
        : [...prev, apiId]
    )
  }

  const handleSubmit = async e => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setSuccess(false)
    
    try {
      const formData = {
        ...form,
        slug: generateSlug(form.nome)
      }
      
      const data = await api.createEmpresa(formData)
      if (data.success) {
        // Conectar APIs selecionadas
        if (selectedAPIs.length > 0) {
          for (const apiId of selectedAPIs) {
            try {
              await api.connectAPI(data.empresa_id, apiId, {})
            } catch (err) {
              console.error(`Erro ao conectar API ${apiId}:`, err)
            }
          }
        }
        
        setSuccess(true)
        setTimeout(() => navigate('/admin'), 1200)
      } else {
        setError(data.error || 'Erro ao cadastrar empresa')
      }
    } catch (err) {
      console.error('Erro ao criar empresa:', err)
      setError('Erro de conexão')
    }
    setLoading(false)
  }

  const sections = [
    {
      id: 'dados-empresa',
      title: 'Dados da Empresa',
      icon: '🏢',
      fields: [
        { name: 'nome', label: 'Nome da Empresa', type: 'text', required: true, placeholder: 'Ex: TinyTeams' },
        { name: 'whatsapp_number', label: 'Número do WhatsApp', type: 'text', placeholder: '+5511999999999' }
      ]
    },
    {
      id: 'dados-entrada',
      title: 'Entrada de Mensagem',
      icon: '📱',
      fields: [
        { name: 'twilio_sid', label: 'Twilio SID', type: 'text', placeholder: 'AC...' },
        { name: 'twilio_token', label: 'Twilio Token', type: 'password', placeholder: 'Token do Twilio' },
        { name: 'twilio_number', label: 'Número Twilio', type: 'text', placeholder: '+5511999999999' }
      ]
    },
    {
      id: 'conexoes-apis',
      title: 'Conexões e APIs',
      icon: '🔗',
      fields: [
        { name: 'google_sheets_id', label: 'Google Sheets ID', type: 'text', placeholder: 'ID da planilha do Google' },
        { name: 'openai_key', label: 'OpenAI Key', type: 'password', placeholder: 'sk-...' }
      ]
    },
    {
      id: 'configuracoes',
      title: 'Configurações',
      icon: '⚙️',
      fields: [
        { name: 'usar_buffer', label: 'Aguardar Mensagens antes de responder', type: 'checkbox' },
        { name: 'mensagem_quebrada', label: 'Mensagem Quebrada', type: 'checkbox' }
      ]
    },
    {
      id: 'prompt',
      title: 'Prompt',
      icon: '🤖',
      fields: [
        { name: 'prompt', label: 'Prompt do Assistente', type: 'textarea', placeholder: 'Digite o prompt que define o comportamento do assistente...' }
      ]
    }
  ]

  const renderField = (field) => {
    const commonProps = {
      name: field.name,
      value: form[field.name] || '',
      onChange: handleChange,
      placeholder: field.placeholder,
      required: field.required
    }

    if (field.type === 'checkbox') {
      return (
        <div key={field.name} className="field-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              {...commonProps}
              checked={form[field.name] || false}
            />
            <span className="checkmark"></span>
            {field.label}
          </label>
        </div>
      )
    }

    if (field.type === 'textarea') {
      return (
        <div key={field.name} className="field-group">
          <label>{field.label}</label>
          <textarea
            {...commonProps}
            rows={6}
            className="form-textarea"
            onKeyDown={handleTextareaKeyDown}
          />
        </div>
      )
    }

    if (field.type === 'password') {
      return (
        <div key={field.name} className="field-group">
          <label>{field.label}</label>
          <input
            type="password"
            {...commonProps}
            onFocus={() => setFocusField(field.name)}
            onBlur={() => setFocusField('')}
            className="form-input"
          />
          {focusField === field.name && tokenHints[field.name] && tokenHints[field.name].length > 0 && (
            <div className="token-hints">
              {tokenHints[field.name].map((h, i) => (
                <div key={i} className="token-hint">
                  {h.token} <span className="token-hint-empresas">({h.empresas})</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )
    }

    return (
      <div key={field.name} className="field-group">
        <label>{field.label}</label>
        <input
          type="text"
          {...commonProps}
          className="form-input"
        />
      </div>
    )
  }

  return (
    <div className="nova-empresa-container">
      <div className="nova-empresa-header">
        <h1>Nova Empresa</h1>
      </div>

      <div className="nova-empresa-content">
        <div className="sections-nav">
          {sections.map(section => (
            <button
              key={section.id}
              className={`section-nav-btn ${activeSection === section.id ? 'active' : ''}`}
              onClick={() => setActiveSection(section.id)}
            >
              <span className="section-icon">{section.icon}</span>
              <span className="section-title">{section.title}</span>
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="nova-empresa-form">
          {sections.map(section => (
            <div
              key={section.id}
              className={`form-section ${activeSection === section.id ? 'active' : ''}`}
            >
              <div className="section-header">
                <h2>{section.icon} {section.title}</h2>
              </div>
              
              <div className="section-fields">
                {section.id === 'conexoes-apis' ? (
                  /* Integrações com accordion */
                  <div className="google-integrations">
                    {/* APIs do Banco de Dados */}
                    {apis.filter(api => api.ativo).map(api => (
                      <div key={api.id} className="integration-group" data-api={api.nome.toLowerCase().replace(/\s+/g, '-')}> 
                        <div className="integration-header">
                          <div className="integration-icon">
                            {api.logo_url ? (
                              <img 
                                src={api.logo_url} 
                                alt={api.nome}
                                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                              />
                            ) : (
                              '🔗'
                            )}
                          </div>
                          <div className="integration-info">
                            <h3>{api.nome}</h3>
                            <p>{api.descricao}</p>
                          </div>
                          <label className="checkbox-label" style={{ margin: 0, padding: 0, border: 'none', background: 'transparent' }}>
                            <input
                              type="checkbox"
                              checked={selectedAPIs.includes(api.id)}
                              onChange={(e) => {
                                e.preventDefault()
                                e.stopPropagation()
                                handleAPISelection(api.id)
                              }}
                            />
                            <span className="checkmark"></span>
                          </label>
                        </div>
                        
                        {selectedAPIs.includes(api.id) && (
                          <div className="integration-fields">
                            {api.tipo_auth === 'oauth2' ? (
                              <>
                                <div className="field-group">
                                  <label>Client ID</label>
                                  <input
                                    type="text"
                                    name={`api_${api.id}_client_id`}
                                    placeholder="Client ID"
                                    className="form-input"
                                    value={form[`api_${api.id}_client_id`] || ''}
                                    onChange={handleChange}
                                  />
                                </div>
                                <div className="field-group">
                                  <label>Client Secret</label>
                                  <input
                                    type="password"
                                    name={`api_${api.id}_client_secret`}
                                    placeholder="Client Secret"
                                    className="form-input"
                                    value={form[`api_${api.id}_client_secret`] || ''}
                                    onChange={handleChange}
                                  />
                                </div>
                              </>
                            ) : (
                              <div className="field-group">
                                <label>{api.nome} API Key</label>
                                <input
                                  type="password"
                                  name={`api_${api.id}_key`}
                                  placeholder={`Chave da API ${api.nome}`}
                                  className="form-input"
                                  value={form[`api_${api.id}_key`] || ''}
                                  onChange={handleChange}
                                />
                                
                                {/* Campo específico para Trinks - Estabelecimento ID */}
                                {api.nome.includes('Trinks') && (
                                  <div className="field-group" style={{ marginTop: '1rem' }}>
                                    <label>ID do Estabelecimento</label>
                                    <input
                                      type="text"
                                      name={`api_${api.id}_estabelecimento_id`}
                                      placeholder="ID do estabelecimento (ex: 12345)"
                                      className="form-input"
                                      value={form[`api_${api.id}_estabelecimento_id`] || ''}
                                      onChange={handleChange}
                                    />
                                    <small className="field-hint">
                                      ID único do estabelecimento na plataforma Trinks. 
                                      Este campo é obrigatório para todos os endpoints da API.
                                    </small>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  /* Campos normais para outras abas */
                  <>
                    {section.fields.map(renderField)}
                    {section.id === 'dados-empresa' && (
                      <div className="knowledge-section">
                        <h3 style={{ marginTop: '1rem' }}>Conhecimento da Empresa</h3>
                        <p className="field-hint">Adicione linhas com Título (esquerda) e Descrição (direita). A chave (key) é gerada automaticamente a partir do título.</p>
                        {(form.knowledge_json?.items || []).map((item, idx) => (
                          <div key={idx} className="knowledge-row">
                            <div className="field-group">
                              <label>Título</label>
                              <input
                                type="text"
                                className="form-input"
                                value={item.title || ''}
                                onChange={(e) => handleKnowledgeChange(idx, 'title', e.target.value)}
                                onBlur={() => ensureKeyForItem(idx)}
                                placeholder="Ex: Horário de funcionamento"
                              />
                            </div>
                            <div className="field-group">
                              <label>Descrição</label>
                              <textarea
                                className="form-textarea"
                                rows={3}
                                value={item.description || ''}
                                onChange={(e) => handleKnowledgeChange(idx, 'description', e.target.value)}
                                onKeyDown={(e) => handleKnowledgeTextareaKeyDown(e, idx, 'description')}
                                placeholder="Ex: Seg-Sex 9h–18h, Sáb 10h–14h"
                              />
                            </div>
                            <div className="actions">
                              <div className="field-group" style={{ width: '130px' }}>
                                <label>Ativo</label>
                                <input
                                  type="checkbox"
                                  checked={item.active !== false}
                                  onChange={(e) => handleKnowledgeChange(idx, 'active', e.target.checked)}
                                />
                              </div>
                              <button type="button" className="remove-btn" onClick={() => handleRemoveKnowledgeItem(idx)}>Remover</button>
                            </div>
                          </div>
                        ))}
                        <button type="button" className="add-btn" onClick={handleAddKnowledgeItem}>+ Adicionar Linha</button>
                      </div>
                    )}
                  </>
                )}
              </div>

              {/* Webhook apenas na aba Entrada de Mensagem */}
              {section.id === 'dados-entrada' && (
                <div className="webhook-info">
                  <strong>Webhook para Twilio:</strong> {webhookUrl}
                </div>
              )}

                              {/* Botões de navegação */}
              <div className="form-actions">
                {activeSection === 'prompt' ? (
                  // Última aba - botão salvar
                  <button type="submit" className="save-btn" disabled={loading}>
                    {loading ? 'Salvando...' : 'Salvar Empresa'}
                  </button>
                ) : (
                  // Abas intermediárias - botão próximo
                  <button type="button" className="next-btn" onClick={handleNextSection}>
                    Próximo
                  </button>
                )}
              </div>
          </div>
        ))}

      </form>

      {/* Mensagens de sucesso e erro fora do formulário */}
      {success && <div className="success-msg">✅ Empresa cadastrada com sucesso!</div>}
      {error && <div className="error-msg">❌ {error}</div>}
    </div>
  </div>
  )
}

export default NovaEmpresa 