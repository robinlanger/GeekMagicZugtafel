# Server configuration

The whole server is configured by one file, `config.yaml`. Start from `config.example.yaml`.

## Where the file lives

With the supplied `docker-compose.yml` the server reads `./config.yaml` from the project folder (mounted read-only at `/config/config.yaml`). Your own pages go into `./pages-custom` (mounted at `/config/pages`, see [Writing pages](writing-pages.md)). **Create that folder before the first start** (`mkdir pages-custom`), otherwise Docker creates it as root.

After every change restart the server:

```sh
docker compose restart
docker compose logs --tail 50
```

The server checks the file at startup. If something is wrong (a typo in a key, an unknown page type, a refresh below the minimum) it refuses to start and prints a clear message to the log.

## Top-level options

| Key | Default | Meaning |
| --- | --- | --- |
| `interval` | `30` | Default display time of a page in seconds. |
| `timezone` | `Europe/Berlin` | Time zone for clocks and times on pages (IANA name). |
| `lang` | `de` | Default language of the built-in pages (`de` or `en`). |
| `custom_pages_dir` | not set | Folder with your own page types. Relative paths are relative to the config file. It may be missing, the server then logs a warning and uses the built-in pages only. In Docker use `/config/pages`. |
| `pages` | required | The playlist, at least one page. |

Unknown top-level keys are rejected.

## Options every page has

```yaml
pages:
  - type: clock
    duration: 15
    refresh: 60
```

| Key | Default | Meaning |
| --- | --- | --- |
| `type` | required | Page type: `url`, `bahn`, `clock` or one of your own. |
| `duration` | `interval` | How many seconds the page stays on the display. |
| `refresh` | `duration` | A page is rendered again at most every `refresh` seconds. Use a larger value for data that changes slowly or for services that limit requests. |

All other keys belong to the page type and are described below.

## Page type: url

Renders a web page as it is, in a browser window of exactly 240x240 pixels.

```yaml
- type: url
  url: http://homeserver.lan/status-240
  wait_for: "#ready"
  wait_ms: 500
  duration: 15
  refresh: 30
```

| Key | Default | Meaning |
| --- | --- | --- |
| `url` | required | `http://` or `https://` address. |
| `wait_for` | none | CSS selector. The screenshot is taken only after an element matching it exists. Use this for pages that build their content with JavaScript. |
| `wait_ms` | `0` | Extra pause in milliseconds before the screenshot (after the page loaded and `wait_for` matched). |
| `timeout_s` | `15` | How long loading and `wait_for` may take before the page counts as failed. |

The server runs in a container. `localhost` there means the container itself, so use the LAN address or name of the other machine. Pages that need a login show the login screen. Tips for designing such pages are in [Writing pages](writing-pages.md#the-url-page-and-its-tips).

## Page type: bahn

Live departures for a German station, from [DBF](https://dbf.finalrewind.org) (db-infoscreen).

```yaml
- type: bahn
  station: "Frankfurt(Main)Hbf"
  via: [Wiesbaden, Mainz]
  platforms: "101,102"
  limit: 4
  title: "Frankfurt"
  refresh: 60
```

| Key | Default | Meaning |
| --- | --- | --- |
| `station` | required | Station name, EVA number or DS100 code. Find the exact name on dbf.finalrewind.org: the part of the address after the search. |
| `via` | all | Only trains that stop at one of these places **after** your station (text or list). Intermediate stops work better than final destinations, because they also catch trains that end earlier. |
| `platforms` | all | Only these platforms (text or list). |
| `limit` | `4` | Rows, 1 to 6. Fewer rows mean bigger text. |
| `title` | the station | Header text. |
| `dbf_url` | `https://dbf.finalrewind.org` | Address of a DBF instance, if you run your own. |
| `refresh` | `60` | **At least 60.** This is DBF's rule of one request per station and minute. If you do not set `refresh` it is raised to 60 automatically. If you set a value below 60 the server refuses to start. |

If DBF cannot be reached the page shows "Keine Daten", an empty list shows "Keine Abfahrten". More details are in `pages/bahn/README.md`.

## Page type: clock

A large clock with weekday and date, meant as the starting point for your own pages.

```yaml
- type: clock
  lang: en
  refresh: 60
```

| Key | Default | Meaning |
| --- | --- | --- |
| `lang` | top-level `lang` | `de` or `en`. |

## How the playlist behaves

- The page currently shown follows from the **clock**: the durations of all pages add up to one cycle, and the position in the cycle is the current time modulo that sum. The server keeps no state per device, so several displays show the same page at the same time.
- The display asks the server for the next picture after the time the server names. That time is always between 2 and 30 seconds. The picture only travels if it changed, otherwise the server answers "not modified".
- Pictures are baseline JPEGs of 240x240 pixels and at most 24 576 bytes. The server lowers the quality (from 85 down to 40) until a picture fits. Very detailed images (photos, fine gradients) may still fail, flat colors work best.
- If a page fails (data source down, template error), the server keeps showing its **last good picture for up to 10 minutes**. After that the page is skipped. If no page works at all, the display shows an error page instead of a black screen. Errors are in the log and on the preview page.

## Checking and operating the server

| Address | What it does |
| --- | --- |
| `http://<server>:8080/` | Preview of all pages with age and last error (refreshes itself). |
| `http://<server>:8080/preview/<n>.jpg` | The current picture of page number `n` (counting from 0). |
| `http://<server>:8080/healthz` | Small JSON for health checks (Docker uses it). |
| `http://<server>:8080/api/v1/frame` | What the display fetches. |

The server runs as a normal (non-root) user and has **no login**. Keep port 8080 inside your home network. To use another port change the left number in `ports:` of `docker-compose.yml`, for example `"9090:8080"`.

Updates of the server: `git pull` and `docker compose up -d --build`. Releases also publish a ready-made image, `ghcr.io/robinlanger/glancebox:<version>`, for amd64 and arm64.
