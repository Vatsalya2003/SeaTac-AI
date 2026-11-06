"""
Helper for test_legacy_unchanged.py (not a test itself). Records what legacy mode does, using one copy of
app_optimized.py, with a fake AI client (no API calls). Writes the result as JSON.

Usage: python legacy_snapshot.py <dir containing app_optimized.py> <output.json>
"""
import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
src_dir, out_file = sys.argv[1], sys.argv[2]

load_dotenv(BACKEND_DIR / ".env")  # same settings for both copies; variables already set are kept
os.environ.pop("QUERY_MODE", None)
os.environ["GEMINI_API_KEY"] = ""
os.environ["CLAUDE_API_KEY"] = ""
sys.path.insert(0, src_dir)
sys.path.insert(1, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)
import app_optimized as app  # noqa: E402

assert Path(app.__file__).resolve().parent == Path(src_dir).resolve(), "imported the wrong copy"

QUESTIONS = ["hi", "hello there", "flights this morning", "Can you show taxi-in by aircraft type?", "thanks",
             "what can you do", "average taxi-in time by aircraft type", "taxi-out by hour", "top 5 aircraft types",
             "between 2 and 4pm departures", "how many departures in the morning", "rush hour taxi out",
             "what was the busiest hour at 3pm", "help me", "explain taxi time", "which runway",
             "show me a chart of taxi-out by hour", "list flights"]
SQLS = ["SELECT HOUR(offblock.event_time) h, COUNT(*) c FROM flight f JOIN flight_event offblock "
        "ON f.call_sign = offblock.call_sign AND offblock.event_type = 'offblock' "
        "WHERE f.operation = 'DEPARTURE' GROUP BY h",
        "SELECT COUNT(*) AS n FROM flight WHERE operation = 'ARRIVAL'",
        "SELECT * FROM flight_event fe WHERE fe.event_type = 'landing' LIMIT 5"]
VOLATILE = {"timestamp", "execution_time", "execution_time_ms", "processing_time", "elapsed"}


class FakeClient:
    """Records the prompts and returns canned text, in the shape of the Anthropic client."""
    def __init__(self, reply):
        self.reply, self.prompts = reply, []

    def _create(self, **kw):
        self.prompts.append(kw)
        return SimpleNamespace(content=[SimpleNamespace(text=self.reply)])

    @property
    def messages(self):
        return SimpleNamespace(create=self._create)


class FakeGenerator:
    def __init__(self, sql):
        self.sql = sql

    async def generate_sql(self, query):
        return self.sql


def scrub(value):
    if isinstance(value, dict):
        return {k: scrub(v) for k, v in value.items() if k not in VOLATILE}
    if isinstance(value, list):
        return [scrub(v) for v in value]
    return value


snap = {}
greeter = app.GreetingHandler(None)
snap["greeting"] = {q: greeter.is_greeting_or_casual(q) for q in QUESTIONS}
snap["greeting_fallback"] = {q: greeter._fallback_response(q) for q in QUESTIONS}
temporal = app.TemporalContextExtractor()
snap["temporal"] = {q: [temporal.inject_temporal_filter(s, q) for s in SQLS] for q in QUESTIONS}
snap["fix_sql"] = [app.fix_common_sql_errors(s) for s in SQLS]
snap["schema"] = app.DETAILED_SCHEMA
db = app.DatabaseManager()
snap["db_config"] = hashlib.sha256(json.dumps(db.db_config, sort_keys=True).encode()).hexdigest()
fake = FakeClient("```sql\nSELECT COUNT(*) AS n FROM flight;\n```")
generator = app.DirectClaudeSQLGenerator(fake)
snap["generator"] = [asyncio.run(generator.generate_sql(q)) for q in QUESTIONS[:5]]
snap["generator_prompts"] = [p["messages"][0]["content"] for p in fake.prompts]
snap["generator_params"] = [{k: v for k, v in p.items() if k != "messages"} for p in fake.prompts]
snap["prebuilt"] = {q: app.SeaTacAgent(None, None, db)._get_prebuilt_sql(q) for q in QUESTIONS}
runs = {}
for i, sql in enumerate(SQLS + [None]):
    for q in QUESTIONS[6:12]:
        runs[f"{i}|{q}"] = asyncio.run(app.SeaTacAgent(FakeGenerator(sql), None, db).process_query(q))
snap["process_query"] = runs
snap["health"] = asyncio.run(app.health_check()).model_dump()
snap["root"] = asyncio.run(app.root())
snap["successful_runs"] = sum(1 for r in runs.values() if r.get("success"))

with open(out_file, "w") as f:
    json.dump(scrub(snap), f, default=str, sort_keys=True, indent=1)
