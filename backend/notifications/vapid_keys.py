"""
Chaves VAPID para Web Push Notifications
"""

# VAPID Keys para Web Push Notifications
import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend

def generate_vapid_keys():
    """Gera novas VAPID keys para push notifications"""
    # Gerar chave privada
    private_key = ec.generate_private_key(
        ec.SECP256R1(),
        default_backend()
    )
    
    # Gerar chave pública
    public_key = private_key.public_key()
    
    # Converter para formato PEM
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    return private_pem.decode(), public_pem.decode()

# VAPID Keys (substitua por suas próprias keys em produção)
VAPID_PRIVATE_KEY = os.getenv('VAPID_PRIVATE_KEY', '')
VAPID_PUBLIC_KEY = os.getenv('VAPID_PUBLIC_KEY', '')

# Configurações VAPID
VAPID_CLAIMS = {
    "sub": "mailto:admin@tinyteams.app",
    "aud": "https://tinyteams.app"
}

# Se não tiver keys, gerar novas
if not VAPID_PRIVATE_KEY or not VAPID_PUBLIC_KEY:
    print("⚠️ VAPID keys não encontradas. Gerando novas...")
    VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY = generate_vapid_keys()
    print("🔑 VAPID keys geradas com sucesso!")
    print("📝 Adicione estas keys ao seu arquivo .env:")
    print(f"VAPID_PRIVATE_KEY='{VAPID_PRIVATE_KEY}'")
    print(f"VAPID_PUBLIC_KEY='{VAPID_PUBLIC_KEY}'")

# Headers VAPID
VAPID_HEADERS = {
    "alg": "ES256",
    "typ": "JWT"
}
