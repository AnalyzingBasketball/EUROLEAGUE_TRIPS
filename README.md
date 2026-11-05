# Viajes, descanso y rotaciones en baloncesto europeo

Aplicación Streamlit que estudia si los kilómetros de viaje y el poco descanso se relacionan con el rendimiento y con las rotaciones de los clubes españoles que compiten a la vez en la liga ACB y en la Euroliga o la EuroCup. Reúne los calendarios de Euroliga y EuroCup desde 2022/23 hasta 2026/27 (en curso) y el de la ACB de la temporada 2026/27, la única que publica la web de la liga. Calcula, para cada partido y club, el descanso, el viaje y la rotación de la plantilla.

Enlace público: https://euroleague-trips.streamlit.app (usuario `admin`, contraseña `admin`).

## Uso

- Usuario de prueba: `admin` / `admin`.
- Menú lateral con dos páginas:
  - Calendario y viajes: tabla de partidos con descanso y kilómetros, catálogo de sedes, ranking de kilómetros por club y mapa de sedes y viajes.
  - Fatiga y rotaciones: tabla de descanso, carga y rotación, próximos partidos de la API de Euroliga y gráficas en dos bloques seguidos: descanso y rotación, y resultados y viaje (victorias en casa y fuera, resultado según km u horas de viaje, mapa de calor de descanso y viaje).
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
common/                  login, menú, tema, utilidades (carga de CSS), botón de imprimir, generador de PDF
controllers/             lógica: métricas, datos de gráficas, mapa interactivo, figuras, informes
models/                  acceso a datos: SQLite, CSV y API, con esquema SQL
data/                    viajes_fatiga.db, metricas.parquet (métricas ya calculadas), sedes.csv, escudos.csv y paises.json
assets/escudos/          escudos de los 74 clubes (PNG de hasta 128 px)
assets/banderas/         banderas de los 23 países de las sedes (PNG de 80 px, nombre = código ISO)
styles/print.css         estilos de la vista de impresión (oculta menú y botones)
.streamlit/config.toml   oculta el menú automático de Streamlit
tests/                   pruebas con pytest (140)
```

## Fuentes de datos

| Fuente | Uso | Origen |
|---|---|---|
| SQLite `data/viajes_fatiga.db` | Partidos, clubes, sedes y minutos por jugador | API pública de Euroliga (calendario, resultados y estadísticas de Euroliga y EuroCup) y webs públicas de la ACB, `acb.com` (calendario) y `live.acb.com` (minutos), descargadas con los scripts de `tarea/scripts/` |
| CSV `data/sedes.csv` | Catálogo de sedes con coordenadas | Direcciones de la API y de los clubes, geocodificadas con Nominatim |
| API de Euroliga | Próximos partidos de la temporada en curso | `api-live.euroleague.net/v2` (pública) |

Las coordenadas y la ciudad de cada sede proceden de OpenStreetMap (© colaboradores de OpenStreetMap, licencia ODbL); la ciudad de las sedes de la ACB es la del club. Los contornos de países del mapa del PDF son de Natural Earth (dominio público), reducidos a Europa y Oriente Medio. Las sedes marcadas `revisar` tienen una coordenada aproximada, a nivel de ciudad.

Los escudos de los 74 clubes están en `assets/escudos/` y `data/escudos.csv` indica de dónde sale cada uno. Los 64 clubes de Euroliga y EuroCup usan el escudo que publica la API de Euroliga, y los 10 clubes de la ACB que no juegan esas competiciones usan el logo de su ficha en acb.com. Los escudos son marcas de sus clubes y se incluyen solo con fines académicos. Las tablas los muestran en una columna de imagen: cada escudo se convierte en una miniatura de 32 px incrustada en la propia tabla, y como categoría viaja una sola vez al navegador, no una por fila.

La tabla de próximos partidos de la API también lleva escudos: la API escribe los nombres de otra forma (Kosner Baskonia Vitoria-Gasteiz, La Laguna Tenerife), así que cada club se reconoce por su código, competición y temporada en la tabla `club_alias`.

El mapa de la página Calendario y viajes tiene tres modos. Con fondo detallado (teselas de OpenStreetMap servidas por Carto), dibuja las sedes por competición, con la leyenda como filtro, y las rutas de viaje: todas las del club elegido o las 25 más repetidas si no hay club, con el grosor según las veces. Un selector resalta una sede y muestra debajo sus partidos con escudos. La vista de animación por meses suma los partidos y los viajes mes a mes, con botones de reproducir y pausa y un control deslizante. Si las teselas no cargan, el fondo simple dibuja los países sin conexión. Streamlit no devuelve el clic sobre un mapa, por eso la sede se elige con un selector.

Las tablas con país (partidos y catálogo de sedes) llevan además una columna con la bandera del país de la sede. Las 23 banderas están en `assets/banderas/` y se descargaron de flagcdn.com (PNG de 80 px, de uso libre). Se tratan igual que los escudos: miniatura de 40 × 27 px con marco fino (las banderas más altas se recortan y las más anchas se aplanan para que todas midan igual) y columna como categoría.

La base se construye fuera de la aplicación con cuatro scripts (`fetch_euroleague.py`, `fetch_acb.py`, `build_db.py` y `precompute_metrics.py`), que no forman parte de la entrega. Un mismo club cambia de código y de nombre según la competición y la temporada, por lo que el modelo separa el club (identificador propio), sus alias por competición y temporada, y los clubes que juegan cada competición cada año. Valencia Basket cambia de pabellón en 2025 y el modelo lo recoge.

## Métricas

- Descanso: días desde el partido anterior del club en la misma temporada, en cualquier competición.
- Km del viaje: 0 en casa; fuera, ida y vuelta entre la sede base del club y la del partido (distancia de Haversine).
- Km 7 y 14 días: kilómetros del viaje acumulados en esas ventanas, incluido el partido.
- Rotación: jugadores con 10 minutos o más, cuota de minutos de los cinco que más juegan, titulares cambiados respecto al partido anterior.
- Horas de viaje (aproximadas): para cada trayecto, el menor entre autobús a 75 km/h y avión a 750 km/h más 3 horas de aeropuerto, por la ida y la vuelta. Es una estimación, no un dato.
- Margen ajustado: margen real menos el esperado por la fuerza de ambos clubes y la ventaja de campo, con una regresión ridge por competición y temporada.

Las gráficas muestran medias con ±1,96 errores estándar y omiten los tramos con menos de 5 partidos; en el mapa de calor, las celdas con menos de 15 quedan en blanco. Son correlaciones, no causas.

## Caché

| Función | `ttl` | Motivo |
|---|---|---|
| Conexión SQLite (`cache_resource`) | sin límite | Conexión de solo lectura compartida entre sesiones |
| Métricas, clubes y sedes (`cache_data`) | 24 h | La base solo cambia al publicar de nuevo. Las métricas se leen de `data/metricas.parquet`, calculadas de antemano, porque la regresión tarda más de un segundo y en un servidor compartido retrasaría la primera visita |
| CSV de sedes | 24 h | Archivo estático dentro de cada publicación |
| API de Euroliga | 1 h | El calendario cambia a diario como mucho y la API limita las peticiones |

## Actualizar los datos

Con la temporada en curso, los resultados nuevos llegan a la base volviendo a construirla (los tres scripts están en `tarea/scripts/` y no forman parte del zip):

1. `python scripts/fetch_euroleague.py --force --from 2026 --to 2026` descarga de nuevo el calendario y los resultados de Euroliga y EuroCup de la temporada y pide los minutos de los partidos jugados que aún no tiene.
2. `python scripts/fetch_acb.py` descarga el calendario de la ACB y los minutos de los partidos nuevos. Las dos webs permiten el acceso en su `robots.txt`; el script se identifica con un `User-Agent` propio y espera un segundo entre peticiones.
3. `python scripts/build_db.py` recrea la base solo con lo descargado en `data/raw/`. Si un partido nuevo se juega en un pabellón que aún no está en `data/raw/sedes_euroliga_eurocup.csv`, el script lo indica en «sin sede» y hay que añadir esa fila (código, nombre, país y coordenadas) y su ciudad en `data/raw/ciudades_sedes.csv`.
4. `python scripts/precompute_metrics.py` guarda las métricas calculadas en `data/metricas.parquet`.
5. `cd app && pytest` comprueba que los datos son coherentes.
6. Se sube el cambio a GitHub y se reinicia la app en Streamlit Cloud.

La tabla de próximos partidos no necesita nada de esto: se pide en directo a la API y se renueva cada hora.

## Limitaciones

- La web de la ACB solo muestra la temporada en curso y no ofrece un modo público de listar las anteriores, de modo que la doble competición solo se puede estudiar en 2026/27. Euroliga y EuroCup sí cubren las cinco temporadas.
- Los partidos de la ACB aún sin fecha fija (los marca la web como «sin programar») no se incluyen.
- Quedan fuera la Champions League, la Copa del Rey y las ligas domésticas de los clubes extranjeros. La carga de los clubes que además juegan la Champions o la Copa, como Unicaja, está subestimada.
- En ACB la sede del partido es el pabellón habitual del local.
- Solo 7 clubes españoles juegan dos competiciones en 2026/27 (Barcelona, Real Madrid, Baskonia, Valencia, Tenerife, Manresa y Burgos); el resto sirve de rival y de referencia.
- La temporada 2026/27 está en curso y tiene pocos partidos.
