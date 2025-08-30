import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import apiService from '../services/api'
import LoadingSpinner from './LoadingSpinner'

const LogsViewer = () => {
  const { empresa } = useParams()
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedEmpresa, setSelectedEmpresa] = useState('')
  const [empresas, setEmpresas] = useState([])
  const [filterLevel, setFilterLevel] = useState('all')
  const [notificationsEnabled, setNotificationsEnabled] = useState(false)
  const [notificationLoading, setNotificationLoading] = useState(false)
  const [pushSubscription, setPushSubscription] = useState(null)


  // ============================================================================
  // SISTEMA DE PUSH NOTIFICATIONS
  // ============================================================================

  // Registrar Service Worker
  const registerServiceWorker = async () => {
    try {
      if ('serviceWorker' in navigator && 'PushManager' in window) {
        const registration = await navigator.serviceWorker.register('/sw.js')
        console.log('✅ Service Worker registrado:', registration)
        return registration
      } else {
        console.warn('⚠️ Service Worker ou Push Manager não suportado')
        return null
      }
    } catch (error) {
      console.error('❌ Erro ao registrar Service Worker:', error)
      return null
    }
  }



  // Solicitar permissão de notificações
  const requestNotificationPermission = async () => {
    try {
      if ('Notification' in window) {
        const permission = await Notification.requestPermission()
        return permission === 'granted'
      }
      return false
    } catch (error) {
      console.error('❌ Erro ao solicitar permissão:', error)
      return false
    }
  }

  // Criar subscription para push
  const createPushSubscription = async (registration) => {
    try {
      const response = await apiService.getVapidPublicKey()
      const vapidKey = response.public_key
      
      if (!vapidKey) return null

      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: vapidKey
      })

      console.log('✅ Push subscription criada:', subscription)
      return subscription
    } catch (error) {
      console.error('❌ Erro ao criar subscription:', error)
      return null
    }
  }

  // Ativar notificações push
  const enablePushNotifications = async () => {
    try {
      setNotificationLoading(true)

      // Registrar Service Worker
      const registration = await registerServiceWorker()
      if (!registration) {
        alert('Service Worker não pôde ser registrado')
        return
      }

      // Solicitar permissão
      const permissionGranted = await requestNotificationPermission()
      if (!permissionGranted) {
        alert('Permissão de notificações negada')
        return
      }

      // Criar subscription
      const subscription = await createPushSubscription(registration)
      if (!subscription) {
        alert('Erro ao criar subscription para notificações')
        return
      }

      // Salvar no backend
      await apiService.subscribeToNotifications(subscription)
      
      // Atualizar estado
      console.log('🔄 Atualizando estado...')
      setPushSubscription(subscription)
      setNotificationsEnabled(true)
      localStorage.setItem('push_notifications_enabled', 'true')
      
      console.log('✅ Estado atualizado - notificationsEnabled:', true)
      console.log('✅ Estado atualizado - pushSubscription:', subscription)
      
      alert('✅ Notificações push ativadas com sucesso!')
      
    } catch (error) {
      console.error('❌ Erro ao ativar notificações:', error)
      alert('Erro ao ativar notificações push')
    } finally {
      setNotificationLoading(false)
    }
  }

  // Desativar notificações push
  const disablePushNotifications = async () => {
    try {
      setNotificationLoading(true)

      if (pushSubscription) {
        // Remover subscription
        await pushSubscription.unsubscribe()
        await apiService.unsubscribeFromNotifications()
      }

      // Atualizar estado
      setPushSubscription(null)
      setNotificationsEnabled(false)
      localStorage.setItem('push_notifications_enabled', 'false')
      
      alert('✅ Notificações push desativadas!')
      
    } catch (error) {
      console.error('❌ Erro ao desativar notificações:', error)
      alert('Erro ao desativar notificações push')
    } finally {
      setNotificationLoading(false)
    }
  }

  // Testar notificação
  const testPushNotification = async () => {
    try {
      console.log('🧪 Iniciando teste de notificação...')
      console.log('🔍 Estado notificationsEnabled:', notificationsEnabled)
      
      if (!notificationsEnabled) {
        console.error('❌ Notificações não estão ativadas')
        alert('Ative as notificações primeiro!')
        return
      }

      console.log('📡 Chamando API de teste...')
      const response = await apiService.testNotification()
      console.log('📡 Resposta da API:', response)
      
      if (response.status === 'success') {
        console.log('✅ Teste bem-sucedido!')
        alert('✅ Notificação de teste enviada! Verifique se apareceu no navegador.')
      } else {
        console.error('❌ Falha no teste:', response)
        alert('❌ Falha ao enviar notificação de teste')
      }
    } catch (error) {
      console.error('❌ Erro ao testar notificação:', error)
      console.error('Stack trace:', error.stack)
      alert('Erro ao testar notificação')
    }
  }

  // Verificar estado inicial das notificações
  useEffect(() => {
    const checkNotificationStatus = async () => {
      try {
        // Verificar se já tem subscription salva
        const saved = localStorage.getItem('push_notifications_enabled')
        console.log('🔍 Estado salvo no localStorage:', saved)
        
        if (saved === 'true') {
          setNotificationsEnabled(true)
          console.log('✅ Estado restaurado do localStorage')
          
          // Verificar se Service Worker está ativo
          if ('serviceWorker' in navigator) {
            const registration = await navigator.serviceWorker.getRegistration()
            if (registration && registration.active) {
              console.log('✅ Service Worker já está ativo')
            }
          }
        }
      } catch (error) {
        console.error('❌ Erro ao verificar status das notificações:', error)
      }
    }

    checkNotificationStatus()
  }, [])

  // Log sempre que o estado mudar
  useEffect(() => {
    console.log('🔄 Estado notificationsEnabled mudou para:', notificationsEnabled)
  }, [notificationsEnabled])

  // Carregar dados iniciais
  useEffect(() => {
    // Se não for admin, usar empresa da URL
    if (empresa && !localStorage.getItem('user')?.includes('"is_superuser":true')) {
      setSelectedEmpresa(empresa)
    }
    
    // Carregar empresas apenas uma vez (não a cada mudança)
    loadEmpresas()
    
    // Carregar logs iniciais
    loadLogs()
    
    // Atualizar logs a cada 30 segundos (reduzido de 10 para 30)
    const interval = setInterval(loadLogs, 30000)
    return () => clearInterval(interval)
  }, [empresa]) // Removido selectedEmpresa e filterLevel das dependências

  // useEffect separado para quando mudar filtros
  useEffect(() => {
    if (selectedEmpresa || filterLevel !== 'all') {
      loadLogs()
    }
  }, [selectedEmpresa, filterLevel])





  const loadEmpresas = async () => {
    try {
      const response = await apiService.listEmpresas()
      // Garantir que sempre temos um array
      const empresasArray = Array.isArray(response?.empresas) ? response.empresas : []
      setEmpresas(empresasArray)
    } catch (error) {
      console.error('Erro ao carregar empresas:', error)
      setEmpresas([]) // Garantir array vazio em caso de erro
    }
  }

  const loadLogs = async () => {
    try {
      setLoading(true)
      // Por padrão, excluir logs de INFO para não poluir
      const excludeInfo = filterLevel === 'all' || filterLevel === 'error' || filterLevel === 'warning'
      const response = await apiService.getLogs(selectedEmpresa || null, 100, filterLevel, excludeInfo)
      // Garantir que sempre temos um array
      const logsArray = Array.isArray(response?.logs) ? response.logs : []
      setLogs(logsArray)
      setError(null)
    } catch (error) {
      console.error('Erro ao carregar logs:', error)
      setError('Erro ao carregar logs')
      setLogs([]) // Garantir array vazio em caso de erro
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
            disabled={empresa && !localStorage.getItem('user')?.includes('"is_superuser":true')}
          >
            <option value="">Todas as empresas</option>
            {Array.isArray(empresas) && empresas.map(emp => (
              <option key={emp.slug} value={emp.slug}>
                {emp.nome}
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
            <option value="all">Erros e Avisos</option>
            <option value="error">Apenas Erros</option>
            <option value="warning">Apenas Avisos</option>
            <option value="info">Todas as Informações</option>
          </select>
        </div>

        {/* ============================================================================ */}
        {/* SISTEMA DE PUSH NOTIFICATIONS */}
        {/* ============================================================================ */}
        
        <div className="filter-group">
          <label>🔔 Notificações Push:</label>
          <div className="btn-group" role="group">
            {!notificationsEnabled ? (
              <button
                className="btn btn-secondary"
                onClick={enablePushNotifications}
                disabled={notificationLoading}
                title="Ativar notificações push no navegador"
                style={{ minWidth: '120px' }}
              >
                {notificationsEnabled ? 'Desativar' : 'Ativar'}
                {notificationLoading && <span className="spinner-border spinner-border-sm ms-2"></span>}
              </button>
            ) : (
              <>
                <button
                  className="btn btn-warning"
                  onClick={testPushNotification}
                  title="Testar notificação push"
                >
                  🧪 Testar
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={disablePushNotifications}
                  disabled={notificationLoading}
                  title="Desativar notificações push"
                  style={{ minWidth: '120px' }}
                >
                  Desativar
                  {notificationLoading && <span className="spinner-border spinner-border-sm ms-2"></span>}
                </button>
              </>
            )}
          </div>
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
          <li><strong>INFO:</strong> Informações gerais sobre o funcionamento do sistema (ocultas por padrão)</li>
        </ul>
      </div>
    </div>
  )
}

export default LogsViewer 