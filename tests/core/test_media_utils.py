"""Tests for pyplayer.core.media_utils — pure function tests."""
from __future__ import annotations

from pyplayer.core.media_utils import (
    get_hms,
    get_ratio_string,
    get_verbose_timestamp,
    remove_dict_value,
    remove_dict_values,
    scale,
)


class TestGetHms:
    def test_zero(self):
        assert get_hms(0) == (0, 0, 0, 0)

    def test_seconds_only(self):
        assert get_hms(45) == (0, 0, 45, 0)

    def test_minutes_and_seconds(self):
        assert get_hms(125) == (0, 2, 5, 0)

    def test_hours_minutes_seconds(self):
        # 1h 1m 1s = 3661
        assert get_hms(3661) == (1, 1, 1, 0)

    def test_milliseconds(self):
        h, m, s, ms = get_hms(5.67)
        assert h == 0
        assert m == 0
        assert s == 5
        assert ms == 67

    def test_exact_hour(self):
        assert get_hms(3600) == (1, 0, 0, 0)

    def test_large_value(self):
        # 25h 30m 45.12s
        total = 25 * 3600 + 30 * 60 + 45.12
        h, m, s, ms = get_hms(total)
        assert h == 25
        assert m == 30
        assert s == 45
        assert ms == 12

    def test_sub_millisecond(self):
        h, m, s, ms = get_hms(1.001)
        assert ms == 0  # rounded to 0 at 2 decimal places in centiseconds


class TestGetRatioString:
    def test_standard_16_9(self):
        assert get_ratio_string(1920, 1080) == '16:9'

    def test_standard_4_3(self):
        assert get_ratio_string(1024, 768) == '4:3'

    def test_square(self):
        assert get_ratio_string(100, 100) == '1:1'

    def test_zero_width(self):
        assert get_ratio_string(0, 100) == '0:0'

    def test_coprime(self):
        # 7:5 is already in lowest terms
        assert get_ratio_string(7, 5) == '7:5'

    def test_large_numbers(self):
        # 3840x2160 = 16:9
        assert get_ratio_string(3840, 2160) == '16:9'


class TestGetVerboseTimestamp:
    def test_single_second(self):
        assert get_verbose_timestamp(1) == '1 second'

    def test_plural_seconds_under_10(self):
        result = get_verbose_timestamp(5.3)
        assert result == '5.3 seconds'

    def test_exact_integer_seconds_under_10(self):
        result = get_verbose_timestamp(5.0)
        assert result == '5 seconds'

    def test_minutes_and_seconds(self):
        # 125s = 2m 5s
        result = get_verbose_timestamp(125)
        assert '2 minutes' in result
        assert '5 seconds' in result

    def test_hours_minutes_seconds(self):
        # 3661s = 1h 1m 1s
        result = get_verbose_timestamp(3661)
        assert '1 hour' in result
        assert '1 minute' in result
        assert '1 second' in result
        assert 'and' in result

    def test_plural_hours(self):
        result = get_verbose_timestamp(7200 + 60)  # 2h 1m
        assert '2 hours' in result

    def test_exactly_10_seconds(self):
        result = get_verbose_timestamp(10)
        assert result == '10 seconds'


class TestRemoveDictValue:
    def test_removes_existing_value(self):
        d = {'a': 1, 'b': 2, 'c': 3}
        remove_dict_value(d, 2)
        assert 'b' not in d
        assert len(d) == 2

    def test_no_match(self):
        d = {'a': 1, 'b': 2}
        remove_dict_value(d, 99)
        assert len(d) == 2

    def test_removes_first_match(self):
        d = {'a': 1, 'b': 1, 'c': 2}
        remove_dict_value(d, 1)
        assert len(d) == 2
        # 'a' should be removed (first match), 'b' stays
        assert 'a' not in d

    def test_empty_dict(self):
        d = {}
        remove_dict_value(d, 1)
        assert d == {}


class TestRemoveDictValues:
    def test_removes_multiple_values(self):
        d = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        remove_dict_values(d, 2, 4)
        assert 'b' not in d
        assert 'd' not in d
        assert len(d) == 2

    def test_no_matches(self):
        d = {'a': 1, 'b': 2}
        remove_dict_values(d, 99, 100)
        assert len(d) == 2

    def test_single_value(self):
        d = {'a': 1, 'b': 2}
        remove_dict_values(d, 1)
        assert 'a' not in d
        assert len(d) == 1

    def test_empty_dict(self):
        d = {}
        remove_dict_values(d, 1, 2)
        assert d == {}


class TestScale:
    def test_scale_by_x(self):
        x, y = scale(1920, 1080, new_x=960)
        assert x == 960
        assert y == 540

    def test_scale_by_y(self):
        x, y = scale(1920, 1080, new_y=540)
        assert x == 960
        assert y == 540

    def test_both_positive_returns_as_is(self):
        # When both new_x and new_y are positive, they're returned as-is
        x, y = scale(1920, 1080, new_x=960, new_y=999)
        assert x == 960
        assert y == 999

    def test_square_scale(self):
        x, y = scale(100, 100, new_x=50)
        assert x == 50
        assert y == 50

    def test_negative_means_unconstrained(self):
        # new_x=-1 means use new_y to calculate
        x, y = scale(4, 3, new_x=-1, new_y=600)
        assert x == 800
        assert y == 600
