/**
 * Service Worker para Web Push Notifications
 */

// Nome do cache
const CACHE_NAME = 'atende-ai-v1';

// Arquivos para cache
const urlsToCache = [
  '/',
  '/index.html',
  '/static/js/bundle.js',
  '/static/css/main.css'
];

// Instalar Service Worker
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('📦 Cache aberto');
        return cache.addAll(urlsToCache);
      })
  );
});

// Interceptar requisições
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        // Retornar do cache se disponível
        if (response) {
          return response;
        }
        // Senão, buscar da rede
        return fetch(event.request);
      }
    )
  );
});

// Receber push notifications
self.addEventListener('push', (event) => {
  console.log('🔔 Push notification recebida:', event);
  
  if (event.data) {
    const data = event.data.json();
    const options = {
      body: data.body,
      icon: data.icon || '/favicon.png',
      badge: data.badge || '/favicon.png',
      data: data.data || {},
      actions: data.actions || [],
      requireInteraction: true,
      tag: 'atende-ai-notification'
    };
    
    event.waitUntil(
      self.registration.showNotification(data.title, options)
    );
  }
});

// Clique na notificação
self.addEventListener('notificationclick', (event) => {
  console.log('👆 Notificação clicada:', event);
  
  event.notification.close();
  
  // 🆕 NOVAS AÇÕES DINÂMICAS
  if (event.action === 'view_conversation') {
    // Abrir conversa específica
    const notificationData = event.notification.data;
    const rotaConversa = notificationData?.rota_conversa;
    
    if (rotaConversa) {
      event.waitUntil(
        clients.matchAll({ type: 'window' })
          .then((clientList) => {
            // Se já existe uma janela aberta, focar nela e navegar
            for (let client of clientList) {
              if (client.url.includes('tinyteams.app') && 'focus' in client) {
                client.focus();
                // Enviar mensagem para navegar para a conversa
                client.postMessage({
                  type: 'NAVIGATE_TO_CONVERSATION',
                  route: rotaConversa
                });
                return;
              }
            }
            // Senão, abrir nova janela na conversa
            if (clients.openWindow) {
              return clients.openWindow(rotaConversa);
            }
          })
      );
    }
  } else if (event.action === 'view_logs') {
    // Abrir página de logs
    event.waitUntil(
      clients.matchAll({ type: 'window' })
        .then((clientList) => {
          for (let client of clientList) {
            if (client.url.includes('tinyteams.app') && 'focus' in client) {
              client.focus();
              client.postMessage({
                type: 'NAVIGATE_TO_LOGS'
              });
              return;
            }
          }
          if (clients.openWindow) {
            return clients.openWindow('/admin/logs');
          }
        })
    );
  } else if (event.action === 'view') {
    // Ação padrão (compatibilidade)
    event.waitUntil(
      clients.matchAll({ type: 'window' })
        .then((clientList) => {
          for (let client of clientList) {
            if (client.url.includes('tinyteams.app') && 'focus' in client) {
              return client.focus();
            }
          }
          if (clients.openWindow) {
            return clients.openWindow('/');
          }
        })
    );
  }
});

// Receber mensagens do app principal
self.addEventListener('message', (event) => {
  console.log('📨 Mensagem recebida no SW:', event.data);
  
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
