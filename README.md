# Stremio for Kodi (`plugin.video.stremio4kodi`)

[![Kodi Compatibility](https://img.shields.io/badge/Kodi-19%20|%2020%20|%2021%20(Matrix%20/%20Nexus%20/%20Omega)-blue.svg)](https://kodi.tv)
[![Version](https://img.shields.io/badge/version-v4.1.3-brightgreen.svg)](https://github.com/sonvice/stremio4kodi/releases)
[![Python Version](https://img.shields.io/badge/Python-3.0%2B-yellow.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-orange.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Android%20|%20CoreELEC%20|%20Linux%20|%20Windows%20|%20macOS-lightgrey.svg)](https://github.com/sonvice/stremio4kodi)

High-performance modular bridge between Stremio's decentralized ecosystem, Torznab indexers, P2P networks, and Kodi's native hardware playback engine.

Engineered in pure Python 3, 100% skin-agnostic, and optimized for both low-power TV devices (Fire TV Stick, Android TV, Smart TV Boxes) and dedicated media centers (NVIDIA Shield, Apple TV, PC, NAS).

---

[ English ](#english) | [ Español ](#español)

---

<a name="english"></a>
## English

### Table of Contents
1. [New Capabilities in Version 4](#new-capabilities-in-version-4)
2. [Supported Services and How to Take Advantage of Them](#supported-services-and-how-to-take-advantage-of-them)
3. [Didactic Installation Guide](#didactic-installation-guide)
4. [Update Guide and Troubleshooting](#update-guide-and-troubleshooting)
5. [Dual-Version Retention Policy](#dual-version-retention-policy)
6. [Quick 1-Minute Mobile Setup (QR Code)](#quick-1-minute-mobile-setup-qr-code)
7. [Recommended Performance Settings](#recommended-performance-settings)
8. [Frequently Asked Questions (FAQ)](#frequently-asked-questions-faq)

---

### New Capabilities in Version 4

#### 1. MediaCore Architecture (Unified Multimedia Orchestrator)
Instead of relying on a single source or protocol, version 4 introduces **MediaCore**, a layered orchestration engine that queries multiple sources in parallel:
* Community Stremio addons (Torrentio, Comet, MediaFusion).
* Torznab torrent indexers (Jackett and Prowlarr).
* Decentralized DHT scrapers.
* Live sports and AceStream broadcast channels.

MediaCore automatically deduplicates streams using the cryptographic `infoHash` and normalizes quality, audio tracks, and codecs into a clean, uniform list before presenting them on screen.

#### 2. Intelligent Scoring Engine & Spanish Booster
Incoming streams are analyzed by resolution, bitrate, and seed health, with priority weighting applied through the **Spanish Booster** algorithm:
* **Automatic Spanish Audio Priority (+3000 points):** Detects metadata flags (Castellano, Spanish, Dual, Multi, Latino), ranking these releases at the top of the stream list.
* **Configurable Filtering Modes:** Boost Mode (prioritizes Spanish audio while keeping original releases accessible) or Strict Mode (hides streams lacking a Spanish audio track).
* **Sanitized Release Titles:** Removes advertising tags, invalid glyphs, and spam words for a clean presentation on TV screens.

#### 3. Modern Home & Content Hub (100% Skin-Agnostic)
* **Unified Streaming Hub:** Consolidates key content shelves into a polished entry menu:
  * Continue Watching (exact playback resumption from local or Trakt timestamps).
  * Today's Trending Movies and TV Shows.
  * Featured Releases in Spanish.
  * Streaming Platforms (Netflix, Disney+, Prime Video, HBO Max, Apple TV+, etc.) mapped directly without exposing technical addon directories.
  * Weekly Top 10 and Universal DHT Search.
* **Universal Kodi Skin Compatibility:** Works natively on Kodi's default skin (**Estuary**) and exports native widgets (`plugin://plugin.video.stremio4kodi/?action=home`) to advanced skins such as **Arctic Fuse**, **AH2**, **Titan**, and **Nimbus**.

#### 4. Ephemeral Mobile Setup via QR Code & Local Web UI
Entering long API tokens and URLs using a TV remote control is tedious and prone to mistakes. Stremio4Kodi implements an ephemeral local web service:
* Generates an on-screen QR code in pure Python using an RGBA PNG raster without binary dependencies.
* Scanning the QR code with any mobile camera opens a responsive local Web UI on your smartphone.
* Paste Real-Debrid API keys, Comet URLs, or Torznab credentials in seconds.
* Tap **Guardar Cambios (Save Changes)** to apply settings in real-time, or **Terminar y Cerrar TV (Finish & Close TV)** to dismiss the dialog on your television and immediately shut down the local web server.

#### 5. Free Integrated OpenSubtitles v3
A native subtitle service that queries OpenSubtitles v3 REST endpoints on playback start. It requires zero accounts, zero passwords, and zero API keys; matched subtitles in Spanish and English are downloaded and synchronized automatically.

---

### Supported Services and How to Take Advantage of Them

| Category | Service | How to Maximize Its Value |
| :--- | :--- | :--- |
| **Debrid Providers** | **Real-Debrid**, **TorBox**, **AllDebrid**, **Premiumize.me**, **Debrid-Link** | Converts torrent hashes into high-speed direct HTTPS cloud streams (CDN). Playback starts instantly with high bitrates (>60 Mbps) in 4K UHD without seeding or exposing your personal IP on P2P networks. |
| **Torrent Engines** | **TorrServer MatriX** | Streams torrents using a circular buffer strictly in **RAM**, preventing eMMC flash storage degradation on FireSticks and TV Boxes. TorrServer can also be run on a local PC/NAS (e.g., `192.168.1.50:8090`) to offload network connections and deliver a pristine HTTP stream to the TV. |
| **Torrent Engines** | **Elementum** | Native disk-caching torrent engine with self-healing architecture binaries. Useful as an automatic fallback if neither Debrid nor TorrServer is available. |
| **Indexer Bridge** | **Torznab (Prowlarr / Jackett)** | Centralizes dozens of public and private torrent trackers (including Spanish trackers like DonTorrent). MediaCore queries these trackers concurrently and sends matching files to Real-Debrid or TorrServer seamlessly. |
| **Stremio Sources** | **Torrentio, Comet, MediaFusion** | Provides access to decentralized community catalogs. You can paste your custom Comet manifest URL to apply personalized size limits, resolutions, and provider sorting. |
| **Live Sports** | **AceStream (Horus / AceWeb)** | Direct playback of live P2P sports events with built-in DNS-over-HTTPS (DoH) bypassing ISP censorship blocks at the socket level. |
| **Metadata & Catalogs** | **The Movie Database (TMDB)** | Supplies synopsis in Spanish/English, Rotten Tomatoes and IMDb ratings, high-definition posters, and platform release listings. |
| **Watchlist Tracking** | **Trakt.tv & Simkl** | Synchronizes playback history, watchlist status, and resume checkpoints across all your devices. |

---

### Didactic Installation Guide

#### Critical Technical Note: Why You Must Install the Repository First
Kodi's Virtual File System (`zip://https://...`) is not a traditional download manager. Attempting to install a complex addon directly from a remote ZIP URL causes Kodi to issue hundreds of partial HTTP Range requests to inspect individual subdirectories. On Android TV, Fire TV Stick, and CoreELEC devices, this saturates open socket limits and causes Kodi to fail with:
```text
Failed to unpack archive
```

**The Correct and Universal Method:** Always install the lightweight repository package first (`repository.sonvice-X.X.X.zip`, under 30 KB, 2 files). Once the repository is installed:
1. Kodi downloads the complete package directly to local storage (`special://home/addons/packages/`).
2. Extraction happens locally at maximum bus speed without network bottlenecks.
3. Automatic background updates are permanently enabled.

---

#### Step-by-Step Installation Procedure

##### Step 1: Enable Unknown Sources in Kodi
1. Open Kodi and navigate to **Settings** (gear icon on the top-left).
2. Select **System** and click the **Add-ons** tab on the left panel.
3. Toggle on **Unknown sources**.
4. Confirm the security warning prompt by selecting **Yes**.

##### Step 2: Add the Sonvice File Source
1. Return to the **Settings** menu and select **File manager**.
2. Select **Add source**.
3. Click on `<None>` and enter the exact URL:
   ```text
   https://sonvice.github.io/repository.sonvice/
   ```
4. Enter a recognizable name in the field below, for example:
   ```text
   Sonvice Repo
   ```
5. Click **OK** to register the source.

##### Step 3: Install the Official Repository
1. Return to Kodi's home screen and select **Add-ons**.
2. Click the open box icon on the top-left (**Add-on browser**).
3. Select **Install from zip file**.
4. Choose **Sonvice Repo**.
5. Select the repository package:
   ```text
   repository.sonvice-1.0.11.zip
   ```
6. Wait a few moments until you see the notification: **Sonvice Repository Add-on installed**.

##### Step 4: Install Stremio for Kodi
1. In the same Add-on browser menu, select **Install from repository**.
2. Choose **Sonvice Repository**.
3. Open **Video add-ons**.
4. Select **Stremio for Kodi** and click the **Install** button on the bottom-right.
5. If Kodi prompts with a list of required dependencies, click **OK** to confirm.

---

### Update Guide and Troubleshooting

#### Symptom: Kodi indicates the repository is installed but does not show the v4 update or stays on the older version
Kodi caches add-on repository listings in a local SQLite database (`Addons33.db`) to minimize server traffic. By default, Kodi only checks for repository updates once every 24 hours.

#### Solution: Force an Immediate Manual Update Check
1. In Kodi, go to **Add-ons** ➔ **Install from repository**.
2. Highlight **Sonvice Repository** (do not click to enter).
3. Open the **Context Menu**:
   * TV Remote / FireStick: Long-press the OK/Center button or press the Menu button (three horizontal lines).
   * PC / Mac: Right-click with your mouse or press the `C` key on your keyboard.
   * Touchscreen (Phone/Tablet): Press and hold on the repository name.
4. From the popup menu, select **Check for updates**.
5. Kodi will immediately contact the CDN, download the newest `addons.xml`, and update the addon to the latest version.

---

### Dual-Version Retention Policy

The repository deliberately maintains **only two versions** of Stremio for Kodi:

1. **Latest Stable Version (`v4.1.x` - Recommended):**
   * Features MediaCore architecture, Modern Home, Spanish Booster, QR Mobile Setup, and widget exports.
2. **Classic / Legacy Version (`v3.7.33`):**
   * Lightweight monolithic version without modular subpackages, preserved for low-spec legacy hardware or users who prefer direct Stremio menu navigation.

---

### Quick 1-Minute Mobile Setup (QR Code)

1. Open **Stremio for Kodi** and select:
   ```text
   Configurar desde el Movil (QR)
   ```
2. Verify that your smartphone is connected to the **same local Wi-Fi network** as Kodi.
3. Open your mobile phone's camera and point it at the QR code displayed on the TV.
4. On the mobile Web UI that opens:
   * **Debrid & P2P:** Paste your Real-Debrid API Token (or TorrServer / TorBox credentials).
   * **Stremio & Comet:** Enter your custom manifest URL.
   * **Torznab:** Enter your Prowlarr or Jackett URL and API Key.
   * **Audio & Filters:** Configure your language priorities.
5. Tap **Guardar Cambios (Save Changes)** to confirm that settings are saved (a green confirmation badge appears on both phone and TV).
6. Tap **Terminar y Cerrar TV (Finish & Close TV)**; the TV dialog closes and the local web server shuts down cleanly.

---

### Recommended Performance Settings

Optimal parameters for TorrServer web UI (`http://localhost:8090` or `http://YOUR_PC_IP:8090`):

| Parameter | Low-End Device (FireStick / TV Box) | PC / Server / NAS | Purpose |
| :--- | :--- | :--- | :--- |
| **Cache size (RAM)** | `100 MB - 150 MB` | `500 MB - 1024 MB` | Ring buffer in system RAM for video chunks. |
| **Preload cache** | `5% - 8%` | `10% - 15%` | Pre-buffer percentage before initiating video playback. |
| **Torrents connect limit** | `20 - 30` | `60 - 100` | Peer connection cap to protect home routers from socket exhaustion. |
| **Save to database** | Disabled | Disabled | Ensures zero disk writes; 100% volatile in RAM. |

---

### Frequently Asked Questions (FAQ)

> [!NOTE]
> **1. What is the difference between Real-Debrid and TorrServer?**
> * **Real-Debrid** is a paid third-party service that downloads torrents to high-speed cloud servers. Playback is served via direct HTTPS downloads without local P2P uploading or seeding.
> * **TorrServer** is a free, open-source application that handles torrent connections locally, caching video chunks in RAM without writing to internal flash storage.

> [!NOTE]
> **2. Why are emojis strictly avoided in addon menus and dialogs?**
> Standard font tables in Kodi on CoreELEC, Android TV, and LibreELEC lack emoji glyphs, resulting in broken rectangles or missing characters. Stremio4Kodi relies exclusively on native Kodi icons (`DefaultX.png`) for uniform, professional rendering.

> [!NOTE]
> **3. How does the integrated OpenSubtitles v3 work?**
> The addon connects directly to OpenSubtitles v3 public REST endpoints, matching the IMDb ID and video duration to automatically download clean, synchronized subtitles in Spanish and English without user registration or API keys.

---

<a name="español"></a>
## Español

### Indice de Contenidos
1. [Nuevas Funcionalidades de la Version 4](#nuevas-funcionalidades-de-la-version-4-es)
2. [Servicios Compatibles y Como Sacarles Provecho](#servicios-compatibles-y-como-sacarles-provecho-es)
3. [Guia Didactica de Instalacion](#guia-didactica-de-instalacion-es)
4. [Guia de Actualizacion y Resolucion de Problemas](#guia-de-actualizacion-y-resolucion-de-problemas-es)
5. [Politica de Retencion de Versiones (Dual-Version)](#politica-de-retencion-de-versiones-dual-version-es)
6. [Configuracion Rapida en 1 Minuto (Codigo QR)](#configuracion-rapida-en-1-minuto-codigo-qr-es)
7. [Ajustes de Rendimiento Recomendados](#ajustes-de-rendimiento-recomendados-es)
8. [Preguntas Frecuentes (FAQ)](#preguntas-frecuentes-faq-es)

---

<a name="nuevas-funcionalidades-de-la-version-4-es"></a>
### Nuevas Funcionalidades de la Version 4

#### 1. Arquitectura MediaCore (Orquestador Multimedia Unificado)
En lugar de depender exclusivamente de un solo proveedor o protocolo, la version 4 incorpora **MediaCore**, un nucleo de orquestacion en capas que consulta en paralelo multiples origenes:
* Addons comunitarios de Stremio (Torrentio, Comet, MediaFusion).
* Indexadores de torrents Torznab (Jackett y Prowlarr).
* Redes DHT descentralizadas.
* Emisiones deportivas y canales en directo mediante AceStream.

MediaCore desduplica resultados automaticamente comparando el identificador hash (`infoHash`) y normaliza la informacion de calidad, codecs y pistas de audio en una estructura uniforme antes de presentarla en pantalla.

#### 2. Motor de Puntuacion Inteligente y Spanish Booster
El sistema clasifica las versiones encontradas en funcion de la resolucion, tasa de bits y salud de la fuente, aplicando de forma preferente el algoritmo **Spanish Booster**:
* **Prioridad automatica al audio en espanol (+3000 puntos):** Analiza etiquetas de metadatos como Castellano, Espanol, Dual, Multi y Latino, posicionando estos enlaces en los primeros lugares de la lista.
* **Modos de filtrado configurables:** Modo Priorizar (los ubica al principio pero conserva versiones originales) o Modo Estricto (oculta cualquier enlace que no incluya pista en espanol).
* **Limpieza de nombres y glifos:** Elimina caracteres residuales, etiquetas publicitarias y caracteres ilegibles para asegurar una lectura limpia en televisores.

#### 3. Home Moderna y Hub de Contenidos (100% Skin-Agnostic)
* **Acceso visual unificado:** La pantalla principal agrupa colecciones de alta demanda:
  * Seguir Viendo (recuperacion de punto de reproduccion guardado).
  * Tendencias de Hoy en Cine y Television.
  * Estrenos Destacados en Espanol.
  * Plataformas de Streaming (Netflix, Disney+, Prime Video, HBO Max, Apple TV+, etc.) organizadas directamente sin exponer carpetas tecnicas.
  * Top 10 Semanal y Buscador Universal.
* **Compatibilidad Universal con Skins de Kodi:** Funciona de forma fluida sobre la interfaz estandar de Kodi (**Estuary**) y permite exportar Widgets nativos (`plugin://plugin.video.stremio4kodi/?action=home`) a skins avanzados como **Arctic Fuse**, **AH2**, **Titan** o **Nimbus**.

#### 4. Configuracion Movil via Codigo QR y Web UI Local
Configurar credenciales complejas con el mando a distancia es lento y propenso a errores. Stremio4Kodi implementa un servicio web efimero que se ejecuta en la red local:
* Muestra en pantalla un codigo QR generado en Python puro mediante mapa de bits PNG sin dependencias externas.
* El usuario escanea el codigo con la camara del telefono movil y se abre una aplicacion web local y responsiva.
* Permite pegar tokens de Real-Debrid, URLs de Comet o claves Torznab en segundos.
* Al pulsar **Guardar Cambios**, los ajustes se sincronizan en Kodi en tiempo real; al pulsar **Terminar y Cerrar TV**, la ventana modal se cierra automaticamente y el servidor web se apaga sin consumir memoria ni mantener puertos abiertos.

#### 5. Subtitulos Gratuitos OpenSubtitles v3 Integrados
Modulo nativo que consulta directamente los servicios REST de OpenSubtitles v3 al inicio de la reproduccion. No requiere registro de cuentas, contraseñas ni claves de pago; los subtitulos en espanol e ingles se descargan de forma instantanea y sincronizada.

---

<a name="servicios-compatibles-y-como-sacarles-provecho-es"></a>
### Servicios Compatibles y Como Sacarles Provecho

| Categoria | Servicio | Como aprovecharlo al maximo |
| :--- | :--- | :--- |
| **Proveedores Debrid** | **Real-Debrid**, **TorBox**, **AllDebrid**, **Premiumize.me**, **Debrid-Link** | Convierte los enlaces torrent en transmisiones de descarga directa de alta velocidad (CDN). Permite reproducir archivos 4K UHD con tasas de bits elevadas (>60 Mbps) sin depender del numero de semillas ni exponer tu direccion IP en redes P2P. |
| **Motores Torrent P2P** | **TorrServer MatriX** | Transmite torrents directamente utilizando un bufer circular en la **memoria RAM**, sin escribir en el almacenamiento interno ni desgastar las memorias flash de televisores o FireSticks. Permite delegar la ejecucion de TorrServer a un PC o NAS local (ej. `192.168.1.50:8090`), transmitiendo solo el flujo de video limpio por red interna. |
| **Motores Torrent P2P** | **Elementum** | Motor torrent nativo que funciona de forma autonoma en disco con recuperacion automatica de dependencias. Ideal como respaldo si no se dispone de TorrServer o Debrid. |
| **Indexadores Privados/Locales**| **Torznab (Prowlarr / Jackett)** | Permite buscar simultaneamente en docenas de trackers publicos y trackers privados especializados (incluyendo trackers espanoles como DonTorrent). MediaCore consulta estos trackers en paralelo y envia el archivo a Real-Debrid o TorrServer de forma transparente. |
| **Fuentes Stremio y Comet** | **Torrentio, Comet, MediaFusion** | Acceso a las bases de datos mundiales de enlaces Stremio. Puedes introducir tu URL privada de manifest de Comet para aplicar tus propios filtros de tamano, resolucion y orden de proveedores. |
| **Transmisiones en Vivo** | **AceStream (Horus / AceWeb)** | Reproduccion directa de eventos deportivos y canales P2P en directo con bypass DNS-over-HTTPS (DoH) integrado hacia Cloudflare y Google, evitando los bloqueos de operadoras a nivel de socket. |
| **Metadatos y Seguimiento** | **The Movie Database (TMDB)** | Proporciona fichas tecnicas, puntuaciones de Rotten Tomatoes e IMDb, sinopsis en espanol, posters en alta definicion y catalogos actualizados. |
| **Seguimiento de Series** | **Trakt.tv / Simkl** | Sincronizacion del historial de reproduccion y marcado automatico de capitulos vistos. |

---

<a name="guia-didactica-de-instalacion-es"></a>
### Guia Didactica de Instalacion

#### Advertencia Tecnica Critica: Por que instalar siempre el Repositorio primero
El motor de archivos remotos de Kodi (`zip://https://...`) no es un gestor de descargas convencional. Si se intenta instalar un archivo ZIP pesado (>50 archivos) directamente desde una direccion web remota, Kodi realiza cientos de peticiones HTTP parciales (Range Requests) para leer individualmente cada carpeta, lo que en Android TV, FireStick o CoreELEC satura la conexion y arroja el error:
```text
Fallo al descomprimir el archivo (Failed to unpack archive)
```

**El metodo correcto y universal:** Se instala primero el archivo ligero del repositorio (`repository.sonvice-X.X.X.zip`, pesa menos de 30 KB y contiene solo 2 ficheros). Una vez instalado el repositorio, Kodi descarga el archivo completo a su almacenamiento temporal local y lo descomprime a maxima velocidad, garantizando ademas las **actualizaciones automaticas**.

---

#### Proceso de Instalacion Paso a Paso

##### Paso 1: Habilitar Origenes Desconocidos en Kodi
1. Inicia Kodi y entra en **Ajustes** (icono de rueda dentada en la esquina superior izquierda).
2. Selecciona **Sistema** y entra en la seccion **Add-ons**.
3. Activa la opcion **Origenes desconocidos**.
4. Aparecera un mensaje de confirmacion; pulsa **Si**.

##### Paso 2: Anadir la Fuente Web de Sonvice
1. En el menu de **Ajustes**, entra en **Explorador de archivos**.
2. Haz doble clic o pulsa en **Anadir fuente**.
3. Haz clic sobre el recuadro que indica `<Ninguno>`.
4. Escribe con precision la siguiente direccion URL:
   ```text
   https://sonvice.github.io/repository.sonvice/
   ```
5. En el campo de nombre inferior, introduce un nombre facil de identificar, por ejemplo:
   ```text
   Sonvice Repo
   ```
6. Pulsa **OK** para guardar la fuente.

##### Paso 3: Instalar el Repositorio Oficial
1. Vuelve a la pantalla principal de Kodi y entra en el menu **Add-ons**.
2. Haz clic en el icono de la caja abierta situado arriba a la izquierda (**Explorador de complementos**).
3. Selecciona la opcion **Instalar desde un archivo .zip**.
4. En la lista de ubicaciones, selecciona **Sonvice Repo**.
5. Haz clic sobre el archivo del repositorio:
   ```text
   repository.sonvice-1.0.11.zip
   ```
6. Espera unos segundos hasta que aparezca la notificacion en pantalla indicando que **Sonvice Repository se ha instalado correctamente**.

##### Paso 4: Instalar Stremio for Kodi
1. Dentro del mismo Explorador de complementos, selecciona **Instalar desde repositorio**.
2. Elige **Sonvice Repository**.
3. Entra en la categoria **Complementos para video**.
4. Haz clic en **Stremio for Kodi** y pulsa el boton **Instalar** (abajo a la derecha).
5. Si Kodi muestra una lista de dependencias adicionales necesarias, pulsa **OK** para confirmar la instalacion.

---

<a name="guia-de-actualizacion-y-resolucion-de-problemas-es"></a>
### Guia de Actualizacion y Resolucion de Problemas

#### Problema: Kodi indica que el repositorio esta instalado pero no muestra la actualizacion a la version 4
Kodi mantiene una base de datos local en SQLite (`Addons33.db`) donde guarda en cache la lista de versiones para no saturar los servidores. De forma predeterminada, Kodi comprueba si hay novedades una vez cada 24 horas, lo que puede provocar que no veas la nueva version de forma inmediata.

#### Solucion: Forzar la Comprobacion Manual de Actualizaciones
1. En Kodi, dirigete a **Add-ons** ➔ **Instalar desde repositorio**.
2. Colocate sobre **Sonvice Repository** (sin hacer clic para entrar).
3. Abre el **Menu contextual**:
   * En mando a distancia de televisor: Manten pulsado el boton central o pulsa el boton Menu (tres lineas horizontales).
   * En ordenador: Haz clic con el boton derecho del raton o pulsa la tecla `C`.
   * En pantalla tactil: Manten pulsado sobre el nombre del repositorio.
4. En el menu desplegable, selecciona **Comprobar actualizaciones** (Check for updates).
5. Kodi se conectara en ese instante al CDN de GitHub Pages, descargara el indice `addons.xml` mas reciente y actualizara el addon a la version actual de forma instantanea.

---

<a name="politica-de-retencion-de-versiones-dual-version-es"></a>
### Politica de Retencion de Versiones (Dual-Version)

El repositorio mantiene intencionadamente **unicamente dos versiones** de Stremio for Kodi:

1. **Ultima Version Estable (`v4.1.x` - Recomendada):**
   * Incluye la arquitectura MediaCore, la Home Moderna, el motor de puntuacion Spanish Booster, configuracion movil por QR y compatibilidad con widgets nativos.
2. **Version Antigua / Clasica (`v3.7.33`):**
   * Version monolitica clasica sin dependencias complejas, conservada permanentemente para dispositivos antiguos o usuarios que prefieran la interfaz tradicional de menus directos de Stremio.

---

<a name="configuracion-rapida-en-1-minuto-codigo-qr-es"></a>
### Configuracion Rapida en 1 Minuto (Codigo QR)

Para no perder tiempo escribiendo contraseñas largas con el mando de la television:

1. Abre **Stremio for Kodi** y pulsa en la opcion del menu:
   ```text
   Configurar desde el Movil (QR)
   ```
2. Asegurate de que tu telefono movil este conectado a la **misma red Wi-Fi** que tu Kodi.
3. Abre la camara o cualquier lector de codigos QR en tu movil y apunta a la pantalla del televisor.
4. Toca en el enlace que aparece para abrir la interfaz web de configuracion:
   * **Pestana Debrid & P2P:** Activa Real-Debrid y pega tu API Token (o credenciales de TorrServer / TorBox).
   * **Pestana Stremio & Comet:** Pega la URL de tu manifest si utilizas configuraciones privadas.
   * **Pestana Torznab:** Introduce la URL y API Key de tu servidor Prowlarr o Jackett.
   * **Pestana Audio & Filtros:** Ajusta si deseas priorizar o exigir audio en espanol.
5. Pulsa el boton **Guardar Cambios** para verificar que todo se guarda correctamente (veras la confirmacion en verde tanto en el movil como en la TV).
6. Pulsa **Terminar y Cerrar TV**; la ventana se cerrara en la television y el servidor web se apagara de forma automatica e instantanea.

---

<a name="ajustes-de-rendimiento-recomendados-es"></a>
### Ajustes de Rendimiento Recomendados

Para la configuracion de TorrServer (`http://localhost:8090` o `http://IP_DE_TU_PC:8090`):

| Parametro | Dispositivos Ligeros (Fire TV Stick / TV Box) | PC / Servidor / NAS | Proposito |
| :--- | :--- | :--- | :--- |
| **Cache size (RAM)** | `100 MB - 150 MB` | `500 MB - 1024 MB` | Bufer de memoria en RAM para los fragmentos de video. |
| **Preload cache** | `5% - 8%` | `10% - 15%` | Porcentaje de bufer previo antes de iniciar la reproduccion. |
| **Torrents connect limit** | `20 - 30` | `60 - 100` | Limite de conexiones simultaneas para proteger routers domesticos. |
| **Save to database** | Desactivado | Desactivado | Garantiza cero escrituras en memoria flash; 100% volatil en RAM. |

---

<a name="preguntas-frecuentes-faq-es"></a>
### Preguntas Frecuentes (FAQ)

> [!NOTE]
> **1. ¿Que diferencia hay entre usar Real-Debrid o TorrServer?**
> * **Real-Debrid** es un servicio de pago externo que descarga los torrents en sus servidores en la nube de alta velocidad. Cuando reproduces una pelicula, la recibes por descarga directa mediante protocolo HTTPS sin hacer P2P y sin consumir tu ancho de banda de subida.
> * **TorrServer** es una herramienta gratuita y de codigo abierto que gestiona las conexiones torrent directamente en tu red domestica, almacenando el video temporalmente en la memoria RAM de tu dispositivo sin tocar el almacenamiento interno.

> [!NOTE]
> **2. ¿Por que el addon no contiene emojis en sus menus?**
> Las fuentes tipograficas estandar de Kodi en sistemas como Android TV, CoreELEC y LibreELEC no incluyen glifos de emojis en sus tablas de caracteres TrueType, provocando que se rendericen rectangulos vacios o simbolos rotos. Stremio4Kodi utiliza exclusivamente iconos nativos del sistema para asegurar una apariencia visual uniforme y profesional en cualquier plataforma.

> [!NOTE]
> **3. ¿Como funcionan los subtitulos de OpenSubtitles v3?**
> El addon se comunica directamente con la interfaz REST publica de OpenSubtitles v3, emparejando la duracion y el identificador IMDb de la pelicula o capitulo para descargar los subtitulos coincidentes en idioma espanol sin requerir cuentas de usuario ni claves comerciales.

---

## License / Licencia

Distributed under the open-source **MIT License**. See `LICENSE` for more information.
