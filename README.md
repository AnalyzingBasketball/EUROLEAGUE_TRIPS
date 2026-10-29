# Viajes, descanso y rotaciones en baloncesto europeo

Aplicación Streamlit que estudia si los kilómetros de viaje y el poco descanso se relacionan con el rendimiento y con las rotaciones de los clubes españoles que compiten a la vez en la liga ACB y en la Euroliga o la EuroCup. Reúne los calendarios de las tres competiciones desde 2022/23 hasta 2026/27 (en curso) y calcula, para cada partido y club, el descanso, el viaje y la rotación de la plantilla.

Enlace público: _pendiente de publicar_.

## Uso

- Usuario de prueba: `admin` / `admin`.
- Menú lateral con dos páginas:
  - Calendario y viajes: tabla de partidos con descanso y kilómetros, catálogo de sedes, ranking de kilómetros por club y mapa de sedes y viajes.
  - Fatiga y rotaciones: tabla de descanso, carga y rotación, próximos partidos de la API de Euroliga y dos gráficas de efecto.
- Cada página tiene un botón para imprimir y otro para exportar a PDF con los datos filtrados en pantalla.

## Instalación y ejecución

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run home.py
```

Se ejecuta desde la carpeta que contiene `home.py`. Se ha probado con Python 3.12 y 3.14. La aplicación no necesita un archivo `.env`; si existe, `DB_PATH` cambia la ruta de la base y `APP_USER` y `APP_PASSWORD` cambian las credenciales (por defecto `admin` / `admin`). En Streamlit Cloud se usarían los _Secrets_.

## Estructura

```
home.py                  portada: configuración, login y resumen
pages/                   una página por análisis (solo presentación)
common/                  login, menú, tema, botón de imprimir, generador de PDF
controllers/             lógica: métricas, datos de gráficas, figuras, informes
models/                  acceso a datos: SQLite, CSV y API, con esquema SQL
data/                    viajes_fatiga.db y sedes.csv
.streamlit/config.toml   oculta el menú automático de Streamlit
tests/                   pruebas con pytest (91)
```

## Fuentes de datos

| Fuente | Uso | Origen |
|---|---|---|
| SQLite `data/viajes_fatiga.db` | Partidos, clubes, sedes y minutos por jugador | API pública de Euroliga y EuroCup (calendario) y estadísticas de ACB y Euroliga procesadas por el autor |
| CSV `data/sedes.csv` | Catálogo de sedes con coordenadas | Direcciones de la API y de los clubes, geocodificadas con Nominatim |
| API de Euroliga | Próximos partidos de la temporada en curso | `api-live.euroleague.net/v2` (pública) |

Las coordenadas proceden de OpenStreetMap (© colaboradores de OpenStreetMap, licencia ODbL). Las sedes marcadas `revisar` tienen una coordenada aproximada, a nivel de ciudad.

La base se construye fuera de la aplicación con dos scripts (`fetch_euroleague.py` y `build_db.py`), que no forman parte de la entrega. Un mismo club cambia de código y de nombre según la competición y la temporada, por lo que el modelo separa el club (identificador propio), sus alias por competición y temporada, y los clubes que juegan cada competición cada año. Valencia Basket cambia de pabellón en 2025 y el modelo lo recoge.

## Métricas

- Descanso: días desde el partido anterior del club en la misma temporada, en cualquier competición.
- Km del viaje: 0 en casa; fuera, ida y vuelta entre la sede base del club y la del partido (distancia de Haversine).
- Km 7 y 14 días: kilómetros del viaje acumulados en esas ventanas, incluido el partido.
- Rotación: jugadores con 10 minutos o más, cuota de minutos de los cinco que más juegan, titulares cambiados respecto al partido anterior.
- Margen ajustado: margen real menos el esperado por la fuerza de ambos clubes y la ventaja de campo, con una regresión ridge por competición y temporada.

Las gráficas muestran medias con ±1,96 errores estándar. Son correlaciones, no causas.

## Caché

| Función | `ttl` | Motivo |
|---|---|---|
| Conexión SQLite (`cache_resource`) | sin límite | Conexión de solo lectura compartida entre sesiones |
| Métricas, clubes y sedes (`cache_data`) | 24 h | La base solo cambia al publicar de nuevo; el cálculo de métricas tarda más de un segundo |
| CSV de sedes | 24 h | Archivo estático dentro de cada publicación |
| API de Euroliga | 1 h | El calendario cambia a diario como mucho y la API limita las peticiones |

## Limitaciones

- No hay minutos de EuroCup, así que la rotación solo se mide en ACB y Euroliga.
- Quedan fuera la Champions League, la Copa del Rey y las ligas domésticas de los clubes extranjeros. La carga de Unicaja y Tenerife, que juegan Champions, está subestimada.
- En ACB la sede del partido es el pabellón habitual del local.
- Solo 9 clubes españoles juegan dos competiciones en el periodo; el resto sirve de rival y de referencia.
- La temporada 2026/27 está en curso y tiene pocos partidos.
