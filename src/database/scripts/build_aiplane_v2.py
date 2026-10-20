"""
Build `AIplane_v2`: the Port's new export loaded into Team 6's ORIGINAL 3-table layout
(aircraft_type, flight, flight_event), so the unchanged old chatbot can run on the new data
for a fair baseline.

Faithful to what produced the committed AIplane.sql:
  - table definitions are copied from data/AIplane.sql
  - column and event mapping from INSTALL.md (15 flight columns, 14 event types)
  - mechanics from db_manager.py: location tagged by event family (gate / runway / taxiway),
    operation cleaned to DEPARTURE/ARRIVAL (anything else -> NULL, no events), aircraft types
    inserted with ON DUPLICATE KEY UPDATE weight_class, missing types grouped into UNKNOWN_###.
  - other-airport times are NOT removed (the old layout never did), so its known traps remain.

Rerunnable: drops and rebuilds the target database. Never commit a dump of it (real tail numbers).

Usage:
    python build_aiplane_v2.py --file /path/to/August_8_and_9_2025_Anonymized.xlsx
"""
import argparse
import os
import re
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pymysql

from load_aerobahn import DATABASE_DIR, DEFAULT_ENV_FILE, clean, db_settings, quote

OLD_DUMP = DATABASE_DIR / "data" / "AIplane.sql"
PROTECTED = {"aiplane", "seatac", "mysql", "sys", "information_schema", "performance_schema"}

FLIGHT_MAP = {  # INSTALL.md "Table 2: flight Mapping"; new export uses (PDT) instead of (US Pacific)
    "call_sign": "Call Sign",
    "flight_ID": "Flight ID",
    "aircraft_type": "Aircraft Type (AODB)",
    "flight_number": "Flight Number",
    "aircraft_registration": "Registration (AODB)",
    "origin_airport": "Origination Airport (ICAO)",
    "destination_airport": "Destination Airport (ICAO)",
    "departure_procedure": "Departure Procedure (Filed)",
    "flight_origination_date": "Flight Origination Date (AODB)",
    "schedule_departure": "Scheduled Off Block Time (Aerobahn) (PDT)",
    "actual_departure": "Actual Off Block Time (Aerobahn) (PDT)",
    "schedule_arrival": "Estimated In Block Time (ATC) (PDT)",
    "actual_arrival": "Actual In Block Time (Aerobahn) (PDT)",
    "operation": "Operation",
}
AIRCRAFT_MAP = ["Aircraft Type (AODB)", "Weight Class (ICAO)", "Wake Category (Aerobahn)", "Wingspan (feet)", "Wingspan (meters)"]
GATE, RUNWAY, TAXIWAY = "Gate Assigned (Aerobahn)", "Runway Assigned (Aerobahn)", "Taxiway Used to Enter/Exit Runway"
EVENT_MAP = [  # INSTALL.md "Event Type Mappings": (event_type, source column, event_source, location column)
    ("Scheduled_Off_Block", "Scheduled Off Block Time (Aerobahn) (PDT)", "Aerobahn", GATE),
    ("Actual_Off_Block", "Actual Off Block Time (Aerobahn) (PDT)", "Aerobahn", GATE),
    ("Movement_Area_Entrance", "Movement Area Entrance Time (PDT)", "Aerobahn", TAXIWAY),
    ("Runway_Entrance", "Runway Entrance Time (PDT)", "Aerobahn", RUNWAY),
    ("Estimated_Take_Off", "Estimated Take Off Time (ATC) (PDT)", "ATC", RUNWAY),
    ("Actual_Take_Off", "Actual Take Off Time (Aerobahn) (PDT)", "Aerobahn", RUNWAY),
    ("Scheduled_Take_Off", "Scheduled Take Off Time (Aerobahn) (PDT)", "Aerobahn", RUNWAY),
    ("Estimated_Landing", "Estimated Landing Time (ATC) (PDT)", "ATC", RUNWAY),
    ("Actual_Landing", "Actual Landing Time (Aerobahn) (PDT)", "Aerobahn", RUNWAY),
    ("Runway_Exit", "Runway Exit Time (PDT)", "Aerobahn", RUNWAY),
    ("Movement_Area_Exit", "Movement Area Exit Time (PDT)", "Aerobahn", TAXIWAY),
    ("Estimated_In_Block", "Estimated In Block Time (ATC) (PDT)", "ATC", GATE),
    ("Actual_In_Block", "Actual In Block Time (Aerobahn) (PDT)", "Aerobahn", GATE),
    ("Boarding_Start", "Actual Start of Boarding Time (Aerobahn) (PDT)", "Aerobahn", GATE),
]


def old_table_ddl():
    """CREATE TABLE statements for aircraft_type, flight, flight_event, copied from AIplane.sql."""
    text = OLD_DUMP.read_text(encoding="utf-8")
    ddl = {}
    for name in ("aircraft_type", "flight", "flight_event"):
        m = re.search(rf"CREATE TABLE `{name}` \(.*?\) ENGINE=[^;]*;", text, re.S)
        if not m:
            sys.exit(f"Could not find CREATE TABLE `{name}` in {OLD_DUMP}")
        ddl[name] = re.sub(r" AUTO_INCREMENT=\d+", "", m.group(0)).rstrip(";")
    return ddl


def clean_operation(value):  # db_manager.py: DEPARTURE / ARRIVAL, otherwise NULL
    if value is None:
        return None
    value = str(value).strip().upper()
    return value if value in ("DEPARTURE", "ARRIVAL") else None


def as_date(value):
    return value.date() if hasattr(value, "date") else value


def span(value):  # wingspan as stored in DECIMAL(8,5)
    return None if value is None else Decimal(str(value)).quantize(Decimal("0.00001"))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--file", default=os.getenv("SEATAC_DATA_FILE"))
    p.add_argument("--database", default="AIplane_v2")
    p.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    args = p.parse_args()
    if not args.file:
        p.error("give --file or set SEATAC_DATA_FILE")
    if args.database.lower() in PROTECTED:
        p.error(f"refusing to drop protected database '{args.database}'")

    path = Path(args.file).expanduser()
    df = pd.read_excel(path, sheet_name=0, dtype=object)
    needed = set(FLIGHT_MAP.values()) | set(AIRCRAFT_MAP) | {GATE, RUNWAY, TAXIWAY} | {src for _, src, _, _ in EVENT_MAP}
    missing = sorted(needed - set(df.columns))
    if missing:
        sys.exit(f"Missing expected columns: {missing}")
    rows = [{c: clean(v) for c, v in r.items()} for r in df.to_dict("records")]
    ddl = old_table_ddl()

    conn = pymysql.connect(**db_settings(args.env_file))
    report = Counter()
    try:
        with conn.cursor() as cur:
            cur.execute(f"DROP DATABASE IF EXISTS {quote(args.database)}")
            cur.execute(f"CREATE DATABASE {quote(args.database)} CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
            cur.execute(f"USE {quote(args.database)}")
            for name in ("aircraft_type", "flight", "flight_event"):
                cur.execute(ddl[name])

            # aircraft_type: distinct attribute combinations, first one wins except weight_class (db_manager.py)
            seen = set()
            for r in rows:
                combo = tuple(r[c] for c in AIRCRAFT_MAP)
                if combo in seen or combo[0] is None:
                    continue
                seen.add(combo)
                cur.execute("INSERT INTO aircraft_type VALUES (%s,%s,%s,%s,%s) "
                            "ON DUPLICATE KEY UPDATE weight_class=VALUES(weight_class)", combo)

            # flight: one row per Excel row
            cols = list(FLIGHT_MAP)
            for r in rows:
                values = {c: r[src] for c, src in FLIGHT_MAP.items()}
                values["operation"] = clean_operation(values["operation"])
                values["flight_number"] = None if values["flight_number"] is None else str(values["flight_number"])
                values["flight_origination_date"] = as_date(values["flight_origination_date"])
                if values["operation"] is None:
                    report[f"flight rows with operation NULL (was '{r['Operation']}')"] += 1
                cur.execute(f"INSERT INTO flight ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))})",
                            [values[c] for c in cols])

            # fix-nulls (INSTALL.md step 4): group missing types by the first Excel row of each call sign
            cur.execute("SELECT DISTINCT call_sign FROM flight WHERE aircraft_type IS NULL")
            null_call_signs = [x[0] for x in cur.fetchall()]
            first_row = {}
            for r in rows:
                first_row.setdefault(r["Call Sign"], r)
            unknowns = {}
            for cs in null_call_signs:
                r = first_row[cs]
                props = (r["Weight Class (ICAO)"], r["Wake Category (Aerobahn)"], span(r["Wingspan (feet)"]), span(r["Wingspan (meters)"]))
                if props not in unknowns:
                    unknowns[props] = f"UNKNOWN_{len(unknowns) + 1:03d}"
                    cur.execute("INSERT INTO aircraft_type VALUES (%s,%s,%s,%s,%s)", (unknowns[props],) + props)
                cur.execute("UPDATE flight SET aircraft_type = %s WHERE call_sign = %s AND aircraft_type IS NULL",
                            (unknowns[props], cs))

            # flight_event: one row per non-empty time column, arrivals and departures only
            event_rows = []
            for r in rows:
                op = clean_operation(r["Operation"])
                if op is None:
                    continue
                for event_type, src, source, loc_col in EVENT_MAP:
                    if r[src] is not None:
                        event_rows.append((r["Call Sign"], op, event_type, r[src], source, r[loc_col]))
                        report[f"events {event_type}"] += 1
            cur.executemany("INSERT INTO flight_event (call_sign, operation, event_type, event_time, event_source, location) "
                            "VALUES (%s,%s,%s,%s,%s,%s)", event_rows)

            counts = {}
            for t in ("aircraft_type", "flight", "flight_event"):
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                counts[t] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM flight WHERE aircraft_type LIKE 'UNKNOWN%'")
            unknown_legs = cur.fetchone()[0]
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print(f"Built `{args.database}` in Team 6's layout from {path.name}")
    print(f"  aircraft_type {counts['aircraft_type']} | flight {counts['flight']} | flight_event {counts['flight_event']}")
    print(f"  UNKNOWN_### types created: {len(unknowns)}, covering {unknown_legs} flight rows "
          f"(Aircraft Type (AODB) was empty for {sum(r['Aircraft Type (AODB)'] is None for r in rows)} rows)")
    for k, v in sorted(report.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
