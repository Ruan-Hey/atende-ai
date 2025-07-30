import React, { useState, useEffect } from 'react';
import api from '../services/api';
import './Usuarios.css';

const Usuarios = () => {
  const [usuarios, setUsuarios] = useState([]);
  const [empresas, setEmpresas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    is_superuser: false,
    empresa_id: ''
  });

  useEffect(() => {
    loadUsuarios();
    loadEmpresas();
  }, []);

  const loadUsuarios = async () => {
    try {
      const data = await api.authenticatedRequest('/api/admin/usuarios');
      setUsuarios(data);
    } catch (error) {
      console.error('Erro ao carregar usuários:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadEmpresas = async () => {
    try {
      const data = await api.authenticatedRequest('/api/admin/empresas');
      setEmpresas(data);
    } catch (error) {
      console.error('Erro ao carregar empresas:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingUser) {
        await api.authenticatedRequest(`/api/admin/usuarios/${editingUser.id}`, {
          method: 'PUT',
          body: JSON.stringify(formData)
        });
      } else {
        await api.authenticatedRequest('/api/admin/usuarios', {
          method: 'POST',
          body: JSON.stringify(formData)
        });
      }
      setShowForm(false);
      setEditingUser(null);
      setFormData({ email: '', password: '', is_superuser: false, empresa_id: '' });
      loadUsuarios();
    } catch (error) {
      console.error('Erro ao salvar usuário:', error);
    }
  };

  const handleEdit = (user) => {
    setEditingUser(user);
    setFormData({
      email: user.email,
      password: '',
      is_superuser: user.is_superuser,
      empresa_id: user.empresa_id || ''
    });
    setShowForm(true);
  };

  const handleDelete = async (userId) => {
    if (window.confirm('Tem certeza que deseja excluir este usuário?')) {
      try {
        await api.authenticatedRequest(`/api/admin/usuarios/${userId}`, {
          method: 'DELETE'
        });
        loadUsuarios();
      } catch (error) {
        console.error('Erro ao excluir usuário:', error);
      }
    }
  };

  const getTipoAcesso = (user) => {
    if (user.is_superuser) return 'Administrador Geral';
    if (user.empresa_id) {
      const empresa = empresas.find(e => e.id === user.empresa_id);
      return `Administrador - ${empresa?.nome || 'Empresa'}`;
    }
    return 'Usuário';
  };

  if (loading) {
    return <div className="usuarios-loading">Carregando usuários...</div>;
  }

  return (
    <div className="usuarios-container">
      <div className="usuarios-header">
        <h1>Gerenciar Usuários</h1>
        <button 
          className="btn-add-user"
          onClick={() => {
            setShowForm(true);
            setEditingUser(null);
            setFormData({ email: '', password: '', is_superuser: false, empresa_id: '' });
          }}
        >
          + Adicionar Usuário
        </button>
      </div>

      {showForm && (
        <div className="form-overlay">
          <div className="form-container">
            <h2>{editingUser ? 'Editar Usuário' : 'Adicionar Usuário'}</h2>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Email:</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                  required
                />
              </div>
              
              <div className="form-group">
                <label>Senha:</label>
                <input
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({...formData, password: e.target.value})}
                  required={!editingUser}
                  placeholder={editingUser ? 'Deixe em branco para manter' : ''}
                />
              </div>
              
              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={formData.is_superuser}
                    onChange={(e) => setFormData({...formData, is_superuser: e.target.checked})}
                  />
                  Administrador Geral
                </label>
              </div>
              
              {!formData.is_superuser && (
                <div className="form-group">
                  <label>Empresa:</label>
                  <select
                    value={formData.empresa_id}
                    onChange={(e) => setFormData({...formData, empresa_id: e.target.value})}
                  >
                    <option value="">Selecione uma empresa</option>
                    {empresas.map(empresa => (
                      <option key={empresa.id} value={empresa.id}>
                        {empresa.nome}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              
              <div className="form-actions">
                <button type="submit" className="btn-save">
                  {editingUser ? 'Atualizar' : 'Adicionar'}
                </button>
                <button 
                  type="button" 
                  className="btn-cancel"
                  onClick={() => {
                    setShowForm(false);
                    setEditingUser(null);
                    setFormData({ email: '', password: '', is_superuser: false, empresa_id: '' });
                  }}
                >
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="usuarios-table">
        <table>
          <thead>
            <tr>
              <th>Email</th>
              <th>Tipo de Acesso</th>
              <th>Empresa</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {usuarios.map(user => (
              <tr key={user.id}>
                <td>{user.email}</td>
                <td>{getTipoAcesso(user)}</td>
                <td>
                  {user.empresa_id ? 
                    empresas.find(e => e.id === user.empresa_id)?.nome || 'N/A' : 
                    'Todas'
                  }
                </td>
                <td>
                  <button 
                    className="btn-edit"
                    onClick={() => handleEdit(user)}
                  >
                    Editar
                  </button>
                  <button 
                    className="btn-delete"
                    onClick={() => handleDelete(user.id)}
                  >
                    Excluir
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default Usuarios; 