# Server starten

<p class="gb-meta">Schritt 2 von 5 · etwa 10 Minuten</p>
<div class="gb-progress" aria-hidden="true"><span class="on"></span><span class="on"></span><span></span><span></span><span></span></div>

Der Server rendert deine Seiten und schickt sie als Bilder an das Display. Er läuft in Docker auf deinem Rechner, der immer an ist.

## Glance Box holen

1. Öffne ein Terminal auf dem Rechner und führe aus:

    ```sh
    git clone https://github.com/robinlanger/glancebox.git
    cd glancebox
    cp config.example.yaml config.yaml
    mkdir pages-custom
    ```

2. Öffne `config.yaml` in einem Editor. Das Beispiel zeigt Abfahrten an einem Bahnhof. Trag bei `station:` deinen ein, oder lösch den Block `bahn` und nimm eine andere Seite hinein, zum Beispiel `clock` oder `weather`. Das kannst du jederzeit ändern.

## Starten

1. Starte den Server:

    ```sh
    docker compose up -d --build
    ```

    Der erste Start dauert ein paar Minuten, weil Docker das Image mit eigenem Browser baut.

2. Öffne `http://<server-ip>:8080/` im Browser, zum Beispiel `http://192.168.1.50:8080/`. Du siehst eine Vorschau jeder Seite.

    !!! tip "Port 8080 schon belegt?"
        Wenn etwas anderes (zum Beispiel Pi-hole) Port 8080 nutzt, leg neben `docker-compose.yml` eine Datei `.env` mit `GLANCEBOX_PORT=8090` an und führe `docker compose up -d` noch einmal aus. Ab dann gilt `:8090`.

3. **Notier dir die Server-Adresse**, zum Beispiel `http://192.168.1.50:8080`. Das Display fragt in Schritt 4 danach. Gib dem Rechner im Router eine feste IP-Adresse, damit sich die Adresse nicht ändert.

Startet der Server nicht, zeigt `docker compose logs --tail 50` den Grund. Alle Optionen: [Konfiguration](../configuration.md).
