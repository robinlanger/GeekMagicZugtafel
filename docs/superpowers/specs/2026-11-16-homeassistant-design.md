# Seite `homeassistant` + Simulations-HA – Design

Stand: 2026-11-16 · Status: Entwurf zur Freigabe (Builder-Check eingearbeitet)

## 1. Absicht und Warum

Die README verspricht „a status page from your Home Assistant“, meint damit aber nur den
Seitentyp `url`, also eine beliebige Webseite. Glance Box soll für v0.4.0 eine **echte Seite
`homeassistant`** bekommen. Sie holt ausgewählte Werte über die HA-REST-API und zeigt sie
schlicht und gut lesbar auf 240x240.

Was jemand sehen will, hängt vom Nutzer ab: der eine seine Solaranlage, der andere den
Stromverbrauch, der nächste ein paar Sensoren. Deshalb gibt es **eine Seite mit frei wählbaren
Entitäten und zwei Layouts**. Für verschiedene Zwecke legt man mehrere Seiten in die Playlist.

Entwickelt und getestet wird gegen ein **simuliertes Home Assistant** auf dem Homelab des
Maintainers. Das echte Smart Home wird nicht benutzt. Die Simulation liegt als Dateien im Repo,
damit jeder sie neu aufsetzen kann.

Vorbilder waren geekmagic-hacs (HA-Integration für die Originalfirmware, viele Layouts und
Widgets) und ein ESPHome-Dashboard für den SmallTV Ultra (2x2-Kacheln für PV, Akku und Netz).
Übernommen wird nur das, was auf 240x240 am häufigsten gebraucht wird: Kacheln und Liste.

## 2. Ziele, Nicht-Ziele, Anti-Ziele

**Ziele**

1. Simulations-HA auf `server` in `~/homeassistant-sim`, gebaut aus Dateien im Repo
   (`tools/ha-sim/`). Die Werte bewegen sich.
2. Seitentyp `homeassistant` in `pages/homeassistant/`, gebaut wie `kuma` und `weather`.
3. Layouts `tiles` (1–4 Werte) und `list` (1–6 Werte), Sprache de/en.
4. Saubere Fehlerfälle: HA nicht erreichbar, Token abgelehnt, Entität fehlt, Entität
   nicht verfügbar.
5. Tests mit Fixtures **und** ein echter Test gegen das Simulations-HA.
6. Doku EN + DE (Vorlagenkatalog, Vorlagenseite, configuration), Vorschaubilder, README-Sätze.

**Nicht-Ziele (diese Runde)**

- Weitere Layouts (Hero, 3x3, Gauges, Diagramme, Verlauf), Icons pro Entität, Wetter- oder
  Klima-Widgets.
- Eine Zusammenfassungs-Seite der Art „3 Lichter an: Küche, Flur, Bad“ (vom Nutzer abgelehnt).
- Geräte vom Display aus schalten. Die Seite liest nur.
- WebSocket-API, `/api/states` (alles) oder `/api/template`.
- HTTPS mit selbst signiertem Zertifikat (keine Option, die die Prüfung abschaltet).
- Übersetzung beliebiger Zustände wie `home`, `heat`, `cleaning`. Sie erscheinen so, wie HA sie
  liefert.
- Release. v0.4.0 kommt erst mit dem OK des Maintainers.

**Anti-Ziele (wäre ein Fehlschlag, auch wenn es technisch geht)**

- Die Seite zeigt alte Werte weiter, obwohl HA nicht erreichbar ist.
- Der Token landet in Git, im Chat, in Logs, in einer Fehlermeldung oder im Vorschaubild.
- Persönliche Daten (E-Mail, Heimnetz-IPs, echte Gerätenamen) im Code, in der Doku, in Bildern
  oder in Commits.
- Die Doku behauptet etwas, das nicht getestet wurde, zum Beispiel dass der Token nur lesen kann.
- Glance Box oder Uptime Kuma auf dem Server werden ungefragt angefasst oder neu gestartet.
- Eine überladene Seite. Gewünscht ist „clean wie Apple, alles Nötige drauf“.

## 3. Rahmenbedingungen

- **Server:** ssh-Alias `server`, Ubuntu x86_64, Docker + Compose, Nutzer in der Gruppe
  `docker`, sudo nur mit Passwort, also ohne sudo arbeiten. Port 8123 ist frei.
- **Tabu ohne Rückfrage:** `~/zugtafel` (Glance Box, :8090) und `~/uptime-kuma` (:3001).
  Glance-Box-Konfiguration für einen Live-Test nur nach Rückfrage ändern und danach wieder auf
  den alten Stand bringen (die vorherigen Seiten `bahn` + `kuma`).
- **DNS:** Pi-hole läuft im Host-Netz und beantwortet kein DNS aus Docker-Bridge-Netzen.
  Container brauchen `dns: [<Router-IP>]`. Container erreichen sich über die LAN-IP des Servers.
- **Display nicht flashen.** Die Firmware ändert sich nicht.
- **Git:** Branch `homeassistant`. Committen ja, pushen und mergen erst nach OK. Trailer
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Datenschutz:** In Code, Doku, Bildern und Commits nur Beispielnamen (`homeassistant.lan`,
  `192.168.1.x`, „Wohnzimmer“). Die echte Server-IP steht nur in lokalen, ignorierten Dateien.
- `python3 tools/check_docs_parity.py` muss grün bleiben. EN und DE brauchen dieselbe
  Überschriften-Struktur.
- `${NAME}` wird nur als ganzer Wert ersetzt (`url: ${HA_URL}`, `token: ${HA_TOKEN}`).

## 4. Ansätze

**Daten holen** (entschieden vom Maintainer: „wie es für die breite Masse am besten ist“)

1. **Gewählt:** eine Anfrage pro Entität, `GET <url>/api/states/<entity_id>`. Höchstens 6 kleine
   Anfragen pro Aktualisierung. Die Antwort 404 gehört eindeutig zu einer Entität. Das bleibt
   auch bei einem HA mit Tausenden Entitäten klein.
2. Verworfen: `GET /api/states` einmal holen und filtern. Das ist eine Anfrage, aber bei großen
   Installationen jedes Mal hunderte KB bis MB. Fehlende Entitäten müssten wir selbst abgleichen.
3. Verworfen: `POST /api/template`. Wir müssten aus der Konfiguration Jinja-Code bauen und dessen
   Fehler auseinandernehmen. Das ist fehleranfällig und schwer zu testen.
4. Verworfen: WebSocket. Es bräuchte eine Dauerverbindung, und die passt nicht zu „Seite holt
   alle N Sekunden“.

**Werte simulieren** (Vorschlag, vom Maintainer nicht beanstandet)

1. **Gewählt:** Template-Entitäten in YAML, die aus `now()` rechnen (Tageskurven, Minutenmuster).
   Das ist reproduzierbar und kommt ohne Automationen und gespeicherten Zustand aus. HA rechnet
   `now()`-Templates jede Minute neu.
2. Verworfen: die `demo`-Integration. Sie bringt rund hundert fest benannte, englische Entitäten,
   und die meisten Werte bewegen sich nicht.
3. Verworfen: `input_number` + Automationen. Das sind mehr bewegliche Teile, und der Zustand
   hängt von der Vorgeschichte ab.

## 5. Teil 1 – Simulations-HA

**Dateien im Repo: `tools/ha-sim/`**

- `docker-compose.yml`: Dienst `homeassistant-sim`, Image
  `ghcr.io/home-assistant/home-assistant:stable`, `ports: ["8123:8123"]`, Bridge-Netz (kein
  `network_mode: host`, kein `privileged`), `restart: unless-stopped`, `TZ=Europe/Berlin`,
  Bind-Mount `./config:/config`. **Kein** `dns:` im Repo. Das steht wie bei Glance Box in einem
  lokalen `docker-compose.override.yml` auf dem Server.
- `config/configuration.yaml`: `homeassistant:` mit Name „Sim-Zuhause“, `unit_system: metric`,
  `time_zone: Europe/Berlin`, `country: DE`. Dazu die Integrationen, die für Onboarding,
  Oberfläche, Profil/Token und die REST-API nötig sind, und die Template-Entitäten (am besten in
  `config/packages/` oder einer eigenen `templates.yaml`).
- `README.md` (nur Englisch, ist Werkzeug, nicht Nutzer-Doku): Aufsetzen, Override mit `dns:`,
  Onboarding, Token anlegen, Entitätenliste.
- `.gitignore` in `tools/ha-sim/config/` für alles, was HA selbst anlegt (`.storage/`,
  Datenbank, Logs, `secrets.yaml` …), damit nie ein Konto oder Token ins Repo rutscht.

**Auf dem Server:** `~/homeassistant-sim/` bekommt eine Kopie von `tools/ha-sim/` (z. B. per
`rsync`/`scp`) plus das lokale Override mit `dns: [<Router-IP>]`. Gestartet wird mit
`docker compose up -d` **in diesem Verzeichnis**. Andere Stacks werden nicht berührt.

**Wer was tut:** Das Aufsetzen auf dem Server (Dateien nach `~/homeassistant-sim` kopieren,
Override anlegen, `docker compose up -d` dort) gehört zum Auftrag und darf ohne weitere Rückfrage
passieren. Die Router-IP für `dns:` wird aus `~/zugtafel/docker-compose.override.yml` **gelesen**.
Lesen ist kein Anfassen, der Maintainer hat selbst auf die Datei verwiesen. Das Sim-HA wird
**früh** aufgesetzt. Danach meldet sich der Builder beim Maintainer für Onboarding und Token und
baut in der Zwischenzeit die Seite mit Fixtures weiter. Der Live-Test kommt erst, wenn der Token
in der lokalen `.env` steht. Vorher wird nichts als „getestet“ gemeldet.

**Einmalig von Hand (Maintainer):**

1. `http://<server>:8123` öffnen und im Onboarding das Besitzerkonto anlegen.
2. Unten links auf den Benutzernamen → Reiter **Sicherheit** → **Langlebige Zugangstoken** →
   **Token erstellen**, Name z. B. `glancebox`.
3. Den Token nur in lokale `.env`-Dateien eintragen, nie in Git oder in den Chat:
   - Mac, Repo-Wurzel `.env` (ist in `.gitignore`): `HA_URL=http://<server-ip>:8123` und
     `HA_TOKEN=…` für den Live-Test.
   - Server `~/zugtafel/.env` erst, wenn ein Live-Test auf dem Display freigegeben ist.

**Simulierte Entitäten (Mindestumfang, Namen deutsch, IDs vom Builder):**

| Was | Domain / device_class | Verhalten |
| --- | --- | --- |
| Temperatur Wohnzimmer | sensor, temperature, °C | ~20–22,5, Tageskurve, eine Nachkommastelle |
| Luftfeuchte Wohnzimmer | sensor, humidity, % | ~45–60, ganzzahlig |
| Temperatur außen | sensor, temperature, °C | Tageskurve ~2–14, zeitweise unter 0 nicht nötig |
| Luftfeuchte außen | sensor, humidity, % | ~60–95 |
| Hausverbrauch | sensor, power, W | wechselt minütlich zwischen ~250 und ~3200, damit W und kW vorkommen |
| PV-Leistung | sensor, power, W | 0 nachts, Glockenkurve tagsüber bis ~4800 |
| Netz | sensor, power, W | Hausverbrauch − PV, also auch **negativ** (Einspeisung) |
| Energie heute | sensor, energy, kWh oder Wh | steigt über den Tag |
| Speicher | sensor, battery, % | 10–100, langsam |
| Akku Rauchmelder | sensor, battery, % | niedrig, z. B. 12 |
| Fenster Bad | binary_sensor, window | z. B. offen, wenn Minute % 10 < 3 |
| Haustür | binary_sensor, door | meist zu, kurz offen |
| Bewegung Flur | binary_sensor, motion | Minutenmuster |
| Mindestens 2 Lichter | light | an/aus, im Wechsel oder abends an |
| Mindestens 1 Schalter | switch | an/aus |
| Kellersensor | sensor, temperature | regelmäßig `unavailable` (Availability-Template), damit dieser Fall live vorkommt |

Wie Lichter und Schalter technisch umgesetzt werden (Template-Light mit `input_boolean`,
zeitgesteuert o. ä.), entscheidet der Builder. Wichtig ist: Domain `light` bzw. `switch` und ein
Zustand, der sich ändert.

## 6. Teil 2 – Seite `homeassistant`

**Dateien:** `pages/homeassistant/page.py`, `template.html`, `README.md` (kurz, wie bei `kuma`),
`test_homeassistant.py`.

**Konfiguration**

```yaml
- type: homeassistant
  url: ${HA_URL}             # http(s)://host:8123, ohne /api
  token: ${HA_TOKEN}         # Long-Lived Access Token
  title: Solar               # Standard: "Home Assistant"
  layout: tiles              # tiles | list; Standard: tiles bei 1–4 Entitäten, sonst list
  lang: de                   # Standard: top-level lang
  refresh: 30
  entities:
    - sensor.pv_power        # Beschriftung = friendly_name aus HA
    - entity: sensor.grid_power
      label: Netz            # eigene Beschriftung
      decimals: 1            # optional, 0–3
```

Prüfung beim Start (`validate`): `url` http/https mit Host. `token` ist ein nicht leerer Text.
`entities` ist eine Liste mit 1–6 Einträgen, jeder ein String oder ein Objekt mit `entity`
(Pflicht), `label` (Text), `decimals` (0–3). Die Entity-ID ist `domain.objekt` aus `a-z0-9_`.
`layout` ist `tiles` oder `list`, `tiles` nur mit höchstens 4 Entitäten. `lang` ist `de` oder
`en`. Fehlermeldungen nennen die Stelle wie bei den anderen Seiten.

**Abruf:** pro Entität `http.get_json(f"{url}/api/states/{entity_id}",
headers={"Authorization": f"Bearer {token}"})`, nacheinander, mit dem Timeout des Helpers.
Antwort laut HA-REST-API: `{entity_id, state, attributes: {unit_of_measurement, friendly_name,
device_class, …}, last_changed, …}`.

Zuordnung der Fehler:

| Ereignis | Ergebnis |
| --- | --- |
| Verbindung scheitert, Timeout, 5xx, kaputtes JSON | ganze Seite: Meldung `Keine Verbindung zu Home Assistant` / `Cannot reach Home Assistant`, darunter `Stand HH:MM` / `As of HH:MM` |
| 401 oder 403 | ganze Seite: `Token abgelehnt` / `Token rejected`, darunter ein Hinweis auf den Long-Lived Access Token |
| 404 für eine Entität | nur diese Zelle: Beschriftung (`label` oder Entity-ID), Wert `fehlt` / `missing`, orange |
| `state` ist `unavailable` oder `unknown` | nur diese Zelle: `n. v.` / `n/a`, orange |

Die Seitenmeldungen sind orange (`ui.notice(…, "warn")`) wie bei `kuma`. Es bleiben keine alten
Werte stehen. Der Token erscheint nie in Logs. Geloggt werden Ausnahmetyp und Meldung ohne
Header. Die Kopfzeile wird nie rot.

**Darstellung von Werten**

- **Zahl** (lässt sich `state` als Zahl lesen): Ganzzahlen bleiben ganzzahlig, sonst höchstens
  eine Nachkommastelle, oder genau `decimals`, wenn gesetzt. Deutsch mit Komma. Minus als
  echtes Minuszeichen.
- **W und Wh ab |1000|** werden zu kW bzw. kWh, mit einer Nachkommastelle (oder `decimals`).
- **Einheit** aus `unit_of_measurement`, kleiner und grau hinter der Zahl.
- **Beschriftung:** `label`, sonst `friendly_name`, sonst die Entity-ID.
- **Wörter statt on/off:**
  - binary_sensor `door`, `window`, `opening`, `garage_door`: `offen`/`zu`, `open`/`closed`.
    „offen“ ist orange.
  - binary_sensor `motion`, `occupancy`, `presence`: `erkannt`/`frei`, `detected`/`clear`. Weiß.
  - `light`, `switch`, `input_boolean`, `fan` und sonstige binary_sensor: `an`/`aus`, `on`/`off`.
    „an“ ist gelb bei `light` und `switch`, sonst weiß.
- **Andere Texte** wie HA sie liefert, mit Ellipse abgeschnitten.

**Layouts** (wie die Mockups vom 2026-11-16, dunkel, DejaVu Sans, Kopfzeile aus `ui.header`)

- Die Kopfzeile (`ui.header` mit Titel und Uhrzeit) steht in **jedem** Layout, auch bei
  einer einzigen Kachel. Werte sind weiß, farbig nur die Zustandswörter oben. Die Einheit steht
  auf derselben Grundlinie wie die Zahl.
- `tiles`: 1 Wert füllt die Fläche. 2 Werte übereinander. 3 Werte: einer breit oben, zwei
  darunter. 4 Werte: 2x2. Oben die Beschriftung klein und grau, darunter der Wert groß und fett,
  die Einheit klein. Trennlinien `var(--divider)`.
- `list`: bis 6 Zeilen à ~34 px. Links die Beschriftung, rechts der Wert mit Einheit.
- **Breite Werte:** Wenn ein Wert in seiner Kachel oder Zeile nicht passt (z. B. `−10,4 kW` in
  einer 4er-Kachel), wird die Schrift in Stufen kleiner. Ob das per Zeichenzahl in Python oder
  im Template geschieht, entscheidet der Builder. Der Renderer muss es ohne JavaScript schaffen,
  falls Chromium dort keins ausführt (prüfen).
- **Lange Beschriftungen** werden mit Ellipse gekürzt. Fehlerwerte (`fehlt`, `n. v.`) sind kurz,
  damit der Name lesbar bleibt.

## 7. Tests

- **Fixtures** (pytest, wie `test_kuma.py`, `glancebox.http.get_json` per monkeypatch): Zahl mit
  Einheit, de/en-Format, W→kW, negative Werte, `decimals`, Ganzzahlen, Wörter je device_class,
  `unavailable`/`unknown`, 404 einer Entität (die anderen bleiben), 401, 403,
  Verbindungsfehler, Timeout, 5xx, kaputtes JSON, Standard-Layout nach Anzahl, alle
  `validate`-Fehler. Der Token taucht in keinem Log auf (`caplog`).
- **Render-Tests** (`@pytest.mark.browser`): jedes Layout mit 1–4 bzw. 6 Einträgen ergibt ein
  240x240-Bild, Fehlerseiten rendern.
- **Live-Test gegen das Simulations-HA:** eigener pytest-Marker (z. B. `homeassistant_live`), der
  nur läuft, wenn `HA_URL` und `HA_TOKEN` gesetzt sind (aus der Umgebung oder der lokalen `.env`,
  sonst übersprungen). Er prüft echte Werte für bekannte Sim-Entitäten, `fehlt` für eine erfundene
  Entität, `Token abgelehnt` mit falschem Token, `Keine Verbindung` mit falschem Port, und rendert
  ein Bild aus echten Daten. **Erst wenn dieser Test einmal grün gelaufen ist, gilt die Seite als
  getestet.** CI überspringt ihn.
- **Lokale Sichtprüfung:** Glance Box lokal auf dem Mac gegen das Simulations-HA starten und die
  Vorschau unter `http://localhost:8080/` ansehen. Der Server bleibt dabei unberührt.
- **Optional, nur nach Rückfrage:** Live-Test auf dem echten Display über die Glance Box auf dem
  Server. Danach `config.yaml` und `.env` dort auf den alten Stand (die vorherigen Seiten `bahn` + `kuma`)
  zurücksetzen und das zurückmelden.

## 8. Doku

- `docs/en/templates/homeassistant.md` + `docs/de/templates/homeassistant.md`, aufgebaut wie
  `kuma.md`: Vorschaubilder, Was es zeigt, Was du brauchst (Token anlegen, Schritt für Schritt),
  Beispiel, Optionen, Einrichtung, Datenschutz & Sicherheit, Wenn etwas nicht stimmt.
- **Datenschutz-Abschnitt, ehrlich:** Ein Long-Lived Access Token hat die Rechte des Benutzers,
  der ihn erstellt hat, und HA kennt keine Nur-Lese-Tokens. Empfehlung: einen eigenen
  HA-Benutzer für Glance Box anlegen. Dass auch ein Nicht-Admin über die API alles lesen und
  Dienste aufrufen kann, wird **nicht live getestet**, sondern mit Verweis auf die HA-Doku
  formuliert („laut Home-Assistant-Dokumentation …“) *(Entscheidung des Planers: spart dem
  Maintainer einen zweiten Benutzer in der Simulation)*. Getestet und so behauptet wird nur, was
  der Live-Test zeigt: Mit dem Token liest die Seite die Zustände. Token nur in `.env`, HA nicht
  nur für diese Seite ins Internet stellen.
- Katalog `docs/*/templates/README.md`: Eintrag unter „Server & smart home“.
- `docs/*/configuration.md`: `homeassistant` in die Liste der Typen und ein Abschnitt
  „Page type: homeassistant“ mit Kurzbeispiel und Verweis.
- `config.example.yaml`: auskommentiertes Beispiel.
- Vorschaubilder `docs/img/templates/homeassistant-tiles.png` und `homeassistant-list.png` über
  `tools/render_previews.py` (SAMPLES), Beispielwerte ohne echte Namen oder IPs.
- `CHANGELOG.md`: Eintrag unter „Unreleased“.
- **README.md + README.de.md:**
  - Pitch (Zeile 11): „a status page from your Home Assistant“ durch eine korrekte Beschreibung
    ersetzen, sinngemäß „live values from Home Assistant, from solar power to open windows“.
  - Galerie: eine Spalte oder Zeile für `homeassistant` mit Vorschaubild. Der Satz „The `url` page
    type shows … for example a status page from Home Assistant“ wird ersetzt, das HA-Beispiel
    fällt dort weg.
  - Ein fairer Satz zur Abgrenzung: Wer die Originalfirmware behalten will, nimmt
    [geekmagic-hacs](https://github.com/adrienbrault/geekmagic-hacs), eine HA-Integration, die das
    Display mit der Originalfirmware ansteuert.

## 9. Dem Builder überlassen

IDs der Sim-Entitäten, Aufteilung der HA-YAML-Dateien, genaue Pixelmaße und Schriftstufen,
Umsetzung der Schriftverkleinerung, Name des Live-Markers, Wortlaut der Doku innerhalb der
obigen Vorgaben, Reihenfolge der Commits.
