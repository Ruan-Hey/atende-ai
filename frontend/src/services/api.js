const API_BASE_URL = 'http://localhost:8000'

class ApiService {
  constructor() {
    // Detecta se está em desenvolvimento local ou produção
    const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    
    this.baseURL = isLocalDev 
      ? 'http://localhost:8000'  // Desenvolvimento local
      : (import.meta.env.VITE_API_URL || 'https://api.tinyteams.app'); // Produção
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    }

    try {
      const response = await fetch(url, config)
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      return await response.json()
    } catch (error) {
      console.error('API request failed:', error)
      throw error
    }
  }

  // Métricas do admin
  async getAdminMetrics() {
    return this.authenticatedRequest('/api/admin/metrics')
  }

  // Métricas de uma empresa específica
  async getEmpresaMetrics(empresaSlug) {
    return this.authenticatedRequest(`/api/admin/empresa/${empresaSlug}`)
  }

  // Listar empresas
  async listEmpresas() {
    return this.authenticatedRequest('/api/admin/empresas')
  }

  // Criar nova empresa
  async createEmpresa(empresaData) {
    return this.authenticatedRequest('/api/admin/empresas', {
      method: 'POST',
      body: JSON.stringify(empresaData)
    })
  }

  // Logs do sistema
  async getLogs(empresa = null, limit = 100, level = null, excludeInfo = true) {
    const params = new URLSearchParams()
    if (empresa) params.append('empresa', empresa)
    if (limit) params.append('limit', limit)
    if (level) params.append('level', level)
    if (excludeInfo !== undefined) params.append('exclude_info', excludeInfo)
    
    return this.authenticatedRequest(`/api/logs?${params.toString()}`)
  }

  // Erros das últimas 24h
  async getErros24h() {
    return this.authenticatedRequest('/api/admin/erros-24h')
  }

  // Health check
  async healthCheck() {
    return this.request('/health')
  }

  // Buscar conversa de um cliente
  async getConversation(empresa, clienteId, { limit = 20, before = null } = {}) {
    const params = new URLSearchParams()
    if (limit) params.append('limit', limit)
    if (before) params.append('before', before)
    const query = params.toString() ? `?${params.toString()}` : ''
    return this.authenticatedRequest(`/api/conversation/${empresa}/${clienteId}${query}`)
  }

  // Buscar clientes de uma empresa
  async getEmpresaClientes(empresaSlug) {
    return this.authenticatedRequest(`/api/admin/empresa/${empresaSlug}/clientes`)
  }

  // Buscar lista de conversas de uma empresa
  async getConversations(empresaSlug) {
    return this.authenticatedRequest(`/api/admin/empresa/${empresaSlug}/clientes`)
  }

  // Buscar configurações de uma empresa
  async getEmpresaConfiguracoes(empresaSlug) {
    return this.authenticatedRequest(`/api/empresas/${empresaSlug}/configuracoes`)
  }

  // Atualizar configurações de uma empresa
  async updateEmpresaConfiguracoes(empresaSlug, configuracoes) {
    return this.authenticatedRequest(`/api/empresas/${empresaSlug}/configuracoes`, {
      method: 'PUT',
      body: JSON.stringify(configuracoes)
    })
  }

  // Upload de Service Account JSON para Google Calendar
  async uploadGoogleServiceAccount(empresaSlug, formData) {
    const url = `${this.baseURL}/api/empresas/${empresaSlug}/google-service-account`
    const token = localStorage.getItem('token')
    
    if (!token) {
      throw new Error('Usuário não autenticado')
    }
    
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          // Não incluir Content-Type para FormData
        },
        body: formData
      })
      
      if (response.status === 401) {
        this.logout()
        window.location.href = '/#/login'
        throw new Error('Sessão expirada')
      }
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Erro no upload')
      }
      
      return await response.json()
    } catch (error) {
      console.error('Upload failed:', error)
      throw error
    }
  }

  // Buscar URL de autorização OAuth2 do Google Calendar
  async getGoogleOAuthUrl(empresaSlug) {
    return this.authenticatedRequest(`/api/empresas/${empresaSlug}/google-oauth-url`)
  }

  // APIs - Listar todas as APIs
  async getAPIs() {
    return this.authenticatedRequest('/api/admin/apis')
  }

  // APIs - Criar nova API
  async createAPI(apiData) {
    return this.authenticatedRequest('/api/admin/apis', {
      method: 'POST',
      body: JSON.stringify(apiData)
    })
  }

  // APIs - Atualizar API
  async updateAPI(apiId, apiData) {
    return this.authenticatedRequest(`/api/admin/apis/${apiId}`, {
      method: 'PUT',
      body: JSON.stringify(apiData)
    })
  }

  // APIs - Conectar API a uma empresa
  async connectAPI(empresaId, apiId, config) {
    return this.authenticatedRequest(`/api/admin/empresas/${empresaId}/apis/${apiId}`, {
      method: 'POST',
      body: JSON.stringify(config)
    })
  }

  // APIs - Listar APIs conectadas a uma empresa
  async getEmpresaAPIs(empresaId) {
    return this.authenticatedRequest(`/api/admin/empresas/${empresaId}/apis`)
  }

  // Login do usuário
  async login(email, password) {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);
    const response = await fetch(`${this.baseURL}/api/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });
    if (!response.ok) {
      throw new Error('Credenciais inválidas');
    }
    return await response.json();
  }

  // Verificar se está logado
  isLoggedIn() {
    return !!localStorage.getItem('token');
  }

  // Logout
  logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  }

  // Obter headers com token
  getAuthHeaders() {
    const token = localStorage.getItem('token');
    return {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` })
    };
  }

  // Fazer requisição autenticada
  async authenticatedRequest(url, options = {}) {
    const headers = this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}${url}`, {
      ...options,
      headers: {
        ...headers,
        ...options.headers
      }
    });
    
    if (response.status === 401) {
      this.logout();
      window.location.href = '/#/login';
      throw new Error('Sessão expirada');
    }
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  }
}

export default new ApiService() 