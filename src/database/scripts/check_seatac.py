"""
Verify the `seatac` database after running load_aerobahn.py.

Prints counts, keys, exclusions per view, agreement with the export's own durations (sys_* columns),
and a comparison with the old AIplane database. It deliberately does NOT print metric averages or
answers to the Port's questions (the team computes expected answers independently).

Usage:
    python check_seatac.py [--database seatac] [--old-database AIplane] [--env-file ../../backend/.env]
"""
import argparse
from pathlib import Path

import pymysql
import yaml

from load_aerobahn import DEFAULT_ENV_FILE, DATABASE_DIR, db_settings

VIEWS = ["v_taxi_in", "v_taxi_out", "v_movement_area", "v_runway_occupancy",
         "v_takeoff_delay", "v_taxiway_usage", "v_runway_activity"]
SYS_CHECKS = [  # (label, view, calculated column, system column)
    ("taxi-in", "v_taxi_in", "duration_sec", "sys_taxi_in_sec"),
    ("taxi-out", "v_taxi_out", "duration_sec", "sys_taxi_out_sec"),
    ("runway occupancy", "v_runway_occupancy", "duration_sec", "sys_runway_occupancy_sec"),
]


def rows(cur, sql, args=None):
    cur.execute(sql, args)
    return cur.fetchall()


def table(title, header, data):
    print(f"\n{title}")
    print("  | " + " | ".join(header) + " |")
    for r in data:
        print("  | " + " | ".join("NULL" if v is None else str(v) for v in r) + " |")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--database", default="seatac")
    p.add_argument("--old-database", default="AIplane")
    p.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    args = p.parse_args()

    conn = pymysql.connect(**db_settings(args.env_file), database=args.database)
    cur = conn.cursor()
    db, old = f"`{args.database}`", f"`{args.old_database}`"

    table("1. Rows by operation (flights)", ["operation", "rows"],
          rows(cur, "SELECT operation, COUNT(*) FROM flights GROUP BY operation ORDER BY operation"))
    print("   total flights:", rows(cur, "SELECT COUNT(*) FROM flights")[0][0],
          "| raw_flight_details:", rows(cur, "SELECT COUNT(*) FROM raw_flight_details")[0][0],
          "| aircraft_types:", rows(cur, "SELECT COUNT(*) FROM aircraft_types")[0][0])

    dup_key = rows(cur, "SELECT COUNT(*) FROM (SELECT 1 FROM flights GROUP BY flight_info_id, operation HAVING COUNT(*) > 1) d")[0][0]
    rep = rows(cur, """SELECT GROUP_CONCAT(operation ORDER BY operation SEPARATOR ' + ') AS ops, COUNT(*) AS ids
                       FROM (SELECT flight_info_id, operation FROM flights
                             WHERE flight_info_id IN (SELECT flight_info_id FROM flights GROUP BY flight_info_id HAVING COUNT(*) > 1)) x
                       GROUP BY flight_info_id""")
    print(f"\n2. Keys: duplicate (flight_info_id, operation) pairs = {dup_key}; "
          f"flight_info_id values used by more than one leg = {len(rep)}")
    for ops, n in rep:
        print(f"   - one flight_info_id shared by: {ops}")

    table("3. sea_date values", ["sea_date", "rows"],
          rows(cur, "SELECT sea_date, COUNT(*) FROM flights GROUP BY sea_date ORDER BY sea_date"))
    print("   aircraft_type NULL legs:", rows(cur, "SELECT COUNT(*) FROM flights WHERE aircraft_type IS NULL")[0][0],
          "| orphan aircraft types (FK check):",
          rows(cur, "SELECT COUNT(*) FROM flights f LEFT JOIN aircraft_types a USING (aircraft_type) "
                    "WHERE f.aircraft_type IS NOT NULL AND a.aircraft_type IS NULL")[0][0])

    print("\n4. Views: rows, included rows, exclusions by reason (no averages)")
    for v in VIEWS:
        total, included = rows(cur, f"SELECT COUNT(*), SUM(exclusion_reason IS NULL) FROM {v}")[0]
        reasons = rows(cur, f"SELECT exclusion_reason, COUNT(*) FROM {v} WHERE exclusion_reason IS NOT NULL "
                            f"GROUP BY exclusion_reason ORDER BY exclusion_reason")
        by_op = rows(cur, f"SELECT operation, COUNT(*), SUM(exclusion_reason IS NULL) FROM {v} GROUP BY operation ORDER BY operation")
        print(f"   {v}: rows {total}, included {int(included or 0)}, excluded "
              f"{', '.join(f'{r}={n}' for r, n in reasons) or 'none'}"
              f"  [by operation: {'; '.join(f'{o} {t}/{int(i or 0)} incl' for o, t, i in by_op)}]")
    hours = rows(cur, "SELECT COUNT(*), MIN(TIMESTAMP(local_date, MAKETIME(local_hour,0,0))), "
                      "MAX(TIMESTAMP(local_date, MAKETIME(local_hour,0,0))) FROM v_movement_area_hourly_peak")[0]
    print(f"   v_movement_area_hourly_peak: {hours[0]} hourly rows, from {hours[1]} to {hours[2]} (values not shown)")

    print("\n5. Our durations vs the export's own (sys_*) columns, included rows with both values")
    print("   difference = ours - sys, in seconds")
    for label, view, calc, sys_col in SYS_CHECKS:
        n, mean_d, mean_abs, max_abs, exact, within60 = rows(cur, f"""
            SELECT COUNT(*), ROUND(AVG({calc} - {sys_col}), 1), ROUND(AVG(ABS({calc} - {sys_col})), 1),
                   MAX(ABS({calc} - {sys_col})), SUM({calc} = {sys_col}), SUM(ABS({calc} - {sys_col}) <= 60)
            FROM {view} WHERE exclusion_reason IS NULL AND {sys_col} IS NOT NULL""")[0]
        print(f"   {label}: n={n}, mean diff {mean_d}s, mean |diff| {mean_abs}s, max |diff| {max_abs}s, "
              f"exact {int(exact or 0)}, within 60 s {int(within60 or 0)}")

    print(f"\n6. Old ({args.old_database}) vs new ({args.database})")
    old_legs = rows(cur, f"SELECT operation, COUNT(*) FROM {old}.flight GROUP BY operation ORDER BY operation")
    print("   legs:", "old", dict(old_legs), "| new", dict(rows(cur, "SELECT operation, COUNT(*) FROM flights GROUP BY operation")))
    oc, nc, both = rows(cur, f"""SELECT (SELECT COUNT(DISTINCT call_sign) FROM {old}.flight),
                                        (SELECT COUNT(DISTINCT call_sign) FROM flights),
                                        (SELECT COUNT(DISTINCT o.call_sign) FROM {old}.flight o JOIN flights n ON n.call_sign = o.call_sign)""")[0]
    print(f"   distinct call signs: old {oc}, new {nc}, in both {both}")
    og, ng, gboth = rows(cur, f"""SELECT (SELECT COUNT(DISTINCT location) FROM {old}.flight_event WHERE location LIKE 'Gate%'),
                                         (SELECT COUNT(DISTINCT gate) FROM flights WHERE gate IS NOT NULL),
                                         (SELECT COUNT(DISTINCT n.gate) FROM flights n
                                            JOIN {old}.flight_event e ON e.location = n.gate)""")[0]
    print(f"   distinct gates: old {og} (from flight_event.location), new {ng} (flights.gate), in both {gboth}")
    matched, total_old = rows(cur, f"""
        SELECT SUM(EXISTS (
                 SELECT 1 FROM {old}.flight_event e
                 JOIN flights n ON n.call_sign = e.call_sign
                  AND n.operation = CASE e.operation WHEN 'ARRIVAL' THEN 'Arrival' ELSE 'Departure' END
                 WHERE e.call_sign = o.call_sign AND e.operation = o.operation
                   AND e.event_type = CASE o.operation WHEN 'ARRIVAL' THEN 'Actual_Landing' ELSE 'Actual_Take_Off' END
                   AND ABS(TIMESTAMPDIFF(SECOND, e.event_time,
                           CASE o.operation WHEN 'ARRIVAL' THEN n.wheels_down ELSE n.wheels_up END)) <= 120)),
               COUNT(*)
        FROM {old}.flight o""")[0]
    print(f"   old legs matching a new row (call sign + operation + SEA touchdown/take-off within 2 min): "
          f"{int(matched)} of {total_old}")

    print("\n7. metric_rules.yaml")
    rules = yaml.safe_load((DATABASE_DIR / "metric_rules.yaml").read_text(encoding="utf-8"))
    existing = {r[0] for r in rows(cur, "SELECT TABLE_NAME FROM information_schema.VIEWS WHERE TABLE_SCHEMA = DATABASE()")}
    for name, m in rules["metrics"].items():
        print(f"   {name}: view {m['view']} {'exists' if m['view'] in existing else 'MISSING'}")
    conn.close()


if __name__ == "__main__":
    main()
