# URLs dos Webhooks para Twilio

## Domínio: tinyteams.app

### URLs dos Webhooks:

#### 1. TinyTeams
```
https://api.tinyteams.app/webhook/tinyteams
```

#### 2. Pancia Piena
```
https://api.tinyteams.app/webhook/pancia-piena
```

#### 3. Umas e Ostras
```
https://api.tinyteams.app/webhook/umas-e-ostras
```

## Configuração no Twilio:

### Para cada empresa:
1. **Acesse:** https://console.twilio.com/
2. **Vá em:** Messaging → Senders → WhatsApp
3. **Configure:**
   - **Webhook URL:** `https://api.tinyteams.app/webhook/{empresa}`
   - **HTTP Method:** `POST`
   - **Event Types:** `message`

### Exemplo para TinyTeams:
- **Webhook URL:** `https://api.tinyteams.app/webhook/tinyteams`
- **HTTP Method:** `POST`
- **Event Types:** `message`

## URLs do Frontend:
- **App:** https://app.tinyteams.app
- **API:** https://api.tinyteams.app 