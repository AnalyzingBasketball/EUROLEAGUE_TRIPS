"""Etiquetas en español para códigos: países y competiciones."""

COUNTRY_NAMES = {
    "ad": "Andorra", "ae": "Emiratos Árabes Unidos", "ba": "Bosnia y Herzegovina", "be": "Bélgica", "bg": "Bulgaria",
    "de": "Alemania", "es": "España", "fr": "Francia", "gb": "Reino Unido", "gr": "Grecia", "il": "Israel", "it": "Italia",
    "lt": "Lituania", "lv": "Letonia", "mc": "Mónaco", "me": "Montenegro", "pl": "Polonia", "ro": "Rumanía", "rs": "Serbia",
    "ru": "Rusia", "si": "Eslovenia", "tr": "Turquía",
}


def country_name(code: object) -> object:
    """Código ISO de dos letras -> nombre en español (si no se conoce, el mismo código en mayúsculas)."""
    return COUNTRY_NAMES.get(code, str(code).upper()) if isinstance(code, str) else code
