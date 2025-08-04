# Scripts de Backup e Restauração - Atende AI

Este diretório contém scripts Python para fazer backup e restauração do banco PostgreSQL hospedado no Render.

## 📁 Arquivos

- `backup_database.py` - Script para fazer backup completo do banco
- `restore_database.py` - Script para restaurar backup do banco
- `README_BACKUP.md` - Este arquivo

## 🚀 Como usar

### 1. Fazer Backup

```bash
python3 backup_database.py
```

O script vai:
- Testar conectividade com o banco
- Fazer backup completo usando `pg_dump`
- Salvar arquivo com timestamp: `backup_atendeai_YYYYMMDD_HHMMSS.sql`

### 2. Restaurar Backup

```bash
python3 restore_database.py
```

O script vai:
- Listar arquivos de backup disponíveis
- Permitir escolher qual arquivo restaurar
- Pedir confirmação antes de sobrescrever o banco
- Restaurar usando `psql`

## ⚠️ Pré-requisitos

1. **PostgreSQL Client Tools**: Certifique-se de que `pg_dump` e `psql` estão instalados
   ```bash
   # macOS (com Homebrew)
   brew install postgresql
   
   # Ubuntu/Debian
   sudo apt-get install postgresql-client
   ```

2. **Python 3**: Os scripts usam Python 3

## 🔧 Configurações

Os scripts estão configurados para o banco de produção no Render:

- **Host**: `dpg-d24vpfngi27c73bh06n0-a.oregon-postgres.render.com`
- **Port**: `5432`
- **Database**: `atendeai`
- **User**: `atendeai`

Se precisar alterar as configurações, edite as variáveis no início dos scripts.

## 📊 Informações do Backup

O backup inclui:
- ✅ Todas as tabelas e dados
- ✅ Estrutura completa do banco
- ✅ Índices e constraints
- ✅ Comandos DROP e CREATE para restauração limpa

## 🛠️ Solução de Problemas

### Erro: "pg_dump não encontrado"
```bash
# Instalar PostgreSQL client tools
brew install postgresql  # macOS
sudo apt-get install postgresql-client  # Ubuntu
```

### Erro de conectividade
- Verifique se o banco está online no Render
- Confirme se as credenciais estão corretas
- Teste conectividade manual: `psql -h host -U user -d database`

### Backup muito lento
- O script tem timeout de 5 minutos para backup
- Para bancos grandes, pode ser necessário aumentar o timeout
- Verifique a conexão de internet

### Restauração falha
- Verifique se o arquivo de backup está íntegro
- Confirme se tem permissões suficientes no banco
- Teste com um banco local primeiro

## 🔒 Segurança

- Os scripts usam variáveis de ambiente para senhas
- Arquivos de backup contêm dados sensíveis
- Mantenha os backups em local seguro
- Considere criptografar os arquivos de backup

## 📝 Logs

Os scripts mostram progresso detalhado:
- ✅ Conectividade testada
- 📊 Informações do banco
- 🚀 Progresso do backup/restauração
- 📏 Tamanho do arquivo gerado
- ❌ Erros detalhados se houver

## 🎯 Casos de Uso

### Backup antes de alterações estruturais
```bash
python3 backup_database.py
# Fazer alterações no código
# Se der problema, restaurar:
python3 restore_database.py
```

### Backup regular (cron)
```bash
# Adicionar ao crontab para backup diário
0 2 * * * cd /path/to/project && python3 backup_database.py
```

### Migração de ambiente
```bash
# Backup do ambiente atual
python3 backup_database.py
# Restaurar em novo ambiente
python3 restore_database.py
```

## 📞 Suporte

Se encontrar problemas:
1. Verifique os logs detalhados dos scripts
2. Teste conectividade manual com `psql`
3. Verifique status do banco no Render
4. Consulte documentação do PostgreSQL 