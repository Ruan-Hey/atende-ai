-- Script FINAL para remover colunas não utilizadas da tabela empresas
-- Execute este script no DBeaver

-- 1. Remover colunas uma por uma (mais seguro)
ALTER TABLE empresas DROP COLUMN IF EXISTS openai_key;
ALTER TABLE empresas DROP COLUMN IF EXISTS google_sheets_id;
ALTER TABLE empresas DROP COLUMN IF EXISTS chatwoot_token;
ALTER TABLE empresas DROP COLUMN IF EXISTS chatwoot_inbox_id;
ALTER TABLE empresas DROP COLUMN IF EXISTS chatwoot_origem;
ALTER TABLE empresas DROP COLUMN IF EXISTS horario_funcionamento;
ALTER TABLE empresas DROP COLUMN IF EXISTS google_calendar_client_id;
ALTER TABLE empresas DROP COLUMN IF EXISTS google_calendar_client_secret;
ALTER TABLE empresas DROP COLUMN IF EXISTS google_calendar_refresh_token;
ALTER TABLE empresas DROP COLUMN IF EXISTS webhook_url;

-- 2. Mostrar estrutura atual da tabela empresas
SELECT 
    column_name, 
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'empresas' 
ORDER BY ordinal_position;

-- 3. Verificar APIs em empresa_apis
SELECT 
    e.nome as empresa_nome,
    a.nome as api_nome,
    ea.config,
    ea.ativo
FROM empresa_apis ea
JOIN empresas e ON ea.empresa_id = e.id
JOIN apis a ON ea.api_id = a.id
WHERE ea.ativo = true
ORDER BY e.nome, a.nome; 