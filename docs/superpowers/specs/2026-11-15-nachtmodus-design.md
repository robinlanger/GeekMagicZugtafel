# Nachtmodus – Design

Stand: 2026-11-15 · Ziel-Version: 0.2.0 · Größe: kleine Änderung (kurzes Design)

## Absicht

Steht das Display im Schlafzimmer, soll es nachts dunkel sein, wie es die Originalfirmware auch
kann. Der Zeitraum und die Nacht-Helligkeit werden **auf der Weboberfläche des Geräts** eingestellt,
nicht in der `config.yaml` des Servers.

- **Ziele:** Zeitraum (z. B. 22:00–07:00, auch über Mitternacht) und Nacht-Helligkeit 0–100 %
  einstellbar; 0 % = Hintergrundbeleuchtung ganz aus. Keine zusätzliche Einstellung für Zeitzone
  oder Sommerzeit.
- **Nicht-Ziele:** mehrere Zeiträume, Wochentage, Sonnenauf-/-untergang, Helligkeitssensor,
  Steuerung über Home Assistant.
- **Anti-Ziele:** Das Display wird nachts hell, obwohl der Nachtmodus aktiv sein müsste (außer im
  unten beschriebenen Kaltstart-Fall). Ein Update oder ein Fehler darf den Nachtmodus nicht dauerhaft
  „verklemmen“ (z. B. Display bleibt tagsüber aus).

## Ansätze

| | Ansatz | Abwägung |
|---|---|---|
| **A (gewählt)** | Server schickt die Ortszeit mit jedem Frame; das Gerät zählt mit `millis()` weiter | Keine neue Einstellung, Zeitzone + Sommerzeit kommen aus der Server-Config. Kaltstart nachts ohne Server: Uhrzeit unbekannt → bleibt hell, bis der Server antwortet. |
| B | NTP auf dem Gerät + POSIX-TZ-String | Serverunabhängig, aber ein fehleranfälliges Zeitzonenfeld für Nutzer. |
| C | Server entscheidet die Nacht | Widerspricht „Einstellung auf der Geräteseite“. |

Robin hat A gewählt (Zeitquelle war ihm egal; A ist meine Empfehlung).

## Design

**Server**
- Jede Antwort von `GET /api/v1/frame` (200, 304 und Fehlerframes) trägt `X-Local-Time: HH:MM:SS`,
  die aktuelle Ortszeit in der konfigurierten `timezone`.

**Firmware**
- Neue Einstellungen in `Settings`: `nightStart`, `nightEnd` (Minuten seit Mitternacht, 0–1439) und
  `nightBrightness` (0–100). Standard: Start = Ende = 0 → Nachtmodus aus. JSON-Schlüssel
  `night_start`, `night_end`, `night_brightness`; alte Settings-Dateien ohne diese Schlüssel laden
  mit den Standardwerten (Parser behält fehlende Schlüssel schon heute bei Default).
- Zeit: Bei jeder Antwort mit gültigem `X-Local-Time` merkt sich das Gerät (Sekunde des Tages,
  `millis()`). Die aktuelle Zeit ergibt sich daraus modulo 24 h. Ohne bisherige Synchronisation gilt
  die Zeit als unbekannt → Tag-Helligkeit.
- Nacht aktiv, wenn Start ≠ Ende und die Zeit im Intervall liegt; Start > Ende bedeutet über
  Mitternacht (22:00–07:00). Start inklusive, Ende exklusiv.
- Die Entscheidung läuft in der Hauptschleife (z. B. alle paar Sekunden) und setzt die
  Hintergrundbeleuchtung nur bei Wechsel. Bilder werden nachts weiter geholt und gezeichnet.
- Auch Offline-Bildschirm und Statusanzeigen (z. B. „Firmware update“) folgen der aktuellen
  Helligkeit, nachts also dunkel.
- Safe Mode ignoriert den Nachtmodus (holt keine Frames, kennt keine Zeit; Sichtbarkeit zählt dort).
- Weboberfläche (DE/EN): drei neue Felder „Nacht von“, „Nacht bis“ (`type=time`) und
  „Helligkeit nachts (%)“ (0–100). Hinweis: „Gleiche Zeiten = Nachtmodus aus.“ Das Einrichtungsportal
  bekommt die Felder nicht (Ersteinrichtung bleibt kurz).
- `/status` bekommt `local_time` (`"HH:MM"` oder `null`) und `night` (true/false).
- Die Tag-Helligkeit bleibt bei 5–100 % (0 nur nachts erlaubt, damit das Display tagsüber nie
  versehentlich „kaputt“ wirkt).

**Tests**
- Native Tests für Intervall-Logik (über Mitternacht, Grenzen, Start = Ende), Zeit-Parser
  (`HH:MM:SS`, kaputte Werte), Zeitfortschreibung inkl. `millis()`-Überlauf, Settings-Encoding/
  Parsing alt ↔ neu.
- Server-Test: Header auf 200/304/Fehler, Zeitzone wird beachtet.
- Am Gerät: Zeitraum um die aktuelle Uhrzeit legen → Display geht aus und wieder an; Server stoppen
  während der Nacht → bleibt dunkel; OTA nachts → Statusanzeige dunkel, Gerät startet und wird nach
  der ersten Antwort wieder dunkel.

**Doku**
- `docs/{de,en}/setup.md`: Abschnitt Nachtmodus. `CHANGELOG.md` unter Unreleased.

## Dem Umsetzer überlassen

Genaues Prüfintervall in der Hauptschleife, Formulierung der UI-Texte, Lage der Felder auf der Seite.
