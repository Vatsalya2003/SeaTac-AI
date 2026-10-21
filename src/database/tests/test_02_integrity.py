"""2. Data integrity: counts, unique key, raw link, the SEA-side rule, and every time identical to the Excel file."""
import pandas as pd
import pytest

from conftest import rows

EXPECTED_COUNTS = {"total": 1061, "Arrival": 525, "Departure": 535, "Missed Approach": 1}
# flights column -> (Excel column, operations whose value is SEA-side). Other operations must be NULL.
INBOUND, OUTBOUND = {"Arrival", "Missed Approach"}, {"Departure"}
FLIGHT_TIMES = {
    "scheduled_off_block": ("Scheduled Off Block Time (Aerobahn) (PDT)", OUTBOUND),
    "actual_off_block": ("Actual Off Block Time (Aerobahn) (PDT)", OUTBOUND),
    "scheduled_take_off": ("Scheduled Take Off Time (Aerobahn) (PDT)", OUTBOUND),
    "wheels_up": ("Wheels Up (PDT)", OUTBOUND),
    "scheduled_landing": ("Scheduled Landing Time (Aerobahn) (PDT)", INBOUND),
    "wheels_down": ("Wheels Down (PDT)", INBOUND),
    "scheduled_in_block": ("Scheduled In Block Time (Aerobahn) (PDT)", INBOUND),
    "actual_in_block": ("Actual In Block Time (Aerobahn) (PDT)", INBOUND),
    "runway_entrance": ("Runway Entrance Time (PDT)", INBOUND | OUTBOUND),
    "runway_exit": ("Runway Exit Time (PDT)", INBOUND | OUTBOUND),
    "movement_area_entrance": ("Movement Area Entrance Time (PDT)", INBOUND | OUTBOUND),
    "movement_area_exit": ("Movement Area Exit Time (PDT)", INBOUND | OUTBOUND),
    "sea_event_time": ("Event Time (PDT)", INBOUND | OUTBOUND),
}


def excel_time(v):
    return None if v is None or pd.isna(v) else pd.Timestamp(v).to_pydatetime()


def excel_key(r):
    return int(r["Flight Info ID"]), r["Operation"]


def test_counts_match_excel(db, excel, report):
    file_counts = {"total": len(excel), **excel["Operation"].value_counts().to_dict()}
    db_counts = {"total": rows(db, "SELECT COUNT(*) FROM flights")[0][0],
                 **dict(rows(db, "SELECT operation, COUNT(*) FROM flights GROUP BY operation"))}
    raw_total = rows(db, "SELECT COUNT(*) FROM raw_flight_details")[0][0]
    report(f"counts: flights {db_counts['total']}, raw {raw_total}, Excel {file_counts['total']}")
    assert file_counts == EXPECTED_COUNTS, "Excel file counts differ from 1,061 / 525 / 535 / 1"
    assert db_counts == EXPECTED_COUNTS, "flights counts differ from the Excel file"
    assert raw_total == EXPECTED_COUNTS["total"], "raw_flight_details count differs from the Excel file"


@pytest.mark.parametrize("table", ["flights", "raw_flight_details"])
def test_key_unique(db, table):
    total, distinct = rows(db, f"SELECT COUNT(*), COUNT(DISTINCT flight_info_id, operation) FROM {table}")[0]
    assert total == distinct, f"{total - distinct} duplicate (flight_info_id, operation) keys in {table}"


def test_every_flight_has_raw_row(db):
    orphans = [r[0] for r in rows(db, """SELECT f.flight_info_id FROM flights f
                                         LEFT JOIN raw_flight_details r USING (flight_info_id, operation)
                                         WHERE r.flight_info_id IS NULL""")]
    assert not orphans, f"{len(orphans)} flights rows with no raw row"


def test_sea_side_rule(db):
    bad = rows(db, """SELECT flight_info_id, operation FROM flights
                      WHERE (operation IN ('Arrival', 'Missed Approach') AND (actual_off_block IS NOT NULL OR wheels_up IS NOT NULL))
                         OR (operation = 'Departure' AND (wheels_down IS NOT NULL OR actual_in_block IS NOT NULL))""")
    assert not bad, f"{len(bad)} legs keep an other-airport time: {sorted(bad)}"


def test_flights_times_identical_to_excel(db, excel, report):
    cols = list(FLIGHT_TIMES)
    stored = {(r[0], r[1]): dict(zip(cols, r[2:])) for r in rows(db, f"SELECT flight_info_id, operation, {', '.join(cols)} FROM flights")}
    matched, mismatched = 0, set()
    for _, r in excel.iterrows():
        key = excel_key(r)
        for col, (src, sea_ops) in FLIGHT_TIMES.items():
            want = excel_time(r[src]) if key[1] in sea_ops else None
            if key in stored and stored[key][col] == want:
                matched += 1
            else:
                mismatched.add(key[0])
    report(f"flights times vs Excel: {matched} matched, {len(excel) * len(cols) - matched} mismatched (cells)")
    assert not mismatched, f"mismatching flight_info_ids: {sorted(mismatched)}"


def test_raw_times_identical_to_excel(db, excel, report):
    cols = [r[0] for r in rows(db, """SELECT COLUMN_NAME FROM information_schema.COLUMNS
                                      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'raw_flight_details'
                                        AND DATA_TYPE = 'datetime' ORDER BY ORDINAL_POSITION""")]
    select = ", ".join("`" + c.replace("`", "``") + "`" for c in cols)
    stored = {(r[0], r[1]): r[2:] for r in rows(db, f"SELECT flight_info_id, operation, {select} FROM raw_flight_details")}
    matched, mismatched = 0, set()
    for _, r in excel.iterrows():
        key = excel_key(r)
        for i, col in enumerate(cols):
            if key in stored and stored[key][i] == excel_time(r[col]):
                matched += 1
            else:
                mismatched.add(key[0])
    report(f"raw_flight_details times vs Excel ({len(cols)} datetime columns): {matched} matched, "
           f"{len(excel) * len(cols) - matched} mismatched (cells)")
    assert not mismatched, f"mismatching flight_info_ids: {sorted(mismatched)}"
