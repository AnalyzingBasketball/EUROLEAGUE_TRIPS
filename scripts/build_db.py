"""Construye app/data/viajes_fatiga.db con lo descargado por fetch_euroleague.py y fetch_acb.py más las sedes (CSV).

Uso: python scripts/build_db.py [--from 2022] [--to 2026]
Lee solo data/raw/: no necesita ninguna ruta externa. La base se recrea desde cero en cada ejecución.
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from controllers.ingest import (
    Venue,
    alias_ranges,
    club_canonical,
    group_venues,
    normalize_venue_name,
    parse_api_game,
    tidy_club_name,
)
from models.db import DEFAULT_DB_PATH, connect, create_schema

RAW = ROOT / "data" / "raw"
MADRID = ZoneInfo("Europe/Madrid")


def load_crosswalk() -> dict[tuple[str, str], str]:
    """Lee la equivalencia código de Euroliga/EuroCup -> club canónico de ACB."""
    df = pd.read_csv(RAW / "clubes_crosswalk.csv")
    return {(r.competicion, r.codigo): r.club_canonico for r in df.itertuples()}


def load_acb_clubs() -> dict[str, dict]:
    """Lee los pabellones ACB: código ACB -> club canónico, ciudad, pabellón y coordenadas."""
    df = pd.read_csv(RAW / "sedes_acb.csv")
    out = {}
    for r in df.itertuples():
        for code in r.acb_codes.split("|"):
            out[code] = r._asdict()
    return out


def load_cities() -> dict[tuple[float, float], str]:
    """Ciudad de cada sede por coordenadas redondeadas (la genera scripts/geocode_ciudades.py)."""
    df = pd.read_csv(RAW / "ciudades_sedes.csv", keep_default_na=False)
    return {(round(r.lat, 4), round(r.lon, 4)): r.ciudad for r in df.itertuples()}


def insert_venues(conn, acb_clubs: dict[str, dict]) -> tuple[dict[tuple[str, str], int], dict[str, int]]:
    """Inserta sedes sin duplicados; devuelve (comp, vcode) -> sede_id y club ACB canónico -> sede_id."""
    cities = load_cities()
    eu = pd.read_csv(RAW / "sedes_euroliga_eurocup.csv")
    acb = pd.read_csv(RAW / "sedes_acb.csv")
    rows = [
        {"key": f"E:{r.vcode}", "nombre": r.nombre, "direccion": r.direccion, "pais": r.pais, "lat": r.lat, "lon": r.lon,
             "precision": r.precision, "revisar": bool(r.revisar)}
        for r in eu.itertuples()
    ] + [
        {"key": f"A:{r.club_canonico}", "nombre": r.pabellon, "direccion": r.direccion, "pais": r.pais, "lat": r.lat,
             "lon": r.lon, "precision": r.precision, "revisar": bool(r.revisar)}
        for r in acb.itertuples()
    ]
    # Primero ACB: su nombre de pabellón prevalece sobre el de la API al unir duplicados.
    rows.sort(key=lambda r: not r["key"].startswith("A:"))
    groups = group_venues([Venue(r["key"], r["nombre"], r["lat"], r["lon"], r["precision"]) for r in rows])
    group_id: dict[int, int] = {}
    for r in rows:
        g = groups[r["key"]]
        if g not in group_id:
            cur = conn.execute(
                "INSERT INTO sede (nombre, direccion, pais, ciudad, lat, lon, precision, revisar) VALUES (?,?,?,?,?,?,?,?)",
                (normalize_venue_name(r["nombre"]), r["direccion"], r["pais"], cities.get((round(r["lat"], 4), round(r["lon"], 4))), r["lat"],
                 r["lon"], r["precision"], int(r["revisar"])),
            )
            group_id[g] = cur.lastrowid
        elif r["revisar"]:
            conn.execute("UPDATE sede SET revisar = 1 WHERE id = ?", (group_id[g],))
    vcode_to_sede = {}
    club_to_sede = {}
    for r in rows:
        sede_id = group_id[groups[r["key"]]]
        kind, value = r["key"].split(":", 1)
        if kind == "E":
            for comp in ("E", "U"):
                vcode_to_sede[(comp, value)] = sede_id
                conn.execute("INSERT OR IGNORE INTO sede_alias VALUES (?,?,?)", (comp, value, sede_id))
        else:
            club_to_sede[value] = sede_id
    return vcode_to_sede, club_to_sede


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="first", type=int, default=2022)
    parser.add_argument("--to", dest="last", type=int, default=2026)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()
    seasons = range(args.first, args.last + 1)

    args.db.parent.mkdir(parents=True, exist_ok=True)
    args.db.unlink(missing_ok=True)
    conn = connect(args.db)
    create_schema(conn, seasons)

    crosswalk = load_crosswalk()
    acb_clubs = load_acb_clubs()
    vcode_to_sede, club_to_sede = insert_venues(conn, acb_clubs)

    # 1. Leer todas las fuentes en memoria.
    api_games, alias_rows = [], []
    for comp in ("E", "U"):
        for y in seasons:
            for g in json.loads((RAW / "api" / f"{comp}{y}.json").read_text(encoding="utf-8"))["data"]:
                row = parse_api_game(g, comp)
                if row:
                    api_games.append(row)
                    alias_rows += [(comp, row["local_code"], row["local_name"], y),
                                   (comp, row["road_code"], row["road_name"], y)]
    acb_games = []
    for f in sorted((RAW / "acb").glob("calendario_*.json")):
        cal = json.loads(f.read_text(encoding="utf-8"))
        for m in cal["partidos"]:
            # Los partidos «sin programar» llevan una fecha provisional: no se pueden situar en el calendario.
            if m["estado"] != "UNSCHEDULED" and args.first <= cal["temporada"] <= args.last:
                acb_games.append({**m, "season": cal["temporada"]})
                alias_rows += [("ACB", m["home"], m["home_name"], cal["temporada"]),
                               ("ACB", m["away"], m["away_name"], cal["temporada"])]

    # 2. Clubes: id canónico + alias por competición y temporada.
    names: dict[tuple[str, str], dict[int, str]] = defaultdict(dict)
    for comp, code, name, season in sorted(alias_rows, key=lambda r: r[3]):
        names[(comp, code)][season] = name
    acb_canon = {code: info["club_canonico"] for code, info in acb_clubs.items()}
    canon_of: dict[tuple[str, str], str] = {}
    for (comp, code), by_season in names.items():
        if comp == "ACB":
            canon_of[(comp, code)] = acb_canon.get(code) or club_canonical(comp, code, by_season, {})
        else:
            # Los códigos de Euroliga y EuroCup comparten espacio de nombres: mismo código = mismo club.
            latest = max(((s, n) for (c, k), d in names.items() if c in ("E", "U") and k == code
                          for s, n in d.items()))[1]
            canon_of[(comp, code)] = crosswalk.get((comp, code)) or latest
    club_id: dict[str, int] = {}
    for canon in sorted(set(canon_of.values())):
        club_id[canon] = conn.execute("INSERT INTO club (nombre) VALUES (?)", (tidy_club_name(canon),)).lastrowid
    for comp, code, name, desde, hasta in alias_ranges(alias_rows, args.last):
        conn.execute(
            "INSERT OR IGNORE INTO club_alias (club_id, competicion_id, codigo, nombre, temporada_desde, temporada_hasta)"
            " VALUES (?,?,?,?,?,?)",
            (club_id[canon_of[(comp, code)]], comp, code, name, desde, hasta),
        )

    def cid(comp: str, code: str) -> int:
        return club_id[canon_of[(comp, code)]]

    # 3. Pabellón habitual de los clubes ACB (la fuente ACB no trae sede por partido).
    for code, info in acb_clubs.items():
        canon = info["club_canonico"]
        if canon in club_id and canon in club_to_sede:
            conn.execute("INSERT OR IGNORE INTO club_pabellon VALUES (?,?,?,NULL)",
                         (club_id[canon], club_to_sede[canon], args.first))
            conn.execute("UPDATE club SET ciudad = ?, pais = ? WHERE id = ?", (info["ciudad"], info["pais"], club_id[canon]))

    # Cambios de pabellón (p. ej. Valencia Basket se muda al Roig Arena en 2025): cierra el anterior y abre el nuevo.
    for r in pd.read_csv(RAW / "club_pabellon_cambios.csv").itertuples():
        cl = club_id[r.club_canonico]
        conn.execute("UPDATE club_pabellon SET temporada_hasta = ? WHERE club_id = ? AND temporada_hasta IS NULL",
                     (r.temporada_desde - 1, cl))
        conn.execute("INSERT INTO club_pabellon VALUES (?,?,?,NULL)",
                     (cl, vcode_to_sede[("E", r.vcode)], r.temporada_desde))

    # 4. Partidos Euroliga/EuroCup.
    missing_venue = Counter()
    for r in api_games:
        home, away = cid(r["comp"], r["local_code"]), cid(r["comp"], r["road_code"])
        sede = vcode_to_sede.get((r["comp"], r["venue_code"]))
        if sede is None:
            missing_venue[r["comp"]] += 1
        conn.execute(
            "INSERT INTO partido (id, competicion_id, temporada_id, fecha, hora_utc, jornada, fase, local_id,"
            " visitante_id, sede_id, neutral, jugado, pts_local, pts_visitante) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (f"{r['comp']}-{r['season']}-{r['game_code']}", r["comp"], r["season"], r["fecha"], r["hora_utc"],
             r["jornada"], r["fase"], home, away, sede, r["neutral"], r["jugado"], r["pts_local"], r["pts_visitante"]),
        )
        for cl in (home, away):
            conn.execute("INSERT OR IGNORE INTO club_temporada VALUES (?,?,?)", (cl, r["season"], r["comp"]))

    # 5. Partidos ACB: sede = pabellón habitual del local.
    for r in acb_games:
        home, away = cid("ACB", r["home"]), cid("ACB", r["away"])
        utc = datetime.fromisoformat(r["fecha_utc"]).replace(tzinfo=ZoneInfo("UTC"))
        sede = conn.execute(
            "SELECT sede_id FROM club_pabellon WHERE club_id = ? AND temporada_desde <= ?"
            " AND (temporada_hasta IS NULL OR temporada_hasta >= ?)", (home, r["season"], r["season"])).fetchone()
        conn.execute(
            "INSERT INTO partido (id, competicion_id, temporada_id, fecha, hora_utc, jornada, fase, local_id, visitante_id,"
            " sede_id, neutral, jugado, pts_local, pts_visitante) VALUES (?,?,?,?,?,?,?,?,?,?,0,?,?,?)",
            (f"ACB-{r['season']}-{r['id']}", "ACB", r["season"], utc.astimezone(MADRID).date().isoformat(),
             r["fecha_utc"], r["jornada"], "Liga Regular", home, away, sede[0] if sede else None, int(r["jugado"]),
             r["pts_local"], r["pts_visitante"]),
        )
        for cl in (home, away):
            conn.execute("INSERT OR IGNORE INTO club_temporada VALUES (?,?,?)", (cl, r["season"], "ACB"))

    # 6. Minutos por jugador de los partidos jugados: ACB (live.acb.com) y Euroliga/EuroCup (API de estadísticas).
    minutes = 0
    sources = [(f, "ACB") for f in sorted((RAW / "acb").glob("minutos_*.json"))]
    sources += [(RAW / "api" / f"minutos_{comp}{y}.json", comp) for comp in ("E", "U") for y in seasons]
    for f, comp in sources:
        if not f.exists():
            continue
        year = int(f.stem[-4:])
        if not args.first <= year <= args.last:
            continue
        for game_code, sides in json.loads(f.read_text(encoding="utf-8")).items():
            pid = f"{comp}-{year}-{game_code}"
            ids = conn.execute("SELECT local_id, visitante_id FROM partido WHERE id = ?", (pid,)).fetchone()
            if ids is None:
                continue
            for club, key in zip(ids, ("local", "visitante")):
                for p in sides[key]:
                    conn.execute("INSERT OR REPLACE INTO minutos_jugador VALUES (?,?,?,?,?,?)",
                                 (pid, club, p["jugador"], p["titular"], p["minutos"], p["puntos"]))
                    minutes += 1

    conn.commit()
    pd.read_sql_query("SELECT id, nombre, ciudad, pais, lat, lon, precision, revisar FROM sede ORDER BY pais, nombre", conn).to_csv(
        args.db.parent / "sedes.csv", index=False)
    print("sin sede:", dict(missing_venue))
    for table in ("sede", "club", "club_alias", "club_temporada", "partido", "minutos_jugador"):
        print(table, conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    conn.close()


if __name__ == "__main__":
    main()
