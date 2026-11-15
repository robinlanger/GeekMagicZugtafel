# Vorlagen-Bibliothek – Design

Stand: 2026-11-15 · Status: Entwurf zur Freigabe (Builder-Check eingearbeitet)

## 1. Absicht und Warum

Die Glance Box kann heute zwei mitgelieferte Seiten (`bahn`, `clock`) und beliebige Webseiten
(`url`). Wer etwas anderes sehen will, muss selbst Python und HTML schreiben. Das Projekt soll
eine **große Bibliothek fertiger Seiten** bekommen, die man nur in die `config.yaml` einträgt.

Das Repo ist öffentlich. Die Bibliothek ist deshalb **für alle Nutzer** gebaut, nicht für ein
bestimmtes Setup: alles Persönliche steht in der YAML (bzw. `.env`), nichts im Code.

Die ersten drei Vorlagen:

1. **Wetter** – der Klassiker, den die Originalfirmware hatte, mit dem Standort aus der YAML.
2. **Server-Status** – „läuft auf meinem Server alles, ist etwas passiert?“, über ein
   etabliertes Monitoring-Programm (Uptime Kuma), **ohne** der Glance Box Rechte auf dem Server
   zu geben.
3. **KI-Limits** – Ersatz für teuer verkaufte Anzeigen, die zeigen, wie viel vom Limit bei
   KI-Anbietern verbraucht ist. Nur über Wege, die **sicher und erlaubt** sind.

Die Doku soll so aufgebaut sein, dass man sich **je nach Bedarf durchklicken** kann: vom
Vorlagen-Katalog zur einzelnen Vorlage mit allem, was man für genau diese braucht.

## 2. Ziele, Nicht-Ziele, Anti-Ziele

**Ziele**

1. Gemeinsamer Unterbau im Server: einheitliche Kopfzeile und Farben als Template-Bausteine,
   `${VAR}`-Verweise in der YAML, ein allgemeiner geschützter Daten-Eingang (Push).
2. Vorlage `wetter` (Open-Meteo).
3. Vorlage `kuma` (Uptime-Kuma-Statusseite).
4. Vorlage `ki` (KI-Limits, ein Anbieter pro Seite).
5. Doku: Vorlagen-Katalog (de/en) mit einer Seite pro Vorlage, Vorschaubild, Voraussetzungen,
   YAML-Beispiel und Einrichtungsschritten.

**Nicht-Ziele (diese Runde)**

- Weitere Monitoring-Programme (Beszel, Glances, Netdata). Die Architektur soll sie nicht
  verbauen.
- KI-Abo-Limits, die nur inoffiziell lesbar sind: Codex/ChatGPT (`wham/usage`), Gemini
  (`retrieveUserQuota`), SuperGrok (gar nicht lesbar). Gemini-API-Kosten (nur über
  BigQuery-Export).
- Eine Übersichtsseite mit allen KI-Anbietern zusammen.
- Auslastungswerte des Servers (CPU, RAM) auf der Status-Seite.
- Ein separates Repo für Vorlagen.

**Anti-Ziele** – das Ergebnis wäre trotz funktionierendem Code ein Fehlschlag, wenn:

- die Glance Box Root-Rechte auf einem Server braucht (Docker-Socket o. Ä.);
- eine Vorlage Zugangsdaten auf eine Weise nutzt, die die Bedingungen des Anbieters verletzt
  (z. B. den Claude-Code-Login-Token auf den Server kopieren und dort abfragen);
- eine Status- oder Limit-Seite bei fehlenden Daten „alles grün“ oder alte Werte ohne Hinweis
  zeigt;
- Tokens im Klartext in der `config.yaml` stehen müssen;
- die Seiten unterschiedlich aussehen, als kämen sie aus verschiedenen Projekten.

## 3. Rahmenbedingungen

- **Seitenvertrag** (siehe `docs/de/writing-pages.md`): Ordner unter `pages/<typ>/` mit
  `page.py` (`fetch(options, ctx)`, optional `validate`, `MIN_REFRESH`) und `template.html`
  (erweitert `base.html`). `fetch` läuft im Worker-Thread, max. 20 s, jeder Netzwerkaufruf mit
  Timeout. Wirft `fetch`, behält die Seite bis zu 10 min ihr letztes Bild.
- **Bild:** 240×240, JPEG ≤ 24 576 Bytes, flache Flächen und Text. Unterste ~8 px verdeckt das
  Gehäuse. Schriften: DejaVu Sans / Sans Condensed.
- **Bestehender Look** (`bahn`): Kopfzeile 34 px, `--header-bg` Blau, Titel links fett 16 px,
  Uhrzeit rechts fett 18 px; CSS-Variablen aus `base.html`.
- **Server** läuft im LAN ohne Authentifizierung (Glance-Box-Design, Abschnitt 9). Bisher nimmt
  er keine Daten an; Endpunkte: `/api/v1/frame`, `/preview/{i}.jpg`, `/`, `/healthz`.
- **Konfiguration** kennt heute keine Geheimnisse und keine Umgebungsvariablen in Werten.
- **Doku** ist zweisprachig; `tools/check_docs_parity.py` prüft in der CI, dass de und en
  zueinander passen.
- **Lizenz/Fairness:** öffentliche Dienste (Open-Meteo) schonend abfragen, Quelle in den Credits
  nennen.

## 4. Approaches (Wege, die Bibliothek zu bauen)

1. **Alles in diesem Repo nach dem Muster von `bahn`/`clock`, mit gemeinsamem Unterbau und
   allgemeinem Daten-Eingang.** Passt zum Bestehenden (ein Image, eine CI, eine Doku). Der
   Server wächst etwas. **Gewählt.**
2. Wie 1, aber der Daten-Eingang nur für Claude. Weniger Arbeit, aber Sonderlogik im Server,
   beim nächsten Push-Fall doppelt gebaut. Verworfen (Empfehlung; der Nutzer hat 1 ohne Einwand
   gewählt).
3. Vorlagen als eigenes Repo, eingehängt über `pages-custom`. Entkoppelt, aber zwei Repos, zwei
   CIs, verteilte Doku. Vom Nutzer verworfen („alles in ein Repo“).

Ebenfalls verworfen: Vorlagen als eigene Web-Apps hinter der `url`-Seite – jeder Nutzer müsste
weitere Dienste betreiben.

## 5. Entscheidungen

### 5.1 Gemeinsamer Unterbau

**Template-Bausteine.** Eine Jinja-Makro-Datei neben `base.html` (z. B. `ui.html`) mit
mindestens: Kopfzeile (Titel, Uhrzeit, Variante „Störung“ mit rotem Hintergrund), Hinweis-
Fläche für „Keine Daten · Stand HH:MM“, Fortschrittsbalken mit Farbstufen. Statusfarben als
CSS-Variablen in `base.html` (zusätzlich `--green`, `--blue` o. Ä.). `bahn` muss nicht umgebaut
werden, darf aber.

**Umgebungsvariablen in der YAML.** Ein String-Wert der Form `${NAME}` (ganzer Wert) wird beim
Laden durch die Umgebungsvariable `NAME` ersetzt. Fehlt sie, startet der Server nicht und nennt
Seite und Variable. `docker-compose.yml` reicht eine `.env` an den Container weiter
(`env_file`, optional). `.env` steht schon in `.gitignore`.

**Daten-Eingang (Push).** Ein allgemeiner Endpunkt, an den Skripte JSON schicken, z. B.
`POST /api/v1/push/<kanal>`. Eigenschaften:

- Geschützt mit einem Schlüssel aus der Konfiguration (über `${VAR}`), als Header
  `Authorization: Bearer …`. Ohne konfigurierten Schlüssel ist der Endpunkt aus (404 o. Ä.).
- Speichert den letzten Wert pro Kanal **im RAM** mit Empfangszeit; kein Schreiben auf Platte.
- Größenlimit für den Body (wenige KB), Kanalname aus einem engen Zeichensatz.
- Seiten lesen den letzten Wert über `ctx` (z. B. `ctx.pushed("claude")` → Daten + Zeitpunkt
  oder `None`). Eine Seite, deren Daten aus dem Push kommen, wird nach Empfang neuer Daten bei
  der nächsten Gelegenheit neu gerendert (Builder: wie genau, siehe 7).

### 5.2 Vorlage `wetter`

- **Quelle:** Open-Meteo (Forecast-API, kein Key). Ortsname über die Open-Meteo-Geocoding-API
  einmal auflösen und im Prozess merken.
- **YAML:** `location: Frankfurt` **oder** `latitude`/`longitude`; optional `title`
  (Standard: Ortsname), `lang`. `MIN_REFRESH` = 900 (15 min).
- **Layout C** (vom Nutzer gewählt): Kopfzeile Ort + Uhrzeit. Groß: Wettersymbol,
  Temperatur (z. B. 46 px fett), Beschreibung („Leicht bewölkt“). Darunter Höchst-/Tiefstwert
  des Tages (rot ↑ / blau ↓). Unten die nächsten 4 vollen Stunden: Uhrzeit, Temperatur,
  Regenwahrscheinlichkeit (blau).
- **Symbole:** eigene, schlichte Inline-SVGs, abgeleitet aus dem WMO-Wettercode, mit
  Nachtvarianten (klar, wolkig, Regen, Schnee, Gewitter, Nebel …). Beschreibungen de/en.
- **Fehler:** Open-Meteo nicht erreichbar → Fehler werfen (letztes Bild bis 10 min ist bei
  Wetter in Ordnung), danach greift das normale Verhalten des Servers.

### 5.3 Vorlage `kuma`

- **Quelle:** öffentliche Statusseite einer Uptime-Kuma-Instanz:
  `GET <url>/api/status-page/<slug>` (Monitore, Gruppen) und
  `GET <url>/api/status-page/heartbeat/<slug>` (letzte Heartbeats, Uptime-Werte). Kein Token,
  keine Rechte auf dem Server.
- **YAML:** `url`, `slug`, optional `title` (Standard: Titel der Statusseite).
- **Layout A** (vom Nutzer gewählt):
  - *Alles gut:* blaue Kopfzeile, großer grüner Haken, „14/14 OK“, darunter eine graue
    Zeile mit einer Zusatzinfo (z. B. „seit 6 Tagen kein Ausfall“ oder, falls die Daten das
    nicht hergeben, „Verfügbarkeit 24 h: 99,9 %“ – Builder entscheidet nach Datenlage).
  - *Störung:* Kopfzeile rot, groß „2 gestört“ (rot), „12 von 14 laufen“, darunter die
    gestörten Dienste als Zeilen mit rotem Punkt und „seit 12 min“. Mehr als ~4 → letzte Zeile
    „+ N weitere“. Monitore im Status „pending“/„maintenance“ zählen nicht als gestört, werden
    aber in Orange angezeigt, wenn Platz ist (Builder-Entscheidung).
- **Fehler:** Kuma nicht erreichbar → die Seite fängt den Fehler ab und zeigt sofort
  „Keine Verbindung zu Uptime Kuma · Stand HH:MM“ in Orange (wie `bahn` „Keine Daten“), **nie**
  ein altes grünes Bild.
- **Doku zur Vorlage:** Kurzanleitung Uptime Kuma installieren (docker compose), Monitore
  anlegen, Statusseite anlegen. Zwei Wege für Container: (a) HTTP-Monitore auf die Webadressen
  der Dienste (empfohlen, keine Rechte nötig), (b) Kumas Docker-Monitor nur über einen
  Socket-Proxy mit Leserechten auf Container-Infos, mit klarem Hinweis, dass dann *Kuma*
  Zugriff auf Docker hat.

### 5.4 Vorlage `ki`

Ein Anbieter pro Seite (`provider:` in der YAML). Wer mehrere nutzt, trägt mehrere Seiten ein.
**Layout F mit großen Balken** (vom Nutzer gewählt): Kopfzeile mit Anbietername, pro Limit eine
Zeile „Name · Reset-Info“ und darunter ein breiter Balken (~30 px hoch), in dem der Wert steht.
Balkenfarbe nach Füllstand: grün, ab 75 % orange, ab 90 % rot. Unten klein „Stand HH:MM“, wenn
die Daten nicht frisch abgefragt sind.

Anbieter in dieser Runde (alle offiziell dokumentiert):

| `provider` | Daten | Weg | Zugang |
|---|---|---|---|
| `claude` | Abo-Limit 5 h und Woche: Prozent + Reset | **Push**: ein mitgeliefertes Statuszeilen-Skript für Claude Code liest `rate_limits.five_hour` / `seven_day` (`used_percentage`, `resets_at`) aus dem JSON, das Claude Code der Statuszeile gibt, und schickt sie an den Daten-Eingang (Kanal z. B. `claude`). Das Skript gibt danach ganz normal eine Statuszeile aus bzw. ruft eine vorhandene auf. | Push-Schlüssel auf dem Rechner des Nutzers; kein Anthropic-Token verlässt den Rechner |
| `copilot` | AI-Credits (seit 1.6.2026) oder Premium-Requests (Jahresabos im alten Modell): verbraucht/Kontingent, Reset-Datum | Billing-Usage-API `GET /users/{username}/settings/billing/{ai_credit,premium_request}/usage` (Prüfung Task 9: dokumentiert, liefert nur den Verbrauch; `account.getQuota` im Copilot SDK ist JSON-RPC in eine laufende Copilot CLI, keine HTTP-API) – das Kontingent trägt der Nutzer als `monthly_allowance` ein | Fine-grained PAT mit Nutzerrecht „Plan“ (lesen) über `${VAR}`; nur selbst gekaufte Abos |
| `anthropic-api` | Kosten im laufenden Monat (USD) | Usage & Cost API der Anthropic-Organisation | Admin-Key `sk-ant-admin…` über `${VAR}` |
| `openai-api` | Kosten im laufenden Monat (USD) | `GET /v1/organization/costs` | Admin-Key über `${VAR}` |
| `xai-api` | Prepaid-Guthaben (und ggf. Monatsverbrauch) | Management API `…/billing/teams/{team_id}/prepaid/balance` | Management-Key + `team_id` über `${VAR}` |

Für Anbieter ohne Limit (API-Kosten) zeigt die Seite den Betrag groß; ein Balken erscheint nur,
wenn der Nutzer in der YAML ein eigenes Budget angibt (`budget: 50`). Builder-Entscheidung, ob
das in dieser Runde mitkommt.

**Statuszeilen-Skript (Entscheidung Claude, korrigierbar):** Das Skript parst nichts. Es
reicht das JSON, das Claude Code ihm über stdin gibt, **im Hintergrund** mit kurzem Timeout
(z. B. `curl -m 2 … &`) an den Daten-Eingang weiter. Der Server zieht `rate_limits` selbst
heraus und verwirft den Rest. So braucht das Skript nur `sh` + `curl` (macOS/Linux) bzw.
PowerShell (Windows), blockiert die Statuszeile nie und ändert sie nicht. Eine vorhandene
eigene Statuszeile ruft es danach unverändert auf.

**Nur im Heimnetz (Entscheidung des Nutzers):** Der Daten-Eingang ist wie der ganze Server nur
im LAN über HTTP erreichbar. Unterwegs schlägt das Senden leise fehl (kurzer Timeout, keine
Fehlermeldung in der Statuszeile); die Box zeigt den letzten Stand mit Uhrzeit, nach der
Rückkehr ist er mit der nächsten Antwort von Claude Code wieder aktuell. Keine Doku und keine
Härtung für Zugriff aus dem Internet; die Doku rät ausdrücklich davon ab, den Server ins
Internet zu stellen.

**Copilot nur offiziell:** Gibt es keine offizielle Schnittstelle, die mit einem passenden
Token funktioniert, fällt `copilot` aus dieser Runde heraus (folgt aus „nur sicher und
erlaubt“). Der Plan behandelt `copilot` deshalb als Prüfschritt, der mit „gestrichen“ enden
darf; die Doku verspricht ihn erst, wenn er gebaut ist.

**Claude-Besonderheiten:** Die Werte kommen nur, solange Claude Code läuft. Die Seite zeigt
immer das Alter („Stand 13:58“). Liegt `resets_at` in der Vergangenheit, zeigt der Balken 0 %
mit „zurückgesetzt“. Nie empfangen → Hinweis „Noch keine Daten – Statuszeilen-Skript
einrichten“.

**Sicherheitshinweise in der Doku:** Der Anthropic-Admin-Key hat volle Rechte über die
Organisation; die Doku sagt das deutlich und empfiehlt eine eigene Organisation oder den
Verzicht. Für OpenAI wird ein Key mit möglichst engen Rechten empfohlen (falls verfügbar).

### 5.5 Doku

- Neuer Bereich **Vorlagen-Katalog** `docs/de/templates/README.md` + `docs/en/templates/…`
  (Name Builder-Entscheidung), verlinkt aus beiden READMEs und aus `configuration.md`.
- Der Katalog ist nach Bedarf gegliedert („Wetter & Zeit“, „Server & Smart Home“,
  „KI & Entwicklung“, „Verkehr“) mit Vorschaubild und Einzeiler pro Vorlage.
- Jede Vorlage hat eine eigene Seite: Vorschaubild, was du brauchst, YAML-Beispiel,
  alle Optionen, Einrichtung Schritt für Schritt (z. B. Kuma installieren, Statuszeilen-Skript
  einrichten), Datenschutz/Sicherheit, Fehlerbilder.
- `bahn` und `clock` wandern in den Katalog. Bestehende `pages/<typ>/README.md` bleiben als
  kurze Entwickler-Notiz oder verlinken auf die Katalogseite (Builder-Entscheidung).
- Vorschaubilder entstehen mit dem vorhandenen `render`-Befehl aus Test-Fixtures.

## 6. Reihenfolge

1. Unterbau (Bausteine, `${VAR}`, Daten-Eingang) mit Tests und Doku.
2. `wetter`.
3. `kuma`.
4. `ki` (zuerst `claude` per Push, dann die übrigen Anbieter).
5. Katalog-Doku vervollständigen (wächst mit jeder Vorlage mit).

Nach jedem Schritt ist etwas Benutzbares fertig.

## 7. Dem Builder überlassen

- Genaue Namen (Vorlagen `wetter` vs. `weather`, Endpunkt, Makro-Datei, Katalog-Pfad).
- Wie eine Push-Seite nach neuen Daten neu gerendert wird (sofort anstoßen oder beim nächsten
  `refresh`).
- Kuma: welche Zusatzzeile, Umgang mit pending/maintenance, Gruppen.
- Copilot: konkrete Schnittstelle und Token-Typ.
- Budget-Balken für API-Kosten.
- Tests: wie bei `bahn` mit aufgezeichneten Antworten (Fixtures), kein Netz in der CI.
