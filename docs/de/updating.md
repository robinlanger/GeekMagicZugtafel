# Firmware aktualisieren

Updates laufen über WLAN, ein Kabel ist nicht nötig. Das Gerät prüft jedes Update, bevor es umschaltet, und schützt sich vor einem Update, das nicht startet.

## Bevor du aktualisierst

1. Lade `glancebox-ultra-<version>.bin` und `glancebox-ultra-<version>.bin.md5` von der [Releases-Seite](https://github.com/robinlanger/glancebox/releases) herunter und lies die Release-Notes.
2. Besorge dir die MD5 der Datei, 32 Hexadezimalzeichen. Sie ist das erste Wort in der `.md5`-Datei:

   ```sh
   cut -d' ' -f1 glancebox-ultra-<version>.bin.md5
   ```

   Du kannst sie auch selbst berechnen und vergleichen: `md5 -q glancebox-ultra-<version>.bin` (macOS) oder `md5sum glancebox-ultra-<version>.bin` (Linux).
3. Halte das **Update-Passwort** bereit (Benutzername `admin`, festgelegt in der [Einrichtung](setup.md)).

Die MD5 ist **Pflicht**. Ohne sie lehnt das Gerät das Update ab. Sie schützt vor einem beschädigten Download.

## Update im Browser

1. Öffne `http://<display-ip>/`.
2. Öffne unter **Gerät** den Punkt **Firmware-Update** und wähle die `.bin`-Datei. Die Seite rechnet die MD5 selbst aus und trägt sie ein; vergleiche sie gern mit der `.md5`-Datei. (Im Safe Mode und ohne JavaScript trägst du die 32-stellige MD5 selbst ein.)
3. Drücke **Hochladen**. Ein Balken zeigt den Fortschritt. Der Browser fragt nach dem Benutzernamen `admin` und dem Update-Passwort.
4. Das Display zeigt „Firmware update“, während es die Datei empfängt, danach „Update OK, restarting“. Es startet innerhalb von ein oder zwei Sekunden neu. Zieh es nicht ab.
5. Nach dem Neustart zeigt die Geräteseite die neue Version. In der ersten Minute steht der Zähler für Fehlstarts auf 1. Er geht zurück auf 0, wenn die Firmware 60 Sekunden lang gesund lief, mit funktionierendem WLAN und Webserver.

## Update mit curl

```sh
curl -u admin:<passwort> -F md5=<md5> -F firmware=@glancebox-ultra-<version>.bin http://<display-ip>/update
```

**Das Feld `md5` muss in der Befehlszeile vor der Datei `firmware` stehen**, weil das Gerät die Felder in der Reihenfolge liest, in der sie ankommen. Fehlt es oder steht es an der falschen Stelle, wird das Update abgelehnt (HTTP 400, „md5 missing or invalid (send md5 before firmware)“). Bei Erfolg kommt `update ok, restarting`.

Das Ergebnis kannst du danach ohne Passwort prüfen:

```sh
curl -s http://<display-ip>/status
```

Das JSON zeigt `version`, `boot_failed` (0, sobald gesund), `safe_mode` und `frames_ok`.

## Was passiert, wenn etwas schiefgeht

### Falsche MD5, beschädigte oder falsche Datei

Das Gerät lehnt das Update mit HTTP 400 und einem kurzen Grund ab (zum Beispiel MD5 stimmt nicht, Datei ist kein ESP8266-Abbild, Datei zu groß) und **läuft mit der alten Firmware weiter**. Das neue Abbild wird nur benutzt, wenn Größe, MD5 und Kopfdaten alle stimmen. Ein falsches Passwort ergibt HTTP 401, und es wird nichts geschrieben. Bricht ein Upload ab (WLAN weg, Kabel gezogen), läuft ebenfalls die alte Firmware weiter. Versuche es einfach noch einmal.

### Die neue Firmware startet nicht richtig

Bei jedem Start steigt ein Zähler im Speicher des Geräts. Er geht auf 0 zurück, sobald die Firmware **gesund** ist: 60 Sekunden Laufzeit, WLAN verbunden und Webserver läuft. Ein Server, der nicht erreichbar ist, zählt nicht dagegen.

Wird die Firmware **3 Starts hintereinander** nicht gesund (Abstürze, Hänger, Neustarts), startet der nächste Start den **Safe Mode**: nur WLAN, eine kleine Update-Seite im Browser, die Update-Funktion und `/status`, mit einem Statusbildschirm auf dem Display. Von dort spielst du eine funktionierende Firmware auf (Browser oder curl), siehe [Rettung](recovery.md#safe-mode).

Beachte: Drei Neustarts von Hand innerhalb einer Minute zählen auch als drei Fehlstarts. Strom aus und wieder an setzt den Zähler zurück.

## Server aktualisieren

Server und Firmware haben eine gemeinsame Versionsnummer. Aktualisiere den Server mit `git pull` und `docker compose up -d --build` (oder hole das neue Image `ghcr.io/robinlanger/glancebox:<version>`). Die Release-Notes sagen, ob Firmware und Server zusammen aktualisiert werden sollten.

## Risiken, die du in Kauf nimmst

- Wer das Update-Passwort kennt und das Gerät in deinem Netz erreicht, kann Firmware darauf installieren. Nimm ein Passwort, das du sonst nirgends benutzt. Es wird mit HTTP-Basic-Authentifizierung **unverschlüsselt** durch dein Heimnetz geschickt.
- Das Gerät kann nicht prüfen, wer die Firmware gebaut hat. Lade Releases nur von der Releases-Seite des Projekts und vergleiche MD5 oder SHA-256 mit den veröffentlichten Dateien.
- Ein Update, das zwar startet, aber auf eine Weise kaputt ist, die nie abstürzt (zum Beispiel ein leeres Display), wird vom Safe Mode nicht erkannt. Spiele das vorige Release noch einmal auf oder nimm den seriellen Weg aus [Rettung](recovery.md#serielles-flashen).
