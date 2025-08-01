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
                <Link to={`/admin/${user.empresa_slug}`} className={location.pathname.includes('/admin/') ? 'active' : ''}>
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
            <li>
              <Link to="/admin/buffer/status" className={location.pathname === '/admin/buffer/status' ? 'active' : ''}>
                <svg className="icon" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>
                </svg>
                Status do Buffer
              </Link>
            </li>
            <li>
              <Link to="/admin/logs" className={location.pathname === '/admin/logs' ? 'active' : ''}>
                <svg className="icon" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
                </svg>
                Logs
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