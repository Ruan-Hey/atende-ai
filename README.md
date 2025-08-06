# Atende AI - Sistema de Atendimento Inteligente

Sistema completo de atendimento automatizado com integração de APIs e interface moderna.

## 🚀 Funcionalidades

### ✅ **Core Features**
- **Atendimento Automatizado** via WhatsApp
- **LangChain Agents** para processamento inteligente
- **Integração Multi-API** (OpenAI, Google Sheets, Google Calendar, APIs customizadas)
- **Interface Admin** completa
- **Sistema de Empresas** com configurações individuais
- **Discovery Automático de APIs** via documentação

### 🔧 **Integrações Disponíveis**
- **OpenAI** - Inteligência Artificial
- **Google Sheets** - Planilhas e dados
- **Google Calendar** - Agendamentos e eventos
- **APIs Customizadas** - Descoberta automática via documentação

### 🎨 **Interface Moderna**
- **Dashboard Admin** com métricas em tempo real
- **Gestão de Empresas** com configurações avançadas
- **Sistema de APIs** com descoberta automática
- **UI Accordion** para integrações Google
- **Design Responsivo** e moderno

## 🛠️ Tecnologias

### Backend
- **FastAPI** - Framework web
- **PostgreSQL** - Banco de dados principal
- **LangChain** - Framework de IA
- **SQLAlchemy** - ORM
- **Twilio** - Integração WhatsApp
- **Docker** - Containerização

### Frontend
- **React** - Framework UI
- **Vite** - Build tool
- **Material-UI** - Componentes
- **Axios** - HTTP client

## 🚀 Deploy Rápido

### 1. Clone o repositório
```bash
git clone <repository-url>
cd Atende\ Ai
```

### 2. Configure as variáveis de ambiente
```bash
cp env.example .env
# Edite o arquivo .env com suas configurações
```

### 3. Execute o deploy
```bash
./deploy_production.sh
```

### 4. Acesse o sistema
- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:8000
- **Health Check**: http://localhost:8000/health

## 📋 Pré-requisitos

- Docker e Docker Compose
- PostgreSQL (configurado via Docker)
- Variáveis de ambiente configuradas

## 🔧 Configuração

### Variáveis de Ambiente (.env)
```env
# Database
DATABASE_URL=postgresql://user:password@localhost/dbname

# OpenAI
OPENAI_API_KEY=sk-...

# Twilio
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=...

# Google (opcional)
GOOGLE_SHEETS_ID=...
GOOGLE_CALENDAR_CLIENT_ID=...
GOOGLE_CALENDAR_CLIENT_SECRET=...
GOOGLE_CALENDAR_REFRESH_TOKEN=...
```

## 🎯 Uso

### 1. Login Admin
- Acesse http://localhost:3000
- Login: `admin` / Senha: `admin123`

### 2. Criar Empresa
- Vá em "Nova Empresa"
- Configure as integrações desejadas
- Salve as configurações

### 3. Configurar APIs
- Acesse "APIs" no menu admin
- Adicione URLs de documentação para descoberta automática
- Conecte APIs às empresas

### 4. Configurar Webhook
- Configure o webhook do Twilio para: `http://seu-dominio:8000/api/webhook/whatsapp`

## 🔍 Monitoramento

### Health Check
```bash
curl http://localhost:8000/health
```

### Logs
```bash
docker-compose logs -f
```

## 📊 Estrutura do Projeto

```
Atende AI/
├── backend/                 # API FastAPI
│   ├── main.py             # Entry point
│   ├── models.py           # Modelos SQLAlchemy
│   ├── services/           # Serviços de negócio
│   ├── agents/             # Agentes LangChain
│   ├── tools/              # Ferramentas customizadas
│   └── integrations/       # Integrações externas
├── frontend/               # Interface React
│   ├── src/
│   │   ├── components/     # Componentes React
│   │   └── services/       # Serviços de API
│   └── public/             # Assets estáticos
├── docker-compose.yml      # Configuração local
├── docker-compose.prod.yml # Configuração produção
└── deploy_production.sh    # Script de deploy
```

## 🆕 Novidades

### ✅ **Sistema de APIs Dinâmicas**
- Descoberta automática via documentação
- Geração automática de ferramentas LangChain
- Interface visual para gestão de APIs

### ✅ **UI Modernizada**
- Accordion para integrações Google
- Cards elegantes para todas as APIs
- Design consistente e responsivo

### ✅ **Limpeza Completa**
- Remoção de código desnecessário
- Otimização de performance
- Documentação atualizada

## 🚀 Status: **PRONTO PARA PRODUÇÃO**

✅ **Testado e Validado**
✅ **Limpeza Completa**
✅ **Documentação Atualizada**
✅ **Script de Deploy Criado**

---

**Atende AI** - Sistema de Atendimento Inteligente v2.0 