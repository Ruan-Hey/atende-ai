#!/bin/bash

echo "🚀 Deploy Manual Atende AI - Produção"
echo "======================================"

# Parar processos existentes
echo "🛑 Parando processos existentes..."
pkill -f "uvicorn main:app" 2>/dev/null
pkill -f "npm run dev" 2>/dev/null
pkill -f "vite" 2>/dev/null

# Ativar ambiente virtual e subir backend
echo "🔧 Iniciando Backend..."
cd backend
source venv/bin/activate
nohup uvicorn main:app --host 0.0.0.0 --port 8000 --reload > ../backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend iniciado com PID: $BACKEND_PID"

# Aguardar backend inicializar
echo "⏳ Aguardando backend inicializar..."
sleep 5

# Testar backend
echo "🧪 Testando Backend..."
curl -s http://localhost:8000/health
echo ""

# Subir frontend
echo "🎨 Iniciando Frontend..."
cd ../frontend
nohup npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend iniciado com PID: $FRONTEND_PID"

# Aguardar frontend inicializar
echo "⏳ Aguardando frontend inicializar..."
sleep 10

# Testar frontend
echo "🧪 Testando Frontend..."
curl -s http://localhost:5175/ | head -5

echo ""
echo "✅ Deploy Manual Concluído!"
echo "🌐 Frontend: http://localhost:5175"
echo "🔧 Backend: http://localhost:8000"
echo "📊 Health Check: http://localhost:8000/health"
echo ""
echo "📝 Logs:"
echo "Backend: tail -f backend.log"
echo "Frontend: tail -f frontend.log"
echo ""
echo "🛑 Para parar: pkill -f 'uvicorn\|npm\|vite'" 