# Testes Unitários - Atende Ai

Este documento descreve a estrutura e execução dos testes unitários do projeto Atende Ai.

## 📋 Visão Geral

Os testes unitários foram criados para garantir a qualidade do código e prevenir regressões antes de cada commit. Eles cobrem:

1. **Carregamento de dados no admin** - Testes para o painel administrativo
2. **Login no admin** - Autenticação e autorização
3. **Webhook e resposta das mensagens do WhatsApp** - Processamento de mensagens
4. **Integração com APIs externas** - OpenAI, Twilio, Google Calendar, Google Sheets
5. **Histórico de mensagens** - Armazenamento e recuperação de conversas

## 🏗️ Estrutura dos Testes

```
backend/tests/
├── __init__.py
├── conftest.py                    # Configuração e fixtures
├── test_admin_data_loading.py     # Testes de carregamento de dados
├── test_admin_login.py            # Testes de login
├── test_webhook_whatsapp.py       # Testes de webhook
├── test_api_integrations.py       # Testes de integração com APIs
├── test_message_history.py         # Testes de histórico
└── test_integration_full_flow.py  # Testes de integração completa
```

## 🚀 Como Executar

### Pré-requisitos

1. Instalar dependências de teste:
```bash
pip install -r requirements.txt
```

2. Configurar variáveis de ambiente para testes:
```bash
cp env.example .env.test
# Editar .env.test com configurações de teste
```

### Execução Básica

```bash
# Executar todos os testes
python run_tests.py all

# Executar testes específicos
python run_tests.py admin
python run_tests.py webhook
python run_tests.py api
python run_tests.py history
python run_tests.py integration

# Executar com cobertura
python run_tests.py all --coverage

# Modo verboso
python run_tests.py all --verbose
```

### Execução com Pytest

```bash
# Todos os testes
pytest tests/

# Testes específicos
pytest tests/test_admin_data_loading.py
pytest tests/test_webhook_whatsapp.py

# Com marcadores
pytest -m admin
pytest -m webhook
pytest -m "not slow"

# Com cobertura
pytest --cov=. --cov-report=html tests/
```

## 📊 Tipos de Teste

### 1. Testes de Carregamento de Dados (Admin)

**Arquivo:** `test_admin_data_loading.py`

Testa o carregamento de dados no painel administrativo:

- ✅ Métricas do admin
- ✅ Lista de empresas
- ✅ Métricas específicas de empresa
- ✅ Lista de clientes
- ✅ Lista de usuários
- ✅ Logs do sistema
- ✅ Status do buffer
- ✅ Performance de carregamento

### 2. Testes de Login (Admin)

**Arquivo:** `test_admin_login.py`

Testa autenticação e autorização:

- ✅ Login bem-sucedido
- ✅ Credenciais inválidas
- ✅ Usuário inexistente
- ✅ Validação de token
- ✅ Controle de acesso (superuser vs usuário regular)
- ✅ Performance de login
- ✅ Logins simultâneos

### 3. Testes de Webhook (WhatsApp)

**Arquivo:** `test_webhook_whatsapp.py`

Testa processamento de mensagens do WhatsApp:

- ✅ Processamento de webhook
- ✅ Empresa inexistente
- ✅ Dados inválidos
- ✅ Mensagens com mídia
- ✅ Integração com OpenAI
- ✅ Resposta via Twilio
- ✅ Tratamento de erros
- ✅ Armazenamento de mensagens
- ✅ Contexto de conversa
- ✅ Limitação de taxa

### 4. Testes de Integração com APIs

**Arquivo:** `test_api_integrations.py`

Testa integrações com APIs externas:

- ✅ OpenAI (geração de respostas)
- ✅ Twilio (envio de mensagens)
- ✅ Google Calendar (eventos)
- ✅ Google Sheets (leitura/escrita)
- ✅ Tratamento de erros
- ✅ Timeout e retry
- ✅ Validação de dados
- ✅ Performance

### 5. Testes de Histórico de Mensagens

**Arquivo:** `test_message_history.py`

Testa armazenamento e recuperação de mensagens:

- ✅ Armazenamento de mensagens
- ✅ Recuperação de histórico
- ✅ Paginação
- ✅ Filtros por data
- ✅ Ordenação por timestamp
- ✅ Mensagens do bot vs usuário
- ✅ Performance com muitas mensagens
- ✅ Acesso concorrente
- ✅ Integridade de dados

### 6. Testes de Integração Completa

**Arquivo:** `test_integration_full_flow.py`

Testa fluxos completos do sistema:

- ✅ Webhook → Processamento → Resposta
- ✅ Fluxo completo do admin
- ✅ Fluxo completo de conversa
- ✅ Tratamento de erros
- ✅ Performance
- ✅ Segurança
- ✅ Integridade de dados
- ✅ Operações concorrentes
- ✅ Recuperação de erros
- ✅ Monitoramento

## 🔧 Configuração

### Fixtures (conftest.py)

O arquivo `conftest.py` contém fixtures comuns para todos os testes:

- `test_db_engine`: Banco de dados SQLite em memória
- `test_db_session`: Sessão do banco de dados
- `client`: Cliente de teste FastAPI
- `mock_redis`: Mock do Redis
- `mock_openai`: Mock do OpenAI
- `mock_twilio`: Mock do Twilio
- `mock_google_calendar`: Mock do Google Calendar
- `mock_google_sheets`: Mock do Google Sheets
- `sample_empresa`: Empresa de exemplo
- `sample_usuario`: Usuário de exemplo
- `sample_mensagem`: Mensagem de exemplo
- `auth_headers`: Headers de autenticação

### Marcadores (Markers)

Os testes usam marcadores para categorização:

- `@pytest.mark.admin`: Testes do admin
- `@pytest.mark.webhook`: Testes de webhook
- `@pytest.mark.api`: Testes de API
- `@pytest.mark.history`: Testes de histórico
- `@pytest.mark.integration`: Testes de integração
- `@pytest.mark.unit`: Testes unitários
- `@pytest.mark.slow`: Testes lentos

## 📈 Cobertura de Código

Para gerar relatório de cobertura:

```bash
# Instalar pytest-cov
pip install pytest-cov

# Executar com cobertura
pytest --cov=. --cov-report=html --cov-report=term-missing tests/

# Abrir relatório
open htmlcov/index.html
```

## 🐛 Debugging

### Executar teste específico

```bash
# Teste específico
pytest tests/test_admin_data_loading.py::TestAdminDataLoading::test_get_admin_metrics_success -v

# Com print statements
pytest tests/test_admin_data_loading.py::TestAdminDataLoading::test_get_admin_metrics_success -s
```

### Logs detalhados

```bash
# Com logs
pytest --log-cli-level=DEBUG tests/
```

## 🔄 CI/CD

Para integração com CI/CD, adicione ao pipeline:

```yaml
# Exemplo para GitHub Actions
- name: Run Tests
  run: |
    cd backend
    python run_tests.py all --coverage
    
- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./backend/coverage.xml
```

## 📝 Boas Práticas

1. **Isolamento**: Cada teste deve ser independente
2. **Mocks**: Use mocks para APIs externas
3. **Fixtures**: Reutilize fixtures comuns
4. **Nomenclatura**: Nomes descritivos para testes
5. **Documentação**: Comente testes complexos
6. **Performance**: Testes devem ser rápidos
7. **Cobertura**: Mantenha alta cobertura de código

## 🚨 Troubleshooting

### Erro: "Module not found"
```bash
# Adicionar diretório ao PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend"
```

### Erro: "Database connection failed"
```bash
# Verificar configuração de banco de teste
# Os testes usam SQLite em memória, não precisam de banco externo
```

### Erro: "Mock not working"
```bash
# Verificar se o mock está no caminho correto
# Usar patch com caminho completo do módulo
```

## 📞 Suporte

Para dúvidas sobre os testes:

1. Verificar logs detalhados
2. Executar teste específico com `-s`
3. Verificar fixtures em `conftest.py`
4. Consultar documentação do pytest

---

**Lembre-se:** Execute os testes antes de cada commit para garantir a qualidade do código! 🚀 