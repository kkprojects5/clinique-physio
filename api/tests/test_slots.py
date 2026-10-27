"""Slot computation edge cases (B-AVL-03 acceptance criteria)."""

from datetime import UTC, date, datetime, time, timedelta

from app.services.slots import CLINIC_TZ, Period, WeeklyRule, compute_slots, local_to_utc

MONDAY = date(2026, 10, 19)  # a regular Monday (daylight time, UTC-4)
LONG_AGO = datetime(2000, 1, 1, tzinfo=UTC)


def local(day, hour, minute=0):
    return local_to_utc(day, time(hour, minute))


def starts(slots):
    """Slot start times as local 'HH:MM' strings, easy to read in assertions."""
    return [s.start.astimezone(CLINIC_TZ).strftime("%H:%M") for s in slots]


def run(rules, day=MONDAY, duration=30, exceptions=(), appointments=(), last_day=None):
    return compute_slots(
        rules=rules,
        exceptions=list(exceptions),
        appointments=list(appointments),
        duration_minutes=duration,
        first_day=day,
        last_day=last_day or day,
        not_before=LONG_AGO,
    )


def test_slots_on_15_minute_grid_inside_working_hours():
    slots = run([WeeklyRule(1, time(8, 0), time(9, 0))])

    assert starts(slots) == ["08:00", "08:15", "08:30"]  # 08:45 + 30 min would end at 09:15


def test_last_slot_must_end_by_end_of_day():
    slots = run([WeeklyRule(1, time(15, 0), time(16, 0))], duration=60)

    assert starts(slots) == ["15:00"]


def test_service_longer_than_window_gives_no_slot():
    assert run([WeeklyRule(1, time(8, 0), time(8, 45))], duration=60) == []


def test_window_starting_off_grid_is_rounded_up():
    slots = run([WeeklyRule(1, time(8, 10), time(9, 0))])

    assert starts(slots) == ["08:15", "08:30"]


def test_other_weekdays_have_no_slots():
    assert run([WeeklyRule(2, time(8, 0), time(16, 0))]) == []  # rule is for Tuesday


def test_existing_appointment_blocks_its_time_plus_5_minute_buffer():
    booked = Period(local(MONDAY, 9, 0), local(MONDAY, 9, 30))
    slots = run([WeeklyRule(1, time(8, 0), time(11, 0))], appointments=[booked])

    # 08:30-09:00 ends too close (buffer); 09:30 starts too close; 09:45 is fine.
    assert "08:15" in starts(slots)
    assert "08:30" not in starts(slots)
    assert "09:30" not in starts(slots)
    assert "09:45" in starts(slots)


def test_overlapping_exceptions_are_all_respected():
    morning_off = Period(local(MONDAY, 8, 0), local(MONDAY, 10, 0))
    training = Period(local(MONDAY, 9, 30), local(MONDAY, 11, 0))
    slots = run([WeeklyRule(1, time(8, 0), time(12, 0))], exceptions=[morning_off, training])

    assert starts(slots) == ["11:00", "11:15", "11:30"]


def test_full_day_exception_removes_all_slots():
    vacation = Period(local(MONDAY, 0, 0), local(MONDAY + timedelta(days=1), 0, 0))

    assert run([WeeklyRule(1, time(8, 0), time(16, 0))], exceptions=[vacation]) == []


def test_two_rules_on_same_day_split_shift():
    rules = [WeeklyRule(1, time(8, 0), time(9, 0)), WeeklyRule(1, time(13, 0), time(14, 0))]

    assert starts(run(rules, duration=60)) == ["08:00", "13:00"]


def test_slots_in_the_past_are_not_offered():
    slots = compute_slots(
        rules=[WeeklyRule(1, time(8, 0), time(10, 0))],
        exceptions=[],
        appointments=[],
        duration_minutes=30,
        first_day=MONDAY,
        last_day=MONDAY,
        not_before=local(MONDAY, 9, 0),
    )

    assert starts(slots) == ["09:00", "09:15", "09:30"]


# --- Daylight saving time (challenge B-C2) ---------------------------------
# 2026-11-01: clocks go back 1 hour (UTC-4 -> UTC-5).
# 2027-03-14: clocks go forward 1 hour (UTC-5 -> UTC-4).


def test_monday_10am_stays_10am_local_after_november_change():
    before = run([WeeklyRule(1, time(10, 0), time(10, 30))], day=date(2026, 10, 26))
    after = run([WeeklyRule(1, time(10, 0), time(10, 30))], day=date(2026, 11, 2))

    assert starts(before) == starts(after) == ["10:00"]
    assert before[0].start.hour == 14  # 10:00 EDT = 14:00 UTC
    assert after[0].start.hour == 15  # 10:00 EST = 15:00 UTC


def test_monday_10am_stays_10am_local_after_march_change():
    before = run([WeeklyRule(1, time(10, 0), time(10, 30))], day=date(2027, 3, 8))
    after = run([WeeklyRule(1, time(10, 0), time(10, 30))], day=date(2027, 3, 15))

    assert starts(before) == starts(after) == ["10:00"]
    assert before[0].start.hour == 15
    assert after[0].start.hour == 14


def test_night_of_november_change_has_25_hours_of_real_time():
    sunday = date(2026, 11, 1)  # 01:00-02:00 happens twice
    slots = run([WeeklyRule(7, time(0, 0), time(4, 0))], day=sunday, duration=60)

    # 00:00 to 04:00 local is 5 real hours on this night (01:00-02:00 happens twice).
    assert slots[-1].end - slots[0].start == timedelta(hours=5)
    # Starts every 15 real minutes: (5 h - 1 h) / 15 min + 1 = 17 possible starts.
    assert len(slots) == 17
    assert all(
        b.start - a.start == timedelta(minutes=15) for a, b in zip(slots, slots[1:], strict=False)
    )


def test_night_of_march_change_has_one_hour_less():
    sunday = date(2027, 3, 14)  # 02:00-03:00 does not exist
    slots = run([WeeklyRule(7, time(0, 0), time(4, 0))], day=sunday, duration=60)

    assert slots[-1].end - slots[0].start == timedelta(hours=3)


def test_range_across_dst_change_keeps_local_times():
    slots = run(
        [WeeklyRule(d, time(9, 0), time(9, 30)) for d in range(1, 8)],
        day=date(2026, 10, 30),
        last_day=date(2026, 11, 3),
    )

    assert starts(slots) == ["09:00"] * 5
