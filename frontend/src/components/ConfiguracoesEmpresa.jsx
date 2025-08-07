import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import apiService from '../services/api'
import LoadingSpinner from './LoadingSpinner'
import './ConfiguracoesEmpresa.css'

const ConfiguracoesEmpresa = () => {
  const { empresa } = useParams()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [empresas, setEmpresas] = useState([])
  const [selectedEmpresa, setSelectedEmpresa] = useState(empresa || '')
  const [activeSection, setActiveSection] = useState('dados-empresa')
  const [configuracoes, setConfiguracoes] = useState({
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
    trinks_expanded: false
  })
  
  // Estado separado para controlar accordions
  const [expandedAccordions, setExpandedAccordions] = useState({
    sheets: false,
    openai: false,
    calendar: false,
    trinks: false
  })
  const [apis, setApis] = useState([])
  const [empresaAPIs, setEmpresaAPIs] = useState([])
  const [showTokens, setShowTokens] = useState({})
  const [tokenHints, setTokenHints] = useState({})
  const [focusField, setFocusField] = useState('')
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')

  const SENSITIVE_FIELDS = [
    { name: 'openai_key', label: 'OpenAI Key' },
    { name: 'twilio_token', label: 'Twilio Token' }
  ]

  useEffect(() => {
    carregarEmpresas()
  }, [])

  useEffect(() => {
    if (selectedEmpresa && selectedEmpresa !== 'nova-empresa') {
      carregarConfiguracoes()
    }
  }, [selectedEmpresa])

  // useEffect separado para carregar APIs SEM afetar os dados da empresa
  useEffect(() => {
    if (selectedEmpresa && selectedEmpresa !== 'nova-empresa') {
      carregarAPIs()
    }
  }, [selectedEmpresa])

  // useEffect para mapear dados das APIs quando entrar na aba de APIs
  useEffect(() => {
    if (activeSection === 'conexoes-apis' && empresaAPIs.length > 0) {
      mapearDadosAPIs(empresaAPIs)
    }
  }, [activeSection, empresaAPIs])

  const carregarEmpresas = async () => {
    try {
      const response = await apiService.listEmpresas()
      
      // Usar a nova estrutura com chave 'empresas'
      const empresasList = response.empresas || []
      setEmpresas(empresasList)
      
      // Se não há empresa selecionada e há empresas disponíveis, selecionar a primeira
      if (!selectedEmpresa && empresasList.length > 0) {
        const primeiraEmpresa = empresasList[0].slug
        setSelectedEmpresa(primeiraEmpresa)
        // Atualizar a URL para a primeira empresa
        navigate(`/admin/${primeiraEmpresa}/configuracoes`, { replace: true })
      }
    } catch (error) {
      console.error('Erro ao carregar empresas:', error)
      setError('Erro ao carregar empresas: ' + error.message)
    }
  }

  const carregarConfiguracoes = async () => {
    if (!selectedEmpresa || selectedEmpresa === 'nova-empresa') return
    
    try {
      setLoading(true)
      const response = await apiService.getEmpresaConfiguracoes(selectedEmpresa)
      
      console.log('Resposta da API:', response)
      
      // Mapear os dados da API para o formato do formulário
      const configData = {
        nome: response.nome || '',
        whatsapp_number: response.whatsapp_number || '',
        google_sheets_id: response.google_sheets_id || '',
        openai_key: response.openai_key || '',
        twilio_sid: response.twilio_sid || '',
        twilio_token: response.twilio_token || '',
        twilio_number: response.twilio_number || '',
        usar_buffer: response.usar_buffer !== undefined ? response.usar_buffer : true,
        mensagem_quebrada: response.mensagem_quebrada || false,
        prompt: response.prompt || '',
        calendar_expanded: response.calendar_expanded || false,
        sheets_expanded: response.sheets_expanded || false,
        openai_expanded: response.openai_expanded || false
      }
      
      console.log('Configurações mapeadas:', configData)
      
      setConfiguracoes(configData)

      // Carregar dicas de tokens
      carregarTokenHints()
    } catch (error) {
      console.error('Erro ao carregar configurações:', error)
      setError('Erro ao carregar configurações da empresa')
    } finally {
      setLoading(false)
    }
  }

  const carregarTokenHints = async () => {
    try {
      const response = await apiService.listEmpresas()
      const hints = {}
      // Usar a nova estrutura com chave 'empresas'
      const empresasList = response.empresas || []
      
      if (empresasList.length > 0) {
        SENSITIVE_FIELDS.forEach(field => {
          const map = {}
          empresasList.forEach(e => {
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
    } catch (error) {
      console.error('Erro ao carregar dicas de tokens:', error)
    }
  }

  const carregarAPIs = async () => {
    try {
      const apisResponse = await apiService.getAPIs()
      setApis(apisResponse.apis || [])
      
      // Buscar empresa para obter o ID
      const empresasResponse = await apiService.listEmpresas()
      const empresa = empresasResponse.empresas?.find(e => e.slug === selectedEmpresa)
      
      if (empresa) {
        try {
          const empresaAPIsResponse = await apiService.getEmpresaAPIs(empresa.id)
          console.log('APIs da empresa:', empresaAPIsResponse.apis)
          console.log('Empresa ID:', empresa.id)
          console.log('Empresa Slug:', empresa.slug)
          setEmpresaAPIs(empresaAPIsResponse.apis || [])
          
          // NÃO mapear aqui - será feito pelo useEffect quando entrar na aba
        } catch (error) {
          console.error('Erro ao carregar APIs da empresa:', error)
          setEmpresaAPIs([])
        }
      }
    } catch (error) {
      console.error('Erro ao carregar APIs:', error)
    }
  }

  // Função separada para mapear dados das APIs - chamada apenas quando necessário
  const mapearDadosAPIs = (empresaAPIs) => {
    const novasConfiguracoes = { ...configuracoes }
    
    empresaAPIs.forEach(empApi => {
      if (empApi.config) {
        const apiId = empApi.api_id
        
        // Para APIs OAuth2 (Google Calendar, Google Sheets)
        if (empApi.api_name === 'Google Calendar' || empApi.api_name === 'Google Sheets') {
          if (empApi.config.google_calendar_client_id || empApi.config.google_sheets_client_id) {
            novasConfiguracoes[`api_${apiId}_client_id`] = empApi.config.google_calendar_client_id || empApi.config.google_sheets_client_id
          }
          if (empApi.config.google_calendar_client_secret || empApi.config.google_sheets_client_secret) {
            novasConfiguracoes[`api_${apiId}_client_secret`] = empApi.config.google_calendar_client_secret || empApi.config.google_sheets_client_secret
          }
        }
        
        // Para APIs com API Key (OpenAI, etc.)
        else {
          if (empApi.api_name === 'OpenAI' && empApi.config.openai_key) {
            novasConfiguracoes[`api_${apiId}_key`] = empApi.config.openai_key
          }
          else {
            const apiKey = empApi.config.api_key || empApi.config.key || empApi.config.token
            if (apiKey) {
              novasConfiguracoes[`api_${apiId}_key`] = apiKey
            }
          }
        }
      }
    })
    
    setConfiguracoes(novasConfiguracoes)
  }

  const conectarAPI = async (apiId) => {
    try {
      // Buscar empresa para obter o ID
      const empresasResponse = await apiService.listEmpresas()
      const empresa = empresasResponse.empresas?.find(e => e.slug === selectedEmpresa)
      
      if (empresa) {
        await apiService.connectAPI(empresa.id, apiId, {})
        setSuccess('API conectada com sucesso!')
        setTimeout(() => setSuccess(false), 3000)
        carregarAPIs() // Recarregar lista
      }
    } catch (error) {
      console.error('Erro ao conectar API:', error)
      setError('Erro ao conectar API: ' + error.message)
    }
  }

  const handleChange = e => {
    const { name, value, type, checked } = e.target
    const newValue = type === 'checkbox' ? checked : value
    setConfiguracoes(f => ({ ...f, [name]: newValue }))
  }

  const handleSalvar = async () => {
    try {
      setSaving(true)
      setError('')
      setSuccess(false)
      

      
      await apiService.updateEmpresaConfiguracoes(selectedEmpresa, configuracoes)
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
    } catch (error) {
      console.error('Erro ao salvar configurações:', error)
      setError('Erro ao salvar configurações. Tente novamente.')
    } finally {
      setSaving(false)
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
      value: configuracoes[field.name] || '',
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
              checked={configuracoes[field.name] || false}
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

  if (loading && selectedEmpresa && selectedEmpresa !== 'nova-empresa') {
    return <LoadingSpinner type="content" />
  }

  return (
    <div className="configuracoes-container">
      <div className="configuracoes-header">
        <h1>Configurações da Empresa</h1>
      </div>

      {/* Filtro de Empresa */}
      <div className="empresa-filter">
        <label>Selecionar Empresa:</label>
        <div className="empresa-select-container">
          <select 
            value={selectedEmpresa} 
            onChange={(e) => {
              const empresaSlug = e.target.value
              setSelectedEmpresa(empresaSlug)
              if (empresaSlug) {
                // Atualizar a URL para a empresa selecionada
                navigate(`/admin/${empresaSlug}/configuracoes`, { replace: true })
              }
            }}
            className="empresa-select"
          >
            <option value="">Selecione uma empresa</option>
            {empresas.map(emp => (
              <option key={emp.slug} value={emp.slug}>
                {emp.nome}
              </option>
            ))}
          </select>
          <div className="select-arrow">▼</div>
        </div>
            </div>

      {empresas.length > 0 ? (
        <div className="configuracoes-content">
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

          {selectedEmpresa && selectedEmpresa !== 'nova-empresa' ? (
            <form className="configuracoes-form">
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
                        {/* Lista unificada de APIs */}
                        {apis.filter(api => api.ativo).map(api => {
                          // Verificar se a API está conectada
                          const connectedAPI = empresaAPIs.find(empApi => empApi.api_name === api.nome)
                          const isConnected = !!connectedAPI
                          
                          // Debug para Trinks
                          if (api.nome.includes('Trinks')) {
                            console.log('API Trinks encontrada:', api)
                            console.log('Connected API:', connectedAPI)
                            console.log('Is Connected:', isConnected)
                            console.log('Todas as APIs da empresa:', empresaAPIs)
                            console.log('Comparando nomes:')
                            empresaAPIs.forEach(empApi => {
                              console.log(`  - empApi.api_name: "${empApi.api_name}" vs api.nome: "${api.nome}"`)
                            })
                          }
                          
                          // Debug para Trinks
                          if (api.nome.includes('Trinks')) {
                            console.log('API Trinks encontrada:', api)
                            console.log('Connected API:', connectedAPI)
                            console.log('Is Connected:', isConnected)
                            console.log('Todas as APIs da empresa:', empresaAPIs)
                          }
                          
                          return (
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
                                <button 
                                  type="button"
                                  className="accordion-toggle"
                                  onClick={(e) => {
                                    e.preventDefault()
                                    e.stopPropagation()
                                    setExpandedAccordions(prev => ({ ...prev, [`api_${api.id}`]: !prev[`api_${api.id}`] }))
                                  }}
                                >
                                  {expandedAccordions[`api_${api.id}`] ? '−' : '+'}
                                </button>
                              </div>
                              
                              {expandedAccordions[`api_${api.id}`] && (
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
                                          value={configuracoes[`api_${api.id}_client_id`] || ''}
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
                                          value={configuracoes[`api_${api.id}_client_secret`] || ''}
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
                                        value={configuracoes[`api_${api.id}_key`] || ''}
                                        onChange={handleChange}
                                      />
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    ) : (
                      /* Campos normais para outras abas */
                      section.fields.map(renderField)
                    )}
                  </div>

                  {/* Webhook apenas na aba Entrada de Mensagem */}
                  {section.id === 'dados-entrada' && (
                                    <div className="webhook-info">
                  <strong>Webhook para Twilio:</strong> https://api.tinyteams.app/webhook/{selectedEmpresa}
                </div>
                  )}

                  {/* Botões de navegação */}
                  <div className="form-actions">
                    {activeSection === 'prompt' ? (
                      // Última aba - botão salvar
                      <button type="button" className="save-btn" onClick={handleSalvar} disabled={saving}>
                        {saving ? 'Salvando...' : 'Salvar Configurações'}
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
          ) : (
            <div className="no-empresa-selected">
              <p>Selecione uma empresa no filtro acima para ver suas configurações.</p>
          </div>
          )}

          {/* Mensagens de sucesso e erro */}
          {success && <div className="success-msg">✅ Configurações salvas com sucesso!</div>}
          {error && <div className="error-msg">❌ {error}</div>}
        </div>
      ) : (
        <div className="no-empresas">
          <p>Nenhuma empresa encontrada. Use a página "Nova Empresa" para criar uma empresa primeiro.</p>
        </div>
      )}
    </div>
  )
}

export default ConfiguracoesEmpresa 