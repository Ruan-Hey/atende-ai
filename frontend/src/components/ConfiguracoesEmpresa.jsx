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
  const [configuracoes, setConfiguracoes] = useState({
    prompt: '',
    configuracoes: {
      mensagemQuebrada: false,
      buffer: false
    },
    apis: {
      openai: {
        ativo: false,
        token: ''
      },
      google: {
        ativo: false,
        token: ''
      },
      chatwoot: {
        ativo: false,
        token: ''
      }
    }
  })
  const [showTokens, setShowTokens] = useState({})

  useEffect(() => {
    carregarConfiguracoes()
  }, [empresa])

  const carregarConfiguracoes = async () => {
    try {
      setLoading(true)
      const response = await apiService.getEmpresaConfiguracoes(empresa)
      setConfiguracoes(response)
    } catch (error) {
      console.error('Erro ao carregar configurações:', error)
      // Se não conseguir carregar, usar configurações padrão
      setConfiguracoes({
        prompt: '',
        configuracoes: {
          mensagemQuebrada: false,
          buffer: false
        },
        apis: {
          openai: { ativo: false, token: '' },
          google: { ativo: false, token: '' },
          chatwoot: { ativo: false, token: '' }
        }
      })
    } finally {
      setLoading(false)
    }
  }

  const handleSalvar = async () => {
    try {
      setSaving(true)
      await apiService.updateEmpresaConfiguracoes(empresa, configuracoes)
      alert('Configurações salvas com sucesso!')
      // Recarregar configurações para atualizar os tokens mascarados
      await carregarConfiguracoes()
    } catch (error) {
      console.error('Erro ao salvar configurações:', error)
      alert('Erro ao salvar configurações. Tente novamente.')
    } finally {
      setSaving(false)
    }
  }

  const toggleTokenVisibility = (apiKey) => {
    setShowTokens(prev => ({
      ...prev,
      [apiKey]: !prev[apiKey]
    }))
  }

  const handleConfiguracaoChange = (key, value) => {
    setConfiguracoes(prev => ({
      ...prev,
      configuracoes: {
        ...prev.configuracoes,
        [key]: value
      }
    }))
  }

  const handleApiChange = (apiKey, field, value) => {
    setConfiguracoes(prev => ({
      ...prev,
      apis: {
        ...prev.apis,
        [apiKey]: {
          ...prev.apis[apiKey],
          [field]: value
        }
      }
    }))
  }

  // Função para verificar se o token está mascarado
  const isTokenMasked = (token) => {
    return token === '***' || token === ''
  }

  // Função para limpar token mascarado quando usuário começa a digitar
  const handleTokenInput = (apiKey, value) => {
    if (value === '***') {
      // Se o usuário clicou no campo mascarado, limpar para permitir edição
      handleApiChange(apiKey, 'token', '')
    } else {
      handleApiChange(apiKey, 'token', value)
    }
  }

  if (loading) {
    return <LoadingSpinner type="content" />
  }

  return (
    <div className="configuracoes-container">
      <div className="configuracoes-header">
        <button 
          className="back-btn" 
          onClick={() => navigate(`/admin/${empresa}`)}
        >
          ← Voltar
        </button>
        <h1>Configurações da Empresa</h1>
      </div>

      <div className="configuracoes-content">
        {/* Seção 1: Prompt Principal */}
        <div className="config-section">
          <div className="section-header">
            <h2>Prompt Principal</h2>
            <p>Configure o prompt principal que será usado pelo assistente</p>
          </div>
          <div className="prompt-container">
            <textarea
              value={configuracoes.prompt}
              onChange={(e) => setConfiguracoes(prev => ({ ...prev, prompt: e.target.value }))}
              placeholder="Digite aqui o prompt principal da sua empresa..."
              className="prompt-textarea"
              rows="8"
            />
            <div className="prompt-info">
              <small>Este prompt será usado como base para todas as interações do assistente</small>
            </div>
          </div>
        </div>

        {/* Seção 2: Configurações Ativas */}
        <div className="config-section">
          <div className="section-header">
            <h2>Configurações Ativas</h2>
            <p>Gerencie as funcionalidades disponíveis</p>
          </div>
          <div className="configuracoes-grid">
            <div className="config-item">
              <div className="config-info">
                <h3>Mensagem Quebrada</h3>
                <p>Permite que o assistente continue conversas interrompidas</p>
              </div>
              <label className="switch">
                <input
                  type="checkbox"
                  checked={configuracoes.configuracoes.mensagemQuebrada}
                  onChange={(e) => handleConfiguracaoChange('mensagemQuebrada', e.target.checked)}
                />
                <span className="slider"></span>
              </label>
            </div>

            <div className="config-item">
              <div className="config-info">
                <h3>Buffer de Mensagens</h3>
                <p>Armazena mensagens temporariamente para melhor performance</p>
              </div>
              <label className="switch">
                <input
                  type="checkbox"
                  checked={configuracoes.configuracoes.buffer}
                  onChange={(e) => handleConfiguracaoChange('buffer', e.target.checked)}
                />
                <span className="slider"></span>
              </label>
            </div>
          </div>
        </div>

        {/* Seção 3: APIs */}
        <div className="config-section">
          <div className="section-header">
            <h2>Integrações de API</h2>
            <p>Configure as APIs externas utilizadas</p>
          </div>
          <div className="apis-container">
            {Object.entries(configuracoes.apis).map(([apiKey, apiConfig]) => (
              <div key={apiKey} className="api-item">
                <div className="api-header">
                  <div className="api-info">
                    <h3>{apiKey.charAt(0).toUpperCase() + apiKey.slice(1)}</h3>
                    <p>Configuração da API {apiKey}</p>
                  </div>
                  <label className="switch">
                    <input
                      type="checkbox"
                      checked={apiConfig.ativo}
                      onChange={(e) => handleApiChange(apiKey, 'ativo', e.target.checked)}
                    />
                    <span className="slider"></span>
                  </label>
                </div>
                
                {apiConfig.ativo && (
                  <div className="api-token-section">
                    <div className="token-input-container">
                                             <input
                         type={showTokens[apiKey] ? "text" : "password"}
                         value={apiConfig.token}
                         onChange={(e) => handleTokenInput(apiKey, e.target.value)}
                         placeholder={isTokenMasked(apiConfig.token) ? "Clique para adicionar token" : `Token da API ${apiKey}`}
                         className="token-input"
                       />
                      <button
                        type="button"
                        className="toggle-token-btn"
                        onClick={() => toggleTokenVisibility(apiKey)}
                      >
                        {showTokens[apiKey] ? "🔒" : "👁️"}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Botão Salvar */}
        <div className="save-section">
          <button 
            className="save-btn"
            onClick={handleSalvar}
            disabled={saving}
          >
            {saving ? 'Salvando...' : 'Salvar Configurações'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default ConfiguracoesEmpresa 