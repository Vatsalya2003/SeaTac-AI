"""
Independent recalculation of every `seatac` view from the Excel export, following docs/CLIENT_CONFIRMED_RULES.md.

Uses only pandas and the export's original column names. It does not read the database, the loader or the view
SQL, so a mistake in any of them shows up as a mismatch. Each view's expected rows are a dict keyed like the view:
(flight_info_id, operation), (flight_info_id, operation, segment_role) or (local_date, local_hour).
"""
import re
from collections import Counter

import pandas as pd

ARRIVAL, DEPARTURE, MISSED_APPROACH = "Arrival", "Departure", "Missed Approach"
TIMES = {  # SEA-side timestamps used by the rules -> Excel column
    "wheels_down": "Wheels Down (PDT)",
    "in_block": "Actual In Block Time (Aerobahn) (PDT)",
    "off_block": "Actual Off Block Time (Aerobahn) (PDT)",  # Q2 source confirmed by the Port: Aerobahn
    "wheels_up": "Wheels Up (PDT)",
    "scheduled_take_off": "Scheduled Take Off Time (Aerobahn) (PDT)",
    "runway_entrance": "Runway Entrance Time (PDT)",
    "runway_exit": "Runway Exit Time (PDT)",
    "movement_area_entrance": "Movement Area Entrance Time (PDT)",
    "movement_area_exit": "Movement Area Exit Time (PDT)",
    "event_time": "Event Time (PDT)",
}
TEXT = {"weight_class": "Weight Class (ICAO)", "aircraft_type": "Aircraft Type (FAA)", "runway": "Runway",
        "taxiway_runway": "Taxiway Used to Enter/Exit Runway", "taxiway_ramp": "Taxiway Used to Enter/Exit Ramp"}
PHONETIC = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                    "Alpha Bravo Charlie Delta Echo Foxtrot Golf Hotel India Juliet Kilo Lima Mike November Oscar "
                    "Papa Quebec Romeo Sierra Tango Uniform Victor Whiskey X-ray Yankee Zulu".split()))


def _value(v):
    if v is None or (not isinstance(v, str) and pd.isna(v)):
        return None
    return v.to_pydatetime() if isinstance(v, pd.Timestamp) else v


def legs(excel):
    """One dict per row of the export: key, operation and the fields the rules need."""
    out = []
    for _, r in excel.iterrows():
        leg = {"key": (int(r["Flight Info ID"]), r["Operation"]), "operation": r["Operation"]}
        leg.update({k: _value(r[c]) for k, c in TIMES.items()})
        leg.update({k: _value(r[c]) for k, c in TEXT.items()})
        out.append(leg)
    return out


def _aircraft(leg):  # views grouped by aircraft type: a leg with no FAA type goes in an 'Unknown' group
    return {"aircraft_type_group": leg["aircraft_type"] or "Unknown"}


def _selection(t):
    return {"selection_date": t.date() if t else None, "selection_hour": t.hour if t else None}


def _interval(start, end, selection):
    """Confirmed rule: missing endpoint or negative elapsed time -> excluded, with the reason."""
    if start is None or end is None:
        reason, seconds = "missing time", None
    else:
        seconds = int((end - start).total_seconds())
        reason = "negative duration" if seconds < 0 else None
    return {"duration_sec": seconds, "exclusion_reason": reason, "included": int(reason is None), **_selection(selection)}


def taxi_in(all_legs):  # Q1, Q6, Q8: wheels down -> in-block, selected by wheels down
    return {l["key"]: {**_interval(l["wheels_down"], l["in_block"], l["wheels_down"]),
                       "weight_class_group": l["weight_class"] or "Unknown", **_aircraft(l)}
            for l in all_legs if l["operation"] == ARRIVAL}


def taxi_out(all_legs):  # Q2, Q6: off-block -> wheels up, selected by off-block
    return {l["key"]: {**_interval(l["off_block"], l["wheels_up"], l["off_block"]),
                       "weight_class_group": l["weight_class"] or "Unknown", **_aircraft(l)}
            for l in all_legs if l["operation"] == DEPARTURE}


def movement_area(all_legs):  # Q3: arrivals touchdown -> area exit; departures area entry -> take-off
    out = {}
    for l in all_legs:
        if l["operation"] == ARRIVAL:
            out[l["key"]] = {**_interval(l["wheels_down"], l["movement_area_exit"], l["wheels_down"]),
                             "start": l["wheels_down"], "end": l["movement_area_exit"], **_aircraft(l)}
        elif l["operation"] == DEPARTURE:
            out[l["key"]] = {**_interval(l["movement_area_entrance"], l["wheels_up"], l["movement_area_entrance"]),
                             "start": l["movement_area_entrance"], "end": l["wheels_up"], **_aircraft(l)}
    return out


def movement_area_hourly_peak(ma):
    """Q3 peak, by brute force (not a sweep): in each local hour, the most aircraft present at once.
    An aircraft is present at t when start <= t < end. Within hour [h, h+1) the count can only rise at h itself
    or at an entry, so the maximum is taken over those moments."""
    used = [(r["start"], r["end"]) for r in ma.values() if r["included"]]
    reasons = Counter(r["exclusion_reason"] for r in ma.values() if not r["included"])
    totals = {"intervals_used": len(used), "intervals_excluded": sum(reasons.values()),
              "excluded_missing_time": reasons["missing time"], "excluded_negative_duration": reasons["negative duration"]}
    present = lambda t: sum(s <= t < e for s, e in used)
    hour = min(s for s, _ in used).replace(minute=0, second=0, microsecond=0)
    last = max(e for _, e in used)
    out = {}
    while hour <= last:
        nxt = hour + pd.Timedelta(hours=1)
        moments = [hour] + [s for s, _ in used if hour <= s < nxt]
        out[(hour.date(), hour.hour)] = {"max_aircraft_in_area": max(present(t) for t in moments), **totals}
        hour = nxt
    return out


def runway_occupancy(all_legs):  # Q4: arrivals touchdown -> runway exit; departures runway entry -> take-off
    out = {}
    for l in all_legs:
        if l["operation"] == ARRIVAL:
            out[l["key"]] = {**_interval(l["wheels_down"], l["runway_exit"], l["wheels_down"]), **_aircraft(l)}
        elif l["operation"] == DEPARTURE:
            out[l["key"]] = {**_interval(l["runway_entrance"], l["wheels_up"], l["runway_entrance"]), **_aircraft(l)}
    return out


def takeoff_delay(all_legs):  # Q5: wheels up - scheduled take-off; negatives kept; no schedule -> can't calculate
    out = {}
    for l in all_legs:
        if l["operation"] != DEPARTURE:
            continue
        sched, up = l["scheduled_take_off"], l["wheels_up"]
        reason = "missing scheduled take-off" if sched is None else "missing take-off" if up is None else None
        out[l["key"]] = {"delay_sec": int((up - sched).total_seconds()) if reason is None else None,
                         "exclusion_reason": reason, "included": int(reason is None), **_selection(up), **_aircraft(l)}
    return out


def taxiway_usage(all_legs):  # Q7: one row per leg per segment field; provisional section-entry proxy times
    out = {}
    for l in all_legs:
        if l["operation"] not in (ARRIVAL, DEPARTURE):
            continue
        dep = l["operation"] == DEPARTURE
        for role, segment, proxy in (
                ("runway", l["taxiway_runway"], l["runway_entrance"] if dep else l["runway_exit"]),
                ("ramp", l["taxiway_ramp"], l["movement_area_entrance"] if dep else l["movement_area_exit"])):
            m = re.fullmatch(r"TaxiwaySegment_([A-Z])_(.+)", segment or "")
            reason = "missing segment" if segment is None else "missing time" if proxy is None else None
            out[l["key"] + (role,)] = {
                "taxiway_segment": segment,
                "taxiway_letter": m.group(1) if m else None,
                "taxiway_name": PHONETIC[m.group(1)] if m else None,
                "segment_number": int(m.group(2)) if m and m.group(2).isdigit() else None,
                "exclusion_reason": reason, "included": int(reason is None), **_selection(proxy)}
    return out


def runway_activity(all_legs):  # Q9: take-offs by wheels up, landings by wheels down, missed approaches separate
    out = {}
    for l in all_legs:
        op = l["operation"]
        activity, t = {DEPARTURE: ("takeoff", l["wheels_up"]), ARRIVAL: ("landing", l["wheels_down"])}.get(
            op, ("missed_approach", l["event_time"]))
        missed = int(op == MISSED_APPROACH)
        reason = ("missing time" if t is None else "missed approach" if missed
                  else "missing runway" if l["runway"] is None else None)
        out[l["key"]] = {"activity": activity, "is_missed_approach": missed, "exclusion_reason": reason,
                         "included": int(reason is None), **_selection(t)}
    return out


def peak_hours(activity):  # Q10: take-offs + completed landings per local hour, RANK per local day (ties share)
    counts = {}
    for r in activity.values():
        if r["selection_date"] is None or r["is_missed_approach"]:
            continue
        c = counts.setdefault((r["selection_date"], r["selection_hour"]), {"operations": 0, "takeoffs": 0, "landings": 0})
        c["operations"] += 1
        c["takeoffs" if r["activity"] == "takeoff" else "landings"] += 1
    for (day, hour), c in counts.items():
        c["hour_rank"] = 1 + sum(o["operations"] > c["operations"] for (d, _), o in counts.items() if d == day)
    return counts


def build(excel):
    all_legs = legs(excel)
    ma = movement_area(all_legs)
    activity = runway_activity(all_legs)
    return {
        "legs": all_legs,
        "v_taxi_in": taxi_in(all_legs),
        "v_taxi_out": taxi_out(all_legs),
        "v_movement_area": ma,
        "v_movement_area_hourly_peak": movement_area_hourly_peak(ma),
        "v_runway_occupancy": runway_occupancy(all_legs),
        "v_takeoff_delay": takeoff_delay(all_legs),
        "v_taxiway_usage": taxiway_usage(all_legs),
        "v_runway_activity": activity,
        "v_peak_hours": peak_hours(activity),
    }
