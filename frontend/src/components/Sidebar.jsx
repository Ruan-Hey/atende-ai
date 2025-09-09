import { Link, useLocation } from 'react-router-dom'
import TinyTeamsLogo from './TinyTeamsLogo'
import api from '../services/api';
import { useState, useEffect } from 'react';

const Sidebar = ({ isOpen = false, isMobile = false, onClose }) => {
  const location = useLocation()
  const [user, setUser] = useState(null);
  
  // Verifica se está na página de uma empresa específica
  const isEmpresaPage = location.pathname.match(/\/admin\/([^\/]+)$/) && !location.pathname.includes('/configuracoes') && !location.pathname.includes('/conversation')
  const empresaSlug = location.pathname.match(/\/admin\/([^\/]+)$/)?.[1]
  
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

  return (
    <aside className={`sidebar ${isMobile ? (isOpen ? 'active' : 'collapsed') : ''}`}>
      <div className="sidebar-header">
        <TinyTeamsLogo />
      </div>
      <nav className="sidebar-nav">
        <div className="nav-section">
          <h4 className="nav-section-title">MENU</h4>
          <ul>
            {user?.is_superuser && (
              <li>
                <Link to="/admin" className={location.pathname === '/admin' ? 'active' : ''}>
                  <svg className="icon" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/>
                  </svg>
                  Dashboard Geral
                </Link>
              </li>
            )}
            {!user?.is_superuser && user?.empresa_slug && (
              <li>
                <Link to={`/admin/empresa/${user.empresa_slug}`} className={location.pathname.includes('/admin/empresa/') ? 'active' : ''}>
                  <svg className="icon" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 7V3H2v18h20V7H12zM6 19H4v-2h2v2zm0-4H4v-2h2v2zm0-4H4V9h2v2zm0-4H4V5h2v2zm4 12H8v-2h2v2zm0-4H8v-2h2v2zm0-4H8V9h2v2zm0-4H8V5h2v2zm10 12h-8v-2h2v-2h-2v-2h2v-2h-2V9h8v10z"/>
                  </svg>
                  Minha Empresa
                </Link>
              </li>
            )}
          </ul>
        </div>
        
        <div className="nav-section">
          <h4 className="nav-section-title">APPS</h4>
          <ul>
            {user?.is_superuser && (
              <li>
                <Link to="/admin/usuarios" className={location.pathname === '/admin/usuarios' ? 'active' : ''}>
                  <svg className="icon" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M16 4c0-1.11.89-2 2-2s2 .89 2 2-.89 2-2 2-2-.89-2-2zm4 18v-6h2.5l-2.54-7.63A1.5 1.5 0 0 0 18.54 8H17c-.8 0-1.54.37-2.01 1l-1.7 2.26V9H12v11h8zm-8-6c0-1.1.9-2 2-2s2 .9 2 2v4.5c0 .83-.67 1.5-1.5 1.5S12 16.33 12 15.5V12z"/>
                  </svg>
                  Usuários
                </Link>
              </li>
            )}
            {user?.is_superuser && (
              <li>
                <Link to="/admin/apis" className={location.pathname === '/admin/apis' ? 'active' : ''}>
                  <svg className="icon" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-1 9H9V9h10v2zm-4 4H9v-2h6v2zm4-8H9V5h10v2z"/>
                  </svg>
                  APIs
                </Link>
              </li>
            )}
            <li>
              <Link 
                to={user?.is_superuser ? "/conversation/tinyteams" : `/conversation/${user?.empresa_slug}`} 
                className={location.pathname.includes('/conversation/') ? 'active' : ''}
              >
                <svg className="icon" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M20 2H4c-1.1 0-1.99.9-1.99 2L2 22l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-2 12H6v-2h12v2zm0-3H6V9h12v2zm0-3H6V6h12v2z"/>
                </svg>
                Conversas
              </Link>
            </li>
            {user?.is_superuser && (
              <li>
                <Link to="/admin/nova-empresa" className={location.pathname === '/admin/nova-empresa' ? 'active' : ''}>
                  <svg className="icon" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
                  </svg>
                  Nova Empresa
                </Link>
              </li>
            )}
            {/* Configurações sempre visível */}
            <li>
              <Link 
                to={user?.is_superuser ? "/admin/empresa/tinyteams/configuracoes" : `/admin/empresa/${user?.empresa_slug}/configuracoes`} 
                className={location.pathname.includes('/configuracoes') ? 'active' : ''}
              >
                <svg className="icon" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M19.14,12.94c0.04-0.3,0.06-0.61,0.06-0.94c0-0.32-0.02-0.64-0.07-0.94l2.03-1.58c0.18-0.14,0.23-0.41,0.12-0.61 l-1.92-3.32c-0.12-0.22-0.37-0.29-0.59-0.22l-2.39,0.96c-0.5-0.38-1.03-0.7-1.62-0.94L14.4,2.81c-0.04-0.24-0.24-0.41-0.48-0.41 h-3.84c-0.24,0-0.43,0.17-0.47,0.41L9.25,5.35C8.66,5.59,8.12,5.92,7.63,6.29L5.24,5.33c-0.22-0.08-0.47,0-0.59,0.22L2.74,8.87 C2.62,9.08,2.66,9.34,2.86,9.48l2.03,1.58C4.84,11.36,4.8,11.69,4.8,12s0.02,0.64,0.07,0.94l-2.03,1.58 c-0.18,0.14-0.23,0.41-0.12,0.61l1.92,3.32c0.12,0.22,0.37,0.29,0.59,0.22l2.39-0.96c0.5,0.38,1.03,0.7,1.62,0.94l0.36,2.54 c0.05,0.24,0.24,0.41,0.48,0.41h3.84c0.24,0,0.44-0.17,0.47-0.41l0.36-2.54c0.59-0.24,1.13-0.56,1.62-0.94l2.39,0.96 c0.22,0.08,0.47,0,0.59-0.22l1.92-3.32c0.12-0.22,0.07-0.47-0.12-0.61L19.14,12.94z M12,15.6c-1.98,0-3.6-1.62-3.6-3.6 s1.62-3.6,3.6-3.6s3.6,1.62,3.6,3.6S13.98,15.6,12,15.6z"/>
                </svg>
                Configurações
              </Link>
            </li>
            <li>
              <Link 
                to={user?.is_superuser ? "/admin/empresa/tinyteams/lembretes" : `/admin/empresa/${user?.empresa_slug}/lembretes`} 
                className={location.pathname.includes('/lembretes') ? 'active' : ''}
              >
                <svg className="icon" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 22c1.1 0 2-.9 2-2h-4a2 2 0 0 0 2 2zm6-6V9a6 6 0 1 0-12 0v7l-2 2v1h16v-1l-2-2z"/>
                </svg>
                Lembretes
              </Link>
            </li>
            <li>
              <Link 
                to={user?.is_superuser ? "/admin/empresa/tinyteams/logs" : `/admin/empresa/${user?.empresa_slug}/logs`} 
                className={location.pathname.includes('/logs') ? 'active' : ''}
              >
                <svg className="icon" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
                </svg>
                Logs
              </Link>
            </li>
          </ul>
        </div>
      </nav>
      
      {/* Botão de logout */}
      <div className="sidebar-logout">
        <button onClick={handleLogout} className="logout-btn">
          <svg className="logout-icon" viewBox="0 0 24 24" fill="currentColor">
            <path d="M10.09 15.59L11.5 17l5-5-5-5-1.41 1.41L12.67 11H3v2h9.67l-2.58 2.59zM19 3H5c-1.11 0-2 .9-2 2v4h2V5h14v14H5v-4H3v4c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2z"/>
          </svg>
          Sair
        </button>
      </div>
    </aside>
  )
}

export default Sidebar 