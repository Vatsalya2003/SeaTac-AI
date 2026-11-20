"""
QUERY_MODE=templates (stage 2), without an AI API.

The tested SQL for each of the Port's 10 questions runs on the real `seatac` database as the read-only user,
and the results are compared with the team's hand-calculated ground truth (TEN_GROUND_TRUTH_ANSWERS.md,
reporting day 2025-08-08). The AI's only job in this mode, picking the question, is replaced by fake replies.
Failure messages name the check, not the metric values (output rule in conftest.py).
"""
import asyncio
import importlib
import os
import sys
from decimal import Decimal, ROUND_HALF_UP
from types import SimpleNamespace

import pytest

from conftest import BACKEND_DIR


@pytest.fixture(scope="module")
def app(admin_db):
    old = os.environ.get("QUERY_MODE")
    os.environ["QUERY_MODE"] = "templates"
    os.environ["GEMINI_API_KEY"] = ""   # no AI client is created
    os.environ["CLAUDE_API_KEY"] = ""
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    module = sys.modules.get("app_optimized")
    module = importlib.reload(module) if module else importlib.import_module("app_optimized")
    assert module.TEMPLATES_MODE and module.VIEWS_MODE
    if not module.db_manager.test_connection():
        pytest.skip("read-only user seatac_reader can't connect (run src/database/scripts/create_reader.py)")
    yield module
    if old is None:
        os.environ.pop("QUERY_MODE", None)
    else:
        os.environ["QUERY_MODE"] = old


@pytest.fixture(scope="module")
def tpl(app):
    return sys.modules["templates"]


@pytest.fixture(scope="module")
def intent_mod(app):
    return sys.modules["intent"]


@pytest.fixture(scope="module")
def ans(app, tpl):
    cache = {}

    def get(qid):
        if qid not in cache:
            cache[qid] = tpl.answer(qid, app.db_manager.fetch)
        return cache[qid]
    return get


def r2(v):
    return None if v is None else float(Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def by(rows, key):
    return {r[key]: r for r in rows}


class FakeIntentClient:
    """Stands in for the LLM client: returns a fixed reply, or raises, and records the prompts."""
    def __init__(self, reply=None, error=None):
        self.reply, self.error, self.prompts = reply, error, []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        self.prompts.append(kw["messages"][0]["content"])
        if self.error:
            raise self.error
        return SimpleNamespace(content=[SimpleNamespace(text=self.reply)])


class FakeGenerator:
    """Stage 1 SQL generator stand-in for the fallback path."""
    def __init__(self, sql):
        self.sql = sql

    async def generate_sql(self, query):
        return self.sql


# ---- ground truth ---------------------------------------------------------------------------------------------

def test_q1_taxi_in_by_aircraft_type(ans):
    a = ans("Q1")
    rows = by(a["data"], "aircraft_type_group")
    assert len(rows) == 16, "Q1 should have 16 aircraft-type groups"
    assert sum(r["flights"] for r in rows.values()) == 525 and a["included_count"] == 525, "Q1 sample size"
    expected = {"B738": (14.53, 81), "B737": (14.20, 9), "B752": (16.63, 1), "A359": (7.29, 3), "Unknown": (99.00, 1),
                "E75L": (10.43, 170), "B739": (13.19, 108), "B39M": (12.36, 87), "BCS1": (9.42, 13), "A339": (9.42, 5)}
    for t, want in expected.items():
        assert (r2(rows[t]["avg_taxi_in_min"]), rows[t]["flights"]) == want, f"Q1 group {t}"
    assert a["data"][0]["aircraft_type_group"] == "Unknown" and a["data"][-1]["aircraft_type_group"] == "A359", "Q1 order"


def test_q2_taxi_out_by_hour(ans, app, tpl):
    a = ans("Q2")
    rows = by(a["data"], "off_block_hour")
    assert sorted(rows) == list(range(24)), "Q2 should list all 24 hours"
    assert rows[3]["avg_taxi_out_min"] is None and rows[4]["avg_taxi_out_min"] is None, "Q2 03/04 must be No data"
    assert (r2(rows[12]["avg_taxi_out_min"]), rows[12]["flights"]) == (22.26, 31), "Q2 longest hour"
    assert r2(rows[6]["avg_taxi_out_min"]) == 11.57, "Q2 06:00"
    assert sum(r["flights"] for r in rows.values()) == 528 and a["included_count"] == 528, "Q2 sample size"
    assert a["excluded"].get("outside the reporting day") == 7, "Q2 Aug-7 off-blocks"
    assert "15.66 min" in a["answer"] and "No data" in a["answer"], "Q2 headline"


def test_q3_movement_area_peak(ans):
    a = ans("Q3")
    gt = [7, 3, 1, 0, 1, 4, 9, 11, 16, 11, 22, 15, 20, 14, 15, 10, 12, 10, 16, 14, 15, 12, 19, 11]
    assert [r["max_aircraft_in_area"] for r in a["data"]] == gt, "Q3 hourly peaks"
    assert a["included_count"] == 1052 and a["excluded"] == {"missing time": 8}, "Q3 intervals used / excluded"
    assert "22 aircraft" in a["answer"] and "520 arrivals" in a["answer"] and "532 departures" in a["answer"], "Q3 text"


def test_q4_runway_occupancy(app, tpl):
    a = tpl.answer("Q4", app.db_manager.fetch)
    runs = {(r["operation"], r["runway"]): (r2(r["avg_occupancy_min"]), r["flights"]) for r in a["data"]}
    assert runs == {("Arrival", "34L"): (0.42, 493), ("Arrival", "34R"): (0.65, 23), ("Arrival", "34C"): (0.55, 1),
                    ("Arrival", "16R"): (0.37, 4), ("Departure", "34R"): (1.29, 512), ("Departure", "34C"): (1.00, 11),
                    ("Departure", "16L"): (0.76, 6), ("Departure", "16C"): (0.61, 3)}, "Q4 by runway"
    ops = by(app.db_manager.fetch(*tpl.build_queries("Q4")[0][1:]), "operation")
    assert (r2(ops["Arrival"]["avg_occupancy_sec"]), ops["Arrival"]["flights"]) == (25.69, 521), "Q4 arrivals"
    assert (float(ops["Departure"]["avg_occupancy_sec"]), ops["Departure"]["flights"]) == (76.5, 532), "Q4 departures"
    assert "0.43 min" in a["answer"] and "76.50 seconds" in a["answer"], "Q4 text"


def test_q5_takeoff_delay(ans):
    a = ans("Q5")
    r = a["data"][0]
    assert round(r["avg_takeoff_delay_min"], 4) == 25.706 and r["flights"] == 533, "Q5 average / sample"
    assert r["early_departures"] == 44, "Q5 early departures must be kept"
    assert a["excluded"] == {"missing scheduled take-off": 2}, "Q5 exclusions"
    assert "25.71 minutes late" in a["answer"], "Q5 text"


def test_q6_weight_class(ans):
    a = ans("Q6")
    rows = by(a["data"], "weight_class")
    assert (r2(rows["Medium"]["avg_taxi_in_min"]), rows["Medium"]["arrivals"]) == (12.25, 517), "Q6 medium taxi-in"
    assert (r2(rows["Heavy"]["avg_taxi_in_min"]), rows["Heavy"]["arrivals"]) == (8.62, 8), "Q6 heavy taxi-in"
    assert (r2(rows["Medium"]["avg_taxi_out_min"]), rows["Medium"]["departures"]) == (15.65, 520), "Q6 medium taxi-out"
    assert (r2(rows["Heavy"]["avg_taxi_out_min"]), rows["Heavy"]["departures"]) == (16.12, 8), "Q6 heavy taxi-out"
    for empty in ("Light", "Super", "Unknown"):
        assert rows[empty]["avg_taxi_in_min"] is None and rows[empty]["avg_taxi_out_min"] is None, f"Q6 {empty} No data"
    assert "No data: Light, Super, Unknown" in a["answer"], "Q6 text"


def test_q7_taxiway_usage(ans):
    # Team rule (2026-11-14): exclusion_reason IS NULL and the proxy time inside the Aug 8 window.
    # Expected numbers are the team's reviewed values for this rule (the ground-truth file still lists the
    # older all-flights assumption: 1,055 / B_28 513 / B_15 226 / B 1,037).
    a = ans("Q7")
    seg = [(r["taxiway_section"], r["flights"]) for r in a["data"]]
    assert len(seg) == 31, "Q7 should have 31 sections"
    assert seg[:5] == [("B_28", 512), ("E_5", 363), ("B_15", 224), ("B_13", 208), ("B_20", 127)], "Q7 top sections"
    assert a["included_count"] == 1053, "Q7 flights counted"
    assert a["excluded"] == {"outside the reporting day": 1, "missing time": 1, "no taxiway recorded": 6}, "Q7 sample"
    assert "Bravo (B), 1,032 flights" in a["answer"] and "Tango (T)" in a["answer"], "Q7 text"
    assert "'2025-08-08 00:00:00'" in a["sql_queries"][0] and "'2025-08-09 00:00:00'" in a["sql_queries"][0], \
        "Q7 shown SQL has both window ends"


def test_q7_other_day_has_no_data(app, tpl):
    a = tpl.answer("Q7", app.db_manager.fetch, "2025-08-09")
    assert a["data"] == [] and "No data for 2025-08-09" in a["answer"]


def test_q8_wheels_down_to_parking(ans):
    a = ans("Q8")
    r = a["data"][0]
    assert round(r["avg_taxi_in_min"], 4) == 12.1954 and r["flights"] == 525, "Q8 average / sample"
    assert "12.20 minutes" in a["answer"], "Q8 text"


def test_q9_runway_activity(ans):
    a = ans("Q9")
    rows = [(r["runway"], r["takeoffs"], r["landings"], r["total_operations"]) for r in a["data"]]
    assert rows == [("34R", 512, 23, 535), ("34L", 1, 497, 498), ("34C", 11, 1, 12), ("16L", 7, 0, 7),
                    ("16R", 0, 4, 4), ("16C", 3, 0, 3)], "Q9 runways"
    assert a["included_count"] == 1059, "Q9 completed operations"
    assert a["excluded"] == {"missed approach": 1, "missing runway": 1}, "Q9 exclusions"
    assert "1 on 34L" in a["answer"], "Q9 missed approach reported separately"


def test_q10_peak_hours(ans):
    # Team rule (2026-11-14): the take-off with no runway counts. The ground truth gives this case:
    # "if included, only the 19:00 hour changes (57 -> 58), rank stays 12".
    a = ans("Q10")
    got = {r["local_hour"]: (r["operations"], r["hour_rank"]) for r in a["data"]}
    gt = {0: (14, 20), 1: (5, 21), 2: (1, 23), 3: (0, 24), 4: (2, 22), 5: (16, 19), 6: (31, 18), 7: (49, 14),
          8: (69, 2), 9: (62, 7), 10: (74, 1), 11: (59, 9), 12: (64, 5), 13: (44, 16), 14: (68, 3), 15: (45, 15),
          16: (64, 5), 17: (50, 13), 18: (66, 4), 19: (58, 12), 20: (62, 7), 21: (59, 9), 22: (59, 9), 23: (39, 17)}
    assert got == gt, "Q10 hourly operations and ranks"
    assert sum(r["takeoffs"] for r in a["data"]) == 535 and sum(r["landings"] for r in a["data"]) == 525, "Q10 totals"
    assert a["included_count"] == 1060 and a["excluded"] == {"missed approach": 1}, "Q10 sample"
    assert "10:00–10:59, 74 operations" in a["answer"] and "12:00 & 16:00 (64, rank 5)" in a["answer"], "Q10 text + ties"
    assert "not a forecast" in a["answer"], "Q10 history-only note"


# ---- template rules ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("qid", [f"Q{i}" for i in range(1, 11)])
def test_same_question_same_sql(tpl, qid):
    assert tpl.build_queries(qid) == tpl.build_queries(qid), "same intent must give the same SQL"


@pytest.mark.parametrize("qid", [f"Q{i}" for i in range(1, 11)])
def test_values_are_parameters(tpl, qid):
    for _, sql, params in tpl.build_queries(qid):
        assert "2025-08-08" not in sql, "dates go in as %s parameters"
        assert sql.count("%s") == len(params)
        assert "ORDER BY" in sql or "COUNT(" in sql, "fixed order (or a single value)"


def test_invalid_requests_raise(tpl):
    for bad in ("Q11", "other", "", None):
        with pytest.raises(tpl.IntentError):
            tpl.build_queries(bad)
    with pytest.raises(tpl.IntentError):
        tpl.build_queries("Q1", "08/08/2025")


def test_other_day_has_no_data(app, tpl):
    a = tpl.answer("Q8", app.db_manager.fetch, "2025-08-09")
    assert a["data"] == [] and "No data for 2025-08-09" in a["answer"]


def test_every_answer_has_definition_and_sample(ans):
    for i in range(1, 11):
        a = ans(f"Q{i}")
        assert a["answer"].startswith("**Answer:**"), f"Q{i} answer first, like views mode"
        assert "**Definition (" in a["answer"] and "**Sample:** based on" in a["answer"], f"Q{i} answer parts"
        averages = i in (1, 2, 4, 5, 6, 8)  # answers that show averages; Q3, Q7, Q9, Q10 are counts
        footer = "_Times are SEA local (PDT)." + (" Averages are rounded to 2 decimals._" if averages else "_")
        assert a["answer"].endswith(footer), f"Q{i} footer"
        assert a["definition"] and a["included_count"] > 0, f"Q{i} metadata"


# ---- intent -----------------------------------------------------------------------------------------------------

def test_parse_reply_validates(intent_mod):
    assert intent_mod.parse_reply('{"question": "Q4", "date": null}') == {"question": "Q4", "date": None}
    assert intent_mod.parse_reply('```json\n{"question": "q10", "date": "2025-08-08"}\n```') == {"question": "Q10", "date": "2025-08-08"}
    for bad in ['{"question": "other", "date": null}', '{"question": "Q11"}', "not json", "",
                '{"question": "Q1", "date": "Aug 8"}', '{"question": "Q1", "date": null, "sql": "DROP TABLE x"}',
                '["Q1"]']:
        assert intent_mod.parse_reply(bad) is None, f"invalid reply accepted: {bad!r}"


def test_prompt_has_menu(intent_mod):
    p = intent_mod.build_prompt("What is the average taxi-in time by aircraft type?")
    assert all(f"- Q{i}:" in p for i in range(1, 11)) and "other" in p and "JSON only" in p


# The ground-truth file's two phrasings per question (direct and natural).
PHRASINGS = {
    "Q1": ["What is the average taxi-in time by aircraft type?", "Which aircraft types take the longest to reach the gate after landing?"],
    "Q2": ["What is the average taxi-out time for each hour of the day?", "Can you show how long departures taxi before takeoff, by hour?"],
    "Q3": ["What is the maximum number of aircraft in the movement area each hour?", "How busy was the movement area during each hour of the day?"],
    "Q4": ["What is the average runway occupancy time for arrivals and departures, by runway?", "How long do aircraft stay on the runway?"],
    "Q5": ["What is the average takeoff delay compared to the scheduled takeoff time?", "How late were departures taking off on average?"],
    "Q6": ["Compare average taxi-in and taxi-out times by weight class.", "Do heavy aircraft taxi longer than medium ones?"],
    "Q7": ["How many flights used each taxiway segment?", "Which taxiway sections were used the most?"],
    "Q8": ["What is the average time from wheels-down to parking?", "On average, how long does an arriving flight take to park after touching down?"],
    "Q9": ["How many takeoffs and landings did each runway have?", "Which runway was used the most?"],
    "Q10": ["What were the busiest hours of the day by number of takeoffs and landings?", "Which hour had the most flight activity?"],
}


@pytest.mark.parametrize("qid,question", [(q, p) for q, ps in PHRASINGS.items() for p in ps])
def test_keyword_fallback_routes_ground_truth_phrasings(intent_mod, qid, question):
    assert intent_mod.keyword_match(question) == qid


def test_keyword_fallback_ignores_other_questions(intent_mod):
    for q in ("What's the weather in Seattle?", "List all carriers", "hello"):
        assert intent_mod.keyword_match(q) is None


def test_ai_failure_uses_keywords(intent_mod):
    client = FakeIntentClient(error=RuntimeError("503 UNAVAILABLE high demand"))
    assert intent_mod.parse("How many takeoffs and landings did each runway have?", client) == \
        {"question": "Q9", "date": None, "source": "keywords"}


def test_ai_other_returns_none(intent_mod):
    client = FakeIntentClient('{"question": "other", "date": null}')
    assert intent_mod.parse("Which carrier has the most flights?", client) is None


# ---- end to end through the agent -------------------------------------------------------------------------------

def test_agent_answers_from_template(app):
    agent = app.SeaTacAgent(None, None, app.db_manager)
    agent.intent_client = FakeIntentClient('{"question": "Q8", "date": null}')
    r = asyncio.run(agent.process_query("What is the average time from wheels-down to parking?"))
    assert r["success"] and r["sql_source"] == "template" and r["use_case"] == "Q8"
    assert r["included_count"] == 525 and r["metric"] and r["definition"]
    assert r["sql_queries"] and "v_taxi_in" in r["sql_queries"][0]


def test_agent_falls_back_to_views_mode(app):
    sql = "SELECT carrier, COUNT(*) AS flights FROM v_taxi_in WHERE exclusion_reason IS NULL GROUP BY carrier ORDER BY carrier"
    agent = app.SeaTacAgent(FakeGenerator(sql), None, app.db_manager)
    agent.intent_client = FakeIntentClient('{"question": "other", "date": null}')
    r = asyncio.run(agent.process_query("How many arrivals did each carrier have?"))
    assert r["success"] and r["sql_source"] == "ai_sql" and r["sql_queries"] == [sql]
    assert r["reasoning_steps"][0]["action"] == "pick_template"


def test_agent_invalid_intent_falls_back(app):
    agent = app.SeaTacAgent(FakeGenerator(None), None, app.db_manager)
    agent.intent_client = FakeIntentClient('{"question": "Q99", "date": null}')
    r = asyncio.run(agent.process_query("something unusual"))
    assert r["sql_source"] == "ai_sql" and not r["success"]


# ---- answer source label sent to the frontend badge (/api/query) ------------------------------------------------

def _ask_endpoint(app, monkeypatch, agent, question):
    monkeypatch.setattr(app, "agent_system", agent)
    return asyncio.run(app.handle_query(app.QueryRequest(query=question)))


def test_endpoint_labels_template_answers_verified(app, monkeypatch):
    agent = app.SeaTacAgent(None, None, app.db_manager)
    agent.intent_client = FakeIntentClient('{"question": "Q8", "date": null}')
    r = _ask_endpoint(app, monkeypatch, agent, "What is the average time from wheels-down to parking?")
    assert r.success and r.sql_source == "template"


def test_endpoint_labels_ai_sql_answers_not_verified(app, monkeypatch):
    sql = "SELECT carrier, COUNT(*) AS flights FROM v_taxi_in WHERE exclusion_reason IS NULL GROUP BY carrier ORDER BY carrier"
    agent = app.SeaTacAgent(FakeGenerator(sql), None, app.db_manager)
    agent.intent_client = FakeIntentClient('{"question": "other", "date": null}')
    r = _ask_endpoint(app, monkeypatch, agent, "How many arrivals did each carrier have?")
    assert r.success and r.sql_source == "ai_sql"


def test_endpoint_gives_no_label_when_it_cannot_answer(app, monkeypatch):
    agent = app.SeaTacAgent(FakeGenerator(None), None, app.db_manager)
    agent.intent_client = FakeIntentClient('{"question": "other", "date": null}')
    r = _ask_endpoint(app, monkeypatch, agent, "something unusual")
    assert not r.success and r.sql_source == "none"


def test_answer_source_for_every_mode(app):
    src = app.answer_source
    assert src({"success": True, "sql_source": "template"}) == "template"
    for legacy_or_views in ("generated", "prebuilt", "claude", "ai_sql", None):  # legacy and views mode
        assert src({"success": True, "sql_source": legacy_or_views}) == "ai_sql"
    for failed in ("template", "ai_sql", "error", "rejected", "none"):
        assert src({"success": False, "sql_source": failed}) == "none"
