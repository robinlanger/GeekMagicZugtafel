#pragma once
// Firmware version, injected from the repo-root VERSION file (scripts/version.py).
#ifndef GB_VERSION
#define GB_VERSION "dev"
#endif

// "GBVER:<version>" literal so tools can read the version from a .bin. An inline
// variable is emitted once per image however many files include this header. `used`
// keeps the compiler from dropping it; the linker (--gc-sections) only keeps it when
// something references it, so runtime code takes the version from here (gbVersion()).
__attribute__((used)) inline const char kGbVersionTag[] = "GBVER:" GB_VERSION;

// The version string ("0.1.0"), pointing into kGbVersionTag.
inline const char* gbVersion() { return kGbVersionTag + 6; }
