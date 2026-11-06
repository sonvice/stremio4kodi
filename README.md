<div align="center">

# 🎬 Stremio for Kodi (`plugin.video.stremio4kodi`)

[![Kodi Compatibility](https://img.shields.io/badge/Kodi-19%20|%2020%20|%2021%20(Matrix%20/%20Nexus%20/%20Omega)-blue.svg)](https://kodi.tv)
[![Version](https://img.shields.io/badge/version-v3.7.28-brightgreen.svg)](https://github.com/sonvice/stremio4kodi/releases)
[![Python Version](https://img.shields.io/badge/Python-3.0%2B-yellow.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-orange.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Android%20|%20CoreELEC%20|%20Linux%20|%20Windows%20|%20macOS-lightgrey.svg)](https://github.com/sonvice/stremio4kodi)

**The ultimate bridge between Stremio's decentralized ecosystem and Kodi's native hardware playback engine.**  
Stream movies, TV shows, and live sports with **TorrServer**, **Elementum**, **Real-Debrid**, integrated **OpenSubtitles v3**, and a zero-lag **AceStream** sports center with DNS anti-censorship bypass.

---

[ 🇬🇧 **English** ](#-english) &nbsp; | &nbsp; [ 🇪🇸 **Español** ](#-español)

---

</div>

<a name="-english"></a>
## 🇬🇧 English

### 🌟 Key Highlights & Features

* **Decentralized Stremio Addon Protocol (v3):** Seamlessly loads catalogs, streams, and metadata from community Stremio addons (Cinemeta, CyberFlix, Torrentio, etc.) directly into Kodi's native user interface.
* **Smart Torrent Engines with RAM Buffering:**
  * **TorrServer MatriX:** High-speed streaming directly in **RAM**, preventing eMMC flash storage wear on TV Boxes, FireSticks, and Smart TVs. Supports PC/NAS remote offloading.
  * **Elementum:** Complete self-healing integration with automatic architecture binary repairs on Android, CoreELEC, and Linux.
  * **Silent Auto-Failover:** Automatically cascades: `Real-Debrid` ➔ `TorrServer` ➔ `Elementum` without disrupting playback.
* **Live AceStream Sports Center:**
  * **Real-Time Sports Trends:** Aggregates live football and sports broadcasts with community karma score voting (`+` / `-`).
  * **Anti-Blocking DNS-over-HTTPS (DoH):** Bypasses ISP censorship blocks (Cloudflare `1.1.1.1` and Google `8.8.8.8`) at the socket level.
  * **Zero-Lag Native Playback:** Instant `<10ms` menu navigation and silent cache restoration on stream exit.
* **Clean Bilingual Titles:** Displays original titles alongside accurate Spanish localized titles with sanitized unicode characters.
* **Free Built-in OpenSubtitles v3:** Automatic, zero-configuration subtitle search and download in multiple languages without needing an account or API key.
* **Hardware-Accelerated Playback:** Full AMLogic, Intel/AMD, NVIDIA Shield, and Apple VideoToolbox hardware decoding via Kodi's native player.

---

### 📥 Didactic Installation Guide

#### Option 1: Via Official Sonvice Repository (Recommended)
Installing via the repository ensures you automatically receive all future updates in the background:

1. **Enable Unknown Sources in Kodi:**
   * Open Kodi ➔ **Settings (⚙️)** ➔ **System** ➔ **Add-ons**.
   * Toggle on **Unknown sources** and confirm **Yes**.
2. **Add the Repository Source:**
   * Go to **Settings (⚙️)** ➔ **File manager** ➔ **Add source**.
   * Click `<None>` and enter:
     ```text
     https://sonvice.github.io/repository.sonvice/
     ```
   * Name the media source (e.g., `Sonvice Repo`) and select **OK**.
3. **Install the Repository:**
   * Return to Kodi Home ➔ **Add-ons** ➔ Click the **Open Box icon** (Add-on Browser).
   * Select **Install from zip file** ➔ Choose `Sonvice Repo` ➔ Select `repository.sonvice-1.0.10.zip`.
4. **Install Stremio for Kodi:**
   * Select **Install from repository** ➔ **Sonvice Repository**.
   * Open **Video add-ons** ➔ Select **Stremio for Kodi** ➔ Click **Install** and confirm dependencies.

#### Option 2: Direct ZIP Download
1. Download the latest release package:  
   👉 [**Download plugin.video.stremio4kodi-3.7.28.zip**](https://cdn.jsdelivr.net/gh/sonvice/repository.sonvice@main/repo/plugin.video.stremio4kodi/plugin.video.stremio4kodi-3.7.28.zip)
2. In Kodi, go to **Add-ons** ➔ **Add-on Browser** ➔ **Install from zip file** and select the downloaded file.

---

### 🚀 Quick Start & Usage

#### 1. Choosing Your Playback Engine
Navigate to **Add-ons** ➔ **Video add-ons** ➔ **Stremio for Kodi** ➔ **Settings** ➔ **General**:
* **TorrServer (Recommended for TV Boxes & FireSticks):** Streams torrents inside circular RAM cache without touching internal storage.
  * *Local TV/PC:* Set Host to `127.0.0.1`, Port `8090`.
  * *Remote PC/NAS Offloading:* Set Host to your PC's local IP (e.g., `192.168.1.xxx`), Port `8090`. Your PC handles the BitTorrent connections, sending a smooth HTTP stream to your TV.
* **Elementum:** Native built-in torrent engine with disk caching and automatic dependency repair.
* **Real-Debrid:** Enter your API token in the **Debrid** tab for instant cached streaming without P2P seeding.

#### 2. Browsing & Watching
* **Discover Catalogs:** Browse Popular, Trending, In Theaters, and Streaming Platforms (Netflix, HBO Max, Disney+, Prime Video, Apple TV+).
* **Instant Subtitles:** OpenSubtitles v3 fetches and loads matching subtitles on playback start automatically.
* **Live Sports:** Open **Live Sports (AceStream)** to browse verified matches with live peer counts and download speeds.

---

### ⚙️ Architecture & Recommended Performance Settings

For TorrServer web dashboard (`http://localhost:8090` or `http://192.168.1.xxx:8090`):

| Setting | Low-Spec Device (FireStick / TV Box) | PC / Server / NAS | Purpose |
| :--- | :--- | :--- | :--- |
| **Cache size (RAM)** | `100 MB - 150 MB` | `500 MB - 1024 MB` | Memory ring buffer for downloaded video chunks. |
| **Preload cache** | `5% - 10%` | `10% - 15%` | Buffer percentage before video starts playback. |
| **Torrents connect limit**| `20 - 30` | `50 - 100` | Peer connection limit to avoid router overload. |
| **Save to database** | Disabled | Disabled | Keeps disk writes zero; operates strictly in RAM. |

---

### ❓ Frequently Asked Questions (FAQ)

<details>
<summary><b>1. Why choose TorrServer over Elementum on TV Boxes?</b></summary>
Elementum writes torrent chunks to local storage. On devices with limited flash memory (8 GB FireSticks or Android TV boxes), this causes premature storage wear and out-of-space crashes. TorrServer operates 100% in volatile RAM.
</details>

<details>
<summary><b>2. How does the AceStream anti-censorship bypass work?</b></summary>
Many Spanish and European ISPs block P2P tracker domains via DNS manipulation. The addon injects a socket-level DNS resolver using DNS-over-HTTPS (DoH) querying Cloudflare (1.1.1.1) and Google (8.8.8.8), completely bypassing ISP DNS blocks.
</details>

<details>
<summary><b>3. Do I need an account for OpenSubtitles?</b></summary>
No. The addon integrates OpenSubtitles v3 with direct REST endpoints, downloading synchronized subtitles without requiring any account or API key.
</details>

---

<a name="-español"></a>
## 🇪🇸 Español

### 🌟 Características Principales

* **Protocolo de Addons de Stremio Descentralizado (v3):** Carga catálogos, enlaces y metadatos desde los addons comunitarios de Stremio (Cinemeta, CyberFlix, Torrentio, etc.) directamente en la interfaz nativa de Kodi.
* **Motores Torrent Inteligentes con Búfer en RAM:**
  * **TorrServer MatriX:** Transmisión directa en **memoria RAM**, protegiendo las memorias eMMC/flash de TV Boxes, FireSticks y televisores contra el desgaste. Permite delegar la carga pesada al PC/NAS doméstico.
  * **Elementum:** Integración con auto-recuperación integral y reparación automática de binarios según arquitectura en Android, CoreELEC y Linux.
  * **Failover Silencioso:** Conmutación jerárquica transparente: `Real-Debrid` ➔ `TorrServer` ➔ `Elementum` sin interrumpir la experiencia de usuario.
* **Centro Deportivo AceStream en Vivo:**
  * **Tendencias en Tiempo Real:** Agregación de partidos de fútbol y eventos deportivos con puntuación de reputación comunitaria (`+` / `-`).
  * **Bypass Anti-Bloqueo DNS-over-HTTPS (DoH):** Evasión de bloqueos de operadoras (Cloudflare `1.1.1.1` y Google `8.8.8.8`) a nivel de socket.
  * **Cero Retardos y 60 FPS:** Apertura de menús en `<10ms` y restauración silenciosa de listas al salir de la reproducción sin pantallas negras.
* **Títulos Bilingües Limpios:** Muestra el título original junto con su traducción al español con codificación de caracteres corregida sin errores unicode.
* **OpenSubtitles v3 Gratuito e Integrado:** Búsqueda y descarga automática de subtítulos en español e inglés sin requerir registro, cuentas ni claves API.
* **Aceleración por Hardware:** Soporte completo de decodificación por hardware en AMLogic, Intel/AMD, NVIDIA Shield y Apple VideoToolbox.

---

### 📥 Guía Didáctica de Instalación

#### Opción 1: Desde el Repositorio Oficial Sonvice (Recomendado)
Instalar desde el repositorio garantiza que recibirás todas las actualizaciones futuras de forma automática en segundo plano:

1. **Activar Orígenes Desconocidos en Kodi:**
   * Abre Kodi ➔ **Ajustes (⚙️)** ➔ **Sistema** ➔ **Add-ons**.
   * Activa la casilla **Orígenes desconocidos** y confirma con **Sí**.
2. **Añadir la Fuente del Repositorio:**
   * Ve a **Ajustes (⚙️)** ➔ **Explorador de archivos** ➔ **Añadir fuente**.
   * Haz clic sobre `<Ninguno>` y escribe exactamente:
     ```text
     https://sonvice.github.io/repository.sonvice/
     ```
   * Asigna un nombre a la fuente (por ejemplo: `Sonvice Repo`) y pulsa **OK**.
3. **Instalar el Repositorio:**
   * Vuelve al menú principal de Kodi ➔ **Add-ons** ➔ Haz clic en el **icono de la caja abierta** (Explorador de complementos).
   * Selecciona **Instalar desde un archivo .zip** ➔ Elige `Sonvice Repo` ➔ Selecciona `repository.sonvice-1.0.10.zip`.
4. **Instalar Stremio for Kodi:**
   * Selecciona **Instalar desde repositorio** ➔ **Sonvice Repository**.
   * Entra en **Complementos para vídeo** ➔ Selecciona **Stremio for Kodi** ➔ Pulsa **Instalar** y confirma dependencias.

#### Opción 2: Descarga Directa del archivo ZIP
1. Descarga el paquete de la última versión:  
   👉 [**Descargar plugin.video.stremio4kodi-3.7.28.zip**](https://cdn.jsdelivr.net/gh/sonvice/repository.sonvice@main/repo/plugin.video.stremio4kodi/plugin.video.stremio4kodi-3.7.28.zip)
2. En Kodi, ve a **Add-ons** ➔ **Explorador de complementos** ➔ **Instalar desde un archivo .zip** y selecciona el archivo descargado.

---

### 🚀 Inicio Rápido y Uso

#### 1. Selección del Motor de Reproducción
Ve a **Add-ons** ➔ **Add-ons de vídeo** ➔ **Stremio for Kodi** ➔ **Ajustes** ➔ **General**:
* **TorrServer (Recomendado en TV Box / FireStick):** Reproduce torrents en la memoria RAM sin degradar la memoria interna.
  * *Mismo televisor o PC local:* Servidor en `127.0.0.1`, Puerto `8090`.
  * *PC o Servidor Remoto:* Introduce la IP local de tu ordenador (ej: `192.168.1.xxx`), Puerto `8090`. Tu PC asume todas las conexiones torrent y envía un flujo HTTP limpio a la tele.
* **Elementum:** Motor torrent nativo integrado con soporte de reparación automática de arquitectura.
* **Real-Debrid:** Introduce tu token API en la pestaña **Debrid** para reproducción en la nube instantánea sin descargas P2P.

#### 2. Navegación y Reproducción
* **Explorar Catálogos:** Películas y series populares, en cartelera y filtrado por plataformas (Netflix, HBO Max, Disney+, Prime Video, Apple TV+).
* **Subtítulos Automáticos:** OpenSubtitles v3 detecta y sincroniza los subtítulos coincidentes al iniciar el vídeo.
* **Deportes en Vivo:** Entra en **Deportes en Directo (AceStream)** para explorar partidos verificados con conteo de peers y velocidad en tiempo real.

---

### ⚙️ Parámetros de Rendimiento Recomendados

Ajustes óptimos para la interfaz web de TorrServer (`http://localhost:8090` o `http://192.168.1.xxx:8090`):

| Parámetro | Dispositivo Modesto (TV Box / FireStick) | PC / Servidor / NAS | Función |
| :--- | :--- | :--- | :--- |
| **Cache size (Memoria RAM)** | `100 MB - 150 MB` | `500 MB - 1024 MB` | Búfer circular en RAM para los fragmentos de vídeo. |
| **Preload cache (Prebúfer)** | `5% - 10%` | `10% - 15%` | Porcentaje de búfer antes de arrancar el reproductor. |
| **Torrents connect limit** | `20 - 30` | `50 - 100` | Límite de conexiones para no saturar routers débiles. |
| **Save to database** | Desactivado | Desactivado | Cero escrituras en almacenamiento; 100% en RAM. |

---

### ❓ Preguntas Frecuentes (FAQ)

<details>
<summary><b>1. ¿Por qué es mejor TorrServer que Elementum en televisores?</b></summary>
Elementum escribe las partes del torrent en el almacenamiento interno. En dispositivos con memoria limitada (como Fire TV Sticks de 8 GB), esto satura el espacio y desgasta las memorias flash. TorrServer trabaja de forma 100% volátil en memoria RAM.
</details>

<details>
<summary><b>2. ¿Cómo funciona el bypass de bloqueo DNS para AceStream?</b></summary>
Las operadoras de telecomunicaciones bloquean dominios de streaming P2P modificando las respuestas DNS estándar. El addon integra un resolvedor interno DoH (DNS-over-HTTPS) que consulta a Cloudflare (1.1.1.1) y Google (8.8.8.8), evadiendo los bloqueos de forma totalmente transparente.
</details>

<details>
<summary><b>3. ¿Necesito una cuenta para los subtítulos?</b></summary>
No. El addon integra OpenSubtitles v3 mediante endpoints REST directos, descargando subtítulos limpios y sincronizados sin necesidad de usuario, contraseña ni clave API.
</details>

---

## 📄 License / Licencia

Distributed under the **MIT License**. See `LICENSE` for more information.
