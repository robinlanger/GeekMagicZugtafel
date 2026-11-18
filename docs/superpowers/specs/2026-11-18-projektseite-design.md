# Projektseite auf GitHub Pages – Design

Stand: 2026-11-18 · Größe: Projekt (volles Design)

## Absicht

Glance Box hat eine gute, zweisprachige Doku, aber nur als Markdown im Repo. Gewünscht ist ein
**schöner öffentlicher Auftritt mit klarer Anleitung**: Wer das Projekt zum ersten Mal sieht,
soll begeistert sein und dann geführt vom Gerätekauf bis zum ersten Bild auf dem Display kommen.

- **Ziele**
  - Startseite im Stil einer Apple-Produktseite, **clean in Weiß** (Entwurf „A in Weiß“,
    `.superpowers/brainstorm/84602-1795035393/content/landing-white.html`): große Überschrift
    „Dein Display. Deine Seiten.“, Hero-Foto, grauer Abschnitt „In drei Schritten zum ersten
    Bild“ mit Links in die Anleitung, Galerie der Vorlagen, drei Stärken.
  - **Geführte Anleitung** in fünf Schritten (Gerät besorgen → Firmware flashen → WLAN
    einrichten → Server starten → Seiten auswählen) mit Fortschrittsbalken, nummerierten
    Teilschritten, Hinweisboxen und Weiter/Zurück.
  - Die bestehende Doku (Konfiguration, Updates, Notfall, eigene Seiten, Vorlagen) als
    Nachschlage-Teil derselben Seite, mit Navigation, Suche und Umschalter DE/EN.
  - Automatisch veröffentlicht bei jedem Push auf `main`.
- **Nicht-Ziele**
  - GitHub-Wiki (zweite Kopie der Doku ohne CI-Check; bleibt leer/aus).
  - Eigene Domain, Blog, Shop, Kommentare, Newsletter.
  - Neue Produktfeatures.
- **Anti-Ziele**
  - Die Seite lädt etwas von fremden Servern (Google Fonts, CDNs, Analytics/Tracking).
  - Doku muss an zwei Stellen gepflegt werden oder die Seite widerspricht der Doku im Repo.
  - Platzhalter wie „Screenshot folgt“ auf der öffentlichen Seite.
  - Persönliche Daten auf der Seite (Heim-IPs, E-Mail, Heimbahnhof); Beispiele nutzen neutrale
    Werte wie `192.168.1.50`.
  - Die bestehenden CI-Checks (Doku-Parität DE/EN) brechen.

## Rahmenbedingungen (aus dem Projekt)

- Doku liegt in `docs/en/**` und `docs/de/**` mit gleicher Überschriften-Struktur
  (`tools/check_docs_parity.py`, Job `docs` in `ci.yml`). Bilder in `docs/img/`.
- `docs/superpowers/**` (Specs, Pläne) gehört **nicht** auf die Seite.
- Einige Doku-Links zeigen aus `docs/` heraus (`../../README.md#quickstart`,
  `../../README.de.md#schnellstart`); auf der Seite müssen sie funktionieren.
- Repo: `robinlanger/glancebox`, öffentlich, Pages noch nicht aktiv, Wiki an (leer). Seite unter
  `https://robinlanger.github.io/glancebox/`.
- Keine Fotos vom Flash-Ablauf, vom Update-Menü der Original-Firmware oder vom
  Einrichtungsportal vorhanden.
- Rulesets schützen `main` und `v*`-Tags (kein Force-Push); die Seite braucht keine Tags.

## Ansätze

| | Ansatz | Abwägung |
|---|---|---|
| A | Handgemachte Einzelseite in `site/` + Links auf Markdown bei GitHub | Freier Look, aber Anleitung bleibt die GitHub-Ansicht ohne Suche/Navigation. |
| **B (gewählt)** | **MkDocs + Material** baut aus `docs/` eine Doku-Seite; eigene Startseite und geführte Anleitung | Schöner Auftritt und klare Anleitung in einem; Doku nur an einer Stelle; kleine Python-Build-Abhängigkeit. |
| C | Astro + Starlight | Sehr schick, aber komplettes Node-Projekt im sonst Python/C++-Repo; wenig Gewinn gegenüber B. |
| verworfen | GitHub-Wiki | Zweite, ungeprüfte Kopie der Doku. |

Robin hat B gewählt (meine Empfehlung) und für die Startseite den Stil A „in einem schönen,
cleanen White-Look“.

## Design

### Aufbau der Seite

```
/                 Startseite EN   (/de/ Startseite DE)
/guide/1-get-the-device/ … /guide/5-choose-pages/   Anleitung (DE: /de/guide/…)
/setup/ /configuration/ /updating/ /recovery/ /flashing/ /writing-pages/
/templates/ (+ eine Seite je Vorlage)
```

Navigation oben (Reiter): **Anleitung · Vorlagen · Eigene Seiten · Hilfe**, rechts Suche,
Sprache und ein schlichter GitHub-Link. Links in der Anleitung: die fünf Schritte; darunter
„Danach“: Geräteseite & Nachtmodus (`setup`), Updates (`updating`), Konfiguration
(`configuration`). **Hilfe** *(meine Entscheidung)*: Notfall & Wiederherstellung (`recovery`),
Firmware-Backup & Flash-Details (`flashing`), Sicherheit (Abschnitt in `setup` bzw. Link auf
`SECURITY.md`). Rechts „Auf dieser Seite“.

**Keine Live-Abfragen an GitHub** *(meine Entscheidung)*: Materials Repo-Widget (Sterne,
Version per `api.github.com` im Browser) wird nicht benutzt. Die aktuelle Version steht in der
Fußzeile und kommt beim Bauen aus `VERSION`; `VERSION` gehört deshalb zu den Auslösern des
Pages-Workflows.

### Startseite (eigenes Template, nicht aus Markdown)

Inhalt wie im Entwurf, Texte aus dem README abgeleitet, je Sprache:
1. Kopf: Kicker „Open Source · ohne Löten“, H1 „Dein Display. Deine Seiten.“ /
   „Your display. Your pages.“, ein Satz Lead, Buttons „In 15 Minuten loslegen“ (→ Schritt 1)
   und „Auf GitHub ansehen ›“, darunter `docs/img/hero.jpg` mit runden Ecken.
2. Grauer Abschnitt „In drei Schritten zum ersten Bild.“ – drei Karten (Gerät besorgen /
   Im Browser flashen / Server starten), jede mit Link in die Anleitung.
3. „Fertige Vorlagen.“ – Galerie aus `docs/img/templates/*.png` mit Bildunterschrift, jeweils
   Link auf die Vorlagen-Seite; dazu `on-device.jpg` als Foto vom echten Gerät.
4. Drei Stärken (sichere Updates, schöne Geräteseite, keine Cloud/MIT).
5. Fußzeile: MIT-Lizenz, Link zu Releases und Sicherheitsrichtlinie (`SECURITY.md`).

Die Startseiten-Texte stehen in den Markdown-Dateien `docs/en/index.md` und `docs/de/index.md`
(Front-Matter mit `template: home.html` und den Texten als Felder). *(Meine Entscheidung:)*
`tools/check_docs_parity.py` vergleicht zusätzlich die Front-Matter-Schlüssel beider Sprachen
(mit Test), damit eine Sprache nicht still Felder verliert.

### Geführte Anleitung (neue Markdown-Seiten)

Neue Dateien `docs/en/guide/1-get-the-device.md` … `5-choose-pages.md` und dieselben Namen unter
`docs/de/guide/`. Inhalt **kurz und geführt**, aus `README` (Quickstart), `flashing.md`,
`setup.md` und `configuration.md` zusammengestellt; für Details verlinken sie auf die
Nachschlage-Seiten statt sie zu kopieren.

Jede Seite: Kopfzeile „Schritt n von 5 · etwa x Minuten“, Fortschrittsbalken, nummerierte
Teilschritte (als gestaltete Liste), Hinweis-/Warnboxen (Material „admonitions“), am Ende
Weiter/Zurück.

| Schritt | Inhalt (Kern) |
|---|---|
| 1 Gerät besorgen | GeekMagic SmallTV Ultra (nicht „Pro“/andere Modelle), was du sonst brauchst (2,4-GHz-WLAN, Rechner mit Docker im Heimnetz). Kein Kauf-Link zu einem Händler (neutral bleiben). |
| 2 Firmware flashen | Release-Datei laden, IP des Displays finden, Update-Menü der Original-Firmware, hochladen, warten. Optionales Backup nur als Verweis auf `flashing.md`. |
| 3 WLAN einrichten | Netz `GlanceBox-XXXX`, Portal-Felder (WLAN, Server-URL, Update-Passwort, Helligkeit), Speichern. |
| 4 Server starten | Docker Compose: Repo/Dateien holen, `config.yaml` aus Beispiel, `docker compose up -d`, prüfen. |
| 5 Seiten auswählen | Vorlagen in `config.yaml` eintragen, Geräteseite öffnen (Helligkeit, Nachtmodus), wohin als Nächstes. |

### Bilder

Keine echten Fotos vom Ablauf vorhanden. Daher:
- **Echte Bilder**, wo möglich: `hero.jpg`, `on-device.jpg`, Vorlagen-Vorschauen, und ein
  neuer Screenshot der Geräteseite (hell, Handy- und Desktop-Breite) aus einer Testseite mit
  neutralen Werten (IP `192.168.1.50`), **nicht** vom echten Gerät.
- **Schlichte Illustrationen** (SVG, im Seitenstil: weiße Flächen, feine Linien, iOS-Blau als
  Akzent) für: Update-Menü der Original-Firmware (stilisiert, ohne fremdes Branding),
  Einrichtungsportal am Handy, Ablauf „Gerät → WLAN → Server → Display“.
- Keine Platzhalter auf der Seite.

### Look

Material for MkDocs, über `extra.css` an den Entwurf angepasst:
- Weiß/`#f5f5f7`, Text `#1d1d1f`, Sekundärtext `#6e6e73`, Akzent `#0071e3`/Links `#0066cc`.
- Systemschrift (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`);
  Material-Google-Fonts **aus** (`theme.font: false`).
- Großzügige Abstände, runde Ecken (Bilder 14–22 px, Karten 20 px), Pillen-Buttons.
- Dunkelmodus: Material-Umschalter vorhanden, Startseite bleibt auch dunkel lesbar (gleiche
  Struktur, dunkle Flächen); Standard ist hell.
- Responsiv: Startseiten-Karten/Galerie brechen am Handy um.

### Technik

- `mkdocs.yml` im Repo-Root, `docs_dir: docs`; `docs/superpowers/**` und `docs/RELEASING.md`
  ausgeschlossen.
- Plugins: Suche (lokal, Material), `mkdocs-static-i18n` (Ordnerstruktur `docs/en`,
  `docs/de`; EN Standard unter `/`, DE unter `/de/`).
- `overrides/` (custom_dir) mit `home.html` für die Startseite.
- Versionierte Abhängigkeiten in `requirements-docs.txt` (exakte Versionen).
- Workflow `.github/workflows/pages.yml`: bei Push auf `main` (Pfade `docs/**`, `mkdocs.yml`,
  `overrides/**`, `README*`, Workflow selbst) und manuell; `mkdocs build --strict`,
  `actions/upload-pages-artifact` + `actions/deploy-pages`. Im CI-Job `docs` zusätzlich
  `mkdocs build --strict` auf Pull Requests, damit kaputte Links vor dem Merge auffallen.
- Links aus `docs/` heraus (README-Anker) werden auf Seiten innerhalb der Doku umgebogen (z. B.
  auf Schritt 4 der Anleitung), sodass `--strict` sauber durchläuft und GitHub-Ansicht wie
  Seite funktionieren.
- Pages in den Repo-Einstellungen aktivieren (Quelle: GitHub Actions) und die Homepage-URL des
  Repos setzen; README bekommt oben einen Link zur Seite. *(Meine Entscheidung:)* Das geht wie
  bisher über einen PR; Pages-Aktivierung und Homepage-URL setze ich per `gh` nach dem Merge.
  Das Wiki bleibt, wie es ist (an, leer), es wird nicht verlinkt.
- Paritätsprüfung DE/EN deckt die neuen Seiten automatisch ab (`docs/en/**` ↔ `docs/de/**`).

### Prüfung

- `mkdocs build --strict` lokal und in CI ohne Warnungen.
- Lokale Vorschau (`mkdocs serve`) hell/dunkel, Handy- und Desktop-Breite, DE und EN.
- Netzwerk-Check der gebauten Seite: keine Anfragen an fremde Hosts (grep im `site/` nach
  `fonts.googleapis`, `http://`/`https://` außer GitHub-Links).
- Paritätsprüfung grün.
- Nach dem ersten Deploy: Seite unter der Pages-URL öffnen.

## Dem Builder überlassen

Genaue Texte der Startseite und der Anleitung (Ton: wie README, kurz, freundlich, du-Form im
Deutschen), Pixelwerte, Illustrationen im Detail, genaue Plugin-Versionen, Aufteilung von
`extra.css`, ob die Galerie per Markdown-Liste oder im Template steht.
