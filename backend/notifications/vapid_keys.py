"""
Chaves VAPID para Web Push Notifications
"""

# Chaves VAPID (geradas para o projeto Atende Ai - PRODUÇÃO)
VAPID_PUBLIC_KEY = "BKX4d946wfF8jf6GfdXOdO24XuvxjH4ZrZlSfEr3o2eRhtt8UP720B8o9EVGYCONRY6gUOe8jP6vQfLpBfAmFEs"
VAPID_PRIVATE_KEY = "rQwXvshxgYE5QNYeCN5Nk6A6ToQ-bpJ1uk1V_GRn3Gc"

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
