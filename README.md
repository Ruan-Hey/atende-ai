# Atende Ai

Sistema de atendimento virtual multi-empresa com painel admin moderno e agrupamento inteligente de mensagens.

## 🚀 Funcionalidades Principais

### **🤖 Atendimento Virtual Inteligente**
- **Processamento de texto e áudio** via OpenAI (GPT-4o + Whisper)
- **Agrupamento de mensagens** com buffer de 10 segundos
- **Contexto de conversa** mantido no Redis
- **Respostas personalizadas** por empresa

### **🏢 Multi-empresa**
- **Configurações isoladas** por empresa
- **Prompts personalizados** para cada negócio
- **Integrações independentes** (Twilio, OpenAI, Google Sheets, Chatwoot)

### **📊 Painel Admin Moderno**
- **Dashboard geral** com métricas macro
- **Dashboards específicos** por empresa
- **Monitoramento de buffer** em tempo real
- **Visualização de logs** e erros
- **Design preto e branco** com logo TinyTeams

### **⚡ Performance Otimizada**
- **Processamento assíncrono** com asyncio
- **Buffer de mensagens** para reduzir respostas
- **Cache Redis** para contexto
- **Escalabilidade** para múltiplas empresas

## 📁 Estrutura do Projeto

```
AtendeAi/
│
├── backend/                    # Backend FastAPI
│   ├── main.py                # Aplicação principal
│   ├── config.py              # Configurações
│   ├── models.py              # Modelos Pydantic
│   ├── services.py            # Lógica de negócio
│   ├── requirements.txt       # Dependências Python
│   │
│   ├── integrations/          # Integrações externas
│   │   ├── openai_service.py
│   │   ├── twilio_service.py
│   │   ├── google_sheets_service.py
│   │   └── chatwoot_service.py
│   │
│   └── services/              # Serviços internos
│       └── message_buffer.py  # Buffer de mensagens
│
├── frontend/                   # Frontend React
│   ├── src/
│   │   ├── components/
│   │   │   ├── AdminDashboard.jsx
│   │   │   ├── EmpresaDashboard.jsx
│   │   │   ├── BufferStatus.jsx
│   │   │   ├── LogsViewer.jsx
│   │   │   └── Sidebar.jsx
│   │   ├── services/
│   │   │   └── api.js
│   │   ├── App.jsx
│   │   └── App.css
│   └── package.json
│
├── empresas/                   # Configurações por empresa
│   ├── umas-e-ostras/
│   │   ├── prompt.txt
│   │   └── config.json
│   └── pancia-piena/
│       ├── prompt.txt
│       └── config.json
│
├── static/                     # Arquivos estáticos
│   └── tinyteams-logo.png     # Logo TinyTeams
│
└── README.md                   # Este arquivo
```

## 🛠️ Como rodar localmente

### **1. Backend (FastAPI)**

```bash
# Ativar ambiente virtual
source backend/venv/bin/activate

# Instalar dependências (se necessário)
pip install -r backend/requirements.txt

# Rodar o servidor
cd backend
uvicorn main:app --reload --port 8000
```

O backend estará disponível em: **http://localhost:8000**

### **2. Frontend (React)**

```bash
# Em outro terminal
cd frontend
npm run dev
```

O frontend estará disponível em: **http://localhost:5173**

### **3. Acessar o painel admin**

- **Dashboard Geral:** http://localhost:5173/admin
- **Status do Buffer:** http://localhost:5173/admin/buffer/status
- **Logs e Erros:** http://localhost:5173/admin/logs
- **Umas e Ostras:** http://localhost:5173/admin/umas-e-ostras
- **Pancia Piena:** http://localhost:5173/admin/pancia-piena

---

## 🏢 Empresas de exemplo

### **Umas e Ostras** - Restaurante
- **Slug:** `umas-e-ostras`
- **Tipo:** Restaurante
- **Configurações:** Prompt personalizado para atendimento gastronômico

### **Pancia Piena** - Pizzaria
- **Slug:** `pancia-piena`
- **Tipo:** Pizzaria
- **Configurações:** Prompt personalizado para pedidos de pizza

Cada empresa tem sua própria pasta com:
- `prompt.txt` - Prompt do atendente virtual
- `config.json` - Configurações (chaves API, etc.)

---

## ⚙️ Configurações

### **Backend (.env)**
```env
PORT=8000
REDIS_URL=redis://localhost:6379/0
```

### **Empresa (config.json)**
```json
{
  "nome": "Nome da Empresa",
  "whatsapp_number": "",
  "google_sheets_id": "",
  "chatwoot_token": "",
  "openai_key": "",
  "twilio_sid": "",
  "twilio_token": "",
  "twilio_number": "",
  "horario_funcionamento": "",
  "filtros_chatwoot": []
}
```

---

## 🔄 Sistema de Buffer

### **Como funciona:**
1. **Mensagem recebida** → Adicionada ao buffer
2. **Timer de 10 segundos** → Aguarda mais mensagens
3. **Mensagens de texto** → Combinadas em uma resposta
4. **Mensagens de áudio** → Processadas individualmente
5. **Processamento** → OpenAI + Twilio + Chatwoot
6. **Resposta única** → Melhor experiência do usuário

### **Benefícios:**
- ✅ **Reduz spam** de respostas
- ✅ **Melhora experiência** do usuário
- ✅ **Otimiza custos** de API
- ✅ **Processamento inteligente** por tipo de mensagem

---

## 📊 Painel Admin

### **Dashboard Geral**
- Total de empresas ativas
- Métricas macro do sistema
- Lista de empresas com status

### **Dashboard por Empresa**
- Métricas específicas da empresa
- Atendimentos e reservas
- Atividade recente

### **Status do Buffer**
- Buffers ativos em tempo real
- Timers e mensagens agrupadas
- Ações para forçar processamento

### **Logs e Erros**
- Visualização de logs do sistema
- Filtros por empresa e nível
- Monitoramento de erros

---

## 🔗 Integrações

### **OpenAI**
- **GPT-4o** para processamento de texto
- **Whisper** para transcrição de áudio
- **Prompts personalizados** por empresa

### **Twilio**
- **WhatsApp Business API**
- **Envio de mensagens** e templates
- **Webhooks** para receber mensagens

### **Google Sheets**
- **Gestão de reservas**
- **Adicionar/atualizar/cancelar** reservas
- **Listagem** de reservas existentes

### **Chatwoot**
- **Gestão de contatos** e conversas
- **Registro automático** de atendimentos
- **Histórico** de conversas

### **Redis**
- **Cache** de contexto de conversa
- **Buffer** de mensagens
- **Sessões** temporárias

---

## 🚀 Próximos passos

- [ ] **Configurar credenciais** das empresas
- [ ] **Implementar logs reais** no backend
- [ ] **Adicionar métricas reais** do banco de dados
- [ ] **Implementar autenticação** no painel admin
- [ ] **Deploy em produção** com Docker
- [ ] **Monitoramento** com Prometheus/Grafana
- [ ] **Notificações** de erros críticos
- [ ] **Backup automático** de configurações

---

## 🛠️ Tecnologias utilizadas

### **Backend:**
- **FastAPI** (Python) - Framework web
- **Redis** - Cache e contexto
- **OpenAI API** - Processamento de linguagem natural
- **Google Sheets API** - Gestão de reservas
- **Twilio API** - WhatsApp Business
- **Chatwoot API** - CRM e atendimento

### **Frontend:**
- **React 18** - Framework frontend
- **Vite** - Build tool
- **React Router** - Navegação
- **Axios** - Requisições HTTP

### **Design:**
- **Layout preto e branco** - Design moderno
- **Logo TinyTeams** - Identidade visual
- **Responsivo** - Mobile-first
- **Animações suaves** - UX otimizada

---

## 📞 Suporte

Para dúvidas ou suporte técnico, entre em contato com a equipe TinyTeams.

---

**Desenvolvido com ❤️ pela TinyTeams** 