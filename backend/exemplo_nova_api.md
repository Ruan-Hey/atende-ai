# 🚀 Exemplo: Adicionando uma Nova API ao Sistema

## 📋 Cenário
Você quer adicionar uma nova API chamada "Pizzaria API" para a empresa "Pancia Piena".

## 🔧 Passos para Adicionar Nova API

### 1. Cadastrar a API no Sistema
```sql
-- Inserir nova API na tabela apis
INSERT INTO apis (nome, descricao, url_documentacao, url_base, tipo_auth, ativo) 
VALUES (
    'Pizzaria API', 
    'API para gerenciar pedidos de pizza', 
    'https://docs.pizzaria.com', 
    'https://api.pizzaria.com/v1', 
    'api_key', 
    true
);
```

### 2. Conectar a API à Empresa
```sql
-- Conectar API à empresa (substitua os IDs pelos corretos)
INSERT INTO empresa_apis (empresa_id, api_id, config, ativo) 
VALUES (
    1, -- ID da empresa Pancia Piena
    9, -- ID da nova API Pizzaria
    '{
        "api_key": "pizza-api-key-123",
        "base_url": "https://api.pizzaria.com/v1",
        "auth_type": "api_key"
    }',
    true
);
```

### 3. Resultado Automático
Após esses passos, o sistema automaticamente:

1. **Detecta a nova API** no `empresa_config`
2. **Cria Tool dinâmica** chamada `pizzaria_api_call`
3. **Disponibiliza para o agente** sem necessidade de código adicional

## 🎯 Como o Agente Usa a Nova API

### Antes (sem a API):
```python
# Agente só tinha acesso a:
- buscar_cliente
- verificar_calendario  
- fazer_reserva
- enviar_mensagem
- google_calendar_api_call
- trinks_api_call
```

### Depois (com a nova API):
```python
# Agente agora tem acesso a:
- buscar_cliente
- verificar_calendario  
- fazer_reserva
- enviar_mensagem
- google_calendar_api_call
- trinks_api_call
- pizzaria_api_call  # ← NOVA TOOL AUTOMÁTICA!
```

## 🔍 Verificação

### No Frontend:
1. Vá em "Configurações da Empresa"
2. Aba "Conexões e APIs"
3. A nova API aparecerá automaticamente como "Conectada"

### No Backend:
```python
# O empresa_config agora inclui:
empresa_config = {
    # ... configurações existentes ...
    
    # Nova API automaticamente adicionada
    'pizzaria_api_enabled': True,
    'pizzaria_api_config': {
        'api_key': 'pizza-api-key-123',
        'base_url': 'https://api.pizzaria.com/v1',
        'auth_type': 'api_key'
    },
    'pizzaria_api_api_key': 'pizza-api-key-123',
    'pizzaria_api_base_url': 'https://api.pizzaria.com/v1'
}
```

## 🎉 Benefícios

1. **Zero Código**: Não precisa modificar nenhum arquivo de código
2. **Automático**: Sistema detecta e configura automaticamente
3. **Flexível**: Funciona com qualquer tipo de API (api_key, oauth, bearer, etc.)
4. **Seguro**: Credenciais ficam no banco de dados
5. **Escalável**: Pode adicionar quantas APIs quiser

## 📞 Exemplo de Uso pelo Agente

Quando um cliente pedir uma pizza, o agente pode automaticamente:

```python
# O agente pode chamar:
pizzaria_api_call('/pedidos', 'POST', {
    'cliente': 'João Silva',
    'pizza': 'Margherita',
    'tamanho': 'Grande',
    'endereco': 'Rua das Flores, 123'
})
```

## 🚀 Próximos Passos

1. **Teste a nova API** no ambiente de desenvolvimento
2. **Configure as credenciais** corretas
3. **Monitore os logs** para verificar se está funcionando
4. **Deploy para produção** quando estiver tudo ok

---

**🎯 Resultado**: Qualquer API nova que você cadastrar e conectar a uma empresa será automaticamente reconhecida pelo agente LangChain, sem necessidade de modificações no código! 