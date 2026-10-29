-- Esquema de viajes y fatiga en clubes con doble competición.
-- Un club tiene un id canónico; sus códigos y nombres cambian por competición y temporada (club_alias).
-- La pertenencia a una competición se deduce por temporada (club_temporada), no de una lista fija de equipos.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS competicion (
    id      TEXT PRIMARY KEY,          -- 'E' Euroliga, 'U' EuroCup, 'ACB' Liga Endesa
    nombre  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS temporada (
    id        INTEGER PRIMARY KEY,     -- año de inicio: 2025 = 2025/26
    etiqueta  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS club (
    id         INTEGER PRIMARY KEY,
    nombre     TEXT NOT NULL UNIQUE,   -- nombre canónico
    ciudad     TEXT,
    pais       TEXT                    -- ISO 3166-1 alfa-2 en minúsculas
);

CREATE TABLE IF NOT EXISTS club_alias (
    id               INTEGER PRIMARY KEY,
    club_id          INTEGER NOT NULL REFERENCES club(id),
    competicion_id   TEXT NOT NULL REFERENCES competicion(id),
    codigo           TEXT NOT NULL,    -- código del club en esa competición
    nombre           TEXT,             -- nombre con el que aparece en la fuente
    temporada_desde  INTEGER NOT NULL REFERENCES temporada(id),
    temporada_hasta  INTEGER REFERENCES temporada(id),  -- NULL = vigente
    UNIQUE (competicion_id, codigo, temporada_desde)
);

CREATE TABLE IF NOT EXISTS club_temporada (
    club_id         INTEGER NOT NULL REFERENCES club(id),
    temporada_id    INTEGER NOT NULL REFERENCES temporada(id),
    competicion_id  TEXT NOT NULL REFERENCES competicion(id),
    PRIMARY KEY (club_id, temporada_id, competicion_id)
);

CREATE TABLE IF NOT EXISTS sede (
    id         INTEGER PRIMARY KEY,
    nombre     TEXT NOT NULL,
    direccion  TEXT,
    pais       TEXT,
    lat        REAL NOT NULL CHECK (lat BETWEEN -90 AND 90),
    lon        REAL NOT NULL CHECK (lon BETWEEN -180 AND 180),
    precision  TEXT NOT NULL CHECK (precision IN ('pabellon', 'calle', 'ciudad')),
    revisar    INTEGER NOT NULL DEFAULT 0 CHECK (revisar IN (0, 1))
);

-- Un mismo pabellón físico llega con varios códigos de la API (p. ej. Ratiopharm Arena).
CREATE TABLE IF NOT EXISTS sede_alias (
    competicion_id  TEXT NOT NULL REFERENCES competicion(id),
    codigo          TEXT NOT NULL,     -- 'vcode' de la API de Euroliga/EuroCup
    sede_id         INTEGER NOT NULL REFERENCES sede(id),
    PRIMARY KEY (competicion_id, codigo)
);

-- Pabellón habitual de un club (se usa en ACB, donde la fuente no trae sede por partido).
CREATE TABLE IF NOT EXISTS club_pabellon (
    club_id          INTEGER NOT NULL REFERENCES club(id),
    sede_id          INTEGER NOT NULL REFERENCES sede(id),
    temporada_desde  INTEGER NOT NULL REFERENCES temporada(id),
    temporada_hasta  INTEGER REFERENCES temporada(id),  -- NULL = vigente
    PRIMARY KEY (club_id, sede_id, temporada_desde)
);

CREATE TABLE IF NOT EXISTS partido (
    id               TEXT PRIMARY KEY, -- '<competicion>-<temporada>-<id de la fuente>'
    competicion_id   TEXT NOT NULL REFERENCES competicion(id),
    temporada_id     INTEGER NOT NULL REFERENCES temporada(id),
    fecha            TEXT NOT NULL,    -- día local del partido, YYYY-MM-DD
    hora_utc         TEXT,             -- ISO 8601 en UTC; NULL en ACB (la fuente no trae hora)
    jornada          INTEGER,
    fase             TEXT,
    local_id         INTEGER NOT NULL REFERENCES club(id),
    visitante_id     INTEGER NOT NULL REFERENCES club(id),
    sede_id          INTEGER REFERENCES sede(id),
    neutral          INTEGER NOT NULL DEFAULT 0 CHECK (neutral IN (0, 1)),
    jugado           INTEGER NOT NULL DEFAULT 0 CHECK (jugado IN (0, 1)),
    pts_local        INTEGER,
    pts_visitante    INTEGER,
    CHECK (local_id <> visitante_id)
);

CREATE INDEX IF NOT EXISTS ix_partido_local ON partido (local_id, fecha);
CREATE INDEX IF NOT EXISTS ix_partido_visitante ON partido (visitante_id, fecha);
CREATE INDEX IF NOT EXISTS ix_partido_temporada ON partido (temporada_id, competicion_id);

CREATE TABLE IF NOT EXISTS minutos_jugador (
    partido_id  TEXT NOT NULL REFERENCES partido(id),
    club_id     INTEGER NOT NULL REFERENCES club(id),
    jugador     TEXT NOT NULL,
    titular     INTEGER NOT NULL DEFAULT 0 CHECK (titular IN (0, 1)),
    minutos     REAL NOT NULL CHECK (minutos >= 0),
    puntos      INTEGER,
    PRIMARY KEY (partido_id, club_id, jugador)
);

CREATE INDEX IF NOT EXISTS ix_minutos_club ON minutos_jugador (club_id, partido_id);
