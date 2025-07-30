import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import api from '../services/api';
import './Login.css';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await api.login(email, password);
      localStorage.setItem('token', res.access_token);
      localStorage.setItem('user', JSON.stringify(res.user));
      
      // Carregar empresas para redirecionamento correto
      try {
        const empresas = await api.listEmpresas();
        localStorage.setItem('empresas', JSON.stringify(empresas));
        
        // Se não for superuser, buscar o slug da empresa do usuário
        if (!res.user.is_superuser && res.user.empresa_id) {
          const userEmpresa = empresas.find(e => e.id === res.user.empresa_id);
          if (userEmpresa) {
            res.user.empresa_slug = userEmpresa.slug;
            localStorage.setItem('user', JSON.stringify(res.user));
          }
        }
      } catch (error) {
        console.error('Erro ao carregar empresas:', error);
      }
      
      // Redireciona para a página original ou admin
      const from = location.state?.from?.pathname || '/admin';
      navigate(from);
    } catch (err) {
      setError('Email ou senha inválidos');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-fullscreen">
      <form className="login-form" onSubmit={handleSubmit}>
        <div className="login-logo">
          <img 
            src="https://img.icons8.com/ios/160/000000/team.png" 
            alt="TinyTeams" 
            style={{ 
              width: 160, 
              height: 60,
              marginBottom: 12, 
              display: 'block', 
              marginLeft: 'auto', 
              marginRight: 'auto',
              borderRadius: '8px'
            }}
            onError={(e) => {
              // Se falhar, substituir por div com texto
              e.target.style.display = 'none';
              e.target.nextSibling.style.display = 'flex';
            }}
          />
          <div style={{ 
            width: 160, 
            height: 60, 
            marginBottom: 12, 
            display: 'none', 
            alignItems: 'center', 
            justifyContent: 'center',
            backgroundColor: '#fff',
            borderRadius: '8px',
            fontWeight: 'bold',
            fontSize: '18px',
            color: '#000',
            marginLeft: 'auto',
            marginRight: 'auto'
          }}>
            TinyTeams
          </div>
        </div>
        <h2>Login</h2>
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Senha"
          value={password}
          onChange={e => setPassword(e.target.value)}
          required
        />
        {error && <div className="login-error">{error}</div>}
        <button type="submit" disabled={loading}>{loading ? 'Entrando...' : 'Entrar'}</button>
      </form>
    </div>
  );
};

export default Login; 