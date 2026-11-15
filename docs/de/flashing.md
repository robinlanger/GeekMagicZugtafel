# Firmware flashen

Diese Seite führt dich von der Original-Firmware von GeekMagic zu Glance Box. Lies sie einmal ganz durch, bevor du anfängst.

## Bevor du anfängst

Du brauchst den **GeekMagic SmallTV Ultra** (ESP8266). Andere Modelle, auch der SmallTV Pro, werden nicht unterstützt, und das Flashen funktioniert dort nicht.

> [!WARNING]
> **Ohne serielle Sicherung gibt es keinen Weg zurück zur Original-Firmware.** Der Aktivierungscode der Original-Firmware ist an die MAC-Adresse deines Geräts gebunden, und es gibt kein öffentliches Abbild zum Aufspielen. Ohne die Sicherung unten ist das Flashen eine Einbahnstraße. Die Sicherung ist freiwillig: Das Flashen selbst braucht kein Löten, die Sicherung schon (oder zumindest Prüfklemmen). Entscheide vor dem Start, ob du zurück können willst.

So funktioniert das erste Flashen: Die Original-Firmware hat eine Webseite für Firmware-Updates. Dort lädst du die `.bin` von Glance Box hoch. Der Maintainer hat diesen Weg an einem echten SmallTV Ultra getestet. Andere Versionen der Original-Firmware können abweichen. Schlägt der Upload fehl, ist nichts verloren: Das Gerät bleibt bei der Original-Firmware.

## Schritt 1: Original-Firmware sichern (optional)

Die Sicherung ist eine Kopie des gesamten Flash-Chips. Du machst sie über die serielle Schnittstelle des ESP-12F-Moduls im Display. Dafür brauchst du einen USB-Seriell-Adapter und etwas Geduld, und du musst das Gehäuse öffnen.

### Was du brauchst

- Einen USB-Seriell-Adapter mit 3,3 V. Zwei gängige Varianten:
  - **Raspberry Pi Pico** mit der Firmware [`debugprobe`](https://github.com/raspberrypi/debugprobe). Seine UART-Pins sind **GP4 = TX** und **GP5 = RX**.
  - **CH340**-Module (CH340G oder CH340C). Stelle Jumper oder Schalter für die Spannung auf **3,3 V**. CP2102- und FT232-Adapter funktionieren genauso.
- Drei bis vier dünne Drähte oder Prüfklemmen.
- `esptool` auf deinem Computer: `pip install esptool` (Python 3). Neuere Versionen bieten neben `esptool.py` auch den Befehl `esptool` an.

Die nötigen Pads und Pins liegen am ESP-12F-Modul: GND, TX, RX und GPIO0. Wo genau sie auf der Platine des Ultra sitzen, und ein Foto, steht in [Rettung](recovery.md#pads-und-foto-noch-nicht-an-echter-hardware-bestätigt). Dieser Teil ist **noch nicht an echter Hardware bestätigt**.

### Verkabelung

Kreuze die Datenleitungen: Was die eine Seite sendet, empfängt die andere.

| Adapter | ESP-12F im Display |
| --- | --- |
| GND | GND |
| TX (Pico: GP4) | RX |
| RX (Pico: GP5) | TX |
| (nicht verbunden) | GPIO0 an GND, nur während das Gerät hochfährt |

Regeln, die dein Gerät schützen:

- **Nur 3,3 V.** Ein 5-V-Adapter kann den ESP8266 zerstören.
- **Den 3,3-V- oder 5-V-Pin des Adapters nicht anschließen.** Das Display wird über seinen eigenen USB-C-Anschluss versorgt. Zwei Stromquellen gleichzeitig sind keine gute Idee.
- Viele Adapter beschriften ihre Pins aus der eigenen Sicht. Passiert nichts, vertausche TX und RX einmal.

### Sicherung erstellen und prüfen

1. Verkabele alles wie oben, mit GPIO0 an GND.
2. Stecke das USB-C-Kabel des Displays ein. Der ESP8266 startet jetzt im seriellen Bootloader.
3. Prüfe die Verbindung (ersetze den Port; auf dem Mac sieht er aus wie `/dev/cu.usbserial-0001` oder `/dev/cu.usbmodem1101`, unter Linux `/dev/ttyUSB0`, unter Windows `COM3`):

   ```sh
   esptool.py --port /dev/ttyUSB0 chip_id
   ```

   Du solltest `Chip is ESP8266` und eine MAC-Adresse sehen. Notiere dir die MAC.
4. Lies den ganzen Flash **zweimal** in zwei Dateien:

   ```sh
   esptool.py --port /dev/ttyUSB0 -b 115200 read_flash 0 ALL backup1.bin
   esptool.py --port /dev/ttyUSB0 -b 115200 read_flash 0 ALL backup2.bin
   ```

5. Vergleiche die beiden Kopien. Die beiden Prüfsummen müssen identisch sein:

   ```sh
   shasum -a 256 backup1.bin backup2.bin
   ```

   (Unter Linux `sha256sum`.) Weichen sie ab, prüfe die Verkabelung und lies erneut.
6. Bewahre `backup1.bin` an mindestens zwei Orten auf (Computer und Cloud oder USB-Stick). **Veröffentliche sie nie**: Sie enthält dein WLAN-Passwort und die Aktivierungsdaten deines Geräts.
7. Ziehe das USB-Kabel ab, entferne den GPIO0-Draht, schließe das Gehäuse.

Den Weg zurück beschreibt [Rettung](recovery.md#sicherung-zurückspielen).

## Schritt 2: Firmware besorgen

1. Öffne die [Releases-Seite](https://github.com/robinlanger/glancebox/releases) und lade `glancebox-ultra-<version>.bin` und `glancebox-ultra-<version>.bin.md5` herunter.
2. Öffne die `.md5`-Datei. Sie enthält eine Zeile mit einer 32-stelligen Prüfsumme und dem Dateinamen. Behalte die 32 Zeichen, du brauchst sie für spätere Updates. Die `.sha256`-Datei ist für alle, die den Download unabhängig prüfen wollen.

## Schritt 3: Über die Original-Weboberfläche flashen

1. Schalte das Display ein und lass es mit der Original-Firmware in dein WLAN. Finde seine IP-Adresse heraus (sie steht auf dem Display oder in der Geräteliste deines Routers).
2. Öffne `http://<display-ip>/` in einem Browser im selben Netzwerk.
3. Suche die Seite für das **Firmware-Update** in der Original-Oberfläche. Auf einem getesteten Ultra heißt der Abschnitt **„7. Firmware update“** mit einem Button **UPLOAD**. In anderen Versionen der Original-Firmware kann er anders heißen.
4. Wähle `glancebox-ultra-<version>.bin` und starte den Upload.
5. **Ziehe das Display etwa eine Minute lang nicht ab.** Es startet von selbst neu, wenn der Upload fertig ist.

Lehnt die Original-Seite die Datei ab, läuft das Display weiter mit der Original-Firmware. Prüfe, ob du die `.bin` für den **Ultra** geladen hast und der Download vollständig ist (MD5 oder SHA-256 vergleichen).

## Schritt 4: Was du beim ersten Start siehst

Nach dem Neustart:

1. Das Display zeigt **„Glance Box setup“**, einen WLAN-Namen wie `GlanceBox-A1B2` und die Adresse `http://192.168.4.1`. Das ist das Einrichtungsportal.
2. Weiter geht es mit [Einrichtung](setup.md): WLAN auswählen, Serveradresse eintragen und das Update-Passwort setzen.
3. Nach dem Speichern startet das Display neu, zeigt kurz Version, IP-Adresse und Serveradresse und dann die erste Seite von deinem Server.
4. Ist der Server nicht erreichbar, bleibt das letzte Bild stehen. Nach etwa zwei Minuten ohne Bild zeigt das Display einen Statusbildschirm mit dem Fehler.

Bleibt das Display nach dem ersten Flashen dunkel oder zeigt nichts Sinnvolles, lies [Rettung](recovery.md).
