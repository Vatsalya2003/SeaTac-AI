"""9. Privacy: no view exposes aircraft identifiers (Registration, Mode S, ship number, source ID), by name or by value."""
import re

import pytest

from conftest import REPO_ROOT, VIEWS, rows

IDENTIFIER = re.compile(r"registration|mode.?s\b|transponder|ship.?number|source.?id|tail.?number|icao.?24|hex", re.I)


def test_no_identifier_columns_in_views(db, report):
    cols = rows(db, f"""SELECT TABLE_NAME, COLUMN_NAME FROM information_schema.COLUMNS
                        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN ({', '.join(['%s'] * len(VIEWS))})""", VIEWS)
    bad = [f"{t}.{c}" for t, c in cols if IDENTIFIER.search(c)]
    report(f"privacy: {len(cols)} view columns checked, {len(bad)} identifier columns")
    assert not bad, f"identifier columns exposed: {bad}"


def test_no_identifier_values_in_views(db, excel, report):
    id_cols = [c for c in excel.columns if IDENTIFIER.search(c)]
    real = {str(v).strip() for c in id_cols for v in excel[c].dropna() if len(str(v).strip()) >= 4}
    hits = set()
    for view in VIEWS:
        for r in rows(db, f"SELECT * FROM {view}"):
            hits |= {f"{view}" for v in r if isinstance(v, str) and v.strip() in real}
    report(f"privacy: {len(real)} identifier values from {len(id_cols)} Excel columns, found in {len(hits)} views")
    assert not hits, f"identifier values exposed in {sorted(hits)}"


def test_schema_file_has_no_data():
    schema = REPO_ROOT / "docs" / "seatac_schema.sql"
    if not schema.exists():
        pytest.skip("docs/seatac_schema.sql not generated yet")
    text = schema.read_text(encoding="utf-8")
    assert not re.search(r"^\s*INSERT\s", text, re.I | re.M), "docs/seatac_schema.sql contains INSERT statements"
    assert "CREATE TABLE `flights`" in text, "docs/seatac_schema.sql is not the seatac schema"
