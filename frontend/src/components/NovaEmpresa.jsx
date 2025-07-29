import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import './NovaEmpresa.css'

const SENSITIVE_FIELDS = [
  { name: 'openai_key', label: 'OpenAI Key' },
  { name: 'twilio_token', label: 'Twilio Token' },
  { name: 'chatwoot_token', label: 'Chatwoot Token' }
]

const NovaEmpresa = () => {
  const [form, setForm] = useState({
    slug: '', nome: '', whatsapp_number: '', google_sheets_id: '', chatwoot_token: '', openai_key: '', twilio_sid: '', twilio_token: '', twilio_number: '', chatwoot_inbox_id: '', chatwoot_origem: '', horario_funcionamento: '', filtros_chatwoot: '', usar_buffer: true, mensagem_quebrada: false, prompt: ''
  })
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')
  const [tokenHints, setTokenHints] = useState({})
  const [focusField, setFocusField] = useState('')
  const navigate = useNavigate()
  const webhookUrl = form.slug ? `https://SEU_NGROK/webhook/${form.slug}` : ''

  useEffect(() => {
    // Buscar empresas e tokens já cadastrados para sugestões camufladas
    fetch('/api/admin/empresas')
      .then(r => r.json())
      .then(data => {
        // Agrupar tokens por valor e empresas
        const hints = {}
        if (Array.isArray(data.empresas)) {
          SENSITIVE_FIELDS.forEach(field => {
            const map = {}
            data.empresas.forEach(e => {
              const val = e[field.name]
              if (val) {
                if (!map[val]) map[val] = []
                map[val].push(e.nome)
              }
            })
            hints[field.name] = Object.entries(map).map(([token, empresas]) => ({
              token: '•'.repeat(8), // camuflado
              empresas: empresas.join(', ')
            }))
          })
        }
        setTokenHints(hints)
      })
  }, [])

  const handleChange = e => {
    const { name, value, type, checked } = e.target
    setForm(f => ({ ...f, [name]: type === 'checkbox' ? checked : value }))
  }
  const handleSubmit = async e => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setSuccess(false)
    try {
      const resp = await fetch('/api/admin/empresas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form)
      })
      const data = await resp.json()
      if (data.success) {
        setSuccess(true)
        setTimeout(() => navigate('/admin'), 1200)
      } else {
        setError(data.error || 'Erro ao cadastrar empresa')
      }
    } catch (err) {
      setError('Erro de conexão')
    }
    setLoading(false)
  }

  return (
    <div className="admin-page">
      <h1 className="nova-empresa-title">Nova Empresa</h1>
      <form onSubmit={handleSubmit} className="empresa-form nova-empresa-form">
        <div className="form-grid">
          <div>
            <label>Slug*<input name="slug" placeholder="tinyteams" value={form.slug} onChange={handleChange} required /></label>
            <label>Nome*<input name="nome" placeholder="Nome da Empresa" value={form.nome} onChange={handleChange} required /></label>
            <label>WhatsApp Number<input name="whatsapp_number" value={form.whatsapp_number} onChange={handleChange} /></label>
            <label>Google Sheets ID<input name="google_sheets_id" value={form.google_sheets_id} onChange={handleChange} /></label>
            <label>Chatwoot Token
              <input name="chatwoot_token" value={form.chatwoot_token} onChange={handleChange} onFocus={() => setFocusField('chatwoot_token')} onBlur={() => setFocusField('')} />
              {focusField === 'chatwoot_token' && tokenHints.chatwoot_token && tokenHints.chatwoot_token.length > 0 && (
                <div className="token-hints">{tokenHints.chatwoot_token.map((h, i) => <div key={i}>{h.token} <span className="token-hint-empresas">({h.empresas})</span></div>)}</div>
              )}
            </label>
            <label>OpenAI Key
              <input name="openai_key" value={form.openai_key} onChange={handleChange} onFocus={() => setFocusField('openai_key')} onBlur={() => setFocusField('')} />
              {focusField === 'openai_key' && tokenHints.openai_key && tokenHints.openai_key.length > 0 && (
                <div className="token-hints">{tokenHints.openai_key.map((h, i) => <div key={i}>{h.token} <span className="token-hint-empresas">({h.empresas})</span></div>)}</div>
              )}
            </label>
            <label>Twilio SID<input name="twilio_sid" value={form.twilio_sid} onChange={handleChange} /></label>
            <label>Twilio Token
              <input name="twilio_token" value={form.twilio_token} onChange={handleChange} onFocus={() => setFocusField('twilio_token')} onBlur={() => setFocusField('')} />
              {focusField === 'twilio_token' && tokenHints.twilio_token && tokenHints.twilio_token.length > 0 && (
                <div className="token-hints">{tokenHints.twilio_token.map((h, i) => <div key={i}>{h.token} <span className="token-hint-empresas">({h.empresas})</span></div>)}</div>
              )}
            </label>
          </div>
          <div>
            <label>Twilio Number<input name="twilio_number" value={form.twilio_number} onChange={handleChange} /></label>
            <label>Chatwoot Inbox ID<input name="chatwoot_inbox_id" value={form.chatwoot_inbox_id} onChange={handleChange} /></label>
            <label>Chatwoot Origem<input name="chatwoot_origem" value={form.chatwoot_origem} onChange={handleChange} /></label>
            <label>Horário de Funcionamento<input name="horario_funcionamento" value={form.horario_funcionamento} onChange={handleChange} /></label>
            <label>Filtros Chatwoot (JSON)<input name="filtros_chatwoot" value={form.filtros_chatwoot} onChange={handleChange} /></label>
            <div className="checkbox-group">
              <label><input type="checkbox" name="usar_buffer" checked={form.usar_buffer} onChange={handleChange} /> Usar Buffer</label>
              <label><input type="checkbox" name="mensagem_quebrada" checked={form.mensagem_quebrada} onChange={handleChange} /> Mensagem Quebrada</label>
            </div>
            <label>Prompt<textarea name="prompt" value={form.prompt} onChange={handleChange} /></label>
          </div>
        </div>
        <div className="webhook-info">Webhook para Twilio: <b>{webhookUrl}</b></div>
        {success && <div className="success-msg">Empresa cadastrada com sucesso!</div>}
        {error && <div className="error-msg">{error}</div>}
        <div className="form-actions">
          <button type="submit" disabled={loading}>{loading ? 'Salvando...' : 'Salvar'}</button>
          <button type="button" onClick={() => navigate('/admin')}>Cancelar</button>
        </div>
      </form>
    </div>
  )
}

export default NovaEmpresa 