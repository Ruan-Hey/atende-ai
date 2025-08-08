-- Script para limpar a tabela empresas removendo colunas que agora estão em empresa_apis
-- Execute este script no DBeaver ou psql

-- Verificar se as colunas existem antes de removê-las
DO $$
DECLARE
    col_name text;
BEGIN
    -- Lista de colunas para remover
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
        -- Verificar se a coluna existe
        IF EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_name = 'empresas' 
            AND column_name = col_name
        ) THEN
            EXECUTE format('ALTER TABLE empresas DROP COLUMN %I', col_name);
            RAISE NOTICE 'Coluna % removida com sucesso', col_name;
        ELSE
            RAISE NOTICE 'Coluna % não existe, pulando...', col_name;
        END IF;
    END LOOP;
END $$;

-- Mostrar estrutura atual da tabela empresas
SELECT 
    column_name, 
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'empresas' 
ORDER BY ordinal_position;

-- Verificar APIs em empresa_apis
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