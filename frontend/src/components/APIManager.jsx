import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import LoadingSpinner from './LoadingSpinner';

const APIManager = () => {
  const [apis, setApis] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [newApi, setNewApi] = useState({
    nome: '',
    descricao: '',
    url_documentacao: '',
    url_base: '',
    logo_url: ''
  });
  const [showForm, setShowForm] = useState(false);
  const [editingApi, setEditingApi] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [user, setUser] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    console.log('APIManager carregando...');
    const userData = localStorage.getItem('user');
    const token = localStorage.getItem('token');
    
    if (userData && token) {
      setUser(JSON.parse(userData));
      loadAPIs();
    } else {
      navigate('/login');
    }
  }, [navigate]);

  const loadAPIs = async () => {
    try {
      setLoading(true);
      console.log('Carregando APIs...');
      const response = await api.getAPIs();
      console.log('Resposta da API:', response);
      setApis(response.apis || []);
    } catch (err) {
      console.error('Erro ao carregar APIs:', err);
      setError('Erro ao carregar APIs: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setError('');
      if (isEditing) {
        console.log('Atualizando API:', editingApi);
        const response = await api.updateAPI(editingApi.id, editingApi);
        console.log('API atualizada:', response);
        setEditingApi(null);
        setIsEditing(false);
        setHasChanges(false);
      } else {
        console.log('Criando API:', newApi);
        const response = await api.createAPI(newApi);
        console.log('API criada:', response);
        setNewApi({ nome: '', descricao: '', url_documentacao: '', url_base: '', logo_url: '' });
      }
      setShowForm(false);
      loadAPIs();
    } catch (err) {
      console.error('Erro ao salvar API:', err);
      setError('Erro ao salvar API: ' + err.message);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    if (isEditing) {
      setEditingApi(prev => ({
        ...prev,
        [name]: value
      }));
      setHasChanges(true);
    } else {
      setNewApi(prev => ({
        ...prev,
        [name]: value
      }));
    }
  };

  const handleLogoChange = (e) => {
    const { value } = e.target;
    if (isEditing) {
      setEditingApi(prev => ({
        ...prev,
        logo_url: value
      }));
      setHasChanges(true);
    } else {
      setNewApi(prev => ({
        ...prev,
        logo_url: value
      }));
    }
  };

  const handleEditAPI = (api) => {
    setEditingApi({ ...api });
    setIsEditing(true);
    setHasChanges(false);
    setShowForm(true);
  };

  const handleCancelEdit = () => {
    setEditingApi(null);
    setIsEditing(false);
    setHasChanges(false);
    setShowForm(false);
  };

  // Função para lidar com quebras de linha nos campos textarea
  const handleTextareaKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      const cursorPosition = e.target.selectionStart
      const value = e.target.value
      const newValue = value.slice(0, cursorPosition) + '\n' + value.slice(cursorPosition)
      
      // Atualizar o valor do campo
      const { name } = e.target
      if (name) {
        if (isEditing) {
          setEditingApi(prev => ({ ...prev, [name]: newValue }))
        } else {
          setNewApi(prev => ({ ...prev, [name]: newValue }))
        }
      }
      
      // Manter o cursor na posição correta após a quebra de linha
      setTimeout(() => {
        const newCursorPosition = cursorPosition + 1
        e.target.setSelectionRange(newCursorPosition, newCursorPosition)
      }, 0)
    }
  }

  if (loading) {
    return <LoadingSpinner type="page" />;
  }

  if (error) {
    return (
      <div className="dashboard">
        <div className="dashboard-header">
          <h1 className="dashboard-title">Erro</h1>
          <p className="dashboard-subtitle" style={{ color: 'red' }}>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1 className="dashboard-title">Gerenciamento de APIs</h1>
        <p className="dashboard-subtitle">Cadastre e gerencie APIs externas para integração com os agentes</p>
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {showForm && (
        <div className="modal">
          <form onSubmit={handleSubmit} className="empresa-form">
            <h2>{isEditing ? 'Editar API' : 'Adicionar Nova API'}</h2>
            
            <div className="form-group">
              <label>Nome da API *</label>
              <input
                type="text"
                name="nome"
                value={isEditing ? editingApi.nome : newApi.nome}
                onChange={handleInputChange}
                required
                placeholder="Ex: Trinks API"
              />
            </div>

            <div className="form-group">
              <label>Descrição</label>
              <textarea
                name="descricao"
                value={isEditing ? editingApi.descricao : newApi.descricao}
                onChange={handleInputChange}
                onKeyDown={handleTextareaKeyDown}
                rows="3"
                placeholder="Descrição da funcionalidade da API"
              />
            </div>

            <div className="form-group">
              <label>URL da Documentação *</label>
              <input
                type="url"
                name="url_documentacao"
                value={isEditing ? editingApi.url_documentacao : newApi.url_documentacao}
                onChange={handleInputChange}
                required
                placeholder="https://api.exemplo.com/docs"
              />
            </div>

            <div className="form-group">
              <label>URL Base da API</label>
              <input
                type="url"
                name="url_base"
                value={isEditing ? editingApi.url_base : newApi.url_base}
                onChange={handleInputChange}
                placeholder="https://api.exemplo.com/v1"
              />
            </div>

            <div className="form-group">
              <label>URL da Logo da API</label>
              <input
                type="url"
                name="logo_url"
                value={isEditing ? editingApi.logo_url : newApi.logo_url}
                onChange={handleLogoChange}
                placeholder="https://exemplo.com/logo.png"
              />
              <small style={{ color: '#666', fontSize: '12px' }}>
                URL da imagem que será exibida na listagem de APIs
              </small>
            </div>

            <div className="form-actions">
              <button 
                type="submit" 
                className="btn btn-primary"
                disabled={isEditing && !hasChanges}
              >
                {isEditing ? 'Salvar Alterações' : 'Criar API'}
              </button>
              <button 
                type="button" 
                onClick={isEditing ? handleCancelEdit : () => setShowForm(false)}
                className="btn btn-secondary"
              >
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="table-container">
        <div className="table-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h3>APIs Cadastradas ({apis.length})</h3>
          <button
            onClick={() => setShowForm(!showForm)}
            className="btn btn-primary"
            style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Nova API
          </button>
        </div>
        
        {apis.length === 0 ? (
          <div className="empty-state">
            <svg width="48" height="48" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p>Nenhuma API cadastrada ainda.</p>
            <p>Clique em "Nova API" para começar.</p>
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Nome</th>
                <th>Descrição</th>
                <th>Status</th>
                <th>Endpoints</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {apis.map((api) => (
                <tr key={api.id}>
                  <td>
                    <div>
                      <strong>{api.nome}</strong>
                      {api.url_documentacao && (
                        <div style={{ marginTop: '4px' }}>
                          <a 
                            href={api.url_documentacao} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            style={{ color: '#0066cc', fontSize: '12px' }}
                          >
                            📄 Documentação
                          </a>
                        </div>
                      )}
                    </div>
                  </td>
                  <td>{api.descricao || '-'}</td>
                  <td>
                    <span style={{ 
                      color: api.ativo ? 'green' : 'red', 
                      fontWeight: 'bold' 
                    }}>
                      {api.ativo ? '✅ Ativa' : '❌ Inativa'}
                    </span>
                  </td>
                  <td>
                    {api.tools_count > 0 ? (
                      <span style={{ fontSize: '12px' }}>
                        {api.tools_count} endpoints
                      </span>
                    ) : (
                      <span style={{ fontSize: '12px', color: '#666' }}>
                        Não processada
                      </span>
                    )}
                  </td>
                  <td>
                    <button 
                      className="btn btn-small"
                      onClick={() => handleEditAPI(api)}
                    >
                      Ver Detalhes
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default APIManager; 