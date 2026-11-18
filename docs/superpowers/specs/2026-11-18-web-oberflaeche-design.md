# Neue Web-Oberfläche des Geräts – Design

Stand: 2026-11-18 · Ziel-Version: 0.5.0 · Größe: Projekt (volles Design)

## Absicht

Die Geräteseite (`http://<gerät>/`) sieht heute „übel billig“ aus: nackte HTML-Formulare,
Prozentwerte zum Eintippen. Sie soll **so schön wie möglich** werden, nach Apples
Gestaltungsregeln, und sich **wie eine Apple-App anfühlen**: Änderungen gelten sofort, die
Helligkeit ändert sich beim Schieben live auf dem Display. Die Seite muss am Handy **und** am
Mac/großen Bildschirmen gut aussehen.

Im selben Release (0.5.0) steckt der Helligkeits-Fix (Branch `fix/backlight-curve`: quadratische
Kurve, PWM-Bereich 1000), ohne den ein Helligkeitsregler kaum sichtbar wirken würde.

- **Ziele**
  - Look „Mischung A + B“ aus dem Brainstorming (Entwürfe in `.superpowers/brainstorm/…/content/`,
    `mix.html` und `desktop.html`): oben **Kacheln** wie in der Home-App, darunter **gruppierte
    Listen** wie in der iOS-Einstellungen-App.
  - Helligkeit und Nacht-Helligkeit als **breite Regler** wie im Kontrollzentrum; beim Schieben
    ändert sich das Display live.
  - **Kein „Sichern“-Knopf**: jede Einstellung wird übernommen, sobald sie fertig geändert ist.
  - Folgt automatisch Hell-/Dunkelmodus des Systems; Dunkelmodus mit Farbverlauf und
    „Glas“-Kacheln.
  - Responsiv: Handy einspaltig; ab etwa 720 px Breite vier Kacheln in einer Reihe und die Listen in
    zwei Spalten; Inhalt höchstens etwa 900 px breit.
  - Notfallmodus-Seite und Meldungsseiten (Fehler, „zurückgesetzt“ …) im selben Look.
- **Nicht-Ziele**
  - Das WLAN-Einrichtungsportal (WiFiManager) beim ersten Start; es bleibt, wie es ist.
  - Gerätename und Anzeige der aktuell gezeigten Server-Seite (bräuchten Server-Änderungen; später
    eigenes Thema).
  - Neue Einstellungen über die heutigen hinaus (der Nachtmodus-Schalter ist nur Bedienung, kein
    neues Feld).
- **Anti-Ziele** (wäre ein Fehlschlag, selbst wenn es „funktioniert“)
  - Die Seite lädt irgendetwas aus dem Internet (Schriften, Skripte, Bilder).
  - Live-Regler schreiben bei jeder Bewegung in den Flash (Verschleiß).
  - Ein Tippfehler (z. B. in der Server-Adresse) wird gespeichert und legt das Gerät lahm.
  - Notfallmodus oder OTA-Update werden unzuverlässiger als heute.
  - Die Firmware sprengt das Größenlimit (`firmware/size-limit.txt`) oder der freie Heap fällt
    spürbar (heute ca. 37 KB im Betrieb).

## Rahmenbedingungen (aus dem Projekt)

- ESP8266, `ESP8266WebServer` (single-threaded), Firmware 0.4.0 = 425 KB von ~1 MB OTA-Limit.
- Flash-Layout darf sich in einem OTA-Release nicht ändern (`docs/RELEASING.md`).
- Schreibende Aufrufe laufen über `webUiAuthorize()`: Origin-Prüfung (CSRF) + Basic Auth
  `admin`/Update-Passwort. Das bleibt für alle neuen Schnittstellen so.
- Sprache DE/EN über `Accept-Language` (`i18n.h/.cpp`, Texte im Flash).
- Settings-Validierung liegt in `lib/core` (`applyServerUrl`, `applyPassword`, `applyNight`,
  `clampBrightness`) und ist nativ getestet; neue reine Logik gehört ebenfalls dorthin, mit Tests.
- Lokal baut die ESP-Toolchain auf diesem Mac nicht („Bad CPU type“); das Firmware-Image baut die
  CI (`.github/workflows/ci.yml`, inkl. Größenprüfung). Native Tests laufen lokal.

## Ansätze

| | Ansatz | Abwägung |
|---|---|---|
| 1 | CSS/JS als zusätzliche C++-Strings in `web_ui.cpp` | Kleinste Änderung, aber schwer zu pflegen; ~5 KB gehen bei jedem Aufruf unkomprimiert übers WLAN. |
| **2 (gewählt)** | Echte Dateien `firmware/web/app.css` + `app.js`, beim Bauen verkleinert, gzip-komprimiert und als PROGMEM eingebettet; HTML rendert weiter die Firmware | Lesbarer Code, schnelle Seite, Browser-Cache; i18n, Notfallmodus und Auth bleiben wie sie sind. Kosten: ein Build-Skript. |
| 3 | Komplette JavaScript-App, Gerät liefert nur JSON | Am flexibelsten, aber größter Umbau (i18n, Notfallmodus ziehen um); ohne JS leer. |
| verworfen | Dateien in LittleFS | Kämen mit einem Firmware-OTA nicht mit; Flash-Layout darf nicht angefasst werden. |

Robin hat Ansatz 2 gewählt (meine Empfehlung).

## Design

### Aufbau der Seite (normaler Modus)

Kopf: „Glance Box“ groß, darunter klein `IP · Version x.y.z`.

**Kacheln** (Home-App-Stil, 2×2 am Handy, 4 in einer Reihe breit):
Verbindung (Online/Offline, grün/rot), Letztes Bild („vor 20 s“), WLAN in Worten, Läuft seit
(„1 T 21 h“). Die Kacheln aktualisieren sich alle 5 s über `GET /status` (gibt es schon).

**Gruppen** (iOS-Listen):
- **Anzeige:** Helligkeit (Regler 5–100), Nachtmodus (Schalter), Von, Bis (Uhrzeitfelder; nur
  aktiv/sichtbar wenn Nachtmodus an), Helligkeit nachts (Regler 0–100, 0 = „Aus“).
- **Server:** Adresse (Textfeld).
- **Gerät:** Firmware aktualisieren, Passwort ändern, Neu starten, Auf Werkszustand zurücksetzen
  (rot, mit Bestätigung).
- **Details** (eingeklappt oder kleine Zeilen, damit nichts verloren geht, was die Statustabelle
  heute zeigt): Bilder gesamt, Fehlstarts, Ortszeit, Nacht aktiv, Notfallmodus, Signal in dBm.

Am Mac: Anzeige links, Server/Gerät/Details rechts.

### Verhalten „sofort übernehmen“

- **Regler:** Beim Schieben (gedrosselt, höchstens ~10 Anfragen/s, immer der letzte Wert gewinnt)
  geht eine **Vorschau** ans Gerät: Display ändert sich sofort, **nichts wird gespeichert**. Beim
  Loslassen wird der Wert **gespeichert**.
- **Schalter Nachtmodus:** speichert sofort. Aus = Von und Bis gleich setzen (heutiges Format,
  „Start = Ende = aus“). An = die zuletzt auf der Seite gesehenen Zeiten, sonst 22:00–07:00.
- **Uhrzeiten, Server-Adresse:** speichern beim Verlassen des Feldes (bzw. Enter), nur wenn sich
  der Wert geändert hat.
- **Server-Adresse – Schutz vor Tippfehlern** *(meine Entscheidung)*: geprüft wird nur die Form
  (`applyServerUrl`: Schema, Host, Länge), **kein** Verbindungstest vor dem Speichern (der
  single-threaded Webserver wäre sekundenlang blockiert). Stattdessen zeigt die Seite nach dem
  Speichern der Adresse einige Sekunden lang „Rückgängig“; die Geräteseite bleibt bei einer falschen,
  aber gültig geformten Adresse erreichbar, nur das Display zeigt „offline“.
- **Rückmeldung:** kurzes ✓ neben dem Feld nach Erfolg; bei Fehler rote Markierung + Text aus der
  Firmware (übersetzt), der alte Wert bleibt auf dem Gerät gültig.
- **Passwort ändern:** bewusst **nicht** automatisch, sondern eigener kleiner Bereich mit Feld und
  Knopf „Ändern“ (der Browser muss danach das neue Passwort verwenden; die Seite sagt das). Läuft
  über `POST /api/settings` mit dem Feld `password` *(meine Entscheidung)*.
- **Firmware aktualisieren:** Datei wählen, MD5 wird im Browser ausgerechnet (das Gerät verlangt sie
  vor der Datei), Upload mit Fortschrittsbalken; das MD5-Feld bleibt als Fallback sichtbar/ausfüllbar.
- **Neu starten / Zurücksetzen:** Knöpfe wie heute, Zurücksetzen mit Bestätigungsdialog.
- **Passwortabfrage:** Der erste schreibende Aufruf löst wie heute die Basic-Auth-Abfrage des
  Browsers aus; danach schickt der Browser die Zugangsdaten selbst mit.

### Neue Schnittstellen der Firmware

Beide mit `webUiAuthorize()` (Origin + Basic Auth), Antwort JSON.

- `POST /api/brightness-preview` mit `pct` (0–100): setzt die Hintergrundbeleuchtung vorübergehend
  auf diesen Wert, speichert nichts. Der Main-Loop (`updateBacklight`) respektiert die Vorschau,
  bis **3 s** lang keine neue Vorschau kam; danach gilt wieder die effektive Helligkeit (Tag/Nacht).
  Reine Logik (Vorschau aktiv? welcher Wert gilt?) in `lib/core`, nativ getestet, millis-Überlauf
  beachten.
- `POST /api/settings` mit **beliebiger Teilmenge** der Felder `server_url`, `brightness`,
  `night_start`, `night_end`, `night_brightness`, `password` (8–32 Zeichen, `applyPassword`): validiert mit den bestehenden `gb::apply*`, ändert
  nur übergebene Felder, speichert einmal, antwortet `{"ok":true}` oder
  `{"ok":false,"field":"…","error":"<übersetzter Text>"}` mit 400. Nach dem Speichern wendet der
  Main-Loop die Helligkeit an (wie heute); im Notfallmodus gibt es die Route nicht.
  Die Teilmengen-Logik (Felder anwenden, Fehler pro Feld) in `lib/core`, nativ getestet.
- `GET /app.css` und `GET /app.js`: eingebettete gzip-Daten, `Content-Encoding: gzip`,
  `Cache-Control: no-cache` mit `ETag` = Inhalts-Hash (304, wenn unverändert). Die Seite
  referenziert sie zusätzlich mit `?v=<hash>`. *(Nach dem Security-Check vom 2026-11-18 geändert:
  Ein ein Jahr gültiger Cache würde über reines HTTP ein einmal untergeschobenes Skript
  dauerhaft machen.)* Alle HTML-Seiten senden `X-Frame-Options: DENY` und
  `Content-Security-Policy: frame-ancestors 'none'` (kein Einbetten in fremde Seiten).

`POST /settings` (heutiges Formular) bleibt für Clients ohne JavaScript und Skripte bestehen.
Ohne JavaScript zeigt die Seite die Felder in einem normalen Formular mit „Sichern“-Knopf
(`<noscript>`), damit nichts unbedienbar wird.

### Notfallmodus *(meine Entscheidung)*

Die Notfallmodus-Seite bekommt **nur das neue CSS** (Route `/app.css` in `beginCommon`, also in
beiden Modi), **kein JavaScript**: Sie bleibt ein normales Formular mit MD5-Feld wie heute. Der
Wiederherstellungsweg ändert sich damit nicht im Verhalten, nur im Aussehen.

### Build

- `firmware/web/app.css`, `firmware/web/app.js`: Quelltext, lesbar, kommentiert.
- PlatformIO-Pre-Skript `firmware/scripts/embed_web.py` (wie `version.py`): entfernt Kommentare und
  überflüssige Leerzeichen (einfacher eigener Minifier, **keine** npm-/Node-Abhängigkeit),
  komprimiert mit Pythons `gzip` (fester mtime, damit der Build reproduzierbar ist), schreibt einen
  Header mit `PROGMEM`-Arrays, Länge und kurzem Hash in ein generiertes, nicht eingechecktes
  Verzeichnis.
- Nur für `env:ultra` (und abgeleitete); `env:native` bleibt unberührt.

### Optik

- Systemschrift (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`), keine
  Web-Fonts.
- Farben/Abstände als CSS-Variablen; Hell: `#f2f2f7` Hintergrund, weiße Gruppen; Dunkel: Farbverlauf
  Blau-Violett, Kacheln/Gruppen halbtransparent mit `backdrop-filter`. Akzent iOS-Blau, Grün für
  Online, Rot für Gefahr; Regler-Füllung gelb (hell) bzw. weiß (dunkel), wie im Entwurf.
- Ziel-Budget: CSS + JS zusammen **≤ 8 KB gzip**; HTML-Antwort der Hauptseite ≤ 6 KB.
- Barrierefreiheit: echte `<input type=range>` (per CSS gestaltet), Labels, Fokus-Ring, ausreichend
  Kontrast, `prefers-reduced-motion` respektieren.

### Texte

Neue Texte (Gruppentitel, „vor … s“, WLAN-Worte, „Aus“, Speichern-Fehler, Passwort-Hinweis, …) in
`i18n` DE/EN. Texte, die das JavaScript braucht, rendert die Firmware als `data-`-Attribute oder
kleines JSON in die Seite; das JS enthält keine Übersetzungen.

WLAN in Worten (RSSI): ≥ −60 dBm „Sehr gut“, ≥ −70 „Gut“, ≥ −80 „Mäßig“, sonst „Schwach“.

### Tests und Prüfung

- Native Unity-Tests für neue Kernlogik (Vorschau-Zeitfenster, Teil-Settings).
- Build-Skript: kleiner Python-Test (Minifier lässt Strings/`url()` unverändert, gzip entpackt zum
  Original-Minifikat).
- CI baut das Image inkl. Größenprüfung.
- Hardware-Test erst **mit Robins Zustimmung** (OTA auf das Gerät <device-ip>): Helligkeitskurve
  sichtbar, Live-Regler, Speichern, Notfallmodus-Seite, OTA über die neue Seite, Heap in `/status`.
- Optischer Check im Browser hell/dunkel, Handy-/Desktop-Breite.

### Branch und Ablauf *(meine Entscheidung)*

- Der Helligkeits-Fix wird zuerst als eigener Commit auf `fix/backlight-curve` festgehalten; die
  Oberfläche baut auf diesem Branch auf (die Vorschau-Logik liegt neben `backlightDuty`).
- Der Plan endet mit einem fertigen, getesteten Branch inkl. CHANGELOG-Einträgen. OTA auf das Gerät,
  Versionssprung auf 0.5.0, Merge und Release sind eigene Schritte, jeweils erst nach Robins OK.

## Dem Builder überlassen

Exakte Pixelwerte, Animationen, Aufteilung von `web_ui.cpp` in Dateien, Name/Ort des generierten
Headers, Implementierung der MD5 im Browser (kleine eigene Funktion, keine Bibliothek aus dem Netz),
genaue Drosselung der Vorschau.
