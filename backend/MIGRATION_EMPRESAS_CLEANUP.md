# 🧹 Migração: Limpeza da Tabela Empresas

## 📋 Resumo das Mudanças

### ❌ Colunas Removidas da Tabela `empresas`:

| **Coluna** | **Motivo** | **Novo Local** |
|------------|------------|----------------|
| `openai_key` | Movido para `empresa_apis` | `empresa_apis.config` |
| `google_sheets_id` | Movido para `empresa_apis` | `empresa_apis.config` |
| `chatwoot_token` | Movido para `empresa_apis` | `empresa_apis.config` |
| `chatwoot_inbox_id` | Movido para `empresa_apis` | `empresa_apis.config` |
| `chatwoot_origem` | Movido para `empresa_apis` | `empresa_apis.config` |
| `horario_funcionamento` | Removido (não usado) | - |

### ✅ Colunas Mantidas na Tabela `empresas`:

| **Coluna** | **Motivo** |
|------------|------------|
| `id` | Chave primária |
| `slug` | Identificador único |
| `nome` | Nome da empresa |
| `prompt` | Prompt do agente |
| `webhook_url` | URL do webhook |
| `status` | Status da empresa |
| `whatsapp_number` | Número do WhatsApp |
| `twilio_sid` | **Mantido** - Configuração Twilio |
| `twilio_token` | **Mantido** - Configuração Twilio |
| `twilio_number` | **Mantido** - Configuração Twilio |
| `usar_buffer` | Configuração de buffer |
| `mensagem_quebrada` | Configuração de mensagem |
| `created_at` | Timestamp de criação |
| `updated_at` | Timestamp de atualização |

## 🔧 Scripts de Migração

### 1. SQL Script (`cleanup_empresas_table.sql`)
```sql
-- Execute no DBeaver para remover as colunas
DO $$
DECLARE
    col_name text;
BEGIN
    FOR col_name IN 
        SELECT unnest(ARRAY[
            'openai_key',
            'google_sheets_id', 
            'chatwoot_token',
            'chatwoot_inbox_id',
            'chatwoot_origem',
            'horario_funcionamento'
        ])
    LOOP
        IF EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_name = 'empresas' 
            AND column_name = col_name
        ) THEN
            EXECUTE format('ALTER TABLE empresas DROP COLUMN %I', col_name);
        END IF;
    END LOOP;
END $$;
```

### 2. Python Script (`cleanup_empresas_table.py`)
```bash
# Execute para verificar e limpar
python cleanup_empresas_table.py
```

## 🚀 Mudanças no Código

### 1. Modelo `Empresa` (`models.py`)
- ✅ Removidas colunas desnecessárias
- ✅ Mantidas apenas colunas essenciais
- ✅ Twilio permanece na tabela `empresas`

### 2. Endpoint GET (`main.py`)
- ✅ Busca OpenAI de `empresa_apis`
- ✅ Busca Google Calendar de `empresa_apis`
- ✅ Busca Chatwoot de `empresa_apis`
- ✅ Twilio continua vindo de `empresas`

### 3. Endpoint PUT (`main.py`)
- ✅ Salva OpenAI em `empresa_apis`
- ✅ Salva Google Calendar em `empresa_apis`
- ✅ Salva Chatwoot em `empresa_apis`
- ✅ Twilio continua sendo salvo em `empresas`

## 🎯 Benefícios

1. **Organização**: Todas as APIs ficam em `empresa_apis`
2. **Flexibilidade**: Sistema dinâmico para novas APIs
3. **Simplicidade**: Twilio permanece simples na `empresas`
4. **Escalabilidade**: Zero código para novas APIs

## 📝 Próximos Passos

1. **Execute o SQL script** no DBeaver
2. **Teste o sistema** para garantir que funciona
3. **Faça commit** das alterações
4. **Deploy** para produção

## ⚠️ Importante

- **Twilio permanece** na tabela `empresas` (por decisão do usuário)
- **Todas as outras APIs** vão para `empresa_apis`
- **Sistema dinâmico** funciona automaticamente
- **Zero migração de dados** (apenas remoção de colunas) 