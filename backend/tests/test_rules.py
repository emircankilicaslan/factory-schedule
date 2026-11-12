from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.rules import RuleViolation, as_utc, validate_update

NOW = datetime(2030, 1, 1, 8, 0, tzinfo=timezone.utc)


def op(id_, start_h, end_h):
    base = datetime(2030, 1, 1, 0, 0, tzinfo=timezone.utc)
    return SimpleNamespace(id=id_, start=base + timedelta(hours=start_h), end=base + timedelta(hours=end_h))


def at(hour, minute=0):
    return datetime(2030, 1, 1, hour, minute, tzinfo=timezone.utc)


def test_valid_update_is_normalized_to_utc():
    s, e = validate_update(at(10), at(11), None, None, [], NOW)
    assert (s, e) == (at(10), at(11))


def test_naive_datetimes_are_treated_as_utc():
    naive = datetime(2030, 1, 1, 10, 0)
    assert as_utc(naive).tzinfo == timezone.utc
    s, _ = validate_update(naive, naive + timedelta(hours=1), None, None, [], NOW)
    assert s == at(10)


def test_end_must_be_after_start():
    with pytest.raises(RuleViolation) as e:
        validate_update(at(10), at(10), None, None, [], NOW)
    assert e.value.code == "INVALID"


def test_r1_cannot_start_before_previous_ends():
    with pytest.raises(RuleViolation) as e:
        validate_update(at(9, 30), at(11), op("OP-1", 8, 10), None, [], NOW)
    assert e.value.code == "R1" and "OP-1" in e.value.message


def test_r1_may_start_exactly_when_previous_ends():
    validate_update(at(10), at(11), op("OP-1", 8, 10), None, [], NOW)


def test_r1_cannot_end_after_next_starts():
    with pytest.raises(RuleViolation) as e:
        validate_update(at(10), at(12), None, op("OP-3", 11, 13), [], NOW)
    assert e.value.code == "R1" and "OP-3" in e.value.message


def test_r2_overlap_on_same_machine_is_rejected():
    with pytest.raises(RuleViolation) as e:
        validate_update(at(10), at(12), None, None, [op("OP-9", 11, 13)], NOW)
    assert e.value.code == "R2" and "OP-9" in e.value.message


def test_r2_touching_intervals_do_not_overlap():
    validate_update(at(10), at(12), None, None, [op("A", 8, 10), op("B", 12, 14)], NOW)


def test_r3_start_in_the_past_is_rejected():
    with pytest.raises(RuleViolation) as e:
        validate_update(at(7, 59), at(9), None, None, [], NOW)
    assert e.value.code == "R3"


def test_r3_start_equal_to_now_is_allowed():
    validate_update(NOW, NOW + timedelta(hours=1), None, None, [], NOW)