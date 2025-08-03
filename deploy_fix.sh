#!/bin/bash

echo "🚀 INICIANDO DEPLOY DA CORREÇÃO"
echo "=================================="

# Verificar se estamos no diretório correto
if [ ! -f "render.yaml" ]; then
    echo "❌ Erro: Execute este script na raiz do projeto"
    exit 1
fi

# Verificar se o git está configurado
if ! git status > /dev/null 2>&1; then
    echo "❌ Erro: Git não está configurado"
    exit 1
fi

echo "📋 Verificando status do git..."
git status

echo ""
echo "🔧 Fazendo commit da correção..."

# Adicionar arquivos modificados
git add backend/integrations/twilio_service.py

# Fazer commit
git commit -m "fix: corrigir problema de número duplicado no Twilio

- Corrige erro '++554184447366' para '+554184447366'
- Remove + duplicado na formatação de números
- Resolve erro 21211 do Twilio"

echo "✅ Commit realizado!"

echo ""
echo "📤 Fazendo push para o repositório..."
git push

echo ""
echo "🎉 DEPLOY INICIADO!"
echo "=================================="
echo "📊 O Render irá detectar as mudanças automaticamente"
echo "⏱️  Deploy deve levar 2-5 minutos"
echo ""
echo "🔍 Para acompanhar o deploy:"
echo "   - Acesse: https://dashboard.render.com"
echo "   - Vá para o serviço 'atende-ai-backend'"
echo "   - Verifique os logs de build"
echo ""
echo "🧪 Para testar após o deploy:"
echo "   - Envie uma mensagem no WhatsApp para +554184447366"
echo "   - Verifique se recebe resposta"
echo ""
echo "📋 Status do deploy será mostrado no dashboard do Render" 