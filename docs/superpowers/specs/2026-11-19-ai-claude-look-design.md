# ai-Seite: Claude-Look und Restanzeige – Design

Stand: 2026-11-19 · Ziel-Version: 0.5.1 · Größe: kleine Änderung (kurzes Design)

## Absicht

1. **Issue #6:** Die ai-Seite soll zeigen können, wie viel eines Limits **übrig** ist (Balken
   startet bei 100 % und läuft gegen 0 %), statt wie viel verbraucht ist.
2. **Claude-Look:** Das jetzige Design (blauer Kopf, Ampelbalken) „passt 0 zu den Claude-Sachen“.
   Die Seiten der Anbieter `claude` und `anthropic-api` sollen in Claudes Farben erscheinen.

## Ziele

- Neue Seitenoption `show: used | remaining`, Standard `used` (bestehende Setups ändern sich
  nicht). Gilt für **alle** Provider der ai-Seite: Claude-Limits, Budget-Zeile (`anthropic-api`,
  `openai-api`), Copilot-Kontingent.
  - Text und Balken wechseln beide: `58 %` übrig statt `42 %` verbraucht.
  - Überverbrauch (> 100 % verbraucht) zeigt `0 %` übrig, roter Balken.
  - Ein zurückgesetztes Fenster (Claude, `resets_at` vorbei) zeigt `100 %` übrig.
  - Farben behalten ihre Bedeutung: die Stufe wird immer aus dem **Verbrauch** berechnet, nicht
    aus dem angezeigten Wert. Rot heißt immer „knapp“.
- Claude-Look (Entwurf **A** „Dunkel wie claude.ai“, Brainstorming-Datei
  `.superpowers/brainstorm/61667-1795116520/content/claude-look.html`), automatisch bei
  `provider: claude` und `provider: anthropic-api`, ohne Einstellung:
  - Hintergrund warmes Anthrazit `#262624`, Kopfzeile `#1F1E1D` mit 1-px-Linie `#3A3936`.
  - Titel in Claude-Orange `#D97757`, **Serifenschrift** (DejaVu Serif Bold); Uhrzeit bleibt
    hell (`#FAF9F5`) in DejaVu Sans.
  - Text `#FAF9F5`, Nebentexte (Reset, Stand, Big-Label) `#A8A69C`, Balkenspur `#3A3936`,
    Balken mit 6 px Radius.
  - **Zwei Farbstufen** statt drei: Balken orange `#D97757`, rot `#E5534B` ab 75 % verbraucht
    (= 25 % übrig oder weniger).
  - Fehlerkopf (`alert`, „No data“) bleibt rot erkennbar.
- Version 0.5.1 mit CHANGELOG-Eintrag, Doku (en + de) zu `show:` und zum Look, Issue #6 wird
  geschlossen.

## Nicht-Ziele

- Kein allgemeines Theme-System, keine `theme:`-Option. Andere Seiten und andere ai-Provider
  (`openai-api`, `xai-api`, `copilot`) bleiben optisch unverändert.
- Keine Firmware-Änderung (der laufende 0.5.0-Soak auf dem Display bleibt ungestört).
- Kein heller Modus (Entwurf B verworfen: leuchtet nachts, fällt in der Rotation heraus).

## Anti-Ziele

- **Kein Logo**, keine Anthropic-Bildmarke, nichts, was wie ein offizielles Anthropic-Produkt
  wirkt. Nur Farben und der beschreibende Name „Claude“ (Repo ist öffentlich).
- Andere Seiten dürfen nicht langsamer oder größer werden (siehe Schrift unten).
- Ein Wechsel auf `remaining` darf die Farbbedeutung nicht umdrehen (grün/orange bei fast leerem
  Kontingent wäre ein Fehler).

## Randbedingungen

- Display 240×240, Rendering über Chromium, JPEG ≤ 24 KB (`MAX_JPEG_BYTES`).
- Schriften werden als base64 in **jedes** Seiten-HTML eingebettet (`font_face_css()` in
  `server/glancebox/render.py`). DejaVu Serif Bold (~300 KB) darf deshalb **nicht** in die
  globale Liste, sondern nur in die Claude-Variante der ai-Seite.

## Ansätze

1. **Provider meldet Theme, ai-Template setzt es um (gewählt).** `claude` und `anthropic-api`
   liefern `theme: "claude"`; `pages/ai/template.html` überschreibt in einem eigenen CSS-Block die
   Variablen und Balkenfarben. Klein, lokal, kein Risiko für andere Seiten; später zu (2)
   ausbaubar.
2. **Allgemeines Theme-System** (`theme:` als Option jeder Seite, Themes zentral in `base.html`).
   Verworfen: Konfigurationsfeld ohne heutigen Bedarf, und der Look soll automatisch kommen.
3. **Eigener Seitentyp `claude`.** Verworfen: bricht bestehende Konfigurationen, doppelte Logik.

## Entschiedenes Wie

- `EMPTY` in `pages/ai/page.py` bekommt `theme: None`; `claude.py` und `anthropic_api.py` setzen
  `theme: "claude"` (auch im `message`-Fall, damit „Noch keine Daten“ ebenfalls im Claude-Look
  erscheint).
- `show` wird in `page.validate` geprüft (`used`/`remaining`, sonst `ValueError`) und zentral in
  `page.fetch` auf die Zeilen angewendet: Provider liefern weiter `percent` = Verbrauch; die Seite
  ergänzt pro Zeile einen Stufenwert (Verbrauch) und rechnet bei `remaining` `percent` und `text`
  auf `max(0, 100 − Verbrauch)` um.
- `ui.bar` in `server/glancebox/templates/ui.html` bekommt einen optionalen Parameter für den
  Stufenwert (Standard: `percent`), damit andere Seiten unverändert bleiben.
- Serif-Schrift: `DejaVuSerif-Bold.ttf` (gleiche Lizenz wie die vorhandenen DejaVu-Dateien) neben
  die anderen Fonts; eingebettet nur, wenn `theme == "claude"`.

## Dem Builder überlassen

- Genaue Form der Template-Variablen und CSS-Selektoren; ob die Rundung von `text` bei
  `remaining` vor oder nach der Subtraktion passiert (Hauptsache 0 % ↔ 100 % konsistent).
- Tests in `pages/ai/test_ai.py` (Validierung, Umrechnung inkl. Überverbrauch und Reset, Stufe
  aus Verbrauch, Theme-Flag) und ein Render-Check, dass das JPEG unter dem Limit bleibt.
- Formulierung der Doku und des CHANGELOG-Eintrags.
