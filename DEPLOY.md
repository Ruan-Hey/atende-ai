# Deploy do Atende Ai

## Pré-requisitos

- Docker
- Docker Compose
- Git

## Passo a Passo para Deploy

### 1. Clone o repositório
```bash
git clone <seu-repositorio>
cd Atende-Ai
```

### 2. Configure as variáveis de ambiente (opcional)
Crie um arquivo `.env` na raiz do projeto se precisar customizar as configurações:

```env
# Database
POSTGRES_DB=atendeai
POSTGRES_USER=postgres
POSTGRES_PASSWORD=sua-senha-segura

# Backend
SECRET_KEY=sua-chave-secreta-muito-segura

# Redis
REDIS_PASSWORD=sua-senha-redis
```

### 3. Execute o deploy
```bash
# Construir e iniciar todos os serviços
docker-compose up -d --build

# Verificar se tudo está rodando
docker-compose ps
```

### 4. Acesse a aplicação
- Frontend: http://localhost
- Backend API: http://localhost/api
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### 5. Comandos úteis

```bash
# Ver logs
docker-compose logs -f

# Parar serviços
docker-compose down

# Parar e remover volumes (cuidado: apaga dados)
docker-compose down -v

# Rebuild específico
docker-compose up -d --build backend
```

## Deploy em Produção

### 1. Configure um servidor
- Ubuntu 20.04+ recomendado
- Docker e Docker Compose instalados

### 2. Configure domínio e SSL
```bash
# Instalar nginx como proxy reverso
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx

# Configurar nginx para seu domínio
sudo nano /etc/nginx/sites-available/atendeai
```

### 3. Configure SSL
```bash
sudo certbot --nginx -d seu-dominio.com
```

### 4. Configure firewall
```bash
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

## Backup e Restore

### Backup do banco
```bash
docker-compose exec postgres pg_dump -U postgres atendeai > backup.sql
```

### Restore do banco
```bash
docker-compose exec -T postgres psql -U postgres atendeai < backup.sql
```

## Monitoramento

### Logs
```bash
# Logs do backend
docker-compose logs -f backend

# Logs do frontend
docker-compose logs -f frontend

# Logs do banco
docker-compose logs -f postgres
```

### Status dos serviços
```bash
docker-compose ps
```

## Troubleshooting

### Problema: Frontend não carrega
```bash
# Verificar se o build foi feito corretamente
docker-compose logs frontend
```

### Problema: Backend não conecta ao banco
```bash
# Verificar se o postgres está rodando
docker-compose logs postgres

# Testar conexão
docker-compose exec backend python -c "import psycopg2; print('Conexão OK')"
```

### Problema: Redis não conecta
```bash
# Verificar logs do redis
docker-compose logs redis

# Testar conexão
docker-compose exec backend python -c "import redis; r=redis.Redis(); print(r.ping())"
``` 