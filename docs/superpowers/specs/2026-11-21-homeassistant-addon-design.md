# Home-Assistant-Add-on – Design

Stand: 2026-11-21 · Ziel-Version: 0.6.0 · Größe: Projekt (volles Design)

## Absicht

Der Glance-Box-Server soll als **Home-Assistant-Add-on** installierbar sein. HA-Nutzer fügen das
Repo im Add-on-Store hinzu, klicken „Installieren“ und „Starten“ und haben einen laufenden Server,
ohne Docker Compose, `.env` oder Long-Lived Token. Ziel ist Reichweite in der HA-Community (dort
gab es schon Interesse, z. B. PV-Werte auf dem Display).

Leitbild des Nutzers: **„Wie bei Apple: so wenig manueller Aufwand wie nötig, aber so viel Freiheit
wie möglich.“** Erfolg heißt: einfache Einrichtung, Übersichtlichkeit, alles funktioniert. Sicherheit
ist ausdrücklich wichtig.

## Ziele

1. **Installierbar über den Add-on-Store** von HA OS / Supervised als eigenes Add-on-Repository
   (das bestehende GitHub-Repo). Ein „Add repository“-Button über `my.home-assistant.io`
   (`supervisor_add_addon_repository?repository_url=…`) in README und Doku.
2. **Läuft ohne Eingaben:** Beim ersten Start entsteht eine Start-Playlist **Uhr + Wetter am
   Heimstandort von HA**. Das Display zeigt sofort etwas Sinnvolles.
3. **Werte aus HA übernehmen:** Zeitzone und Standort (`time_zone`, `latitude`, `longitude` aus
   `GET http://supervisor/core/api/config`). Sprache ebenfalls, falls `/api/config` sie liefert
   (in der Doku nicht bestätigt, siehe Offene Punkte); sonst Standard `en`, änderbar in der YAML.
4. **Formular nur für Geheimnisse:** Push-Key und API-Keys der Anbieter als Typ `password`, alle
   optional. Sie ersetzen die `.env`. Werte aus dem Formular stehen dem Server als Umgebungsvariablen
   zur Verfügung, sodass die Playlist sie weiter als `${NAME}` nutzt.
5. **Playlist bleibt YAML** im Konfigurationsordner des Add-ons (`map: app_config`, im Container
   `/config`, also genau dort, wo der Server heute `config.yaml` und `pages/` erwartet). Bearbeitet
   mit dem File editor oder Studio Code Server. Volle Freiheit wie heute, inkl. eigener Seiten.
6. **HA-Seite ohne Token:** Ist im Add-on-Modus bei `type: homeassistant` weder `url` noch `token`
   gesetzt, nutzt die Seite den Supervisor-Proxy (`http://supervisor/core` mit `SUPERVISOR_TOKEN`).
   Explizit gesetzte `url`/`token` haben Vorrang (z. B. für ein zweites HA).
7. **Seitenleiste „Glance Box“ über Ingress** (hinter dem HA-Login): Kasten „Display verbinden“ mit
   der Server-Adresse zum Kopieren (`http://<LAN-IP von HA>:<Host-Port>`), darunter die bestehende
   Übersicht mit Live-Vorschau jeder Seite, Fehler und Alter, plus Hinweis, wo die `config.yaml` liegt
   und Link zur Doku.
8. **Doku:** neuer Abschnitt „Home Assistant“ (EN + DE), kurz: einmal das Display im Browser flashen
   (wie bisher), danach läuft alles in HA. Dazu `DOCS.md` im Add-on-Ordner (HA zeigt sie im
   Add-on-Store an).
9. **Bestehende Docker-Installationen ändern sich nicht.** Der Add-on-Modus ist nur aktiv, wenn der
   Server als Add-on läuft.

## Nicht-Ziele

- Display flashen aus HA heraus, automatisches Finden des Servers durch das Display (mDNS):
  bräuchte Firmware-Änderungen, späteres eigenes Thema.
- Playlist im Formular oder in einer grafischen Oberfläche bearbeiten.
- HACS-Integration (Integrationen laufen im HA-Prozess, Chromium nicht möglich).
- Aufnahme in den offiziellen HA-Add-on-Store oder die „Community Add-ons“ (kuratiert, nicht unser
  Einfluss). „Kompatibel mit dem Store“ heißt hier: als eigenes Repository im Store hinzufügbar.
- Unterstützung für armv7/armhf/i386 (bei HA veraltet; unser Image gibt es nur für amd64/arm64).

## Anti-Ziele (wäre ein Misserfolg, auch wenn es technisch läuft)

- Einrichtung braucht mehr als: Repo hinzufügen, installieren, starten, Adresse ins Display tippen.
- Geheimnisse landen im Klartext in der YAML oder in Logs.
- Das Add-on bekommt mehr Rechte als nötig (Docker-Socket, Host-Netzwerk, `full_access`,
  `hassio_role` über `default`); Ausnahme bewusst: `homeassistant_api` (S1-a).
- Die Ingress-Seite ist ohne HA-Login aus dem LAN erreichbar.
- Doku oder Posts behaupten, das Add-on sei getestet, bevor es auf echtem HA OS lief.

## Rahmenbedingungen

- Add-ons gibt es nur bei **HA OS / Supervised**, nicht bei HA Container.
- Supervisor zieht das Image `image:` mit dem Tag = Add-on-`version`. Unser Release-Workflow pusht
  `ghcr.io/robinlanger/glancebox:<VERSION>` als Multi-Arch-Manifest (amd64, arm64); das passt
  ohne `{arch}`. Add-on-`version` muss bei jedem Release mit `VERSION` übereinstimmen.
- Image ohne HA-Basis ist erlaubt. Keine eigene Init → `init: true` (Standard) lassen. Labels
  `io.hass.version`, `io.hass.arch`, `io.hass.type=app` im Image ergänzen (oder `legacy: true`).
- Das Image läuft als `pwuser` (nicht root). Ob `/config` (app_config) und `/data` für `pwuser`
  beschreibbar sind, ist in der HA-Doku nicht beschrieben → **erster Prüfpunkt in der Test-VM**.
- Optionen liegen beim Start in `/data/options.json`; Änderungen brauchen einen Neustart des Add-ons.
- Ingress-Anfragen kommen nur von `172.30.32.2`, mit Header `X-Ingress-Path`; die Seite muss
  **relative URLs** nutzen (heute: `src="/preview/…"` in `templates/index.html` ist absolut).
- LAN-IP für den Kasten „Display verbinden“: `GET http://supervisor/network/info`
  (`interfaces[]` mit `primary: true`, `ipv4.address` ohne `/24`), braucht `hassio_api: true` mit
  Rolle `default`. Host-Port: aus `GET http://supervisor/addons/self/info` (Feld mit der Port-Zuordnung;
  genaue Feldnamen beim Bau prüfen).
- `homeassistant_api: true` gibt dem Add-on über den Proxy **Administratorrechte in HA**; eine
  Nur-Lesen-Stufe gibt es nicht (siehe Entscheidung S1).
- Nichts behaupten, was nicht getestet ist; Test auf echtem HA OS (Test-VM, unten).

## Ansätze

| | Ansatz | Bewertung |
|---|---|---|
| **A** ✅ | Add-on nutzt das vorhandene GHCR-Image; der Server bekommt einen **Add-on-Modus** (erkennt `/data/options.json` bzw. `SUPERVISOR_TOKEN`) | Ein Image, Add-on automatisch bei jedem Release aktuell, keine zweite Pipeline. Kosten: kleines HA-Modul im Server, das sonst inaktiv ist. **Gewählt vom Nutzer.** |
| B | Eigenes Add-on-Image `FROM glancebox:<version>` mit Startskript | Server bliebe HA-frei, aber zweites Image je Release und Architektur, Versionen synchron halten, bashio fehlt im Playwright-Image. Für Ingress-Kasten muss der Server trotzdem geändert werden. |
| C | HACS-Integration | Unmöglich: Chromium läuft nicht im HA-Prozess. |

Ort: **im bestehenden Repo** (`repository.yaml` an der Wurzel, Add-on im Ordner `homeassistant/`
o. ä.), damit Stars und Issues an einer Stelle bleiben.

## Entschiedene Teile des Wie

- **Einstellungen gemischt** (Nutzer, auch wegen Sicherheit): Formular = Geheimnisse; YAML = Playlist.
  Zeitzone/Standort/Sprache kommen aus HA, nicht ins Formular.
- **Start-Playlist:** Uhr + Wetter (Heimstandort). Wird nur angelegt, wenn `/config/config.yaml`
  fehlt; eine vorhandene Datei wird nie überschrieben.
- **Ingress-Seite** wie skizziert (Nutzer: „für den Start perfekt“):

  ```
  ┌ Glance Box ─────────────────────────────┐
  │ Display verbinden                        │
  │ Server-Adresse:  http://192.168.x.x:8090 │  [kopieren]
  │ → im Setup-Portal des Displays eintragen │
  │ Playlist            (Vorschau, live)     │
  │ [Uhr-Bild]   Uhr       aktuell           │
  │ [Wetter]     Wetter    vor 2 min         │
  │ Seiten ändern: config.yaml im File editor│  [Doku ↗]
  └──────────────────────────────────────────┘
  ```
- **Testumgebung:** HA OS als KVM-VM in einem Docker-Container unter `~/haos` auf dem Heimserver
  (kein sudo, keine Änderung am Host-Netz; Ports 8123 und Add-on-Port weitergeleitet). Abbau mit
  einem Befehl.
- **Rechte (mein Vorschlag):** `ingress: true`, `panel_icon: mdi:monitor`, `panel_admin: true`,
  `hassio_api: true` (nur Rolle `default`, für `/network/info`), `homeassistant_api: true` (S1-a),
  `map: [app_config:rw]`, Port `8080/tcp` → Standard-Host-Port 8090 (änderbar), kein Host-Netz,
  kein Docker-API, AppArmor an (Standardprofil; eigenes Profil optional später).
- **Ingress getrennt vom Display-Port:** Ingress auf eigenem Port (`ingress_port`, z. B. 8099), der
  nur Übersicht und Vorschau ausliefert und nur `172.30.32.2` annimmt. Der Display-Port 8080 bleibt
  wie heute (Frames, Push, Vorschau ohne Login, nur LAN).

## Entscheidung S1: **a, direkt verbinden** (Nutzer, 2026-11-21)

Die tokenlose HA-Seite braucht `homeassistant_api: true`, und das ist **Admin-Zugriff auf HA**. Die
Seite selbst liest nur `GET /api/states/<id>`.

- **S1-a Komfort:** `homeassistant_api: true` immer an; HA-Seite geht ohne Token.
- **S1-b Sicherheit:** aus; wer die HA-Seite will, legt einen **eigenen HA-Benutzer ohne
  Admin-Rechte** an und trägt dessen Token als Passwortfeld ein (ein Schritt mehr).
Entschieden: **S1-a**. Begründung: Mit S1-b würden die meisten ihr eigenes Admin-Token einfügen
(gleiche Rechte, plus ein Geheimnis, das verloren gehen kann). Der Supervisor-Token gehört nur zu
diesem Add-on und verfällt beim Deinstallieren. Die Doku sagt offen, dass das Add-on Admin-Zugriff
auf HA hat und warum.

- **S1-c Wahl:** Schalter im Formular „Home Assistant direkt verbinden“ geht nicht, weil
  `homeassistant_api` statisch in der Add-on-Konfiguration steht. Daher nur a oder b.

## Entscheidungen nach der Builder-Prüfung (meine Calls, vom Nutzer prüfbar)

- **B1 HA-Werte bei jedem Start, nichts eingefroren:** Im Add-on-Modus gelten Zeitzone, Sprache und
  Standort aus HA, solange die YAML sie nicht selbst setzt (YAML hat Vorrang). Die Start-Playlist
  enthält **keine Koordinaten**; die Wetterseite bekommt im Add-on-Modus ohne `location`/`latitude`
  den HA-Heimstandort. Grund: ändert jemand seinen Standort in HA, folgt das Display; keine
  Heimkoordinaten in einer Datei, die man vielleicht teilt.
- **B2 Geheimnisse: feste Felder + freie Liste:** Formular hat benannte Felder für Push-Key und die
  Anbieter-Keys (Anthropic, OpenAI, xAI, Copilot) und zusätzlich eine Liste „Weitere Geheimnisse“
  (`name: str`, `value: password`) für eigene Seiten. Alle werden zu Umgebungsvariablen für `${NAME}`.
  Grund: Freiheit für eigene Seiten ohne Klartext in der YAML.
- **B3 Display-Port im Add-on-Modus schlank:** Auf dem LAN-Port bleiben nur `/api/v1/frame`,
  `/api/v1/push/…` und `/healthz`. Übersicht (`/`) und Vorschaubilder gibt es im Add-on-Modus **nur
  über Ingress**. Docker-Installationen bleiben unverändert. Grund: sonst wäre die Vorschau (mit
  HA-Werten) doch ohne Login im LAN sichtbar.
- **B4 Veröffentlichung erst nach Abnahme:** Die Arbeit bleibt auf einem Branch, bis die Abnahme in
  der Test-VM bestanden ist. Abnahme = Repo im Store hinzufügen, installieren, starten, Ingress-Seite
  mit Adresse und Vorschau, **echtes Display holt Frames über den Add-on-Port**, HA-Seite zeigt eine
  Entität. Erst dann Merge, Tag 0.6.0 und Doku/Posts. Die VM-Skripte unter `~/haos` gehören nicht ins
  Repo (persönliches Setup).

## Dem Builder überlassen

- Genauer Ordnername des Add-ons, Icon/Logo (`icon.png`, `logo.png`), Übersetzungen der Formular-
  felder (`translations/en.yaml`, `de.yaml`).
- Wie Formularwerte in Umgebungsvariablen übersetzt werden (Namensschema), solange `${NAME}` in der
  YAML funktioniert und nichts davon geloggt wird.
- Wie der Add-on-Modus erkannt wird (`/data/options.json` vorhanden und/oder `SUPERVISOR_TOKEN`).
- Lösung für Schreibrechte in `/config`, falls `pwuser` dort nicht schreiben darf (z. B. Start-
  Playlist nur im Speicher + Hinweis in der Ingress-Seite, oder Anpassung im Image), mit Rückfrage,
  falls dafür der Container als root starten müsste.
- Versionsabgleich Add-on ↔ `VERSION` im Release-Workflow (Prüfung oder automatisches Setzen).
- Tests: Unit-Tests für Add-on-Modus (Optionen → Umgebung, Start-Playlist, Supervisor-Antworten
  gemockt), Ingress-Quelladresse; Abnahme in der Test-VM.

## Offene Punkte zum Prüfen beim Bau

1. Schreibrechte von `pwuser` auf `/config` und `/data` im Add-on.
2. Liefert `/api/config` ein Feld `language`? Sonst Standard `en`.
3. Feldnamen für den Host-Port in `/addons/self/info`.
4. Ob `password?` (optional) im Schema funktioniert (Doku zeigt nur `str?`).
