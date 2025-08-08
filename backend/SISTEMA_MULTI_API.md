# Sistema Multi-API de Agenda

## **Como Funciona Agora**

### **1. Prioridade de APIs**

O sistema agora verifica APIs de agenda na seguinte ordem:

1. **Google Calendar** (se configurado)
2. **Trinks** (se configurado)
3. **Outras APIs** (detectadas automaticamente)

### **2. Detecção Automática**

```python
def _find_calendar_api(self, empresa_config):
    # 1. Google Calendar
    if empresa_config.get('google_calendar_client_id'):
        return "Google Calendar", config
    
    # 2. Trinks
    if empresa_config.get('trinks_enabled'):
        return "Trinks", config
    
    # 3. Outras APIs (por nome)
    for key, value in empresa_config.items():
        if key.endswith('_enabled') and value is True:
            api_name = key.replace('_enabled', '').replace('_', ' ').title()
            if any(word in api_name.lower() for word in ['calendar', 'agenda', 'booking', 'schedule', 'trinks']):
                return api_name, config
```

### **3. Cenários de Uso**

#### **Cenário 1: Só Google Calendar**
```
Cliente: "Quero ver horários disponíveis"
→ Sistema: Usa Google Calendar
→ Resposta: "Horários disponíveis no Google Calendar: 10h, 14h, 16h"
```

#### **Cenário 2: Só Trinks**
```
Cliente: "Quero ver horários disponíveis"
→ Sistema: Usa Trinks
→ Resposta: "Verificação Trinks para 2024-01-15: Horários: 09h, 11h, 15h"
```

#### **Cenário 3: Múltiplas APIs**
```
Cliente: "Quero ver horários disponíveis"
→ Sistema: Usa Google Calendar (prioridade)
→ Resposta: "Horários disponíveis no Google Calendar: 10h, 14h, 16h"
```

#### **Cenário 4: Nenhuma API**
```
Cliente: "Quero ver horários disponíveis"
→ Sistema: Não encontra API de agenda
→ Resposta: "Nenhuma API de agenda configurada para esta empresa. Não posso verificar disponibilidade."
```

### **4. Configuração das APIs**

#### **Google Calendar (Específica)**
```python
empresa_config = {
    'google_calendar_client_id': 'xxx',
    'google_calendar_client_secret': 'xxx',
    'google_sheets_id': 'xxx'
}
```

#### **Trinks (Específica)**
```python
empresa_config = {
    'trinks_enabled': True,
    'trinks_config': {
        'api_key': 'xxx',
        'base_url': 'https://api.trinks.com'
    }
}
```

#### **Outras APIs (Genéricas)**
```python
empresa_config = {
    'minha_api_enabled': True,
    'minha_api_config': {
        'api_key': 'xxx',
        'base_url': 'https://api.minhaagenda.com'
    }
}
```

### **5. Endpoints Suportados**

#### **Verificação de Disponibilidade**
- Google Calendar: `get_available_slots()`
- Trinks: `/api/availability`
- Genéricas: `/availability`, `/slots`, `/calendar/availability`, etc.

#### **Fazer Reserva**
- Google Calendar: `create_event()` + Google Sheets
- Trinks: `/api/bookings`
- Genéricas: `/bookings`, `/reservations`, `/appointments`, etc.

#### **Cancelar Reserva**
- Google Calendar: `delete_event()`
- Trinks: `/api/bookings/{id}`
- Genéricas: `/bookings/{id}`

### **6. Vantagens do Sistema**

✅ **Flexibilidade**: Suporta qualquer API de agenda  
✅ **Fallback**: Se uma API falha, tenta outra  
✅ **Extensibilidade**: Fácil adicionar novas APIs  
✅ **Compatibilidade**: Mantém Google Calendar como padrão  
✅ **Detecção Automática**: Encontra APIs por nome  

### **7. Como Adicionar Nova API**

1. **Criar API no banco**:
```sql
INSERT INTO apis (nome, descricao, url_base, tipo_auth) 
VALUES ('Minha Agenda', 'API de agenda personalizada', 'https://api.minhaagenda.com', 'api_key');
```

2. **Conectar à empresa**:
```sql
INSERT INTO empresa_apis (empresa_id, api_id, config, ativo) 
VALUES (1, 1, '{"api_key": "xxx", "base_url": "https://api.minhaagenda.com"}', true);
```

3. **Sistema detecta automaticamente** se o nome contém palavras-chave de agenda

### **8. Logs e Debug**

O sistema registra qual API está sendo usada:
```
INFO: Usando Google Calendar para verificar disponibilidade
INFO: Usando Trinks para fazer reserva
INFO: API genérica 'Minha Agenda' para cancelar reserva
```

### **9. Teste**

Para testar com diferentes APIs:

```python
# Teste com Google Calendar
empresa_config = {'google_calendar_client_id': 'xxx'}

# Teste com Trinks
empresa_config = {'trinks_enabled': True, 'trinks_config': {...}}

# Teste com API genérica
empresa_config = {'minha_api_enabled': True, 'minha_api_config': {...}}
```

**Resultado**: O agente agora é muito mais inteligente e flexível! 🎯 