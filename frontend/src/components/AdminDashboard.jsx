import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import apiService from '../services/api'

const AdminDashboard = () => {
  const [metrics, setMetrics] = useState({
    total_empresas: 0,
    total_clientes: 0,
    total_reservas: 0,
    total_atendimentos: 0,
    empresas: []
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const navigate = useNavigate()
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState({
    slug: '', nome: '', whatsapp_number: '', google_sheets_id: '', chatwoot_token: '', openai_key: '', twilio_sid: '', twilio_token: '', twilio_number: '', chatwoot_inbox_id: '', chatwoot_origem: '', horario_funcionamento: '', filtros_chatwoot: '', usar_buffer: true, mensagem_quebrada: false, prompt: ''
  })
  const webhookUrl = form.slug ? `https://SEU_NGROK/webhook/${form.slug}` : ''

  const [empresas, setEmpresas] = useState([]);
  const [erros24h, setErros24h] = useState({});
  const [user, setUser] = useState(null);

  useEffect(() => {
    const userData = localStorage.getItem('user');
    if (userData) {
      setUser(JSON.parse(userData));
      loadData();
    } else {
      // Se não está logado, redirecionar para login
      navigate('/login');
    }
  }, [navigate]);

  const loadData = async () => {
    try {
      // Carregar métricas gerais
      const metricsData = await apiService.getAdminMetrics();
      setMetrics(metricsData);
      
      // Carregar empresas (já filtradas pelo backend conforme o usuário)
      const empresasData = await apiService.listEmpresas();
      setEmpresas(empresasData);
      
      // Carregar erros das últimas 24h
      const errosData = await apiService.getErros24h();
      setErros24h(errosData);
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
      setError('Erro ao carregar dados. Verifique se o backend está rodando.');
    } finally {
      setLoading(false);
    }
  };

  const getEmpresasFiltradas = () => {
    if (!empresas) return []
    return empresas.filter(e =>
      e.nome.toLowerCase().includes(search.toLowerCase())
    )
  }

  const empresasOrdenadas = [...empresas].sort((a, b) => (erros24h[b.slug] || 0) - (erros24h[a.slug] || 0))

  const handleChange = e => {
    const { name, value, type, checked } = e.target
    setForm(f => ({ ...f, [name]: type === 'checkbox' ? checked : value }))
  }
  const handleSubmit = async e => {
    e.preventDefault()
    // Enviar para backend
    await fetch('/api/admin/empresas', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form)
    })
    setShowModal(false)
  }

  if (loading) {
    return (
      <div className="dashboard">
        <div className="dashboard-header">
          <h1 className="dashboard-title">Carregando...</h1>
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
            onClick={loadData}
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
        <h1 className="dashboard-title">Dashboard Geral</h1>
        <p className="dashboard-subtitle">Visão macro do sistema Atende Ai</p>
      </div>

      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-title">Total de Empresas</div>
          <div className="metric-value">{metrics.total_empresas}</div>
        </div>
        <div className="metric-card">
          <div className="metric-title">Clientes Atendidos</div>
          <div className="metric-value">{metrics.total_clientes}</div>
        </div>
        <div className="metric-card">
          <div className="metric-title">Reservas Realizadas</div>
          <div className="metric-value">{metrics.total_reservas}</div>
        </div>
        <div className="metric-card">
          <div className="metric-title">Total de Atendimentos</div>
          <div className="metric-value">{metrics.total_atendimentos}</div>
        </div>
      </div>

      <div className="table-container">
        <div className="table-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h3>Empresas</h3>
          <input
            type="text"
            placeholder="Buscar empresa..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ padding: 6, borderRadius: 4, border: '1px solid #ccc', minWidth: 200 }}
          />
        </div>
        <table className="table">
          <thead>
            <tr>
              <th>Empresa</th>
              <th>Status</th>
              <th>Slug</th>
              <th>Atendimentos</th>
              <th>Erros (24h)</th>
            </tr>
          </thead>
          <tbody>
            {empresasOrdenadas.map(empresa => (
              <tr
                key={empresa.slug}
                style={{ cursor: 'pointer' }}
                onClick={() => navigate(`/admin/${empresa.slug}`)}
                title="Ver painel da empresa"
              >
                <td>{empresa.nome}</td>
                <td>
                  <span style={{ color: empresa.status === 'ativo' ? 'green' : 'red', fontWeight: 'bold' }}>
                    {empresa.status === 'ativo' ? '✅' : '❌'} {empresa.status}
                  </span>
                </td>
                <td>{empresa.slug}</td>
                <td>{empresa.atendimentos}</td>
                <td>{erros24h[empresa.slug] || 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {showModal && (
        <div className="modal">
          <form onSubmit={handleSubmit} className="empresa-form">
            <h2>Cadastrar Nova Empresa</h2>
            <input name="slug" placeholder="Slug (ex: tinyteams)" value={form.slug} onChange={handleChange} required />
            <input name="nome" placeholder="Nome" value={form.nome} onChange={handleChange} required />
            <input name="whatsapp_number" placeholder="WhatsApp Number" value={form.whatsapp_number} onChange={handleChange} />
            <input name="google_sheets_id" placeholder="Google Sheets ID" value={form.google_sheets_id} onChange={handleChange} />
            <input name="chatwoot_token" placeholder="Chatwoot Token" value={form.chatwoot_token} onChange={handleChange} />
            <input name="openai_key" placeholder="OpenAI Key" value={form.openai_key} onChange={handleChange} />
            <input name="twilio_sid" placeholder="Twilio SID" value={form.twilio_sid} onChange={handleChange} />
            <input name="twilio_token" placeholder="Twilio Token" value={form.twilio_token} onChange={handleChange} />
            <input name="twilio_number" placeholder="Twilio Number" value={form.twilio_number} onChange={handleChange} />
            <input name="chatwoot_inbox_id" placeholder="Chatwoot Inbox ID" value={form.chatwoot_inbox_id} onChange={handleChange} />
            <input name="chatwoot_origem" placeholder="Chatwoot Origem" value={form.chatwoot_origem} onChange={handleChange} />
            <input name="horario_funcionamento" placeholder="Horário de Funcionamento" value={form.horario_funcionamento} onChange={handleChange} />
            <input name="filtros_chatwoot" placeholder="Filtros Chatwoot (JSON)" value={form.filtros_chatwoot} onChange={handleChange} />
            <label><input type="checkbox" name="usar_buffer" checked={form.usar_buffer} onChange={handleChange} /> Usar Buffer</label>
            <label><input type="checkbox" name="mensagem_quebrada" checked={form.mensagem_quebrada} onChange={handleChange} /> Mensagem Quebrada</label>
            <textarea name="prompt" placeholder="Prompt da Empresa" value={form.prompt} onChange={handleChange} />
            <div style={{margin:'10px 0',fontSize:'0.9em',color:'#555'}}>Webhook para Twilio: <b>{webhookUrl}</b></div>
            <button type="submit">Salvar</button>
            <button type="button" onClick={() => setShowModal(false)}>Cancelar</button>
          </form>
        </div>
      )}
    </div>
  )
}

export default AdminDashboard