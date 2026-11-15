# Flashing the firmware

This page takes you from the stock GeekMagic firmware to Glance Box. Read the whole page once before you start.

## Before you start

You need the **GeekMagic SmallTV Ultra** (ESP8266). Other models, including the SmallTV Pro, are not supported and flashing them will not work.

> [!WARNING]
> **There is no way back to the stock firmware without a serial backup.** The activation code of the stock firmware is bound to the MAC address of your device, and there is no public image to flash instead. If you do not make the backup below, the flash is a one-way street. Making the backup is optional, but **strongly recommended**.

How the first flash works: the stock firmware has a web page for firmware updates. You upload the Glance Box `.bin` there. This route is reported to work by the community. It will be re-confirmed by the maintainer on a real device before the first release (this page is updated if anything differs). If the upload fails, nothing is lost: the device stays on the stock firmware.

## Step 1: Back up the stock firmware (recommended)

The backup is a copy of the whole flash chip. You make it over the serial connection of the ESP-12F module inside the display. It needs a USB-to-serial adapter, a little patience, and you have to open the case.

### What you need

- A 3.3 V USB-to-serial adapter. Two common options:
  - **Raspberry Pi Pico** with the [`debugprobe`](https://github.com/raspberrypi/debugprobe) firmware. Its UART pins are **GP4 = TX** and **GP5 = RX**.
  - **CH340** modules (CH340G or CH340C). Set the voltage jumper or switch to **3.3 V**. CP2102 and FT232 adapters work the same way.
- Three to four thin wires or clip leads.
- `esptool` on your computer: `pip install esptool` (Python 3). Newer versions also offer the command `esptool` in addition to `esptool.py`.

The pads and pins you need are on the ESP-12F module: GND, TX, RX and GPIO0. Where exactly they are on the Ultra board, and a photo, is in [Recovery](recovery.md#pad-labels-and-photo-pending-verification-on-real-hardware). That part is **pending verification on real hardware**.

### Wiring

Cross the data lines: what one side sends, the other side receives.

| Adapter | ESP-12F on the display |
| --- | --- |
| GND | GND |
| TX (Pico: GP4) | RX |
| RX (Pico: GP5) | TX |
| (not connected) | GPIO0 goes to GND, only while the device powers up |

Rules that protect your device:

- **3.3 V only.** A 5 V adapter can destroy the ESP8266.
- **Do not connect the 3.3 V or 5 V pin of the adapter.** The display is powered through its own USB-C port. Two power sources at once is a bad idea.
- Many adapter modules label their pins from their own point of view. If nothing happens, swap TX and RX once.

### Making and checking the backup

1. Wire everything as shown, with GPIO0 connected to GND.
2. Plug the display's own USB-C cable in. The ESP8266 now starts in its serial bootloader.
3. Check the connection (replace the port; on macOS it looks like `/dev/cu.usbserial-0001` or `/dev/cu.usbmodem1101`, on Linux `/dev/ttyUSB0`, on Windows `COM3`):

   ```sh
   esptool.py --port /dev/ttyUSB0 chip_id
   ```

   You should see `Chip is ESP8266` and a MAC address. Write the MAC down.
4. Read the whole flash, **twice**, into two files:

   ```sh
   esptool.py --port /dev/ttyUSB0 -b 115200 read_flash 0 ALL backup1.bin
   esptool.py --port /dev/ttyUSB0 -b 115200 read_flash 0 ALL backup2.bin
   ```

5. Compare the two copies. The two hashes must be identical:

   ```sh
   shasum -a 256 backup1.bin backup2.bin
   ```

   (On Linux use `sha256sum`.) If they differ, check the wiring and read again.
6. Store `backup1.bin` in at least two places (computer and cloud or USB stick). **Never publish it**: it contains your Wi-Fi password and your device's activation data.
7. Unplug the USB cable, remove the GPIO0 wire, close the case.

The way back is described in [Recovery](recovery.md#restoring-the-backup).

## Step 2: Get the firmware

1. Open the [releases page](https://github.com/robinlanger/glancebox/releases) and download `glancebox-ultra-<version>.bin` and `glancebox-ultra-<version>.bin.md5`.
2. Open the `.md5` file. It contains one line with a 32-character hash and the file name. Keep the 32 characters, you need them for later updates. The `.sha256` file is for people who want to check the download independently.

## Step 3: Flash through the stock web interface

1. Power the display and let it join your Wi-Fi with the stock firmware. Find its IP address (shown on the display, or in your router's device list).
2. Open `http://<display-ip>/` in a browser on the same network.
3. Find the **firmware update** page of the stock interface. On a tested Ultra the section is called **"7. Firmware update"** with an **UPLOAD** button. Other stock firmware versions may name it differently.
4. Choose `glancebox-ultra-<version>.bin` and start the upload.
5. **Do not unplug the display** for about a minute. It restarts on its own when the upload is done.

If the stock page rejects the file, the display keeps running the stock firmware. Check that you downloaded the `.bin` for the **Ultra** and that the download is complete (compare the MD5 or SHA-256).

## Step 4: What you see on first boot

After the restart:

1. The display shows **"Glance Box setup"**, a Wi-Fi name like `GlanceBox-A1B2` and the address `http://192.168.4.1`. This is the setup portal.
2. Continue with [Setup](setup.md): choose your Wi-Fi, enter the server address and set the update password.
3. After saving, the display restarts, briefly shows the version, its IP address and the server address, and then the first page from your server.
4. If the server cannot be reached, the last picture stays. After about two minutes without a picture, the display shows a status screen with the error.

If the display stays dark or shows nothing sensible after the first flash, see [Recovery](recovery.md).
