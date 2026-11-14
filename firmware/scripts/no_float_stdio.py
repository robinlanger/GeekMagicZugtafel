"""PlatformIO post-script: drop the core's forced float printf/scanf support.

The ESP8266 Arduino builder links with `-u _printf_float -u _scanf_float`, which pulls
~17 KB of float formatting/parsing into every image. Glance Box never formats or parses
floats with printf/scanf (checked: our src/ and lib/, WiFiManager, TFT_eSPI and the core
code paths we use; String(float) and TFT_eSPI::drawFloat use dtostrf, not printf).
Without these symbols a stray %f would print nothing instead of a number; nothing crashes.
"""

Import("env")  # noqa: F821  (provided by PlatformIO/SCons)

_DROP = {"_printf_float", "_scanf_float"}

flags = list(env["LINKFLAGS"])  # noqa: F821
kept = []
i = 0
while i < len(flags):
    if flags[i] == "-u" and i + 1 < len(flags) and flags[i + 1] in _DROP:
        i += 2  # skip "-u <symbol>" pair only; other -u flags (app_entry, ...) stay
        continue
    kept.append(flags[i])
    i += 1
env.Replace(LINKFLAGS=kept)  # noqa: F821
