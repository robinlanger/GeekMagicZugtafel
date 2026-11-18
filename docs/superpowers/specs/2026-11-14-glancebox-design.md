# Glance Box – Design

Stand: 2026-11-14 · Status: Entwurf zur Freigabe

> *Open firmware + server that turns the GeekMagic SmallTV Ultra into a tiny web display.*

## 1. Absicht und Warum

Das bestehende Repo `GeekMagicZugtafel` zeigt DB-Abfahrten auf einem GeekMagic SmallTV Ultra mit
**Originalfirmware**. Ein Docker-Container zeichnet jede Minute ein JPEG (Pillow) und lädt es per
`/doUpload` in den **Flash** des Geräts. Weil sich Uhrzeit und Countdown jede Minute ändern, wird
praktisch jede Minute Flash beschrieben, und der Inhalt ist auf das eine fest programmierte Layout
beschränkt.

Ziel ist ein **allgemeines, öffentliches Projekt**, das das Ultra zu einem kleinen Web-Display macht:

- Eine **eigene Firmware** holt sich fertig gerenderte Bilder vom Server und zeigt sie aus dem
  **RAM** an. Im Normalbetrieb wird der Flash nicht beschrieben.
- Ein **Server** (Docker) rendert beliebige, auf 240×240 optimierte Webseiten mit headless
  Chromium. Was angezeigt wird, steht in einer `config.yaml`: eine Playlist, die z. B. alle 30 s
  wechselt (Homelab-Status, Zugverbindungen, …).
- Inhalte entstehen über **einfache einzelne Skripte** (Python + HTML-Template). Die bestehende
  Zugtafel wird das erste Skript.
- Das Repo wird **öffentlich**. Deshalb muss alles gut dokumentiert (deutsch + englisch), mit CI
  abgesichert und reproduzierbar sein. **OTA-Updates dürfen so gut wie nie schiefgehen.**

Der Besitzer hat ein **Ultra (ESP8266)** und akzeptiert, dass die Originalfirmware danach
praktisch nicht wiederherstellbar ist (sie verlangt einen MAC-gebundenen Aktivierungscode) und
dass im schlimmsten Fall einmal seriell (mit Löten) geflasht werden muss.

## 2. Ziele, Nicht-Ziele, Anti-Ziele

**Ziele (v1)**

1. Firmware für das SmallTV Ultra: WLAN-Einrichtung per Captive Portal, Bilder vom Server holen
   und anzeigen, abgesichertes OTA, Notfallmodus.
2. Server: Playlist aus `config.yaml`, Seitentypen `url` und Skript-Seiten, Rendern per Chromium,
   Auslieferung als Baseline-JPEG.
3. Die Zugtafel als erste Skript-Seite (`bahn`), funktional gleichwertig zu heute.
4. CI für Firmware, Server und Doku, Releases mit festgepinnten Versionen.
5. Zweisprachige Doku (EN Haupt-README, DE gleichwertig) mit Anleitung zum ersten Flashen,
   Einrichtung, Konfiguration, eigenen Seiten und Notfall-Recovery.

**Nicht-Ziele (v1)**, bewusst später oder nie:

- Eigene Playlists pro Gerät (v1: eine Playlist für alle Geräte).
- SmallTV Pro (ESP32) oder andere Displays. Die Architektur soll es nicht verbauen, v1 testet nur das Ultra.
- Weiterbetrieb mit Originalfirmware (der bisherige Upload-Modus `device.py` entfällt).
- Animationen, Video, Touch/Interaktion.
- Server-initiierte (automatische) Firmware-Updates. v1: Update nur aktiv über die Geräte-Webseite
  oder das Smoketest-Skript.
- Authentifizierung am Server (v1 läuft im LAN, siehe Abschnitt 9).
- Home-Assistant-Integration.

**Anti-Ziele**, die das Projekt trotz funktionierendem Code zum Fehlschlag machen würden:

- Ein OTA-Update bricked ein Gerät so, dass es nur noch seriell zu retten ist.
- Die Firmware schreibt im Normalbetrieb Flash (Ausnahmen: WLAN-/Einstellungen speichern, OTA).
- Das Gerät braucht Internet oder eine Cloud. Es redet nur mit dem eigenen Server im LAN.
- Für Fremde nicht nachbaubar: undokumentierte Schritte, ungepinnte Toolchains, „funktioniert nur bei mir“.
- Eine kaputte Seite führt zu schwarzem Bildschirm statt übersprungen zu werden.

## 3. Rahmenbedingungen

**Hardware SmallTV Ultra** (Quelle: ESPHome-Geräteseite, am echten Gerät zu verifizieren):

| | |
|---|---|
| Modul | ESP-12F (ESP8266), PlatformIO-Board `esp12e`, Flash vermutlich 4 MB |
| Display | 240×240, ST7789V, SPI Mode 3, 40 MHz, **kein CS-Pin** |
| Pins | CLK GPIO14, MOSI GPIO13, DC GPIO0, RST GPIO2 |
| Backlight | GPIO5, PWM, **invertiert** |
| Farben | BGR, `invert_colors: true` |
| USB | nur Strom (kein USB-Seriell-Chip) |
| Taster | keine |

- **RAM:** ca. 40–50 KB frei. Ein volles Frame (240×240×2 = 115 KB) passt **nicht** in den RAM.
  Deshalb wird das JPEG blockweise gestreamt und dekodiert.
- **Erstes Flashen** geht ohne Löten über „Firmware update“ in der Weboberfläche der Originalfirmware.
  Größen- und Formatgrenzen des Original-Updaters sind unbekannt (siehe Risiken, Abschnitt 10).
- **Serielles Flashen** (Notfall): Gehäuse öffnen (2 Schrauben), USB-Seriell-Adapter (3,3 V)
  anlöten, GPIO0 beim Einschalten auf GND.
- **ESP8266-OTA:** Neues Image wird in freien Flash geschrieben, beim Neustart kopiert der
  Bootloader es an Stelle 0. Es gibt **kein automatisches Rollback**. Die Firmware darf höchstens
  etwa die Hälfte des Sketch-Bereichs belegen, sonst ist kein OTA mehr möglich.
- **DBF** (Datenquelle Bahn): max. eine Anfrage pro Station und Minute.
- **Lizenz** bleibt MIT. DejaVu-Fonts liegen bereits mit Lizenz bei.

## 4. Betrachtete Ansätze

| Ansatz | Kurz | Bewertung |
|---|---|---|
| **A) Eigene Firmware (PlatformIO/Arduino, C++), Gerät holt JPEG** | Schlanke Firmware, JPEG wird gestreamt dekodiert, Captive Portal, abgesichertes OTA | **Gewählt.** Volle Kontrolle über OTA-Robustheit, kleiner Code, reproduzierbarer Build, leicht in CI. Dafür mehr Eigenbau (OTA-Absicherung, Portal) |
| B) ESPHome mit `online_image` | Konfiguration statt Code | Verworfen: RAM für 240×240 auf ESP8266 zu knapp, Abhängigkeit von ESPHome-Änderungen, Berichte über Ultras, die nach Konfigurationswechsel nicht mehr booten |
| C) Server schickt Bilder ans Gerät (Push, ins RAM) | Wie heute, nur ohne Flash | Verworfen: Gerät bräuchte eigenen Upload-Server und Puffer, Server muss Geräte-IPs kennen. Pull ist einfacher und speicherschonender |

Gewählt hat der Besitzer **A**, auf Empfehlung.

**Hardware-Runner in CI:** Wir starten **ohne** Runner (Entscheidung von Claude, vom Besitzer
freigegeben). Stattdessen gibt es ein OTA-Smoketest-Skript, das vor jedem Release Pflicht ist. Es
ist so gebaut, dass es später unverändert in einem Self-hosted-Runner laufen kann. Das wird
dokumentiert.

## 5. Architektur

```
config.yaml ─▶ glancebox-server (Docker) ─┬─ Seiten-Skripte (Python + Jinja) ─▶ HTML
                 │                         └─ url-Seiten ──────────────────────▶ HTML
                 │   headless Chromium (Playwright) rendert 240×240 ─▶ Baseline-JPEG (Cache)
                 ▼
        GET /api/v1/frame  ◀── HTTP (LAN) ── Glance Box Firmware (ESP8266)
                                               └─ TJpgDec streamt Blöcke ─▶ ST7789
```

### 5.1 Repo-Struktur (Vorschlag, Details beim Builder)

```
firmware/            PlatformIO-Projekt (platformio.ini, src/, lib/, test/)
server/              Python-Paket glancebox (+ tests/)
pages/               mitgelieferte Seiten, je Ordner: page.py + template.html (+ README)
  bahn/
  example-url/ …     (mind. ein einfaches Beispiel für eigene Seiten)
tools/ota-smoketest.sh
docs/en/, docs/de/   Anleitungen; README.md (EN) + README.de.md
docker-compose.yml, config.example.yaml
.github/workflows/   ci.yml, release.yml
```

Das Repo wird auf GitHub umbenannt, `robinlanger/GeekMagicZugtafel` → `robinlanger/glancebox`.
Das macht der Besitzer, GitHub leitet die alte URL weiter. Das Python-Paket `zugtafel` geht in
`server/glancebox` und `pages/bahn` auf. `device.py` und das Zeichnen mit Pillow (`render.py`)
entfallen.

### 5.2 Protokoll Gerät ↔ Server (v1)

- `GET /api/v1/frame?id=<chip-id>&fw=<version>`, optional mit Header `If-None-Match: <etag>`.
  - `200`, `Content-Type: image/jpeg`: Baseline-JPEG 240×240, Header `ETag` und
    `X-Next-In: <Sekunden>` (wann das Gerät wieder fragen soll).
  - `304`: unverändert, mit `X-Next-In`.
  - Fehler oder Timeout: Gerät behält das letzte Bild und versucht es mit Backoff erneut.
- **Der Server steuert das Timing.** Die aktuelle Seite ergibt sich **zustandslos aus der Uhrzeit**
  (Summe der `duration`-Werte der Playlist als Zyklus, Position = `now mod Zyklus`). Damit laufen
  mehrere Geräte synchron, und der Server braucht keinen Zustand pro Gerät. `X-Next-In` = Zeit bis
  zum nächsten Seitenwechsel oder zum nächsten frischen Render der aktuellen Seite, begrenzt auf
  2–30 s.
- `id` und `fw` dienen nur Log und Diagnose (v1).
- Die Protokollversion steht im Pfad (`/v1/`). Spätere inkompatible Änderungen bekommen `/v2/`, und
  der Server spricht eine Zeit lang beide.

### 5.3 Firmware

**Stack** (Claudes Wahl, mit Versionen in `platformio.ini` gepinnt): Plattform `espressif8266`,
Framework Arduino, TFT_eSPI (ST7789, `TFT_CS -1`), TJpg_Decoder, WiFiManager (Captive Portal),
ESP8266WebServer + Updater für die Update-Seite. Gleichwertige Bibliotheken darf der Builder
wählen, wenn er es begründet.

**Verhalten**

- **Erster Start / kein WLAN:** Access Point `GlanceBox-XXXX` mit Captive Portal. Dort trägt man
  WLAN, Server-URL (z. B. `http://homeserver:8080`) und das **Update-Passwort** ein. Das Display
  zeigt AP-Namen und Anleitung.
- **Normalbetrieb:** Schleife nach 5.2. Beim Booten kurzer Statusbildschirm (Version, IP).
  Helligkeit ist im Portal einstellbar.
- **Server nicht erreichbar:** Das letzte Bild bleibt stehen. Nach ca. 2 min ohne Erfolg erscheint
  ein Statusbildschirm (IP, Server-URL, Fehler), der auf dem Gerät mit eingebautem Font gezeichnet
  wird.
- **Geräte-Webseite** (`http://<ip>/`): Status, Einstellungen, Firmware-Update (Passwort nötig),
  Neustart, Einstellungen zurücksetzen. Texte DE/EN je nach `Accept-Language`.
- **`GET /status`** (JSON, ohne Passwort): Version, Uptime, freier Heap, RSSI, Boot-Zähler,
  Safe-Mode ja/nein, Zeitpunkt und Anzahl erfolgreicher Frames. Wird vom Smoketest genutzt.
- **Flash-Schreiben** nur beim Speichern von Einstellungen und bei OTA.

### 5.4 OTA-Absicherung (Kern-Anforderung)

1. **Vor dem Umschalten:** Upload per HTTP an `/update` mit Passwort und **MD5** (Parameter oder
   Header). Das Image wird vollständig in den freien Flash geschrieben. Erst wenn Größe, MD5 und
   ESP8266-Image-Header (Magic-Byte, passende Flash-Konfiguration) stimmen, wird umgeschaltet.
   Ein Abbruch oder falsches MD5 lässt das alte Image unangetastet, und das Gerät läuft weiter.
2. **Nach dem Umschalten – Boot-Loop-Schutz:** Ein Zähler im RTC-Speicher wird früh beim Booten
   erhöht. Er wird auf 0 gesetzt, sobald die Firmware **gesund** ist: 60 s Uptime **und** WLAN
   verbunden **und** Webserver läuft. Ein erfolgreicher Frame ist bewusst *keine* Bedingung, damit
   ein toter Server keinen Safe Mode auslöst. Bei **3 Fehlstarts in Folge** startet der
   **Safe Mode**: nur WLAN (gespeicherte Daten, sonst AP), Update-Seite, `/status` und ein
   Statusbildschirm. Kein JPEG-Code, kein Frame-Abruf. Der Safe Mode muss mit minimalem Code
   auskommen und selbst getestet sein.
   **Architektur-Entscheidung (Claude):** Der Safe Mode liegt **im selben Image** wie die App. Einen
   separaten, nie überschriebenen Loader (rBoot-artig, App an anderem Flash-Offset) gibt es in v1
   nicht. Grund: Das Arduino-Core linkt Sketches auf eine feste Adresse. Mehrere Slots bräuchten
   eigene Linker-Skripte und Flash-Mapping, also deutlich mehr Komplexität und Fehlerquellen. Das
   Restrisiko „neues Image stürzt ab, bevor die Safe-Mode-Prüfung läuft“ wird so begrenzt:
   - Boot-Zähler und Safe-Mode-Entscheidung sind die **allerersten** Schritte in `setup()`, vor
     Display, WLAN und allem anderen.
   - Der **Hardware- und Software-Watchdog bleibt aktiv**, damit Hänger ebenfalls als Fehlstart
     zählen. Reset-Grund (`ESP.getResetInfoPtr()`) wird ausgewertet.
   - Der Smoketest auf echter Hardware ist Pflicht vor jedem Release.
   Ein permanenter Loader bleibt als mögliche spätere Härtung dokumentiert.
3. **Größenlimit:** Die CI bricht ab, wenn das Firmware-Image eine feste Grenze überschreitet. Die
   Grenze ist so gewählt, dass OTA im gewählten Flash-Layout sicher passt, mit Reserve.
4. **Smoketest** `tools/ota-smoketest.sh <ip> <bin>` (gegen ein echtes Gerät):
   1. `/status` lesen (Ausgangsversion).
   2. **Negativtest:** Image mit falschem MD5 hochladen → muss abgelehnt werden, Gerät läuft weiter
      mit alter Version.
   3. Neues Image hochladen → Neustart abwarten → `/status` zeigt neue Version, Boot-Zähler 0,
      Frames werden wieder geholt.
   4. **Rückweg:** das vorige Release wieder per OTA aufspielen und prüfen. Danach erneut das neue
      Image. So ist bewiesen, dass jede Version sich selbst ersetzen kann.
   5. Exit-Code ≠ 0 bei jedem Fehler, klare Ausgabe. Läuft ohne Interaktion, damit es später in
      einen Runner passt.
5. **Release-Checkliste** (`docs/RELEASING.md`, nur Englisch, Maintainer-Doku): Smoketest ist
   Pflicht und wird im Release-Text vermerkt (Version, Gerät, Datum).

### 5.5 Server

**Stack** (Claudes Wahl): Python 3.12, FastAPI + Uvicorn, Playwright (Chromium), Jinja2, PyYAML,
Pillow (JPEG-Kodierung), requests/httpx. Docker-Image auf Basis des offiziellen Playwright-Images,
**Version gepinnt**. Multi-Arch (amd64 + arm64, z. B. für Raspberry Pi). Läuft als Nicht-Root.

**`config.yaml`** (Beispiel, Feldnamen darf der Builder verfeinern):

```yaml
interval: 30              # Standard-Anzeigedauer pro Seite (s)
timezone: Europe/Berlin
pages:
  - type: bahn
    station: "Frankfurt(Main)Hbf"
    via: [Wiesbaden, Mainz]
    platforms: ["1", "2"]
    limit: 4
    title: Heimweg
    refresh: 60           # Daten max. 1×/min (DBF-Regel, Minimum 60 für bahn)
  - type: url
    url: http://homeserver.lan/status-240
    duration: 15
    refresh: 30
```

- **Seitentypen**
  - `url`: Die Seite wird so wie sie ist mit Viewport 240×240 und `deviceScaleFactor` 1 gerendert.
    Optional mit Wartezeit oder Selektor, bevor der Screenshot gemacht wird.
  - **Skript-Seiten:** Ordner `pages/<typ>/` mit `page.py`, das eine Funktion bereitstellt
    (Vorschlag: `fetch(options: dict, ctx) -> dict`), und `template.html` (Jinja). Gemeinsames
    Basis-CSS mit 240×240, gebündelten DejaVu-Fonts und Umlauten ist verfügbar. Eigene Seiten
    liegen in einem gemounteten Ordner (z. B. `./pages-custom/`), ohne das Image neu zu bauen.
    Konfigurationsfehler werden beim Start klar gemeldet. Den Vertrag einer Seite dokumentieren wir
    in `docs/*/writing-pages.md`.
- **Rendering:** Hintergrund-Scheduler rendert jede Seite gemäß `refresh` vor und cacht das JPEG
  (Baseline, nicht progressiv, Qualität ca. 85). `/api/v1/frame` liefert immer sofort aus dem
  Cache. Eine Chromium-Instanz, Pages wiederverwenden. Die Uhrzeit im Header einer Seite verlangt
  ggf. Neu-Rendern jede Minute.
- **Fehler:** Wenn `fetch` oder das Rendern fehlschlägt, bleibt das letzte gute Bild der Seite bis
  max. 10 min gültig. Danach wird die Seite übersprungen. Fehler landen im Log. Ist keine Seite
  verfügbar, kommt eine einfache Fehlerseite (nie schwarz).
- **Zusatzendpunkte:** `GET /preview/<index>.jpg` und eine einfache Übersicht `/`, um Seiten im
  Browser zu prüfen (wichtig für Leute, die eigene Seiten bauen). `GET /healthz` für Docker.
- **CLI:** `python -m glancebox render <index|typ> -o out.png` zum lokalen Testen ohne Gerät
  (Ersatz für `DRY_RUN`).

### 5.6 Seite `bahn` (Migration der Zugtafel)

- `departures.py` (DBF holen, parsen, VIA-Filter nur auf Halte *nach* dem Bahnhof, Gleisfilter,
  Sortierung nach tatsächlicher Abfahrt, Mitternachtslogik) wird übernommen, **inkl. bestehender
  Tests**.
- Das Template bildet den heutigen Look nach (`docs/vorschau.png`): Kopf mit Titel und Uhrzeit,
  pro Zeile Linie (farbiges Badge), Ziel, Minuten, Planzeit, Verspätung, Gleis (orange bei
  Wechsel), Ausfälle rot, 1–6 Zeilen.
- Optionen wie bisher die Env-Variablen: `station`, `via`, `platforms`, `limit`, `title`,
  `dbf_url`, `refresh` (min. 60). Anzeigesprache standardmäßig Deutsch.
- Der User-Agent wird auf `glancebox/<version>` angepasst.

## 6. CI, Releases, Reproduzierbarkeit

**`ci.yml` (jeder Push/PR)**

- Server: ruff, pytest (inkl. `bahn`-Tests). Ein Render-Test erzeugt im Docker-Image ein Bild
  einer Beispielseite mit Fixture-Daten und prüft Größe und Format (240×240, Baseline-JPEG). Ein
  Pixelvergleich mit Toleranz ist optional, falls stabil.
- Firmware: `pio run -e ultra` (Build), `pio test -e native` (Unit-Tests für die reine Logik:
  Boot-Zähler/Safe-Mode-Entscheidung, `X-Next-In`-/Backoff-Logik, Einstellungsprüfung, MD5- und
  Header-Prüfung) und der Größencheck des Images.
- Docker-Build (ohne Push).
- Doku: Prüfen, dass zu jeder Datei in `docs/en/` eine in `docs/de/` existiert (und
  `README.md` ↔ `README.de.md`) und die Überschriftenstruktur übereinstimmt.

**`release.yml` (Tag `vX.Y.Z`)**

- Firmware-`.bin` + `.md5` + `.sha256`, Docker-Image nach GHCR (multi-arch) und GitHub-Release mit
  Changelog-Auszug.
- Eine Versionsnummer für Firmware und Server. Die Firmware kennt ihre Version zur Build-Zeit.
- Toolchain und Bibliotheken sind gepinnt (`platformio.ini`, Python-Lockfile oder gepinnte
  `requirements.txt`, Basis-Images mit Tag).

## 7. Doku (DE + EN)

- `README.md` (EN) mit gut sichtbarem Link auf `README.de.md`: was es ist, Foto, Schnellstart,
  Warnhinweis „kein Weg zurück zur Originalfirmware“.
- `docs/{en,de}/`: `flashing.md` (erstes Flashen über die Original-Weboberfläche, Schritt für
  Schritt), `setup.md` (Captive Portal, Update-Passwort), `configuration.md` (`config.yaml`
  vollständig), `writing-pages.md` (eigene Skript-Seite und url-Seite, Beispiel), `updating.md`
  (OTA), `recovery.md` (Safe Mode, serielles Flashen inkl. Pinout, sobald am echten Gerät
  verifiziert).
- `docs/RELEASING.md` (EN, Maintainer): Release-Ablauf + Smoketest.
- Code, Kommentare, Commits: Englisch.

## 8. Vom Besitzer entschieden

- Eigene Firmware (Ansatz A). Das Gerät holt die Bilder, sie werden aus dem RAM angezeigt.
- Originalfirmware wird aufgegeben, Löten im Notfall ist akzeptiert.
- CI ist Pflicht, OTA muss sehr robust und getestet sein.
- Öffentliches Repo, gut dokumentiert, reproduzierbar.
- Inhalte: Playlist in YAML, wechselt standardmäßig alle 30 s, Seiten als einfache Einzelskripte,
  Bahn als erstes Skript.
- Doku zweisprachig DE + EN.
- Name **glancebox** / „Glance Box“, ohne „GeekMagic“ im Namen. „GeekMagic SmallTV Ultra“ steht
  in der Beschreibung.
- Kein Hardware-Runner zum Start (Entscheidung an Claude delegiert).
- Vor dem ersten Flash: serieller Zugang mit Raspberry Pi Pico als Adapter + Backup der
  Originalfirmware.

## 9. Claudes Entscheidungen (zur Prüfung)

- Englisch für Code und Commits. EN-README als Haupt-README.
- Das Gerät holt die Bilder (Pull). Der Server steuert das Timing zustandslos aus der Uhrzeit.
  Eine Playlist für alle Geräte.
- Zwei Seitentypen: `url` und Skript-Seite (`page.py` + Jinja-Template).
- Server ohne Authentifizierung (LAN). **Update-Passwort am Gerät ist Pflicht**, weil sonst
  jeder im LAN flashen könnte.
- Safe Mode nach 3 Fehlstarts. „Gesund“ = 60 s Uptime + WLAN + Webserver, nicht abhängig vom
  Server.
- Kaputte Seiten zeigen max. 10 min das letzte gute Bild, danach wird die Seite übersprungen.
- Der bisherige Original-Firmware-Modus (`device.py`) entfällt ersatzlos.
- Bibliotheken: TFT_eSPI, TJpg_Decoder, WiFiManager, FastAPI, Playwright (Begründung in 5.3/5.5).

## 10. Risiken und offene Punkte für den Builder

1. **Erstes Flashen über die Originalfirmware:** Akzeptiertes Format und maximale Größe sind
   unbekannt. **Als allererstes ein Spike:** minimales Image (Display an, Text, OTA-Seite) über die
   Original-Weboberfläche flashen und das Flash-Layout (`ESP.getFlashChipRealSize()`) auslesen.
   Erst dann Flash-Layout und Größenlimit festlegen. **Der Plan hält nach diesem Spike an.** Lehnt
   die Originalfirmware das Image ab oder ist das Limit zu klein, wird mit dem Besitzer neu
   entschieden: Zwischen-Image, das die volle Firmware nachlädt, oder erstes Flashen seriell. Bis
   dahin verspricht die Doku „ohne Löten“ nur mit dem Hinweis, dass dies am eigenen Gerät
   bestätigt ist.
   **Sicherheitsnetz vor dem ersten Flash (vom Besitzer entschieden):** Ein Raspberry Pi Pico dient
   als USB-Seriell-Adapter (Firmware `debugprobe`, UART an GP4 = TX / GP5 = RX, 3,3 V). Das Ultra
   wird über sein eigenes USB-C versorgt, verbunden werden nur GND, TX↔RX, RX↔TX, dazu GPIO0 beim
   Einschalten auf GND. **Vor dem ersten Flash** wird damit ein vollständiges Backup der
   Originalfirmware gezogen (`esptool.py read_flash 0 ALL`) und ein serieller Flash einmal geprobt.
   Die Anleitung dazu (inkl. Pico) kommt in `recovery.md`, weil andere Nutzer oft auch einen Pico
   statt eines CH340 haben.
   **Hardware-Schritte** (Spike, Pins/Farben bestätigen, Dauerlauftest, Smoketest, Pinout-Foto)
   macht der Besitzer am eigenen Ultra. Der Plan ordnet sie als Haltepunkte ein. Firmware-Teile,
   die nicht davon abhängen (Server, `bahn`, Native-Tests, CI, Doku), laufen vorher oder parallel.
2. **Pins/Farben** stammen aus der ESPHome-Community und sind am Gerät zu bestätigen (BGR,
   Inversion, Backlight invertiert).
3. **DC liegt auf GPIO0** (Boot-Pin), **RST auf GPIO2**. Prüfen, dass das Display-Setup den Boot
   nicht stört und der Safe Mode das Display trotzdem bedienen kann.
4. **RAM:** Heap während des JPEG-Streamings über Stunden beobachten (Dauerlauftest ≥ 24 h,
   `/status` loggen). Fragmentierung vermeiden, keine `String`-Konkatenation in der Schleife.
5. **Serielles Pinout** für `recovery.md` ist noch unbelegt (Community hat es nur als Bild). Beim
   Öffnen des eigenen Geräts fotografieren und dokumentieren.
6. **Chromium-Ressourcen** (~200–300 MB RAM) im Docker-Image. Für Homeserver okay, in der Doku
   erwähnen.
