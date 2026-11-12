from datetime import datetime
from zoneinfo import ZoneInfo

from zugtafel.departures import Departure, _clean_train, matches, parse, parse_directions
from zugtafel.render import SIZE, render

# Route enthält auch Halte VOR dem eigenen Bahnhof – die dürfen nicht matchen.
DIRECTIONS = {
    "departures": [
        {"train": "XY RB1", "destination": "Ost", "scheduledDeparture": "10:00",
         "route": [{"name": "West Hbf"}, {"name": "Musterstadt"}, {"name": "Ost"}]},
        {"train": "XY RB1", "destination": "West Hbf", "scheduledDeparture": "10:05",
         "route": [{"name": "Ost"}, {"name": "Musterstadt"}, {"name": "Mitte"}, {"name": "West Hbf"}]},
        {"train": "XY RB2", "destination": "Nord(Main)Hbf", "scheduledDeparture": "10:10",
         "route": [{"name": "Musterstadt"}, {"name": "Nord(Main)Hbf"}]},
    ]
}


def test_direction_filter_ignores_previous_stops():
    deps = parse(DIRECTIONS, "Musterstadt")
    dirs = parse_directions("West, nord")
    assert [d.destination for d in deps if matches(d, dirs)] == ["West Hbf", "Nord Hbf"]
    assert [d.destination for d in deps if matches(d, parse_directions("Mitte"))] == ["West Hbf"]
    assert all(matches(d, []) for d in deps)

SAMPLE = {
    "departures": [
        {"train": "HLB RB75", "destination": "Wiesbaden Hbf", "scheduledDeparture": "19:50",
         "delayDeparture": 4, "platform": "9", "scheduledPlatform": "9", "isCancelled": 0},
        {"train": "VIA RB66", "destination": "Darmstadt Hbf", "scheduledArrival": "19:53",
         "scheduledDeparture": None, "delayDeparture": None, "platform": "6", "isCancelled": 0},
        {"train": "S 3", "destination": "Bad Soden(Taunus)", "scheduledDeparture": "19:58",
         "delayDeparture": 0, "platform": "2", "scheduledPlatform": "1", "isCancelled": 0},
        {"train": "ICE 1234", "destination": "Hamburg-Altona", "scheduledDeparture": "20:05",
         "delayDeparture": None, "platform": "3", "scheduledPlatform": "3", "isCancelled": 1},
    ]
}

TZ = ZoneInfo("Europe/Berlin")


def test_clean_train():
    assert _clean_train("HLB RB75") == "RB75"
    assert _clean_train("S 1") == "S1"
    assert _clean_train("RE 60") == "RE60"
    assert _clean_train("ICE 123") == "ICE 123"


def test_parse_skips_arrivals_only():
    deps = parse(SAMPLE)
    assert [d.train for d in deps] == ["RB75", "S3", "ICE 1234"]
    assert deps[1].platform_changed is True
    assert deps[2].cancelled is True
    assert deps[1].destination == "Bad Soden"


def test_minutes_until_with_delay_and_midnight():
    now = datetime(2026, 11, 12, 19, 45, tzinfo=TZ)
    d = Departure("RB75", "X", "19:50", 4, None, False, False)
    assert d.minutes_until(now) == 9
    late = datetime(2026, 11, 12, 23, 55, tzinfo=TZ)
    d2 = Departure("S1", "X", "00:05", 0, None, False, False)
    assert d2.minutes_until(late) == 10


def test_render_sizes():
    now = datetime(2026, 11, 12, 19, 45, tzinfo=TZ)
    for img in (render("Musterstadt", parse(SAMPLE), now),
                render("Musterstadt", [], now),
                render("Musterstadt", None, now, error="Stand 19:45")):
        assert img.size == (SIZE, SIZE)


def test_bundled_fonts_have_umlauts():
    import os
    from zugtafel import render as r
    pkg_fonts = os.path.join(os.path.dirname(r.__file__), "fonts")
    for name in ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf",
                 "DejaVuSansCondensed.ttf", "DejaVuSansCondensed-Bold.ttf"):
        f = r.font(name, 13)
        assert getattr(f, "path", "").startswith(pkg_fonts), name
        assert f.getmask("ü").getbbox() is not None
