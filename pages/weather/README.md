# weather: current weather and the next four hours

User documentation: [docs/en/templates/weather.md](../../docs/en/templates/weather.md) ([Deutsch](../../docs/de/templates/weather.md)). Developer notes below.

Data comes from [Open-Meteo](https://open-meteo.com) (free, no key, CC BY 4.0). One geocoding request per `location` (cached for the life of the process), one forecast request per refresh.

```yaml
- type: weather
  location: Frankfurt am Main     # or latitude: 50.11 and longitude: 8.68, never both
  # title: Zuhause                # default: geocoded name, else "Wetter"/"Weather"
  # lang: en                      # default: top-level lang
  refresh: 900                    # minimum 900 (15 min)
```

- `fetch` lets errors propagate: the last image stays for up to 10 minutes.
- The four hours are the hourly slots after the current hour in the configured time zone, also across midnight.
- `icons.html` holds one macro `icon(key, w, h)` with flat SVGs; keys are `clear`, `partly`, `cloudy`, `fog`, `rain`, `snow`, `thunder`, plus `clear-night` and `partly-night`.
