# Atende Ai

Sistema de atendimento virtual multi-empresa com painel admin moderno, autenticação JWT e métricas em tempo real.

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
- **Status ativo/inativo** por empresa

### **🔐 Sistema de Autenticação**
- **JWT (JSON Web Tokens)** para segurança
- **Login com email/senha** criptografado
- **Controle de acesso** por empresa
- **Superusuários** com acesso total
- **Usuários por empresa** com acesso restrito

### **📊 Painel Admin Moderno**
- **Dashboard geral** com métricas macro
- **Dashboards específicos** por empresa
- **Monitoramento de buffer** em tempo real
- **Visualização de logs** e erros
- **Lista de clientes** por empresa
- **Design preto e branco** com logo TinyTeams

### **⚡ Performance Otimizada**
- **Processamento assíncrono** com asyncio
- **Buffer de mensagens** para reduzir respostas
- **Cache Redis** para contexto
- **Escalabilidade** para múltiplas empresas
- **Métricas em tempo real** baseadas em atividades

## 📁 Estrutura do Projeto

```
AtendeAi/
│
├── backend/                    # Backend FastAPI
│   ├── main.py                # Aplicação principal + JWT
│   ├── config.py              # Configurações
│   ├── models.py              # Modelos SQLAlchemy + Pydantic
│   ├── requirements.txt       # Dependências Python
│   │
│   ├── integrations/          # Integrações externas
│   │   ├── openai_service.py
│   │   ├── twilio_service.py
│   │   ├── google_sheets_service.py
│   │   └── chatwoot_service.py
│   │
│   └── services/              # Serviços internos
│       ├── services.py        # Métricas e processamento
│       └── message_buffer.py  # Buffer de mensagens
│
├── frontend/                   # Frontend React
│   ├── src/
│   │   ├── components/
│   │   │   ├── Login.jsx      # Tela de login
│   │   │   ├── AdminDashboard.jsx
│   │   │   ├── EmpresaDashboard.jsx
│   │   │   ├── BufferStatus.jsx
│   │   │   ├── LogsViewer.jsx
│   │   │   └── Sidebar.jsx
│   │   ├── services/
│   │   │   └── api.js         # API com autenticação
│   │   ├── App.jsx
│   │   └── App.css
│   └── package.json
│
├── static/                     # Arquivos estáticos
│   └── tinyteams-logo-login.png # Logo TinyTeams
│
└── README.md                   # Este arquivo
```

## 🛠️ Como rodar localmente

### **1. Pré-requisitos**
```bash
# Instalar Redis
brew install redis  # macOS
# ou
sudo apt-get install redis-server  # Ubuntu

# Instalar PostgreSQL
brew install postgresql  # macOS
# ou
sudo apt-get install postgresql  # Ubuntu
```

### **2. Backend (FastAPI)**

```bash
# Ativar ambiente virtual
source backend/venv/bin/activate

# Instalar dependências
pip install -r backend/requirements.txt

# Configurar banco de dados
cd backend
alembic upgrade head

# Rodar o servidor
uvicorn main:app --reload --port 8001
```

O backend estará disponível em: **http://localhost:8001**

### **3. Frontend (React)**

```bash
# Em outro terminal
cd frontend
npm install
npm run dev
```

O frontend estará disponível em: **http://localhost:5175**

### **4. Acessar o painel admin**

- **Login:** http://localhost:5175/#/login
- **Dashboard Geral:** http://localhost:5175/#/admin
- **Dashboard TinyTeams:** http://localhost:5175/#/admin/tinyteams
- **Status do Buffer:** http://localhost:5175/#/admin/buffer
- **Logs e Erros:** http://localhost:5175/#/admin/logs

**Credenciais padrão:**
- **Email:** ruangimeneshey@gmail.com
- **Senha:** admin123

---

## 🏢 Empresas Configuradas

### **TinyTeams** - Empresa Principal
- **Slug:** `tinyteams`
- **Status:** Ativo
- **Configurações:** Sistema principal de atendimento

### **Pancia Piena** - Pizzaria
- **Slug:** `pancia-piena`
- **Status:** Ativo
- **Configurações:** Atendimento para pedidos de pizza

### **Umas e Ostras** - Restaurante
- **Slug:** `umas-e-ostras`
- **Status:** Ativo
- **Configurações:** Atendimento gastronômico

---

## ⚙️ Configurações

### **Backend (.env)**
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/atendeai

# Redis
REDIS_URL=redis://localhost:6379

# JWT
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256

# APIs
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
OPENAI_API_KEY=your-openai-key
GOOGLE_CREDENTIALS=your-google-credentials
CHATWOOT_API_KEY=your-chatwoot-key
CHATWOOT_BASE_URL=your-chatwoot-url
```

### **Empresa (Database)**
```sql
-- Tabela empresas
CREATE TABLE empresas (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'ativo',
    openai_key TEXT,
    twilio_sid VARCHAR(255),
    twilio_token VARCHAR(255),
    twilio_number VARCHAR(50),
    chatwoot_origem VARCHAR(500),
    chatwoot_token VARCHAR(255),
    prompt TEXT,
    webhook_url VARCHAR(500),
    usar_buffer BOOLEAN DEFAULT true,
    mensagem_quebrada BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Tabela usuários
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    senha_hash VARCHAR(255) NOT NULL,
    is_superuser BOOLEAN DEFAULT false,
    empresa_id INTEGER REFERENCES empresas(id),
    created_at TIMESTAMP DEFAULT NOW()
);
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
- Total de clientes únicos
- Total de atendimentos
- Lista de empresas com status

### **Dashboard por Empresa**
- Métricas específicas da empresa
- Atendimentos e reservas
- Clientes únicos
- Atividade recente
- Lista de clientes da empresa

### **Status do Buffer**
- Buffers ativos em tempo real
- Timers e mensagens agrupadas
- Ações para forçar processamento

### **Logs e Erros**
- Visualização de logs do sistema
- Filtros por empresa e nível
- Monitoramento de erros

### **Gestão de Usuários**
- Lista de usuários
- Criação de novos usuários
- Edição de permissões
- Controle de acesso por empresa

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
- **Métricas** em tempo real

### **PostgreSQL**
- **Dados persistentes** de empresas
- **Usuários** e autenticação
- **Logs** e histórico
- **Configurações** por empresa

---

## 🚀 Deploy em Produção

### **Render (PaaS)**
- **Backend:** https://api.tinyteams.app
- **Frontend:** https://tinyteams.app
- **Database:** PostgreSQL gerenciado
- **Redis:** Redis gerenciado

### **Configurações de Produção**
- ✅ **SSL/HTTPS** automático
- ✅ **Deploy automático** via GitHub
- ✅ **Variáveis de ambiente** seguras
- ✅ **DNS** configurado (Cloudflare)
- ✅ **Monitoramento** de logs

### **Domínios**
- **API:** api.tinyteams.app
- **Web:** tinyteams.app
- **Documentação:** docs.tinyteams.app

---

## 🛠️ Tecnologias utilizadas

### **Backend:**
- **FastAPI** (Python) - Framework web
- **SQLAlchemy** - ORM para PostgreSQL
- **Alembic** - Migrações de banco
- **Redis** - Cache e contexto
- **JWT** - Autenticação segura
- **OpenAI API** - Processamento de linguagem natural
- **Google Sheets API** - Gestão de reservas
- **Twilio API** - WhatsApp Business
- **Chatwoot API** - CRM e atendimento

### **Frontend:**
- **React 19** - Framework frontend
- **Vite** - Build tool
- **React Router** - Navegação
- **Axios** - Requisições HTTP
- **HashRouter** - Compatibilidade com static hosting

### **Design:**
- **Layout preto e branco** - Design moderno
- **Logo TinyTeams** - Identidade visual
- **Responsivo** - Mobile-first
- **Animações suaves** - UX otimizada

### **Infraestrutura:**
- **Render** - PaaS para deploy
- **PostgreSQL** - Banco de dados
- **Redis** - Cache e sessões
- **Cloudflare** - DNS e CDN

---

## 📈 Métricas e Monitoramento

### **Métricas em Tempo Real**
- **Clientes únicos** por empresa
- **Total de atendimentos** por empresa
- **Atividade recente** dos clientes
- **Status** das empresas (ativo/inativo)

### **Monitoramento**
- **Logs** em tempo real
- **Erros** de 24h
- **Status** do buffer
- **Performance** das APIs

---

## 🔧 Comandos Úteis

### **Desenvolvimento Local**
```bash
# Backend
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8001

# Frontend
cd frontend
npm run dev

# Redis
redis-cli

# PostgreSQL
psql -U postgres -d atendeai
```

### **Deploy**
```bash
# Commit e push
git add .
git commit -m "🚀 Deploy: Nova funcionalidade"
git push origin main

# Build frontend
cd frontend
npm run build
```

---

## 📞 Suporte

Para dúvidas ou suporte técnico, entre em contato com a equipe TinyTeams.

---

**Desenvolvido com ❤️ pela TinyTeams** 