#pragma once
#include <Arduino.h>
#include <TFT_eSPI.h>

// Initialise the ST7789 (inversion on) and the inverted PWM backlight on GPIO5.
void displayBegin(uint8_t brightnessPct);
void displaySetBrightness(uint8_t pct);
// Draws a baseline 240x240 JPEG at (0,0). Returns false on decode error.
bool displayJpeg(const uint8_t* data, size_t len);
// Title (font 4) plus up to n lines (font 2), ASCII only.
void displayStatus(const char* title, const char* const* lines, size_t n);
// Direct access for the spike test pattern.
TFT_eSPI& displayTft();
