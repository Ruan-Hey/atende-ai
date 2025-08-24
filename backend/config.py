import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Carregar variáveis de ambiente globais
load_dotenv()

class Config:
    # Database - Usar banco de produção por padrão
    POSTGRES_URL = os.getenv("DATABASE_URL", "postgresql://atendeai:2pjZBzhDlZY275Z4FubsnBFPsjvLHNRw@dpg-d24vpfngi27c73bh06n0-a.oregon-postgres.render.com/atendeai")
    # Fallback para compatibilidade
    if not POSTGRES_URL or POSTGRES_URL == "postgresql://postgres:postgres@localhost:5432/atendeai":
        POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://atendeai:2pjZBzhDlZY275Z4FubsnBFPsjvLHNRw@dpg-d24vpfngi27c73bh06n0-a.oregon-postgres.render.com/atendeai")
    
    # Se a URL não parece uma URL válida, usar fallback
    if not POSTGRES_URL.startswith("postgresql://"):
        print(f"⚠️ URL inválida detectada: {POSTGRES_URL}")
        POSTGRES_URL = "postgresql://atendeai:2pjZBzhDlZY275Z4FubsnBFPsjvLHNRw@dpg-d24vpfngi27c73bh06n0-a.oregon-postgres.render.com/atendeai"
    
    
    
    # JWT
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
    ALGORITHM = "HS256"
    
    # Twilio
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
    
    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    
    # Google
    GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS", "")
    
    # Chatwoot
    CHATWOOT_API_KEY = os.getenv("CHATWOOT_API_KEY", "")
    CHATWOOT_BASE_URL = os.getenv("CHATWOOT_BASE_URL", "")

    # Caminho para as empresas
    EMPRESAS_PATH = Path('../../empresas')

    @classmethod
    def get_empresa_config(cls, empresa_slug):
        """Carrega configuração de uma empresa específica"""
        empresa_path = cls.EMPRESAS_PATH / empresa_slug

        if not empresa_path.exists():
            raise ValueError(f"Empresa '{empresa_slug}' não encontrada")

        # Carregar config.json
        config_file = empresa_path / 'config.json'
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {}

        # Carregar prompt.txt
        prompt_file = empresa_path / 'prompt.txt'
        if prompt_file.exists():
            with open(prompt_file, 'r', encoding='utf-8') as f:
                config['prompt'] = f.read().strip()

        return config

    @classmethod
    def list_empresas(cls):
        """Lista todas as empresas disponíveis"""
        empresas = []
        for empresa_dir in cls.EMPRESAS_PATH.iterdir():
            if empresa_dir.is_dir():
                config_file = empresa_dir / 'config.json'
                if config_file.exists():
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        empresas.append({
                            'slug': empresa_dir.name,
                            'nome': config.get('nome', empresa_dir.name),
                            'status': 'ativo'
                        })
        return empresas 

# Configuração de Logging Limpo
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'clean': {
            'format': '%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s',
            'datefmt': '%H:%M:%S'
        },
        'detailed': {
            'format': '%(asctime)s | %(levelname)-8s | %(name)-25s | %(funcName)s:%(lineno)d | %(message)s',
            'datefmt': '%H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'clean',
            'stream': 'ext://sys.stdout'
        },
        'file': {
            'class': 'logging.FileHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'filename': 'app.log',
            'mode': 'a'
        }
    },
    'loggers': {
        '': {  # Root logger
            'level': 'INFO',
            'handlers': ['console', 'file']
        },
        'agents.smart_agent': {
            'level': 'INFO',
            'handlers': ['console', 'file'],
            'propagate': False
        },
        'rules.rules_loader': {
            'level': 'INFO',
            'handlers': ['console', 'file'],
            'propagate': False
        },
        'tools': {
            'level': 'INFO',
            'handlers': ['console', 'file'],
            'propagate': False
        },
        'integrations': {
            'level': 'INFO',
            'handlers': ['console', 'file'],
            'propagate': False
        },
        'httpx': {  # Reduzir logs do httpx
            'level': 'WARNING',
            'handlers': ['file'],
            'propagate': False
        },
        'uvicorn': {  # Reduzir logs do uvicorn
            'level': 'WARNING',
            'handlers': ['file'],
            'propagate': False
        }
    }
} 