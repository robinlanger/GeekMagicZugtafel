# Zugtafel 🚆

Zeigt die nächsten Abfahrten eines Bahnhofs auf einem **GeekMagic SmallTV** (Ultra oder Pro) an, **ohne die Firmware zu flashen**. Ein kleiner Docker-Container holt jede Minute die Abfahrten, rendert ein 240×240-Bild und lädt es per HTTP aufs Display.

```
DBF (dbf.finalrewind.org) ──JSON──▶ zugtafel ──JPEG/HTTP──▶ GeekMagic SmallTV
```

![Vorschau](docs/vorschau.png)

Angezeigt werden pro Zeile: Linie, Ziel, Minuten bis zur Abfahrt, Planzeit, Verspätung und Gleis (orange bei Gleiswechsel). Ausfälle werden rot markiert.

## Schnellstart

```bash
git clone <dein-repo> zugtafel && cd zugtafel
cp .env.example .env
nano .env            # STATION und DEVICE_IP eintragen
docker compose up -d --build
docker compose logs -f
```

Den genauen Bahnhofsnamen findest du auf <https://dbf.finalrewind.org>: Die URL nach der Suche (z. B. `.../Musterstadt`) ist der Wert für `STATION`.

**Tipp:** Vergib dem Display im Router eine feste IP-Adresse.

## Konfiguration (`.env`)

| Variable | Standard | Beschreibung |
|---|---|---|
| `STATION` | – | Bahnhof (Name, EVA-Nr. oder DS100) |
| `DEVICE_IP` | – | IP-Adresse des Displays |
| `DEVICE_PROFILE` | `ultra` | `ultra` (ESP8266) oder `pro` (ESP32) |
| `VIA` | – | Nur Züge über diesen Halt, z. B. `Frankfurt(Main)Hbf` |
| `PLATFORMS` | – | Nur diese Gleise, z. B. `1,2` |
| `TITLE` | Bahnhof | Eigene Überschrift |
| `LIMIT` | `5` | Anzahl Zeilen (1–6) |
| `INTERVAL` | `60` | Aktualisierung in Sekunden (min. 60) |
| `DBF_URL` | `https://dbf.finalrewind.org` | Eigene DBF-Instanz möglich |
| `DRY_RUN` | `0` | `1` = Bild nur lokal speichern statt hochladen |

## Lokal testen (ohne Display)

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt pytest
pytest -q
STATION="Frankfurt(Main)Hbf" DRY_RUN=1 python -m zugtafel --once   # erzeugt zugtafel.png
```

## Hinweise

- **Datenquelle:** [DBF / db-infoscreen](https://github.com/derf/db-fakedisplay) von derf, ein privat betriebener, kostenloser Dienst. Bitte max. eine Anfrage pro Station und Minute; das Programm hält sich daran. Für mehr Last lässt sich DBF selbst per Docker betreiben (`DBF_URL`).
- **Display-API:** Upload über `/doUpload?dir=/image/`, danach wird das Bild über `/set?theme=…` und `/set?img=…` angezeigt (Ultra). Beim **Pro** zeigt der Album-Modus alle Bilder im Wechsel: im Webinterface andere Bilder löschen und den Picture-Modus wählen.
- **Flash-Speicher:** Es wird nur hochgeladen, wenn sich das Bild geändert hat. Da Uhrzeit und Minuten-Countdown sich jede Minute ändern, ist das praktisch jede Minute.

## Lizenz

MIT
