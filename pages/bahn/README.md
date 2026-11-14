# bahn: departure board / Abfahrtstafel

## English

Live departures for a German station from [DBF](https://dbf.finalrewind.org) (db-infoscreen).

```yaml
- type: bahn
  station: "Frankfurt(Main)Hbf"   # required
  via: [Wiesbaden, Mainz]         # optional: only trains calling at these places (string or list)
  platforms: "101,102"            # optional: only these platforms (string or list)
  limit: 4                        # 1-6 rows, default 4 (fewer rows = bigger text)
  title: "Frankfurt"              # header text, default: station
  dbf_url: https://dbf.finalrewind.org
  refresh: 60                     # seconds, minimum 60 (DBF rule)
```

Display: line badge (S green, long distance white/red, RB/RE red), minutes to departure
(yellow at 3 min or less), `+delay` (orange below 6 min, red above), `Gl. X` (orange if the
platform changed), cancelled trains struck through in red. If DBF cannot be reached the page
shows "Keine Daten"; an empty list shows "Keine Abfahrten". The layout is `template.html`.

This is a deliberate exception to the server's rule that a failing page keeps its last good
picture for up to 10 minutes: old departure minutes would count down wrongly, so the page
reports the failure at once (and logs it) instead of raising an error.

## Deutsch

Live-Abfahrten für einen deutschen Bahnhof von [DBF](https://dbf.finalrewind.org) (db-infoscreen).

```yaml
- type: bahn
  station: "Frankfurt(Main)Hbf"   # Pflicht
  via: [Wiesbaden, Mainz]         # optional: nur Züge mit Halt an diesen Orten (Text oder Liste)
  platforms: "101,102"            # optional: nur diese Gleise (Text oder Liste)
  limit: 4                        # 1-6 Zeilen, Standard 4 (weniger Zeilen = größere Schrift)
  title: "Frankfurt"              # Kopfzeile, Standard: station
  dbf_url: https://dbf.finalrewind.org
  refresh: 60                     # Sekunden, mindestens 60 (DBF-Regel)
```

Anzeige: Linien-Badge (S grün, Fernverkehr weiß/rot, RB/RE rot), Minuten bis Abfahrt (gelb ab
3 Minuten oder weniger), `+Verspätung` (orange unter 6 Min., sonst rot), `Gl. X` (orange bei
Gleiswechsel), ausfallende Züge rot durchgestrichen. Ist DBF nicht erreichbar, zeigt die Seite
„Keine Daten“; eine leere Liste zeigt „Keine Abfahrten“. Das Layout steht in `template.html`.

Das ist eine bewusste Ausnahme von der Server-Regel, dass eine fehlerhafte Seite ihr letztes
gutes Bild bis zu 10 Minuten behält: Alte Abfahrtsminuten würden falsch weiterzählen, deshalb
meldet die Seite den Fehler sofort (und schreibt ihn ins Log), statt eine Ausnahme zu werfen.
