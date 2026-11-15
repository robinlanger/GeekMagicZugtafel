#pragma once
#include <Arduino.h>

// C string of an Arduino String that honours its length.
//
// ESP8266 core: String::clear() only sets the length to 0 and does not write a NUL,
// so c_str() of a cleared String still returns the old text. ESP8266WebServer clears
// collected request headers that way before every request, so a header the current
// request did not send would otherwise read as the previous request's value.
inline const char* strOrEmpty(const String& s) { return s.length() > 0 ? s.c_str() : ""; }
