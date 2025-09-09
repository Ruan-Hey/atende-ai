import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import apiService from '../services/api'
import LoadingSpinner from './LoadingSpinner'

const EmpresaDashboard = () => {
  const params = useParams()
  const navigate = useNavigate()
  
  const { empresa } = params
  
  // Normalizar o slug da empresa para minúsculas
  const empresaSlug = empresa ? empresa.toLowerCase() : null
  
  // Se não tiver empresa, mostrar erro
  if (!empresa || !empresaSlug) {
    return (
      <div className="dashboard">
        <div className="dashboard-header">
          <h1 className="dashboard-title">Erro</h1>
          <p className="dashboard-subtitle" style={{ color: 'red' }}>
            Slug da empresa não encontrado na URL. 
            <br />
            URL atual: {window.location.pathname}
            <br />
            Parâmetros: {JSON.stringify(params)}
          </p>
        </div>
      </div>
    )
  }

  const [empresaData, setEmpresaData] = useState({
    nome: empresa,
    atendimentos: 0,
    reservas: 0,
    clientes: 0,
    status: 'Ativo'
  })

  const [clientes, setClientes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadEmpresaData = useCallback(async () => {
    try {
      setLoading(true)
      
      // Carregar dados da empresa usando o slug normalizado
      const data = await apiService.getEmpresaMetrics(empresaSlug)
      setEmpresaData(data)
      
      // Carregar lista de clientes usando o slug normalizado
      try {
        const clientesData = await apiService.getEmpresaClientes(empresaSlug)
        setClientes(clientesData.clientes || [])
      } catch (clientesError) {
        console.error('Erro ao carregar clientes:', clientesError)
        setClientes([])
      }
      
    } catch (error) {
      console.error(`Erro ao carregar dados da empresa ${empresaSlug}:`, error)
      setError('Erro ao carregar dados da empresa. Verifique se o backend está rodando.')
    } finally {
      setLoading(false)
    }
  }, [empresaSlug])

  useEffect(() => {
    if (empresaSlug) {
      loadEmpresaData()
    }
  }, [empresaSlug, loadEmpresaData])

  const getEmpresaDisplayName = (empresaSlug) => {
    const names = {
      'tinyteams': 'TinyTeams',
      'umas-e-ostras': 'Umas e Ostras',
      'pancia-piena': 'Pancia Piena'
    }
    return names[empresaSlug] || empresaSlug
  }

  const handleClienteClick = (clienteId) => {
    navigate(`/conversation/${empresaSlug}/${clienteId}`)
  }

  const getActivityInfo = (tipoAtividade) => {
    switch (tipoAtividade) {
      case 'mensagem':
        return { icon: '💬', label: 'Mensagem', color: '#374151' }
      case 'reserva':
        return { icon: '📅', label: 'Reserva', color: '#10b981' }
      case 'atendimento':
        return { icon: '👨‍💼', label: 'Atendimento', color: '#f59e0b' }
      case 'consulta':
        return { icon: '❓', label: 'Consulta', color: '#8b5cf6' }
      default:
        return { icon: '📋', label: tipoAtividade || 'Atividade', color: '#6b7280' }
    }
  }

  const formatDate = (timestamp) => {
    if (!timestamp) return 'N/A'
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now - date
    const diffMins = Math.floor(diffMs / (1000 * 60))
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffMins < 1) return 'Agora'
    if (diffMins < 60) return `${diffMins}min atrás`
    if (diffHours < 24) return `${diffHours}h atrás`
    if (diffDays < 7) return `${diffDays}d atrás`
    return date.toLocaleDateString('pt-BR', { 
      day: '2-digit', 
      month: '2-digit', 
      year: 'numeric' 
    })
  }

  if (loading) {
    return <LoadingSpinner type="page" />
  }

  if (error) {
    return (
      <div className="dashboard">
        <div className="dashboard-header">
          <h1 className="dashboard-title">Erro</h1>
          <p className="dashboard-subtitle" style={{ color: 'red' }}>{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1 className="dashboard-title">{getEmpresaDisplayName(empresa)}</h1>
        <p className="dashboard-subtitle">Dashboard específico da empresa</p>
      </div>

      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-title">Total de Atendimentos</div>
          <div className="metric-value">{empresaData.atendimentos}</div>
        </div>
        
        <div className="metric-card">
          <div className="metric-title">Reservas Realizadas</div>
          <div className="metric-value">{empresaData.reservas}</div>
        </div>
        
        <div className="metric-card">
          <div className="metric-title">Clientes Únicos</div>
          <div className="metric-value">{empresaData.clientes}</div>
        </div>
        
        <div className="metric-card">
          <div className="metric-title">Status</div>
          <div className="metric-value" style={{ fontSize: '1.5rem' }}>
            {empresaData.status === 'ativo' ? '✅' : '❌'} {empresaData.status}
          </div>
        </div>
      </div>

      <div className="table-container">
        <div className="table-header">
          <h3>Clientes da Empresa</h3>
        </div>
        {clientes.length > 0 ? (
          <div className="clientes-list">
            {clientes.map((cliente, index) => (
              <div
                key={index}
                className="cliente-item"
                onClick={() => handleClienteClick(cliente.cliente_id)}
              >
                <div className="cliente-avatar">
                  {cliente.nome ? cliente.nome.charAt(0).toUpperCase() : 'C'}
                  {cliente.ultima_atividade && 
                   new Date(cliente.ultima_atividade) > new Date(Date.now() - 24 * 60 * 60 * 1000) && (
                    <div className="recent-activity-indicator"></div>
                  )}
                </div>
                <div className="cliente-info">
                  <div className="cliente-header">
                    <div className="cliente-name">
                      {cliente.nome}
                      {cliente.ultima_atividade && 
                       new Date(cliente.ultima_atividade) > new Date(Date.now() - 24 * 60 * 60 * 1000) && (
                        <span className="recent-activity-badge"></span>
                      )}
                    </div>
                    <div className="cliente-phone">
                      +{cliente.cliente_id}
                    </div>
                  </div>
                  <div className="cliente-activity-info">
                    {(() => {
                      const activityInfo = getActivityInfo(cliente.tipo_atividade)
                      return (
                        <>
                          <span 
                            className="activity-type"
                            style={{ 
                              color: activityInfo.color,
                              background: activityInfo.color === '#374151' ? '#f3f4f6' : 
                                         activityInfo.color === '#10b981' ? '#ecfdf5' :
                                         activityInfo.color === '#f59e0b' ? '#fffbeb' :
                                         activityInfo.color === '#8b5cf6' ? '#faf5ff' :
                                         '#f9fafb'
                            }}
                          >
                            {activityInfo.icon} {activityInfo.label}
                          </span>
                          <span className="activity-time">
                            {formatDate(cliente.ultima_atividade)}
                          </span>
                          {cliente.total_mensagens > 0 && (
                            <span className="message-count">
                              {cliente.total_mensagens} msg
                            </span>
                          )}
                        </>
                      )
                    })()}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>
            Nenhum cliente encontrado para esta empresa.
          </div>
        )}
      </div>
    </div>
  )
}

export default EmpresaDashboard 