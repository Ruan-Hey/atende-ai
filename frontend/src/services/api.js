const API_BASE_URL = 'http://localhost:8001'

class ApiService {
  constructor() {
    // Em desenvolvimento usa localhost, em produção usa a URL do Render
    this.baseURL = process.env.NODE_ENV === 'production' 
      ? (process.env.REACT_APP_API_URL || 'https://atende-ai-backend.onrender.com')
      : 'http://localhost:8001';
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

  // Status do buffer de mensagens
  async getBufferStatus() {
    return this.authenticatedRequest('/api/admin/buffer/status')
  }

  // Forçar processamento do buffer
  async forceProcessBuffer(cliente_id, empresa) {
    const params = new URLSearchParams({
      cliente_id,
      empresa
    })
    return this.authenticatedRequest(`/api/admin/buffer/force-process?${params.toString()}`, {
      method: 'POST'
    })
  }

  // Logs do sistema
  async getLogs(empresa = null, limit = 100) {
    const params = new URLSearchParams()
    if (empresa) params.append('empresa', empresa)
    if (limit) params.append('limit', limit)
    
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