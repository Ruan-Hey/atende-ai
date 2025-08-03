import { useState, useEffect } from 'react'
import apiService from '../services/api'
import LoadingSpinner from './LoadingSpinner'

const BufferStatus = () => {
  const [bufferStatus, setBufferStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadBufferStatus()
    // Atualizar a cada 5 segundos
    const interval = setInterval(loadBufferStatus, 5000)
    return () => clearInterval(interval)
  }, [])

  const loadBufferStatus = async () => {
    try {
      setLoading(true)
      const status = await apiService.getBufferStatus()
      setBufferStatus(status)
      setError(null)
    } catch (error) {
      console.error('Erro ao carregar status do buffer:', error)
      setError('Erro ao carregar status do buffer')
    } finally {
      setLoading(false)
    }
  }

  const forceProcessBuffer = async (cliente_id, empresa) => {
    try {
      await apiService.forceProcessBuffer(cliente_id, empresa)
      loadBufferStatus() // Recarregar status
    } catch (error) {
      console.error('Erro ao forçar processamento:', error)
    }
  }

  if (loading && !bufferStatus) {
    return <LoadingSpinner type="content" />
  }

  if (error) {
    return (
      <div className="dashboard">
        <div className="dashboard-header">
          <h1 className="dashboard-title">Erro</h1>
          <p className="dashboard-subtitle" style={{ color: 'red' }}>{error}</p>
          <button 
            className="btn btn-primary" 
            onClick={loadBufferStatus}
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
        <h1 className="dashboard-title">Status do Buffer de Mensagens</h1>
        <p className="dashboard-subtitle">Monitoramento em tempo real do agrupamento de mensagens</p>
      </div>

      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-title">Buffers Ativos</div>
          <div className="metric-value">{bufferStatus?.active_buffers || 0}</div>
        </div>
        
        <div className="metric-card">
          <div className="metric-title">Timers Ativos</div>
          <div className="metric-value">{bufferStatus?.active_timers || 0}</div>
        </div>
      </div>

      <div className="table-container">
        <div className="table-header">
          <h3>Detalhes dos Buffers</h3>
        </div>
        {bufferStatus?.buffer_details && Object.keys(bufferStatus.buffer_details).length > 0 ? (
          <table className="table">
            <thead>
              <tr>
                <th>Cliente/Empresa</th>
                <th>Mensagens</th>
                <th>Mensagem Mais Antiga</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(bufferStatus.buffer_details).map(([key, details]) => {
                const [empresa, cliente_id] = key.split(':', 2)
                const oldestMessage = details.oldest_message ? 
                  new Date(details.oldest_message).toLocaleString('pt-BR') : 'N/A'
                
                return (
                  <tr key={key}>
                    <td>
                      <strong>{empresa}</strong><br/>
                      <small>{cliente_id}</small>
                    </td>
                    <td>
                      <span style={{ 
                        color: details.message_count > 1 ? 'orange' : 'green',
                        fontWeight: 'bold' 
                      }}>
                        {details.message_count} mensagem{details.message_count !== 1 ? 's' : ''}
                      </span>
                    </td>
                    <td>{oldestMessage}</td>
                    <td>
                      <button 
                        className="btn btn-secondary"
                        onClick={() => forceProcessBuffer(cliente_id, empresa)}
                        style={{ fontSize: '0.8rem', padding: '0.5rem 1rem' }}
                      >
                        Forçar Processamento
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        ) : (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>
            Nenhum buffer ativo no momento.
          </div>
        )}
      </div>

      <div style={{ marginTop: '2rem', padding: '1rem', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
        <h4>Como funciona o buffer:</h4>
        <ul style={{ marginTop: '0.5rem', paddingLeft: '1.5rem' }}>
          <li>Mensagens são agrupadas por cliente e empresa</li>
          <li>Timer de 10 segundos para processar mensagens agrupadas</li>
          <li>Mensagens de texto são combinadas em uma única resposta</li>
          <li>Mensagens de áudio são processadas individualmente</li>
          <li>Reduz o número de respostas e melhora a experiência do usuário</li>
        </ul>
      </div>
    </div>
  )
}

export default BufferStatus 