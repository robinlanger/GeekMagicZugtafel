import pytest

from glancebox.schedule import clamp_next_in, select


def test_select_slots():
    d = [30, 15]
    a = [True, True]
    assert select(d, a, 0) == (0, 30)
    assert select(d, a, 29) == (0, 1)
    assert select(d, a, 30) == (1, 15)
    assert select(d, a, 45) == (0, 30)


def test_select_skips_unavailable():
    assert select([30, 15], [False, True], 0) == (1, 30)


def test_select_none_available():
    assert select([30, 15], [False, False], 0) == (None, 30)


def test_select_invalid_input():
    with pytest.raises(ValueError):
        select([], [], 0)
    with pytest.raises(ValueError):
        select([30], [True, True], 0)


def test_clamp_next_in():
    assert clamp_next_in(0.2) == 2
    assert clamp_next_in(14.1) == 15
    assert clamp_next_in(90) == 30
