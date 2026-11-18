# Updating the firmware

Updates go over Wi-Fi, no cable needed. The device checks every update before it switches to it, and it protects itself against an update that does not start.

## Before you update

1. Download `glancebox-ultra-<version>.bin` and `glancebox-ultra-<version>.bin.md5` from the [releases page](https://github.com/robinlanger/glancebox/releases) and read the release notes.
2. Get the MD5 of the file, 32 hexadecimal characters. It is the first word in the `.md5` file:

   ```sh
   cut -d' ' -f1 glancebox-ultra-<version>.bin.md5
   ```

   You can also compute it yourself and compare: `md5 -q glancebox-ultra-<version>.bin` (macOS) or `md5sum glancebox-ultra-<version>.bin` (Linux).
3. Have the **update password** ready (user name `admin`, set in [Setup](setup.md)).

The MD5 is **required**. Without it the device refuses the update. It protects against a damaged download.

## Update in the browser

1. Open `http://<display-ip>/`.
2. Under **Device**, open **Firmware update** and choose the `.bin` file. The page computes the MD5 itself and fills it in; compare it with the `.md5` file if you like. (In safe mode, and without JavaScript, enter the 32-character MD5 yourself.)
3. Press **Upload**. A bar shows the progress. The browser asks for the user name `admin` and the update password.
4. The display shows "Firmware update" while it receives the file, then "Update OK, restarting". It restarts within a second or two. Do not unplug it.
5. After the restart, the device page shows the new version. For the first minute the failed-boot counter shows 1. It goes back to 0 when the firmware has run healthily for 60 seconds with Wi-Fi and web server working.

## Update with curl

```sh
curl -u admin:<password> -F md5=<md5> -F firmware=@glancebox-ultra-<version>.bin http://<display-ip>/update
```

**The `md5` field must come before the `firmware` file** on the command line, because the device reads the fields in the order they arrive. If it is missing or in the wrong place the update is refused (HTTP 400, "md5 missing or invalid (send md5 before firmware)"). On success you get `update ok, restarting`.

You can then check the result without a password:

```sh
curl -s http://<display-ip>/status
```

The JSON shows `version`, `boot_failed` (0 once healthy), `safe_mode` and `frames_ok`.

## What happens if something is wrong

### A wrong MD5, a damaged or wrong file

The device rejects the update with HTTP 400 and a short reason (for example MD5 mismatch, file is not an ESP8266 image, file too big) and **keeps running the old firmware**. The new image is only used when its size, MD5 and header are all correct. A wrong password gives HTTP 401, and nothing is written. If an upload is interrupted (Wi-Fi drops, cable pulled), the old firmware keeps running too. Just try again.

### The new firmware does not start properly

Each boot raises a counter in the device's memory. The counter goes back to 0 once the firmware is **healthy**: 60 seconds of uptime, Wi-Fi connected and web server running. A server that is down does not count against it.

If the firmware fails to become healthy **3 boots in a row** (crashes, hangs, restarts), the next boot starts **safe mode**: only Wi-Fi, a small update page in the browser, the update function and `/status`, with a status screen on the display. From there you upload a good firmware (browser or curl), see [Recovery](recovery.md#safe-mode).

Note that restarting the device by hand three times within a minute also counts as three failed boots. Switching the power off and on again clears the counter.

## Updating the server

The server and the firmware have one version number. Update the server with `git pull` and `docker compose up -d --build` (or pull the new image `ghcr.io/robinlanger/glancebox:<version>`). The release notes say if firmware and server should be updated together.

## Risks you accept

- Anyone who knows the update password and can reach the device in your network can install firmware on it. Choose a password you use nowhere else. It travels with HTTP Basic authentication, **unencrypted**, over your home network.
- The device cannot check who built the firmware. Only download releases from the project's releases page and compare MD5 or SHA-256 with the published files.
- An update that starts but is broken in a way that never crashes (for example a blank display) is not caught by the safe mode. Upload the previous release again, or use the serial route in [Recovery](recovery.md#serial-flashing).
