FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primeiro para aproveitar cache do Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY . .

# Expor porta
EXPOSE 8001

# Scripts de inicialização
COPY init_db.py .
COPY migrate_db.py .

# Comando para rodar a aplicação
CMD ["sh", "-c", "python migrate_db.py && python init_db.py && uvicorn main:app --host 0.0.0.0 --port 8001"] 