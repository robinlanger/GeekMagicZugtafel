# Setting up the display

After the first flash (or after a factory reset) the display opens a Wi-Fi setup portal. This page walks through it and explains what the settings mean.

## What you need first

- The Glance Box server running and reachable from your home network, see the [README](../../README.md#quickstart). Note its address, for example `http://192.168.1.20:8080`. If port 8080 is already taken (for example by Pi-hole), create a `.env` file next to `docker-compose.yml` containing `GLANCEBOX_PORT=8090` and restart. The address is then `…:8090`. Give the server a fixed IP address (or a fixed name) in your router, otherwise the display loses it after a router restart.
- Your 2.4 GHz Wi-Fi name and password.
- A password you choose for updates (at least 8 characters, 32 at most, printable ASCII only, no umlauts).

## The setup portal

1. The display shows **"Glance Box setup"** with the name `GlanceBox-XXXX` (the last four digits of the chip ID) and the address `http://192.168.4.1`.
2. On your phone or computer, join the Wi-Fi network **`GlanceBox-XXXX`**. It has no password. Most phones open the setup page automatically. If not, open `http://192.168.4.1` yourself.
3. Choose **Configure WiFi** and select your network. Then fill in:

   | Field | Meaning |
   | --- | --- |
   | Wi-Fi network and password | Your home network (2.4 GHz). |
   | Server URL | Address of the Glance Box server, for example `http://homeserver:8080`. Only `http://` works (no `https://`). A trailing slash is removed for you. |
   | Update password | The password for updates and for changing settings later. The user name is always `admin`. |
   | Brightness | 5 to 100 percent. You can change it later on the device web page. |

4. Save. If something is invalid (short password, `https://`, missing host) the portal shows the error in English and German and asks again.
5. The display restarts, joins your Wi-Fi and shows the first page.

**Language.** The device web page and its messages follow your browser language (German or English). The text on the display itself is English.

## The device web page

Open `http://<display-ip>/` (the IP is shown on the display at boot and in your router). It shows version, uptime, signal strength, the number of frames received, failed boots and whether safe mode is active. Below that you can:

- change the server URL, the brightness and the [night mode](#night-mode) and set a new update password (these changes need the update password, user `admin`),
- upload a firmware update (see [Updating](updating.md)),
- restart the device, or **reset settings and Wi-Fi** (back to the setup portal).

`http://<display-ip>/status` returns the same facts as JSON, without a password. Handy for scripts and for Home Assistant.

## Night mode

If the display is in a bedroom, it can dim or go completely dark at night. Set on the device web page:

- **Night from** and **Night until**, for example 22:00 and 07:00. The window may span midnight.
- **Night brightness** from 0 to 100 %. **0 % means completely dark**, the backlight is off.

If both times are equal (default: 00:00 and 00:00), night mode is off. The display keeps fetching frames at night, so the current picture is there right away in the morning.

The display gets the time from the Glance Box server, in the time zone set as `timezone` in your `config.yaml` (daylight saving time included). **The server must be version 0.2.0 or newer as well.** With an older server the device page shows "-" for "Local time" and night mode never kicks in. If the server goes down, the display keeps counting on its own. If it restarts at night and cannot reach the server, it does not know the time yet and stays bright until the server answers. Safe mode has no night mode.

`/status` shows the current time (`local_time`) and whether it is night (`night`).

## Changing Wi-Fi later

- **Server URL, brightness, password:** use the device web page.
- **New Wi-Fi network:** either use **Reset settings and Wi-Fi** on the device web page and go through the portal again, or switch the display off and on while the old network is gone. If the saved network cannot be reached, the setup portal opens for 180 seconds. Joining it and changing anything then asks for the **current update password**. If nobody uses it within 180 seconds, the display keeps trying the saved network in the background.

## What to know about security

Please read this; it describes what the design accepts on purpose.

- **The setup portal is an open Wi-Fi network** (no password), because the device has no other way to learn your Wi-Fi at the start. On a device that is **not yet configured** the portal stays open until you finish the setup. In that time anyone within radio range can connect and enter Wi-Fi credentials, a server address and the update password. So do the first setup right away, not an hour later. On an already configured device the portal opens for at most **180 seconds** (when the saved network is gone) and needs the current update password for any change.
- **The update password protects over-the-air updates and the settings** (user `admin`, HTTP Basic authentication). Basic authentication is **not encrypted**, so anyone who can listen to your home network could read it. Use a password you use nowhere else.
- **The device web page and `/status` use plain HTTP.** Do not expose the display to the internet (no port forwarding).
- **The server has no login at all.** Anyone in your network who reaches port 8080 sees what the display shows. Keep it in the LAN and do not forward the port. Do not put secrets on pages. Whatever a page shows, the server also serves.
- Forgot the update password? Use the serial route in [Recovery](recovery.md) and flash again, or restore a backup.
