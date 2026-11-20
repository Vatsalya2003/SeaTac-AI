"""
Templates mode (QUERY_MODE=templates), stage 2: pre-written, tested SQL for the Port's 10 questions.

The AI never writes SQL in this mode. intent.py decides which question (Q1-Q10) is being asked, and this module
runs the matching queries on the `seatac` views (read-only user seatac_reader) and writes the answer in code:
a headline, the full table, the sample size with exclusions, the metric definition and any open items.

- QUESTIONS: the menu (id -> title, metric names in metric_rules.yaml, one-line description)
- build_queries(qid, day): the SQL for one question, with its parameters (never pasted into the SQL text)
- answer(qid, run, day): runs the queries and returns the answer dict the backend sends to the frontend

Results are checked against the team's hand-calculated ground truth in tests/test_templates.py.
Rules: only rows with exclusion_reason IS NULL; default reporting day 2025-08-08 (SEA local, start inclusive,
end exclusive); full precision in SQL, rounded to 2 decimals (half up) only in the text; fixed ORDER BY;
an average with no rows is "No data", never 0.
"""
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

import views_mode

DEFAULT_DAY = "2025-08-08"          # the Port's rule: answers cover the Aug 8 local day
AVAILABLE_DAYS = {DEFAULT_DAY}      # the export holds one operating day


class IntentError(ValueError):
    """The question id or a filter isn't valid for templates mode (the caller falls back to stage 1)."""


QUESTIONS = {
    "Q1": {"title": "Taxi-in time by aircraft type", "metrics": ["taxi_in"],
           "description": "average taxi-in time (wheels down to parking) for each aircraft type"},
    "Q2": {"title": "Taxi-out time by hour of day", "metrics": ["taxi_out"],
           "description": "average taxi-out time (off-block to take-off) for each local hour of the day"},
    "Q3": {"title": "Movement area occupancy", "metrics": ["movement_area_peak"],
           "description": "most aircraft in the movement area at the same time, for each hour"},
    "Q4": {"title": "Runway occupancy time", "metrics": ["runway_occupancy"],
           "description": "how long aircraft stay on the runway, arrivals and departures, overall and by runway"},
    "Q5": {"title": "Take-off (wheels-up) delay", "metrics": ["takeoff_delay"],
           "description": "average delay of actual take-off compared with the scheduled take-off time"},
    "Q6": {"title": "Taxi times by weight class", "metrics": ["taxi_in", "taxi_out"],
           "description": "average taxi-in and taxi-out times by ICAO weight class (light, medium, heavy)"},
    "Q7": {"title": "Taxiway usage", "metrics": ["taxiway_usage"],
           "description": "how many flights used each taxiway or taxiway section"},
    "Q8": {"title": "Wheels-down to parking time", "metrics": ["taxi_in"],
           "description": "one overall average time from wheels down (touchdown) to parking for all arrivals"},
    "Q9": {"title": "Runway activity", "metrics": ["runway_utilization"],
           "description": "number of take-offs and landings on each runway, and which runway was used most"},
    "Q10": {"title": "Peak hours (history only)", "metrics": ["peak_hours"],
            "description": "the busiest hours of the day by number of take-offs plus landings"},
}

HOURS_CTE = "WITH RECURSIVE hours (h) AS (SELECT 0 UNION ALL SELECT h + 1 FROM hours WHERE h < 23)"


# ---- SQL ------------------------------------------------------------------------------------------------------

def _check_day(day):
    day = day or DEFAULT_DAY
    try:
        parsed = date.fromisoformat(day)
    except (TypeError, ValueError):
        raise IntentError(f"not a date: {day!r}")
    return parsed.isoformat()


def build_queries(qid, day=DEFAULT_DAY):
    """-> list of (name, sql, params). Raises IntentError for an unknown question or a bad date."""
    if qid not in QUESTIONS:
        raise IntentError(f"unknown question: {qid!r}")
    day = _check_day(day)
    next_day = (date.fromisoformat(day) + timedelta(days=1)).isoformat()
    if qid == "Q1":
        return [("by_type",
                 "SELECT aircraft_type_group, AVG(duration_min) AS avg_taxi_in_min, COUNT(*) AS flights "
                 "FROM v_taxi_in WHERE exclusion_reason IS NULL AND selection_date = %s "
                 "GROUP BY aircraft_type_group ORDER BY avg_taxi_in_min DESC, aircraft_type_group", (day,))]
    if qid == "Q2":
        return [("by_hour",
                 f"{HOURS_CTE} SELECT hours.h AS off_block_hour, AVG(t.duration_min) AS avg_taxi_out_min, "
                 "COUNT(t.flight_info_id) AS flights FROM hours LEFT JOIN v_taxi_out t ON t.selection_hour = hours.h "
                 "AND t.exclusion_reason IS NULL AND t.selection_date = %s GROUP BY hours.h ORDER BY hours.h", (day,)),
                ("overall",
                 "SELECT AVG(duration_min) AS avg_taxi_out_min, COUNT(*) AS flights FROM v_taxi_out "
                 "WHERE exclusion_reason IS NULL AND selection_date = %s", (day,))]
    if qid == "Q3":
        return [("peak_by_hour",
                 "SELECT local_hour, max_aircraft_in_area, intervals_used, intervals_excluded, excluded_missing_time, "
                 "excluded_negative_duration FROM v_movement_area_hourly_peak WHERE local_date = %s "
                 "ORDER BY local_hour", (day,)),
                ("intervals",   # intervals overlapping the day (start inclusive, end exclusive), for the sample
                 "SELECT operation, COUNT(*) AS flights FROM v_movement_area WHERE exclusion_reason IS NULL "
                 "AND start_time < %s AND end_time > %s GROUP BY operation ORDER BY operation", (next_day, day))]
    if qid == "Q4":
        return [("by_operation",
                 "SELECT operation, AVG(duration_sec) AS avg_occupancy_sec, AVG(duration_sec) / 60 AS avg_occupancy_min, "
                 "COUNT(*) AS flights FROM v_runway_occupancy WHERE exclusion_reason IS NULL AND selection_date = %s "
                 "GROUP BY operation ORDER BY operation", (day,)),
                ("by_runway",
                 "SELECT operation, runway, AVG(duration_sec) AS avg_occupancy_sec, "
                 "AVG(duration_sec) / 60 AS avg_occupancy_min, COUNT(*) AS flights FROM v_runway_occupancy "
                 "WHERE exclusion_reason IS NULL AND selection_date = %s GROUP BY operation, runway "
                 "ORDER BY operation, flights DESC, runway", (day,))]
    if qid == "Q5":
        return [("overall",
                 "SELECT AVG(delay_min) AS avg_takeoff_delay_min, COUNT(*) AS flights, "
                 "SUM(delay_min < 0) AS early_departures FROM v_takeoff_delay "
                 "WHERE exclusion_reason IS NULL AND selection_date = %s", (day,))]
    if qid == "Q6":
        out = []
        for name, view, col in (("taxi_in", "v_taxi_in", "avg_taxi_in_min"), ("taxi_out", "v_taxi_out", "avg_taxi_out_min")):
            out.append((name,
                        f"SELECT w.weight_class_group, w.label AS weight_class, AVG(t.duration_min) AS {col}, "
                        f"COUNT(t.flight_info_id) AS flights FROM v_weight_classes w LEFT JOIN {view} t "
                        "ON t.weight_class_group = w.weight_class_group AND t.exclusion_reason IS NULL "
                        "AND t.selection_date = %s GROUP BY w.weight_class_group, w.label, w.sort_order "
                        "ORDER BY w.sort_order", (day,)))
        return out
    if qid == "Q7":
        # Team rule (2026-11-14): the Port says to select by section-entry time. The export has none, so the
        # proxy selection_time from metric_rules.yaml selects the reporting day (start inclusive, end exclusive).
        # Rows with 'missing time' or 'missing segment' are excluded.
        used = "exclusion_reason IS NULL AND selection_time >= %s AND selection_time < %s"
        window = (f"{day} 00:00:00", f"{next_day} 00:00:00")
        leg = "CONCAT(flight_info_id, '-', operation)"
        return [("by_segment",
                 "SELECT REPLACE(taxiway_segment, 'TaxiwaySegment_', '') AS taxiway_section, taxiway_name, "
                 f"COUNT(DISTINCT flight_info_id, operation) AS flights FROM v_taxiway_usage WHERE {used} "
                 "GROUP BY taxiway_segment, taxiway_name ORDER BY flights DESC, taxiway_section", window),
                ("by_taxiway",
                 "SELECT taxiway_letter, taxiway_name, COUNT(DISTINCT flight_info_id, operation) AS flights "
                 f"FROM v_taxiway_usage WHERE {used} GROUP BY taxiway_letter, taxiway_name "
                 "ORDER BY flights DESC, taxiway_letter", window),
                ("total",
                 f"SELECT COUNT(DISTINCT flight_info_id, operation) AS flights FROM v_taxiway_usage WHERE {used}", window),
                ("legs",   # for the sample: how many legs have a usable row, and why the others are left out
                 f"SELECT COUNT(DISTINCT CASE WHEN exclusion_reason IS NULL THEN {leg} END) AS usable, "
                 f"COUNT(DISTINCT CASE WHEN taxiway_segment IS NOT NULL AND (exclusion_reason IS NULL "
                 f"OR exclusion_reason = 'missing time') THEN {leg} END) AS with_segment, "
                 "(SELECT COUNT(*) FROM v_runway_activity) AS all_legs FROM v_taxiway_usage", ())]
    if qid == "Q8":
        return [("overall",
                 "SELECT AVG(duration_min) AS avg_taxi_in_min, COUNT(*) AS flights FROM v_taxi_in "
                 "WHERE exclusion_reason IS NULL AND selection_date = %s", (day,))]
    if qid == "Q9":
        return [("by_runway",
                 "SELECT runway, SUM(activity = 'takeoff') AS takeoffs, SUM(activity = 'landing') AS landings, "
                 "COUNT(*) AS total_operations FROM v_runway_activity WHERE exclusion_reason IS NULL "
                 "AND selection_date = %s GROUP BY runway ORDER BY total_operations DESC, runway", (day,)),
                ("missed",
                 "SELECT runway, COUNT(*) AS missed_approaches FROM v_runway_activity WHERE is_missed_approach = 1 "
                 "AND selection_date = %s GROUP BY runway ORDER BY runway", (day,))]
    # Q10 (team rule, 2026-11-14): v_peak_hours, i.e. all take-offs + completed landings; a runway is not needed,
    # so the take-off with no runway counts. All 24 hours are listed (empty hours = 0) and ties share a rank.
    return [("by_hour",
             f"{HOURS_CTE} SELECT hours.h AS local_hour, COALESCE(p.takeoffs, 0) AS takeoffs, "
             "COALESCE(p.landings, 0) AS landings, COALESCE(p.operations, 0) AS operations, "
             "RANK() OVER (ORDER BY COALESCE(p.operations, 0) DESC) AS hour_rank "
             "FROM hours LEFT JOIN v_peak_hours p ON p.local_hour = hours.h AND p.local_date = %s "
             "ORDER BY hours.h", (day,)),
            ("missed",
             "SELECT COUNT(*) AS missed_approaches FROM v_runway_activity WHERE is_missed_approach = 1 "
             "AND selection_date = %s", (day,))]


# ---- formatting -----------------------------------------------------------------------------------------------

def _num(v):
    """Decimal/int/float -> float or int for JSON; None stays None."""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return int(v) if v == v.to_integral_value() and v.as_tuple().exponent >= 0 else float(v)
    return v


def clean(rows):
    return [{k: _num(v) for k, v in r.items()} for r in rows]


def r2(v):
    """Round half up to 2 decimals, for the text only (SQL keeps full precision)."""
    if v is None:
        return "No data"
    return str(Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def n(v):
    return f"{int(v or 0):,}"


def hour_label(h):
    return f"{int(h):02d}:00"


def _table(rows, columns, headers=None):
    headers = headers or columns
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for r in rows:
        cells = []
        for c in columns:
            v = r.get(c)
            if c.startswith("avg_"):
                cells.append(r2(v))
            elif c in ("off_block_hour", "local_hour"):
                cells.append(hour_label(v))
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                cells.append(n(v))
            else:
                cells.append("No data" if v is None else str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _chart(kind, title, labels, datasets, y_label):
    colors = ["rgba(59, 130, 246, 0.7)", "rgba(16, 185, 129, 0.7)", "rgba(245, 158, 11, 0.7)"]
    return {
        "type": kind, "title": title,
        "data": {"labels": labels, "datasets": [
            {"label": label, "data": data, "backgroundColor": colors[i % 3],
             "borderColor": colors[i % 3].replace("0.7", "1"), "borderWidth": 2,
             "tension": 0.4 if kind == "line" else 0, "fill": False}
            for i, (label, data) in enumerate(datasets)]},
        "options": {"responsive": True, "scales": {"y": {"beginAtZero": True,
                                                          "title": {"display": True, "text": y_label}}}},
    }


def _definitions(qid):
    """[(metric name, definition)] from metric_rules.yaml, labelled the way views_mode.build_answer labels them."""
    metrics = (views_mode.metric_rules() or {}).get("metrics", {})
    return [(m.replace("_", " "), metrics[m]["definition"].strip()) for m in QUESTIONS[qid]["metrics"] if m in metrics]


def _flight_sample(run, view, day, noun):
    """'528 of 535 departures (excluded: 7 outside the reporting day)' and the numbers behind it."""
    tot = run(f"SELECT COUNT(*) AS total, SUM(exclusion_reason IS NULL AND selection_date = %s) AS used, "
              f"SUM(exclusion_reason IS NULL AND (selection_date IS NULL OR selection_date <> %s)) AS outside "
              f"FROM {view}", (day, day))[0]
    reasons = run(f"SELECT exclusion_reason AS reason, COUNT(*) AS n FROM {view} WHERE exclusion_reason IS NOT NULL "
                  f"GROUP BY exclusion_reason ORDER BY exclusion_reason")
    excluded = {r["reason"]: int(r["n"]) for r in reasons}
    if int(tot["outside"] or 0):
        excluded["outside the reporting day"] = int(tot["outside"])
    used, total = int(tot["used"] or 0), int(tot["total"] or 0)
    text = f"{used:,} of {total:,} {noun}"
    text += " (excluded: " + ", ".join(f"{k} {v:,}" for k, v in excluded.items()) + ")" if excluded else " (none excluded)"
    return text, used, excluded


# ---- answers --------------------------------------------------------------------------------------------------

def _show(sql, params):
    """SQL text for display only (the query itself runs with %s parameters): each %s replaced by its value, in order."""
    parts = sql.split("%s")
    out = parts[0]
    for value, rest in zip(params, parts[1:]):
        out += f"'{value}'" + rest
    return out


def footer(has_averages):
    """Last line of every answer; the rounding note only when the answer shows averages."""
    return "_Times are SEA local (PDT)." + (" Averages are rounded to 2 decimals._" if has_averages else "_")


def answer(qid, run, day=DEFAULT_DAY):
    """Run the templates for one question. run(sql, params) -> list of dict rows (read-only connection).

    Returns {answer, data, chart, sql_queries, metric, definition, included_count, excluded}.
    """
    queries = build_queries(qid, day)
    day = _check_day(day)
    sql_queries = [_show(sql, params) for _, sql, params in queries]
    if day not in AVAILABLE_DAYS:
        return {"answer": f"**No data for {day}.** The data covers one operating day at SEA: {DEFAULT_DAY}. "
                          f"Ask about {DEFAULT_DAY}, or leave the date out.",
                "data": [], "chart": None, "sql_queries": sql_queries, "metric": QUESTIONS[qid]["title"],
                "definition": " ".join(d for _, d in _definitions(qid)), "included_count": 0, "excluded": {}}
    res = {name: clean(run(sql, params)) for name, sql, params in queries}
    built = BUILDERS[qid](res, run, day)
    definitions = _definitions(qid)
    # Same layout as views_mode.build_answer (answer, table, Sample, Definition, notes, footer),
    # plus the one headline sentence the Stage 2 guide asks for.
    parts = [f"**Answer:** {built['headline'].strip()}"]
    for table in built.get("tables", []):
        rows = sum(1 for line in table.splitlines() if line.startswith("|")) - 2  # minus header and --- line
        parts.append(f"**Answer** ({rows} rows):\n\n{table}")
    parts.append(f"**Sample:** based on {built['sample']}.")
    parts += [f"**Definition ({name}):** {d}" for name, d in definitions]
    parts += [f"_Note: {x}_" for x in built.get("notes", [])]
    has_averages = (any(k.startswith("avg_") for row in built["data"] for k in row)
                    or any("Avg" in t for t in built.get("tables", [])))
    parts.append(footer(has_averages))
    return {"answer": "\n\n".join(parts), "data": built["data"], "chart": built.get("chart"),
            "sql_queries": sql_queries, "metric": QUESTIONS[qid]["title"],
            "definition": " ".join(d for _, d in definitions),
            "included_count": built["included"], "excluded": built.get("excluded", {})}


def _q1(res, run, day):
    rows = res["by_type"]
    sample, used, excluded = _flight_sample(run, "v_taxi_in", day, "arrivals")
    if not rows:
        return {"headline": "No data: no arrivals on this day.", "data": [], "sample": sample, "included": 0}
    top, low = rows[0], rows[-1]
    big = [r for r in rows if r["flights"] >= 10]
    head = (f"Longest average taxi-in: **{top['aircraft_type_group']} {r2(top['avg_taxi_in_min'])} min** "
            f"({n(top['flights'])} flight{'s' if top['flights'] != 1 else ''}). ")
    if big and big[0] is not top:
        head += (f"Among types with 10 or more flights, the longest is **{big[0]['aircraft_type_group']} "
                 f"{r2(big[0]['avg_taxi_in_min'])} min** ({n(big[0]['flights'])} flights). ")
    head += f"Shortest: **{low['aircraft_type_group']} {r2(low['avg_taxi_in_min'])} min** ({n(low['flights'])} flights)."
    notes = []
    if any(r["flights"] == 1 for r in rows):
        notes.append("Groups with only 1 flight may not be representative.")
    if any(r["aircraft_type_group"] == "Unknown" for r in rows):
        notes.append("'Unknown' is an arrival with no FAA aircraft type in the data; it is kept as its own group.")
    chart = _chart("bar", "Average taxi-in time by aircraft type", [r["aircraft_type_group"] for r in rows],
                   [("Average taxi-in (min)", [r["avg_taxi_in_min"] for r in rows])], "Minutes")
    return {"headline": head, "tables": [_table(rows, ["aircraft_type_group", "avg_taxi_in_min", "flights"],
                                                ["Aircraft type", "Avg taxi-in (min)", "Flights"])],
            "data": rows, "chart": chart, "sample": sample, "included": used, "excluded": excluded, "notes": notes}


def _q2(res, run, day):
    rows, overall = res["by_hour"], res["overall"][0]
    sample, used, excluded = _flight_sample(run, "v_taxi_out", day, "departures")
    have = [r for r in rows if r["flights"]]
    empty = [hour_label(r["off_block_hour"]) for r in rows if not r["flights"]]
    head = f"Overall average taxi-out: **{r2(overall['avg_taxi_out_min'])} min** over {n(overall['flights'])} departures."
    if have:
        hi = max(have, key=lambda r: r["avg_taxi_out_min"])
        head += f" Longest hour: **{hour_label(hi['off_block_hour'])}** ({r2(hi['avg_taxi_out_min'])} min, {n(hi['flights'])} flights)."
        big = [r for r in have if r["flights"] >= 10]
        if big:
            lo = min(big, key=lambda r: r["avg_taxi_out_min"])
            head += (f" Shortest hour with 10 or more flights: **{hour_label(lo['off_block_hour'])}** "
                     f"({r2(lo['avg_taxi_out_min'])} min, {n(lo['flights'])} flights).")
    if empty:
        head += f" No data (no departures): {', '.join(empty)}."
    notes = ["Hours are the local hour the aircraft left parking (off-block), not the take-off hour.",
             "Provisional: off-block time is Aerobahn's Actual Off Block Time (the team's working assumption); "
             "awaiting Port confirmation."]
    chart = _chart("line", "Average taxi-out time by hour of off-block", [hour_label(r["off_block_hour"]) for r in rows],
                   [("Average taxi-out (min)", [r["avg_taxi_out_min"] for r in rows])], "Minutes")
    return {"headline": head, "tables": [_table(rows, ["off_block_hour", "avg_taxi_out_min", "flights"],
                                                ["Hour (off-block)", "Avg taxi-out (min)", "Flights"])],
            "data": rows, "chart": chart, "sample": sample, "included": used, "excluded": excluded, "notes": notes}


def _q3(res, run, day):
    rows = res["peak_by_hour"]
    if not rows:
        return {"headline": "No data for this day.", "data": [], "sample": "no intervals", "included": 0}
    ranked = sorted(rows, key=lambda r: (-r["max_aircraft_in_area"], r["local_hour"]))
    top, nxt = ranked[0], ranked[1:3]
    quiet = min(rows, key=lambda r: (r["max_aircraft_in_area"], r["local_hour"]))
    head = (f"Busiest: the **{hour_label(top['local_hour'])} hour, with {top['max_aircraft_in_area']} aircraft** in the "
            f"movement area at the same time. Next: " + ", ".join(f"{hour_label(r['local_hour'])} ({r['max_aircraft_in_area']})"
                                                               for r in nxt)
            + f". Quietest: {hour_label(quiet['local_hour'])} ({quiet['max_aircraft_in_area']}).")
    used, exc = rows[0]["intervals_used"], rows[0]["intervals_excluded"]
    ops = {r["operation"]: r["flights"] for r in res["intervals"]}
    sample = (f"{n(used)} aircraft intervals ({', '.join(f'{n(v)} {k.lower()}s' for k, v in ops.items())}), "
              f"{n(exc)} excluded (missing time {n(rows[0]['excluded_missing_time'])})")
    data = [{"local_hour": r["local_hour"], "max_aircraft_in_area": r["max_aircraft_in_area"]} for r in rows]
    notes = ["This is the highest number of aircraft present at the same moment, not the number of aircraft "
             "that passed through during the hour.",
             "Provisional: the hatched movement-area boundary is mapped to the export's Movement Area "
             "Entrance/Exit times (working assumption); awaiting Port confirmation."]
    chart = _chart("bar", "Peak aircraft in the movement area, by hour",
                   [hour_label(r["local_hour"]) for r in rows], [("Aircraft at once", [r["max_aircraft_in_area"] for r in rows])],
                   "Aircraft")
    return {"headline": head, "tables": [_table(data, ["local_hour", "max_aircraft_in_area"], ["Hour", "Most aircraft at once"])],
            "data": data, "chart": chart, "sample": sample, "included": used, "excluded": {"missing time": exc}, "notes": notes}


def _q4(res, run, day):
    ops, runways = res["by_operation"], res["by_runway"]
    sample, used, excluded = _flight_sample(run, "v_runway_occupancy", day, "arrivals and departures")
    head = " ".join(f"{r['operation']}s: **{r2(r['avg_occupancy_min'])} min** ({r2(r['avg_occupancy_sec'])} seconds), "
                    f"{n(r['flights'])} flights." for r in ops)
    notes = ["Arrivals and departures are measured from different events, so they are shown separately.",
             "Clear Active is not used (Port instruction), so this differs from the export's own Runway Occupancy Time column."]
    labels = [f"{r['operation'][:3]} {r['runway']}" for r in runways]
    chart = _chart("bar", "Average runway occupancy by runway", labels,
                   [("Average occupancy (s)", [r["avg_occupancy_sec"] for r in runways])], "Seconds")
    tables = [_table(ops, ["operation", "avg_occupancy_min", "avg_occupancy_sec", "flights"],
                     ["Operation", "Avg (min)", "Avg (s)", "Flights"]),
              "**By runway:**\n\n" + _table(runways, ["operation", "runway", "avg_occupancy_min", "avg_occupancy_sec", "flights"],
                                             ["Operation", "Runway", "Avg (min)", "Avg (s)", "Flights"])]
    return {"headline": head, "tables": tables, "data": runways, "chart": chart, "sample": sample,
            "included": used, "excluded": excluded, "notes": notes}


def _q5(res, run, day):
    r = res["overall"][0]
    sample, used, excluded = _flight_sample(run, "v_takeoff_delay", day, "departures")
    avg = r["avg_takeoff_delay_min"]
    late = "late" if avg is not None and avg >= 0 else "early"
    head = (f"Average take-off delay: **{r2(abs(avg)) if avg is not None else 'No data'} minutes {late}** "
            f"compared with the scheduled take-off time, over {n(r['flights'])} departures. "
            f"{n(r['early_departures'])} departures took off early; they are kept (no delay threshold).")
    notes = []
    if "missing scheduled take-off" in excluded:
        notes.append("Departures with no scheduled take-off time can't be calculated and are excluded "
                     "(scheduled off-block is never used in its place).")
    return {"headline": head, "data": [r], "sample": sample, "included": used, "excluded": excluded, "notes": notes}


def _q6(res, run, day):
    t_in, t_out = res["taxi_in"], res["taxi_out"]
    s_in, u_in, e_in = _flight_sample(run, "v_taxi_in", day, "arrivals")
    s_out, u_out, e_out = _flight_sample(run, "v_taxi_out", day, "departures")
    # ICAO also has Super (J); this data has none, so it is listed as No data like any empty class.
    super_row = {"weight_class_group": "J", "weight_class": "Super", "flights": 0}
    t_in = t_in[:3] + [dict(super_row, avg_taxi_in_min=None)] + t_in[3:]
    t_out = t_out[:3] + [dict(super_row, avg_taxi_out_min=None)] + t_out[3:]

    def part(rows, col):
        return ", ".join(f"{r['weight_class']} **{r2(r[col])} min** ({n(r['flights'])})" for r in rows if r["flights"])

    empty = [r["weight_class"] for r in t_in if not r["flights"]]
    head = (f"Taxi-in (arrivals): {part(t_in, 'avg_taxi_in_min')}. Taxi-out (departures): {part(t_out, 'avg_taxi_out_min')}."
            + (f" No data: {', '.join(empty)}." if empty else ""))
    data = [{"weight_class": a["weight_class"], "avg_taxi_in_min": a["avg_taxi_in_min"], "arrivals": a["flights"],
             "avg_taxi_out_min": b["avg_taxi_out_min"], "departures": b["flights"]} for a, b in zip(t_in, t_out)]
    notes = ["Weight class is the ICAO classification (Weight Class (ICAO)). Arrival and departure averages are shown separately.",
             "Taxi-out uses the Q2 interval (off-block to take-off; off-block source pending Port confirmation)."]
    if any(r["flights"] and r["flights"] < 10 for r in t_in + t_out):
        notes.append("Some classes have fewer than 10 flights and may not be representative.")
    shown = [r for r in data if r["arrivals"] or r["departures"]]
    chart = _chart("bar", "Average taxi times by ICAO weight class", [r["weight_class"] for r in shown],
                   [("Taxi-in (min)", [r["avg_taxi_in_min"] for r in shown]),
                    ("Taxi-out (min)", [r["avg_taxi_out_min"] for r in shown])], "Minutes")
    return {"headline": head, "tables": [_table(data, ["weight_class", "avg_taxi_in_min", "arrivals", "avg_taxi_out_min", "departures"],
                                                ["Weight class", "Avg taxi-in (min)", "Arrivals", "Avg taxi-out (min)", "Departures"])],
            "data": data, "chart": chart, "sample": f"taxi-in {s_in}; taxi-out {s_out}", "included": u_in + u_out,
            "excluded": {"taxi-in": e_in, "taxi-out": e_out}, "notes": notes}


def _q7(res, run, day):
    seg, twy = res["by_segment"], res["by_taxiway"]
    total, lg = res["total"][0]["flights"], res["legs"][0]
    legs = lg["all_legs"]
    excluded = {"outside the reporting day": lg["usable"] - total,
                "missing time": lg["with_segment"] - lg["usable"],
                "no taxiway recorded": legs - lg["with_segment"]}
    excluded = {k: v for k, v in excluded.items() if v}
    head = ("Most used taxiway section: **" + seg[0]["taxiway_section"] + f" ({n(seg[0]['flights'])} flights)**, then "
            + ", ".join(f"{r['taxiway_section']} ({n(r['flights'])})" for r in seg[1:4])
            + f". Most used taxiway: **{twy[0]['taxiway_name']} ({twy[0]['taxiway_letter']}), {n(twy[0]['flights'])} flights**."
            if seg else "No taxiway use recorded.")
    sample = (f"{n(total)} of {n(legs)} flight legs"
              + (" (excluded: " + ", ".join(f"{k} {n(v)}" for k, v in excluded.items()) + ")" if excluded else "")
              + f"; {len(seg)} sections")
    notes = ["Each flight is counted once per section, even if it used that section more than once.",
             "Tango (T), Hotel (H) and Whiskey (W) do not appear in this data: the export only records the section used "
             "to enter or exit the runway and the ramp, not the full taxi route.",
             "Provisional: the export has no per-section entry time, so the reporting day is selected by a proxy time "
             "(runway or movement-area entry/exit); awaiting Port confirmation. The missed approach is not included."]
    chart = _chart("bar", "Flights per taxiway section (top 15)", [r["taxiway_section"] for r in seg[:15]],
                   [("Flights", [r["flights"] for r in seg[:15]])], "Flights")
    tables = [_table(twy, ["taxiway_name", "taxiway_letter", "flights"], ["Taxiway", "Letter", "Flights"]),
              "**By section:**\n\n" + _table(seg, ["taxiway_section", "taxiway_name", "flights"], ["Section", "Taxiway", "Flights"])]
    return {"headline": head, "tables": tables, "data": seg, "chart": chart, "sample": sample, "included": total,
            "excluded": excluded, "notes": notes}


def _q8(res, run, day):
    r = res["overall"][0]
    sample, used, excluded = _flight_sample(run, "v_taxi_in", day, "arrivals")
    head = (f"Average time from wheels down to parking: **{r2(r['avg_taxi_in_min'])} minutes**, "
            f"one overall average across {n(r['flights'])} arrivals.")
    return {"headline": head, "data": [r], "sample": sample, "included": used, "excluded": excluded,
            "notes": ["For the breakdown by aircraft type, ask for taxi-in time by aircraft type."]}


def _q9(res, run, day):
    rows, missed = res["by_runway"], res["missed"]
    sample, used, excluded = _flight_sample(run, "v_runway_activity", day, "take-offs, landings and missed approaches")
    tk, ld = sum(r["takeoffs"] for r in rows), sum(r["landings"] for r in rows)
    head = (f"Most used runway: **{rows[0]['runway']}, {n(rows[0]['total_operations'])} operations** "
            f"({n(rows[0]['takeoffs'])} take-offs + {n(rows[0]['landings'])} landings). "
            f"In total: {n(tk)} take-offs and {n(ld)} completed landings ({n(tk + ld)} operations)." if rows else "No data.")
    if missed:
        head += " Missed approaches, reported separately: " + ", ".join(
            f"**{n(m['missed_approaches'])} on {m['runway']}**" for m in missed) + "."
    notes = ["Take-offs are counted at wheels up and landings at wheels down. Missed approaches are not completed landings."]
    if "missing runway" in excluded:
        notes.append("Operations with no runway recorded are left out of the per-runway counts.")
    chart = _chart("bar", "Take-offs and landings by runway", [r["runway"] for r in rows],
                   [("Take-offs", [r["takeoffs"] for r in rows]), ("Landings", [r["landings"] for r in rows])], "Operations")
    return {"headline": head, "tables": [_table(rows, ["runway", "takeoffs", "landings", "total_operations"],
                                                ["Runway", "Take-offs", "Landings", "Total"])],
            "data": rows, "chart": chart, "sample": sample, "included": used, "excluded": excluded, "notes": notes}


def _q10(res, run, day):
    rows = res["by_hour"]
    used = sum(r["operations"] for r in rows)
    missed = int(res["missed"][0]["missed_approaches"] or 0)
    excluded = {"missed approach": missed} if missed else {}
    sample = (f"{n(used)} take-offs and completed landings"
              + (f" (excluded: missed approach {n(missed)})" if missed else " (none excluded)"))
    ranked = sorted(rows, key=lambda r: (r["hour_rank"], r["local_hour"]))
    top = ranked[0]

    def span(h):
        return f"{int(h):02d}:00–{int(h):02d}:59"

    head = (f"Busiest hour: **{span(top['local_hour'])}, {n(top['operations'])} operations** "
            f"({n(top['takeoffs'])} take-offs + {n(top['landings'])} landings). Top hours: "
            + ", ".join(f"#{r['hour_rank']} {hour_label(r['local_hour'])} ({n(r['operations'])})" for r in ranked[:6]) + ".")
    ties = {}
    for r in rows:
        ties.setdefault(r["hour_rank"], []).append(r)
    tied = [v for k, v in sorted(ties.items()) if len(v) > 1 and v[0]["operations"]]
    if tied:
        head += " Tied hours share a rank: " + "; ".join(
            " & ".join(hour_label(r["local_hour"]) for r in v) + f" ({n(v[0]['operations'])}, rank {v[0]['hour_rank']})"
            for v in tied) + "."
    notes = ["History only: this describes past activity on one day and is not a forecast.",
             "Every take-off and completed landing counts, including a take-off with no runway recorded (a runway is "
             "not needed for this count), so the total can be higher than in runway activity. The missed approach is "
             "not counted."]
    chart = _chart("bar", "Take-offs plus landings by hour", [hour_label(r["local_hour"]) for r in rows],
                   [("Take-offs", [r["takeoffs"] for r in rows]), ("Landings", [r["landings"] for r in rows])], "Operations")
    return {"headline": head, "tables": [_table(ranked, ["hour_rank", "local_hour", "takeoffs", "landings", "operations"],
                                                ["Rank", "Hour", "Take-offs", "Landings", "Total"])],
            "data": rows, "chart": chart, "sample": sample, "included": used, "excluded": excluded, "notes": notes}


BUILDERS = {"Q1": _q1, "Q2": _q2, "Q3": _q3, "Q4": _q4, "Q5": _q5, "Q6": _q6, "Q7": _q7, "Q8": _q8, "Q9": _q9, "Q10": _q10}
