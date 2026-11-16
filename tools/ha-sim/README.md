# Simulated Home Assistant

A throwaway Home Assistant instance with template entities whose values follow the clock.
It exists to develop and live-test the Glance Box `homeassistant` page without a real smart
home. Nothing here is part of Glance Box itself.

## Setup on a Docker host

Copy this directory to the host, e.g. into `~/homeassistant-sim`:

```bash
ssh <host> mkdir -p ~/homeassistant-sim
rsync -a tools/ha-sim/ <host>:homeassistant-sim/
```

If the host runs Pi-hole (or another resolver that refuses queries from the Docker network),
the container cannot resolve names for onboarding and integrations. Point it at the router
instead with a local `~/homeassistant-sim/docker-compose.override.yml` (kept out of git, like
the Glance Box one):

```yaml
services:
  homeassistant-sim:
    dns: [<router-ip>]
```

Start it:

```bash
cd ~/homeassistant-sim && docker compose up -d
```

HA state (owner account, tokens, database) lives in the named volume `ha-data`. Only
`config/configuration.yaml` and `config/packages/` are mounted from this directory, read-only,
so editing them here and running `docker compose restart` picks up changes.

## Onboarding and token

1. Open `http://<host>:8123` and create the owner account in the onboarding.
2. Click your user name at the bottom left → tab **Security** → **Long-lived access tokens**
   → **Create token**, e.g. named `glancebox`.
3. Put the token only into local `.env` files, never into git or a chat. For the live test on
   the dev machine, in the repo root `.env` (git-ignored):

   ```
   HA_URL=http://<host-ip>:8123
   HA_TOKEN=...
   ```

## Entities

| Entity ID | Kind | Behaviour |
| --- | --- | --- |
| `sensor.temperatur_wohnzimmer` | temperature, °C | 20–22.5, daily curve |
| `sensor.luftfeuchte_wohnzimmer` | humidity, % | 45–60 |
| `sensor.temperatur_aussen` | temperature, °C | 2–14, daily curve |
| `sensor.luftfeuchte_aussen` | humidity, % | 60–95 |
| `sensor.hausverbrauch` | power, W | changes every minute, 250–3200 |
| `sensor.pv_leistung` | power, W | 0 at night, bell curve up to 4800 between 06:00 and 20:00 |
| `sensor.netz` | power, W | consumption − PV, negative while feeding in |
| `sensor.energie_heute` | energy, kWh | rises over the day |
| `sensor.speicher` | battery, % | 10–100, slowly |
| `sensor.akku_rauchmelder` | battery, % | constant 12 (low) |
| `sensor.kellersensor` | temperature, °C | `unavailable` every sixth minute |
| `binary_sensor.fenster_bad` | window | open when minute % 10 < 3 |
| `binary_sensor.haustur` | door | open when minute % 15 == 0 |
| `binary_sensor.bewegung_flur` | motion | on when minute % 4 == 0 |
| `light.licht_kuche` | light | on when minute % 6 < 3 |
| `light.licht_flur` | light | on from 17:00 to 01:00 |
| `switch.kaffeemaschine` | switch | on when minute % 20 < 5 |

Lights and the switch only follow their time pattern; turning them on or off does nothing.

## Cleanup

```bash
cd ~/homeassistant-sim && docker compose down -v
```

`-v` also removes the `ha-data` volume, i.e. the account and all tokens. No sudo needed.
