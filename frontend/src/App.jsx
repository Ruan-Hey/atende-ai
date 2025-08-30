import { HashRouter as Router, Routes, Route, useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'
import './App.css'

// Componentes do painel admin
import AdminDashboard from './components/AdminDashboard'
import EmpresaDashboard from './components/EmpresaDashboard'
import LogsViewer from './components/LogsViewer'
import ConversationView from './components/ConversationView'
import Sidebar from './components/Sidebar'
import NovaEmpresa from './components/NovaEmpresa'
import Login from './components/Login'
import ProtectedRoute from './components/ProtectedRoute'
import Usuarios from './components/Usuarios'
import ConfiguracoesEmpresa from './components/ConfiguracoesEmpresa'
import APIManager from './components/APIManager'

// Força a inclusão do componente no build
console.log('ConfiguracoesEmpresa component loaded:', ConfiguracoesEmpresa)
console.log('APIManager component loaded:', APIManager)

function AppRoutes() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(false)
  const location = useLocation();
  const isLoginPage = location.pathname === '/login';

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768)
    }
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen)
  }
  const closeSidebar = () => {
    if (isMobile) {
      setSidebarOpen(false)
    }
  }

  return (
    <div className="app">
      {/* Barra de navegação superior para mobile */}
      {!isLoginPage && isMobile && (
        <nav className="mobile-navbar">
          <button 
            className="mobile-hamburger-btn" 
            onClick={toggleSidebar}
          >
            ☰
          </button>
        </nav>
      )}
      
      {/* Overlay para mobile */}
      {!isLoginPage && (
        <div 
          className={`sidebar-overlay ${sidebarOpen ? 'active' : ''}`}
          onClick={closeSidebar}
        />
      )}
      {/* Sidebar */}
      {!isLoginPage && (
        <Sidebar 
          isOpen={sidebarOpen}
          isMobile={isMobile}
          onClose={closeSidebar}
        />
      )}
      <main className={`main-content ${!isLoginPage && isMobile ? 'with-mobile-navbar' : ''}`}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/admin" element={
            <ProtectedRoute>
              <AdminDashboard />
            </ProtectedRoute>
          } />
          <Route path="/admin/nova-empresa" element={
            <ProtectedRoute>
              <NovaEmpresa />
            </ProtectedRoute>
          } />
          <Route path="/admin/usuarios" element={
            <ProtectedRoute>
              <Usuarios />
            </ProtectedRoute>
          } />
          <Route path="/admin/apis" element={
            <ProtectedRoute>
              <APIManager />
            </ProtectedRoute>
          } />
          <Route path="/admin/empresa/:empresa" element={
            <ProtectedRoute>
              <EmpresaDashboard />
            </ProtectedRoute>
          } />
          <Route path="/admin/empresa/:empresa/logs" element={
            <ProtectedRoute>
              <LogsViewer />
            </ProtectedRoute>
          } />
          <Route path="/admin/empresa/:empresa/conversation/:conversationId" element={
            <ProtectedRoute>
              <ConversationView />
            </ProtectedRoute>
          } />
          <Route path="/admin/empresa/:empresa/configuracoes" element={
            <ProtectedRoute>
              <ConfiguracoesEmpresa />
            </ProtectedRoute>
          } />
          <Route path="/conversation/:empresa" element={
            <ProtectedRoute>
              <ConversationView />
            </ProtectedRoute>
          } />
          <Route path="/conversation/:empresa/:clienteId" element={
            <ProtectedRoute>
              <ConversationView />
            </ProtectedRoute>
          } />
          <Route path="/" element={
            <ProtectedRoute>
              <AdminDashboard />
            </ProtectedRoute>
          } />
          <Route path="*" element={
            <div style={{ padding: '2rem', textAlign: 'center' }}>
              <h2>Página não encontrada</h2>
              <p>A URL que você está tentando acessar não existe.</p>
              <button onClick={() => window.history.back()} className="btn btn-primary">
                Voltar
              </button>
            </div>
          } />
        </Routes>
      </main>
    </div>
  )
}

function App() {
  return (
    <Router>
      <AppRoutes />
    </Router>
  )
}

export default App
