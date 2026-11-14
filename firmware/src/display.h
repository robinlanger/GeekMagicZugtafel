#pragma once
#include <Arduino.h>
#include <TFT_eSPI.h>

// Initialise the ST7789 (inversion on) and the inverted PWM backlight on GPIO5.
void displayBegin(uint8_t brightnessPct);
void displaySetBrightness(uint8_t pct);
enum class JpegStreamResult : uint8_t { Ok, InputError, DecodeError };
// Decodes a baseline 240x240 JPEG of exactly len bytes straight from the stream to (0,0),
// block by block (no frame buffer). Never reads beyond len bytes; gives up when the body
// is not complete within deadlineMs. On failure the frame is left partially drawn.
JpegStreamResult displayJpegStream(Stream& stream, size_t len, uint32_t deadlineMs);
// Title (font 4) plus up to n lines (font 2), ASCII only.
void displayStatus(const char* title, const char* const* lines, size_t n);
// Direct access for the spike test pattern.
TFT_eSPI& displayTft();
