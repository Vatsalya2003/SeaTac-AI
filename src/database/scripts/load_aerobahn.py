"""
Load the Port of Seattle Aerobahn flight-details export into the `seatac` MySQL database.

Rerunnable: drops and rebuilds the target database every time.

Usage:
    python load_aerobahn.py --file /path/to/August_8_and_9_2025_Anonymized.xlsx
    SEATAC_DATA_FILE=/path/to/file.xlsx python load_aerobahn.py

Connection settings come from DB_HOST / DB_PORT / DB_USER / DB_PASSWORD (environment variables),
falling back to an env file (default: src/backend/.env).

The Port data is private: never commit the Excel file or a dump of this database.
"""
import argparse
import datetime as dt
import os
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import pymysql
from dotenv import dotenv_values

DATABASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ENV_FILE = DATABASE_DIR.parent / "backend" / ".env"
VIEWS_SQL = DATABASE_DIR / "sql" / "seatac_views.sql"
PROTECTED_DATABASES = {"aiplane", "aiplane_v2", "mysql", "sys", "information_schema", "performance_schema"}
BATCH_SIZE = 500

# Original Excel columns that become the primary key. MySQL column names are case-insensitive,
# so `Operation` and `operation` can't both exist: the originals are renamed, not duplicated.
PK_RENAMES = {"Flight Info ID": "flight_info_id", "Operation": "operation"}

# flights column -> (source Excel column, MySQL type)
FLIGHT_COLUMNS = {
    "call_sign": ("Call Sign", "VARCHAR(20)"),
    "carrier": ("Carrier", "VARCHAR(20)"),
    "carrier_group": ("Carrier Group", "VARCHAR(50)"),
    "aircraft_type": ("Aircraft Type (FAA)", "VARCHAR(20)"),
    "weight_class_icao": ("Weight Class (ICAO)", "CHAR(1)"),
    "origin_airport": ("Origination Airport", "VARCHAR(10)"),
    "destination_airport": ("Destination Airport", "VARCHAR(10)"),
    "international_domestic": ("International or Domestic Indicator", "VARCHAR(20)"),
    "runway": ("Runway", "VARCHAR(10)"),
    "gate": ("Gate Assigned (Aerobahn)", "VARCHAR(30)"),
    "parking_area": ("Parking Area", "VARCHAR(50)"),
    "taxiway_runway": ("Taxiway Used to Enter/Exit Runway", "VARCHAR(50)"),
    "taxiway_ramp": ("Taxiway Used to Enter/Exit Ramp", "VARCHAR(50)"),
    "scheduled_off_block": ("Scheduled Off Block Time (Aerobahn) (PDT)", "DATETIME"),
    "actual_off_block": ("Actual Off Block Time (Aerobahn) (PDT)", "DATETIME"),
    "scheduled_take_off": ("Scheduled Take Off Time (Aerobahn) (PDT)", "DATETIME"),
    "wheels_up": ("Wheels Up (PDT)", "DATETIME"),
    "scheduled_landing": ("Scheduled Landing Time (Aerobahn) (PDT)", "DATETIME"),
    "wheels_down": ("Wheels Down (PDT)", "DATETIME"),
    "scheduled_in_block": ("Scheduled In Block Time (Aerobahn) (PDT)", "DATETIME"),
    "actual_in_block": ("Actual In Block Time (Aerobahn) (PDT)", "DATETIME"),
    "runway_entrance": ("Runway Entrance Time (PDT)", "DATETIME"),
    "runway_exit": ("Runway Exit Time (PDT)", "DATETIME"),
    "movement_area_entrance": ("Movement Area Entrance Time (PDT)", "DATETIME"),
    "movement_area_exit": ("Movement Area Exit Time (PDT)", "DATETIME"),
    "sea_event_time": ("Event Time (PDT)", "DATETIME"),
    "passenger_count": ("Passenger Count (AODB)", "INT"),
}
# flights holds SEA-side times only: these columns describe the OTHER airport for that operation and are
# set to NULL in flights (the original values stay in raw_flight_details). A missed approach is an inbound
# flight, so it follows the arrival rule.
OTHER_AIRPORT_COLUMNS = {
    "Arrival": ["scheduled_off_block", "actual_off_block", "scheduled_take_off", "wheels_up"],
    "Missed Approach": ["scheduled_off_block", "actual_off_block", "scheduled_take_off", "wheels_up"],
    "Departure": ["scheduled_landing", "wheels_down", "scheduled_in_block", "actual_in_block"],
}
# system-computed durations (h:mm:ss in the export) -> seconds
SYS_DURATIONS = {
    "sys_taxi_in_sec": "Actual Taxi In Time",
    "sys_taxi_out_sec": "Actual Taxi Out Time",
    "sys_runway_occupancy_sec": "Runway Occupancy Time",
}
# aircraft_types column -> (source Excel column, MySQL type)
AIRCRAFT_COLUMNS = {
    "engine_class": ("Engine Class", "VARCHAR(20)"),
    "wake_category": ("Wake Category (Aerobahn)", "VARCHAR(10)"),
    "design_group": ("Design Group (FAA)", "VARCHAR(10)"),
    "wingspan_ft": ("Wingspan (feet)", "DECIMAL(8,2)"),
    "fuselage_ft": ("Fuselage (feet)", "DECIMAL(8,2)"),
    "max_takeoff_weight_kg": ("Maximum Takeoff Weight (kg)", "INT"),
    "max_landing_weight_kg": ("Maximum Landing Weight (kg)", "INT"),
}


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--file", default=os.getenv("SEATAC_DATA_FILE"), help="Aerobahn .xlsx export (or SEATAC_DATA_FILE)")
    p.add_argument("--database", default="seatac", help="target database (dropped and rebuilt)")
    p.add_argument("--env-file", default=str(DEFAULT_ENV_FILE), help="file with DB_HOST/DB_PORT/DB_USER/DB_PASSWORD")
    p.add_argument("--skip-views", action="store_true", help="build tables only")
    args = p.parse_args()
    if not args.file:
        p.error("give --file or set SEATAC_DATA_FILE")
    if args.database.lower() in PROTECTED_DATABASES:
        p.error(f"refusing to drop protected database '{args.database}'")
    return args


def db_settings(env_file):
    file_values = dotenv_values(env_file) if env_file and Path(env_file).exists() else {}
    get = lambda k, default=None: os.getenv(k) or file_values.get(k) or default
    return {
        "host": get("DB_HOST", "localhost"),
        "port": int(get("DB_PORT", 3306)),
        "user": get("DB_USER", "root"),
        "password": get("DB_PASSWORD", ""),
        "charset": "utf8mb4",
        "autocommit": False,
    }


def to_seconds(value):
    if value is None:
        return None
    if isinstance(value, dt.time):
        return value.hour * 3600 + value.minute * 60 + value.second
    if isinstance(value, dt.timedelta):
        return int(value.total_seconds())
    text = str(value).strip()
    sign = -1 if text.startswith("-") else 1
    h, m, s = (int(float(x)) for x in text.lstrip("-").split(":"))
    return sign * (h * 3600 + m * 60 + s)


def clean(value):
    """Excel cell -> value PyMySQL can bind (NaN -> None, numpy scalars -> Python)."""
    if value is None or (isinstance(value, float) and pd.isna(value)) or value is pd.NaT:
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        return value.item()
    return value


def raw_column_type(series):
    kinds = set(series.dropna().map(lambda v: type(v).__name__))
    if kinds == {"datetime"} or kinds == {"Timestamp"}:
        return "DATETIME"
    if kinds == {"time"}:
        return "TIME"
    if kinds == {"bool"}:
        return "TINYINT(1)"
    if kinds == {"int"}:
        return "BIGINT"
    if kinds and kinds <= {"int", "float"}:
        return "DOUBLE"
    return "TEXT"  # strings and mixed columns (e.g. negative delays exported as text)


def raw_value(value, sql_type):
    value = clean(value)
    if value is None:
        return None
    if sql_type == "TEXT" and isinstance(value, dt.time):
        return value.strftime("%H:%M:%S")
    if sql_type == "TEXT":
        return str(value)
    if sql_type == "TINYINT(1)":
        return int(bool(value))
    return value


def quote(name):
    return "`" + name.replace("`", "``") + "`"


def insert_rows(cursor, table, columns, rows):
    sql = f"INSERT INTO {quote(table)} ({', '.join(map(quote, columns))}) VALUES ({', '.join(['%s'] * len(columns))})"
    for start in range(0, len(rows), BATCH_SIZE):
        cursor.executemany(sql, rows[start:start + BATCH_SIZE])


def most_common(values):
    counts = Counter(v for v in values if v is not None)
    return (counts.most_common(1)[0][0], counts) if counts else (None, counts)


def main():
    args = parse_args()
    path = Path(args.file).expanduser()
    if not path.exists():
        sys.exit(f"Data file not found: {path}")

    print(f"Reading {path.name} ...")
    df = pd.read_excel(path, sheet_name=0, dtype=object)
    required = set(PK_RENAMES) | {src for src, _ in FLIGHT_COLUMNS.values()} | set(SYS_DURATIONS.values()) | \
        {src for src, _ in AIRCRAFT_COLUMNS.values()}
    missing = sorted(required - set(df.columns))
    if missing:
        sys.exit(f"Missing expected columns: {missing}")
    if df.duplicated(list(PK_RENAMES)).any():
        sys.exit("Flight Info ID + Operation is not unique in the file")
    print(f"  {len(df)} rows x {df.shape[1]} columns")

    # ---- raw layer: every column with at least one value
    raw_cols = [c for c in df.columns if df[c].notna().any() and c not in PK_RENAMES]
    raw_types = {c: raw_column_type(df[c]) for c in raw_cols}
    print(f"  raw_flight_details: {len(raw_cols) + 2} columns ({df.shape[1] - len(raw_cols) - 2} empty columns skipped)")

    # ---- aircraft types: most common value per attribute
    aircraft_rows, conflicts = [], []
    typed = df[df["Aircraft Type (FAA)"].notna()]
    for ac_type, group in typed.groupby("Aircraft Type (FAA)", sort=True):
        row = [ac_type]
        for col, (src, _) in AIRCRAFT_COLUMNS.items():
            value, counts = most_common(clean(v) for v in group[src])
            if len(counts) > 1:
                conflicts.append(f"{ac_type}.{col}: {dict(counts)} -> used {value!r}")
            row.append(value)
        aircraft_rows.append(row)

    # ---- flights
    flight_cols = ["flight_info_id", "operation"] + list(FLIGHT_COLUMNS) + ["sea_date"] + list(SYS_DURATIONS) + ["source_file"]
    flight_rows, nulled = [], Counter()
    for _, r in df.iterrows():
        operation = clean(r["Operation"])
        values = {col: clean(r[src]) for col, (src, _) in FLIGHT_COLUMNS.items()}
        for col in OTHER_AIRPORT_COLUMNS.get(operation, []):
            if values[col] is not None:
                nulled[(operation, col)] += 1
            values[col] = None
        event_time = values["sea_event_time"]
        flight_rows.append(
            [clean(r["Flight Info ID"]), operation]
            + [values[col] for col in FLIGHT_COLUMNS]
            + [event_time.date() if event_time else None]
            + [to_seconds(clean(r[src])) for src in SYS_DURATIONS.values()]
            + [path.name]
        )
    raw_rows = [[clean(r["Flight Info ID"]), clean(r["Operation"])] + [raw_value(r[c], raw_types[c]) for c in raw_cols]
                for _, r in df.iterrows()]

    # ---- write
    settings = db_settings(args.env_file)
    db = args.database
    conn = pymysql.connect(**settings)
    try:
        with conn.cursor() as cur:
            cur.execute(f"DROP DATABASE IF EXISTS {quote(db)}")
            cur.execute(f"CREATE DATABASE {quote(db)} CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
            cur.execute(f"USE {quote(db)}")

            raw_ddl = ",\n  ".join([f"{quote('flight_info_id')} BIGINT NOT NULL", f"{quote('operation')} VARCHAR(20) NOT NULL"]
                                   + [f"{quote(c)} {raw_types[c]} NULL" for c in raw_cols])
            cur.execute(f"CREATE TABLE raw_flight_details (\n  {raw_ddl},\n  PRIMARY KEY (flight_info_id, operation)\n)"
                        " ENGINE=InnoDB ROW_FORMAT=DYNAMIC COMMENT='Every non-empty column of the Aerobahn export, original names'")

            ac_ddl = ",\n  ".join(["aircraft_type VARCHAR(20) NOT NULL"] + [f"{c} {t} NULL" for c, (_, t) in AIRCRAFT_COLUMNS.items()])
            cur.execute(f"CREATE TABLE aircraft_types (\n  {ac_ddl},\n  PRIMARY KEY (aircraft_type)\n) ENGINE=InnoDB"
                        " COMMENT='One row per FAA aircraft type; most common attribute value when the export disagrees'")

            fl_ddl = ",\n  ".join(
                ["flight_info_id BIGINT NOT NULL", "operation VARCHAR(20) NOT NULL"]
                + [f"{c} {t} NULL" for c, (_, t) in FLIGHT_COLUMNS.items()]
                + ["sea_date DATE NULL"] + [f"{c} INT NULL" for c in SYS_DURATIONS] + ["source_file VARCHAR(255) NOT NULL"])
            cur.execute(
                f"CREATE TABLE flights (\n  {fl_ddl},\n  PRIMARY KEY (flight_info_id, operation),\n"
                "  KEY idx_flights_aircraft_type (aircraft_type),\n  KEY idx_flights_sea_date (sea_date),\n"
                "  CONSTRAINT fk_flights_aircraft_type FOREIGN KEY (aircraft_type) REFERENCES aircraft_types (aircraft_type)\n"
                ") ENGINE=InnoDB COMMENT='One row per flight leg at SEA. SEA-side times only (other-airport times are NULL; "
                "originals in raw_flight_details). Local PDT, not shifted'")

            insert_rows(cur, "raw_flight_details", ["flight_info_id", "operation"] + raw_cols, raw_rows)
            insert_rows(cur, "aircraft_types", ["aircraft_type"] + list(AIRCRAFT_COLUMNS), aircraft_rows)
            insert_rows(cur, "flights", flight_cols, flight_rows)

            if not args.skip_views:
                statements = [s.strip() for s in VIEWS_SQL.read_text(encoding="utf-8").split(";\n") if s.strip()]
                for statement in statements:
                    if any(line.strip() and not line.strip().startswith("--") for line in statement.splitlines()):
                        cur.execute(statement)
                print(f"  views: {len(statements)} statements from {VIEWS_SQL.name}")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print(f"Loaded into `{db}`: raw_flight_details {len(raw_rows)}, flights {len(flight_rows)}, aircraft_types {len(aircraft_rows)}")
    print("Other-airport times set to NULL in flights (SEA-side only; originals kept in raw_flight_details):")
    for (operation, col), n in sorted(nulled.items()):
        print(f"  {operation:<15} {col:<20} {n}")
    print(f"Aircraft types with conflicting attribute values: {len(conflicts)}")
    for line in conflicts:
        print("  " + line)


if __name__ == "__main__":
    main()
