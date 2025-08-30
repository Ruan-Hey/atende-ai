"""
Chaves VAPID para Web Push Notifications
"""

# VAPID Keys para Web Push Notifications
import os
import json
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend

# Caminho para o arquivo de configuração das chaves
KEYS_FILE = os.path.join(os.path.dirname(__file__), 'vapid_keys.json')

def generate_vapid_keys():
    """Gera novas VAPID keys para push notifications"""
    # Gerar chave privada
    private_key = ec.generate_private_key(
        ec.SECP256R1(),
        default_backend()
    )
    
    # Gerar chave pública
    public_key = private_key.public_key()
    
    # Converter para formato PEM (para chave privada)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Converter para formato base64url sem padding (para chave pública - formato do navegador)
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    
    # Converter para base64url sem padding
    public_base64 = base64.urlsafe_b64encode(public_bytes).decode('utf-8').rstrip('=')
    
    return private_pem.decode(), public_base64

def save_keys_to_file(private_key, public_key):
    """Salva as chaves VAPID em um arquivo JSON"""
    try:
        keys_data = {
            'private_key': private_key,
            'public_key': public_key
        }
        with open(KEYS_FILE, 'w') as f:
            json.dump(keys_data, f, indent=2)
        print(f"💾 Chaves VAPID salvas em: {KEYS_FILE}")
    except Exception as e:
        print(f"⚠️ Erro ao salvar chaves: {e}")

def load_keys_from_file():
    """Carrega as chaves VAPID do arquivo JSON"""
    try:
        if os.path.exists(KEYS_FILE):
            with open(KEYS_FILE, 'r') as f:
                keys_data = json.load(f)
            return keys_data.get('private_key'), keys_data.get('public_key')
    except Exception as e:
        print(f"⚠️ Erro ao carregar chaves: {e}")
    return None, None

# Tentar carregar chaves existentes primeiro
VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY = load_keys_from_file()

# Se não tiver keys, gerar novas e salvar
if not VAPID_PRIVATE_KEY or not VAPID_PUBLIC_KEY:
    print("⚠️ VAPID keys não encontradas. Gerando novas...")
    VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY = generate_vapid_keys()
    
    # Salvar as novas chaves
    save_keys_to_file(VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY)
    
    print("🔑 VAPID keys geradas com sucesso!")
    print("📝 As chaves foram salvas automaticamente para uso futuro.")

# Configurações VAPID
VAPID_CLAIMS = {
    "sub": "mailto:admin@tinyteams.app",
    "aud": "https://tinyteams.app"
}

# Headers VAPID
VAPID_HEADERS = {
    "alg": "ES256",
    "typ": "JWT"
}
