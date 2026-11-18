-- SeaTac AI: SQL Queries for Questions 1-5
-- Database: seatac
-- These queries use the validated metric views in the seatac database.


-- ============================================================
-- Question 1: Taxi-In Performance by Aircraft Type
-- What is the average taxi-in time for each aircraft type?
-- Taxi-in: wheels down (touchdown) to actual in-block.
-- Unit: minutes
-- ============================================================

SELECT
    aircraft_type_group,
    ROUND(AVG(duration_sec) / 60, 2) AS avg_taxi_in_min,
    COUNT(*) AS flights
FROM seatac.v_taxi_in
WHERE exclusion_reason IS NULL
GROUP BY aircraft_type_group
ORDER BY avg_taxi_in_min DESC;


-- ============================================================
-- Question 2: Taxi-Out Performance by Hour of Day
-- What is the average taxi-out time for each hour of the day?
-- Taxi-out: actual off-block to wheels up (takeoff).
-- The hour is based on the actual off-block time in SEA local time.
-- Unit: minutes
-- ============================================================

SELECT
    selection_hour,
    ROUND(AVG(duration_sec) / 60, 2) AS avg_taxi_out_min,
    COUNT(*) AS flights
FROM seatac.v_taxi_out
WHERE exclusion_reason IS NULL
GROUP BY selection_hour
ORDER BY selection_hour;


-- ============================================================
-- Question 3: Movement Area Occupancy
-- How many aircraft were in the movement area at the same time?
-- This query reports the maximum simultaneous aircraft count
-- for each local hour.
-- ============================================================

SELECT
    local_date,
    local_hour,
    max_aircraft_in_area,
    intervals_used,
    intervals_excluded,
    excluded_missing_time,
    excluded_negative_duration
FROM seatac.v_movement_area_hourly_peak
ORDER BY local_date, local_hour;


-- ============================================================
-- Question 4: Runway Occupancy Time
-- What is the average runway occupancy time for arrivals and
-- departures?
-- Arrival: wheels down to runway exit.
-- Departure: runway entrance to wheels up.
-- Unit: seconds
-- ============================================================

SELECT
    operation,
    ROUND(AVG(duration_sec), 2) AS avg_runway_occupancy_sec,
    COUNT(*) AS flights
FROM seatac.v_runway_occupancy
WHERE exclusion_reason IS NULL
GROUP BY operation
ORDER BY operation;


-- ============================================================
-- Question 5: Wheels-Up Delay Tracker
-- How do actual takeoff times compare with scheduled takeoff times?
-- Delay: wheels up minus scheduled takeoff time.
-- Positive values are late; negative values are early and remain valid.
-- Unit: minutes
-- ============================================================

SELECT
    ROUND(AVG(delay_sec) / 60, 2) AS avg_takeoff_delay_min,
    SUM(CASE WHEN delay_sec > 0 THEN 1 ELSE 0 END) AS late_flights,
    SUM(CASE WHEN delay_sec < 0 THEN 1 ELSE 0 END) AS early_flights,
    SUM(CASE WHEN delay_sec = 0 THEN 1 ELSE 0 END) AS on_time_flights,
    COUNT(*) AS flights
FROM seatac.v_takeoff_delay
WHERE exclusion_reason IS NULL;
