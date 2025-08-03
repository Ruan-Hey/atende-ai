import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import apiService from '../services/api'
import LoadingSpinner from './LoadingSpinner'

const EmpresaDashboard = () => {
  const { empresa } = useParams()
  const navigate = useNavigate()
  
  // Normalizar o slug da empresa para minúsculas
  const empresaSlug = empresa.toLowerCase()
  
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

  useEffect(() => {
    loadEmpresaData()
  }, [empresaSlug])

  const loadEmpresaData = async () => {
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
  }

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

  const formatDate = (timestamp) => {
    if (!timestamp) return 'N/A'
    return new Date(timestamp).toLocaleString('pt-BR')
  }

  if (loading) {
    return <LoadingSpinner type="content" />
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
          <table className="table">
            <thead>
              <tr>
                <th>Nome</th>
                <th>Telefone</th>
                <th>Último Atendimento</th>
              </tr>
            </thead>
            <tbody>
              {clientes.map((cliente, index) => (
                <tr key={index}>
                  <td>
                    <span 
                      onClick={() => handleClienteClick(cliente.cliente_id)}
                      style={{ 
                        cursor: 'pointer',
                        color: '#007bff',
                        textDecoration: 'underline',
                        fontWeight: 'bold'
                      }}
                    >
                      {cliente.nome}
                    </span>
                  </td>
                  <td>
                    <span 
                      onClick={() => handleClienteClick(cliente.cliente_id)}
                      style={{ 
                        cursor: 'pointer',
                        color: '#007bff',
                        textDecoration: 'underline',
                        fontWeight: 'bold'
                      }}
                    >
                      +{cliente.cliente_id}
                    </span>
                  </td>
                  <td>{formatDate(cliente.ultima_atividade)}</td>
                </tr>
              ))}
            </tbody>
          </table>
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