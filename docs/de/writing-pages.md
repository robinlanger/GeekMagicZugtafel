# Eigene Seiten schreiben

Es gibt zwei Wege, eigene Inhalte aufs Display zu bringen: Du richtest den Server auf eine Webseite (`url`-Seite), oder du schreibst einen kleinen Seitentyp aus einer Python-Datei und einem HTML-Template (Skript-Seite). Der erste Weg braucht gar keine Programmierung.

## Zwei Arten von Seiten

| | `url`-Seite | Skript-Seite |
| --- | --- | --- |
| Was du schreibst | nichts, oder eine Webseite, die du selbst betreibst | `page.py` und `template.html` |
| Geeignet für | Dashboards oder Statusseiten, die es schon gibt | Daten aus einer API, einer Datei oder einem Sensor, in deinem eigenen Layout |
| Konfiguration | `type: url` und `url: ...` | `type: <Ordnername>` |

## Der Vertrag einer Seite

Eine Skript-Seite ist ein Ordner mit zwei Dateien. Der Ordnername ist der Seitentyp:

```
pages-custom/
  mypage/
    page.py
    template.html
```

### page.py

```python
def fetch(options: dict, ctx) -> dict:
    return {"title": "Hallo"}
```

- `fetch(options, ctx)` ist **Pflicht**. Es gibt ein Dict zurück. Jeder Schlüssel wird im Template zu einer Variablen. Die Funktion läuft in einem Worker-Thread (blockierende Aufrufe wie HTTP-Anfragen sind in Ordnung) und muss innerhalb von 20 Sekunden fertig sein.
- `validate(options)` ist optional. Wirf `ValueError("...")`, um eine fehlerhafte Konfiguration abzulehnen. Der Server startet dann nicht und zeigt deine Meldung mit der Seitennummer.
- `MIN_REFRESH = 60` ist optional (eine ganze Zahl). Es legt das kleinste erlaubte `refresh` für deine Seite fest, zum Beispiel um ein Anfragelimit einzuhalten.
- Andere `.py`-Dateien im selben Ordner kannst du mit `from .helper import etwas` importieren.

`options` enthält alle Schlüssel des Seiteneintrags in der `config.yaml` außer `type`, `duration` und `refresh`. `ctx` hat drei Felder:

| Feld | Bedeutung |
| --- | --- |
| `ctx.now` | die aktuelle Zeit als datetime mit der Zeitzone aus der `config.yaml` |
| `ctx.lang` | das `lang` von oberster Ebene (`de` oder `en`) |
| `ctx.timezone` | der Name der Zeitzone |

Wirft `fetch` einen Fehler, behält die Seite bis zu 10 Minuten ihr letztes gutes Bild, und der Fehler erscheint im Log und auf der Vorschauseite. Ein Fehler in `page.py` beim Laden (ein Tippfehler) stoppt den Server beim Start mit einer klaren Meldung.

### template.html

Ein Jinja2-Template. Erweitere `base.html`. Es richtet die 240x240-Fläche, den dunklen Hintergrund, die mitgelieferten DejaVu-Schriften (mit Umlauten) und diese CSS-Variablen ein: `--bg`, `--header-bg`, `--fg`, `--muted`, `--divider`, `--orange`, `--red`, `--yellow`.

```html
{% extends "base.html" %}
{% block head %}<style>h1{font-size:28px;margin:20px}</style>{% endblock %}
{% block body %}<h1>{{ title }}</h1>{% endblock %}
```

Werte werden automatisch HTML-maskiert. Die Fläche ist genau 240x240 Pixel groß und nichts scrollt, was nicht passt, wird abgeschnitten. Die Schriften heißen „DejaVu Sans“ und „DejaVu Sans Condensed“ (normal und fett). Die schmale Variante bringt mehr Zeichen in eine Zeile.

## Beispiel: die Seite clock

Die mitgelieferte Seite `clock` ist das kleinste sinnvolle Beispiel (`pages/clock/`). Ihre `page.py` macht drei Dinge:

1. `validate` lehnt jede andere `lang` als `de` oder `en` ab.
2. `fetch` nimmt die Sprache (die eigene Option `lang` der Seite oder die von oberster Ebene), formatiert `ctx.now` und gibt `{"time": "14:05", "weekday": "Dienstag", "date": "14.11.2026"}` zurück.
3. Mehr nicht: kein Netzwerk, kein Zustand.

Ihr `template.html` erweitert `base.html` und nutzt `{{ time }}`, `{{ weekday }}` und `{{ date }}`, zentriert in der 240x240-Fläche mit einer großen, fetten Uhrzeit. Kopiere sie und ändere sie ab:

```sh
mkdir -p pages-custom
cp -r pages/clock pages-custom/mypage
```

Bearbeite `pages-custom/mypage/page.py` und `template.html`, trage die Seite in die `config.yaml` ein:

```yaml
pages:
  - type: mypage
    refresh: 30
```

und starte mit `docker compose restart` neu. Eine Seite in `pages-custom` mit dem Namen einer mitgelieferten Seite (`clock`, `bahn`) ersetzt die mitgelieferte.

## Die url-Seite und ihre Tipps

```yaml
- type: url
  url: http://homeserver.lan/status-240
  wait_for: "#ready"
```

Der Server lädt die Adresse in einem Headless-Chromium mit einem Fenster von genau **240x240 Pixeln** und Skalierungsfaktor 1 und macht einen Screenshot. Deshalb:

- **Gestalte für 240x240.** Eine auf diese Größe geschrumpfte Desktop-Seite ist unlesbar. Baue eine Seite extra fürs Display: große Schrift (mindestens 18 px), wenige Elemente, hoher Kontrast, keine Scrollbalken. Nutze `html, body { width: 240px; height: 240px; overflow: hidden; }`.
- **Nutze `wait_for`**, wenn sich die Seite per JavaScript füllt. Gib dem fertigen Inhalt ein Element (zum Beispiel `<div id="ready">`) und setze `wait_for: "#ready"`. Nimm `wait_ms` nur für eine feste Extra-Pause, zum Beispiel bei einer Animation.
- **Halte das Bild einfach.** Ein Bild muss als JPEG in 24 576 Bytes passen. Flächen und einfacher Text lassen sich sehr gut komprimieren, Fotos und feine Farbverläufe schlecht. Muss der Server die Qualität stark senken, wird Text unscharf.
- **Der Server muss die Adresse aus dem Container heraus erreichen.** Nimm die LAN-Adresse oder den Namen, nicht `localhost`.
- **Keine Anmeldeseiten.** Der Browser des Servers hat keine gespeicherten Anmeldungen. Eine Seite mit Anmeldung zeigt die Anmeldung. Baue eine schreibgeschützte Seite fürs Display, und stelle sie nicht ins Internet, denn das Display-Bild wird ohne jedes Passwort ausgeliefert.
- Jede Aktualisierung lädt die Seite neu, also bedeutet `refresh: 30` alle 30 Sekunden eine Anfrage an deine Seite.

## Vorschau im Browser

Öffne `http://<server>:8080/`. Dort siehst du jede Seite deiner Playlist als 240x240-Bild mit Alter und letztem Fehler, und die Seite aktualisiert sich alle 30 Sekunden selbst. Starte nach einer Änderung an `page.py` oder `template.html` den Server neu (`docker compose restart`) und lade die Seite neu. Erscheint deine Seite nicht als Bild, sagt dir der Fehlertext darunter, warum. Die Einzelheiten stehen in `docker compose logs`.

## Der Befehl render

Um eine Seite ohne Display auszuprobieren, rendere eine Seite einmal in eine Datei:

```sh
docker compose exec glancebox python -m glancebox render 0 -o /tmp/page0.png
docker compose cp glancebox:/tmp/page0.png .
```

`0` ist die Nummer der Seite in `pages:` (ab 0 gezählt). Die Ausgabe ist ein PNG, wenn der Name auf `.png` endet, sonst ein JPEG, genau so, wie es das Display bekäme. Der Befehl nutzt die Konfiguration des laufenden Servers (`--config` wählt eine andere Datei) und endet mit einer Fehlermeldung, wenn Konfiguration oder Rendern scheitern. Außerhalb von Docker installierst du den Server (`pip install -e server` in einer Python-3.12-Umgebung mit dem Chromium von Playwright) und führst `python -m glancebox render 0 -o page0.png --config config.yaml` aus.
