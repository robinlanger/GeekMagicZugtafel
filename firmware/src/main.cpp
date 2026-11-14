#include <Arduino.h>

#include "display.h"

#ifndef GB_VERSION
#define GB_VERSION "dev"
#endif
static const char kVersionTag[] __attribute__((used)) = "GBVER:" GB_VERSION;

void setup() {
  displayBegin(80);
  const char* lines[] = {"starting..."};
  displayStatus("Glance Box " GB_VERSION, lines, 1);
}

void loop() {}
