# AGENTS.md — Guía para Agentes de Codificación

Este archivo proporciona contexto e instrucciones técnicas para que los agentes de IA (como Antigravity, Claude, etc.) entiendan la arquitectura del proyecto y puedan trabajar en él de forma segura y eficiente.

---

## 1. Contexto del Proyecto

* **Nombre del Addon:** Stremio for Kodi (`plugin.video.stremio4kodi`)
* **Propósito:** Cliente ligero para Kodi que consume la API de addons de Stremio. Permite listar catálogos y reproducir contenido mediante motores de torrents o cuentas Debrid.
* **Lenguaje:** Python 3 (compatible con la API de Kodi Python 3.0.0+).
* **Dependencias de Kodi:** `xbmc.python`, `xbmc.addon`, `script.module.requests`.

---

## 2. Flujo de Trabajo y Relación con el Repositorio

El proyecto está dividido en dos repositorios/carpetas hermanas:
1. `plugin.video.stremio4kodi` (esta carpeta): Contiene el código fuente del addon.
2. `repository.sonvice` (carpeta hermana): Contiene el índice y el script generador (`generator.py`) del repositorio remoto de Kodi.

### Cómo publicar cambios y subir versión:
1. Realiza las modificaciones en esta carpeta (`plugin.video.stremio4kodi`).
2. Sube la versión del addon en el archivo `addon.xml` (ej: de `3.2.3` a `3.2.4`).
3. Ve a la carpeta hermana `repository.sonvice` y ejecuta:
   ```bash
   python3 generator.py
   ```
   *Esto generará automáticamente los nuevos paquetes `.zip`, reconstruirá los índices `addons.xml` y `addons.xml.md5` y regenerará el `index.html`.*
4. Sube los cambios generados al repositorio remoto en GitHub para que Kodi detecte la nueva versión.

---

## 3. Características Clave Añadidas en v3.2.6

### 3.1. Buscador DHT Descentralizado Multifuente (Paralelo)
* **Archivo del Cliente:** [dht_search.py](file:///home/wilson/Pictures/plugin.video.stremio4kodi_v3.2.3/plugin.video.stremio4kodi/resources/lib/dht_search.py)
* **APIs Utilizadas:** 
  * `Bitsearch` (`https://bitsearch.eu/api/v1/search`)
  * `Apibay (The Pirate Bay)` (`https://apibay.org/q.php`)
  * `SolidTorrents` (`https://solidtorrents.net/api/v1/search`)
* **Mecanismo:** Realiza búsquedas de texto simultáneas en paralelo utilizando un `ThreadPoolExecutor` con hilos concurrentes. Combina los resultados de los tres buscadores y los deduplica según su `infoHash` de forma insensible a mayúsculas. Los resultados se integran con `TorrentResolver`.
* **Integración en Menú:** Añadido como ruta `dht_search` en [router.py](file:///home/wilson/Pictures/plugin.video.stremio4kodi_v3.2.3/plugin.video.stremio4kodi/resources/lib/router.py).

### 3.2. Trending Torrents (Tendencias)
* **APIs Utilizadas:** Endpoints JSON precompilados de Apibay/The Pirate Bay:
  * Top 48h: `https://apibay.org/precompiled/data_top100_48h.json`
  * Recientes/Novedades: `https://apibay.org/precompiled/data_top100_recent.json`
* **Mecanismo:** Permite listar las tendencias o novedades de torrents de las últimas 48 horas sin necesidad de escribir una búsqueda, estructurándolas como streams listos para reproducir.
* **Integración en Menú:** Añadido como ruta `trending` en [router.py](file:///home/wilson/Pictures/plugin.video.stremio4kodi_v3.2.3/plugin.video.stremio4kodi/resources/lib/router.py).

### 3.3. Repositorio con Espejo CDN (jsDelivr)
* **Objetivo:** Evitar que los bloqueos de ISPs locales al dominio `raw.githubusercontent.com` rompan las actualizaciones automáticas.
* **Mecanismo:** El archivo `addon.xml` del repositorio remoto utiliza URLs de la red de entrega de contenido (CDN) gratuita **jsDelivr** (apuntando a la rama `main` del repo de GitHub).

---

## 4. Características Añadidas en v3.2.9

### 4.1. Filtros de Búsqueda DHT
* **Selector de Categorías:** Se añade una ventana de diálogo interactiva al buscar torrents en DHT que permite filtrar por:
  * 🎬 Películas (Video)
  * 📺 Series (TV)
  * 🎵 Música
* **Exclusión de Basura:** Esto evita que aparezcan archivos ejecutables de software, comprimidos u otros tipos de archivos no aptos para reproducción.

### 4.2. Verificador de Caché Real-Debrid en DHT / Tendencias
* **Comprobación rápida de disponibilidad instantánea (Instant Availability):** Al buscar en DHT o consultar tendencias, el addon verifica en paralelo contra la API de Real-Debrid si el torrent está almacenado en su caché.
* **Priorización visual:** Muestra la etiqueta `[RD+]` al inicio de cada stream y prioriza su orden colocándolos al principio del listado.

### 4.3. Sincronización en Tiempo Real con Trakt (Scrobbling)
* **Monitor de Reproducción en Segundo Plano:** Implementado en `service.py` como un reproductor monitorizado que informa periódicamente a la API de Trakt.tv sobre el estado de la reproducción actual (`start` / `pause` / `stop`) y su progreso porcentual en tiempo real.

---

## 5. Características Añadidas en v3.3.0 - v3.4.5

### 5.1. Integración Completa de la API de TMDB
* **Soporte de Autenticación Híbrida (v3 Key y v4 JWT):** Admite claves de API de 32 caracteres hex así como Tokens Bearer v4 JWT (`eyJhbGci...`), enviándolos automáticamente mediante la cabecera `Authorization: Bearer <token>`.
* **Menús y Navegación Limpios:**
  * *Tendencias (Hoy / Semana)*
  * *Lo más popular*
  * *En cartelera (Estrenos Cine)* con parámetro `region=ES` para evitar colisiones con lo más popular global.
  * *Mejor puntuadas*
  * *Top 100 Últimos Años*
  * *Categorías / Géneros*
  * *Catálogos Stremio (Cinemeta / Addons)*
* **Respaldo Cinemeta Transparente:** En caso de fallo de red o caída de la API de TMDB, el addon conmuta automáticamente a los catálogos de Stremio Cinemeta (`https://v3-cinemeta.strem.io`) garantizando que nunca aparezca una pantalla vacía (`0/0`).

### 5.2. Resolución de Streams y Reproducción DHT (Wolchok et al.)
* **Documentación Base:** Basado en la investigación de *Scott Wolchok et al.* (`Wolchok.pdf`) sobre la indagación e indexación de torrent `infoHash` y nodos pares en la red **Mainline BitTorrent DHT**.
* **Búsqueda Bilingüe Paralela:** Consulta streams usando el título original en inglés y el título traducido al español para maximizar la tasa de acierto de torrents disponibles.
* **Desduplicación Inteligente:** `StremioClient.dedup_items` desduplica elementos según la firma unificada `tmdb_id`, `imdb_id`, `id` de catálogo o combinación `título:año`.

### 5.3. Interfaz Nativa de Kodi a Prueba de Fallos
* **Compatibilidad de Fuentes (Sin Emojis):** Se eliminaron los caracteres emoji unicode (que generaban rectángulos rotos `[]` en la tipografía por defecto de Kodi Estuary) sustituyéndolos por iconos nativos (`DefaultFolder.png`, `DefaultMovies.png`, `DefaultTVShows.png`, `DefaultGenre.png`, `DefaultYear.png`).
* **Manejo Seguro de Metadatos:** En `resources/lib/ui.py`, todas las llamadas a la API `VideoInfoTag` (`setPlot`, `setYear`, `setMediaType`, `setIMDBNumber`, `setRating`, `setGenres`) están protegidas con bloques `try/except` para garantizar que la interfaz procese e imprima siempre todos los elementos sin interrumpir la renderización del contenedor.
* **Firma Robusta de Finalización:** `ui.end_directory(handle, content_type, sort_methods, update_listing, cache_to_disc, succeeded)` soporta el parámetro `succeeded` evitando errores de ejecución `TypeError`.

---

## 6. Pautas para Futuros Cambios

1. **Evitar dependencias pesadas de Python:** Kodi se ejecuta en múltiples arquitecturas y sistemas limitados. Cualquier cliente HTTP debe usar preferiblemente `urllib.request` como motor primario, con fallbacks a `requests` y `curl` (usando `subprocess`).
2. **Preservar los motores locales:** El plugin debe permitir la resolución de torrents directos mediante magnet links hacia Elementum o Quasar de forma nativa cuando no hay cuentas Debrid configuradas.
3. **Mantenimiento del Generador:** No modifiques las carpetas empaquetadas dentro de `repository.sonvice/repo/` directamente; siempre modifícalas en la carpeta del addon original y vuelve a correr `generator.py`.

---

## 7. Roadmap de Futuras Mejoras Propuestas

1. **Filtro Avanzado de Audio (Castellano / Latino / VOSE):** Etiquetar visualmente en la lista de streams con banderas o distintivos `[ES-ES]` (Castellano), `[ES-LA]` (Latino) o `[VOSE]` (Subtitulado).
2. **Descarga de Subtítulos Automáticos (OpenSubtitles v3 / Subscene):** Descargar automáticamente subtítulos sincronizados en español si el torrent carece de pistas de subtítulos incrustadas.
3. **Integración Personal de Trakt.tv:** Mostrar las listas personales ("Ver más tarde", "Películas vistas", "Colección") directamente en el menú principal del addon.
4. **Reproducción de Trailers Oficiales de YouTube:** Añadir una opción en el menú contextual de cada película ("Ver Tráiler") para reproducir el avance oficial en YouTube antes de abrir los torrents.
5. **Soporte Multi-Debrid (AllDebrid / Premiumize):** Ampliar los conectores de Debrid para soportar AllDebrid y Premiumize.me junto con Real-Debrid.

