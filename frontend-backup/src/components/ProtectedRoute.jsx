import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import api from '../services/api';

const ProtectedRoute = ({ children }) => {
  const location = useLocation();
  
  // Se não estiver logado, redireciona para login
  if (!api.isLoggedIn()) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  
  // Verificar se é usuário restrito tentando acessar painel geral
  const userData = localStorage.getItem('user');
  if (userData) {
    const user = JSON.parse(userData);
    
    // Se não é superuser e está tentando acessar /admin (painel geral)
    if (!user.is_superuser && location.pathname === '/admin') {
      // Redirecionar para sua empresa específica
      if (user.empresa_slug) {
        return <Navigate to={`/admin/${user.empresa_slug}`} replace />;
      }
      // Se não tem empresa vinculada, redirecionar para login
      return <Navigate to="/login" replace />;
    }
  }
  
  return children;
};

export default ProtectedRoute; 