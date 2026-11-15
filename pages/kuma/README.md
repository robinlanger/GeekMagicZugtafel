# kuma: state of an Uptime Kuma status page

User documentation: [docs/en/templates/kuma.md](../../docs/en/templates/kuma.md) ([Deutsch](../../docs/de/templates/kuma.md)). Developer notes below.

```yaml
- type: kuma
  url: http://192.168.1.20:3001   # http(s), required
  slug: home                      # status page slug, [a-z0-9-]+, required
  # title: Homelab                # default: title of the status page
  # lang: en                      # default: top-level lang
  refresh: 30                     # recommended; Kuma caches for 1 minute
```

- Two public requests per refresh: `/api/status-page/{slug}` (monitor list) and `/api/status-page/heartbeat/{slug}` (beats and 24 h uptime). The response shape is documented at the top of `page.py` (verified against Uptime Kuma 2.0.2).
- A monitor's state is the status of its last beat (0 down, 1 up, 2 pending, 3 maintenance); no beats means pending. Only status 0 is "down".
- Any exception from the requests or the parsing gives the `error` state (orange notice) so the display never keeps an old "all OK".
- `fetch` also returns `lang`, because the template has no other way to pick its texts.
