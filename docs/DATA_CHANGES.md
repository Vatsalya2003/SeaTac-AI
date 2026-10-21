# Data Changes — Team 6's sample vs the Port's updated export

> What changed between the old one-day sample (database `AIplane`) and the Port's updated export (database `seatac`), with verified numbers, and which old findings no longer apply.
> Related docs: [DB_SCHEMA.md](DB_SCHEMA.md) (new database) · [legacy/DB_SCHEMA_TEAM6.md](legacy/DB_SCHEMA_TEAM6.md) (old database) · [PROPOSAL_FACT_CHECK.md](PROPOSAL_FACT_CHECK.md)
>
> Numbers verified on 2026-10-19 with [`check_seatac.py`](../src/database/scripts/check_seatac.py) against both databases. The Port file is private and is **not in this repo**.

---

## At a glance

| | Old: `AIplane` (Team 6) | New: `seatac` |
|---|---|---|
| Source | 37-column Excel extract (`src/database/data/field_mapping.xlsx`), cut down from a 593-column sample | Port export `August_8_and_9_2025_Anonymized.xlsx`: 1,061 rows × 585 columns (223 non-empty), **all kept** in `raw_flight_details` |
| Operating day | 2025-08-08 | 2025-08-08 (every `sea_date`) |
| Flight legs | **725** (358 arrivals, 367 departures) | **1,061** (525 arrivals, 535 departures, **1 missed approach**) |
| Old legs found in the new data | — | **719 of 725** match a new leg (same call sign and operation, SEA touchdown or take-off within 2 minutes). 6 don't |
| Distinct call signs | 660 | 927 (**655 in both**) |
| Airline codes | QTA, ZYX (anonymised) | QTA (712 legs), ZYX (349), the same anonymisation |
| Gates | 63 | **88 gates plus the placeholder `*ASCG1S`**. All 63 old gates appear in the new data, and 88 matches the Port's published gate count |
| Runways | 6 designators | 6 designators (3 physical runways) |
| Aircraft types | 14 real + 2 made-up `UNKNOWN_###` | 16 FAA types; 3 legs with no type, **no made-up types** |
| Leg key | None: joins used `call_sign` + `operation`, which isn't unique | **`flight_info_id` + `operation`**, unique |
| Layout | 3 tables: `flight`, `flight_event` (one row per timestamp), `aircraft_type` | 3 layers: `raw_flight_details` → `flights` + `aircraft_types` → metric views |
| Where metrics are defined | In the LLM prompt and generated SQL | In SQL views with an `exclusion_reason` per row, plus [`metric_rules.yaml`](../src/database/metric_rules.yaml) (Samer's confirmed definitions) |

**The old dataset is essentially a subset of the new one:** 719 of its 725 legs are in the new file, and the new file adds about 336 more legs for the same day.

---

## Old findings that no longer apply

| Old finding (Team 6 data) | Why it no longer applies in `seatac` |
|---|---|
| **Call-sign joins duplicate rows.** `call_sign` wasn't unique, and 10 call signs repeated within the same operation, so joins on `call_sign` + `operation` multiplied rows | Every leg has a proper key (`flight_info_id` + `operation`), and the views never join on call sign. Call signs still repeat (19 legs share a call sign within the same operation), but that no longer matters |
| **The location trap.** Events at the *other* airport were tagged with SEA gates and runways (3,188 events), because `location` was filled by event type | Gate, runway and taxiway are plain columns on each leg, and **`flights` holds SEA-side times only**: other-airport times are NULL there (they stay in `raw_flight_details`). There's no `location` column to misread |
| **"No scheduled arrival time"** (`schedule_arrival` was really the ATC *estimate*, and there was no scheduled in-block) | `scheduled_in_block` (Scheduled In Block Time (Aerobahn)) and `scheduled_landing` exist for all arrivals |
| **`Actual_Landing` used as touchdown** (no explicit wheels-down; `Actual_Take_Off` for wheels-up) | Explicit `wheels_down` and `wheels_up` columns. They are identical to the Aerobahn landing and take-off times (525 of 525, 535 of 535), so they're now named for what they are |
| **Missing aircraft types replaced with `UNKNOWN_###`** | The FAA aircraft type is filled for 1,058 of 1,061 legs. The 3 without a type stay NULL (the foreign key allows it) |
| **"No flight has both runway entry and exit" seen as a ≈50% data gap** | Confirmed as **structural**, not missing data: entry is recorded for departures and exit for arrivals. Samer's definitions use the matching pair for each operation (arrivals touchdown → exit, departures entry → wheels-up), and the views exclude only 6 legs |
| **Wheels-up delay looked extreme against "Scheduled_Take_Off"** | `v_takeoff_delay` now uses Samer's confirmed definition (wheels up − scheduled take-off, no threshold, early kept). Results haven't been compared with the old figure; expected answers are being computed independently |
| **Ramp event types existed with no data** | Not used in the new schema |

## Old findings that still apply

| Finding | Still true in the new data |
|---|---|
| One operating day only | Yes (2025-08-08). Q10 "peak hour prediction" stays history-only |
| No light aircraft | Yes: only `M` and `H` weight classes |
| Taxiway names (Tango/Hotel/Whiskey) | Segment codes are now decoded (the Port confirmed the phonetic alphabet: `TaxiwaySegment_B_28` = Bravo, segment 28). But **Tango, Hotel and Whiskey still don't appear**, because the export records only the entry/exit segment for the runway and the ramp (15 runway-side and 16 ramp-side codes) |
| Other-airport times exist in the export | Yes, in `raw_flight_details` (e.g. arrivals' origin off-block). `flights` and the views don't use them |
| The export's own durations use other sources | The export's taxi-in and taxi-out use **AODB** gate times, and its runway occupancy uses **CrossThreshold / Clear Active**. See [DB_SCHEMA.md → definition decisions](DB_SCHEMA.md#definition-decisions-and-pending-items) |

## New things to know

- **Missed approach:** 1 row with `operation = 'Missed Approach'`. Its `flight_info_id` is shared with an arrival. It follows the arrival rule for SEA-side times and is flagged and excluded in `v_runway_activity`.
- **E75L variant conflict:** about 93 of 340 E75L legs carry a different wake category and wingspan, likely two E175 variants under one code ([details](DB_SCHEMA.md#2b-aircraft_types--one-row-per-faa-type)).
- **QTA3199 taxi-in:** an Aerobahn in-block time 99 minutes after touchdown with no second source. It is currently included in taxi-in.
- **Confirmed by the Port (2026-10-21):** the Q2 off-block source is **Aerobahn**, and the Q7 segment codes use the **phonetic alphabet**.
- **Still pending Port confirmation:** the Q3 movement-area boundary mapping, and the meaning of the code `TaxiwaySegment_B_SSR`.

## Baseline database: `AIplane_v2`

So the **unchanged** old chatbot can be tested fairly on the new data, `AIplane_v2` holds the new export in Team 6's original 3-table layout. It has the same table definitions as `AIplane` and the same mapping and traps.
- 1,061 flights and 11,975 events.
- The missed approach is stored with operation NULL.
- 238 legs with no AODB aircraft type, 233 of them E75L, become 3 `UNKNOWN_###` types.

Details: [DB_SCHEMA.md → AIplane_v2](DB_SCHEMA.md#aiplane_v2--the-new-data-in-team-6s-old-layout-baseline-only).
