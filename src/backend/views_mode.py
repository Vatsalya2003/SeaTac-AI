"""
Views mode (QUERY_MODE=views): the chatbot queries the `seatac` metric views instead of the old tables.

- VIEWS_SCHEMA: the prompt text that describes the views and the Port's confirmed rules
- check_view_sql(): only a single SELECT on the seatac views may run
- is_greeting_or_casual(): small-talk check that sends real questions ("Can you...", "Show...") to SQL
- build_answer(): the answer text, written in code from the FULL result, with the metric definition
  (src/database/metric_rules.yaml) and the sample size. No second AI call.

Used only when QUERY_MODE=views. Legacy mode never calls anything here.
"""
import re
from pathlib import Path

VIEWS_DATABASE = "seatac"
METRIC_RULES = Path(__file__).resolve().parent.parent / "database" / "metric_rules.yaml"

VIEWS = ["v_taxi_in", "v_taxi_out", "v_weight_classes", "v_movement_area", "v_movement_area_hourly_peak",
         "v_runway_occupancy", "v_takeoff_delay", "v_taxiway_usage", "v_runway_activity", "v_peak_hours"]
# per-flight views (they have exclusion_reason) -> what one row is, for the sample-size sentence
ROW_NOUNS = {
    "v_taxi_in": "arrivals",
    "v_taxi_out": "departures",
    "v_takeoff_delay": "departures",
    "v_movement_area": "flight legs",
    "v_runway_occupancy": "flight legs",
    "v_taxiway_usage": "taxiway-segment records (2 per leg)",
    "v_runway_activity": "take-offs, landings and missed approaches",
}

VIEWS_SCHEMA = """
DATABASE: seatac (MySQL 8). Port of Seattle (SEA) airfield data for one operating day, 2025-08-08.
Query ONLY these views. The Port's confirmed calculation rules are already built into them.
All times are SEA local time (PDT), exactly as exported. One row = one flight leg unless noted.

VIEWS
1. v_taxi_in   - Q1 (by aircraft type), Q6 (by weight class, arrivals), Q8 (one overall average)
   Arrivals: wheels down (touchdown) -> actual in-block (parked). Selected by wheels-down time.
   Columns: flight_info_id, operation, call_sign, carrier, aircraft_type, aircraft_type_group, weight_class_icao,
   weight_class_group, runway, gate, sea_date, start_time, end_time, selection_time, selection_date, selection_hour,
   duration_sec, duration_min, sys_taxi_in_sec, exclusion_reason, included
2. v_taxi_out  - Q2 (by hour of day), Q6 (by weight class, departures)
   Departures: actual off-block (left parking) -> wheels up (take-off). Selected by off-block time.
   Columns: flight_info_id, operation, call_sign, carrier, aircraft_type, aircraft_type_group, weight_class_icao,
   weight_class_group, runway, gate, sea_date, start_time, end_time, selection_time, selection_date, selection_hour,
   off_block_date, off_block_hour, duration_sec, duration_min, sys_taxi_out_sec, exclusion_reason, included
3. v_weight_classes - Q6 helper: the fixed list of groups (weight_class_group, label, sort_order):
   L Light, M Medium, H Heavy, Unknown. LEFT JOIN it to v_taxi_in / v_taxi_out ON weight_class_group so every
   class is listed; a class with no rows gives NULL (shown as "No data"), never 0.
4. v_movement_area - Q3 (time in the movement area)
   Arrivals: wheels down -> movement area exit. Departures: movement area entrance -> wheels up.
   Columns: flight_info_id, operation, call_sign, aircraft_type, aircraft_type_group, weight_class_icao, runway,
   sea_date, start_time, end_time, selection_time, selection_date, selection_hour, duration_sec, duration_min,
   exclusion_reason, included
5. v_movement_area_hourly_peak - Q3 (most aircraft in the movement area at the same time, per local hour)
   One row per local hour. Columns: local_date, local_hour, max_aircraft_in_area, intervals_used,
   intervals_excluded, excluded_missing_time, excluded_negative_duration. No exclusion_reason column.
6. v_runway_occupancy - Q4 (runway occupancy time, in SECONDS)
   Arrivals: wheels down -> runway exit. Departures: runway entrance -> wheels up. Report arrivals and
   departures separately (GROUP BY operation) unless asked for both together.
   Columns: flight_info_id, operation, call_sign, aircraft_type, aircraft_type_group, weight_class_icao, runway,
   sea_date, start_time, end_time, selection_time, selection_date, selection_hour, duration_sec,
   sys_runway_occupancy_sec, exclusion_reason, included
7. v_takeoff_delay - Q5 (take-off delay)
   Departures: wheels up - scheduled take-off. Positive = late, negative = early (negatives are valid, keep them).
   Columns: flight_info_id, operation, call_sign, carrier, aircraft_type, aircraft_type_group, weight_class_icao,
   runway, sea_date, scheduled_take_off, wheels_up, selection_time, selection_date, selection_hour, delay_sec,
   delay_min, exclusion_reason, included
8. v_taxiway_usage - Q7 (taxiway use). TWO rows per leg: segment_role 'runway' and 'ramp'.
   Count legs with COUNT(DISTINCT flight_info_id, operation), grouped by taxiway_name (a taxiway, e.g. 'Bravo')
   or taxiway_segment (a section, e.g. 'TaxiwaySegment_B_28').
   Columns: flight_info_id, operation, call_sign, aircraft_type, weight_class_icao, runway, sea_date, segment_role,
   taxiway_segment, taxiway_letter, taxiway_name, segment_number, selection_time, selection_date, selection_hour,
   is_proxy_time, exclusion_reason, included
9. v_runway_activity - Q9 (take-offs and landings per runway)
   One row per take-off (activity 'takeoff'), completed landing ('landing') or missed approach
   ('missed_approach', is_missed_approach = 1). Runways: 16C, 16L, 16R, 34C, 34L, 34R.
   Columns: flight_info_id, operation, call_sign, aircraft_type, weight_class_icao, runway, sea_date, activity,
   activity_time, selection_time, selection_date, selection_hour, local_date, local_hour, is_missed_approach,
   exclusion_reason, included
10. v_peak_hours - Q10 (busiest hours: take-offs + completed landings per local hour, history only)
   One row per local hour. Columns: local_date, local_hour, operations, takeoffs, landings, hour_rank
   (RANK() per local_date, so tied hours share a rank). No exclusion_reason column.

RULES
- Use only rows WHERE exclusion_reason IS NULL in every per-flight view (views 1, 2, 4, 6, 7, 8, 9).
- Group by aircraft type with aircraft_type_group (missing types are 'Unknown'), and by weight class with
  weight_class_group (via v_weight_classes for Q6). Never group by aircraft_type or weight_class_icao.
- Filter and group by time with selection_date and selection_hour (local). Never use sea_date for windows.
  A window includes its start and excludes its end: selection_time >= start AND selection_time < end.
- Averages in minutes: ROUND(AVG(duration_sec) / 60, 2) (take-off delay: ROUND(AVG(delay_sec) / 60, 2)).
  Runway occupancy: ROUND(AVG(duration_sec), 2) in seconds.
- Always return the number of flights used as COUNT(*) AS flights (Q7: COUNT(DISTINCT flight_info_id, operation)).
- No duration cutoffs, no minimum group size, no "BETWEEN 1 AND 120" filters.
- Identify flights by flight_info_id + operation, never by call_sign.
- Missed approaches (Q9): count them separately with is_missed_approach = 1 (not completed landings).
- Q10 peak hours: use v_peak_hours (it already counts take-offs + landings without needing a runway).
- One SELECT statement only. No other tables, no comments, no semicolons.

EXAMPLES
Q8: SELECT ROUND(AVG(duration_sec) / 60, 2) AS avg_taxi_in_min, COUNT(*) AS flights
    FROM v_taxi_in WHERE exclusion_reason IS NULL
Q1: SELECT aircraft_type_group, ROUND(AVG(duration_sec) / 60, 2) AS avg_taxi_in_min, COUNT(*) AS flights
    FROM v_taxi_in WHERE exclusion_reason IS NULL GROUP BY aircraft_type_group ORDER BY avg_taxi_in_min DESC
Q6: SELECT w.label AS weight_class, ROUND(AVG(t.duration_sec) / 60, 2) AS avg_taxi_in_min, COUNT(t.flight_info_id) AS flights
    FROM v_weight_classes w LEFT JOIN v_taxi_in t ON t.weight_class_group = w.weight_class_group AND t.exclusion_reason IS NULL
    GROUP BY w.weight_class_group, w.label, w.sort_order ORDER BY w.sort_order
Q9: SELECT runway, activity, COUNT(*) AS flights FROM v_runway_activity
    WHERE exclusion_reason IS NULL GROUP BY runway, activity ORDER BY runway, activity
"""

SQL_INSTRUCTIONS = """Write ONE MySQL SELECT statement on the views above that answers the question.
Return ONLY the SQL: no explanation, no markdown, no comments, no semicolon.
If the question can't be answered from these views, return exactly: CANNOT_ANSWER"""

FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|replace|truncate|rename|grant|revoke|call|do|"
                       r"handler|load|lock|unlock|set|into|outfile|dumpfile|sleep|benchmark|execute|prepare|"
                       r"information_schema|performance_schema|mysql)\b", re.I)
STRINGS = re.compile(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"")


def _strip_strings(sql):
    return STRINGS.sub("''", sql)


def referenced_relations(sql):
    """Names after FROM / JOIN (not subqueries), lower-case, without backticks or a seatac. prefix."""
    names = re.findall(r"\b(?:from|join)\s+(?!\()([`\w.]+)", _strip_strings(sql), re.I)
    out = []
    for n in names:
        n = n.replace("`", "").lower()
        out.append(n[len(VIEWS_DATABASE) + 1:] if n.startswith(VIEWS_DATABASE + ".") else n)
    return out


def check_view_sql(sql):
    """-> (ok, cleaned_sql_or_reason). Only a single SELECT that reads the seatac views is allowed."""
    if not sql or not sql.strip():
        return False, "empty query"
    sql = sql.strip()
    if sql.endswith(";"):
        sql = sql[:-1].strip()
    bare = _strip_strings(sql)
    if ";" in bare:
        return False, "more than one statement"
    if re.search(r"--|/\*|#", bare):
        return False, "comments are not allowed"
    if not re.match(r"^\(*\s*select\b", bare, re.I):
        return False, "only a SELECT statement is allowed"
    word = FORBIDDEN.search(bare)
    if word:
        return False, f"'{word.group(1)}' is not allowed"
    relations = referenced_relations(sql)
    if not relations:
        return False, "the query reads no view"
    others = [r for r in relations if r not in VIEWS]
    if others:
        return False, f"only the seatac views may be queried (found: {', '.join(sorted(set(others)))})"
    if re.search(r"\b\w+\.\w+\s*\(", bare) or re.search(r"\b(?!seatac\b)\w+\s*\.\s*v_\w+", bare, re.I):
        return False, "references outside the seatac views are not allowed"
    return True, sql


# ---- small talk ---------------------------------------------------------------------------------------------
DATA_STARTERS = ("can you", "could you", "show", "which", "what", "how many", "how long", "how late", "list",
                 "give", "compare", "find", "tell me the", "average", "when", "where", "is there", "are there")
GREETINGS = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening", "how are you", "whats up",
             "what's up", "howdy", "greetings", "yo", "sup", "hiya", "good day"]
CASUAL_STARTS = ["thank you", "thanks", "appreciate", "awesome", "great", "nice", "help", "who are you",
                 "goodbye", "bye", "see you"]
SYSTEM_QUESTIONS = ["what can you", "who are you", "what do you do", "how does this work", "what is this"]


def is_greeting_or_casual(query):
    """Whole words only (so 'this' is not 'hi'); questions that start like a data question go to SQL."""
    q = re.sub(r"\s+", " ", query.lower().strip())
    if any(p in q for p in SYSTEM_QUESTIONS):
        return True
    if q.startswith(DATA_STARTERS):
        return False
    if len(q.split()) <= 3 and any(re.search(rf"\b{re.escape(g)}\b", q) for g in GREETINGS):
        return True
    return any(re.match(rf"{re.escape(c)}\b", q) for c in CASUAL_STARTS)


# ---- answer written in code -----------------------------------------------------------------------------------
_rules_cache = {}


def metric_rules():
    if "rules" not in _rules_cache:
        try:
            import yaml
            _rules_cache["rules"] = yaml.safe_load(METRIC_RULES.read_text(encoding="utf-8"))
        except Exception as e:  # the answer still works, just without definitions
            print(f"⚠️  metric_rules.yaml not loaded: {e}")
            _rules_cache["rules"] = {}
    return _rules_cache["rules"]


def _fmt(v):
    if v is None:
        return "No data"
    if isinstance(v, float):
        return f"{v:,.2f}"
    if isinstance(v, int) and not isinstance(v, bool):
        return f"{v:,}"
    return str(v)


def _result_text(rows, max_rows=25):
    if not rows:
        return "No flights matched this question."
    cols = list(rows[0].keys())
    if len(rows) == 1 and len(cols) <= 6:
        return "**Answer:** " + " · ".join(f"{c}: **{_fmt(rows[0][c])}**" for c in cols)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(_fmt(r[c]) for c in cols) + " |" for r in rows[:max_rows]]
    shown = f" (first {max_rows} of {len(rows)} rows; all rows are in the table below)" if len(rows) > max_rows else ""
    return f"**Answer** ({len(rows)} rows){shown}:\n\n" + "\n".join(lines)


def _top_level_where(sql):
    """WHERE clause of a simple single-view query (no JOIN, subquery, UNION or WITH), else None."""
    bare = _strip_strings(sql)
    if re.search(r"\b(join|union|with)\b", bare, re.I) or len(re.findall(r"\bselect\b", bare, re.I)) != 1:
        return None
    m = re.search(r"\bwhere\b(.*?)(?=\bgroup\s+by\b|\bhaving\b|\border\s+by\b|\blimit\b|$)", sql, re.I | re.S)
    return m.group(1).strip() if m else ""


EXCLUSION_FILTER = re.compile(r"\b(?:\w+\.)?exclusion_reason\s+is\s+null\b|\b(?:\w+\.)?included\s*=\s*(?:1|true)\b", re.I)


def _from_alias(sql, view):
    """'v_taxi_in t' when the query gives the view an alias, so the WHERE clause can be reused as written."""
    m = re.search(rf"\bfrom\s+`?(?:{VIEWS_DATABASE}\.)?{view}`?(?:\s+(?:as\s+)?(\w+))?", _strip_strings(sql), re.I)
    alias = m.group(1) if m and m.group(1) and m.group(1).lower() not in ("where", "group", "order", "limit", "having") else None
    return f"{view} {alias}" if alias else view


def _counts(run, view, where):
    rows = run(f"SELECT COUNT(*) AS total, SUM(exclusion_reason IS NULL) AS used FROM {view} WHERE {where}")
    reasons = run(f"SELECT exclusion_reason AS reason, COUNT(*) AS n FROM {view} WHERE ({where}) "
                  f"AND exclusion_reason IS NOT NULL GROUP BY exclusion_reason ORDER BY exclusion_reason")
    total, used = int(rows[0]["total"] or 0), int(rows[0]["used"] or 0)
    excluded = ", ".join(f"{r['reason']} {int(r['n'])}" for r in reasons)
    return total, used, excluded


def _sample_text(sql, run):
    relations = referenced_relations(sql)
    flight_views = [v for v in dict.fromkeys(relations) if v in ROW_NOUNS]
    notes = []
    where = _top_level_where(sql)
    if len(flight_views) == 1 and len(set(relations)) == 1 and where is not None:
        view = flight_views[0]
        filtered = EXCLUSION_FILTER.sub("1=1", where) if where else "1=1"
        total, used, excluded = _counts(run, _from_alias(sql, view), filtered)
        scope = " matching the question's filters" if filtered.replace("1=1", "").strip(" ()andAND") else ""
        line = f"**Sample:** based on {used:,} of {total:,} {ROW_NOUNS[view]}{scope}"
        line += f" (excluded: {excluded})." if excluded else " (none excluded)."
        if where == "" or not EXCLUSION_FILTER.search(where):
            line += " ⚠️ This query did not apply the exclusion rule (exclusion_reason IS NULL), so excluded rows may be included."
        notes.append(line)
    else:
        for view in flight_views:
            total, used, excluded = _counts(run, view, "1=1")
            notes.append(f"**Sample ({view}, whole day):** {used:,} of {total:,} {ROW_NOUNS[view]} usable"
                         + (f" (excluded: {excluded})." if excluded else " (none excluded)."))
        if flight_views:
            notes.append("The query uses joins or subqueries, so these counts are for the whole day, not its filters.")
    if "v_movement_area_hourly_peak" in relations:
        r = run("SELECT DISTINCT intervals_used, intervals_excluded, excluded_missing_time FROM v_movement_area_hourly_peak")
        if r:
            notes.append(f"**Sample:** peak counts use {int(r[0]['intervals_used']):,} aircraft intervals "
                         f"({int(r[0]['intervals_excluded']):,} excluded: missing time {int(r[0]['excluded_missing_time']):,}).")
    if "v_peak_hours" in relations:
        notes.append("**Sample:** counts take-offs and completed landings; the missed approach is not counted.")
    return notes


def _definitions(sql):
    metrics = (metric_rules() or {}).get("metrics", {})
    out = []
    for view in dict.fromkeys(referenced_relations(sql)):
        for name, m in metrics.items():
            if m.get("view") == view:
                out.append(f"**Definition ({name.replace('_', ' ')}):** {m.get('definition', '').strip()}")
                for limit in m.get("known_limits", []):
                    if "PENDING" in limit or "PROVISIONAL" in limit:
                        out.append(f"_Note: {limit}_")
                sel = m.get("selection", "")
                if "PROVISIONAL" in sel:
                    out.append(f"_Note: {sel}_")
    return out


def build_answer(sql, rows, run):
    """The answer, written in code from the full result. run(sql) -> list of dict rows (read-only connection)."""
    parts = [_result_text(rows)]
    try:
        parts += _sample_text(sql, run)
    except Exception as e:
        parts.append(f"_(Sample size could not be calculated: {e})_")
    parts += _definitions(sql)
    parts.append("_Times are SEA local (PDT). Averages are rounded to 2 decimals._")
    return "\n\n".join(parts)
