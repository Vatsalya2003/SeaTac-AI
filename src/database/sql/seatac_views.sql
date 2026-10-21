-- Metric views for the `seatac` database (run by scripts/load_aerobahn.py after the tables are built).
-- Definitions confirmed by Samer (Port of Seattle). All times are local PDT, never shifted.
--
-- Every view has:
--   exclusion_reason  NULL = row is used in the metric
--                     'missing time'      = the start or end timestamp is NULL
--                     'negative duration' = end is before start (not used in v_takeoff_delay, where negative = early)
--   included          1 when exclusion_reason IS NULL
-- Statements are separated by a semicolon at the end of a line. Keep semicolons out of comments.

-- Q1, Q6, Q8 - taxi-in: arrivals, wheels down -> actual in-block
CREATE OR REPLACE VIEW v_taxi_in AS
SELECT
  f.flight_info_id, f.operation, f.call_sign, f.carrier, f.aircraft_type, f.weight_class_icao,
  f.runway, f.gate, f.sea_date,
  f.wheels_down AS start_time,
  f.actual_in_block AS end_time,
  TIMESTAMPDIFF(SECOND, f.wheels_down, f.actual_in_block) AS duration_sec,
  TIMESTAMPDIFF(SECOND, f.wheels_down, f.actual_in_block) / 60 AS duration_min,
  f.sys_taxi_in_sec,
  CASE WHEN f.wheels_down IS NULL OR f.actual_in_block IS NULL THEN 'missing time'
       WHEN f.actual_in_block < f.wheels_down THEN 'negative duration' END AS exclusion_reason,
  (f.wheels_down IS NOT NULL AND f.actual_in_block IS NOT NULL AND f.actual_in_block >= f.wheels_down) AS included
FROM flights f
WHERE f.operation = 'Arrival';

-- Q2, Q6 - taxi-out: departures, actual off-block -> wheels up, with the local date and hour of off-block
CREATE OR REPLACE VIEW v_taxi_out AS
SELECT
  f.flight_info_id, f.operation, f.call_sign, f.carrier, f.aircraft_type, f.weight_class_icao,
  f.runway, f.gate, f.sea_date,
  f.actual_off_block AS start_time,
  f.wheels_up AS end_time,
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

-- Q3 - time in the movement area.
-- Arrivals: wheels down -> movement area exit. Departures: movement area entrance -> wheels up.
-- BOUNDARY PENDING PORT CONFIRMATION: whether the runway itself counts as part of the movement area
-- (i.e. starting arrivals at wheels down and ending departures at wheels up) still needs the Port to confirm.
CREATE OR REPLACE VIEW v_movement_area AS
SELECT
  f.flight_info_id, f.operation, f.call_sign, f.aircraft_type, f.weight_class_icao, f.runway, f.sea_date,
  f.wheels_down AS start_time,
  f.movement_area_exit AS end_time,
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
  TIMESTAMPDIFF(SECOND, f.movement_area_entrance, f.wheels_up),
  TIMESTAMPDIFF(SECOND, f.movement_area_entrance, f.wheels_up) / 60,
  CASE WHEN f.movement_area_entrance IS NULL OR f.wheels_up IS NULL THEN 'missing time'
       WHEN f.wheels_up < f.movement_area_entrance THEN 'negative duration' END,
  (f.movement_area_entrance IS NOT NULL AND f.wheels_up IS NOT NULL AND f.wheels_up >= f.movement_area_entrance)
FROM flights f
WHERE f.operation = 'Departure';

-- Q3 helper - per local hour, the maximum number of aircraft in the movement area at the same time.
-- Sweep over all included v_movement_area intervals. At the same instant, exits are counted before
-- entries (an aircraft leaving as another enters is not counted twice). An hour-start marker carries the
-- aircraft already in the area into each hour. Same boundary caveat as v_movement_area (pending Port).
CREATE OR REPLACE VIEW v_movement_area_hourly_peak AS
WITH RECURSIVE
  intervals AS (
    SELECT start_time, end_time FROM v_movement_area WHERE exclusion_reason IS NULL
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
  )
SELECT DATE(t) AS local_date, HOUR(t) AS local_hour, MAX(aircraft_in_area) AS max_aircraft_in_area
FROM running
GROUP BY DATE(t), HOUR(t);

-- Q4 - runway occupancy, in seconds.
-- Arrivals: wheels down -> runway exit. Departures: runway entrance -> wheels up.
CREATE OR REPLACE VIEW v_runway_occupancy AS
SELECT
  f.flight_info_id, f.operation, f.call_sign, f.aircraft_type, f.weight_class_icao, f.runway, f.sea_date,
  f.wheels_down AS start_time,
  f.runway_exit AS end_time,
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
  TIMESTAMPDIFF(SECOND, f.runway_entrance, f.wheels_up),
  f.sys_runway_occupancy_sec,
  CASE WHEN f.runway_entrance IS NULL OR f.wheels_up IS NULL THEN 'missing time'
       WHEN f.wheels_up < f.runway_entrance THEN 'negative duration' END,
  (f.runway_entrance IS NOT NULL AND f.wheels_up IS NOT NULL AND f.wheels_up >= f.runway_entrance)
FROM flights f
WHERE f.operation = 'Departure';

-- Q5 - take-off delay: departures, wheels up minus scheduled take-off, in minutes, no threshold.
-- Negative values mean an early take-off and are KEPT (only missing times are excluded).
CREATE OR REPLACE VIEW v_takeoff_delay AS
SELECT
  f.flight_info_id, f.operation, f.call_sign, f.carrier, f.aircraft_type, f.weight_class_icao, f.runway, f.sea_date,
  f.scheduled_take_off,
  f.wheels_up,
  TIMESTAMPDIFF(SECOND, f.scheduled_take_off, f.wheels_up) AS delay_sec,
  TIMESTAMPDIFF(SECOND, f.scheduled_take_off, f.wheels_up) / 60 AS delay_min,
  CASE WHEN f.scheduled_take_off IS NULL OR f.wheels_up IS NULL THEN 'missing time' END AS exclusion_reason,
  (f.scheduled_take_off IS NOT NULL AND f.wheels_up IS NOT NULL) AS included
FROM flights f
WHERE f.operation = 'Departure';

-- Q7 - taxiway usage: one row per flight leg per taxiway segment field (runway-side and ramp-side).
-- Count DISTINCT (flight_info_id, operation) per taxiway_segment (a section) or per taxiway_name (a taxiway).
-- Arrivals and departures only. 'missing segment' = the taxiway field is empty for that leg.
-- Segment codes use the phonetic alphabet (confirmed by the Port): TaxiwaySegment_B_28 = taxiway Bravo, segment 28.
-- segment_number is NULL when the part after the letter is not a number (e.g. TaxiwaySegment_B_SSR).
-- Tango, Hotel and Whiskey never appear: the export only records the segment used to enter/exit the runway and ramp.
CREATE OR REPLACE VIEW v_taxiway_usage AS
SELECT
  u.*,
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
       THEN CAST(SUBSTRING_INDEX(u.taxiway_segment, '_', -1) AS UNSIGNED) END AS segment_number
FROM (
  SELECT
    f.flight_info_id, f.operation, f.call_sign, f.aircraft_type, f.weight_class_icao, f.runway, f.sea_date,
    'runway' AS segment_role,
    f.taxiway_runway AS taxiway_segment,
    CASE WHEN f.taxiway_runway IS NULL THEN 'missing segment' END AS exclusion_reason,
    (f.taxiway_runway IS NOT NULL) AS included
  FROM flights f
  WHERE f.operation IN ('Arrival', 'Departure')
  UNION ALL
  SELECT
    f.flight_info_id, f.operation, f.call_sign, f.aircraft_type, f.weight_class_icao, f.runway, f.sea_date,
    'ramp',
    f.taxiway_ramp,
    CASE WHEN f.taxiway_ramp IS NULL THEN 'missing segment' END,
    (f.taxiway_ramp IS NOT NULL)
  FROM flights f
  WHERE f.operation IN ('Arrival', 'Departure')
) u;

-- Q9, Q10 - runway activity: one row per SEA take-off (departure, wheels up) or landing (arrival, wheels down).
-- Missed approaches are flagged (is_missed_approach = 1) and excluded from take-off/landing counts by default
-- (exclusion_reason 'missed approach'). Their time is the export's Event Time.
CREATE OR REPLACE VIEW v_runway_activity AS
SELECT
  a.flight_info_id, a.operation, a.call_sign, a.aircraft_type, a.weight_class_icao, a.runway, a.sea_date,
  a.activity, a.activity_time,
  DATE(a.activity_time) AS local_date,
  HOUR(a.activity_time) AS local_hour,
  a.is_missed_approach,
  CASE WHEN a.activity_time IS NULL THEN 'missing time'
       WHEN a.is_missed_approach = 1 THEN 'missed approach' END AS exclusion_reason,
  (a.activity_time IS NOT NULL AND a.is_missed_approach = 0) AS included
FROM (
  SELECT f.*,
         CASE f.operation WHEN 'Departure' THEN 'takeoff' WHEN 'Arrival' THEN 'landing' ELSE 'missed_approach' END AS activity,
         CASE f.operation WHEN 'Departure' THEN f.wheels_up WHEN 'Arrival' THEN f.wheels_down ELSE f.sea_event_time END AS activity_time,
         (f.operation = 'Missed Approach') AS is_missed_approach
  FROM flights f
) a;
