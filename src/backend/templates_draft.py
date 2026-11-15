"""
Draft SQL templates for Stage 2 (QUERY_MODE=templates).

Gemini returns an intent such as:
    {"metric": "taxi_in", "group_by": "aircraft_type", "filters": {"hour_from": 6, "hour_to": 9}}

build_query(intent) turns it into SQL using ONLY pre-written pieces:
- the view and the value expression come from METRICS (never from the AI)
- group_by keys map to a whitelist of column names
- filter values are passed as query parameters (%s), never pasted into the SQL
- only rows with exclusion_reason IS NULL are used
- ORDER BY is fixed, so the same intent always gives the same SQL and the same row order

Values come back at full precision. Round to 2 decimals only when displaying
(the Port's rule: calculate at full precision, display 2 decimals).

DRAFT: review with the team, then test every template against the ground truth.
"""


class IntentError(ValueError):
    """The intent can't be served by a template. The caller falls back to Stage 1 (views mode)."""


# Filters most metrics can use: name -> (SQL condition with %s, type of the value)
COMMON_FILTERS = {
    "hour_from": ("selection_hour >= %s", int),     # a window includes its start...
    "hour_to": ("selection_hour < %s", int),        # ...and excludes its end
    "date": ("selection_date = %s", str),
    "runway": ("runway = %s", str),
    "aircraft_type": ("aircraft_type_group = %s", str),
}

METRICS = {
    # Q1 (by aircraft type), Q6 (by weight class), Q8 (overall)
    "taxi_in": {
        "view": "v_taxi_in",
        "value": "AVG(duration_sec) / 60",
        "value_name": "avg_taxi_in_min",
        "unit": "min",
        "group_by": {"aircraft_type": "aircraft_type_group", "weight_class": "weight_class_group",
                     "runway": "runway", "hour": "selection_hour", "carrier": "carrier"},
        "filters": {**COMMON_FILTERS, "weight_class": ("weight_class_group = %s", str),
                    "carrier": ("carrier = %s", str)},
    },
    # Q5 (overall). Negative values = early departures, and they are kept.
    "takeoff_delay": {
        "view": "v_takeoff_delay",
        "value": "AVG(delay_sec) / 60",
        "value_name": "avg_delay_min",
        "unit": "min",
        "group_by": {"aircraft_type": "aircraft_type_group", "carrier": "carrier",
                     "runway": "runway", "hour": "selection_hour"},
        "filters": {**COMMON_FILTERS, "carrier": ("carrier = %s", str)},
    },
    # Q4. Arrivals and departures are always reported separately.
    "runway_occupancy": {
        "view": "v_runway_occupancy",
        "value": "AVG(duration_sec)",
        "value_name": "avg_occupancy_sec",
        "unit": "sec",
        "always_group": ["operation"],
        "group_by": {"runway": "runway", "aircraft_type": "aircraft_type_group", "hour": "selection_hour"},
        "filters": {**COMMON_FILTERS, "operation": ("operation = %s", str)},
    },
}

RUNWAY_ACTIVITY_FILTERS = {k: COMMON_FILTERS[k] for k in ("hour_from", "hour_to", "date", "runway")}


def _where(filters, allowed, prefix=""):
    """Turn whitelisted filters into ' AND ...' conditions plus a list of parameter values."""
    clauses, params = [], []
    for name, value in (filters or {}).items():
        if name not in allowed:
            raise IntentError(f"filter '{name}' is not supported for this metric")
        condition, cast = allowed[name]
        try:
            value = cast(value)
        except (TypeError, ValueError):
            raise IntentError(f"filter '{name}' has an invalid value")
        if name in ("hour_from", "hour_to") and not 0 <= value <= 24:
            raise IntentError("hours must be between 0 and 24")
        clauses.append(prefix + condition)
        params.append(value)
    return "".join(" AND " + c for c in clauses), params


def _sample_query(view, where, params, prefix=""):
    """Counts for the 'based on X of Y' sentence, using the same filters but ignoring the exclusion rule."""
    return {
        "sql": f"SELECT COUNT(*) AS total, SUM(exclusion_reason IS NULL) AS used FROM {view} WHERE 1=1{where}",
        "reasons_sql": (f"SELECT exclusion_reason AS reason, COUNT(*) AS n FROM {view} WHERE exclusion_reason "
                        f"IS NOT NULL{where} GROUP BY exclusion_reason ORDER BY exclusion_reason"),
        "params": params,
    }


def _taxi_in_by_weight_class(intent):
    """Q6: LEFT JOIN the fixed class list, so an empty class (Light) shows NULL -> 'No data', never 0."""
    where, params = _where(intent.get("filters"), METRICS["taxi_in"]["filters"], prefix="t.")
    sql = ("SELECT w.label AS weight_class, AVG(t.duration_sec) / 60 AS avg_taxi_in_min, "
           "COUNT(t.flight_info_id) AS flights "
           "FROM v_weight_classes w LEFT JOIN v_taxi_in t "
           f"ON t.weight_class_group = w.weight_class_group AND t.exclusion_reason IS NULL{where} "
           "GROUP BY w.weight_class_group, w.label, w.sort_order ORDER BY w.sort_order")
    plain_where, _ = _where(intent.get("filters"), METRICS["taxi_in"]["filters"])
    return {"metric": "taxi_in", "unit": "min", "sql": sql, "params": params,
            "sample": _sample_query("v_taxi_in", plain_where, params)}


def _runway_utilization(intent):
    """Q9: takeoffs, completed landings and total per runway, plus a separate missed-approach count."""
    where, params = _where(intent.get("filters"), RUNWAY_ACTIVITY_FILTERS)
    sql = ("SELECT runway, SUM(activity = 'takeoff') AS takeoffs, SUM(activity = 'landing') AS landings, "
           f"COUNT(*) AS total FROM v_runway_activity WHERE exclusion_reason IS NULL{where} "
           "GROUP BY runway ORDER BY total DESC, runway")
    missed = f"SELECT COUNT(*) AS missed_approaches FROM v_runway_activity WHERE is_missed_approach = 1{where}"
    return {"metric": "runway_utilization", "unit": "flights", "sql": sql, "params": params,
            "extra": {"missed_approaches": {"sql": missed, "params": params}},
            "sample": _sample_query("v_runway_activity", where, params)}


def build_query(intent):
    """intent -> {'sql', 'params', 'sample', ...}. Raises IntentError if no template fits."""
    metric = intent.get("metric")
    group_key = intent.get("group_by")
    if metric == "runway_utilization":
        return _runway_utilization(intent)
    if metric == "taxi_in" and group_key == "weight_class":
        return _taxi_in_by_weight_class(intent)
    m = METRICS.get(metric)
    if m is None:
        raise IntentError(f"no template for metric '{metric}'")

    group_cols = list(m.get("always_group", []))
    if group_key:
        if group_key not in m["group_by"]:
            raise IntentError(f"'{metric}' can't be grouped by '{group_key}'")
        group_cols.append(m["group_by"][group_key])

    where, params = _where(intent.get("filters"), m["filters"])
    select = ", ".join(group_cols + [f"{m['value']} AS {m['value_name']}", "COUNT(*) AS flights"])
    sql = f"SELECT {select} FROM {m['view']} WHERE exclusion_reason IS NULL{where}"
    if group_cols:
        fixed = list(m.get("always_group", []))                 # e.g. arrivals before departures
        if group_key == "hour":
            order = ", ".join(group_cols)                        # hours in clock order
        else:
            order = ", ".join(fixed + [f"{m['value_name']} DESC"] + [c for c in group_cols if c not in fixed])
        sql += " GROUP BY " + ", ".join(group_cols) + " ORDER BY " + order
    return {"metric": metric, "unit": m["unit"], "sql": sql, "params": params,
            "sample": _sample_query(m["view"], where, params)}


if __name__ == "__main__":
    # Print the SQL for the midterm questions (no database needed).
    examples = {
        "Q1": {"metric": "taxi_in", "group_by": "aircraft_type"},
        "Q8": {"metric": "taxi_in"},
        "Q6": {"metric": "taxi_in", "group_by": "weight_class"},
        "Q5": {"metric": "takeoff_delay"},
        "Q4": {"metric": "runway_occupancy", "group_by": "runway"},
        "Q9": {"metric": "runway_utilization"},
        "Q1, 6-9 AM": {"metric": "taxi_in", "group_by": "aircraft_type", "filters": {"hour_from": 6, "hour_to": 9}},
    }
    for name, intent in examples.items():
        q = build_query(intent)
        print(f"{name}:\n  {q['sql']}\n  params: {q['params']}\n")
