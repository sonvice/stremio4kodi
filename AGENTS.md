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

## 3. Características Clave Añadidas en v3.2.4

### 3.1. Buscador DHT Descentralizado
* **Archivo del Cliente:** [dht_search.py](file:///home/wilson/Pictures/plugin.video.stremio4kodi_v3.2.3/plugin.video.stremio4kodi/resources/lib/dht_search.py)
* **API Utilizada:** `https://bitsearch.eu/api/v1/search` (Endpoint JSON público del crawler DHT Bitsearch).
* **Mecanismo:** Permite realizar búsquedas de texto directo en la DHT de Kademlia. Los resultados se devuelven formateados como objetos de flujo compatibles con `TorrentResolver`, permitiendo reproducir directamente a través de **Elementum/Quasar** o **Real-Debrid** con soporte de ordenación por semillas, filtrados de idioma y calidad automáticos.
* **Integración en Menú:** Añadido como ruta `dht_search` en [router.py](file:///home/wilson/Pictures/plugin.video.stremio4kodi_v3.2.3/plugin.video.stremio4kodi/resources/lib/router.py).

### 3.2. Repositorio con Espejo CDN (jsDelivr)
* **Objetivo:** Evitar que los bloqueos de ISPs locales al dominio `raw.githubusercontent.com` rompan las actualizaciones automáticas.
* **Mecanismo:** El archivo `addon.xml` del repositorio remoto utiliza URLs de la red de entrega de contenido (CDN) gratuita **jsDelivr** (apuntando a la rama `main` del repo de GitHub).

---

## 4. Pautas para Futuros Cambios

1. **Evitar dependencias pesadas de Python:** Kodi se ejecuta en múltiples arquitecturas y sistemas limitados. Cualquier cliente HTTP debe usar preferiblemente `requests` con un fallback a comandos del sistema como `curl` (usando `subprocess`).
2. **Preservar los motores locales:** El plugin debe permitir la resolución de torrents directos mediante magnet links hacia Elementum o Quasar de forma nativa cuando no hay cuentas Debrid configuradas.
3. **Mantenimiento del Generador:** No modifiques las carpetas empaquetadas dentro de `repository.sonvice/repo/` directamente; siempre modifícalas en la carpeta del addon original y vuelve a correr `generator.py`.
