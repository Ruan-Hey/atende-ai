#!/bin/bash

# Instalar Certbot
sudo apt update
sudo apt install certbot python3-certbot-nginx -y

# Configurar SSL
sudo certbot --nginx -d seu-dominio.com -d www.seu-dominio.com

# Renovar automaticamente
sudo crontab -e
# Adicionar: 0 12 * * * /usr/bin/certbot renew --quiet 