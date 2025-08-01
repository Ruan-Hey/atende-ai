#!/usr/bin/env python3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "message": "Server is running"}

@app.get("/test")
def test():
    return {"message": "Test endpoint working"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Iniciando servidor simples na porta 8001...")
    uvicorn.run(app, host="0.0.0.0", port=8001) 