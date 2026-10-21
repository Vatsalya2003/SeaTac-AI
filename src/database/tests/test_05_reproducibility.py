"""5. Reproducibility: two loader runs give identical tables (CHECKSUM TABLE) and identical view output (hash)."""
import hashlib
import subprocess
import sys

from conftest import DATA_FILE, DATABASE, DATABASE_DIR, connect, rows

TABLES = ["raw_flight_details", "flights", "aircraft_types"]


def load():
    subprocess.run([sys.executable, "load_aerobahn.py", "--file", str(DATA_FILE), "--database", DATABASE],
                   cwd=DATABASE_DIR / "scripts", check=True, capture_output=True)


def snapshot():
    conn = connect(database=DATABASE)
    try:
        sums = {t: c for t, c in rows(conn, f"CHECKSUM TABLE {', '.join(TABLES)}")}
        hashes = {}
        for (view,) in rows(conn, "SELECT TABLE_NAME FROM information_schema.VIEWS WHERE TABLE_SCHEMA = DATABASE()"):
            n = rows(conn, "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s",
                     (view,))[0][0]
            ordered = rows(conn, f"SELECT * FROM {view} ORDER BY {', '.join(str(i) for i in range(1, n + 1))}")
            hashes[view] = hashlib.sha256(repr(ordered).encode()).hexdigest()
        return sums, hashes
    finally:
        conn.close()


def test_loader_twice_gives_identical_database(excel, report):  # excel fixture: skips if the file is missing
    load()
    first = snapshot()
    load()
    second = snapshot()
    same_tables = [t for t in first[0] if first[0][t] == second[0].get(t)]
    same_views = [v for v in first[1] if first[1][v] == second[1].get(v)]
    report(f"reproducibility: {len(same_tables)} of {len(first[0])} table checksums identical, "
           f"{len(same_views)} of {len(first[1])} view hashes identical")
    assert first[0] == second[0], f"CHECKSUM TABLE differs for {sorted(set(first[0]) - set(same_tables))}"
    assert first[1] == second[1], f"ordered output differs for {sorted(set(first[1]) - set(same_views))}"
