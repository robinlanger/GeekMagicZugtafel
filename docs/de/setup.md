# Display einrichten

Nach dem ersten Flashen (oder nach einem Zurücksetzen) öffnet das Display ein WLAN-Einrichtungsportal. Diese Seite führt dich durch das Portal und erklärt die Einstellungen.

## Was du zuerst brauchst

- Den laufenden Glance-Box-Server, erreichbar aus deinem Heimnetz, siehe [README](../../README.de.md#schnellstart). Notiere seine Adresse, zum Beispiel `http://192.168.1.20:8080`. Ist Port 8080 schon belegt (zum Beispiel durch Pi-hole), leg neben `docker-compose.yml` eine Datei `.env` mit `GLANCEBOX_PORT=8090` an und starte neu. Die Adresse lautet dann `…:8090`. Gib dem Server im Router eine feste IP-Adresse (oder einen festen Namen), sonst verliert das Display ihn nach einem Router-Neustart.
- Name und Passwort deines 2,4-GHz-WLANs.
- Ein selbst gewähltes Passwort für Updates (mindestens 8, höchstens 32 Zeichen, nur druckbares ASCII, keine Umlaute).

## Das Einrichtungsportal

1. Das Display zeigt **„Glance Box setup“** mit dem Namen `GlanceBox-XXXX` (die letzten vier Stellen der Chip-ID) und der Adresse `http://192.168.4.1`.
2. Verbinde dein Handy oder deinen Computer mit dem WLAN **`GlanceBox-XXXX`**. Es hat kein Passwort. Die meisten Handys öffnen die Einrichtungsseite automatisch. Wenn nicht, öffne `http://192.168.4.1` selbst.
3. Wähle **Configure WiFi** und dein Netzwerk aus. Fülle dann aus:

   | Feld | Bedeutung |
   | --- | --- |
   | WLAN-Name und Passwort | Dein Heimnetz (2,4 GHz). |
   | Server URL | Adresse des Glance-Box-Servers, zum Beispiel `http://homeserver:8080`. Nur `http://` geht (kein `https://`). Ein abschließender Schrägstrich wird für dich entfernt. |
   | Update password | Das Passwort für Updates und für spätere Änderungen der Einstellungen. Der Benutzername ist immer `admin`. |
   | Brightness | Helligkeit von 5 bis 100 Prozent. Du kannst sie später auf der Geräteseite ändern. |

4. Speichern. Ist etwas ungültig (zu kurzes Passwort, `https://`, fehlender Host), zeigt das Portal den Fehler auf Englisch und Deutsch und fragt erneut.
5. Das Display startet neu, verbindet sich mit deinem WLAN und zeigt die erste Seite.

**Sprache.** Die Geräteseite und ihre Meldungen richten sich nach der Sprache deines Browsers (Deutsch oder Englisch). Die Texte auf dem Display selbst sind englisch.

## Die Geräteseite

Öffne `http://<display-ip>/` (die IP steht beim Start auf dem Display und in deinem Router). Sie zeigt Version, Laufzeit, Signalstärke, die Anzahl empfangener Bilder, Fehlstarts und ob der Safe Mode aktiv ist. Darunter kannst du:

- die Server-URL, die Helligkeit und den [Nachtmodus](#nachtmodus) ändern und ein neues Update-Passwort setzen (diese Änderungen brauchen das Update-Passwort, Benutzer `admin`),
- ein Firmware-Update hochladen (siehe [Aktualisieren](updating.md)),
- das Gerät neu starten oder **Einstellungen und WLAN zurücksetzen** (zurück ins Einrichtungsportal).

`http://<display-ip>/status` liefert dieselben Angaben als JSON, ohne Passwort. Praktisch für Skripte und für Home Assistant.

## Nachtmodus

Steht das Display im Schlafzimmer, kann es nachts dunkler werden oder ganz ausgehen. Stell dafür auf der Geräteseite ein:

- **Nacht von** und **Nacht bis**, zum Beispiel 22:00 und 07:00. Der Zeitraum darf über Mitternacht gehen.
- **Helligkeit nachts** von 0 bis 100 %. **0 % heißt ganz dunkel**, die Hintergrundbeleuchtung ist dann aus.

Sind beide Zeiten gleich (Standard: 00:00 und 00:00), ist der Nachtmodus aus. Das Display holt nachts weiter Bilder, morgens steht also sofort das aktuelle Bild da.

Die Uhrzeit bekommt das Display vom Glance-Box-Server, in der Zeitzone aus `timezone` in deiner `config.yaml` (Sommerzeit inklusive). Fällt der Server aus, zählt das Display die Zeit selbst weiter. Startet es aber nachts neu und erreicht den Server nicht, kennt es die Uhrzeit noch nicht und bleibt hell, bis der Server antwortet. Im Safe Mode gibt es keinen Nachtmodus.

`/status` zeigt die aktuelle Uhrzeit (`local_time`) und ob gerade Nacht ist (`night`).

## WLAN später ändern

- **Server-URL, Helligkeit, Passwort:** über die Geräteseite.
- **Neues WLAN:** Nutze entweder **Einstellungen und WLAN zurücksetzen** auf der Geräteseite und geh das Portal noch einmal durch, oder schalte das Display aus und wieder ein, solange das alte Netz weg ist. Ist das gespeicherte Netz nicht erreichbar, öffnet sich das Einrichtungsportal für 180 Sekunden. Wer sich dort verbindet und etwas ändern will, muss das **aktuelle Update-Passwort** eingeben. Wird das Portal 180 Sekunden lang nicht benutzt, versucht das Display im Hintergrund weiter, das gespeicherte Netz zu erreichen.

## Was du zur Sicherheit wissen solltest

Bitte lies das. Hier steht, was das Design bewusst in Kauf nimmt.

- **Das Einrichtungsportal ist ein offenes WLAN** (ohne Passwort), weil das Gerät am Anfang keinen anderen Weg hat, dein WLAN kennenzulernen. Bei einem Gerät, das **noch nicht eingerichtet** ist, bleibt das Portal offen, bis du fertig bist. In dieser Zeit kann sich jeder in Funkreichweite verbinden und WLAN-Zugangsdaten, eine Serveradresse und das Update-Passwort eintragen. Richte das Gerät also sofort ein und nicht erst in einer Stunde. Bei einem bereits eingerichteten Gerät öffnet sich das Portal höchstens **180 Sekunden** lang (wenn das gespeicherte Netz fehlt) und verlangt für jede Änderung das aktuelle Update-Passwort.
- **Das Update-Passwort schützt Updates über WLAN und die Einstellungen** (Benutzer `admin`, HTTP-Basic-Authentifizierung). Basic-Authentifizierung ist **nicht verschlüsselt**, wer in deinem Heimnetz mitlauschen kann, kann das Passwort lesen. Nimm ein Passwort, das du sonst nirgends benutzt.
- **Geräteseite und `/status` laufen über unverschlüsseltes HTTP.** Mach das Display nicht aus dem Internet erreichbar (keine Portweiterleitung).
- **Der Server hat gar keine Anmeldung.** Jeder in deinem Netz, der Port 8080 erreicht, sieht, was das Display zeigt. Lass ihn im LAN und leite den Port nicht weiter. Packe keine Geheimnisse auf Seiten. Was eine Seite zeigt, liefert der Server auch aus.
- Update-Passwort vergessen? Nimm den seriellen Weg aus [Rettung](recovery.md) und flashe neu oder spiele eine Sicherung zurück.
