# Chaves VAPID estáticas que funcionam
VAPID_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgJvghjWJEDX7B3+3P
r1HfcRT
-----END PRIVATE KEY-----"""

VAPID_PUBLIC_KEY = "BJvghjWJEDX7B3+3Pr1HfcRT"

VAPID_CLAIMS = {
    "sub": "mailto:admin@tinyteams.app",
    "aud": "https://tinyteams.app"
}

VAPID_HEADERS = {
    "alg": "ES256",
    "typ": "JWT"
}
