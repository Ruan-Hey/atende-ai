/**
 * Service Worker para Web Push Notifications
 */

// Service Worker para Push Notifications
const CACHE_NAME = 'atende-ai-notifications-v1';

// Instalação do Service Worker
self.addEventListener('install', (event) => {
  console.log('🔧 Service Worker instalado');
  self.skipWaiting();
});

// Ativação do Service Worker
self.addEventListener('activate', (event) => {
  console.log('🚀 Service Worker ativado');
  event.waitUntil(self.clients.claim());
});

// Recebimento de Push Notifications
self.addEventListener('push', (event) => {
  console.log('📱 Push notification recebida:', event);
  
  if (event.data) {
    try {
      const data = event.data.json();
      console.log('📋 Dados da notificação:', data);
      
      const options = {
        body: data.message || 'Nova notificação do Atende AI',
        icon: '/tinyteams-logo.png',
        badge: '/tinyteams-logo.png',
        tag: 'atende-ai-notification',
        data: data,
        actions: [
          {
            action: 'view',
            title: 'Ver Detalhes'
          },
          {
            action: 'close',
            title: 'Fechar'
          }
        ]
      };

      event.waitUntil(
        self.registration.showNotification(
          data.title || 'Atende AI - Notificação',
          options
        )
      );
    } catch (error) {
      console.error('❌ Erro ao processar notificação:', error);
      
      // Notificação de fallback
      event.waitUntil(
        self.registration.showNotification('Atende AI', {
          body: 'Nova notificação recebida',
          icon: '/tinyteams-logo.png'
        })
      );
    }
  }
});

// Clique na notificação
self.addEventListener('notificationclick', (event) => {
  console.log('👆 Notificação clicada:', event);
  
  event.notification.close();
  
  if (event.action === 'view' || !event.action) {
    // Abrir/focar na aplicação
    event.waitUntil(
      self.clients.matchAll({ type: 'window' }).then((clients) => {
        if (clients.length > 0) {
          // Focar na janela existente
          clients[0].focus();
        } else {
          // Abrir nova janela
          self.clients.openWindow('/');
        }
      })
    );
  }
});

// Recebimento de mensagens do frontend
self.addEventListener('message', (event) => {
  console.log('💬 Mensagem recebida no Service Worker:', event.data);
  
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
