# TJpgDec (vendored)

ChaN's Tiny JPEG Decompressor **R0.03** (Jul 01, 2021).

- Source: http://elm-chan.org/fsw/tjpgd/ (archive http://elm-chan.org/fsw/tjpgd/arc/tjpgd3.zip,
  SHA-256 `052fe3efbc9a8be29f31597ad009c5b51a4f6905878eb28569e0ab3d46d0c013`)
- License: ChaN's free-software terms in the header of `tjpgd.c` (kept verbatim).
- `tjpgd.c` and `tjpgd.h` are unmodified.
- `tjpgdcnf.h` is the original file with three values changed for Glance Box:
  `JD_FORMAT 1` (RGB565 output), `JD_USE_SCALE 0` (no descaling), `JD_FASTDECODE 1`
  (32-bit barrel shifter, no Huffman LUT: suits ESP8266 RAM).
- `library.json` is ours (PlatformIO metadata).

Replaces the Bodmer TJpg_Decoder wrapper, whose header drags SPIFFS and SD/SdFat
(~42 KB of dead code) into the image.
