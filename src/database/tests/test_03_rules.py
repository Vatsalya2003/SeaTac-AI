"""
3. Rule compliance: every view against an independent pandas recalculation from the Excel file
(tests/excel_expected.py, following docs/CLIENT_CONFIRMED_RULES.md), flight by flight.

Durations, exclusions, exclusion reasons and selection date/hour must match. Only "N matched, M mismatched"
and the mismatching keys are reported, never the values.
"""
from decimal import Decimal

import pytest

from conftest import rows

# view -> (key columns, compared columns)
FLIGHT_KEY = ["flight_info_id", "operation"]
SELECTION = ["selection_date", "selection_hour"]
AIRCRAFT = ["aircraft_type_group"]
CHECKS = {
    "v_taxi_in": (FLIGHT_KEY, ["duration_sec", "exclusion_reason", "included", "weight_class_group"] + SELECTION + AIRCRAFT),
    "v_taxi_out": (FLIGHT_KEY, ["duration_sec", "exclusion_reason", "included", "weight_class_group"] + SELECTION + AIRCRAFT),
    "v_movement_area": (FLIGHT_KEY, ["duration_sec", "exclusion_reason", "included"] + SELECTION + AIRCRAFT),
    "v_runway_occupancy": (FLIGHT_KEY, ["duration_sec", "exclusion_reason", "included"] + SELECTION + AIRCRAFT),
    "v_takeoff_delay": (FLIGHT_KEY, ["delay_sec", "exclusion_reason", "included"] + SELECTION + AIRCRAFT),
    "v_taxiway_usage": (FLIGHT_KEY + ["segment_role"], ["taxiway_segment", "taxiway_letter", "taxiway_name",
                                                         "segment_number", "exclusion_reason", "included"] + SELECTION),
    "v_runway_activity": (FLIGHT_KEY, ["activity", "is_missed_approach", "exclusion_reason", "included"] + SELECTION),
    "v_peak_hours": (["local_date", "local_hour"], ["operations", "takeoffs", "landings", "hour_rank"]),
    "v_movement_area_hourly_peak": (["local_date", "local_hour"], [
        "max_aircraft_in_area", "intervals_used", "intervals_excluded", "excluded_missing_time",
        "excluded_negative_duration"]),
}
MINUTE_COLUMNS = {"v_taxi_in": ("duration_min", "duration_sec"), "v_taxi_out": ("duration_min", "duration_sec"),
                  "v_movement_area": ("duration_min", "duration_sec"), "v_takeoff_delay": ("delay_min", "delay_sec")}


def normalise(v):
    return int(v) if isinstance(v, Decimal) else v  # SUM() returns DECIMAL


def compare(expected, actual):
    """-> (matched count, sorted mismatching keys). A key missing on either side is a mismatch."""
    bad = {k for k in expected.keys() | actual.keys()
           if k not in expected or k not in actual
           or any(normalise(actual[k][c]) != expected[k][c] for c in expected[k] if c in actual[k])}
    return len(expected.keys() | actual.keys()) - len(bad), sorted(bad, key=str)


@pytest.mark.parametrize("view", list(CHECKS))
def test_view_matches_excel_recalculation(db, expected, report, view):
    keys, cols = CHECKS[view]
    actual = {tuple(r[:len(keys)]): dict(zip(cols, r[len(keys):]))
              for r in rows(db, f"SELECT {', '.join(keys + cols)} FROM {view}")}
    want = {k: {c: v[c] for c in cols} for k, v in expected[view].items()}
    matched, bad = compare(want, actual)
    label = "hours" if keys[0] == "local_date" else "rows"
    ids = sorted({k[0] for k in bad}) if label == "rows" else [f"{d} {h:02d}:00" for d, h in bad]
    report(f"{view}: {matched} matched, {len(bad)} mismatched ({label})" + (f" - {ids}" if bad else ""))
    assert not bad, f"mismatching {'flight_info_ids' if label == 'rows' else 'hours'}: {ids}"


@pytest.mark.parametrize("view", list(MINUTE_COLUMNS))
def test_minutes_equal_seconds_over_60(db, view):
    minutes, seconds = MINUTE_COLUMNS[view]
    bad = [r[0] for r in rows(db, f"""SELECT flight_info_id FROM {view}
                                      WHERE ABS({minutes} - {seconds} / 60) >= 0.0001
                                         OR ({minutes} IS NULL) <> ({seconds} IS NULL)""")]
    assert not bad, f"{view}: {minutes} disagrees with {seconds} for flight_info_ids {sorted(bad)}"


def test_weight_classes_list(db):
    assert rows(db, "SELECT weight_class_group, label FROM v_weight_classes ORDER BY sort_order") == (
        ("L", "Light"), ("M", "Medium"), ("H", "Heavy"), ("Unknown", "Unknown"))
