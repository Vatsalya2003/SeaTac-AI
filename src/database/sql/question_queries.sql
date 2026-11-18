-- SeaTac AI: tested reference queries for Port priority questions Q1-Q10, on the `seatac` metric views.
-- Draft for stage 2 (AI reference examples). Checked against PRJ/TEN_GROUND_TRUTH_ANSWERS.md.
-- Rules (docs/CLIENT_CONFIRMED_RULES.md, metric_rules.yaml):
--   * only included rows: exclusion_reason IS NULL
--   * default reporting day: 2025-08-08 SEA local; selection_time >= start and < next-day start
--   * calculate from full-precision values and return averages rounded to 2 decimals
--   * an average with no rows is NULL -> show "No data", never 0, a count with no events is 0
--   * fixed ORDER BY so the same question always gives the same rows
-- The backend connection selects the seatac database. These references contain SELECT statements only.

-- ---------------------------------------------------------------------------------------------
-- Q1  Taxi-in by aircraft type (wheels down -> in-block), minutes.  GT: 16 groups, N=525
--     e.g. B738 14.53 (81), B737 14.20 (9), A359 7.29 (3), Unknown 99.00 (1)
SELECT aircraft_type_group, ROUND(AVG(duration_min), 2) AS avg_taxi_in_min, COUNT(*) AS flights
FROM v_taxi_in
WHERE exclusion_reason IS NULL
  AND selection_time >= '2025-08-08 00:00:00'
  AND selection_time <  '2025-08-09 00:00:00'
GROUP BY aircraft_type_group
ORDER BY avg_taxi_in_min DESC, aircraft_type_group;

-- ---------------------------------------------------------------------------------------------
-- Q2a Taxi-out by local hour of OFF-BLOCK. SQL returns hours that have eligible flights.
--     A later backend presentation step may fill missing hours with avg NULL ("No data") and flights 0.
--     GT: N=528 (7 Aug-7 off-blocks excluded), 12:00 = 22.26 longest; 03:00 and 04:00 are absent.
SELECT selection_hour AS off_block_hour,
       ROUND(AVG(duration_min), 2) AS avg_taxi_out_min,
       COUNT(*) AS flights
FROM v_taxi_out
WHERE exclusion_reason IS NULL
  AND selection_time >= '2025-08-08 00:00:00'
  AND selection_time <  '2025-08-09 00:00:00'
GROUP BY selection_hour
ORDER BY selection_hour;

-- Q2b Taxi-out overall.  GT: 15.66 min, N=528
SELECT ROUND(AVG(duration_min), 2) AS avg_taxi_out_min, COUNT(*) AS flights
FROM v_taxi_out
WHERE exclusion_reason IS NULL
  AND selection_time >= '2025-08-08 00:00:00'
  AND selection_time <  '2025-08-09 00:00:00';

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
SELECT operation, ROUND(AVG(duration_sec), 2) AS avg_occupancy_sec,
       ROUND(AVG(duration_sec) / 60, 2) AS avg_occupancy_min,
       COUNT(*) AS flights
FROM v_runway_occupancy
WHERE exclusion_reason IS NULL
  AND selection_time >= '2025-08-08 00:00:00'
  AND selection_time <  '2025-08-09 00:00:00'
GROUP BY operation
ORDER BY operation;

-- Q4b Runway occupancy by runway.  GT: arr 34L 0.42 (493), 34R 0.65 (23), 34C 0.55 (1), 16R 0.37 (4),
--     dep 34R 1.29 (512), 34C 1.00 (11), 16L 0.76 (6), 16C 0.61 (3)
SELECT operation, runway, ROUND(AVG(duration_sec), 2) AS avg_occupancy_sec,
       ROUND(AVG(duration_sec) / 60, 2) AS avg_occupancy_min,
       COUNT(*) AS flights
FROM v_runway_occupancy
WHERE exclusion_reason IS NULL
  AND selection_time >= '2025-08-08 00:00:00'
  AND selection_time <  '2025-08-09 00:00:00'
GROUP BY operation, runway
ORDER BY operation, flights DESC, runway;

-- ---------------------------------------------------------------------------------------------
-- Q5  Take-off delay (wheels up - scheduled take-off), minutes, early departures kept, no threshold.
--     GT: 25.71 min (25.7060), N=533, 2 excluded (missing schedule)
SELECT ROUND(AVG(delay_min), 2) AS avg_takeoff_delay_min, COUNT(*) AS flights,
       SUM(delay_min < 0) AS early_departures
FROM v_takeoff_delay
WHERE exclusion_reason IS NULL
  AND selection_time >= '2025-08-08 00:00:00'
  AND selection_time <  '2025-08-09 00:00:00';

-- ---------------------------------------------------------------------------------------------
-- Q6a Taxi-in by ICAO weight class, every class listed (flights = 0 -> "No data").
--     GT: Medium 12.25 (517), Heavy 8.62 (8), Light / Unknown "No data"
SELECT w.weight_class_group, w.label, ROUND(AVG(t.duration_min), 2) AS avg_taxi_in_min,
       COUNT(t.flight_info_id) AS flights
FROM v_weight_classes w
LEFT JOIN v_taxi_in t ON t.weight_class_group = w.weight_class_group
     AND t.exclusion_reason IS NULL
     AND t.selection_time >= '2025-08-08 00:00:00'
     AND t.selection_time <  '2025-08-09 00:00:00'
GROUP BY w.weight_class_group, w.label, w.sort_order
ORDER BY w.sort_order;

-- Q6b Taxi-out by ICAO weight class.  GT: Medium 15.65 (520), Heavy 16.12 (8), others "No data"
SELECT w.weight_class_group, w.label, ROUND(AVG(t.duration_min), 2) AS avg_taxi_out_min,
       COUNT(t.flight_info_id) AS flights
FROM v_weight_classes w
LEFT JOIN v_taxi_out t ON t.weight_class_group = w.weight_class_group
     AND t.exclusion_reason IS NULL
     AND t.selection_time >= '2025-08-08 00:00:00'
     AND t.selection_time <  '2025-08-09 00:00:00'
GROUP BY w.weight_class_group, w.label, w.sort_order
ORDER BY w.sort_order;

-- Q6c Complete weight-class comparison: taxi-in and taxi-out returned together in one SELECT.
SELECT w.weight_class_group, w.label,
       arr.avg_taxi_in_min, COALESCE(arr.arrivals, 0) AS arrivals,
       dep.avg_taxi_out_min, COALESCE(dep.departures, 0) AS departures
FROM v_weight_classes w
LEFT JOIN (
  SELECT weight_class_group, ROUND(AVG(duration_min), 2) AS avg_taxi_in_min,
         COUNT(*) AS arrivals
  FROM v_taxi_in
  WHERE exclusion_reason IS NULL
    AND selection_time >= '2025-08-08 00:00:00'
    AND selection_time <  '2025-08-09 00:00:00'
  GROUP BY weight_class_group
) arr ON arr.weight_class_group = w.weight_class_group
LEFT JOIN (
  SELECT weight_class_group, ROUND(AVG(duration_min), 2) AS avg_taxi_out_min,
         COUNT(*) AS departures
  FROM v_taxi_out
  WHERE exclusion_reason IS NULL
    AND selection_time >= '2025-08-08 00:00:00'
    AND selection_time <  '2025-08-09 00:00:00'
  GROUP BY weight_class_group
) dep ON dep.weight_class_group = w.weight_class_group
ORDER BY w.sort_order;

-- ---------------------------------------------------------------------------------------------
-- Q7  Taxiway usage. PROVISIONAL: the export has no real per-section entry time, so selection_time is
--     a proxy. Strict reporting-window rule: only rows with a valid proxy time inside the window count.
--     Rows with 'missing time' or 'missing segment' are excluded. Tango, Hotel and Whiskey do not appear.
--     GT: 1,053 flights, 31 segments, B_28 512, E_5 363, B_15 224, B_13 208, B_20 127.
-- Q7a by taxiway section
SELECT taxiway_segment, taxiway_name, segment_number, COUNT(DISTINCT flight_info_id, operation) AS flights
FROM v_taxiway_usage
WHERE exclusion_reason IS NULL
  AND selection_time >= '2025-08-08 00:00:00'
  AND selection_time <  '2025-08-09 00:00:00'
GROUP BY taxiway_segment, taxiway_name, segment_number
ORDER BY flights DESC, taxiway_segment;

-- Q7b by taxiway letter.  GT: B (Bravo) 1,032, E 365, J 109, Z 21
SELECT taxiway_letter, taxiway_name, COUNT(DISTINCT flight_info_id, operation) AS flights
FROM v_taxiway_usage
WHERE exclusion_reason IS NULL
  AND selection_time >= '2025-08-08 00:00:00'
  AND selection_time <  '2025-08-09 00:00:00'
GROUP BY taxiway_letter, taxiway_name
ORDER BY flights DESC, taxiway_letter;

-- Q7c total flights with a usable taxiway record in the reporting window.  GT: 1,053
SELECT COUNT(DISTINCT flight_info_id, operation) AS flights
FROM v_taxiway_usage
WHERE exclusion_reason IS NULL
  AND selection_time >= '2025-08-08 00:00:00'
  AND selection_time <  '2025-08-09 00:00:00';

-- ---------------------------------------------------------------------------------------------
-- Q8  Wheels down -> parking, one overall average, minutes.  GT: 12.20 min (12.1954), N=525
SELECT ROUND(AVG(duration_min), 2) AS avg_taxi_in_min, COUNT(*) AS flights
FROM v_taxi_in
WHERE exclusion_reason IS NULL
  AND selection_time >= '2025-08-08 00:00:00'
  AND selection_time <  '2025-08-09 00:00:00';

-- ---------------------------------------------------------------------------------------------
-- Q9a Take-offs and completed landings per runway.  GT: 34R 512 + 23 = 535, 34L 1 + 497 = 498, ...
--     total 534 take-offs + 525 landings = 1,059, 1 take-off with no runway excluded
SELECT runway,
       SUM(activity = 'takeoff') AS takeoffs,
       SUM(activity = 'landing') AS landings,
       COUNT(*) AS total
FROM v_runway_activity
WHERE exclusion_reason IS NULL
  AND selection_time >= '2025-08-08 00:00:00'
  AND selection_time <  '2025-08-09 00:00:00'
GROUP BY runway
ORDER BY total DESC, runway;

-- Q9b Missed approaches, reported separately (not completed landings).  GT: 1, on 34L
SELECT runway, COUNT(*) AS missed_approaches
FROM v_runway_activity
WHERE is_missed_approach = 1
  AND selection_time >= '2025-08-08 00:00:00'
  AND selection_time <  '2025-08-09 00:00:00'
GROUP BY runway
ORDER BY missed_approaches DESC, runway;

-- Q9c Complete runway activity: take-offs, completed landings and missed approaches in one SELECT.
SELECT runway,
       SUM(activity = 'takeoff' AND exclusion_reason IS NULL) AS takeoffs,
       SUM(activity = 'landing' AND exclusion_reason IS NULL) AS landings,
       SUM(is_missed_approach = 1) AS missed_approaches,
       SUM(exclusion_reason IS NULL) AS completed_operations
FROM v_runway_activity
WHERE selection_time >= '2025-08-08 00:00:00'
  AND selection_time <  '2025-08-09 00:00:00'
  AND (exclusion_reason IS NULL OR is_missed_approach = 1)
GROUP BY runway
ORDER BY completed_operations DESC, runway;

-- ---------------------------------------------------------------------------------------------
-- Q10 Historical peak hours (take-offs + completed landings), ranked with ties.
--     SQL returns hours that have operations. A later backend presentation step may add zero-operation hours
--     and recompute their tied ranks. GT: 10:00 = 74 (rank 1), 08:00 = 69, 14:00 = 68,
--     18:00 = 66, 12:00 & 16:00 = 64 (rank 5); 03:00 is absent. History only, not a forecast.
SELECT local_hour, takeoffs, landings, operations, hour_rank
FROM v_peak_hours
WHERE local_date = '2025-08-08'
ORDER BY hour_rank, local_hour;
