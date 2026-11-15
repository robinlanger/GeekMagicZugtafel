#include "i18n.h"

#include "arduino_str.h"

#include "web_util.h"

namespace {
#define GB_STR(name, text) const char name[] PROGMEM = text;

// English
GB_STR(en0, "Status")
GB_STR(en1, "Uptime")
GB_STR(en2, "Signal")
GB_STR(en3, "Frames")
GB_STR(en4, "Last frame")
GB_STR(en5, "Safe mode")
GB_STR(en6, "Failed boots")
GB_STR(en7, "Settings")
GB_STR(en8, "Server URL")
GB_STR(en9, "Brightness (%)")
GB_STR(en10, "New update password (empty = keep)")
GB_STR(en11, "Save")
GB_STR(en12, "Saved.")
GB_STR(en13, "Changes need the update password (user admin).")
GB_STR(en14, "Firmware update")
GB_STR(en15, "MD5 of the .bin file")
GB_STR(en16, "Upload")
GB_STR(en17, "Device")
GB_STR(en18, "Restart")
GB_STR(en19, "Reset settings and Wi-Fi")
GB_STR(en20, "Really reset settings and Wi-Fi?")
GB_STR(en21, "Restarting...")
GB_STR(en22, "Reset done. The device restarts and opens the setup portal.")
GB_STR(en23, "Back")
GB_STR(en24, "Server URL: https is not supported, use http://")
GB_STR(en25, "Server URL: only http:// is supported")
GB_STR(en26, "Server URL: host is missing")
GB_STR(en27, "Server URL is too long")
GB_STR(en28, "Password must have at least 8 characters")
GB_STR(en29, "Password must have at most 32 characters")
GB_STR(en30, "Password: use printable ASCII characters only")
GB_STR(en31, "Brightness must be a number from 5 to 100")
GB_STR(en32, "Saving failed")
GB_STR(en33, "Current update password is wrong")
GB_STR(en34, "Reset failed: settings could not be erased")
GB_STR(en35, "Safe mode")
GB_STR(en36, "The device failed to boot several times and is running the minimal safe firmware. Upload a working firmware (.bin) below, or try the normal firmware again.")
GB_STR(en37, "Boot normal firmware")
GB_STR(en38, "Night from")
GB_STR(en39, "Night until")
GB_STR(en40, "Night brightness (%)")
GB_STR(en41, "Same times = night mode off. 0 % = completely dark.")
GB_STR(en42, "Local time")
GB_STR(en43, "Night")
GB_STR(en44, "Night times must be HH:MM")
GB_STR(en45, "Night brightness must be a number from 0 to 100")

// German
GB_STR(de0, "Status")
GB_STR(de1, "Laufzeit")
GB_STR(de2, "Signal")
GB_STR(de3, "Frames")
GB_STR(de4, "Letzter Frame")
GB_STR(de5, "Safe Mode")
GB_STR(de6, "Fehlstarts")
GB_STR(de7, "Einstellungen")
GB_STR(de8, "Server-URL")
GB_STR(de9, "Helligkeit (%)")
GB_STR(de10, "Neues Update-Passwort (leer = unverändert)")
GB_STR(de11, "Speichern")
GB_STR(de12, "Gespeichert.")
GB_STR(de13, "Änderungen brauchen das Update-Passwort (Benutzer admin).")
GB_STR(de14, "Firmware-Update")
GB_STR(de15, "MD5 der .bin-Datei")
GB_STR(de16, "Hochladen")
GB_STR(de17, "Gerät")
GB_STR(de18, "Neustart")
GB_STR(de19, "Einstellungen und WLAN zurücksetzen")
GB_STR(de20, "Einstellungen und WLAN wirklich zurücksetzen?")
GB_STR(de21, "Neustart ...")
GB_STR(de22, "Zurückgesetzt. Das Gerät startet neu und öffnet das Einrichtungsportal.")
GB_STR(de23, "Zurück")
GB_STR(de24, "Server-URL: https wird nicht unterstützt, bitte http://")
GB_STR(de25, "Server-URL: nur http:// wird unterstützt")
GB_STR(de26, "Server-URL: Host fehlt")
GB_STR(de27, "Server-URL ist zu lang")
GB_STR(de28, "Passwort braucht mindestens 8 Zeichen")
GB_STR(de29, "Passwort darf höchstens 32 Zeichen haben")
GB_STR(de30, "Passwort: nur druckbare ASCII-Zeichen")
GB_STR(de31, "Helligkeit muss eine Zahl von 5 bis 100 sein")
GB_STR(de32, "Speichern fehlgeschlagen")
GB_STR(de33, "Aktuelles Update-Passwort ist falsch")
GB_STR(de34, "Zurücksetzen fehlgeschlagen: Einstellungen nicht gelöscht")
GB_STR(de35, "Abgesicherter Modus")
GB_STR(de36, "Das Gerät ist mehrfach nicht hochgefahren und läuft mit der minimalen Notfall-Firmware. Lade unten eine funktionierende Firmware (.bin) hoch oder versuche es noch einmal mit der normalen Firmware.")
GB_STR(de37, "Normale Firmware starten")
GB_STR(de38, "Nacht von")
GB_STR(de39, "Nacht bis")
GB_STR(de40, "Helligkeit nachts (%)")
GB_STR(de41, "Gleiche Zeiten = Nachtmodus aus. 0 % = ganz dunkel.")
GB_STR(de42, "Uhrzeit")
GB_STR(de43, "Nacht")
GB_STR(de44, "Nachtzeiten müssen im Format HH:MM sein")
GB_STR(de45, "Helligkeit nachts muss eine Zahl von 0 bis 100 sein")

#undef GB_STR

const char* const kEn[] PROGMEM = {en0,  en1,  en2,  en3,  en4,  en5,  en6,  en7,  en8,
                                   en9,  en10, en11, en12, en13, en14, en15, en16, en17,
                                   en18, en19, en20, en21, en22, en23, en24, en25, en26,
                                   en27, en28, en29, en30, en31, en32, en33, en34, en35, en36, en37, en38, en39, en40, en41, en42, en43, en44, en45};
const char* const kDe[] PROGMEM = {de0,  de1,  de2,  de3,  de4,  de5,  de6,  de7,  de8,
                                   de9,  de10, de11, de12, de13, de14, de15, de16, de17,
                                   de18, de19, de20, de21, de22, de23, de24, de25, de26,
                                   de27, de28, de29, de30, de31, de32, de33, de34, de35, de36, de37, de38, de39, de40, de41, de42, de43, de44, de45};
static_assert(sizeof(kEn) / sizeof(kEn[0]) == static_cast<size_t>(Msg::Count), "kEn size");
static_assert(sizeof(kDe) / sizeof(kDe[0]) == static_cast<size_t>(Msg::Count), "kDe size");
}  // namespace

Lang langFromHeader(const String& acceptLanguage) {
  return gb::prefersGerman(strOrEmpty(acceptLanguage)) ? Lang::De : Lang::En;
}

const __FlashStringHelper* tr(Lang lang, Msg msg) {
  const char* const* table = lang == Lang::De ? kDe : kEn;
  return reinterpret_cast<const __FlashStringHelper*>(
      pgm_read_ptr(&table[static_cast<size_t>(msg)]));
}

Msg msgForError(const std::string& code, bool isPassword) {
  if (code == "https_unsupported") return Msg::ErrHttps;
  if (code == "unsupported_scheme") return Msg::ErrScheme;
  if (code == "empty_host") return Msg::ErrEmptyHost;
  if (code == "too_short") return Msg::ErrPwShort;
  if (code == "invalid_chars") return Msg::ErrPwChars;
  if (code == "too_long") return isPassword ? Msg::ErrPwLong : Msg::ErrTooLong;
  return Msg::ErrSaveFailed;
}
