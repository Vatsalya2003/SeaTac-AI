"""7. Speed: every view query (SELECT * with all rows fetched) must finish within 500 ms."""
import statistics
import time

import pytest

from conftest import VIEWS, rows

LIMIT_MS = 500
RUNS = 3


@pytest.mark.parametrize("view", VIEWS)
def test_view_query_under_500ms(db, report, view):
    times = []
    for _ in range(RUNS):
        start = time.perf_counter()
        rows(db, f"SELECT * FROM {view}")
        times.append((time.perf_counter() - start) * 1000)
    ms = statistics.median(times)
    report(f"speed {view}: {ms:.0f} ms (median of {RUNS})")
    assert ms <= LIMIT_MS, f"{view} took {ms:.0f} ms (limit {LIMIT_MS} ms)"
