"""Lógica pura de ingesta: normaliza partidos de la API de Euroliga/EuroCup y resuelve clubes y sedes."""
import math
import unicodedata
from dataclasses import dataclass

VENUE_ACRONYMS = {"BJK", "PAOK", "USH", "CSKA", "LDLC", "SAP", "BLM", "PG"}
VENUE_LOWER = {"de", "del", "della", "dello", "da", "do", "dos", "di", "la", "le", "and"}
VENUE_FIXES = {"PALAEUR": "PalaEur", "PALADOZZA": "PalaDozza", "PALALEONESSA A2A": "PalaLeonessa A2A"}
CLUB_FIXES = {"NINERS Chemnitz": "Niners Chemnitz", "BOSNA BH Telecom Sarajevo": "Bosna BH Telecom Sarajevo"}


def normalize_venue_name(name: str) -> str:
    """Nombre de pabellón con mayúscula inicial en cada palabra; solo toca los nombres escritos todo en mayúsculas.

    Se respetan las siglas (BJK, PAOK, SAP...), las partículas en minúscula (de, dello) y los tokens con cifras (A2A).
    """
    name = " ".join(name.replace("&", " & ").split())
    if name != name.upper():
        return name  # ya viene en mayúsculas y minúsculas
    if name in VENUE_FIXES:
        return VENUE_FIXES[name]
    words = []
    for i, word in enumerate(name.split()):
        if word in VENUE_ACRONYMS or any(c.isdigit() for c in word) or word == "&":
            words.append(word)
        elif word.lower() in VENUE_LOWER and i > 0:
            words.append(word.lower())
        else:
            words.append("-".join(part.capitalize() for part in word.split("-")))
    return " ".join(words)


def tidy_club_name(name: str) -> str:
    """Nombre de club con cada palabra empezando en mayúscula y sin marcas escritas todo en mayúsculas (NINERS, BOSNA)."""
    name = CLUB_FIXES.get(name, name)
    return " ".join(word[:1].upper() + word[1:] for word in name.split())


def norm(text: str) -> str:
    """Minúsculas, sin tildes ni espacios sobrantes, para comparar nombres."""
    nfkd = unicodedata.normalize("NFKD", text or "")
    return " ".join("".join(c for c in nfkd if not unicodedata.combining(c)).lower().split())


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en km sobre la esfera terrestre entre dos coordenadas."""
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


@dataclass(frozen=True)
class Venue:
    """Sede candidata para unir duplicados."""

    key: str
    nombre: str
    lat: float
    lon: float
    precision: str


def same_venue(a: Venue, b: Venue, max_km: float = 0.25) -> bool:
    """Misma sede si comparten nombre o están a menos de `max_km` y ambas tienen coordenada precisa."""
    if norm(a.nombre) == norm(b.nombre):
        return True
    if "ciudad" in (a.precision, b.precision):
        return False
    return haversine_km(a.lat, a.lon, b.lat, b.lon) <= max_km


def group_venues(venues: list[Venue]) -> dict[str, int]:
    """Asigna un número de grupo a cada clave de sede; las sedes iguales comparten grupo."""
    parent = list(range(len(venues)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, a in enumerate(venues):
        for j in range(i + 1, len(venues)):
            if same_venue(a, venues[j]):
                parent[find(j)] = find(i)
    roots: dict[int, int] = {}
    return {v.key: roots.setdefault(find(i), len(roots)) for i, v in enumerate(venues)}


def club_canonical(
    comp: str, code: str, names_by_season: dict[int, str], crosswalk: dict[tuple[str, str], str]
) -> str:
    """Nombre canónico: el del crosswalk si existe; si no, el nombre más reciente de ese código."""
    if (comp, code) in crosswalk:
        return crosswalk[(comp, code)]
    return names_by_season[max(names_by_season)]


def parse_api_game(game: dict, comp: str) -> dict | None:
    """Convierte un partido de la API v2 en una fila plana; devuelve None si algún club es virtual."""
    local, road = game["local"], game["road"]
    if local["club"].get("isVirtual") or road["club"].get("isVirtual"):
        return None
    played = bool(game.get("played"))
    venue = game.get("venue") or {}
    return {
        "game_code": game["gameCode"],
        "season": game["season"]["year"],
        "comp": comp,
        "fecha": (game.get("localDate") or game["date"])[:10],
        "hora_utc": (game.get("utcDate") or "").rstrip("Z") or None,
        "jornada": game.get("round"),
        "fase": (game.get("phaseType") or {}).get("name"),
        "local_code": local["club"]["code"],
        "local_name": local["club"]["name"],
        "road_code": road["club"]["code"],
        "road_name": road["club"]["name"],
        "venue_code": venue.get("code"),
        "neutral": int(bool(game.get("isNeutralVenue"))),
        "jugado": int(played),
        "pts_local": local.get("score") if played else None,
        "pts_visitante": road.get("score") if played else None,
    }


def alias_ranges(
    rows: list[tuple[str, str, str, int]], last_season: int
) -> list[tuple[str, str, str, int, int | None]]:
    """Agrupa (comp, código, nombre, temporada) en rangos; hasta=None si llega a la última temporada."""
    spans: dict[tuple[str, str, str], list[int]] = {}
    for comp, code, name, season in rows:
        spans.setdefault((comp, code, name), []).append(season)
    return [
        (comp, code, name, min(s), None if max(s) == last_season else max(s))
        for (comp, code, name), s in sorted(spans.items())
    ]
