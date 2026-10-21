"""4. Edge cases named in the confirmed rules or found in the data. Cases are located from the Excel file, not hard-coded."""
import pandas as pd

from conftest import rows


def excel_times(excel, column):
    return pd.to_datetime(excel[column], errors="coerce")


def view_rows(db, view, cols, where="1=1", args=None):
    return {(r[0], r[1]): r[2:] for r in rows(db, f"SELECT flight_info_id, operation, {', '.join(cols)} FROM {view} WHERE {where}", args)}


def midnight_cases(excel, column):
    """Departures whose selection timestamp falls on an earlier local date than their SEA event."""
    t, ev = excel_times(excel, column), excel_times(excel, "Event Time (PDT)")
    hit = (excel["Operation"] == "Departure") & t.notna() & (t.dt.date != ev.dt.date)
    return {(int(i), "Departure"): d for i, d in zip(excel.loc[hit, "Flight Info ID"], t[hit].dt.date)}


def test_midnight_q2_selection_date_is_off_block_date(db, excel, report):
    cases = midnight_cases(excel, "Actual Off Block Time (Aerobahn) (PDT)")
    got = view_rows(db, "v_taxi_out", ["selection_date", "off_block_date", "sea_date"])
    bad = [k[0] for k, d in cases.items() if got[k][0] != d or got[k][1] != d or got[k][2] == d]
    report(f"midnight Q2 (pushback before midnight): {len(cases) - len(bad)} matched, {len(bad)} mismatched")
    assert cases, "no flight crossing midnight found in the data"
    assert not bad, f"selection_date is not the off-block date for flight_info_ids {sorted(bad)}"


def test_midnight_q4_selection_date_is_runway_entry_date(db, excel, report):
    cases = midnight_cases(excel, "Runway Entrance Time (PDT)")
    got = view_rows(db, "v_runway_occupancy", ["selection_date"])
    bad = [k[0] for k, d in cases.items() if got[k][0] != d]
    report(f"midnight Q4 (runway entry before midnight): {len(cases) - len(bad)} matched, {len(bad)} mismatched")
    assert cases, "no flight crossing midnight found in the data"
    assert not bad, f"selection_date is not the runway-entry date for flight_info_ids {sorted(bad)}"


def test_missing_times_give_the_right_reason(db, excel, report):
    arr, dep = excel["Operation"] == "Arrival", excel["Operation"] == "Departure"
    null = lambda c: excel[c].isna()
    cases = {  # view -> (legs with a missing endpoint in the Excel file, expected reason)
        "v_taxi_in": (arr & (null("Wheels Down (PDT)") | null("Actual In Block Time (Aerobahn) (PDT)")), "missing time"),
        "v_taxi_out": (dep & (null("Actual Off Block Time (Aerobahn) (PDT)") | null("Wheels Up (PDT)")), "missing time"),
        "v_movement_area": ((arr & (null("Wheels Down (PDT)") | null("Movement Area Exit Time (PDT)")))
                            | (dep & (null("Movement Area Entrance Time (PDT)") | null("Wheels Up (PDT)"))), "missing time"),
        "v_runway_occupancy": ((arr & (null("Wheels Down (PDT)") | null("Runway Exit Time (PDT)")))
                               | (dep & (null("Runway Entrance Time (PDT)") | null("Wheels Up (PDT)"))), "missing time"),
        "v_takeoff_delay": (dep & null("Scheduled Take Off Time (Aerobahn) (PDT)"), "missing scheduled take-off"),
    }
    total, bad = 0, []
    for view, (mask, reason) in cases.items():
        got = view_rows(db, view, ["exclusion_reason", "included"])
        keys = [(int(i), op) for i, op in zip(excel.loc[mask, "Flight Info ID"], excel.loc[mask, "Operation"])]
        total += len(keys)
        bad += [f"{view}:{k[0]}" for k in keys if got[k] != (reason, 0)]
    report(f"missing-time reasons: {total - len(bad)} matched, {len(bad)} mismatched")
    assert total, "no missing-time case found in the data"
    assert not bad, f"wrong reason or included flag: {bad}"


def test_qta3199_included(db):
    got = rows(db, "SELECT exclusion_reason, included FROM v_taxi_in WHERE call_sign = 'QTA3199'")
    assert got == ((None, 1),), "QTA3199 is not an included taxi-in row"


def test_missed_approach_flagged_and_not_counted(db, report):
    flagged = rows(db, "SELECT exclusion_reason, included, is_missed_approach FROM v_runway_activity WHERE operation = 'Missed Approach'")
    counted = rows(db, "SELECT COUNT(*) FROM v_runway_activity WHERE activity_time IS NOT NULL AND is_missed_approach = 0")[0][0]
    peak_total = rows(db, "SELECT SUM(operations) FROM v_peak_hours")[0][0]
    elsewhere = rows(db, """SELECT (SELECT COUNT(*) FROM v_taxi_in WHERE operation = 'Missed Approach')
                                 + (SELECT COUNT(*) FROM v_taxiway_usage WHERE operation = 'Missed Approach')""")[0][0]
    report(f"missed approaches: {len(flagged)} flagged, {elsewhere} counted in other views")
    assert flagged == (("missed approach", 0, 1),), "the missed approach is not flagged and excluded"
    assert peak_total == counted, "v_peak_hours does not equal take-offs + completed landings"
    assert elsewhere == 0, "the missed approach appears in v_taxi_in or v_taxiway_usage"


def test_shared_flight_info_id_gives_two_legs(db, excel, report):
    ids = excel["Flight Info ID"]
    shared = {int(i): set(excel.loc[ids == i, "Operation"]) for i in ids[ids.duplicated()].unique()}
    got = {}
    for i, op in rows(db, "SELECT flight_info_id, operation FROM v_runway_activity"):
        got.setdefault(i, []).append(op)
    bad = [i for i, ops in shared.items() if sorted(got.get(i, [])) != sorted(ops)]
    report(f"shared flight_info_id: {len(shared)} ids, {len(shared) - len(bad)} with two separate legs")
    assert shared, "no shared flight_info_id found in the data"
    assert not bad, f"not two separate legs for flight_info_ids {bad}"


def test_null_weight_class_becomes_unknown(db):
    for view in ("v_taxi_in", "v_taxi_out"):
        bad = rows(db, f"""SELECT COUNT(*) FROM {view}
                           WHERE weight_class_group <> COALESCE(weight_class_icao, 'Unknown') OR weight_class_group IS NULL""")[0][0]
        assert bad == 0, f"{view}: {bad} rows where weight_class_group is not the class or 'Unknown'"


def test_null_aircraft_type_becomes_unknown(db, excel, report):
    """Views grouped by aircraft type put legs with no FAA type in an 'Unknown' aircraft_type_group.
    aircraft_type itself stays NULL."""
    no_type = {(int(i), op) for i, op in zip(excel.loc[excel["Aircraft Type (FAA)"].isna(), "Flight Info ID"],
                                             excel.loc[excel["Aircraft Type (FAA)"].isna(), "Operation"])}
    total, bad = 0, []
    for view in ("v_taxi_in", "v_taxi_out", "v_movement_area", "v_runway_occupancy", "v_takeoff_delay"):
        got = view_rows(db, view, ["aircraft_type", "aircraft_type_group"])
        for k in no_type & got.keys():
            total += 1
            if got[k] != (None, "Unknown"):
                bad.append(f"{view}:{k[0]}")
        bad += [f"{view}:{k[0]}" for k, (t, g) in got.items() if t is not None and g != t]
    report(f"NULL aircraft type -> 'Unknown' group: {total - len(bad)} matched, {len(bad)} mismatched")
    assert total, "no leg without an aircraft type found in the data"
    assert not bad, f"aircraft_type_group is not 'Unknown' (or aircraft_type changed): {bad}"


def test_light_shows_no_data(db):
    """Light has no eligible rows: its count is 0 and its average is NULL (displayed as "No data"), never 0."""
    for view in ("v_taxi_in", "v_taxi_out"):
        n, avg_is_null = rows(db, f"""SELECT COUNT(t.flight_info_id), AVG(t.duration_min) IS NULL
                                      FROM v_weight_classes w
                                      LEFT JOIN {view} t ON t.weight_class_group = w.weight_class_group AND t.included = 1
                                      WHERE w.label = 'Light'""")[0]
        assert (n, avg_is_null) == (0, 1), f"{view}: Light does not come out as No data"


def test_q10_ties_share_rank(db, report):
    hours = rows(db, "SELECT local_date, local_hour, operations, hour_rank FROM v_peak_hours")
    bad, tied = [], set()
    for d, h, ops, rank in hours:
        same = [r for r in hours if r[0] == d and r[2] == ops]
        if len(same) > 1:
            tied.add((d, ops))
        if any(r[3] != rank for r in same) or rank != 1 + sum(r[0] == d and r[2] > ops for r in hours):
            bad.append(f"{d} {h:02d}:00")
    report(f"Q10 ties: {len(tied)} tied groups, {len(hours) - len(bad)} hours ranked correctly, {len(bad)} wrong")
    assert tied, "no tied hours in the data"
    assert not bad, f"wrong RANK for hours {bad}"


def test_event_on_the_hour_falls_in_that_hour(db, excel, report):
    cases = [  # (Excel column, view, operation the view takes it from)
        ("Wheels Up (PDT)", "v_takeoff_delay", "Departure"),
        ("Wheels Up (PDT)", "v_runway_activity", "Departure"),
        ("Movement Area Entrance Time (PDT)", "v_movement_area", "Departure"),
        ("Wheels Down (PDT)", "v_taxi_in", "Arrival"),
        ("Actual Off Block Time (Aerobahn) (PDT)", "v_taxi_out", "Departure"),
        ("Runway Entrance Time (PDT)", "v_runway_occupancy", "Departure"),
    ]
    total, bad = 0, []
    for column, view, op in cases:
        t = excel_times(excel, column)
        hit = (excel["Operation"] == op) & t.notna() & (t.dt.minute == 0) & (t.dt.second == 0)
        got = view_rows(db, view, ["selection_date", "selection_hour"])
        for i, ts in zip(excel.loc[hit, "Flight Info ID"], t[hit]):
            total += 1
            if got[(int(i), op)] != (ts.date(), ts.hour):
                bad.append(f"{view}:{int(i)}")
    peak_hours = {(d, h) for d, h in rows(db, "SELECT local_date, local_hour FROM v_movement_area_hourly_peak WHERE max_aircraft_in_area > 0")}
    t = excel_times(excel, "Movement Area Entrance Time (PDT)")
    hit = (excel["Operation"] == "Departure") & t.notna() & (t.dt.minute == 0) & (t.dt.second == 0)
    for ts in t[hit]:
        total += 1
        if (ts.date(), ts.hour) not in peak_hours:
            bad.append(f"v_movement_area_hourly_peak:{ts.hour:02d}:00")
    report(f"events at exactly hh:00:00: {total - len(bad)} matched, {len(bad)} mismatched")
    assert total, "no event at exactly hh:00:00 in the data"
    assert not bad, f"not placed in hour hh: {bad}"


def test_q4_example_gives_76_seconds(db, excel, report):
    """Port example: a departure with 76 s runway entry -> take-off and 111 s entry -> Clear Active must give 76 s."""
    t = lambda c: excel_times(excel, c)
    entry = t("Runway Entrance Time (PDT)")
    hit = ((excel["Operation"] == "Departure") & ((t("Clear Active (PDT)") - entry).dt.total_seconds() == 111)
           & ((t("Wheels Up (PDT)") - entry).dt.total_seconds() == 76))
    keys = [(int(i), "Departure") for i in excel.loc[hit, "Flight Info ID"]]
    got = view_rows(db, "v_runway_occupancy", ["duration_sec"])
    bad = [k[0] for k in keys if got[k][0] != 76]
    report(f"Q4 example flights: {len(keys) - len(bad)} give 76 s, {len(bad)} do not")
    assert keys, "Q4 example flight not found in the data"
    assert not bad, f"not 76 s for flight_info_ids {bad}"
