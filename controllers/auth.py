"""Validación de credenciales. Usuario y clave salen del entorno; por defecto admin/admin (lo exige el enunciado)."""
import hmac
import os

DEFAULT_USER = "admin"
DEFAULT_PASSWORD = "admin"


def validate_credentials(user: str, password: str) -> bool:
    """Compara usuario y clave en tiempo constante; rechaza vacíos."""
    if not user or not password:
        return False
    expected_user = os.getenv("APP_USER", DEFAULT_USER)
    expected_password = os.getenv("APP_PASSWORD", DEFAULT_PASSWORD)
    user_ok = hmac.compare_digest(user.encode(), expected_user.encode())
    password_ok = hmac.compare_digest(password.encode(), expected_password.encode())
    return user_ok and password_ok
