"""
Legacy mode (QUERY_MODE unset) must behave exactly as before views mode was added.

legacy_snapshot.py records greeting detection, hour-filter injection, SQL fixes, the schema prompt, the
database settings, the SQL generator's prompts (fake AI client), prebuilt SQL, full process_query runs against
the legacy database, /health and /. It runs twice, in separate processes: once with app_optimized.py from the
commit before views mode was added, once with the current file. The two snapshots must be identical.
No AI API is called. Set LEGACY_BASE to compare against a different commit.
"""
import json
import os
import subprocess
import sys

import pytest

from conftest import BACKEND_DIR, REPO_ROOT

APP_PATH = "src/backend/app_optimized.py"


def git(*args):
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout.strip()


def base_commit():
    if os.getenv("LEGACY_BASE"):
        return os.environ["LEGACY_BASE"]
    try:
        added = git("log", "--diff-filter=A", "--format=%H", "--", "src/backend/views_mode.py").splitlines()
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git history not available")
    if not added:
        pytest.skip("views_mode.py isn't committed yet; set LEGACY_BASE")
    return added[-1] + "^"


def snapshot(src_dir, out_file):
    env = {k: v for k, v in os.environ.items() if k != "QUERY_MODE"}
    proc = subprocess.run([sys.executable, str(BACKEND_DIR / "tests" / "legacy_snapshot.py"), str(src_dir),
                           str(out_file)], cwd=BACKEND_DIR, env=env, capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, f"snapshot failed for {src_dir}:\n{proc.stderr[-2000:]}"
    with open(out_file) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def snapshots(tmp_path_factory, admin_db):
    base_dir = tmp_path_factory.mktemp("legacy_base")
    (base_dir / "app_optimized.py").write_text(git("show", f"{base_commit()}:{APP_PATH}") + "\n")
    tmp = tmp_path_factory.mktemp("snapshots")
    return snapshot(base_dir, tmp / "base.json"), snapshot(BACKEND_DIR, tmp / "current.json")


def test_snapshot_exercised_the_database(snapshots):
    base, _ = snapshots
    assert base["successful_runs"] > 0, "no process_query run succeeded; is the legacy database loaded?"


@pytest.mark.parametrize("part", ["greeting", "greeting_fallback", "temporal", "fix_sql", "schema", "db_config",
                                  "generator", "generator_prompts", "generator_params", "prebuilt",
                                  "process_query", "health", "root", "successful_runs"])
def test_legacy_behaviour_unchanged(snapshots, part):
    base, current = snapshots
    assert part in base and part in current
    if base[part] != current[part]:
        keys = sorted(k for k in set(base[part]) | set(current[part])
                      if base[part].get(k) != current[part].get(k)) if isinstance(base[part], dict) else []
        pytest.fail(f"legacy mode changed in '{part}'" + (f" (keys: {keys[:10]})" if keys else ""))
