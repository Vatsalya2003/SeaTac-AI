-- SeaTac AI: one tested query per Port priority question (Q1-Q10), on the `seatac` metric views.
-- Draft for stage 2 (templates mode). Checked against PRJ/TEN_GROUND_TRUTH_ANSWERS.md.
-- The chatbot runs the same logic from src/backend/templates.py. Keep the two in step.
-- Q6c and Q9c (combined tables) come from a teammate's review. Q7 and Q10 use the team rules chosen
-- 2026-11-14 (see docs/STAGE2_CHANGES.md): Q7 = 1,053 and Q10 19:00 = 58, which differ from the older
-- ground-truth assumptions (1,055 and 57) noted under each one.
-- Rules (docs/CLIENT_CONFIRMED_RULES.md, metric_rules.yaml):
--   * only included rows: exclusion_reason IS NULL
--   * default reporting day: selection_date = '2025-08-08' (SEA local, [00:00, next day 00:00))
--   * full precision in SQL, round to 2 decimals only when writing the answer text
--   * an average with no rows is NULL -> show "No data", never 0, a count with no events is 0
--   * fixed ORDER BY so the same question always gives the same rows
-- Runs as the read-only user seatac_reader (SELECT on the views only).

USE seatac;

-- ---------------------------------------------------------------------------------------------
-- Q1  Taxi-in by aircraft type (wheels down -> in-block), minutes.  GT: 16 groups, N=525
--     e.g. B738 14.53 (81), B737 14.20 (9), A359 7.29 (3), Unknown 99.00 (1)
SELECT aircraft_type_group, AVG(duration_min) AS avg_taxi_in_min, COUNT(*) AS flights
FROM v_taxi_in
WHERE exclusion_reason IS NULL AND selection_date = '2025-08-08'
GROUP BY aircraft_type_group
ORDER BY avg_taxi_in_min DESC, aircraft_type_group;

-- ---------------------------------------------------------------------------------------------
-- Q2a Taxi-out by local hour of OFF-BLOCK, all 24 hours (empty hours -> NULL = "No data").
--     GT: N=528 (7 Aug-7 off-blocks excluded), 12:00 = 22.26 longest, 03:00 and 04:00 "No data"
WITH RECURSIVE hours (h) AS (SELECT 0 UNION ALL SELECT h + 1 FROM hours WHERE h < 23)
SELECT hours.h AS off_block_hour, AVG(t.duration_min) AS avg_taxi_out_min, COUNT(t.flight_info_id) AS flights
FROM hours
LEFT JOIN v_taxi_out t ON t.selection_hour = hours.h
     AND t.exclusion_reason IS NULL AND t.selection_date = '2025-08-08'
GROUP BY hours.h
ORDER BY hours.h;

-- Q2b Taxi-out overall.  GT: 15.66 min, N=528
SELECT AVG(duration_min) AS avg_taxi_out_min, COUNT(*) AS flights
FROM v_taxi_out
WHERE exclusion_reason IS NULL AND selection_date = '2025-08-08';

-- ---------------------------------------------------------------------------------------------
-- Q3  Movement area: highest number of aircraft in the area at the same time, per local hour.
--     PROVISIONAL (hatched-area mapping pending). GT: 10:00 = 22, 12:00 = 20, 22:00 = 19, 03:00 = 0,
--     1,052 intervals used, 8 excluded.  This is THE Q3 answer: average durations are the wrong measure.
SELECT local_date, local_hour, max_aircraft_in_area, intervals_used, intervals_excluded
FROM v_movement_area_hourly_peak
WHERE local_date = '2025-08-08'
ORDER BY local_date, local_hour;

-- ---------------------------------------------------------------------------------------------
-- Q4a Runway occupancy, arrivals and departures separately.  GT: arr 0.43 min / 25.69 s (521),
--     dep 1.275 min / 76.50 s (532, accept 1.27 or 1.28). Never near 0.76 / 1.90 min (export column).
SELECT operation, AVG(duration_sec) AS avg_occupancy_sec, AVG(duration_sec) / 60 AS avg_occupancy_min,
       COUNT(*) AS flights
FROM v_runway_occupancy
WHERE exclusion_reason IS NULL AND selection_date = '2025-08-08'
GROUP BY operation
ORDER BY operation;

-- Q4b Runway occupancy by runway.  GT: arr 34L 0.42 (493), 34R 0.65 (23), 34C 0.55 (1), 16R 0.37 (4),
--     dep 34R 1.29 (512), 34C 1.00 (11), 16L 0.76 (6), 16C 0.61 (3)
SELECT operation, runway, AVG(duration_sec) AS avg_occupancy_sec, AVG(duration_sec) / 60 AS avg_occupancy_min,
       COUNT(*) AS flights
FROM v_runway_occupancy
WHERE exclusion_reason IS NULL AND selection_date = '2025-08-08'
GROUP BY operation, runway
ORDER BY operation, flights DESC, runway;

-- ---------------------------------------------------------------------------------------------
-- Q5  Take-off delay (wheels up - scheduled take-off), minutes, early departures kept, no threshold.
--     GT: 25.71 min (25.7060), N=533, 2 excluded (missing schedule)
SELECT AVG(delay_min) AS avg_takeoff_delay_min, COUNT(*) AS flights,
       SUM(delay_min < 0) AS early_departures
FROM v_takeoff_delay
WHERE exclusion_reason IS NULL AND selection_date = '2025-08-08';

-- ---------------------------------------------------------------------------------------------
-- Q6a Taxi-in by ICAO weight class, every class listed (flights = 0 -> "No data").
--     GT: Medium 12.25 (517), Heavy 8.62 (8), Light / Unknown "No data"
SELECT w.weight_class_group, w.label, AVG(t.duration_min) AS avg_taxi_in_min, COUNT(t.flight_info_id) AS flights
FROM v_weight_classes w
LEFT JOIN v_taxi_in t ON t.weight_class_group = w.weight_class_group
     AND t.exclusion_reason IS NULL AND t.selection_date = '2025-08-08'
GROUP BY w.weight_class_group, w.label, w.sort_order
ORDER BY w.sort_order;

-- Q6b Taxi-out by ICAO weight class.  GT: Medium 15.65 (520), Heavy 16.12 (8), others "No data"
SELECT w.weight_class_group, w.label, AVG(t.duration_min) AS avg_taxi_out_min, COUNT(t.flight_info_id) AS flights
FROM v_weight_classes w
LEFT JOIN v_taxi_out t ON t.weight_class_group = w.weight_class_group
     AND t.exclusion_reason IS NULL AND t.selection_date = '2025-08-08'
GROUP BY w.weight_class_group, w.label, w.sort_order
ORDER BY w.sort_order;

-- Q6c Taxi-in and taxi-out by weight class in one table (every class listed, empty -> NULL / 0).
SELECT w.weight_class_group, w.label,
       arr.avg_taxi_in_min, COALESCE(arr.arrivals, 0) AS arrivals,
       dep.avg_taxi_out_min, COALESCE(dep.departures, 0) AS departures
FROM v_weight_classes w
LEFT JOIN (SELECT weight_class_group, AVG(duration_min) AS avg_taxi_in_min, COUNT(*) AS arrivals
           FROM v_taxi_in
           WHERE exclusion_reason IS NULL AND selection_date = '2025-08-08'
           GROUP BY weight_class_group) arr ON arr.weight_class_group = w.weight_class_group
LEFT JOIN (SELECT weight_class_group, AVG(duration_min) AS avg_taxi_out_min, COUNT(*) AS departures
           FROM v_taxi_out
           WHERE exclusion_reason IS NULL AND selection_date = '2025-08-08'
           GROUP BY weight_class_group) dep ON dep.weight_class_group = w.weight_class_group
ORDER BY w.sort_order;

-- ---------------------------------------------------------------------------------------------
-- Q7  Taxiway usage.  PROVISIONAL. Team rule: the Port says to select by section-entry time. The export
--     has none, so the proxy selection_time (metric_rules.yaml) selects the Aug 8 window, start inclusive
--     and end exclusive. Rows with 'missing time' or 'missing segment' are excluded. Tango, Hotel and
--     Whiskey do not appear.
--     Expected: 1,053 flights, 31 sections, B_28 512, E_5 363, B_15 224, B_13 208, B_20 127.
--     Not counted, of 1,061 legs: 1 proxy time outside Aug 8, 1 missing time, 6 no taxiway recorded.
--     (Older ground-truth assumption, all flights with a segment and no date filter: 1,055, B_28 513, B 1,037.)
-- Q7a by taxiway section
SELECT taxiway_segment, taxiway_name, segment_number, COUNT(DISTINCT flight_info_id, operation) AS flights
FROM v_taxiway_usage
WHERE exclusion_reason IS NULL
  AND selection_time >= '2025-08-08 00:00:00'
  AND selection_time <  '2025-08-09 00:00:00'
GROUP BY taxiway_segment, taxiway_name, segment_number
ORDER BY flights DESC, taxiway_segment;

-- Q7b by taxiway letter.  Expected: B (Bravo) 1,032, E 365, J 109, Z 21
SELECT taxiway_letter, taxiway_name, COUNT(DISTINCT flight_info_id, operation) AS flights
FROM v_taxiway_usage
WHERE exclusion_reason IS NULL
  AND selection_time >= '2025-08-08 00:00:00'
  AND selection_time <  '2025-08-09 00:00:00'
GROUP BY taxiway_letter, taxiway_name
ORDER BY flights DESC, taxiway_letter;

-- Q7c total flights with a usable taxiway record in the reporting window.  Expected: 1,053
SELECT COUNT(DISTINCT flight_info_id, operation) AS flights
FROM v_taxiway_usage
WHERE exclusion_reason IS NULL
  AND selection_time >= '2025-08-08 00:00:00'
  AND selection_time <  '2025-08-09 00:00:00';

-- ---------------------------------------------------------------------------------------------
-- Q8  Wheels down -> parking, one overall average, minutes.  GT: 12.20 min (12.1954), N=525
SELECT AVG(duration_min) AS avg_taxi_in_min, COUNT(*) AS flights
FROM v_taxi_in
WHERE exclusion_reason IS NULL AND selection_date = '2025-08-08';

-- ---------------------------------------------------------------------------------------------
-- Q9a Take-offs and completed landings per runway.  GT: 34R 512 + 23 = 535, 34L 1 + 497 = 498, ...
--     total 534 take-offs + 525 landings = 1,059, 1 take-off with no runway excluded
SELECT runway,
       SUM(activity = 'takeoff') AS takeoffs,
       SUM(activity = 'landing') AS landings,
       COUNT(*) AS total
FROM v_runway_activity
WHERE exclusion_reason IS NULL AND selection_date = '2025-08-08'
GROUP BY runway
ORDER BY total DESC, runway;

-- Q9b Missed approaches, reported separately (not completed landings).  GT: 1, on 34L
SELECT runway, COUNT(*) AS missed_approaches
FROM v_runway_activity
WHERE is_missed_approach = 1 AND selection_date = '2025-08-08'
GROUP BY runway
ORDER BY missed_approaches DESC, runway;

-- Q9c Take-offs, completed landings and missed approaches per runway in one table.
SELECT runway,
       SUM(activity = 'takeoff' AND exclusion_reason IS NULL) AS takeoffs,
       SUM(activity = 'landing' AND exclusion_reason IS NULL) AS landings,
       SUM(is_missed_approach = 1) AS missed_approaches,
       SUM(exclusion_reason IS NULL) AS completed_operations
FROM v_runway_activity
WHERE selection_date = '2025-08-08'
  AND (exclusion_reason IS NULL OR is_missed_approach = 1)
GROUP BY runway
ORDER BY completed_operations DESC, runway;

-- ---------------------------------------------------------------------------------------------
-- Q10 Historical peak hours (take-offs + completed landings), all 24 hours, ranked with ties.
--     Team rule: v_peak_hours counts every take-off and completed landing. A runway is not needed, so the
--     take-off with no runway counts: 535 take-offs + 525 landings = 1,060. The missed approach is not counted.
--     GT: 10:00 = 74 (rank 1), 08:00 = 69, 14:00 = 68, 18:00 = 66, 12:00 & 16:00 = 64 (rank 5),
--     19:00 = 58 (rank 12, the ground truth's "if included" case, otherwise 57), 03:00 = 0 (rank 24).
--     History only: never phrase as a forecast.
WITH RECURSIVE hours (h) AS (SELECT 0 UNION ALL SELECT h + 1 FROM hours WHERE h < 23)
SELECT hours.h AS local_hour,
       COALESCE(p.takeoffs, 0) AS takeoffs,
       COALESCE(p.landings, 0) AS landings,
       COALESCE(p.operations, 0) AS operations,
       RANK() OVER (ORDER BY COALESCE(p.operations, 0) DESC) AS hour_rank
FROM hours
LEFT JOIN v_peak_hours p ON p.local_hour = hours.h AND p.local_date = '2025-08-08'
ORDER BY hour_rank, local_hour;
