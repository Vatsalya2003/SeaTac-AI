"""
Create (or reset) the read-only MySQL user `seatac_reader`, with SELECT on the `seatac` views only.

No access to the tables (raw_flight_details, flights, aircraft_types) or to any other database.
Rerunnable: revokes everything first, then grants SELECT on each view that exists now.
Run it again after adding a view.

Usage:
    python create_reader.py [--database seatac] [--env-file ../../backend/.env]

The password comes from SEATAC_READER_PASSWORD (environment variable, else the env file). It is never printed.
The admin connection uses DB_HOST / DB_PORT / DB_USER / DB_PASSWORD, like load_aerobahn.py.
"""
import argparse
import os
import sys
from pathlib import Path

import pymysql
from dotenv import dotenv_values

from load_aerobahn import DEFAULT_ENV_FILE, db_settings, quote

READER_USER = "seatac_reader"
READER_HOST = "localhost"


def reader_password(env_file):
    file_values = dotenv_values(env_file) if env_file and Path(env_file).exists() else {}
    return os.getenv("SEATAC_READER_PASSWORD") or file_values.get("SEATAC_READER_PASSWORD")


def create_reader(env_file=DEFAULT_ENV_FILE, database="seatac"):
    """Create/reset the reader and return the list of views it can read."""
    password = reader_password(env_file)
    if not password:
        raise RuntimeError(f"SEATAC_READER_PASSWORD is not set (environment or {env_file})")
    conn = pymysql.connect(**db_settings(env_file), database=database)
    try:
        with conn.cursor() as cur:
            account = "%s@%s"
            cur.execute(f"CREATE USER IF NOT EXISTS {account} IDENTIFIED BY %s", (READER_USER, READER_HOST, password))
            cur.execute(f"ALTER USER {account} IDENTIFIED BY %s", (READER_USER, READER_HOST, password))
            cur.execute(f"REVOKE ALL PRIVILEGES, GRANT OPTION FROM {account}", (READER_USER, READER_HOST))
            cur.execute("SELECT TABLE_NAME FROM information_schema.VIEWS WHERE TABLE_SCHEMA = %s ORDER BY TABLE_NAME",
                        (database,))
            views = [r[0] for r in cur.fetchall()]
            for view in views:
                cur.execute(f"GRANT SELECT ON {quote(database)}.{quote(view)} TO {account}", (READER_USER, READER_HOST))
        conn.commit()
    finally:
        conn.close()
    return views


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--database", default="seatac")
    p.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    args = p.parse_args()
    try:
        views = create_reader(args.env_file, args.database)
    except RuntimeError as e:
        sys.exit(str(e))
    print(f"{READER_USER}@{READER_HOST}: SELECT on {len(views)} views in `{args.database}`, nothing else")


if __name__ == "__main__":
    main()
