"""
Sistema de cache para agentes WhatsApp
Mantém agentes em memória por cliente para preservar contexto
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from .whatsapp_agent import WhatsAppAgent

logger = logging.getLogger(__name__)

class AgentCache:
    """Cache de agentes WhatsApp por cliente"""
    
    def __init__(self):
        self._agents: Dict[str, Dict[str, Any]] = {}
        self._max_agents = 100  # Máximo de agentes em cache
        self._cleanup_interval = timedelta(hours=1)  # Limpeza a cada hora
        self._last_cleanup = datetime.now()
    
    def get_agent(self, empresa_slug: str, cliente_id: str, empresa_config: Dict[str, Any]) -> WhatsAppAgent:
        """Obtém ou cria um agente para o cliente"""
        cache_key = f"{empresa_slug}:{cliente_id}"
        
        # Verificar se agente já existe no cache
        if cache_key in self._agents:
            agent_data = self._agents[cache_key]
            
            # Verificar se não expirou (24 horas)
            if datetime.now() - agent_data['created_at'] < timedelta(hours=24):
                logger.info(f"Reutilizando agente existente para {cache_key}")
                return agent_data['agent']
            else:
                # Remover agente expirado
                logger.info(f"Removendo agente expirado para {cache_key}")
                del self._agents[cache_key]
        
        # Criar novo agente
        logger.info(f"Criando novo agente para {cache_key}")
        agent = WhatsAppAgent(empresa_config)
        
        # Adicionar ao cache
        self._agents[cache_key] = {
            'agent': agent,
            'created_at': datetime.now(),
            'last_used': datetime.now(),
            'empresa_config': empresa_config
        }
        
        # Limpar cache se necessário
        self._cleanup_if_needed()
        
        return agent
    
    def update_last_used(self, empresa_slug: str, cliente_id: str):
        """Atualiza timestamp de último uso"""
        cache_key = f"{empresa_slug}:{cliente_id}"
        if cache_key in self._agents:
            self._agents[cache_key]['last_used'] = datetime.now()
    
    def remove_agent(self, empresa_slug: str, cliente_id: str):
        """Remove agente específico do cache"""
        cache_key = f"{empresa_slug}:{cliente_id}"
        if cache_key in self._agents:
            logger.info(f"Removendo agente do cache: {cache_key}")
            del self._agents[cache_key]
    
    def clear_cache(self):
        """Limpa todo o cache"""
        logger.info("Limpando cache de agentes")
        self._agents.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        now = datetime.now()
        active_agents = 0
        expired_agents = 0
        
        for cache_key, agent_data in self._agents.items():
            if now - agent_data['created_at'] < timedelta(hours=24):
                active_agents += 1
            else:
                expired_agents += 1
        
        return {
            'total_agents': len(self._agents),
            'active_agents': active_agents,
            'expired_agents': expired_agents,
            'max_agents': self._max_agents,
            'last_cleanup': self._last_cleanup.isoformat()
        }
    
    def _cleanup_if_needed(self):
        """Limpa cache se necessário"""
        now = datetime.now()
        
        # Limpeza automática a cada hora
        if now - self._last_cleanup > self._cleanup_interval:
            self._cleanup_expired_agents()
            self._cleanup_oldest_agents()
            self._last_cleanup = now
    
    def _cleanup_expired_agents(self):
        """Remove agentes expirados (mais de 24 horas)"""
        now = datetime.now()
        expired_keys = []
        
        for cache_key, agent_data in self._agents.items():
            if now - agent_data['created_at'] > timedelta(hours=24):
                expired_keys.append(cache_key)
        
        for key in expired_keys:
            logger.info(f"Removendo agente expirado: {key}")
            del self._agents[key]
    
    def _cleanup_oldest_agents(self):
        """Remove agentes mais antigos se cache estiver cheio"""
        if len(self._agents) <= self._max_agents:
            return
        
        # Ordenar por último uso (mais antigos primeiro)
        sorted_agents = sorted(
            self._agents.items(),
            key=lambda x: x[1]['last_used']
        )
        
        # Remover os mais antigos
        agents_to_remove = len(self._agents) - self._max_agents
        for i in range(agents_to_remove):
            key, _ = sorted_agents[i]
            logger.info(f"Removendo agente antigo por limite de cache: {key}")
            del self._agents[key]

# Instância global do cache
agent_cache = AgentCache() 