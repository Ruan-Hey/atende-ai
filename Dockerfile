# Build stage para o frontend
FROM node:18-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Build stage para o backend
FROM python:3.11-slim AS backend-build
WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .

# Production stage
FROM python:3.11-slim
WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Copiar backend
COPY --from=backend-build /app /app/backend

# Copiar frontend build
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

# Copiar configuração do nginx
COPY frontend/nginx.conf /etc/nginx/nginx.conf

# Script de inicialização
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 80

# Comando para iniciar
CMD ["sh", "-c", "cd /app/backend && python migrate_db.py && python init_db.py && python -m uvicorn main:app --host 0.0.0.0 --port 8001 & sleep 5 && nginx -g 'daemon off;'"] 