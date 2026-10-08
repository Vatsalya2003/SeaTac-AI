# Database Schema — `AIplane` (MySQL)

> **Repo layout:** this copy lives in `docs/`. Code is under `src/` (`src/backend`, `src/frontend`, `src/database`, `src/electron`). Files from the team's *OLD Data* folder are not in this repo.

> What each table and column *means*, how the tables connect, and where the traps are.
> Related docs: [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) · [TECH_STACK.md](TECH_STACK.md) · [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) · [SETUP_GUIDE.md](SETUP_GUIDE.md) (run it locally)
>
> **Source of truth:** [`SeaTac-AI/database/data/AIplane.sql`](../src/database/data/AIplane.sql), a MySQL dump that contains both the schema and the data. Every row count and data fact below comes from parsing that file (2026-09-29), not from the older README numbers.

---

## The big picture in 30 seconds

There are **three tables**:

```
aircraft_type (16 rows)          flight (725 rows)                    flight_event (7,995 rows)
────────────────────             ─────────────────                    ──────────────────────────
aircraft_type  PK  ◄──── FK ──── aircraft_type                        id  PK
weight_class                     id  PK                               call_sign  ──┐  (no FK; see issues)
wake_category                    call_sign  ◄──────────── "logical" ───────────────┘
wingspan_ft / wingspan_m         operation (ARRIVAL/DEPARTURE)        operation
                                 airports, scheduled/actual times     event_type  (what happened)
                                                                      event_time  (when)
                                                                      location    (where: gate/runway/taxiway)
```

- **`flight`** has one row per flight *leg*, either **arriving at** or **departing from** Seattle (KSEA). Every row with a known airport has KSEA as its origin or its destination.
- **`flight_event`** has one row per *thing that happened to a flight* with a timestamp, such as "landed at 10:29" or "arrived at gate at 10:35". **Most questions are answered here** by subtracting one event's time from another's (e.g. taxi-in = in-block time − landing time).
- **`aircraft_type`** is a small lookup table of aircraft specs (size class, wingspan).

**Scope of the data:** a single operating day, **2025-08-08**. Event times run from 2025-08-07 15:32 to 2025-08-09 11:12 because flights cross midnight. Airline codes are **anonymised**: `QTA` (504 flights) and `ZYX` (221). All times are **US Pacific local time**, stored as `DATETIME` with no timezone.

How the tables were produced from the Excel export is covered in [DEVELOPER_GUIDE.md → Rebuilding the database](DEVELOPER_GUIDE.md#25-rebuilding-the-database-from-excel-and-why-it-currently-fails).

---

## Table: `aircraft_type`

A lookup table: one row per aircraft model.

| Column | Type | What it means | Values in the data |
|---|---|---|---|
| `aircraft_type` | `VARCHAR(20)`, **primary key** | The ICAO aircraft type code: a short code for the model. `B738` = Boeing 737-800, `B39M` = Boeing 737 MAX 9, `A21N` = Airbus A321neo | 14 real codes plus `UNKNOWN_001` and `UNKNOWN_002` (see issues) |
| `weight_class` | `VARCHAR(10)` | ICAO weight category: **L**ight, **M**edium or **H**eavy. It affects spacing and taxi behaviour | 14 × `M`, 2 × `H` (`A339` and `A359`, the widebodies). No light aircraft |
| `wake_category` | `VARCHAR(10)` | The wake-turbulence category letter as recorded by Aerobahn (how much turbulence the aircraft leaves behind, which sets separation). ⚠️ The exact letter scheme (e.g. RECAT) isn't documented in the repo; check the Data Dictionary (team's `OLD Data/technical/700-041227_Data_Dictionary V2.xlsx`; not in this repo) | 14 × `D`, 2 × `B` |
| `wingspan_ft` | `DECIMAL(8,5)` | Wingspan in feet | e.g. 117.45 for a 737-800 |
| `wingspan_m` | `DECIMAL(8,5)` | Wingspan in metres (the same measurement) | e.g. 35.80 |

---

## Table: `flight`

One row per flight leg that touches SEA. 367 departures and 358 arrivals.

| Column | Type | What it means | Notes and gotchas |
|---|---|---|---|
| `id` | `INT` auto-increment, **primary key** | Internal row number | The **only** truly unique identifier for a flight. Values start around 2111 (left over from earlier imports) |
| `call_sign` | `VARCHAR(20)`, not null | The radio identifier air traffic control uses, e.g. `QTA328` | ⚠️ **Not unique.** 63 call signs appear more than once (see issues) |
| `flight_ID` | `VARCHAR(20)` | The flight identifier from the source export | Identical to `call_sign` in every row, so it adds no information |
| `aircraft_type` | `VARCHAR(20)`, FK → `aircraft_type` | Which aircraft model flew this leg | Never null. 9 originally-missing values were filled with `UNKNOWN_###` |
| `flight_number` | `VARCHAR(20)` | The number part of the flight, e.g. `'328'` | Stored as text even though it's numeric |
| `aircraft_registration` | `VARCHAR(20)` | The aircraft's tail number, e.g. `N569AS`, identifying the physical plane | 7 nulls |
| `origin_airport` | `VARCHAR(10)` | Departure airport as a 4-letter ICAO code (`KSEA` = Seattle, `KORD` = Chicago O'Hare) | 3 nulls |
| `destination_airport` | `VARCHAR(10)` | Arrival airport, ICAO code | 3 nulls |
| `departure_procedure` | `VARCHAR(50)` | The published departure route (a "SID", e.g. `MONTN2`) filed for the leg's departure airport | 92 nulls |
| `flight_origination_date` | `DATE` | The flight's operating date according to AODB (the Port's operations database) | **Only filled for departures.** It is null for all 358 arrivals |
| `schedule_departure` | `DATETIME` | Scheduled **off-block** time: when the plane was due to push back from its gate | From "Scheduled Off Block Time (Aerobahn)". For arrivals, this is the push-back at the *other* airport |
| `actual_departure` | `DATETIME` | Actual off-block time | From "Actual Off Block Time (Aerobahn)" |
| `schedule_arrival` | `DATETIME` | Despite the name, this is **ATC's *estimated* in-block time**, not a schedule | From "Estimated In Block Time (ATC)" ([INSTALL.md mapping](../src/database/INSTALL.md)). The name is misleading |
| `actual_arrival` | `DATETIME` | Actual **in-block** time: when the plane parked at the gate | 142 nulls |
| `operation` | `ENUM('DEPARTURE','ARRIVAL')` | Whether this leg is **leaving** SEA or **arriving** at SEA | Always set. It is the key to interpreting everything else in the row |

> **Duplicated data:** the same four times also exist as rows in `flight_event`. The LLM prompt only tells the model about a few `flight` columns, so in practice generated SQL uses `flight_event` for all times (see [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md#3-how-a-question-flows-through-the-system-end-to-end)).

---

## Table: `flight_event`

One row per timestamped event. It was built by taking each flight's time columns and turning every non-empty one into its own row.

| Column | Type | What it means |
|---|---|---|
| `id` | `INT` auto-increment, **primary key** | Row number |
| `call_sign` | `VARCHAR(20)` | Which flight this event belongs to. It links to `flight.call_sign`, but **no foreign key is defined** (see issues) |
| `operation` | `ENUM('DEPARTURE','ARRIVAL')` | Copied from the flight. **Always filter on it** alongside `call_sign` |
| `event_type` | `ENUM(...)`, 18 allowed values | *What* happened (see the glossary below). The values are case-sensitive, and the LLM must use them exactly |
| `event_time` | `DATETIME` | *When* it happened, in US Pacific local time |
| `event_source` | `ENUM('AODB','ATC','Aerobahn','Filed')` | *Which system* reported it. The data only contains `Aerobahn` (5,843 rows: actual and scheduled times) and `ATC` (2,152 rows: estimates) |
| `location` | `VARCHAR(50)` | *Where* it happened: a gate (`Gate_N14`), a runway (`34L`) or a taxiway segment (`TaxiwaySegment_B_28`). ⚠️ Read the location trap below before using this |

**Indexes:** `call_sign`, `event_type` and `event_time` are each indexed.

### Event types: what each one means

A departing plane's normal sequence runs **top to bottom**; an arriving plane's runs **bottom to top**.

| `event_type` | Plain meaning | Rows | Source |
|---|---|---|---|
| `Boarding_Start` | Passengers start boarding | 221 | Aerobahn |
| `Scheduled_Off_Block` | When the plane was *supposed* to push back from the gate | 720 | Aerobahn |
| `Actual_Off_Block` | When it *actually* pushed back ("off-block" = wheel chocks removed) | 719 | Aerobahn |
| `Movement_Area_Entrance` | Plane leaves the ramp and enters the taxiways controlled by the tower | 366 | Aerobahn |
| `Runway_Entrance` | Plane rolls onto the runway | 367 | Aerobahn |
| `Scheduled_Take_Off` | Planned takeoff time | 718 | Aerobahn |
| `Estimated_Take_Off` | ATC's estimate of takeoff | 718 | ATC |
| `Actual_Take_Off` | Wheels leave the ground ("wheels up") | 723 | Aerobahn |
| `Estimated_Landing` | ATC's estimate of touchdown | 718 | ATC |
| `Actual_Landing` | Wheels touch the ground ("wheels down") | 712 | Aerobahn |
| `Runway_Exit` | Plane turns off the runway | 357 | Aerobahn |
| `Movement_Area_Exit` | Plane leaves the tower-controlled taxiways and enters the ramp | 357 | Aerobahn |
| `Estimated_In_Block` | ATC's estimate of gate arrival | 716 | ATC |
| `Actual_In_Block` | Plane parks at the gate ("in-block" = chocks in) | 583 | Aerobahn |
| `North_Ramp_Enter` / `North_Ramp_Exit` / `South_Ramp_Enter` / `South_Ramp_Exit` | Entering or leaving the north/south ramp areas | **0** | Added Mar 2026 (see issues) |

**The formulas the whole project relies on** (from `DETAILED_SCHEMA` in [`backend/app_optimized.py`](../src/backend/app_optimized.py)):
- **Taxi-in** = `Actual_In_Block` − `Actual_Landing` (arrivals)
- **Taxi-out** = `Actual_Take_Off` − `Actual_Off_Block` (departures)
- **Wheels-up delay** = `Actual_Take_Off` − `Scheduled_Take_Off`
- **Runway occupancy:** the earlier docs imply `Runway_Exit` − `Runway_Entrance`, but **that returns nothing**, because no flight has both events (issue 4). ⚠️ Our suggestion, which needs Port confirmation: use `Actual_Take_Off` − `Runway_Entrance` for departures and `Runway_Exit` − `Actual_Landing` for arrivals. The client's user story does say to "utilize wheels up time" for this question.
- By convention, results outside 1–120 minutes are filtered out as bad data.

For a visual definition of hold time, taxi time and gate-rest time, see `OLD Data/technical/Arrival Hold Visual.jpg` (in the team's OLD Data folder; not in this repo).

### Location values

- **63 gates** (e.g. `Gate_N14`, `Gate_C4`).
- **6 runway designators**: `16L/34R`, `16C/34C` and `16R/34L`. These are **3 physical runways**, each named once per direction. The Spring 2026 mid-term PDF says "5 runways"; the data has 6 designators.
- **13 taxiway segments** (`TaxiwaySegment_B_28`, `…_C_1`, etc.). The client's user story asks about "Tango, Hotel, Whiskey" taxiways, which don't appear under those names. ⚠️ Mapping segment codes to taxiway names needs Port input.
- **Oddities:** 8 nulls, and 3 rows with the value `*ASCG1S`, meaning unknown.

---

## Relationships

| From | To | Enforced? | How to join correctly |
|---|---|---|---|
| `flight.aircraft_type` | `aircraft_type.aircraft_type` | ✅ Yes: a real foreign key (`fk_flight_aircraft_type`, `ON DELETE SET NULL`, `ON UPDATE CASCADE`) | `JOIN aircraft_type a ON f.aircraft_type = a.aircraft_type` |
| `flight_event.call_sign` | `flight.call_sign` | ❌ No: logical only (the column comment says "FK" but there is no constraint) | Join on **both** `call_sign` **and** `operation`: `ON f.call_sign = e.call_sign AND f.operation = e.operation`. Even this isn't fully safe (see duplicates below) |

---

## Known schema issues

Each item below is a fact checked against the data unless it's marked ⚠️.

1. **`call_sign` is not unique in `flight`, and there's no proper flight key in `flight_event`.**
   660 distinct call signs across 725 rows. In 53 cases the same call sign has one arrival and one departure; that's the intended design, per [INSTALL.md](../src/database/INSTALL.md). But **10 call signs have two legs with the *same* operation**: 6 are DEPARTURE twice, 2 ARRIVAL twice, and 2 have three legs. Examples: `QTA1201`, `QTA328`, `QTA536`. Their events are duplicated too. Any join on `call_sign` (+ `operation`) **multiplies rows** for these flights and skews averages and counts.
   *Fix idea:* add `flight_event.flight_id` referencing `flight.id`, and join on that.
2. **No foreign key from `flight_event` to `flight`**, so events can point at flights that don't exist. This follows from issue 1: you can't make a foreign key to a non-unique column.
3. **The location trap: events at the *other* airport are tagged with SEA locations.** The import script chooses `location` by event *category* (gate events get the SEA gate, runway events get the SEA runway) no matter where the event happened. Example: departure `QTA1004` (SEA → Spokane) has an `Actual_Landing` at 21:00 with location `34R` and an `Actual_In_Block` at `Gate_N5`. Both actually happened in Spokane.
   **Rule of thumb:** only these events happened at SEA:
   - **DEPARTURE rows:** boarding, off-block, movement-area entrance, runway entrance, take-off.
   - **ARRIVAL rows:** landing, runway exit, movement-area exit, in-block.
   A "runway utilisation" query that counts all takeoffs and landings per runway without this filter roughly **doubles** the counts.
4. **Each flight has only half of the runway events: the "≈50% gap".** In the data:
   - `Runway_Entrance` exists **only for departures** (361 of 361).
   - `Runway_Exit` exists **only for arrivals** (354 of 354).
   - **No flight has both**, and `Movement_Area_Entrance`/`Exit` follow the same count pattern.
   The Spring 2026 team called this an ~50% gap in the source data (mid-term PDF p.4) affecting questions 3, 4 and 9. ⚠️ Our reading is different. It looks *structural*: the export only records the SEA-side runway crossing for each leg, i.e. entry for takeoffs and exit for landings. So these questions need per-operation formulas, not "exit − entrance" (see the formulas above). Confirm with the Port before relying on this.
5. **The ramp event types exist but have no data.** Commit `7c13e84` (Jo, 2026-03-24) added `North/South_Ramp_Enter/Exit` to the `event_type` enum, but the committed dump contains zero such rows. The matching import-script change (`7feb7e9`) can't run against the committed Excel file; see [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md#25-rebuilding-the-database-from-excel-and-why-it-currently-fails).
6. **Made-up aircraft types.** `UNKNOWN_001` (2 flights) and `UNKNOWN_002` (7 flights) were created by `db_manager.py fix-nulls` for flights with no aircraft type, grouped by matching weight, wake and wingspan ([INSTALL.md Step 4](../src/database/INSTALL.md)). They show up in "by aircraft type" results.
7. **Misleading column names.** `schedule_arrival` holds an ATC *estimate*. `flight_ID` just duplicates `call_sign`. `flight_number` is text.
8. **The database name is inconsistent.** The dump creates `AIplane`. `app_optimized.py` defaults to `AIplane`, but `app.py` and `backend/setup.sh` use `aiplane`. On Linux, MySQL database names are usually case-sensitive, so the wrong one fails. ⚠️ On macOS it usually works either way.
9. **Needs MySQL 8 or later.** The dump uses the `utf8mb4_0900_ai_ci` collation, which exists only in MySQL 8+. It was dumped from MySQL **9.5.0**. [`database/README.md`](../src/database/README.md) says MariaDB 10.5+ works. ⚠️ That's probably false because of this collation.
10. **The docs are stale about the schema.** The READMEs describe the event types as 14 (there are now 18), call `flight_event.call_sign` an "FK" (it isn't), and give column types that differ from the dump (e.g. `DECIMAL(10,2)` vs the real `DECIMAL(8,5)`). When they disagree, trust `AIplane.sql`.

## Data quality facts

| Fact | Numbers |
|---|---|
| Arrivals with both landing and in-block events (usable for taxi-in) | 353 of 354 (counted by call sign + operation) |
| Departures with both off-block and takeoff events (usable for taxi-out) | 361 of 361 |
| Flights with both runway entrance **and** exit | **0** (issue 4) |
| Heavy (widebody) aircraft | Only 16 flights (A339, A359), so weight-class comparisons are based on few examples |
| Flight legs not touching KSEA | 0 (3 rows have null airports) |
