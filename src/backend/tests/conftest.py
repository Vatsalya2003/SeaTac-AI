"""
Shared fixtures for the backend tests (run from src/backend: pytest -q).

These tests never call an AI API: the SQL generator is replaced by a fake that returns hand-written SQL,
and the AI keys are blanked before app_optimized is imported.

Output rule (same as src/database/tests): tests report PASS/FAIL and counts only. They never print metric
averages or answers to the Port's questions, and failure messages don't include metric values.

Needs: MySQL running with the `seatac` database loaded (src/database/scripts/load_aerobahn.py), the
read-only user (src/database/scripts/create_reader.py), and src/backend/.env with DB_* and
SEATAC_READER_PASSWORD.
"""
import os
from pathlib import Path

import mysql.connector
import pytest
from dotenv import dotenv_values

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent.parent
ENV_FILE = BACKEND_DIR / ".env"


def env_settings():
    """Values from src/backend/.env, with the process environment taking priority."""
    values = dotenv_values(ENV_FILE) if ENV_FILE.exists() else {}
    return {k: os.environ.get(k, v) for k, v in values.items()}


def admin_connect(database="seatac"):
    """The .env DB user (not the read-only user), for independent checks the tests compare against."""
    s = env_settings()
    return mysql.connector.connect(host=s.get("DB_HOST", "localhost"), port=int(s.get("DB_PORT") or 3306),
                                   user=s.get("DB_USER", "root"), password=s.get("DB_PASSWORD", ""),
                                   database=database)


@pytest.fixture(scope="session")
def admin_db():
    try:
        conn = admin_connect()
    except mysql.connector.Error as e:
        pytest.skip(f"MySQL / seatac database not available ({e.errno})")
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def admin_fetch(admin_db):
    def fetch(sql, args=None):
        cur = admin_db.cursor(dictionary=True)
        try:
            cur.execute(sql, args)
            return cur.fetchall()
        finally:
            cur.close()
    return fetch
