"""
Shared fixtures for the `seatac` test suite.

Output rule: tests report PASS/FAIL and counts of matches or mismatches only. They never print metric
averages or answers to the Port's questions (the team calculates expected answers by hand, independently).
Failure messages name flight_info_ids, hours or column names, never metric values.

Settings:
    SEATAC_DATA_FILE   the Aerobahn .xlsx export (default: August_8_and_9_2025_Anonymized.xlsx at the repo root)
    src/backend/.env   DB_HOST / DB_PORT / DB_USER / DB_PASSWORD, and SEATAC_READER_PASSWORD for the security tests
"""
import os
import sys
from pathlib import Path

import pandas as pd
import pymysql
import pytest

DATABASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = DATABASE_DIR.parent.parent
sys.path.insert(0, str(DATABASE_DIR / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from load_aerobahn import DEFAULT_ENV_FILE, db_settings  # noqa: E402

import excel_expected  # noqa: E402

DATABASE = "seatac"
DATA_FILE = Path(os.getenv("SEATAC_DATA_FILE") or REPO_ROOT / "August_8_and_9_2025_Anonymized.xlsx").expanduser()
VIEWS = ["v_taxi_in", "v_taxi_out", "v_weight_classes", "v_movement_area", "v_movement_area_hourly_peak",
         "v_runway_occupancy", "v_takeoff_delay", "v_taxiway_usage", "v_runway_activity", "v_peak_hours"]

_report_lines = []
_outcomes = {}


def connect(**overrides):
    settings = db_settings(DEFAULT_ENV_FILE)
    settings.update(autocommit=True, **overrides)
    return pymysql.connect(**settings)


def rows(conn, sql, args=None):
    with conn.cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchall()


@pytest.fixture(scope="module")
def db():
    conn = connect(database=DATABASE)
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def excel():
    if not DATA_FILE.exists():
        pytest.skip(f"Aerobahn export not found ({DATA_FILE.name}); set SEATAC_DATA_FILE")
    return pd.read_excel(DATA_FILE, sheet_name=0, dtype=object)


@pytest.fixture(scope="session")
def expected(excel):
    return excel_expected.build(excel)


@pytest.fixture(scope="session")
def report():
    """report(line): add a line to the summary printed after the run (counts only, never metric values)."""
    return _report_lines.append


def pytest_runtest_logreport(report):
    if report.when == "call" or report.outcome != "passed":
        _outcomes.setdefault(report.nodeid, report.outcome.upper())  # PASSED / FAILED / SKIPPED


def pytest_terminal_summary(terminalreporter):
    if _outcomes:
        terminalreporter.section("PASS/FAIL by test")
        for nodeid, outcome in _outcomes.items():
            terminalreporter.write_line(f"{outcome:<8} {nodeid.removeprefix('tests/')}")
    if _report_lines:
        terminalreporter.section("Counts (no metric values)")
        for line in _report_lines:
            terminalreporter.write_line(line)
