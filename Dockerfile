FROM python:3.11-slim

WORKDIR /app

# Copiar requirements
COPY backend/requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY backend/ .

# Expor porta padrão
EXPOSE 8000

# Comando para rodar usando $PORT
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]