import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../services/api'
import './ConfiguracoesEmpresa.css'
import LoadingSpinner from './LoadingSpinner'

const defaultCfg = () => ({
  enabled: false,
  provider: 'Trinks',
  timezone: 'America/Sao_Paulo',
  send_time_local: '11:00',
  lead_days: 1,
  twilio_template_sid: '',
  twilio_variable_order: ['name','time','professional'],
  dedupe_strategy: 'first_slot_per_day'
})

const Reminders = () => {
  const { empresa } = useParams()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [empresas, setEmpresas] = useState([])
  const [selectedEmpresa, setSelectedEmpresa] = useState(empresa || '')
  const [reminders, setReminders] = useState([])
  const [activeId, setActiveId] = useState(null)
  const [formCfg, setFormCfg] = useState(defaultCfg())
  const [preview, setPreview] = useState([])
  const [previewLoading, setPreviewLoading] = useState(false)
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')


  useEffect(() => {
    const loadEmp = async () => {
      try {
        const res = await api.listEmpresas()
        const list = res.empresas || []
        setEmpresas(list)
        if (!selectedEmpresa && list.length > 0) {
          const first = list[0].slug
          setSelectedEmpresa(first)
          navigate(`/admin/empresa/${first}/lembretes`, { replace: true })
        }
      } catch (e) {
        setErr('Erro ao carregar empresas: ' + e.message)
      }
    }
    loadEmp()
  }, [])

  useEffect(() => {
    const load = async () => {
      if (!selectedEmpresa) return
      try {
        setLoading(true)
        const res = await api.listEmpresaReminders(selectedEmpresa)
        setReminders(res.items || [])
        setActiveId(null)
        setFormCfg(defaultCfg())
      } catch (e) {
        setErr(e.message)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [selectedEmpresa])

  // Loading de página padronizado (mesmo padrão das demais telas)
  if (loading && selectedEmpresa) {
    return <LoadingSpinner type="page" />
  }

  const openNew = () => {
    if (activeId === 'new') {
      cancelEdit()
    } else {
      setActiveId('new')
      setFormCfg(defaultCfg())
    }
  }

  const openEdit = (rem) => {
    if (activeId === rem.id) {
      cancelEdit()
    } else {
      setActiveId(rem.id)
      setFormCfg({ ...defaultCfg(), ...rem })
    }
  }

  const cancelEdit = () => {
    setActiveId(null)
    setFormCfg(defaultCfg())
  }

  const saveReminder = async () => {
    try {
      setSaving(true)
      setMsg('')
      setErr('')
      if (activeId === 'new') {
        await api.createEmpresaReminder(selectedEmpresa, formCfg)
      } else if (activeId) {
        await api.updateEmpresaReminder(selectedEmpresa, activeId, formCfg)
      }
      const res = await api.listEmpresaReminders(selectedEmpresa)
      setReminders(res.items || [])
      setActiveId(null)
      setFormCfg(defaultCfg())
      setMsg('Salvo com sucesso')
      setTimeout(() => setMsg(''), 2000)
    } catch (e) {
      setErr(e.message)
    } finally {
      setSaving(false)
    }
  }

  const deleteReminder = async (remId) => {
    try {
      setErr('')
      await api.deleteEmpresaReminder(selectedEmpresa, remId)
      const res = await api.listEmpresaReminders(selectedEmpresa)
      setReminders(res.items || [])
      if (activeId === remId) cancelEdit()
    } catch (e) {
      setErr(e.message)
    }
  }

  const doPreview = async (remId) => {
    try {
      setMsg('')
      setErr('')
      setPreviewLoading(true)
      const res = await api.previewEmpresaReminders(selectedEmpresa, remId || (activeId === 'new' ? null : activeId))
      setPreview(res.items || [])
    } catch (e) {
      setErr(e.message)
    } finally {
      setPreviewLoading(false)
    }
  }

  const runNow = async (remId) => {
    try {
      setMsg('')
      setErr('')
      const res = await api.runNowEmpresaReminders(selectedEmpresa, remId || (activeId === 'new' ? null : activeId))
      if (res.success) setMsg('Execução disparada')
      else setErr(res.message || 'Falha ao executar')
    } catch (e) {
      setErr(e.message)
    }
  }

  return (
    <div className="configuracoes-container">
      <div className="configuracoes-header">
        <h1>Lembretes</h1>
      </div>

      {/* Filtro de Empresa */}
      <div className="empresa-filter">
        <label>Selecionar Empresa:</label>
        <div className="empresa-select-container">
          <select
            value={selectedEmpresa}
            onChange={(e) => {
              const slug = e.target.value
              setSelectedEmpresa(slug)
              if (slug) navigate(`/admin/empresa/${slug}/lembretes`, { replace: true })
            }}
            className="empresa-select"
          >
            <option value="">Selecione uma empresa</option>
            {empresas.map(emp => (
              <option key={emp.slug} value={emp.slug}>{emp.nome}</option>
            ))}
          </select>
          <div className="select-arrow">▼</div>
        </div>
      </div>

      <div className="configuracoes-content">
          <div className="sections-nav">
            <button className={`section-nav-btn active`}>
              <span className="section-icon">⏰</span>
              <span className="section-title">Lembretes</span>
            </button>
          </div>

          <div className="configuracoes-form">
            {msg && <div className="success-msg">✅ {msg}</div>}
            {err && <div className="error-msg">❌ {err}</div>}

            <div className="table-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <h2>⏰ Lembretes</h2>
              <button type="button" className="btn btn-primary" onClick={openNew}>Novo Lembrete</button>
            </div>

            <div style={{ overflowX: 'auto' }}>
            <table className="table" style={{ minWidth: 720 }}>
              <thead>
                <tr>
                  <th>Ativo</th>
                  <th>Horário</th>
                  <th>Dias</th>
                  <th>Timezone</th>
                  <th>Template</th>
                  <th style={{ textAlign: 'right' }}>Ações</th>
                </tr>
              </thead>
              <tbody>
                {reminders.map(rem => (
                  <>
                    <tr key={`row-${rem.id}`}>
                      <td>{rem.enabled ? '✅' : '❌'}</td>
                      <td>{rem.send_time_local}</td>
                      <td>{rem.lead_days}</td>
                      <td>{rem.timezone}</td>
                      <td style={{ maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{rem.twilio_template_sid || '-'}</td>
                      <td style={{ textAlign: 'right', display: 'flex', gap: 8, justifyContent: 'flex-end', flexWrap: 'wrap' }}>
                        <button className="btn btn-small" style={{ padding: '6px 10px', fontSize: 12, minWidth: 120 }} onClick={() => doPreview(rem.id)}>Preview</button>
                        <button className="btn btn-small" style={{ padding: '6px 10px', fontSize: 12, minWidth: 120 }} onClick={() => runNow(rem.id)}>Executar</button>
                        <button className="btn btn-small" style={{ padding: '6px 10px', fontSize: 12, minWidth: 120 }} onClick={() => openEdit(rem)}>{activeId === rem.id ? 'Recolher' : 'Editar'}</button>
                        <button className="btn btn-small" style={{ padding: '6px 10px', fontSize: 12, minWidth: 120 }} onClick={() => deleteReminder(rem.id)}>Excluir</button>
                      </td>
                    </tr>
                    {activeId === rem.id && (
                      <tr key={`form-${rem.id}`}>
                        <td colSpan={6}>
                          <div className={`form-section active`}>
                            <div className="section-fields" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 12, alignItems: 'start' }}>
                              <ProviderAndVars empresa={selectedEmpresa} cfg={formCfg} setCfg={setFormCfg} />
                              <div className="field-group">
                                <label>Twilio Template SID</label>
                                <input className="form-input" type="text" value={formCfg.twilio_template_sid} onChange={e => setFormCfg(p => ({ ...p, twilio_template_sid: e.target.value }))} />
                              </div>
                              <div className="field-group">
                                <label>Timezone</label>
                                <input className="form-input" type="text" value={formCfg.timezone} onChange={e => setFormCfg(p => ({ ...p, timezone: e.target.value }))} />
                              </div>
                              <div className="field-group">
                                <label>Horário Local (HH:MM)</label>
                                <input className="form-input" type="text" value={formCfg.send_time_local} onChange={e => setFormCfg(p => ({ ...p, send_time_local: e.target.value }))} />
                              </div>
                              <div className="field-group">
                                <label>Dias de antecedência</label>
                                <input className="form-input" type="number" min="0" value={formCfg.lead_days} onChange={e => setFormCfg(p => ({ ...p, lead_days: parseInt(e.target.value || '1') }))} />
                              </div>
                              <div style={{ gridColumn: '1 / -1', display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 12, marginTop: 8 }}>
                                <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                                  <input type="checkbox" checked={!!formCfg.enabled} onChange={e => setFormCfg(p => ({ ...p, enabled: e.target.checked }))} /> Ativar
                                </label>
                                <button className="btn btn-primary" style={{ padding: '0.5rem 1rem' }} onClick={saveReminder} disabled={saving}>{saving ? 'Salvando...' : 'Salvar'}</button>
                              </div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}

                {activeId === 'new' && (
                  <tr key="form-new">
                    <td colSpan={6}>
                      <div className={`form-section active`}>
                        <div className="section-fields" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 12, alignItems: 'start' }}>
                          <ProviderAndVars empresa={selectedEmpresa} cfg={formCfg} setCfg={setFormCfg} />
                          <div className="field-group">
                            <label>Twilio Template SID</label>
                            <input className="form-input" type="text" value={formCfg.twilio_template_sid} onChange={e => setFormCfg(p => ({ ...p, twilio_template_sid: e.target.value }))} />
                          </div>
                          <div className="field-group">
                            <label>Timezone</label>
                            <input className="form-input" type="text" value={formCfg.timezone} onChange={e => setFormCfg(p => ({ ...p, timezone: e.target.value }))} />
                          </div>
                          <div className="field-group">
                            <label>Horário Local (HH:MM)</label>
                            <input className="form-input" type="text" value={formCfg.send_time_local} onChange={e => setFormCfg(p => ({ ...p, send_time_local: e.target.value }))} />
                          </div>
                          <div className="field-group">
                            <label>Dias de antecedência</label>
                            <input className="form-input" type="number" min="0" value={formCfg.lead_days} onChange={e => setFormCfg(p => ({ ...p, lead_days: parseInt(e.target.value || '1') }))} />
                          </div>
                          <div style={{ gridColumn: '1 / -1', display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 12, marginTop: 8 }}>
                            <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                              <input type="checkbox" checked={!!formCfg.enabled} onChange={e => setFormCfg(p => ({ ...p, enabled: e.target.checked }))} /> Ativar
                            </label>
                            <button className="btn btn-primary" style={{ padding: '0.5rem 1rem' }} onClick={saveReminder} disabled={saving}>{saving ? 'Salvando...' : 'Salvar'}</button>
                          </div>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
            </div>
          </div>

          <div style={{ marginTop: '1.5rem' }}>
            <h3>Pré-visualização</h3>
            <div style={{ position: 'relative', minHeight: previewLoading ? 160 : 'auto' }}>
              {previewLoading && (
                <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1, pointerEvents: 'none' }}>
                  <LoadingSpinner type="inline" />
                </div>
              )}
              {!previewLoading && preview.length === 0 && <div style={{ color: '#666' }}>Sem itens</div>}
              {!previewLoading && preview.length > 0 && (
                <table className="table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr>
                      <th style={{ textAlign: 'left' }}>Telefone</th>
                      <th style={{ textAlign: 'left' }}>Cliente</th>
                      <th style={{ textAlign: 'left' }}>Horário</th>
                      <th style={{ textAlign: 'left' }}>Profissional</th>
                      <th style={{ textAlign: 'left' }}>Mensagem</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.map((it, idx) => (
                      <tr key={idx}>
                        <td>{it.phone || '-'}</td>
                        <td>{it.name}</td>
                        <td>{it.time}</td>
                        <td>{it.professional}</td>
                        <td style={{ whiteSpace: 'pre-wrap' }}>{it.message_preview || <code>{JSON.stringify(it.variables)}</code>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
      </div>
    </div>
  )
}

export default Reminders

const ProviderAndVars = ({ empresa, cfg, setCfg }) => {
  const [providers, setProviders] = useState(['Trinks'])
  const [placeholders, setPlaceholders] = useState(['name','time','professional'])

  useEffect(() => {
    const loadOptions = async () => {
      try {
        const res = await api.getEmpresaReminderOptions(empresa)
        setProviders(res.providers || ['Trinks'])
        setPlaceholders(res.placeholders || ['name','time','professional'])
      } catch {}
    }
    if (empresa) loadOptions()
  }, [empresa])

  return (
    <>
      <div className="field-group">
        <label>Provider</label>
        <select className="empresa-select" value={cfg.provider} onChange={e => setCfg(p => ({ ...p, provider: e.target.value }))}>
          {providers.map(p => <option key={p} value={p}>{p}</option>)}
        </select>
      </div>
      <div className="field-group">
        <label>Ordem das variáveis</label>
        <div style={{ display: 'flex', gap: 8 }}>
          {[0,1,2].map(i => (
            <select key={i} className="empresa-select" value={(cfg.twilio_variable_order || [])[i] || ''} onChange={e => {
              const arr = [...(cfg.twilio_variable_order || [])]
              arr[i] = e.target.value
              setCfg(p => ({ ...p, twilio_variable_order: arr.filter(Boolean) }))
            }}>
              <option value="">(vazio)</option>
              {placeholders.map(ph => <option key={ph} value={ph}>{ph}</option>)}
            </select>
          ))}
        </div>
      </div>
    </>
  )
}


