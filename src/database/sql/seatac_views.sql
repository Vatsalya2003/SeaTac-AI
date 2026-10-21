-- Metric views for the `seatac` database (run by scripts/load_aerobahn.py after the tables are built).
-- Definitions confirmed by the Port of Seattle: see docs/CLIENT_CONFIRMED_RULES.md. Times are SEA local (PDT)
-- exactly as exported, never shifted.
--
-- Every metric view has:
--   exclusion_reason  NULL = row is used in the metric. Otherwise one of:
--                     'missing time'      = a start or end timestamp is NULL
--                     'negative duration' = end is before start (not used in v_takeoff_delay, where negative = early)
--                     plus view-specific reasons noted below
--   included          1 when exclusion_reason IS NULL
--   selection_time    the timestamp the confirmed selection rule uses to place the row in a reporting window,
--                     with selection_date and selection_hour (local). Windows include the start and exclude the end.
-- No view applies an upper cutoff or a minimum group size. Zero and very long durations are kept.
-- Statements are separated by a semicolon at the end of a line. Keep semicolons out of comments.

-- Q1, Q6, Q8 - taxi-in: arrivals, wheels down -> actual in-block (end confirmed as in-block).
-- Never uses Actual Landing in place of wheels down. Selection: arrivals by wheels-down time.
CREATE OR REPLACE VIEW v_taxi_in AS
SELECT
  f.flight_info_id, f.operation, f.call_sign, f.carrier, f.aircraft_type, f.weight_class_icao,
  COALESCE(f.weight_class_icao, 'Unknown') AS weight_class_group,
  f.runway, f.gate, f.sea_date,
  f.wheels_down AS start_time,
  f.actual_in_block AS end_time,
  f.wheels_down AS selection_time,
  DATE(f.wheels_down) AS selection_date,
  HOUR(f.wheels_down) AS selection_hour,
  TIMESTAMPDIFF(SECOND, f.wheels_down, f.actual_in_block) AS duration_sec,
  TIMESTAMPDIFF(SECOND, f.wheels_down, f.actual_in_block) / 60 AS duration_min,
  f.sys_taxi_in_sec,
  CASE WHEN f.wheels_down IS NULL OR f.actual_in_block IS NULL THEN 'missing time'
       WHEN f.actual_in_block < f.wheels_down THEN 'negative duration' END AS exclusion_reason,
  (f.wheels_down IS NOT NULL AND f.actual_in_block IS NOT NULL AND f.actual_in_block >= f.wheels_down) AS included
FROM flights f
WHERE f.operation = 'Arrival';

-- Q2, Q6 - taxi-out: departures, actual off-block (Aerobahn, confirmed by the Port) -> wheels up.
-- Selection: departures by off-block time, so a flight pushing back before midnight belongs to the earlier day.
CREATE OR REPLACE VIEW v_taxi_out AS
SELECT
  f.flight_info_id, f.operation, f.call_sign, f.carrier, f.aircraft_type, f.weight_class_icao,
  COALESCE(f.weight_class_icao, 'Unknown') AS weight_class_group,
  f.runway, f.gate, f.sea_date,
  f.actual_off_block AS start_time,
  f.wheels_up AS end_time,
  f.actual_off_block AS selection_time,
  DATE(f.actual_off_block) AS selection_date,
  HOUR(f.actual_off_block) AS selection_hour,
  DATE(f.actual_off_block) AS off_block_date,
  HOUR(f.actual_off_block) AS off_block_hour,
  TIMESTAMPDIFF(SECOND, f.actual_off_block, f.wheels_up) AS duration_sec,
  TIMESTAMPDIFF(SECOND, f.actual_off_block, f.wheels_up) / 60 AS duration_min,
  f.sys_taxi_out_sec,
  CASE WHEN f.actual_off_block IS NULL OR f.wheels_up IS NULL THEN 'missing time'
       WHEN f.wheels_up < f.actual_off_block THEN 'negative duration' END AS exclusion_reason,
  (f.actual_off_block IS NOT NULL AND f.wheels_up IS NOT NULL AND f.wheels_up >= f.actual_off_block) AS included
FROM flights f
WHERE f.operation = 'Departure';

-- Q6 helper - the fixed list of weight-class groups, so a group with no eligible rows shows "No data" (never 0).
-- LEFT JOIN this to v_taxi_in / v_taxi_out on weight_class_group.
CREATE OR REPLACE VIEW v_weight_classes AS
SELECT 'L' AS weight_class_group, 'Light' AS label, 1 AS sort_order
UNION ALL SELECT 'M', 'Medium', 2
UNION ALL SELECT 'H', 'Heavy', 3
UNION ALL SELECT 'Unknown', 'Unknown', 4;

-- Q3 - time in the movement area (interval = [start_time, end_time): entry counted, exit not).
-- Arrivals: touchdown (wheels down) -> movement area exit toward parking.
-- Departures: movement area entrance -> take-off (wheels up). Confirmed by the Port: runway time counts.
-- PENDING (Port): mapping Aerobahn's Movement Area Entrance/Exit events to the client's hatched-area boundary.
-- LIMIT: the export has one entrance/exit pair per leg, so an exit and re-entry within a leg is not visible.
-- Selection: intervals OVERLAPPING the window count (start_time < window_end AND end_time > window_start).
-- selection_time is the interval start.
CREATE OR REPLACE VIEW v_movement_area AS
SELECT
  f.flight_info_id, f.operation, f.call_sign, f.aircraft_type, f.weight_class_icao, f.runway, f.sea_date,
  f.wheels_down AS start_time,
  f.movement_area_exit AS end_time,
  f.wheels_down AS selection_time,
  DATE(f.wheels_down) AS selection_date,
  HOUR(f.wheels_down) AS selection_hour,
  TIMESTAMPDIFF(SECOND, f.wheels_down, f.movement_area_exit) AS duration_sec,
  TIMESTAMPDIFF(SECOND, f.wheels_down, f.movement_area_exit) / 60 AS duration_min,
  CASE WHEN f.wheels_down IS NULL OR f.movement_area_exit IS NULL THEN 'missing time'
       WHEN f.movement_area_exit < f.wheels_down THEN 'negative duration' END AS exclusion_reason,
  (f.wheels_down IS NOT NULL AND f.movement_area_exit IS NOT NULL AND f.movement_area_exit >= f.wheels_down) AS included
FROM flights f
WHERE f.operation = 'Arrival'
UNION ALL
SELECT
  f.flight_info_id, f.operation, f.call_sign, f.aircraft_type, f.weight_class_icao, f.runway, f.sea_date,
  f.movement_area_entrance,
  f.wheels_up,
  f.movement_area_entrance,
  DATE(f.movement_area_entrance),
  HOUR(f.movement_area_entrance),
  TIMESTAMPDIFF(SECOND, f.movement_area_entrance, f.wheels_up),
  TIMESTAMPDIFF(SECOND, f.movement_area_entrance, f.wheels_up) / 60,
  CASE WHEN f.movement_area_entrance IS NULL OR f.wheels_up IS NULL THEN 'missing time'
       WHEN f.wheels_up < f.movement_area_entrance THEN 'negative duration' END,
  (f.movement_area_entrance IS NOT NULL AND f.wheels_up IS NOT NULL AND f.wheels_up >= f.movement_area_entrance)
FROM flights f
WHERE f.operation = 'Departure';

-- Q3 helper - per local hour, the maximum number of aircraft in the movement area at the same time.
-- Sweep over all included v_movement_area intervals: +1 at entry, -1 at exit, and a 0 marker at every hour start.
-- At the same second, exits are counted first, then the hour marker, then entries, so an exit is not counted
-- (end-exclusive), an entry is (start-inclusive), and an aircraft leaving as another enters is never counted twice.
-- The hour marker carries aircraft already inside into each hour, so intervals overlapping the hour count.
-- intervals_used / intervals_excluded (+ by reason) are whole-dataset counts, repeated on every row, so the
-- exclusions can be reported with the answer. Same pending boundary mapping and re-entry limit as v_movement_area.
CREATE OR REPLACE VIEW v_movement_area_hourly_peak AS
WITH RECURSIVE
  intervals AS (
    SELECT start_time, end_time FROM v_movement_area WHERE exclusion_reason IS NULL
  ),
  exclusion_counts AS (
    SELECT SUM(exclusion_reason IS NULL) AS intervals_used,
           SUM(exclusion_reason IS NOT NULL) AS intervals_excluded,
           SUM(exclusion_reason = 'missing time') AS excluded_missing_time,
           SUM(exclusion_reason = 'negative duration') AS excluded_negative_duration
    FROM v_movement_area
  ),
  bounds AS (
    SELECT CAST(DATE_FORMAT(MIN(start_time), '%Y-%m-%d %H:00:00') AS DATETIME) AS first_hour,
           MAX(end_time) AS last_time
    FROM intervals
  ),
  hours AS (
    SELECT first_hour AS hour_start FROM bounds
    UNION ALL
    SELECT h.hour_start + INTERVAL 1 HOUR FROM hours h JOIN bounds b ON h.hour_start + INTERVAL 1 HOUR <= b.last_time
  ),
  events AS (
    SELECT end_time AS t, -1 AS delta, 0 AS tie_order FROM intervals
    UNION ALL
    SELECT hour_start, 0, 1 FROM hours
    UNION ALL
    SELECT start_time, 1, 2 FROM intervals
  ),
  running AS (
    SELECT t, SUM(delta) OVER (ORDER BY t, tie_order ROWS UNBOUNDED PRECEDING) AS aircraft_in_area
    FROM events
  ),
  peaks AS (
    SELECT DATE(t) AS local_date, HOUR(t) AS local_hour, MAX(aircraft_in_area) AS max_aircraft_in_area
    FROM running
    GROUP BY DATE(t), HOUR(t)
  )
SELECT p.local_date, p.local_hour, p.max_aircraft_in_area,
       c.intervals_used, c.intervals_excluded, c.excluded_missing_time, c.excluded_negative_duration
FROM peaks p CROSS JOIN exclusion_counts c;

-- Q4 - runway occupancy, in seconds. No Clear Active (Port instruction).
-- Arrivals: touchdown (wheels down) -> runway exit. Departures: runway entrance -> wheels up.
-- Selection: by the start of the occupancy interval (touchdown / runway entry).
CREATE OR REPLACE VIEW v_runway_occupancy AS
SELECT
  f.flight_info_id, f.operation, f.call_sign, f.aircraft_type, f.weight_class_icao, f.runway, f.sea_date,
  f.wheels_down AS start_time,
  f.runway_exit AS end_time,
  f.wheels_down AS selection_time,
  DATE(f.wheels_down) AS selection_date,
  HOUR(f.wheels_down) AS selection_hour,
  TIMESTAMPDIFF(SECOND, f.wheels_down, f.runway_exit) AS duration_sec,
  f.sys_runway_occupancy_sec,
  CASE WHEN f.wheels_down IS NULL OR f.runway_exit IS NULL THEN 'missing time'
       WHEN f.runway_exit < f.wheels_down THEN 'negative duration' END AS exclusion_reason,
  (f.wheels_down IS NOT NULL AND f.runway_exit IS NOT NULL AND f.runway_exit >= f.wheels_down) AS included
FROM flights f
WHERE f.operation = 'Arrival'
UNION ALL
SELECT
  f.flight_info_id, f.operation, f.call_sign, f.aircraft_type, f.weight_class_icao, f.runway, f.sea_date,
  f.runway_entrance,
  f.wheels_up,
  f.runway_entrance,
  DATE(f.runway_entrance),
  HOUR(f.runway_entrance),
  TIMESTAMPDIFF(SECOND, f.runway_entrance, f.wheels_up),
  f.sys_runway_occupancy_sec,
  CASE WHEN f.runway_entrance IS NULL OR f.wheels_up IS NULL THEN 'missing time'
       WHEN f.wheels_up < f.runway_entrance THEN 'negative duration' END,
  (f.runway_entrance IS NOT NULL AND f.wheels_up IS NOT NULL AND f.wheels_up >= f.runway_entrance)
FROM flights f
WHERE f.operation = 'Departure';

-- Q5 - take-off delay: departures, wheels up minus scheduled take-off, in minutes, no threshold.
-- Negative values mean an early take-off and are KEPT. Never falls back to scheduled off-block.
-- 'missing scheduled take-off' = the calculation cannot be completed for that flight.
-- Selection: departures by actual take-off time.
CREATE OR REPLACE VIEW v_takeoff_delay AS
SELECT
  f.flight_info_id, f.operation, f.call_sign, f.carrier, f.aircraft_type, f.weight_class_icao, f.runway, f.sea_date,
  f.scheduled_take_off,
  f.wheels_up,
  f.wheels_up AS selection_time,
  DATE(f.wheels_up) AS selection_date,
  HOUR(f.wheels_up) AS selection_hour,
  TIMESTAMPDIFF(SECOND, f.scheduled_take_off, f.wheels_up) AS delay_sec,
  TIMESTAMPDIFF(SECOND, f.scheduled_take_off, f.wheels_up) / 60 AS delay_min,
  CASE WHEN f.scheduled_take_off IS NULL THEN 'missing scheduled take-off'
       WHEN f.wheels_up IS NULL THEN 'missing take-off' END AS exclusion_reason,
  (f.scheduled_take_off IS NOT NULL AND f.wheels_up IS NOT NULL) AS included
FROM flights f
WHERE f.operation = 'Departure';

-- Q7 - taxiway usage: one row per flight leg per taxiway segment field (runway-side and ramp-side).
-- Count DISTINCT (flight_info_id, operation) per taxiway_segment (a section) or per taxiway_name (a taxiway).
-- Arrivals and departures only. 'missing segment' = the taxiway field is empty for that leg.
-- Segment codes use the phonetic alphabet (confirmed by the Port): TaxiwaySegment_B_28 = taxiway Bravo, segment 28.
-- segment_number is NULL when the part after the letter is not a number (e.g. TaxiwaySegment_B_SSR).
-- Tango, Hotel and Whiskey never appear: the export only records the segment used to enter/exit the runway and ramp.
-- Selection rule: by section-entry time. The export has NO per-segment times, so selection_time is a PROVISIONAL
-- PROXY (is_proxy_time = 1), pending Port confirmation:
--   departure ramp-side -> movement area entrance     departure runway-side -> runway entrance
--   arrival runway-side -> runway exit                arrival ramp-side     -> movement area exit
-- 'missing time' = a segment is recorded but its proxy time is NULL, so the row can't be placed in a window.
CREATE OR REPLACE VIEW v_taxiway_usage AS
SELECT
  u.flight_info_id, u.operation, u.call_sign, u.aircraft_type, u.weight_class_icao, u.runway, u.sea_date,
  u.segment_role, u.taxiway_segment,
  CASE WHEN u.taxiway_segment REGEXP '^TaxiwaySegment_[A-Z]_'
       THEN SUBSTRING(u.taxiway_segment, 16, 1) END AS taxiway_letter,
  CASE WHEN u.taxiway_segment REGEXP '^TaxiwaySegment_[A-Z]_' THEN
    CASE SUBSTRING(u.taxiway_segment, 16, 1)
       WHEN 'A' THEN 'Alpha'   WHEN 'B' THEN 'Bravo'  WHEN 'C' THEN 'Charlie' WHEN 'D' THEN 'Delta'
       WHEN 'E' THEN 'Echo'    WHEN 'F' THEN 'Foxtrot' WHEN 'G' THEN 'Golf'   WHEN 'J' THEN 'Juliet'
       WHEN 'K' THEN 'Kilo'    WHEN 'L' THEN 'Lima'   WHEN 'M' THEN 'Mike'    WHEN 'N' THEN 'November'
       WHEN 'P' THEN 'Papa'    WHEN 'Q' THEN 'Quebec' WHEN 'Z' THEN 'Zulu' END
  END AS taxiway_name,
  CASE WHEN u.taxiway_segment REGEXP '^TaxiwaySegment_[A-Z]_[0-9]+$'
       THEN CAST(SUBSTRING_INDEX(u.taxiway_segment, '_', -1) AS UNSIGNED) END AS segment_number,
  u.proxy_time AS selection_time,
  DATE(u.proxy_time) AS selection_date,
  HOUR(u.proxy_time) AS selection_hour,
  1 AS is_proxy_time,
  CASE WHEN u.taxiway_segment IS NULL THEN 'missing segment'
       WHEN u.proxy_time IS NULL THEN 'missing time' END AS exclusion_reason,
  (u.taxiway_segment IS NOT NULL AND u.proxy_time IS NOT NULL) AS included
FROM (
  SELECT
    f.flight_info_id, f.operation, f.call_sign, f.aircraft_type, f.weight_class_icao, f.runway, f.sea_date,
    'runway' AS segment_role,
    f.taxiway_runway AS taxiway_segment,
    CASE f.operation WHEN 'Departure' THEN f.runway_entrance ELSE f.runway_exit END AS proxy_time
  FROM flights f
  WHERE f.operation IN ('Arrival', 'Departure')
  UNION ALL
  SELECT
    f.flight_info_id, f.operation, f.call_sign, f.aircraft_type, f.weight_class_icao, f.runway, f.sea_date,
    'ramp',
    f.taxiway_ramp,
    CASE f.operation WHEN 'Departure' THEN f.movement_area_entrance ELSE f.movement_area_exit END
  FROM flights f
  WHERE f.operation IN ('Arrival', 'Departure')
) u;

-- Q9 - runway activity: one row per SEA take-off (departure, wheels up) or completed landing (arrival, wheels down).
-- Missed approaches are flagged (is_missed_approach = 1) and excluded ('missed approach'), not counted as landings.
-- 'missing runway' = a completed take-off/landing with no runway identifier: excluded from per-runway counts.
-- (Q10 uses v_peak_hours, which does not need a runway, so it keeps those operations.)
-- Selection: take-offs by actual take-off, landings by wheels down.
CREATE OR REPLACE VIEW v_runway_activity AS
SELECT
  a.flight_info_id, a.operation, a.call_sign, a.aircraft_type, a.weight_class_icao, a.runway, a.sea_date,
  a.activity, a.activity_time,
  a.activity_time AS selection_time,
  DATE(a.activity_time) AS selection_date,
  HOUR(a.activity_time) AS selection_hour,
  DATE(a.activity_time) AS local_date,
  HOUR(a.activity_time) AS local_hour,
  a.is_missed_approach,
  CASE WHEN a.activity_time IS NULL THEN 'missing time'
       WHEN a.is_missed_approach = 1 THEN 'missed approach'
       WHEN a.runway IS NULL THEN 'missing runway' END AS exclusion_reason,
  (a.activity_time IS NOT NULL AND a.is_missed_approach = 0 AND a.runway IS NOT NULL) AS included
FROM (
  SELECT f.*,
         CASE f.operation WHEN 'Departure' THEN 'takeoff' WHEN 'Arrival' THEN 'landing' ELSE 'missed_approach' END AS activity,
         CASE f.operation WHEN 'Departure' THEN f.wheels_up WHEN 'Arrival' THEN f.wheels_down ELSE f.sea_event_time END AS activity_time,
         (f.operation = 'Missed Approach') AS is_missed_approach
  FROM flights f
) a;

-- Q10 - historical peak hours: take-offs + completed landings per local hour, ranked separately for each local day.
-- RANK() (not ROW_NUMBER) so tied hours share a rank. Missed approaches and rows without a time are not counted.
-- A runway is not needed for this count. History only: not a forecast.
CREATE OR REPLACE VIEW v_peak_hours AS
SELECT
  local_date, local_hour,
  COUNT(*) AS operations,
  SUM(activity = 'takeoff') AS takeoffs,
  SUM(activity = 'landing') AS landings,
  RANK() OVER (PARTITION BY local_date ORDER BY COUNT(*) DESC) AS hour_rank
FROM v_runway_activity
WHERE activity_time IS NOT NULL AND is_missed_approach = 0
GROUP BY local_date, local_hour;
