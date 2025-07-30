import { Link, useLocation } from 'react-router-dom'
import TinyTeamsLogo from './TinyTeamsLogo'
import api from '../services/api';
import { useState, useEffect } from 'react';

const Sidebar = ({ isOpen = false, isMobile = false, onClose }) => {
  const location = useLocation()
  const [user, setUser] = useState(null);
  
  useEffect(() => {
    const userData = localStorage.getItem('user');
    if (userData) {
      setUser(JSON.parse(userData));
    }
  }, []);

  const handleLogout = () => {
    api.logout();
    window.location.href = '/#/login';
  };

  const handleLinkClick = () => {
    if (isMobile && onClose) {
      onClose()
    }
  }

  return (
    <aside className={`sidebar ${isMobile ? (isOpen ? 'active' : 'collapsed') : ''}`}>
      <div className="sidebar-header">
        <TinyTeamsLogo />
        <h3>Atende Ai</h3>
        <p>Painel Admin</p>
      </div>
      <nav className="sidebar-nav">
        <ul>
          {user?.is_superuser && (
            <li>
              <Link to="/admin" className={location.pathname === '/admin' ? 'active' : ''}>
                <span className="icon">📊</span>
                Dashboard Geral
              </Link>
            </li>
          )}
          {!user?.is_superuser && user?.empresa_slug && (
            <li>
              <Link to={`/admin/${user.empresa_slug}`} className={location.pathname.includes('/admin/') ? 'active' : ''}>
                <span className="icon">🏢</span>
                Minha Empresa
              </Link>
            </li>
          )}
          {user?.is_superuser && (
            <li>
              <Link to="/admin/usuarios" className={location.pathname === '/admin/usuarios' ? 'active' : ''}>
                <span className="icon">👥</span>
                Usuários
              </Link>
            </li>
          )}
          <li>
            <Link to="/admin/buffer/status" className={location.pathname === '/admin/buffer/status' ? 'active' : ''}>
              <span className="icon">📋</span>
              Status do Buffer
            </Link>
          </li>
          <li>
            <Link to="/admin/logs" className={location.pathname === '/admin/logs' ? 'active' : ''}>
              <span className="icon">📝</span>
              Logs
            </Link>
          </li>
          {user?.is_superuser && (
            <li>
              <Link to="/admin/nova-empresa" className={location.pathname === '/admin/nova-empresa' ? 'active' : ''}>
                <span className="icon">➕</span>
                Nova Empresa
              </Link>
            </li>
          )}
        </ul>
      </nav>
      
      {/* Botão de logout */}
      <div className="sidebar-logout">
        <button onClick={handleLogout} className="logout-btn">
          Sair
        </button>
      </div>
    </aside>
  )
}

export default Sidebar 