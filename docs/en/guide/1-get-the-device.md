# Get the device

<p class="gb-meta">Step 1 of 5 · about 5 minutes</p>
<div class="gb-progress" aria-hidden="true"><span class="on"></span><span></span><span></span><span></span><span></span></div>

Glance Box runs on one specific display. Check these three things before you start.

## What to buy

1. **A GeekMagic SmallTV Ultra.** It is a small cube with a 240×240 screen and an ESP8266 inside, sold for around 15 €.

    !!! warning "Only the Ultra"
        Other models, including the **SmallTV Pro**, use different hardware. Glance Box does not support them, and flashing them will not work.

2. **A USB power supply** and a matching cable. A phone charger works.

## What else you need

1. **A computer that is always on in your home network** for the server: a home server, a NAS or a PC (a Raspberry Pi 4/5 should work too, but is not tested yet). It needs [Docker](https://docs.docker.com/get-docker/) with Docker Compose.
2. **A 2.4 GHz Wi-Fi network.** The display cannot use 5 GHz.
3. **A browser** on a phone or computer in the same network.

## Before you flash

!!! info "Flashing is a one-way street, unless you make a backup"
    The stock firmware is bound to your device and there is no public image to go back to. You can keep a backup of the stock firmware, but that needs a USB serial adapter and clip leads. Most people skip it. Details: [Flashing details & backup](../flashing.md).

Next you start the server, so the display has something to show as soon as it is flashed.
