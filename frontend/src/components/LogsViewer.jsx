import { useState, useEffect } from 'react'
import apiService from '../services/api'

const LogsViewer = () => {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedEmpresa, setSelectedEmpresa] = useState('')
  const [empresas, setEmpresas] = useState([])
  const [filterLevel, setFilterLevel] = useState('all')

  useEffect(() => {
    loadEmpresas()
    loadLogs()
    // Atualizar logs a cada 10 segundos
    const interval = setInterval(loadLogs, 10000)
    return () => clearInterval(interval)
  }, [selectedEmpresa, filterLevel])

  const loadEmpresas = async () => {
    try {
      const response = await apiService.listEmpresas()
      setEmpresas(response.empresas || [])
    } catch (error) {
      console.error('Erro ao carregar empresas:', error)
    }
  }

  const loadLogs = async () => {
    try {
      setLoading(true)
      const response = await apiService.getLogs(selectedEmpresa || null, 100)
      setLogs(response.logs || [])
      setError(null)
    } catch (error) {
      console.error('Erro ao carregar logs:', error)
      setError('Erro ao carregar logs')
    } finally {
      setLoading(false)
    }
  }

  const getLevelColor = (level) => {
    switch (level?.toLowerCase()) {
      case 'error':
        return '#dc3545'
      case 'warning':
        return '#ffc107'
      case 'info':
        return '#17a2b8'
      case 'debug':
        return '#6c757d'
      default:
        return '#6c757d'
    }
  }

  const getLevelIcon = (level) => {
    switch (level?.toLowerCase()) {
      case 'error':
        return '❌'
      case 'warning':
        return '⚠️'
      case 'info':
        return 'ℹ️'
      case 'debug':
        return '🔍'
      default:
        return '📝'
    }
  }

  const filteredLogs = logs.filter(log => {
    if (filterLevel !== 'all' && log.level?.toLowerCase() !== filterLevel) {
      return false
    }
    return true
  })

  if (loading && logs.length === 0) {
    return (
      <div className="dashboard">
        <div className="dashboard-header">
          <h1 className="dashboard-title">Carregando logs...</h1>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="dashboard">
        <div className="dashboard-header">
          <h1 className="dashboard-title">Erro</h1>
          <p className="dashboard-subtitle" style={{ color: 'red' }}>{error}</p>
          <button 
            className="btn btn-primary" 
            onClick={loadLogs}
            style={{ marginTop: '1rem' }}
          >
            Tentar novamente
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1 className="dashboard-title">Logs e Erros do Sistema</h1>
        <p className="dashboard-subtitle">Monitoramento em tempo real de logs e erros</p>
      </div>

      <div className="filters-container" style={{ marginBottom: '2rem' }}>
        <div className="filter-group">
          <label htmlFor="empresa-filter">Empresa:</label>
          <select 
            id="empresa-filter"
            value={selectedEmpresa}
            onChange={(e) => setSelectedEmpresa(e.target.value)}
            className="form-select"
          >
            <option value="">Todas as empresas</option>
            {empresas.map(empresa => (
              <option key={empresa.slug} value={empresa.slug}>
                {empresa.nome}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="level-filter">Nível:</label>
          <select 
            id="level-filter"
            value={filterLevel}
            onChange={(e) => setFilterLevel(e.target.value)}
            className="form-select"
          >
            <option value="all">Todos os níveis</option>
            <option value="error">Erro</option>
            <option value="warning">Aviso</option>
            <option value="info">Informação</option>
            <option value="debug">Debug</option>
          </select>
        </div>

        <button 
          className="btn btn-secondary"
          onClick={loadLogs}
        >
          🔄 Atualizar
        </button>
      </div>

      <div className="logs-container">
        <div className="logs-header">
          <h3>Logs ({filteredLogs.length})</h3>
          <div className="logs-stats">
            <span style={{ color: '#dc3545' }}>❌ {filteredLogs.filter(l => l.level === 'ERROR').length}</span>
            <span style={{ color: '#ffc107' }}>⚠️ {filteredLogs.filter(l => l.level === 'WARNING').length}</span>
            <span style={{ color: '#17a2b8' }}>ℹ️ {filteredLogs.filter(l => l.level === 'INFO').length}</span>
          </div>
        </div>

        {filteredLogs.length > 0 ? (
          <div className="logs-list">
            {filteredLogs.map((log, index) => (
              <div 
                key={index} 
                className="log-entry"
                style={{ 
                  borderLeft: `4px solid ${getLevelColor(log.level)}`,
                  backgroundColor: log.level === 'ERROR' ? '#fff5f5' : '#fff'
                }}
              >
                <div className="log-header">
                  <span className="log-level" style={{ color: getLevelColor(log.level) }}>
                    {getLevelIcon(log.level)} {log.level}
                  </span>
                  <span className="log-timestamp">
                    {new Date(log.timestamp).toLocaleString('pt-BR')}
                  </span>
                  {log.empresa && (
                    <span className="log-empresa">
                      🏢 {log.empresa}
                    </span>
                  )}
                </div>
                <div className="log-message">
                  {log.message}
                </div>
                {log.details && (
                  <div className="log-details">
                    <pre>{JSON.stringify(log.details, null, 2)}</pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>
            Nenhum log encontrado com os filtros atuais.
          </div>
        )}
      </div>

      <div style={{ marginTop: '2rem', padding: '1rem', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
        <h4>Tipos de Log:</h4>
        <ul style={{ marginTop: '0.5rem', paddingLeft: '1.5rem' }}>
          <li><strong>ERROR:</strong> Erros críticos que precisam de atenção imediata</li>
          <li><strong>WARNING:</strong> Avisos sobre situações que podem se tornar problemas</li>
          <li><strong>INFO:</strong> Informações gerais sobre o funcionamento do sistema</li>
          <li><strong>DEBUG:</strong> Informações detalhadas para desenvolvimento</li>
        </ul>
      </div>
    </div>
  )
}

export default LogsViewer 