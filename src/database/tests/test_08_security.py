"""
8. Security: the read-only user seatac_reader (scripts/create_reader.py) can read every view and nothing else.

Its password is read from SEATAC_READER_PASSWORD (environment or src/backend/.env), never hard-coded.
Write probes are aimed at a table name that doesn't exist or match no rows, so they change nothing even if allowed.
"""
import subprocess

import pymysql
import pytest

from conftest import DATABASE, REPO_ROOT, VIEWS, connect, rows
from create_reader import READER_USER, create_reader, reader_password
from load_aerobahn import DEFAULT_ENV_FILE

DENIED = {1142, 1044, 1045}  # command denied, database access denied, login denied


@pytest.fixture(scope="module")
def reader():
    if not reader_password(DEFAULT_ENV_FILE):
        pytest.fail("add SEATAC_READER_PASSWORD to src/backend/.env (or the environment)")
    create_reader(DEFAULT_ENV_FILE, DATABASE)
    conn = connect(user=READER_USER, password=reader_password(DEFAULT_ENV_FILE), database=DATABASE)
    yield conn
    conn.close()


def denied(conn, sql):
    try:
        rows(conn, sql)
    except pymysql.err.MySQLError as e:
        return e.args[0] in DENIED
    return False


def test_grants_are_select_on_views_only(reader):
    grants = [g[0] for g in rows(reader, "SHOW GRANTS")]
    other = [g for g in grants if not g.startswith("GRANT USAGE ON *.*")
             and not any(g.startswith(f"GRANT SELECT ON `{DATABASE}`.`{v}` TO") for v in VIEWS)]
    assert not other, f"{len(other)} grants beyond SELECT on the views"
    assert len(grants) == len(VIEWS) + 1, "missing SELECT on some view"


@pytest.mark.parametrize("view", VIEWS)
def test_reader_can_read_view(reader, view):
    rows(reader, f"SELECT * FROM {view} LIMIT 1")


@pytest.mark.parametrize("table", ["raw_flight_details", "flights", "aircraft_types"])
def test_reader_cannot_read_table(reader, table):
    assert denied(reader, f"SELECT 1 FROM {table} LIMIT 1"), f"reader can read {table}"


@pytest.mark.parametrize("sql", [
    "INSERT INTO flights (flight_info_id) SELECT 1 FROM DUAL WHERE 1 = 0",
    "UPDATE flights SET call_sign = call_sign WHERE 1 = 0",
    "DELETE FROM flights WHERE 1 = 0",
    "DELETE FROM v_taxi_in WHERE 1 = 0",
    "UPDATE v_taxi_in SET call_sign = call_sign WHERE 1 = 0",
    "DROP TABLE zz_reader_probe",
    "DROP VIEW zz_reader_probe",
    "CREATE TABLE zz_reader_probe (x INT)",
], ids=["insert", "update", "delete", "delete_view", "update_view", "drop_table", "drop_view", "create"])
def test_reader_cannot_write(reader, sql):
    assert denied(reader, sql), "write command was not denied"


def test_reader_cannot_see_aiplane(reader):
    visible = {r[0].lower() for r in rows(reader, "SHOW DATABASES")}
    assert not visible & {"aiplane", "aiplane_v2"}, "AIplane is visible to the reader"
    assert denied(reader, "SELECT 1 FROM AIplane.flight LIMIT 1"), "reader can read AIplane"


def test_reader_password_not_hard_coded():
    """No file git would commit (tracked or untracked, .gitignore respected) contains the reader password."""
    password = reader_password(DEFAULT_ENV_FILE)
    if not password:
        pytest.fail("add SEATAC_READER_PASSWORD to src/backend/.env (or the environment)")
    files = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=REPO_ROOT,
                           capture_output=True, text=True, check=True).stdout.split("\0")
    leaks = [f for f in files if f and (REPO_ROOT / f).is_file()
             and password in (REPO_ROOT / f).read_text(encoding="utf-8", errors="ignore")]
    assert not leaks, f"reader password found in {leaks}"
