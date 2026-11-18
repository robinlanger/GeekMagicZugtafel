# Gerät besorgen

<p class="gb-meta">Schritt 1 von 5 · etwa 5 Minuten</p>
<div class="gb-progress" aria-hidden="true"><span class="on"></span><span></span><span></span><span></span><span></span></div>

Glance Box läuft auf genau einem Display. Prüf diese drei Dinge, bevor du anfängst.

## Was du kaufst

1. **Einen GeekMagic SmallTV Ultra.** Ein kleiner Würfel mit 240×240-Bildschirm und einem ESP8266 darin, für etwa 15 €.

    !!! warning "Nur der Ultra"
        Andere Modelle, auch der **SmallTV Pro**, haben andere Hardware. Glance Box unterstützt sie nicht, und das Flashen funktioniert dort nicht.

2. **Ein USB-Netzteil** mit passendem Kabel. Ein Handy-Ladegerät reicht.

## Was du sonst brauchst

1. **Einen Rechner, der immer in deinem Heimnetz läuft**, für den Server: Homeserver, NAS oder PC (ein Raspberry Pi 4/5 sollte auch gehen, ist aber noch nicht getestet). Darauf brauchst du [Docker](https://docs.docker.com/get-docker/) mit Docker Compose.
2. **Ein WLAN mit 2,4 GHz.** 5 GHz kann das Display nicht.
3. **Einen Browser** auf Handy oder Rechner im selben Netz.

## Bevor du flashst

!!! info "Flashen ist eine Einbahnstraße, außer du machst ein Backup"
    Die Original-Firmware ist an dein Gerät gebunden, und es gibt kein öffentliches Image zum Zurückspielen. Du kannst die Original-Firmware sichern, dafür brauchst du aber einen USB-Seriell-Adapter und Klemmen. Die meisten lassen das weg. Details: [Flash-Details & Backup](../flashing.md).

Als Nächstes startest du den Server, damit das Display gleich nach dem Flashen etwas zu zeigen hat.
