#!/bin/bash

echo "🚀 Deploy Atende AI - Produção"
echo "================================"

# Verificar se estamos no diretório correto
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Erro: Execute este script na raiz do projeto"
    exit 1
fi

# Parar containers existentes
echo "🛑 Parando containers existentes..."
docker-compose down

# Limpar imagens antigas
echo "🧹 Limpando imagens antigas..."
docker system prune -f

# Construir e subir containers
echo "🔨 Construindo e subindo containers..."
docker-compose -f docker-compose.prod.yml up -d --build

# Aguardar inicialização
echo "⏳ Aguardando inicialização dos serviços..."
sleep 30

# Verificar status
echo "🔍 Verificando status dos serviços..."
docker-compose -f docker-compose.prod.yml ps

# Testar endpoints
echo "🧪 Testando endpoints..."
curl -f http://localhost:8000/health || echo "❌ Backend não está respondendo"
curl -f http://localhost:3000/ || echo "❌ Frontend não está respondendo"

echo "✅ Deploy concluído!"
echo "🌐 Frontend: http://localhost:3000"
echo "🔧 Backend: http://localhost:8000"
echo "📊 Health Check: http://localhost:8000/health" 