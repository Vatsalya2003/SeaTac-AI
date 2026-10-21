"""6. Determinism: each view query run twice returns identical rows in the same order."""
import pytest

from conftest import VIEWS, rows


def test_view_list_is_complete(db):
    assert sorted(VIEWS) == sorted(r[0] for r in rows(db, "SELECT TABLE_NAME FROM information_schema.VIEWS WHERE TABLE_SCHEMA = DATABASE()"))


@pytest.mark.parametrize("view", VIEWS)
def test_view_query_is_deterministic(db, view):
    first = rows(db, f"SELECT * FROM {view}")
    second = rows(db, f"SELECT * FROM {view}")
    assert first == second, f"{view} returned different rows or a different order"
