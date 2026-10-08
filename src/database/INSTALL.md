# Excel to MySQL Database Import Guide

**Database:** AIplane  
**Purpose:** Import flight data from Excel to MySQL database

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Prerequisites](#prerequisites)
3. [Database Schema](#database-schema)
4. [Excel File Requirements](#excel-file-requirements)
5. [Import Steps](#import-steps)
6. [Data Verification](#data-verification)
7. [Troubleshooting](#troubleshooting)

---

## System Overview

This system imports flight operation data from Excel spreadsheets into a MySQL database with three normalized tables:

- **aircraft_type** - Aircraft specifications (14-16 records)
- **flight** - Flight records (725 records)
- **flight_event** - Timestamped flight events (~7,995 records)

**Data Flow:**
```
Excel File (725 rows × 37 columns)
    ↓
Python Script: db_manager.py
    ↓
MySQL Database (3 tables)
```

---

## Prerequisites

### 1. Software Requirements

- **Python 3.8+**
- **MySQL 8.0+** (or MariaDB 10.5+)

### 2. Install Python Packages

```bash
pip3 install pandas openpyxl pymysql
```

### 3. Create Database

```bash
mysql -u root -p < AIplane.sql
```

This creates the `AIplane` database with three tables.

### 4. Configure Database Connection

Edit `config.py` with your database credentials:

```python
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'YOUR_PASSWORD',
    'database': 'AIplane',
    'charset': 'utf8mb4',
    'port': 3306
}

EXCEL_FILE_PATH = "/src/database/data/field_mapping.xlsx"
```

### 5. Test Connection

```bash
python3 src/database/scripts/db_manager.py test
```

---

## Database Schema

### Table 1: `aircraft_type`
Stores aircraft specifications.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| aircraft_type | VARCHAR(10) PRIMARY KEY | Aircraft type code | 'B739', 'A21N' |
| weight_class | ENUM('L','M','H','J') | ICAO weight class | 'M' |
| wake_category | VARCHAR(5) | Wake turbulence category | 'D' |
| wingspan_ft | DECIMAL(10,2) | Wingspan in feet | 117.45 |
| wingspan_m | DECIMAL(10,2) | Wingspan in meters | 35.80 |

---

### Table 2: `flight`
Stores flight records.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| id | INT PRIMARY KEY AUTO_INCREMENT | Unique record ID | 1, 2, 3... |
| call_sign | VARCHAR(20) | Flight call sign | 'QTA328' |
| flight_ID | VARCHAR(20) | Flight identifier | 'QTA328' |
| aircraft_type | VARCHAR(10) | Aircraft type (FK) | 'B739' |
| flight_number | INT | Flight number | 328 |
| aircraft_registration | VARCHAR(20) | Aircraft registration | 'N12345' |
| origin_airport | VARCHAR(10) | Origin ICAO code | 'KSEA' |
| destination_airport | VARCHAR(10) | Destination ICAO code | 'KORD' |
| departure_procedure | VARCHAR(100) | SID procedure | 'HAROB9' |
| flight_origination_date | DATE | Flight date | '2025-08-08' |
| schedule_departure | DATETIME | Scheduled off-block time | '2025-08-08 05:00:00' |
| actual_departure | DATETIME | Actual off-block time | '2025-08-08 05:01:00' |
| schedule_arrival | DATETIME | Scheduled in-block time | '2025-08-08 10:35:00' |
| actual_arrival | DATETIME | Actual in-block time | '2025-08-08 11:01:46' |
| operation | ENUM('DEPARTURE','ARRIVAL') | Operation type | 'DEPARTURE' |

**Important:** `call_sign` is NOT unique (same flight can have DEPARTURE and ARRIVAL records).

---

### Table 3: `flight_event`
Stores timestamped events (multiple events per flight).

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| id | INT PRIMARY KEY AUTO_INCREMENT | Unique event ID | 1, 2, 3... |
| call_sign | VARCHAR(20) | Links to flight | 'QTA328' |
| operation | ENUM('DEPARTURE','ARRIVAL') | Operation type | 'DEPARTURE' |
| event_type | VARCHAR(50) | Event name | 'Actual_Take_Off' |
| event_time | DATETIME | Event timestamp | '2025-08-08 05:18:00' |
| event_source | ENUM('AODB','ATC','Aerobahn','Filed') | Data source | 'Aerobahn' |
| location | VARCHAR(50) | Location identifier | '34L', 'Gate_N14' |

**Event Types:** Scheduled_Off_Block, Actual_Off_Block, Movement_Area_Entrance, Movement_Area_Exit, Runway_Entrance, Runway_Exit, Estimated_Take_Off, Actual_Take_Off, Scheduled_Take_Off, Estimated_Landing, Actual_Landing, Estimated_In_Block, Actual_In_Block, Boarding_Start

---

## Excel File Requirements

### Fpr Sample file
- **Filename:** `field_mapping.xlsx`
- **Format:** Excel 2007+ (.xlsx)
- **Structure:** 725 data rows + 1 header row, 37 columns

### Key Columns

**Aircraft Information:**
- `Aircraft Type (AODB)` - Aircraft type for aircraft_type table
- `Weight Class (ICAO)` - Weight classification
- `Wake Category (Aerobahn)` - Wake turbulence category
- `Wingspan (feet)` / `Wingspan (meters)` - Wingspan dimensions

**Flight Information:**
- `Call Sign` - Flight identifier
- `Aircraft Type (AODB).1` - Aircraft type for flight (can be NULL)
- `Flight Number` - Numeric flight number
- `Operation` - 'Departure' or 'Arrival'
- `Origination Airport (ICAO)` / `Destination Airport (ICAO)` - Airport codes

**Location Information:**
- `Gate Assigned (Aerobahn)` - Gate location (e.g., 'Gate_N14')
- `Runway Assigned (Aerobahn)` - Runway location (e.g., '34L')
- `Taxiway Used to Enter Exit Runway` - Taxiway location (e.g., 'TaxiwaySegment_B_28')

**Time Columns (14 columns):**
Each non-NULL timestamp creates one event record. Columns include various departure times, arrival times, runway times, gate times, etc.

---

## Import Steps

### Step 1: Prepare Files

- ✅ `create_database.sql` - Database schema
- ✅ `config.py` - Configuration file 
- ✅ `migrate_to_mysql.py` - Main import script
- ✅ `smart_unknown_matcher.py` - Handles NULL aircraft types
- ✅ `field_mapping.xlsx` - Source data file

---

### Step 2: Mapping

Below are the complete field mappings showing how Excel columns are transformed into database tables.

#### Table 1: aircraft_type Mapping

| Target Field | Excel Column | Description |
|--------------|--------------|-------------|
| aircraft_type | Aircraft Type (AODB) | Aircraft type code (Primary Key) |
| weight_class | Weight Class (ICAO) | Weight class |
| wake_category | Wake Category (Aerobahn) | Wake turbulence category |
| wingspan_ft | Wingspan (feet) | Wingspan in feet |
| wingspan_m | Wingspan (meters) | Wingspan in meters |

**Sample Data (First 5 unique records):**
```
Aircraft Type | Weight Class | Wake Category | Wingspan (feet) | Wingspan (meters)
B39M          | M            | D             | 117.81          | 35.91
B739          | M            | D             | 117.45          | 35.80
BCS1          | M            | D             | 115.16          | 35.10
B738          | M            | D             | 117.45          | 35.80
A21N          | M            | D             | 117.45          | 35.80
```

**Total:** 14 different aircraft types

---

#### Table 2: flight Mapping

| Target Field | Excel Column | Description |
|--------------|--------------|-------------|
| call_sign | Call Sign | Call sign (Primary Key) |
| flight_ID | Flight ID | Flight ID |
| aircraft_type | Aircraft Type (AODB).1 | Aircraft type (FK to aircraft_type) |
| flight_number | Flight Number | Flight number |
| aircraft_registration | Registration (AODB) | Aircraft registration |
| origin_airport | Origination Airport (ICAO) | Origin airport ICAO code |
| destination_airport | Destination Airport (ICAO) | Destination airport ICAO code |
| departure_procedure | Departure Procedure (Filed) | Departure procedure |
| flight_origination_date | Flight Origination Date (AODB) | Flight origination date |
| schedule_departure | Scheduled Off Block Time (Aerobahn) (US Pacific) | Scheduled departure time |
| actual_departure | Actual Off Block Time (Aerobahn) (US Pacific) | Actual departure time |
| schedule_arrival | Estimated In Block Time (ATC) (US Pacific) | Scheduled arrival time |
| actual_arrival | Actual In Block Time (Aerobahn) (US Pacific) | Actual arrival time |
| operation | Operation | Operation type (DEPARTURE/ARRIVAL) |

**Sample Data (First 3 records):**
```
Call Sign | Flight ID | Flight Number | Operation | Origin | Destination
QTA328    | QTA328    | 328           | Departure | KSEA   | KORD
QTA367    | QTA367    | 367           | Departure | KSEA   | KIAD
QTA536    | QTA536    | 536           | Departure | KSEA   | KBOS
```

**Total:** 725 flight records

---

#### Table 3: flight_event Mapping

**Direct Field Mappings:**

| DB Field | Excel Column | Description |
|----------|--------------|-------------|
| id | (auto-increment) | Unique event ID (Primary Key) |
| call_sign | Call Sign | Flight call sign (FK to flight) |
| operation | Operation | DEPARTURE or ARRIVAL |
| location | (Dynamic - based on event_type) | Actual location value |

**Event Type Mappings (event_type, event_time, event_source):**

| Event Type | Excel Time Column (→ event_time) | Source |
|------------|----------------------------------|--------|
| Scheduled_Off_Block | Scheduled Off Block Time (Aerobahn) (US Pacific) | Aerobahn |
| Actual_Off_Block | Actual Off Block Time (Aerobahn) (US Pacific) | Aerobahn |
| Movement_Area_Entrance | Movement Area Entrance Time (US Pacific) | Aerobahn |
| Runway_Entrance | Runway Entrance Time (US Pacific) | Aerobahn |
| Estimated_Take_Off | Estimated Take Off Time (ATC) (US Pacific) | ATC |
| Actual_Take_Off | Actual Take Off Time (Aerobahn) (US Pacific) | Aerobahn |
| Scheduled_Take_Off | Scheduled Take Off Time (Aerobahn) (US Pacific) | Aerobahn |
| Estimated_Landing | Estimated Landing Time (ATC) (US Pacific) | ATC |
| Actual_Landing | Actual Landing Time (Aerobahn) (US Pacific) | Aerobahn |
| Runway_Exit | Runway Exit Time (US Pacific) | Aerobahn |
| Movement_Area_Exit | Movement Area Exit Time (US Pacific) | Aerobahn |
| Estimated_In_Block | Estimated In Block Time (ATC) (US Pacific) | ATC |
| Actual_In_Block | Actual In Block Time (Aerobahn) (US Pacific) | Aerobahn |
| Boarding_Start | Actual Start of Boarding Time (Aerobahn) (US Pacific) | Aerobahn |

**How Events are Created:**

For each row in Excel:
- **call_sign** → from 'Call Sign' column
- **operation** → from 'Operation' column (DEPARTURE/ARRIVAL)
- **location** → DYNAMICALLY determined based on event_type:
  - Runway events (Take_Off, Landing, Runway_Entrance/Exit) → from 'Runway Assigned (Aerobahn)' column (e.g., '34L', '34R')
  - Gate events (Off_Block, In_Block, Boarding_Start) → from 'Gate Assigned (Aerobahn)' column (e.g., 'Gate_N14')
  - Taxiway events (Movement_Area_Entrance/Exit) → from 'Taxiway Used to Enter Exit Runway' column (e.g., 'TaxiwaySegment_B_28')
- For each time column above (if non-null):
  - **event_type** → the event type name (e.g., 'Actual_Take_Off')
  - **event_time** → the actual timestamp value from that column
  - **event_source** → the data source (AODB, ATC, Aerobahn, or Filed)

**Example:**

If a row has Call Sign='QTA328', Operation='Departure', Gate='Gate_N14', Runway='34R', Taxiway='TaxiwaySegment_B_28', and 3 non-null time values, it will generate 3 separate event records:

```
Record 1: call_sign='QTA328', operation='DEPARTURE', event_type='Actual_Off_Block',
          event_time='2025-08-08 23:43:04', event_source='Aerobahn', location='Gate_N14'

Record 2: call_sign='QTA328', operation='DEPARTURE', event_type='Movement_Area_Entrance',
          event_time='2025-08-08 23:48:12', event_source='Aerobahn', location='TaxiwaySegment_B_28'

Record 3: call_sign='QTA328', operation='DEPARTURE', event_type='Actual_Take_Off',
          event_time='2025-08-08 23:55:30', event_source='Aerobahn', location='34R'
```

**Expected Result:** ~7,995 flight_event records will be generated

---

#### Data Summary

**Total rows in Excel file:** 725

**Non-null value statistics:**

| Column Name | Non-Null Count | Null Count |
|-------------|----------------|------------|
| Call Sign | 725 | 0 |
| Aircraft Type (AODB) | 716 | 9 |
| Flight Number | 725 | 0 |
| Operation | 725 | 0 |
| Origination Airport (ICAO) | 722 | 3 |
| Destination Airport (ICAO) | 722 | 3 |
| Scheduled Off Block Time | 720 | 5 |
| Actual Off Block Time | 719 | 6 |
| Actual Take Off Time | 723 | 2 |
| Actual Landing Time | 712 | 13 |

**Note:** 9 flights have NULL Aircraft Type - these will be handled automatically in Step 4


---

### Step 3: Run Import

```bash
python3 db_manager.py
```

**Process:**
1. Reads Excel file
2. Clears existing data in database
3. Extracts and inserts aircraft types
4. Extracts and inserts flights
5. Extracts and inserts flight events

**Expected Output:**
```
============================================================
Excel to MySQL Migration Script
============================================================
Reading Excel file: field_mapping.xlsx
Loaded 725 rows

Extracting aircraft types...
Found 14 unique aircraft types

Extracting flight records...
Found 725 unique flights

Extracting flight events...
Extracted 7995 flight events

Connecting to MySQL database...
Connected successfully!

Clearing existing data...
Tables cleared successfully

Inserting 14 aircraft types...
Inserted 14 aircraft types

Inserting 725 flights...
Inserted 725 flights

Inserting 7995 flight events...
  Inserted 1000/7995 events
  Inserted 2000/7995 events
  ...
  Inserted 7995/7995 events
Successfully inserted all flight events

============================================================
Migration completed successfully!
============================================================
Summary:
  - Aircraft types: 14
  - Flights: 725
  - Flight events: 7995
============================================================
```

---

### Step 4: Handle NULL Aircraft Types

If some flights have NULL aircraft type in Excel, run:

```bash
python3 smart_unknown_matcher.py
```

**What it does:**
- Finds flights with NULL aircraft_type
- Groups them by properties (weight, wake, wingspan)
- Creates UNKNOWN_001, UNKNOWN_002, etc. for each unique property combination
- Updates flight records to use the UNKNOWN aircraft type

---

### Step 5: Verify Import

```bash
python3  src/database/scripts/db_manager.py verify
```

**Checks:**
- Record counts in all tables
- Sample data from each table
- Data integrity

**Expected Output:**
```
aircraft_type: 14 records
flight: 725 records
flight_event: 7995 records

✓ All tables populated successfully
```

---

## Data Verification

### Quick SQL Checks

**1. Check Record Counts:**
```sql
USE AIplane;

SELECT 'aircraft_type' as table_name, COUNT(*) as count FROM aircraft_type
UNION ALL
SELECT 'flight', COUNT(*) FROM flight
UNION ALL
SELECT 'flight_event', COUNT(*) FROM flight_event;
```

**Expected:**
- aircraft_type: 14-16
- flight: 725
- flight_event: ~7,995

---

**2. Verify No NULL Aircraft Types:**
```sql
SELECT COUNT(*) FROM flight WHERE aircraft_type IS NULL;
```

**Expected:** 0

---

**3. View Sample Flight with Events:**
```sql
SELECT 
    f.call_sign,
    f.flight_number,
    f.aircraft_type,
    f.origin_airport,
    f.destination_airport,
    fe.event_type,
    fe.event_time,
    fe.location
FROM flight f
JOIN flight_event fe ON f.call_sign = fe.call_sign
WHERE f.call_sign = 'QTA328'
ORDER BY fe.event_time;
```

---

**4. Check Location Distribution:**
```sql
SELECT 
    CASE 
        WHEN location LIKE 'Gate_%' THEN 'Gate'
        WHEN location LIKE 'TaxiwaySegment_%' THEN 'Taxiway'
        WHEN location LIKE '%L' OR location LIKE '%R' THEN 'Runway'
        ELSE 'Other/NULL'
    END as location_type,
    COUNT(*) as count
FROM flight_event
GROUP BY location_type;
```

**Expected Distribution:**
- Runway: ~4,300 (54%)
- Gate: ~2,900 (37%)
- Taxiway: ~700 (9%)

---

## Troubleshooting

### Issue 1: "ModuleNotFoundError: No module named 'pandas'"

**Solution:**
```bash
pip3 install pandas openpyxl pymysql
```

---

### Issue 2: "Access denied for user 'root'@'localhost'"

**Problem:** Incorrect database credentials.

**Solution:**
1. Verify password in `config.py`
2. Check MySQL user permissions:
```sql
GRANT ALL PRIVILEGES ON AIplane.* TO 'root'@'localhost';
FLUSH PRIVILEGES;
```

---

### Issue 3: "Can't connect to MySQL server"

**Problem:** MySQL server not running or wrong port.

**Solution:**
1. Start MySQL: `mysql.server start` or `sudo systemctl start mysql`
2. Verify port in `config.py` (default: 3306)
3. Check MySQL is running: `mysql -u root -p`

---

### Issue 4: Fewer than 725 flights imported

**Problem:** Import error or data issue.

**Solution:**
1. Check script output for error messages
2. Verify Excel has exactly 725 data rows (+ 1 header)
3. Ensure database table structure is correct
4. Re-run import: `python3 migrate_to_mysql.py`

---

### Issue 5: Fewer than 7,995 events imported

**Problem:** Normal - NULL timestamps in Excel are skipped.

**Solution:** This is expected. Count should be around 7,900-8,000 depending on data quality.


---

## Re-importing Data

To import updated data:

### Option 1: Run Import Script
```bash
python3 src/database/scripts/db_manager.py import-excel
python3 src/database/scripts/db_manager.py fix-nulls
```

### Option 2: Manual Cleanup
```sql
USE AIplane;

DELETE FROM flight_event;
DELETE FROM flight;
DELETE FROM aircraft_type;
```

Then run `python3 src/database/scripts/db_manager.py import-excel`.

---

## Important Notes

### Data Characteristics

1. **Call Sign Duplicates:** 
   - Same `call_sign` can appear multiple times in `flight` table
   - This is normal (DEPARTURE + ARRIVAL legs of same flight)
   - Use `id` column as unique identifier

2. **NULL Aircraft Types:**
   - Excel may have NULL in aircraft type column
   - Automatically handled as UNKNOWN_001, UNKNOWN_002, etc.
   - Each UNKNOWN represents a unique combination of properties

3. **Location Field:**
   - Dynamically populated based on event type
   - Runway events → runway value (e.g., '34L')
   - Gate events → gate value (e.g., 'Gate_N14')
   - Taxiway events → taxiway value (e.g., 'TaxiwaySegment_B_28')

4. **Event Creation:**
   - Each non-NULL timestamp in Excel creates one event
   - One Excel row can generate 10-15 event records
   - NULL timestamps are skipped

### Performance

- **Import Time:** 30-60 seconds for full dataset
- **Database Size:** ~2-3 MB
- **Batch Processing:** 1,000 records per batch

### Data Backup

**Create Backup:**
```bash
mysqldump -u root -p AIplane > AIplane_backup.sql
```

---

## Summary Checklist

Import checklist:

- [ ] Install Python packages: `pip3 install pandas openpyxl pymysql`
- [ ] Create database: `mysql -u root -p < AIplane.sql`
- [ ] Edit `config.py` with database credentials and Excel file path
- [ ] Test connection: `python3 src/database/scripts/db_manager.py test`
- [ ] Run import: `python3 src/database/scripts/db_manager.py import-excel`
- [ ] Handle NULL aircraft: `python3 src/database/scripts/db_manager.py fix-nulls`
- [ ] Verify data: `python3 src/database/scripts/db_manager.py verify`
- [ ] Check sample queries work correctly
- [ ] Create backup: `mysqldump -u root -p AIplane > backup.sql`

---

**End of Guide**