# AGENTS.md — Guía para Agentes de Codificación

Este archivo proporciona contexto e instrucciones técnicas para que los agentes de IA (como Antigravity, Claude, etc.) entiendan la arquitectura del proyecto y puedan trabajar en él de forma segura y eficiente.

---

## 1. Contexto del Proyecto

* **Nombre del Addon:** Stremio for Kodi (`plugin.video.stremio4kodi`)
* **Propósito:** Cliente ligero para Kodi que consume la API de addons de Stremio. Permite listar catálogos y reproducir contenido mediante motores de torrents o cuentas Debrid.
* **Lenguaje:** Python 3 (compatible con la API de Kodi Python 3.0.0+).
* **Dependencias de Kodi:** `xbmc.python`, `xbmc.addon`, `script.module.requests`.

---

## ⚠️ REGLA ESTRICTA DE INTERFAZ: PROHIBICIÓN ABSOLUTA DE EMOJIS (Iconos Nativos Únicamente)

> [!IMPORTANT]
> **EL ADDON/PLUGIN NO DEBE CONTENER EMOJIS BAJO NINGUNA CIRCUNSTANCIA.**
> Queda terminantemente prohibido insertar caracteres emoji Unicode (ej: 🏠, ⚡, 🎬, 🔥, 📺, 🍿, 🇪🇸, 🏆, 🔍, ⚙️, etc.) en etiquetas de menús (`label`), diálogos, notificaciones o archivos `settings.xml`.
> 
> * **Motivo técnico:** Las fuentes tipográficas estándar de Kodi (Estuary, CoreELEC, Android TV, LibreELEC) no incluyen glifos de emojis en sus tablas TTF y renderizan rectángulos rotos o caracteres basura vacíos (`[]` / ``).
> * **Solución obligatoria:** Si es necesario aportar riqueza visual a una entrada, se deben utilizar **únicamente iconos nativos de Kodi** mediante el parámetro `icon="DefaultX.png"`.
>   * Carpetas generales: `DefaultFolder.png`
>   * Películas: `DefaultMovies.png`
>   * Series: `DefaultTVShows.png`
>   * Seguir viendo / En progreso: `DefaultInProgressShows.png`
>   * Recientes / Novedades: `DefaultRecentlyAddedMovies.png` / `DefaultRecentlyAddedEpisodes.png`
>   * Plataformas y Estudios: `DefaultStudios.png`
>   * Ajustes / Programas: `DefaultAddonProgram.png`
>   * Búsqueda: `DefaultAddonsSearch.png`
>   * Géneros: `DefaultGenre.png`
>   * Años: `DefaultYear.png`
>   * Red / Magnets: `DefaultNetwork.png`
>   * Favoritos: `DefaultFavourites.png`

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

## 6. Arquitectura de Motores de Reproducción Torrent (v3.7.11 - v3.7.12)

### 6.1. Integración con TorrServer MatriX (Streaming Desacoplado en RAM)
* **Objetivo:** Permitir reproducir torrents directamente sin almacenar gigabytes en el almacenamiento flash/SSD del dispositivo cliente (como TVs, CoreELEC o Android TV), evitando el desgaste de memoria interna y optimizando el ancho de banda.
* **Archivos clave:** [`torrent.py`](file:///home/wilson/Pictures/plugin.video.stremio4kodi_v3.2.3/plugin.video.stremio4kodi/resources/lib/torrent.py), [`config.py`](file:///home/wilson/Pictures/plugin.video.stremio4kodi_v3.2.3/plugin.video.stremio4kodi/resources/lib/config.py), [`settings.xml`](file:///home/wilson/Pictures/plugin.video.stremio4kodi_v3.2.3/plugin.video.stremio4kodi/resources/settings.xml).
* **Mecanismo de Streaming:**
  * Endpoint HTTP directo de TorrServer:
    `http://{host}:{port}/stream/{clean_name}?link={quote(uri)}&index={best_id}&play`
  * Selección inteligente de archivo: Consulta la API interna `POST /torrents` con `{action: "get", hash: info_hash}` para inspeccionar `file_stats`.
    * En series: mapea el `file_idx` bencode (0-based) al ID de TorrServer (`id = file_stats[file_idx]["id"]` o `file_idx + 1`).
    * En películas sin índice: selecciona automáticamente el archivo de vídeo más pesado (`max(length)` excluyendo archivos `.nfo`, `.srt`, `.sample`).
  * Autenticación HTTP básica opcional (`Authorization: Basic ...` y `http://user:pass@host:port/...`).
* **Servicio Host en PC:**
  * Binario: `TorrServer-linux-amd64` (MatriX.147.1) ubicado en `~/.local/bin/torrserver`.
  * Servicio systemd: Administrado como servicio de usuario en `~/.config/systemd/user/torrserver.service`.
  * Puerto por defecto: `8090` (escucha en `0.0.0.0`, permitiendo acceso tanto local `127.0.0.1` como por red local LAN `192.168.1.xxx`).
  * Interfaz Web de Monitoreo: Accesible opcionalmente en `http://localhost:8090` para consultar velocidad de descarga, peers y buffer en RAM en tiempo real.

### 6.2. Modo Inteligente "Auto" con Failover Silencioso
* **Jerarquía de Selección en Tiempo Real:**
  1. **Real-Debrid:** Si está habilitado y el hash/torrent se resuelve vía API debrid.
  2. **TorrServer:** Comprobación rápida ping vía `GET http://{host}:{port}/echo` con un timeout estricto de **0.6 segundos**.
  3. **Elementum:** Si el PC o host de TorrServer está apagado, en reposo (suspensión) o inaccesible, conmuta instantáneamente y en silencio a Elementum **sin mostrar ventanas de error ni detener la reproducción**.
  4. **Torrest:** Fallback adicional si Elementum tampoco estuviese disponible.
* **Auto-Heal de Elementum:**
  * Si el demonio Go de Elementum no responde en el puerto `65220` (por ejemplo, tras el arranque en frío de Kodi), la función `try_recover_elementum()` ejecuta un reinicio del addon a través de JSON-RPC de Kodi (`Addons.SetAddonEnabled` desactivando y reactivando `plugin.video.elementum`), esperando hasta 3.5s a que el puerto vuelva a responder antes de declarar el motor no disponible.

### 6.3. Reproducción Nativa Directa
* Cuando TorrServer o Elementum resuelven una URL HTTP directa (`http://...`), la reproducción se lanza mediante `xbmc.Player().play(playable_url, li)` inyectando un `ListItem` con metadatos completos (`VideoInfoTag`, `ResumePoint`, propiedades de ventana).
* Esto permite que los descargadores de subtítulos nativos de Kodi (y el módulo integrado OpenSubtitles v3) reconozcan el nombre del vídeo, temporada y capítulo sin depender de esquemas intermediarios `plugin://`.

---

## 7. Pautas para Futuros Cambios

1. **Evitar dependencias pesadas de Python:** Kodi se ejecuta en múltiples arquitecturas y sistemas limitados. Cualquier cliente HTTP debe usar preferiblemente `urllib.request` como motor primario, con fallbacks a `requests` y `curl` (usando `subprocess`).
2. **Preservar los motores locales y el Failover:** Mantener siempre el orden de prioridad en modo Auto y asegurar que las verificaciones de salud de los motores remotos nunca superen los 600ms para evitar bloqueos en la interfaz de Kodi.
3. **Mantenimiento del Generador:** No modifiques las carpetas empaquetadas dentro de `repository.sonvice/repo/` directamente; siempre modifícalas en la carpeta del addon original y vuelve a correr `generator.py`.
4. **Purga de CDN al publicar:** Al hacer `git push` en `repository.sonvice`, purgar siempre la caché de jsDelivr para `addons.xml` y `addons.xml.md5` para que los clientes Kodi reciban las actualizaciones al instante:
   ```bash
   curl -s "https://purge.jsdelivr.net/gh/sonvice/repository.sonvice@main/repo/addons.xml"
   curl -s "https://purge.jsdelivr.net/gh/sonvice/repository.sonvice@main/repo/addons.xml.md5"
   ```

---

## 8. Roadmap de Futuras Mejoras Propuestas

1. **Filtro Avanzado de Audio (Castellano / Latino / VOSE):** Etiquetar visualmente en la lista de streams con banderas o distintivos `[ES-ES]` (Castellano), `[ES-LA]` (Latino) o `[VOSE]` (Subtitulado).
2. **Descarga de Subtítulos Automáticos (OpenSubtitles v3 / Subscene):** Descargar automáticamente subtítulos sincronizados en español si el torrent carece de pistas de subtítulos incrustadas.
3. **Integración Personal de Trakt.tv:** Mostrar las listas personales ("Ver más tarde", "Películas vistas", "Colección") directamente en el menú principal del addon.
4. **Reproducción de Trailers Oficiales de YouTube:** Añadir una opción en el menú contextual de cada película ("Ver Tráiler") para reproducir el avance oficial en YouTube antes de abrir los torrents.
5. **Soporte Multi-Debrid (AllDebrid / Premiumize):** Ampliar los conectores de Debrid para soportar AllDebrid y Premiumize.me junto con Real-Debrid.

---

## 9. Características Añadidas en v3.7.13 - v3.7.19 (AceStream Zero-Lag, setResolvedUrl & Silent Cache Navigation)
* **Restauración Silenciosa de Listas sin Notificaciones Falsas (v3.7.19):** Al cortar o salir de una reproducción, Kodi refresca el contenedor desde la caché local en <10 ms. Se eliminó la notificación fija de "Cargando tendencias..." cuando los datos ya están en caché para evitar la falsa sensación de recarga por red.
* **Corrección Total del Falso Diálogo 'Failed to play' (v3.7.18):** Eliminado el fallo donde Kodi saltaba el canal como no reproducible (`Playlist Player: skipping unplayable item`) porque el addon terminaba el directorio antes de resolver. Ahora se usa la API oficial `xbmcplugin.setResolvedUrl(handle, True, li)` para una resolución perfecta sin diálogos fantasma de error mientras reproduce.
* **Eliminación Total de Pantalla Negra y Congelación al Salir (v3.7.18):** Retirado `inputstream.ffmpegdirect` en modo timeshift que bloqueaba el cierre del reproductor hasta 66 segundos en CoreELEC. Kodi ahora usa su reproductor nativo por hardware AMLogic que cierra y retorna al menú en 50 milisegundos.
* **Retorno a Motor AceStream Local Simple (v3.7.18):** Desactivada la delegación remota al PC para AceStream para mantener la arquitectura sencilla, directa y sin dependencias externas en la TV Box (`127.0.0.1:6878`).
* **Aislamiento Total de Lista Tradicional IPFS/M3U (v3.7.17):** La pesada lista IPFS ya no se descarga ni procesa al entrar al menú de AceStream. Se ha trasladado a una opción dedicada al final del menú (`📦 Canales Tradicionales (Lista IPFS / M3U)`), permitiendo una apertura 100% instantánea de las tendencias de fútbol y del buscador.
* **Módulo Híbrido Multifuente (`acestream_search.py`):** Integración simultánea de `search-ace.stream` (API REST JSON de alta velocidad) y `acestreamid.com` (scraping con reputación/votos comunitarios y fecha activa).
* **Bypass DNS Anti-Bloqueo (DoH):** Resolución transparente vía DNS-over-HTTPS (Cloudflare / Google) con fallback a Anycast IPs para sortear bloqueos de ISPs españolas a dominios de streaming P2P.
* **Tendencias de Fútbol y Deportes:** Submenú con canales ordenados por karma positivo (votos a favor vs votos en contra) y actividad reciente. Carga optimizada en paralelo (<1 segundo).
* **Buscador Interactivo AceStream:** Búsqueda en tiempo real de canales y eventos con limpieza automática de enlaces promocionales y spam.
* **Corrección de API Python 3 DialogProgress:** Eliminado el error `takes at most 2 arguments` en `DialogProgress.create` y `update`.
* **Renderizado Instantáneo de Menú:** Eliminado el cuello de botella donde `_acestream` bloqueaba el hilo principal de Kodi esperando la descarga de listas IPFS. Ahora el menú de AceStream abre en <10 ms.
* **Feedback Visual Inmediato y 60 FPS:** Diálogo de progreso P2P inmediato al pulsar canal (`DialogProgress`) y sustitución de llamadas bloqueantes `time.sleep` por `xbmc.sleep` para no congelar la interfaz ni los controles del mando.
* **Corrección de Diálogo 'Failed to play':** Eliminado el falso error modal en Kodi (`xbmcplugin.endOfDirectory(succeeded=True)`).
* **Conexión Inmediata a Peers (Anti-congestión):** Eliminado el bombardeo de 15 hilos concurrentes que saturaba el motor en segundo plano, permitiendo enganchar peers desde el primer clic.
* **Soporte de AceStream Host Remoto (Offload a PC):** Nuevo ajuste `acestream_host` que permite a televisores o FireSticks delegar el P2P pesado al PC (`192.168.1.xxx:6878`).
* **Protección contra Cortes en Vivo:** Inyección de propiedades `IsLive=true`, `http-reconnect=true` y soporte de `inputstream.ffmpegdirect` para evitar cierres repentinos por underflow o pausas en el enjambre P2P.

---

## 10. Corrección Crítica de Reproducción en Búfer 0.00% (v3.7.32)
* **Eliminación del Bloqueo Permanente a 0.00% (0 B / 0 B) en Elementum:** Diagnóstico y corrección del fallo en el motor `Elementum` donde la descarga permanecía a `0 kB/s` y `0 B / 0 B` indefinidamente al reproducir capítulos o paquetes multi-archivo debido a un bloqueo de prioridades de archivo en modo memoria (`IsMemoryStorage`).
* **Auto-configuración de Almacenamiento Seguro para Elementum:** `dependencies.py` ahora autoconfigura Elementum con `download_storage=0` (File), ruta temporal auto-creada (`special://temp/elementum_downloads/`), auto-eliminación de fragmentos al parar (`keep_files_playing=2`, `keep_files_finished=2`) y estrategia rápida de asignación (`download_file_strategy=0`).
* **Conmutación Inteligente a TorrServer (Fallback Automático):** Si Elementum no responde o su resolución falla, el addon conmuta automáticamente a TorrServer activo local (`127.0.0.1:8090`).
* **Prevención de Pausa Prematura en `service.py`:** El watchdog en segundo plano ya no pausa torrents en estado `Buffering` o `Downloading`.
* **Migración del Repositorio a GitHub Pages (CDN Fastly):** Actualización de los endpoints del repositorio en `repository.sonvice/addon.xml` hacia `https://sonvice.github.io/repository.sonvice/repo/` para evitar errores HTTP 403 Forbidden causados por políticas de cuota en jsDelivr.

---

## 11. Prioridad Predeterminada TorrServer y Fallback Instantáneo (<1s) a Elementum (v3.7.33)
* **TorrServer como Motor Prioritario por Defecto:** Se establece `TorrServer` como la primera opción en la lista de motores y el valor por defecto en `settings.xml` y `config.py`. Los dispositivos con recursos limitados (Android TV, FireStick, TV Boxes) obtienen reproducción inmediata en RAM sin consumo ni desgaste de almacenamiento flash.
* **Sonda Ultra-Rápida de Estado (<0.8s):** Rediseño de `is_engine_alive("TorrServer")` con un único socket probe optimizado (0.5s en localhost, 1.0s en red local LAN). Se eliminaron reintentos con sleep y peticiones urllib redundantes.
* **Conmutación Fluida en < 1 Segundo si TorrServer no está Activo:** Antes de enviar peticiones pesadas a la API de TorrServer, `resolve_torrserver_stream` ejecuta un chequeo previo ultrarrápido (<0.8s). Si TorrServer está apagado o no responde, el addon salta de inmediato a `Elementum` con la notificación `TorrServer no detectado. Usando Elementum...` en menos de 1 segundo (cumpliendo con creces la meta de <5 segundos).
* **Gestión Visual de Motores:** En `_manage_engines` ([router.py](file:///home/wilson/Pictures/plugin.video.stremio4kodi_v3.2.3/plugin.video.stremio4kodi/resources/lib/router.py)) ahora se muestra el estado en vivo de TorrServer (`Activo` o `No detectado`) con su host y puerto configurados.

---

## 12. MediaCore v4.0.0 — Arquitectura Orquestada Unificada (Inspirada en HolyArrs)
* **Arquitectura "One UI, One Media Core":** Desacoplamiento total del addon en módulos limpios dentro de `resources/lib/mediacore/`:
  * **`models.py`:** Contratos de dominio universales (`MediaItem`, `StreamRelease`, `PlaybackResult`).
  * **`playback/` (Playback Provider Hub):** Interfaz común `BasePlaybackProvider` implementada por `TorrServerProvider`, `DebridPlaybackProvider`, `ElementumProvider`, `AceStreamPlaybackProvider` y `DirectHttpProvider`. Pipeline de fallback inteligente con handoff inmediato (<1s) si TorrServer está apagado.
  * **`sources/` (Sources Hub):** Puente concurrente con `StremioSource` (Torrentio, Comet, MediaFusion), `DhtSource` (Apibay, Bitsearch), `LiveAceStreamSource` y el **nuevo `TorznabSource`**.
  * **Integración Nativa Torznab (Jackett & Prowlarr):** Soporte para indexadores privados y locales mediante la API XML estándar de Torznab. Configurable desde ajustes.
  * **`scoring/` (Scoring & Ranker Engine):** Normalización RTN automática, clasificación y filtrado de idioma español (Castellano, Latino, Dual, VOSE), bonificación Debrid en caché y **deduplicación limpia por `infoHash`** entre múltiples fuentes.
  * **`metadata/` (Metadata Hub):** Agregación de TMDB, Trakt, Cinemeta y Rotten Tomatoes (Tomatometer y Audience Score).
  * **`orchestrator.py` (`MediaCore`):** Orquestador central reutilizable que coordina la búsqueda, puntuación y reproducción multimedia.
  * **`router.py` Adelgazado:** Despachador de interfaz de usuario de Kodi desacoplado que delega la lógica de negocio al orquestador `MediaCore`.

---

## 13. Stremio4Kodi v4.1.0 — Home Moderna, Configuración Móvil vía QR y Unificación de Catálogos
* **Configuración Móvil por Código QR (Mobile Web Setup):**
  * **Servidor HTTP Local Efímero (`resources/lib/websetup/server.py`):** Levanta un servidor `ThreadingHTTPServer` en el puerto 52025 de la red local, asegurado con un token criptográfico efímero de sesión (`?k=token_urlsafe`).
  * **Generador Pure-Python de QR y PNG (`resources/lib/websetup/qr.py`):** Codificador PNG de 8 bits RGB sin dependencias binarias (usando `zlib` y `struct`), compatible universalmente con cualquier arquitectura de Kodi sin Pillow ni C++.
  * **Ventana Modal de Kodi (`resources/lib/websetup/dialog.py` y XMLs en `resources/skins/`):** Muestra el código QR en grande y la URL local en pantalla con monitoreo reactivo automático al recibir los ajustes guardados.
  * **Web UI Móvil Responsiva (`resources/lib/websetup/static/index.html`):** Interfaz táctil oscura tipo Glassmorphism para configurar cuentas Debrid (Real-Debrid, TorBox, AllDebrid, Premiumize), TorrServer, Stremio Manifests (Comet privado, Torrentio), Torznab y preferencias de audio en español sin teclear con el mando de la TV.
* **Eliminación Crítica de "Catálogos Stremio" y Rediseño de Plataformas:**
  * Supresión de la carpeta técnica `[B]Catalogos Stremio (Cinemeta / Addons)[/B]` al final de los menús de Películas y Series (evitando el antipatrón de fuga de abstracción técnica).
  * Creación de accesos directos de primer nivel: **"Plataformas (Netflix, HBO, Disney+...)"** y **"Colecciones y Sagas"** con metadatos y arte enriquecidos.
* **Home Moderna / Hub Principal de Streaming:**
  * Vista central unificada con estantes clave: *Seguir Viendo (En progreso)*, *Tendencias de Hoy (Películas)*, *Series Más Populares*, *Estrenos en Castellano*, *Plataformas de Streaming*, *Top 10 Semanal* y *Buscador Universal*.
* **Endpoints de Widgets para Skins de Kodi:**
  * Exposición de rutas de widgets nativos (`action=widget_continue`, `action=widget_trending_movies`, `action=widget_trending_shows`, `action=widget_spanish`, `action=widget_platforms`) para integración con skins como Estuary, Arctic Fuse, Titan y AH2.
* **Retención Multi-Versión en Repositorio (`repository.sonvice`):**
  * El repositorio conserva y lista simultáneamente `v4.1.0` (Última), `v4.0.0` (MediaCore base) y `v3.7.33` (Legacy Estable) en su `index.html` para el gestor de archivos de Kodi.




