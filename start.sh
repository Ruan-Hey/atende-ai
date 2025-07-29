#!/bin/bash

# Inicializar banco de dados
cd /app/backend
python migrate_db.py
python init_db.py

# Iniciar backend em background
python -m uvicorn main:app --host 0.0.0.0 --port 8001 &

# Aguardar backend iniciar
sleep 5

# Iniciar nginx
nginx -g "daemon off;" 