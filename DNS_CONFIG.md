# Configuração DNS para tinyteams.app

## Configuração Atual:
- **`api.tinyteams.app`** → Backend (Render)
- **`app.tinyteams.app`** → Frontend (Render)

## Para usar o domínio principal:

### Opção 1: Usar tinyteams.app como Frontend
- **Tipo:** `CNAME`
- **Nome:** `@` (ou deixar em branco)
- **Valor:** `atende-ai-frontend.onrender.com`
- **TTL:** `600`

### Opção 2: Usar tinyteams.app como Backend
- **Tipo:** `A`
- **Nome:** `@` (ou deixar em branco)
- **Valor:** `76.76.19.34`
- **TTL:** `600`

## URLs Finais:
- **Frontend:** `https://tinyteams.app`
- **API:** `https://api.tinyteams.app`
- **Webhooks:** `https://api.tinyteams.app/webhook/{empresa}`

## Qual opção você prefere?
1. **tinyteams.app** → Frontend (app)
2. **tinyteams.app** → Backend (api) 