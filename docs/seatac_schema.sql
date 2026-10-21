-- MySQL dump 10.13  Distrib 8.4.8, for macos15 (arm64)
--
-- Host: localhost    Database: seatac
-- ------------------------------------------------------
-- Server version	8.4.8

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `aircraft_types`
--

DROP TABLE IF EXISTS `aircraft_types`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `aircraft_types` (
  `aircraft_type` varchar(20) NOT NULL,
  `engine_class` varchar(20) DEFAULT NULL,
  `wake_category` varchar(10) DEFAULT NULL,
  `design_group` varchar(10) DEFAULT NULL,
  `wingspan_ft` decimal(8,2) DEFAULT NULL,
  `fuselage_ft` decimal(8,2) DEFAULT NULL,
  `max_takeoff_weight_kg` int DEFAULT NULL,
  `max_landing_weight_kg` int DEFAULT NULL,
  PRIMARY KEY (`aircraft_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='One row per FAA aircraft type; most common attribute value when the export disagrees';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `flights`
--

DROP TABLE IF EXISTS `flights`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `flights` (
  `flight_info_id` bigint NOT NULL,
  `operation` varchar(20) NOT NULL,
  `call_sign` varchar(20) DEFAULT NULL,
  `carrier` varchar(20) DEFAULT NULL,
  `carrier_group` varchar(50) DEFAULT NULL,
  `aircraft_type` varchar(20) DEFAULT NULL,
  `weight_class_icao` char(1) DEFAULT NULL,
  `origin_airport` varchar(10) DEFAULT NULL,
  `destination_airport` varchar(10) DEFAULT NULL,
  `international_domestic` varchar(20) DEFAULT NULL,
  `runway` varchar(10) DEFAULT NULL,
  `gate` varchar(30) DEFAULT NULL,
  `parking_area` varchar(50) DEFAULT NULL,
  `taxiway_runway` varchar(50) DEFAULT NULL,
  `taxiway_ramp` varchar(50) DEFAULT NULL,
  `scheduled_off_block` datetime DEFAULT NULL,
  `actual_off_block` datetime DEFAULT NULL,
  `scheduled_take_off` datetime DEFAULT NULL,
  `wheels_up` datetime DEFAULT NULL,
  `scheduled_landing` datetime DEFAULT NULL,
  `wheels_down` datetime DEFAULT NULL,
  `scheduled_in_block` datetime DEFAULT NULL,
  `actual_in_block` datetime DEFAULT NULL,
  `runway_entrance` datetime DEFAULT NULL,
  `runway_exit` datetime DEFAULT NULL,
  `movement_area_entrance` datetime DEFAULT NULL,
  `movement_area_exit` datetime DEFAULT NULL,
  `sea_event_time` datetime DEFAULT NULL,
  `passenger_count` int DEFAULT NULL,
  `sea_date` date DEFAULT NULL,
  `sys_taxi_in_sec` int DEFAULT NULL,
  `sys_taxi_out_sec` int DEFAULT NULL,
  `sys_runway_occupancy_sec` int DEFAULT NULL,
  `source_file` varchar(255) NOT NULL,
  PRIMARY KEY (`flight_info_id`,`operation`),
  KEY `idx_flights_operation` (`operation`),
  KEY `idx_flights_aircraft_type` (`aircraft_type`),
  KEY `idx_flights_runway` (`runway`),
  KEY `idx_flights_sea_date` (`sea_date`),
  CONSTRAINT `fk_flights_aircraft_type` FOREIGN KEY (`aircraft_type`) REFERENCES `aircraft_types` (`aircraft_type`),
  CONSTRAINT `fk_flights_raw` FOREIGN KEY (`flight_info_id`, `operation`) REFERENCES `raw_flight_details` (`flight_info_id`, `operation`),
  CONSTRAINT `chk_flights_operation` CHECK ((`operation` in (_utf8mb4'Arrival',_utf8mb4'Departure',_utf8mb4'Missed Approach')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='One row per flight leg at SEA. SEA-side times only (other-airport times are NULL; originals in raw_flight_details). Local PDT, not shifted';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `raw_flight_details`
--

DROP TABLE IF EXISTS `raw_flight_details`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `raw_flight_details` (
  `flight_info_id` bigint NOT NULL,
  `operation` varchar(20) NOT NULL,
  `APREQ (ATC) (PDT)` datetime DEFAULT NULL,
  `Actual In (PDT)` datetime DEFAULT NULL,
  `Actual In Block Time (AODB) (PDT)` datetime DEFAULT NULL,
  `Actual In Block Time (ATC) (PDT)` datetime DEFAULT NULL,
  `Actual In Block Time (Aerobahn) (PDT)` datetime DEFAULT NULL,
  `Actual In Block Time (Surveillance) (PDT)` datetime DEFAULT NULL,
  `Actual In Block Time (VDGS) (PDT)` datetime DEFAULT NULL,
  `Actual Landing Time (AODB) (PDT)` datetime DEFAULT NULL,
  `Actual Landing Time (ATC) (PDT)` datetime DEFAULT NULL,
  `Actual Landing Time (Aerobahn) (PDT)` datetime DEFAULT NULL,
  `Actual Landing Time (Surveillance) (PDT)` datetime DEFAULT NULL,
  `Actual Landing Time (Third Party) (PDT)` datetime DEFAULT NULL,
  `Actual Off (PDT)` datetime DEFAULT NULL,
  `Actual Off Block Time (AODB) (PDT)` datetime DEFAULT NULL,
  `Actual Off Block Time (ATC) (PDT)` datetime DEFAULT NULL,
  `Actual Off Block Time (Aerobahn) (PDT)` datetime DEFAULT NULL,
  `Actual Off Block Time (Surveillance) (PDT)` datetime DEFAULT NULL,
  `Actual Off Block Time (VDGS) (PDT)` datetime DEFAULT NULL,
  `Actual On (PDT)` datetime DEFAULT NULL,
  `Actual Out (PDT)` datetime DEFAULT NULL,
  `Actual Pushback Start Time (Surveillance) (PDT)` datetime DEFAULT NULL,
  `Actual Start of Boarding Time (Aerobahn) (PDT)` datetime DEFAULT NULL,
  `Actual Start of Boarding Time (Carrier) (PDT)` datetime DEFAULT NULL,
  `Actual Take Off Time (AODB) (PDT)` datetime DEFAULT NULL,
  `Actual Take Off Time (ATC) (PDT)` datetime DEFAULT NULL,
  `Actual Take Off Time (Aerobahn) (PDT)` datetime DEFAULT NULL,
  `Actual Take Off Time (Surveillance) (PDT)` datetime DEFAULT NULL,
  `Actual Take Off Time (Third Party) (PDT)` datetime DEFAULT NULL,
  `Actual Taxi In Time` time DEFAULT NULL,
  `Actual Taxi Out Time` time DEFAULT NULL,
  `Aircraft Cabin Door Closed (Carrier) (PDT)` datetime DEFAULT NULL,
  `Aircraft Type (AODB)` text,
  `Aircraft Type (Carrier)` text,
  `Aircraft Type (FAA)` text,
  `Aircraft/Vehicle Type (Third Party)` text,
  `Arrival Delay (Aerobahn)` text,
  `Arrival Delay (Carrier)` text,
  `Arrival Procedure` text,
  `Arrival Procedure (Filed)` text,
  `Assigned Gate` text,
  `At Gate (inbound) (PDT)` datetime DEFAULT NULL,
  `At Parking Area (inbound) (PDT)` datetime DEFAULT NULL,
  `At Spot (inbound) (PDT)` datetime DEFAULT NULL,
  `At Spot (outbound) (PDT)` datetime DEFAULT NULL,
  `Calculated Takeoff Time (ATC) (PDT)` datetime DEFAULT NULL,
  `Calculated Takeoff Time (Aerobahn) (PDT)` datetime DEFAULT NULL,
  `Call Sign` text,
  `Call Sign (AODB)` text,
  `Call Sign (FAA)` text,
  `Call Sign (Surv)` text,
  `Call Sign (Third Party)` text,
  `Call Sign (VDGS)` text,
  `Call Sign Inbound` text,
  `Call Sign Outbound` text,
  `Carrier` text,
  `Carrier Group` text,
  `Clear Active (PDT)` datetime DEFAULT NULL,
  `Codeshares` text,
  `CrossThreshold (PDT)` datetime DEFAULT NULL,
  `Crossbleed Required (Manual)` tinyint(1) DEFAULT NULL,
  `Departure Delay (Aerobahn)` text,
  `Departure Delay (Carrier)` text,
  `Departure Procedure` text,
  `Departure Procedure (Filed)` text,
  `Design Group (FAA)` bigint DEFAULT NULL,
  `Destination Airport` text,
  `Destination Airport (ICAO)` text,
  `Diversion Destination Airport` text,
  `Diversion Destination Airport (ICAO)` text,
  `Diversion Status` text,
  `Diversion Time (PDT)` datetime DEFAULT NULL,
  `Earliest Off Block Time (ATC) (PDT)` datetime DEFAULT NULL,
  `Engine Class` text,
  `Engine Model` text,
  `Engine Type` text,
  `Estimated Departure Clearance Time (ATC) (PDT)` datetime DEFAULT NULL,
  `Estimated Departure Clearance Time (Aerobahn) (PDT)` datetime DEFAULT NULL,
  `Estimated In Block Time (ATC) (PDT)` datetime DEFAULT NULL,
  `Estimated Landing Time (ATC) (PDT)` datetime DEFAULT NULL,
  `Estimated Off Block Time (ATC) (PDT)` datetime DEFAULT NULL,
  `Estimated Take Off Time (ATC) (PDT)` datetime DEFAULT NULL,
  `Estimated Tow Off Time (AODB) (PDT)` datetime DEFAULT NULL,
  `Estimated Tow On Time (AODB) (PDT)` datetime DEFAULT NULL,
  `Event Time (PDT)` datetime DEFAULT NULL,
  `Excess Gate Occupancy Time (Aerobahn)` text,
  `Excess Gate Occupancy Time (Carrier)` text,
  `Filed Speed in Knots (ATC)` bigint DEFAULT NULL,
  `First Fix` text,
  `Flight ID` text,
  `Flight ID Inbound` text,
  `Flight ID Outbound` text,
  `Flight Number` bigint DEFAULT NULL,
  `Flight Origination Date` datetime DEFAULT NULL,
  `Flight Origination Date (AODB)` datetime DEFAULT NULL,
  `Flight Origination Date (Carrier)` datetime DEFAULT NULL,
  `Flight Route` text,
  `Flight Route (Filed)` text,
  `Flight Type (AODB)` text,
  `Fuselage (feet)` double DEFAULT NULL,
  `Fuselage (meters)` double DEFAULT NULL,
  `Gate` text,
  `Gate Assigned (AODB)` text,
  `Gate Assigned (Aerobahn)` text,
  `Gate Assigned (Manual)` text,
  `Gate Assigned - Hardstand (Carrier)` text,
  `Gate Occupancy Start Time (Carrier) (PDT)` datetime DEFAULT NULL,
  `Gate Occupancy Time` time DEFAULT NULL,
  `Gate Occupancy Time (Carrier)` time DEFAULT NULL,
  `Hold Cnt` bigint DEFAULT NULL,
  `Hold Dur` time DEFAULT NULL,
  `Hold End (PDT)` datetime DEFAULT NULL,
  `Hold Start (PDT)` datetime DEFAULT NULL,
  `Hold Tot Dur` time DEFAULT NULL,
  `Inbound - Actual In Block Time (Carrier) (PDT)` datetime DEFAULT NULL,
  `Inbound - Actual Landing Time (ATC) (PDT)` datetime DEFAULT NULL,
  `Inbound - Actual Takeoff Time (ATC) (PDT)` datetime DEFAULT NULL,
  `International or Domestic Indicator` text,
  `Is On Time` tinyint(1) DEFAULT NULL,
  `Last Fix` text,
  `Left Gate (outbound) (PDT)` datetime DEFAULT NULL,
  `Left Parking Area (outbound) (PDT)` datetime DEFAULT NULL,
  `Manually Corrected Flight` tinyint(1) DEFAULT NULL,
  `Marketing Carrier` text,
  `Maximum Landing Weight (kg)` bigint DEFAULT NULL,
  `Maximum Landing Weight (lbs)` bigint DEFAULT NULL,
  `Maximum Takeoff Weight (kg)` bigint DEFAULT NULL,
  `Maximum Takeoff Weight (lbs)` bigint DEFAULT NULL,
  `Metering Compliance Status` text,
  `Metering Compliance Status - Simple` text,
  `Metering Status (Surveillance)` text,
  `Mode 3/A` bigint DEFAULT NULL,
  `Mode 3/A (Aerobahn)` bigint DEFAULT NULL,
  `Mode S` text,
  `Model` text,
  `Movement Area Entrance Time (PDT)` datetime DEFAULT NULL,
  `Movement Area Exit Time (PDT)` datetime DEFAULT NULL,
  `Movement Time` time DEFAULT NULL,
  `Number Of Engines` bigint DEFAULT NULL,
  `On Active (outbound) (PDT)` datetime DEFAULT NULL,
  `On Time Status` text,
  `Operator Email` text,
  `Origination Airport` text,
  `Origination Airport (ICAO)` text,
  `Parking Area` text,
  `Parking Region Time (Aerobahn)` time DEFAULT NULL,
  `Passenger Count (AODB)` bigint DEFAULT NULL,
  `Passenger Count Local (AODB)` bigint DEFAULT NULL,
  `Ramp Actual` text,
  `Ramp Time` time DEFAULT NULL,
  `Recovery Exists` tinyint(1) DEFAULT NULL,
  `Registration` text,
  `Registration (AODB)` text,
  `Registration (ATC)` text,
  `Registration (Carrier)` text,
  `Registration (Surveillance)` text,
  `Registration (Third Party)` text,
  `Registration (VDGS)` text,
  `Route Remarks Keywords (ATC)` text,
  `Runup Reposition Required (Manual)` tinyint(1) DEFAULT NULL,
  `Runway` text,
  `Runway Assigned (Aerobahn)` text,
  `Runway Entrance Time (PDT)` datetime DEFAULT NULL,
  `Runway Exit Time (PDT)` datetime DEFAULT NULL,
  `Runway Occupancy Time` time DEFAULT NULL,
  `Runway Region Occupancy Time` time DEFAULT NULL,
  `SIBT Date` datetime DEFAULT NULL,
  `SOBT Date` datetime DEFAULT NULL,
  `Scheduled In (PDT)` datetime DEFAULT NULL,
  `Scheduled In Block Time (AODB) (PDT)` datetime DEFAULT NULL,
  `Scheduled In Block Time (Aerobahn) (PDT)` datetime DEFAULT NULL,
  `Scheduled In Block Time (VDGS) (PDT)` datetime DEFAULT NULL,
  `Scheduled Landing Time (Aerobahn) (PDT)` datetime DEFAULT NULL,
  `Scheduled Landing Time (Third Party) (PDT)` datetime DEFAULT NULL,
  `Scheduled Off (ASDI) (PDT)` datetime DEFAULT NULL,
  `Scheduled Off Block Time (AODB) (PDT)` datetime DEFAULT NULL,
  `Scheduled Off Block Time (ATC) (PDT)` datetime DEFAULT NULL,
  `Scheduled Off Block Time (Aerobahn) (PDT)` datetime DEFAULT NULL,
  `Scheduled Off Block Time (VDGS) (PDT)` datetime DEFAULT NULL,
  `Scheduled On (ASDI) (PDT)` datetime DEFAULT NULL,
  `Scheduled Out (PDT)` datetime DEFAULT NULL,
  `Scheduled Take Off Time (Aerobahn) (PDT)` datetime DEFAULT NULL,
  `Scheduled Take Off Time (Third Party) (PDT)` datetime DEFAULT NULL,
  `Ship Number` bigint DEFAULT NULL,
  `Ship Number (AODB)` bigint DEFAULT NULL,
  `Source Specific Id (AODB)` bigint DEFAULT NULL,
  `Source Specific Id (ATC)` bigint DEFAULT NULL,
  `Source Specific Id (Third Party)` text,
  `Source Specific Id (VDGS)` text,
  `Special Aircraft Qualifier` text,
  `Spot` text,
  `Stationary Taxi Total Duration` time DEFAULT NULL,
  `TMAT Deviation` time DEFAULT NULL,
  `TOBT Change Total` bigint DEFAULT NULL,
  `TOBT Update Time (PDT)` datetime DEFAULT NULL,
  `Target ID` bigint DEFAULT NULL,
  `Target Initialization Time  (PDT)` datetime DEFAULT NULL,
  `Target Off Block Time (Aerobahn) (PDT)` datetime DEFAULT NULL,
  `Target Off Block Time (Carrier) (PDT)` datetime DEFAULT NULL,
  `Target Take Off Time (Aerobahn) (PDT)` datetime DEFAULT NULL,
  `Taxiway Used to Enter/Exit Ramp` text,
  `Taxiway Used to Enter/Exit Runway` text,
  `Terminal Actual` text,
  `Terminal Assigned (AODB)` text,
  `Terminal Assigned (Aerobahn)` text,
  `Terminal Assigned (Carrier)` text,
  `Terminal Assigned (Manual)` text,
  `Terminated` tinyint(1) DEFAULT NULL,
  `Total Passenger Count` bigint DEFAULT NULL,
  `Total Seat Count` bigint DEFAULT NULL,
  `Total Taxi Time` time DEFAULT NULL,
  `Transition Fix` text,
  `Turnaround End Time (Video) (PDT)` datetime DEFAULT NULL,
  `Turnaround Start Time (Video) (PDT)` datetime DEFAULT NULL,
  `Wake Category (Aerobahn)` text,
  `Weight Class` text,
  `Weight Class (ICAO)` text,
  `Weight Class (USA)` text,
  `Wheels Down (PDT)` datetime DEFAULT NULL,
  `Wheels Up (PDT)` datetime DEFAULT NULL,
  `Wingspan (feet)` double DEFAULT NULL,
  `Wingspan (meters)` double DEFAULT NULL,
  PRIMARY KEY (`flight_info_id`,`operation`),
  CONSTRAINT `chk_raw_operation` CHECK ((`operation` in (_utf8mb4'Arrival',_utf8mb4'Departure',_utf8mb4'Missed Approach')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='Every non-empty column of the Aerobahn export, original names';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Temporary view structure for view `v_movement_area`
--

DROP TABLE IF EXISTS `v_movement_area`;
/*!50001 DROP VIEW IF EXISTS `v_movement_area`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `v_movement_area` AS SELECT 
 1 AS `flight_info_id`,
 1 AS `operation`,
 1 AS `call_sign`,
 1 AS `aircraft_type`,
 1 AS `aircraft_type_group`,
 1 AS `weight_class_icao`,
 1 AS `runway`,
 1 AS `sea_date`,
 1 AS `start_time`,
 1 AS `end_time`,
 1 AS `selection_time`,
 1 AS `selection_date`,
 1 AS `selection_hour`,
 1 AS `duration_sec`,
 1 AS `duration_min`,
 1 AS `exclusion_reason`,
 1 AS `included`*/;
SET character_set_client = @saved_cs_client;

--
-- Temporary view structure for view `v_movement_area_hourly_peak`
--

DROP TABLE IF EXISTS `v_movement_area_hourly_peak`;
/*!50001 DROP VIEW IF EXISTS `v_movement_area_hourly_peak`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `v_movement_area_hourly_peak` AS SELECT 
 1 AS `local_date`,
 1 AS `local_hour`,
 1 AS `max_aircraft_in_area`,
 1 AS `intervals_used`,
 1 AS `intervals_excluded`,
 1 AS `excluded_missing_time`,
 1 AS `excluded_negative_duration`*/;
SET character_set_client = @saved_cs_client;

--
-- Temporary view structure for view `v_peak_hours`
--

DROP TABLE IF EXISTS `v_peak_hours`;
/*!50001 DROP VIEW IF EXISTS `v_peak_hours`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `v_peak_hours` AS SELECT 
 1 AS `local_date`,
 1 AS `local_hour`,
 1 AS `operations`,
 1 AS `takeoffs`,
 1 AS `landings`,
 1 AS `hour_rank`*/;
SET character_set_client = @saved_cs_client;

--
-- Temporary view structure for view `v_runway_activity`
--

DROP TABLE IF EXISTS `v_runway_activity`;
/*!50001 DROP VIEW IF EXISTS `v_runway_activity`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `v_runway_activity` AS SELECT 
 1 AS `flight_info_id`,
 1 AS `operation`,
 1 AS `call_sign`,
 1 AS `aircraft_type`,
 1 AS `weight_class_icao`,
 1 AS `runway`,
 1 AS `sea_date`,
 1 AS `activity`,
 1 AS `activity_time`,
 1 AS `selection_time`,
 1 AS `selection_date`,
 1 AS `selection_hour`,
 1 AS `local_date`,
 1 AS `local_hour`,
 1 AS `is_missed_approach`,
 1 AS `exclusion_reason`,
 1 AS `included`*/;
SET character_set_client = @saved_cs_client;

--
-- Temporary view structure for view `v_runway_occupancy`
--

DROP TABLE IF EXISTS `v_runway_occupancy`;
/*!50001 DROP VIEW IF EXISTS `v_runway_occupancy`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `v_runway_occupancy` AS SELECT 
 1 AS `flight_info_id`,
 1 AS `operation`,
 1 AS `call_sign`,
 1 AS `aircraft_type`,
 1 AS `aircraft_type_group`,
 1 AS `weight_class_icao`,
 1 AS `runway`,
 1 AS `sea_date`,
 1 AS `start_time`,
 1 AS `end_time`,
 1 AS `selection_time`,
 1 AS `selection_date`,
 1 AS `selection_hour`,
 1 AS `duration_sec`,
 1 AS `sys_runway_occupancy_sec`,
 1 AS `exclusion_reason`,
 1 AS `included`*/;
SET character_set_client = @saved_cs_client;

--
-- Temporary view structure for view `v_takeoff_delay`
--

DROP TABLE IF EXISTS `v_takeoff_delay`;
/*!50001 DROP VIEW IF EXISTS `v_takeoff_delay`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `v_takeoff_delay` AS SELECT 
 1 AS `flight_info_id`,
 1 AS `operation`,
 1 AS `call_sign`,
 1 AS `carrier`,
 1 AS `aircraft_type`,
 1 AS `aircraft_type_group`,
 1 AS `weight_class_icao`,
 1 AS `runway`,
 1 AS `sea_date`,
 1 AS `scheduled_take_off`,
 1 AS `wheels_up`,
 1 AS `selection_time`,
 1 AS `selection_date`,
 1 AS `selection_hour`,
 1 AS `delay_sec`,
 1 AS `delay_min`,
 1 AS `exclusion_reason`,
 1 AS `included`*/;
SET character_set_client = @saved_cs_client;

--
-- Temporary view structure for view `v_taxi_in`
--

DROP TABLE IF EXISTS `v_taxi_in`;
/*!50001 DROP VIEW IF EXISTS `v_taxi_in`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `v_taxi_in` AS SELECT 
 1 AS `flight_info_id`,
 1 AS `operation`,
 1 AS `call_sign`,
 1 AS `carrier`,
 1 AS `aircraft_type`,
 1 AS `aircraft_type_group`,
 1 AS `weight_class_icao`,
 1 AS `weight_class_group`,
 1 AS `runway`,
 1 AS `gate`,
 1 AS `sea_date`,
 1 AS `start_time`,
 1 AS `end_time`,
 1 AS `selection_time`,
 1 AS `selection_date`,
 1 AS `selection_hour`,
 1 AS `duration_sec`,
 1 AS `duration_min`,
 1 AS `sys_taxi_in_sec`,
 1 AS `exclusion_reason`,
 1 AS `included`*/;
SET character_set_client = @saved_cs_client;

--
-- Temporary view structure for view `v_taxi_out`
--

DROP TABLE IF EXISTS `v_taxi_out`;
/*!50001 DROP VIEW IF EXISTS `v_taxi_out`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `v_taxi_out` AS SELECT 
 1 AS `flight_info_id`,
 1 AS `operation`,
 1 AS `call_sign`,
 1 AS `carrier`,
 1 AS `aircraft_type`,
 1 AS `aircraft_type_group`,
 1 AS `weight_class_icao`,
 1 AS `weight_class_group`,
 1 AS `runway`,
 1 AS `gate`,
 1 AS `sea_date`,
 1 AS `start_time`,
 1 AS `end_time`,
 1 AS `selection_time`,
 1 AS `selection_date`,
 1 AS `selection_hour`,
 1 AS `off_block_date`,
 1 AS `off_block_hour`,
 1 AS `duration_sec`,
 1 AS `duration_min`,
 1 AS `sys_taxi_out_sec`,
 1 AS `exclusion_reason`,
 1 AS `included`*/;
SET character_set_client = @saved_cs_client;

--
-- Temporary view structure for view `v_taxiway_usage`
--

DROP TABLE IF EXISTS `v_taxiway_usage`;
/*!50001 DROP VIEW IF EXISTS `v_taxiway_usage`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `v_taxiway_usage` AS SELECT 
 1 AS `flight_info_id`,
 1 AS `operation`,
 1 AS `call_sign`,
 1 AS `aircraft_type`,
 1 AS `weight_class_icao`,
 1 AS `runway`,
 1 AS `sea_date`,
 1 AS `segment_role`,
 1 AS `taxiway_segment`,
 1 AS `taxiway_letter`,
 1 AS `taxiway_name`,
 1 AS `segment_number`,
 1 AS `selection_time`,
 1 AS `selection_date`,
 1 AS `selection_hour`,
 1 AS `is_proxy_time`,
 1 AS `exclusion_reason`,
 1 AS `included`*/;
SET character_set_client = @saved_cs_client;

--
-- Temporary view structure for view `v_weight_classes`
--

DROP TABLE IF EXISTS `v_weight_classes`;
/*!50001 DROP VIEW IF EXISTS `v_weight_classes`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `v_weight_classes` AS SELECT 
 1 AS `weight_class_group`,
 1 AS `label`,
 1 AS `sort_order`*/;
SET character_set_client = @saved_cs_client;

--
-- Dumping routines for database 'seatac'
--

--
-- Final view structure for view `v_movement_area`
--

/*!50001 DROP VIEW IF EXISTS `v_movement_area`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_0900_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_movement_area` AS select `f`.`flight_info_id` AS `flight_info_id`,`f`.`operation` AS `operation`,`f`.`call_sign` AS `call_sign`,`f`.`aircraft_type` AS `aircraft_type`,coalesce(`f`.`aircraft_type`,'Unknown') AS `aircraft_type_group`,`f`.`weight_class_icao` AS `weight_class_icao`,`f`.`runway` AS `runway`,`f`.`sea_date` AS `sea_date`,`f`.`wheels_down` AS `start_time`,`f`.`movement_area_exit` AS `end_time`,`f`.`wheels_down` AS `selection_time`,cast(`f`.`wheels_down` as date) AS `selection_date`,hour(`f`.`wheels_down`) AS `selection_hour`,timestampdiff(SECOND,`f`.`wheels_down`,`f`.`movement_area_exit`) AS `duration_sec`,(timestampdiff(SECOND,`f`.`wheels_down`,`f`.`movement_area_exit`) / 60) AS `duration_min`,(case when ((`f`.`wheels_down` is null) or (`f`.`movement_area_exit` is null)) then 'missing time' when (`f`.`movement_area_exit` < `f`.`wheels_down`) then 'negative duration' end) AS `exclusion_reason`,((`f`.`wheels_down` is not null) and (`f`.`movement_area_exit` is not null) and (`f`.`movement_area_exit` >= `f`.`wheels_down`)) AS `included` from `flights` `f` where (`f`.`operation` = 'Arrival') union all select `f`.`flight_info_id` AS `flight_info_id`,`f`.`operation` AS `operation`,`f`.`call_sign` AS `call_sign`,`f`.`aircraft_type` AS `aircraft_type`,coalesce(`f`.`aircraft_type`,'Unknown') AS `aircraft_type_group`,`f`.`weight_class_icao` AS `weight_class_icao`,`f`.`runway` AS `runway`,`f`.`sea_date` AS `sea_date`,`f`.`movement_area_entrance` AS `movement_area_entrance`,`f`.`wheels_up` AS `wheels_up`,`f`.`movement_area_entrance` AS `movement_area_entrance`,cast(`f`.`movement_area_entrance` as date) AS `DATE(f.movement_area_entrance)`,hour(`f`.`movement_area_entrance`) AS `HOUR(f.movement_area_entrance)`,timestampdiff(SECOND,`f`.`movement_area_entrance`,`f`.`wheels_up`) AS `TIMESTAMPDIFF(SECOND, f.movement_area_entrance, f.wheels_up)`,(timestampdiff(SECOND,`f`.`movement_area_entrance`,`f`.`wheels_up`) / 60) AS `Name_exp_32`,(case when ((`f`.`movement_area_entrance` is null) or (`f`.`wheels_up` is null)) then 'missing time' when (`f`.`wheels_up` < `f`.`movement_area_entrance`) then 'negative duration' end) AS `Name_exp_33`,((`f`.`movement_area_entrance` is not null) and (`f`.`wheels_up` is not null) and (`f`.`wheels_up` >= `f`.`movement_area_entrance`)) AS `Name_exp_34` from `flights` `f` where (`f`.`operation` = 'Departure') */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `v_movement_area_hourly_peak`
--

/*!50001 DROP VIEW IF EXISTS `v_movement_area_hourly_peak`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_0900_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_movement_area_hourly_peak` AS with recursive `intervals` as (select `v_movement_area`.`start_time` AS `start_time`,`v_movement_area`.`end_time` AS `end_time` from `v_movement_area` where (`v_movement_area`.`exclusion_reason` is null)), `exclusion_counts` as (select sum((`v_movement_area`.`exclusion_reason` is null)) AS `intervals_used`,sum((`v_movement_area`.`exclusion_reason` is not null)) AS `intervals_excluded`,sum((`v_movement_area`.`exclusion_reason` = 'missing time')) AS `excluded_missing_time`,sum((`v_movement_area`.`exclusion_reason` = 'negative duration')) AS `excluded_negative_duration` from `v_movement_area`), `bounds` as (select cast(date_format(min(`intervals`.`start_time`),'%Y-%m-%d %H:00:00') as datetime) AS `first_hour`,max(`intervals`.`end_time`) AS `last_time` from `intervals`), `hours` as (select `bounds`.`first_hour` AS `hour_start` from `bounds` union all select (`h`.`hour_start` + interval 1 hour) AS `h.hour_start + INTERVAL 1 HOUR` from (`hours` `h` join `bounds` `b` on(((`h`.`hour_start` + interval 1 hour) <= `b`.`last_time`)))), `events` as (select `intervals`.`end_time` AS `t`,-(1) AS `delta`,0 AS `tie_order` from `intervals` union all select `hours`.`hour_start` AS `hour_start`,0 AS `0`,1 AS `1` from `hours` union all select `intervals`.`start_time` AS `start_time`,1 AS `1`,2 AS `2` from `intervals`), `running` as (select `events`.`t` AS `t`,sum(`events`.`delta`) OVER (ORDER BY `events`.`t`,`events`.`tie_order` ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)  AS `aircraft_in_area` from `events`), `peaks` as (select cast(`running`.`t` as date) AS `local_date`,hour(`running`.`t`) AS `local_hour`,max(`running`.`aircraft_in_area`) AS `max_aircraft_in_area` from `running` group by cast(`running`.`t` as date),hour(`running`.`t`)) select `p`.`local_date` AS `local_date`,`p`.`local_hour` AS `local_hour`,`p`.`max_aircraft_in_area` AS `max_aircraft_in_area`,`c`.`intervals_used` AS `intervals_used`,`c`.`intervals_excluded` AS `intervals_excluded`,`c`.`excluded_missing_time` AS `excluded_missing_time`,`c`.`excluded_negative_duration` AS `excluded_negative_duration` from (`peaks` `p` join `exclusion_counts` `c`) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `v_peak_hours`
--

/*!50001 DROP VIEW IF EXISTS `v_peak_hours`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_0900_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_peak_hours` AS select `v_runway_activity`.`local_date` AS `local_date`,`v_runway_activity`.`local_hour` AS `local_hour`,count(0) AS `operations`,sum((`v_runway_activity`.`activity` = 'takeoff')) AS `takeoffs`,sum((`v_runway_activity`.`activity` = 'landing')) AS `landings`,rank() OVER (PARTITION BY `v_runway_activity`.`local_date` ORDER BY count(0) desc )  AS `hour_rank` from `v_runway_activity` where ((`v_runway_activity`.`activity_time` is not null) and (`v_runway_activity`.`is_missed_approach` = 0)) group by `v_runway_activity`.`local_date`,`v_runway_activity`.`local_hour` */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `v_runway_activity`
--

/*!50001 DROP VIEW IF EXISTS `v_runway_activity`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_0900_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_runway_activity` AS select `a`.`flight_info_id` AS `flight_info_id`,`a`.`operation` AS `operation`,`a`.`call_sign` AS `call_sign`,`a`.`aircraft_type` AS `aircraft_type`,`a`.`weight_class_icao` AS `weight_class_icao`,`a`.`runway` AS `runway`,`a`.`sea_date` AS `sea_date`,`a`.`activity` AS `activity`,`a`.`activity_time` AS `activity_time`,`a`.`activity_time` AS `selection_time`,cast(`a`.`activity_time` as date) AS `selection_date`,hour(`a`.`activity_time`) AS `selection_hour`,cast(`a`.`activity_time` as date) AS `local_date`,hour(`a`.`activity_time`) AS `local_hour`,`a`.`is_missed_approach` AS `is_missed_approach`,(case when (`a`.`activity_time` is null) then 'missing time' when (`a`.`is_missed_approach` = 1) then 'missed approach' when (`a`.`runway` is null) then 'missing runway' end) AS `exclusion_reason`,((`a`.`activity_time` is not null) and (`a`.`is_missed_approach` = 0) and (`a`.`runway` is not null)) AS `included` from (select `f`.`flight_info_id` AS `flight_info_id`,`f`.`operation` AS `operation`,`f`.`call_sign` AS `call_sign`,`f`.`carrier` AS `carrier`,`f`.`carrier_group` AS `carrier_group`,`f`.`aircraft_type` AS `aircraft_type`,`f`.`weight_class_icao` AS `weight_class_icao`,`f`.`origin_airport` AS `origin_airport`,`f`.`destination_airport` AS `destination_airport`,`f`.`international_domestic` AS `international_domestic`,`f`.`runway` AS `runway`,`f`.`gate` AS `gate`,`f`.`parking_area` AS `parking_area`,`f`.`taxiway_runway` AS `taxiway_runway`,`f`.`taxiway_ramp` AS `taxiway_ramp`,`f`.`scheduled_off_block` AS `scheduled_off_block`,`f`.`actual_off_block` AS `actual_off_block`,`f`.`scheduled_take_off` AS `scheduled_take_off`,`f`.`wheels_up` AS `wheels_up`,`f`.`scheduled_landing` AS `scheduled_landing`,`f`.`wheels_down` AS `wheels_down`,`f`.`scheduled_in_block` AS `scheduled_in_block`,`f`.`actual_in_block` AS `actual_in_block`,`f`.`runway_entrance` AS `runway_entrance`,`f`.`runway_exit` AS `runway_exit`,`f`.`movement_area_entrance` AS `movement_area_entrance`,`f`.`movement_area_exit` AS `movement_area_exit`,`f`.`sea_event_time` AS `sea_event_time`,`f`.`passenger_count` AS `passenger_count`,`f`.`sea_date` AS `sea_date`,`f`.`sys_taxi_in_sec` AS `sys_taxi_in_sec`,`f`.`sys_taxi_out_sec` AS `sys_taxi_out_sec`,`f`.`sys_runway_occupancy_sec` AS `sys_runway_occupancy_sec`,`f`.`source_file` AS `source_file`,(case `f`.`operation` when 'Departure' then 'takeoff' when 'Arrival' then 'landing' else 'missed_approach' end) AS `activity`,(case `f`.`operation` when 'Departure' then `f`.`wheels_up` when 'Arrival' then `f`.`wheels_down` else `f`.`sea_event_time` end) AS `activity_time`,(`f`.`operation` = 'Missed Approach') AS `is_missed_approach` from `flights` `f`) `a` */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `v_runway_occupancy`
--

/*!50001 DROP VIEW IF EXISTS `v_runway_occupancy`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_0900_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_runway_occupancy` AS select `f`.`flight_info_id` AS `flight_info_id`,`f`.`operation` AS `operation`,`f`.`call_sign` AS `call_sign`,`f`.`aircraft_type` AS `aircraft_type`,coalesce(`f`.`aircraft_type`,'Unknown') AS `aircraft_type_group`,`f`.`weight_class_icao` AS `weight_class_icao`,`f`.`runway` AS `runway`,`f`.`sea_date` AS `sea_date`,`f`.`wheels_down` AS `start_time`,`f`.`runway_exit` AS `end_time`,`f`.`wheels_down` AS `selection_time`,cast(`f`.`wheels_down` as date) AS `selection_date`,hour(`f`.`wheels_down`) AS `selection_hour`,timestampdiff(SECOND,`f`.`wheels_down`,`f`.`runway_exit`) AS `duration_sec`,`f`.`sys_runway_occupancy_sec` AS `sys_runway_occupancy_sec`,(case when ((`f`.`wheels_down` is null) or (`f`.`runway_exit` is null)) then 'missing time' when (`f`.`runway_exit` < `f`.`wheels_down`) then 'negative duration' end) AS `exclusion_reason`,((`f`.`wheels_down` is not null) and (`f`.`runway_exit` is not null) and (`f`.`runway_exit` >= `f`.`wheels_down`)) AS `included` from `flights` `f` where (`f`.`operation` = 'Arrival') union all select `f`.`flight_info_id` AS `flight_info_id`,`f`.`operation` AS `operation`,`f`.`call_sign` AS `call_sign`,`f`.`aircraft_type` AS `aircraft_type`,coalesce(`f`.`aircraft_type`,'Unknown') AS `aircraft_type_group`,`f`.`weight_class_icao` AS `weight_class_icao`,`f`.`runway` AS `runway`,`f`.`sea_date` AS `sea_date`,`f`.`runway_entrance` AS `runway_entrance`,`f`.`wheels_up` AS `wheels_up`,`f`.`runway_entrance` AS `runway_entrance`,cast(`f`.`runway_entrance` as date) AS `DATE(f.runway_entrance)`,hour(`f`.`runway_entrance`) AS `HOUR(f.runway_entrance)`,timestampdiff(SECOND,`f`.`runway_entrance`,`f`.`wheels_up`) AS `TIMESTAMPDIFF(SECOND, f.runway_entrance, f.wheels_up)`,`f`.`sys_runway_occupancy_sec` AS `sys_runway_occupancy_sec`,(case when ((`f`.`runway_entrance` is null) or (`f`.`wheels_up` is null)) then 'missing time' when (`f`.`wheels_up` < `f`.`runway_entrance`) then 'negative duration' end) AS `Name_exp_33`,((`f`.`runway_entrance` is not null) and (`f`.`wheels_up` is not null) and (`f`.`wheels_up` >= `f`.`runway_entrance`)) AS `Name_exp_34` from `flights` `f` where (`f`.`operation` = 'Departure') */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `v_takeoff_delay`
--

/*!50001 DROP VIEW IF EXISTS `v_takeoff_delay`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_0900_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_takeoff_delay` AS select `f`.`flight_info_id` AS `flight_info_id`,`f`.`operation` AS `operation`,`f`.`call_sign` AS `call_sign`,`f`.`carrier` AS `carrier`,`f`.`aircraft_type` AS `aircraft_type`,coalesce(`f`.`aircraft_type`,'Unknown') AS `aircraft_type_group`,`f`.`weight_class_icao` AS `weight_class_icao`,`f`.`runway` AS `runway`,`f`.`sea_date` AS `sea_date`,`f`.`scheduled_take_off` AS `scheduled_take_off`,`f`.`wheels_up` AS `wheels_up`,`f`.`wheels_up` AS `selection_time`,cast(`f`.`wheels_up` as date) AS `selection_date`,hour(`f`.`wheels_up`) AS `selection_hour`,timestampdiff(SECOND,`f`.`scheduled_take_off`,`f`.`wheels_up`) AS `delay_sec`,(timestampdiff(SECOND,`f`.`scheduled_take_off`,`f`.`wheels_up`) / 60) AS `delay_min`,(case when (`f`.`scheduled_take_off` is null) then 'missing scheduled take-off' when (`f`.`wheels_up` is null) then 'missing take-off' end) AS `exclusion_reason`,((`f`.`scheduled_take_off` is not null) and (`f`.`wheels_up` is not null)) AS `included` from `flights` `f` where (`f`.`operation` = 'Departure') */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `v_taxi_in`
--

/*!50001 DROP VIEW IF EXISTS `v_taxi_in`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_0900_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_taxi_in` AS select `f`.`flight_info_id` AS `flight_info_id`,`f`.`operation` AS `operation`,`f`.`call_sign` AS `call_sign`,`f`.`carrier` AS `carrier`,`f`.`aircraft_type` AS `aircraft_type`,coalesce(`f`.`aircraft_type`,'Unknown') AS `aircraft_type_group`,`f`.`weight_class_icao` AS `weight_class_icao`,coalesce(`f`.`weight_class_icao`,'Unknown') AS `weight_class_group`,`f`.`runway` AS `runway`,`f`.`gate` AS `gate`,`f`.`sea_date` AS `sea_date`,`f`.`wheels_down` AS `start_time`,`f`.`actual_in_block` AS `end_time`,`f`.`wheels_down` AS `selection_time`,cast(`f`.`wheels_down` as date) AS `selection_date`,hour(`f`.`wheels_down`) AS `selection_hour`,timestampdiff(SECOND,`f`.`wheels_down`,`f`.`actual_in_block`) AS `duration_sec`,(timestampdiff(SECOND,`f`.`wheels_down`,`f`.`actual_in_block`) / 60) AS `duration_min`,`f`.`sys_taxi_in_sec` AS `sys_taxi_in_sec`,(case when ((`f`.`wheels_down` is null) or (`f`.`actual_in_block` is null)) then 'missing time' when (`f`.`actual_in_block` < `f`.`wheels_down`) then 'negative duration' end) AS `exclusion_reason`,((`f`.`wheels_down` is not null) and (`f`.`actual_in_block` is not null) and (`f`.`actual_in_block` >= `f`.`wheels_down`)) AS `included` from `flights` `f` where (`f`.`operation` = 'Arrival') */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `v_taxi_out`
--

/*!50001 DROP VIEW IF EXISTS `v_taxi_out`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_0900_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_taxi_out` AS select `f`.`flight_info_id` AS `flight_info_id`,`f`.`operation` AS `operation`,`f`.`call_sign` AS `call_sign`,`f`.`carrier` AS `carrier`,`f`.`aircraft_type` AS `aircraft_type`,coalesce(`f`.`aircraft_type`,'Unknown') AS `aircraft_type_group`,`f`.`weight_class_icao` AS `weight_class_icao`,coalesce(`f`.`weight_class_icao`,'Unknown') AS `weight_class_group`,`f`.`runway` AS `runway`,`f`.`gate` AS `gate`,`f`.`sea_date` AS `sea_date`,`f`.`actual_off_block` AS `start_time`,`f`.`wheels_up` AS `end_time`,`f`.`actual_off_block` AS `selection_time`,cast(`f`.`actual_off_block` as date) AS `selection_date`,hour(`f`.`actual_off_block`) AS `selection_hour`,cast(`f`.`actual_off_block` as date) AS `off_block_date`,hour(`f`.`actual_off_block`) AS `off_block_hour`,timestampdiff(SECOND,`f`.`actual_off_block`,`f`.`wheels_up`) AS `duration_sec`,(timestampdiff(SECOND,`f`.`actual_off_block`,`f`.`wheels_up`) / 60) AS `duration_min`,`f`.`sys_taxi_out_sec` AS `sys_taxi_out_sec`,(case when ((`f`.`actual_off_block` is null) or (`f`.`wheels_up` is null)) then 'missing time' when (`f`.`wheels_up` < `f`.`actual_off_block`) then 'negative duration' end) AS `exclusion_reason`,((`f`.`actual_off_block` is not null) and (`f`.`wheels_up` is not null) and (`f`.`wheels_up` >= `f`.`actual_off_block`)) AS `included` from `flights` `f` where (`f`.`operation` = 'Departure') */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `v_taxiway_usage`
--

/*!50001 DROP VIEW IF EXISTS `v_taxiway_usage`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_0900_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_taxiway_usage` AS select `u`.`flight_info_id` AS `flight_info_id`,`u`.`operation` AS `operation`,`u`.`call_sign` AS `call_sign`,`u`.`aircraft_type` AS `aircraft_type`,`u`.`weight_class_icao` AS `weight_class_icao`,`u`.`runway` AS `runway`,`u`.`sea_date` AS `sea_date`,`u`.`segment_role` AS `segment_role`,`u`.`taxiway_segment` AS `taxiway_segment`,(case when regexp_like(`u`.`taxiway_segment`,'^TaxiwaySegment_[A-Z]_') then substr(`u`.`taxiway_segment`,16,1) end) AS `taxiway_letter`,(case when regexp_like(`u`.`taxiway_segment`,'^TaxiwaySegment_[A-Z]_') then (case substr(`u`.`taxiway_segment`,16,1) when 'A' then 'Alpha' when 'B' then 'Bravo' when 'C' then 'Charlie' when 'D' then 'Delta' when 'E' then 'Echo' when 'F' then 'Foxtrot' when 'G' then 'Golf' when 'J' then 'Juliet' when 'K' then 'Kilo' when 'L' then 'Lima' when 'M' then 'Mike' when 'N' then 'November' when 'P' then 'Papa' when 'Q' then 'Quebec' when 'Z' then 'Zulu' end) end) AS `taxiway_name`,(case when regexp_like(`u`.`taxiway_segment`,'^TaxiwaySegment_[A-Z]_[0-9]+$') then cast(substring_index(`u`.`taxiway_segment`,'_',-(1)) as unsigned) end) AS `segment_number`,`u`.`proxy_time` AS `selection_time`,cast(`u`.`proxy_time` as date) AS `selection_date`,hour(`u`.`proxy_time`) AS `selection_hour`,1 AS `is_proxy_time`,(case when (`u`.`taxiway_segment` is null) then 'missing segment' when (`u`.`proxy_time` is null) then 'missing time' end) AS `exclusion_reason`,((`u`.`taxiway_segment` is not null) and (`u`.`proxy_time` is not null)) AS `included` from (select `f`.`flight_info_id` AS `flight_info_id`,`f`.`operation` AS `operation`,`f`.`call_sign` AS `call_sign`,`f`.`aircraft_type` AS `aircraft_type`,`f`.`weight_class_icao` AS `weight_class_icao`,`f`.`runway` AS `runway`,`f`.`sea_date` AS `sea_date`,'runway' AS `segment_role`,`f`.`taxiway_runway` AS `taxiway_segment`,(case `f`.`operation` when 'Departure' then `f`.`runway_entrance` else `f`.`runway_exit` end) AS `proxy_time` from `flights` `f` where (`f`.`operation` in ('Arrival','Departure')) union all select `f`.`flight_info_id` AS `flight_info_id`,`f`.`operation` AS `operation`,`f`.`call_sign` AS `call_sign`,`f`.`aircraft_type` AS `aircraft_type`,`f`.`weight_class_icao` AS `weight_class_icao`,`f`.`runway` AS `runway`,`f`.`sea_date` AS `sea_date`,'ramp' AS `ramp`,`f`.`taxiway_ramp` AS `taxiway_ramp`,(case `f`.`operation` when 'Departure' then `f`.`movement_area_entrance` else `f`.`movement_area_exit` end) AS `CASE f.operation WHEN 'Departure' THEN f.movement_area_entrance ELSE f.movement_area_exit END` from `flights` `f` where (`f`.`operation` in ('Arrival','Departure'))) `u` */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `v_weight_classes`
--

/*!50001 DROP VIEW IF EXISTS `v_weight_classes`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_0900_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_weight_classes` AS select 'L' AS `weight_class_group`,'Light' AS `label`,1 AS `sort_order` union all select 'M' AS `M`,'Medium' AS `Medium`,2 AS `2` union all select 'H' AS `H`,'Heavy' AS `Heavy`,3 AS `3` union all select 'Unknown' AS `Unknown`,'Unknown' AS `Unknown`,4 AS `4` */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-10-21 14:00:53
