# Viajes, descanso y rotaciones en baloncesto europeo

Aplicación Streamlit que estudia si los kilómetros de viaje y el poco descanso se relacionan con el rendimiento y con las rotaciones de los clubes españoles que compiten a la vez en la liga ACB y en la Euroliga o la EuroCup. Estudia solo la temporada en curso, 2026/27: reúne los calendarios de la ACB, la Euroliga y la EuroCup de esa temporada. Calcula, para cada partido y club, el descanso, el viaje y la rotación de la plantilla.

Enlace público: https://euroleague-trips.streamlit.app (usuario `admin`, contraseña `admin`).

## Uso

- Usuario de prueba: `admin` / `admin`.
- Menú lateral con dos páginas:
  - Calendario y viajes: tabla de partidos con descanso y kilómetros, catálogo de sedes, ranking de kilómetros por club y mapa de sedes y viajes.
  - Fatiga y rotaciones: tabla de descanso, carga y rotación, próximos partidos de la API de Euroliga y gráficas en dos bloques seguidos: descanso y rotación, y resultados y viaje (victorias en casa y fuera, resultado según km u horas de viaje, mapa de calor de descanso y viaje). El mapa de calor está al final de la página; por defecto usa los clubes con doble competición y, al desmarcar «Solo doble competición», pasa a usar todos.
- Cada página tiene un botón para imprimir y otro para exportar a PDF con los datos filtrados en pantalla.

## Instalación y ejecución

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run home.py
```

Se ejecuta desde la carpeta que contiene `home.py`. Se ha probado con Python 3.12 y 3.14. La aplicación no necesita secretos para funcionar. El ZIP incluye un `.env` de prueba generado desde `.env.example` (base local y credenciales `admin` / `admin`); no contiene claves de servicios. En Streamlit Cloud se usarían los _Secrets_.

## Estructura

```
home.py                  portada: configuración, login y resumen
pages/                   una página por análisis (solo presentación)
common/                  login, menú, tema, utilidades (carga de CSS), botón de imprimir, generador de PDF
controllers/             lógica: métricas, datos de gráficas, mapa interactivo, figuras, informes
models/                  acceso a datos: SQLite, CSV y API, con esquema SQL
data/                    base, métricas, catálogos y descargas públicas usadas para construirlos
assets/escudos/          escudos de los 63 clubes (PNG de hasta 128 px)
assets/banderas/         banderas de los 19 países de las sedes (PNG de 80 px, nombre = código ISO)
styles/print.css         estilos de la vista de impresión (oculta menú y botones, hoja horizontal, tablas estáticas)
.streamlit/config.toml   oculta el menú automático de Streamlit
scripts/                descarga pública, construcción de SQLite y precálculo de métricas
data/raw/                calendarios, minutos y catálogos descargados de Euroliga, EuroCup y ACB
tests/                   pruebas con pytest (163)
docs/cuaderno_app.ipynb   cuaderno que contiene el código de la aplicación y lo exporta a los .py
```

El cuaderno `docs/cuaderno_app.ipynb` es la fuente de los 29 archivos `.py` de la aplicación (más el esquema SQL, la hoja de estilos de impresión y `config.toml`). Cada archivo vive en una celda marcada con `#| archivo: ruta`, precedida de su explicación, y la última sección los exporta y comprueba que coinciden con los de la aplicación. Recorre la app en el orden en que viaja un dato: descarga, base SQLite, modelos, métricas, gráficas, PDF, login y páginas. Por defecto no sobrescribe nada; para regenerar la aplicación se ejecuta `exportar(APP)` a mano. Hace falta Jupyter (`pip install jupyter`), que no forma parte de `requirements.txt` porque la aplicación publicada no lo necesita.

## Fuentes de datos

| Fuente | Uso | Origen |
|---|---|---|
| SQLite `data/viajes_fatiga.db` | Partidos, clubes, sedes y minutos por jugador | API pública de Euroliga (calendario, resultados y estadísticas de Euroliga y EuroCup) y webs públicas de la ACB, `acb.com` (calendario) y `live.acb.com` (minutos), descargadas con los scripts incluidos en `scripts/` |
| CSV `data/sedes.csv` | Catálogo de sedes con coordenadas | Direcciones de la API y de los clubes, geocodificadas con Nominatim |
| API de Euroliga | Próximos partidos de la temporada en curso | `api-live.euroleague.net/v2` (pública) |

Las coordenadas y la ciudad de cada sede proceden de OpenStreetMap (© colaboradores de OpenStreetMap, licencia ODbL); la ciudad de las sedes de la ACB es la del club. Los contornos de países del mapa del PDF son de Natural Earth (dominio público), reducidos a Europa y Oriente Medio. Las sedes marcadas `revisar` tienen una coordenada aproximada, a nivel de ciudad.

Los escudos de los 63 clubes están en `assets/escudos/` y `data/escudos.csv` indica de dónde sale cada uno. Los 53 clubes de Euroliga y EuroCup usan el escudo que publica la API de Euroliga, y los 10 clubes de la ACB que no juegan esas competiciones usan el logo de su ficha en acb.com. Los escudos son marcas de sus clubes y se incluyen solo con fines académicos. Las tablas los muestran en una columna de imagen: cada escudo se convierte en una miniatura de 32 px incrustada en la propia tabla, y como categoría viaja una sola vez al navegador, no una por fila.

La tabla de próximos partidos de la API también lleva escudos: la API escribe los nombres de otra forma (Kosner Baskonia Vitoria-Gasteiz, La Laguna Tenerife), así que cada club se reconoce por su código, competición y temporada en la tabla `club_alias`.

El mapa de la página Calendario y viajes tiene tres modos. Con fondo detallado (teselas de OpenStreetMap servidas por Carto), dibuja las sedes por competición, con la leyenda como filtro, y todos los desplazamientos (los del club elegido o los de todos los clubes), de la sede base a la del partido, con el color de la competición y el grosor según las veces. Un selector resalta una sede y muestra debajo sus partidos con escudos. La vista de animación por meses suma los partidos y los viajes mes a mes, con botones de reproducir y pausa y un control deslizante. Si las teselas no cargan, el fondo simple dibuja los países sin conexión. Streamlit no devuelve el clic sobre un mapa, por eso la sede se elige con un selector.

Las tablas con país (partidos y catálogo de sedes) llevan además una columna con la bandera del país de la sede. Las 19 banderas están en `assets/banderas/` y se descargaron de flagcdn.com (PNG de 80 px, de uso libre). Se tratan igual que los escudos: miniatura de 40 × 27 px con marco fino (las banderas más altas se recortan y las más anchas se aplanan para que todas midan igual) y columna como categoría.

La base se construye fuera de la aplicación con los scripts incluidos en `scripts/`: `fetch_euroleague.py`, `fetch_acb.py`, `build_db.py` y `precompute_metrics.py`. Los JSON de origen y catálogos usados en esta entrega están en `data/raw/`. Un mismo club cambia de código y de nombre según la competición y la temporada, por lo que el modelo separa el club (identificador propio), sus alias por competición y temporada, y los clubes que juegan cada competición cada año. La base solo carga la temporada en curso y solo conserva las sedes en las que se juega algún partido.

## Métricas

- Descanso: días desde el partido anterior del club en la misma temporada, en cualquier competición.
- Km del viaje: ida y vuelta entre la sede base del club y la del partido (distancia de Haversine); 0 si se juega en la sede base. Un club que juega como local en otro pabellón (por ejemplo, un equipo israelí en Chipre) también suma ese viaje. Se supone que el club vuelve a su base entre partidos.
- Km 7 y 14 días: kilómetros del viaje acumulados en esas ventanas, incluido el partido.
- Rotación: jugadores con 10 minutos o más, cuota de minutos de los cinco que más juegan, titulares cambiados respecto al partido anterior.
- Horas de viaje (aproximadas): para cada trayecto, el menor entre autobús a 75 km/h y avión a 750 km/h más 3 horas de aeropuerto, por la ida y la vuelta. Es una estimación, no un dato.
- Margen ajustado: margen real menos el esperado por la fuerza de ambos clubes y la ventaja de campo, con una regresión ridge por competición y temporada.

Las gráficas muestran medias con ±1,96 errores estándar y dibujan todos los tramos con datos (los que tienen pocos partidos son poco fiables y con uno solo no hay barra de error); en el mapa de calor, las celdas con menos de 5 partidos quedan en blanco. Son correlaciones, no causas.

## Caché

| Función | `ttl` | Motivo |
|---|---|---|
| Conexión SQLite (`cache_resource`) | sin límite | Conexión de solo lectura compartida entre sesiones |
| Métricas, clubes y sedes (`cache_data`) | 24 h | La base solo cambia al publicar de nuevo. Las métricas se leen de `data/metricas.parquet`, calculadas de antemano, porque la regresión tarda más de un segundo y en un servidor compartido retrasaría la primera visita |
| CSV de sedes | 24 h | Archivo estático dentro de cada publicación |
| API de Euroliga | 1 h | El calendario cambia a diario como mucho y la API limita las peticiones |

## Actualizar los datos

Con la temporada en curso, los resultados nuevos llegan a la base al ejecutar los scripts incluidos en el ZIP, desde la carpeta que contiene `home.py`:

1. `python scripts/fetch_euroleague.py --force --from 2026 --to 2026` descarga de nuevo el calendario y los resultados de Euroliga y EuroCup de la temporada y pide los minutos de los partidos jugados que aún no tiene.
2. `python scripts/fetch_acb.py` descarga el calendario de la ACB y los minutos de los partidos nuevos. Las dos webs permiten el acceso en su `robots.txt`; el script se identifica con un `User-Agent` propio y espera un segundo entre peticiones.
3. `python scripts/build_db.py` recrea la base solo con lo descargado en `data/raw/`. Si un partido nuevo se juega en un pabellón que aún no está en `data/raw/sedes_euroliga_eurocup.csv`, el script lo indica en «sin sede» y hay que añadir esa fila (código, nombre, país y coordenadas) y su ciudad en `data/raw/ciudades_sedes.csv`. Si la API cambia el nombre de un club (por un patrocinador nuevo, por ejemplo), el nombre se fija en `data/raw/clubes_crosswalk.csv`, con una fila por competición y código.
4. `python scripts/precompute_metrics.py` guarda las métricas calculadas en `data/metricas.parquet`.
5. `pytest` comprueba que los datos son coherentes.
6. Se sube el cambio a GitHub y se reinicia la app en Streamlit Cloud.

La tabla de próximos partidos no necesita nada de esto: se pide en directo a la API y se renueva cada hora.

## Limitaciones

- La web de la ACB solo muestra la temporada en curso y no ofrece un modo público de listar las anteriores, y por eso el estudio se limita a la temporada 2026/27 en las tres competiciones.
- Los partidos de la ACB aún sin fecha fija (los marca la web como «sin programar») no se incluyen.
- Quedan fuera la Champions League, la Copa del Rey y las ligas domésticas de los clubes extranjeros. La carga de los clubes que además juegan la Champions o la Copa está subestimada.
- En ACB la sede del partido es el pabellón habitual del local.
- Solo 7 clubes españoles juegan dos competiciones en 2026/27 (Barcelona, Real Madrid, Baskonia, Valencia, Tenerife, Manresa y Burgos); el resto sirve de rival y de referencia.
- La temporada 2026/27 está en curso y tiene pocos partidos.
