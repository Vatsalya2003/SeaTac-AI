"""
QUERY_MODE=views, end to end without an AI API.

A fake SQL generator returns hand-written SQL for each of the Port's 10 questions; the real agent then checks
the SQL, runs it as the read-only user and writes the answer in code. Results are compared against queries
run directly on the views and the flights table with the admin user. No metric values are hard-coded here:
the views themselves are checked against the Excel file by src/database/tests.
"""
import asyncio
import importlib
from datetime import date, datetime
from decimal import Decimal
import os
import re
import sys

import pytest

from conftest import BACKEND_DIR


@pytest.fixture(scope="module")
def app(admin_db):
    os.environ["QUERY_MODE"] = "views"
    os.environ["GEMINI_API_KEY"] = ""   # blanked before import: load_dotenv doesn't override set variables,
    os.environ["CLAUDE_API_KEY"] = ""   # so no AI client is created
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    module = sys.modules.get("app_optimized")
    module = importlib.reload(module) if module else importlib.import_module("app_optimized")
    assert module.VIEWS_MODE
    if not module.db_manager.test_connection():
        pytest.skip("read-only user seatac_reader can't connect (run src/database/scripts/create_reader.py)")
    return module


@pytest.fixture(scope="module")
def vm(app):
    return sys.modules["views_mode"]


class FakeGenerator:
    """Stands in for DirectClaudeSQLGenerator: returns fixed SQL, never calls an AI API."""
    def __init__(self, sql):
        self.sql = sql

    async def generate_sql(self, query):
        return self.sql


@pytest.fixture(scope="module")
def ask(app):
    def run(sql, question="question"):
        agent = app.SeaTacAgent(FakeGenerator(sql), None, app.db_manager)
        return asyncio.run(agent.process_query(question))
    return run


# Hand-written SQL for the Port's 10 questions (Q3 has two parts).
QUESTIONS = {
    "Q1": "SELECT aircraft_type_group, ROUND(AVG(duration_sec) / 60, 2) AS avg_taxi_in_min, COUNT(*) AS flights "
          "FROM v_taxi_in WHERE exclusion_reason IS NULL GROUP BY aircraft_type_group ORDER BY avg_taxi_in_min DESC",
    "Q2": "SELECT selection_hour, ROUND(AVG(duration_sec) / 60, 2) AS avg_taxi_out_min, COUNT(*) AS flights "
          "FROM v_taxi_out WHERE exclusion_reason IS NULL GROUP BY selection_hour ORDER BY selection_hour",
    "Q3a": "SELECT local_date, local_hour, max_aircraft_in_area FROM v_movement_area_hourly_peak "
           "ORDER BY local_date, local_hour",
    "Q3b": "SELECT operation, ROUND(AVG(duration_sec) / 60, 2) AS avg_min, COUNT(*) AS flights "
           "FROM v_movement_area WHERE exclusion_reason IS NULL GROUP BY operation",
    "Q4": "SELECT operation, ROUND(AVG(duration_sec), 2) AS avg_occupancy_sec, COUNT(*) AS flights "
          "FROM v_runway_occupancy WHERE exclusion_reason IS NULL GROUP BY operation",
    "Q5": "SELECT ROUND(AVG(delay_sec) / 60, 4) AS avg_delay_min, COUNT(*) AS flights, SUM(delay_sec < 0) AS early "
          "FROM v_takeoff_delay WHERE exclusion_reason IS NULL",
    "Q6": "SELECT w.label AS weight_class, ROUND(AVG(t.duration_sec) / 60, 2) AS avg_taxi_in_min, "
          "COUNT(t.flight_info_id) AS flights FROM v_weight_classes w LEFT JOIN v_taxi_in t "
          "ON t.weight_class_group = w.weight_class_group AND t.exclusion_reason IS NULL "
          "GROUP BY w.weight_class_group, w.label, w.sort_order ORDER BY w.sort_order",
    "Q7": "SELECT taxiway_name, COUNT(DISTINCT flight_info_id, operation) AS flights FROM v_taxiway_usage "
          "WHERE exclusion_reason IS NULL GROUP BY taxiway_name ORDER BY flights DESC",
    "Q8": "SELECT ROUND(AVG(duration_sec) / 60, 4) AS avg_taxi_in_min, COUNT(*) AS flights "
          "FROM v_taxi_in WHERE exclusion_reason IS NULL",
    "Q9": "SELECT runway, activity, COUNT(*) AS flights FROM v_runway_activity WHERE exclusion_reason IS NULL "
          "GROUP BY runway, activity ORDER BY runway, activity",
    "Q10": "SELECT local_date, local_hour, operations, hour_rank FROM v_peak_hours WHERE hour_rank <= 3 "
           "ORDER BY local_date, hour_rank",
}
SINGLE_VIEW = {"Q1": "v_taxi_in", "Q2": "v_taxi_out", "Q3b": "v_movement_area", "Q4": "v_runway_occupancy",
               "Q5": "v_takeoff_delay", "Q7": "v_taxiway_usage", "Q8": "v_taxi_in", "Q9": "v_runway_activity"}
SAMPLE = re.compile(r"\*\*Sample:\*\* based on ([\d,]+) of ([\d,]+) ")


@pytest.fixture(scope="module")
def answers(ask):
    return {k: ask(sql) for k, sql in QUESTIONS.items()}


def _num(s):
    return int(s.replace(",", ""))


def _as_json(row):
    """The same conversion DatabaseManager.execute_query applies: Decimal -> float, date/datetime -> ISO text."""
    return {k: float(v) if isinstance(v, Decimal) else v.isoformat() if isinstance(v, (date, datetime)) else v
            for k, v in row.items()}


# ---- setup ------------------------------------------------------------------------------------------------

def test_connects_as_read_only_user_to_seatac(app):
    assert app.db_manager.db_config["user"] == "seatac_reader"
    assert app.db_manager.db_config["database"] == "seatac"


def test_no_ai_client_in_tests(app):
    assert app.claude_client is None


def test_read_only_user_cannot_read_tables(app):
    with pytest.raises(Exception, match="(?i)denied"):
        app.db_manager.fetch("SELECT 1 FROM flights LIMIT 1")


# ---- the 10 questions ---------------------------------------------------------------------------------------

@pytest.mark.parametrize("key", QUESTIONS)
def test_question_runs_with_definition(answers, key):
    r = answers[key]
    assert r["success"], f"{key} failed"
    assert r["row_count"] > 0
    assert "**Definition" in r["answer"]
    assert "Times are SEA local" in r["answer"]


@pytest.mark.parametrize("key", QUESTIONS)
def test_rows_are_exactly_the_query_result(answers, admin_fetch, key):
    """No fallback rows and no injected filters: the rows equal the same SQL run directly."""
    r = answers[key]
    direct = [_as_json(row) for row in admin_fetch(QUESTIONS[key])]
    assert r["sql_queries"] == [QUESTIONS[key]]
    if r["row_count"] != len(direct) or r["data"] != direct[:100]:
        pytest.fail(f"{key}: rows differ from the direct query")  # no values in the message


@pytest.mark.parametrize("key", QUESTIONS)
def test_one_ai_call_only(answers, key):
    """The answer is written in code: there is no second AI call for insights."""
    assert answers[key]["insights"] == [answers[key]["answer"]]


@pytest.mark.parametrize("key", list(SINGLE_VIEW))
def test_sample_size_matches_the_view(answers, admin_fetch, key):
    view = SINGLE_VIEW[key]
    m = SAMPLE.search(answers[key]["answer"])
    assert m, f"{key}: no sample-size sentence"
    counts = admin_fetch(f"SELECT COUNT(*) AS total, SUM(exclusion_reason IS NULL) AS used FROM {view}")[0]
    if (_num(m.group(1)), _num(m.group(2))) != (int(counts["used"]), int(counts["total"])):
        pytest.fail(f"{key}: sample counts differ from the view")


@pytest.mark.parametrize("view, operation", [("v_taxi_in", "Arrival"), ("v_taxi_out", "Departure"),
                                             ("v_takeoff_delay", "Departure")])
def test_sample_total_matches_flights_table(admin_fetch, ask, view, operation):
    """Independent of the views: the sample total equals the flights of that kind in the flights table."""
    r = ask(f"SELECT COUNT(*) AS flights FROM {view} WHERE exclusion_reason IS NULL")
    total = _num(SAMPLE.search(r["answer"]).group(2))
    expected = admin_fetch("SELECT COUNT(*) AS n FROM flights WHERE operation = %s", (operation,))[0]["n"]
    if total != expected:
        pytest.fail(f"{view}: sample total differs from the {operation} count in flights")


def test_exclusion_reasons_listed(answers, admin_fetch):
    reasons = admin_fetch("SELECT exclusion_reason AS reason, COUNT(*) AS n FROM v_takeoff_delay "
                          "WHERE exclusion_reason IS NOT NULL GROUP BY exclusion_reason")
    answer = answers["Q5"]["answer"]
    if not reasons:
        assert "(none excluded)" in answer
    for r in reasons:
        if f"{r['reason']} {int(r['n']):,}" not in answer:
            pytest.fail(f"exclusion reason '{r['reason']}' missing or miscounted")


def test_join_gets_whole_day_note(answers):
    assert "whole day" in answers["Q6"]["answer"]


def test_null_average_shown_as_no_data(answers):
    if any(row["avg_taxi_in_min"] is None for row in answers["Q6"]["data"]):
        assert "No data" in answers["Q6"]["answer"]


def test_peak_interval_sample(answers):
    assert "aircraft intervals" in answers["Q3a"]["answer"]


def test_peak_hours_note(answers):
    assert "missed approach is not counted" in answers["Q10"]["answer"]


def test_taxiway_proxy_marked_provisional(answers):
    assert "PROVISIONAL" in answers["Q7"]["answer"]


# ---- filters, aliases, empty results ------------------------------------------------------------------------

def test_alias_and_hour_filter_sample_follows_filter(ask):
    r = ask("SELECT ROUND(AVG(t.duration_sec) / 60, 2) AS avg_min, COUNT(*) AS flights FROM v_taxi_in t "
            "WHERE t.exclusion_reason IS NULL AND t.selection_hour = 8")
    assert r["success"]
    assert "matching the question's filters" in r["answer"]
    if _num(SAMPLE.search(r["answer"]).group(1)) != r["data"][0]["flights"]:
        pytest.fail("filtered sample count differs from the query's flight count")


def test_missing_exclusion_filter_warns(ask):
    r = ask("SELECT COUNT(*) AS flights FROM v_movement_area")
    assert r["success"]
    assert "did not apply the exclusion rule" in r["answer"]


def test_no_rows_gives_clear_message_and_no_fallback(ask):
    r = ask("SELECT runway, COUNT(*) AS flights FROM v_runway_activity "
            "WHERE exclusion_reason IS NULL AND runway = '99X' GROUP BY runway")
    assert r["success"] and r["row_count"] == 0 and r["data"] == []
    assert "No flights matched" in r["answer"]


def test_string_literal_with_keyword_text(ask):
    r = ask("SELECT runway, activity, COUNT(*) AS flights FROM v_runway_activity "
            "WHERE exclusion_reason = 'missing runway' GROUP BY runway, activity")
    assert r["success"]


def test_no_hour_filter_injection(ask):
    r = ask(QUESTIONS["Q1"], "top 5 aircraft types at 2pm")
    assert r["sql_queries"] == [QUESTIONS["Q1"]]


def test_generation_failure_returns_no_rows(ask):
    r = ask(None)
    assert not r["success"]
    assert "couldn't answer this reliably" in r["answer"]
    assert "data" not in r


# ---- SQL rejected before running ----------------------------------------------------------------------------

REJECTED = {
    "DROP TABLE flights": "only a SELECT",
    "DELETE FROM v_taxi_in": "only a SELECT",
    "UPDATE v_taxi_in SET call_sign = 'X'": "only a SELECT",
    "WITH x AS (SELECT 1) DELETE FROM v_taxi_in": "only a SELECT",
    "SELECT * FROM flights": "only the seatac views",
    "SELECT * FROM raw_flight_details": "only the seatac views",
    "SELECT * FROM AIplane.flight": "only the seatac views",
    "SELECT * FROM v_taxi_in; DROP TABLE flights": "more than one statement",
    "SELECT * FROM v_taxi_in -- comment": "comments",
    "SELECT * FROM v_taxi_in /* x */": "comments",
    "SELECT * FROM v_taxi_in # x": "comments",
    "SELECT * FROM v_taxi_in INTO OUTFILE '/tmp/x'": "not allowed",
    "SELECT * FROM information_schema.tables": "not allowed",
    "SELECT SLEEP(10) FROM v_taxi_in": "not allowed",
    "SELECT 1": "reads no view",
}


@pytest.mark.parametrize("sql", REJECTED)
def test_rejected_before_running(vm, ask, sql):
    ok, why = vm.check_view_sql(sql)
    assert not ok and REJECTED[sql] in why
    r = ask(sql)
    assert not r["success"]
    assert "rejected before running" in r["answer"]
    assert "data" not in r


def test_comma_join_to_table_blocked_by_read_only_user(ask):
    """The text check doesn't catch a comma join; the read-only user's permissions do."""
    r = ask("SELECT * FROM v_taxi_in t, flights f")
    assert not r["success"]
    assert "denied" in r["answer"].lower()


def test_valid_join_on_views_accepted(vm):
    assert vm.check_view_sql(QUESTIONS["Q6"])[0]


def test_one_trailing_semicolon_accepted(vm):
    ok, sql = vm.check_view_sql(QUESTIONS["Q8"] + ";")
    assert ok and not sql.endswith(";")


# ---- small talk ---------------------------------------------------------------------------------------------

DATA_QUESTIONS = ["Can you show taxi-in by aircraft type?", "Show me runway use", "Which runway was busiest?",
                  "flights this morning", "Could you list the peak hours", "What is the average taxi-out?",
                  "How many departures?", "your busiest hour", "super late departures",
                  "Which hour had the most take-offs?"]
SMALL_TALK = ["hi", "Hello there", "thanks!", "Thank you so much", "what can you do?", "who are you", "bye",
              "good morning"]


@pytest.mark.parametrize("q", DATA_QUESTIONS)
def test_data_question_goes_to_sql(app, q):
    assert not app.GreetingHandler(None).is_greeting_or_casual(q)


@pytest.mark.parametrize("q", SMALL_TALK)
def test_small_talk_stays_small_talk(app, q):
    assert app.GreetingHandler(None).is_greeting_or_casual(q)


# ---- prompt -------------------------------------------------------------------------------------------------

def test_prompt_columns_exist_in_views(vm, admin_fetch):
    cols = {v: {r["COLUMN_NAME"] for r in admin_fetch(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = 'seatac' AND TABLE_NAME = %s", (v,))}
        for v in vm.VIEWS}
    missing = []
    for block in re.split(r"\n(?=\s*\d+\. v_)", vm.VIEWS_SCHEMA.split("RULES")[0]):
        m = re.search(r"\d+\. (v_\w+)", block)
        if m and "Columns:" in block:
            text = block.split("Columns:")[1].split("No exclusion")[0]
            while re.search(r"\([^()]*\)", text):  # drop notes in parentheses, including nested ones like RANK()
                text = re.sub(r"\([^()]*\)", "", text)
            listed = re.findall(r"\b[a-z_]+\b", text)
            missing += [f"{m.group(1)}.{c}" for c in listed if c not in cols[m.group(1)]]
    assert not missing, missing


def test_prompt_lists_every_view(vm):
    assert all(v in vm.VIEWS_SCHEMA for v in vm.VIEWS)
