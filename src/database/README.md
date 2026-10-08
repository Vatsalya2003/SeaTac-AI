# Database - Airfield Data Intelligence

MySQL database for Seattle-Tacoma International Airport flight operations data.

## Overview

| Metric | Value |
|--------|-------|
| **Database** | AIplane |
| **Engine** | MySQL 8.0+ |
| **Tables** | 3 |
| **Total Records** | ~8,700 |
| **Source** | Port of Seattle AerobahnDW |

## Schema

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  aircraft_type  │       │     flight      │       │  flight_event   │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ aircraft_type PK│◄──────│ aircraft_type FK│       │ id PK           │
│ weight_class    │       │ id PK           │       │ call_sign FK    │
│ wake_category   │       │ call_sign       │◄──────│ operation       │
│ wingspan_ft     │       │ flight_number   │       │ event_type      │
│ wingspan_m      │       │ operation       │       │ event_time      │
└─────────────────┘       │ origin_airport  │       │ event_source    │
     16 records           │ destination     │       │ location        │
                          └─────────────────┘       └─────────────────┘
                               725 records              7,995 records
```

## Quick Start

```bash
# Option 1: Import from SQL dump (recommended)
mysql -u root -p < data/AIplane.sql

# Option 2: Import from Excel
python scripts/db_manager.py import-excel
python scripts/db_manager.py fix-nulls

# Verify installation
python scripts/db_manager.py verify
```

## Directory Structure

```
database/
├── data/
│   ├── AIplane.sql           # Complete database dump with data
│   └── field_mapping.xlsx    # Source Excel data (725 flights)
├── scripts/
│   ├── config.py             # Database configuration
│   └── db_manager.py         # Database management CLI
├── INSTALL.md                # Detailed setup guide
└── README.md                 # This file
```

## Database Management CLI

```bash
cd scripts

# Test database connection
python db_manager.py test

# Import data from Excel
python db_manager.py import-excel

# Fix NULL aircraft types
python db_manager.py fix-nulls

# Verify data integrity
python db_manager.py verify
```

## Tables

### aircraft_type (16 records)

Aircraft specifications and classifications.

| Column | Type | Description |
|--------|------|-------------|
| `aircraft_type` | VARCHAR(20) PK | Aircraft code (B738, A321) |
| `weight_class` | VARCHAR(10) | ICAO class (L/M/H) |
| `wake_category` | VARCHAR(10) | Wake turbulence (B/C/D) |
| `wingspan_ft` | DECIMAL(8,5) | Wingspan in feet |
| `wingspan_m` | DECIMAL(8,5) | Wingspan in meters |

### flight (725 records)

Individual flight records.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT PK | Auto-increment ID |
| `call_sign` | VARCHAR(20) | Flight identifier (QTA328) |
| `aircraft_type` | VARCHAR(20) FK | Links to aircraft_type |
| `flight_number` | VARCHAR(20) | Flight number |
| `operation` | ENUM | DEPARTURE or ARRIVAL |
| `origin_airport` | VARCHAR(10) | Origin ICAO code |
| `destination_airport` | VARCHAR(10) | Destination ICAO code |
| `schedule_departure` | DATETIME | Scheduled off-block |
| `actual_departure` | DATETIME | Actual off-block |
| `schedule_arrival` | DATETIME | Scheduled in-block |
| `actual_arrival` | DATETIME | Actual in-block |

### flight_event (7,995 records)

Timestamped operational events.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT PK | Auto-increment ID |
| `call_sign` | VARCHAR(20) FK | Links to flight |
| `operation` | ENUM | DEPARTURE or ARRIVAL |
| `event_type` | ENUM | Event name (see below) |
| `event_time` | DATETIME | Event timestamp |
| `event_source` | ENUM | AODB/ATC/Aerobahn/Filed |
| `location` | VARCHAR(50) | Gate/Runway/Taxiway |

**Event Types:**
- Gate: `Scheduled_Off_Block`, `Actual_Off_Block`, `Actual_In_Block`, `Boarding_Start`
- Runway: `Runway_Entrance`, `Runway_Exit`, `Actual_Take_Off`, `Actual_Landing`
- Movement: `Movement_Area_Entrance`, `Movement_Area_Exit`
- Estimates: `Estimated_Take_Off`, `Estimated_Landing`, `Estimated_In_Block`

## Sample Queries

```sql
-- Average taxi-in time by aircraft type
SELECT 
    f.aircraft_type,
    AVG(TIMESTAMPDIFF(MINUTE, landing.event_time, inblock.event_time)) as avg_taxi_in
FROM flight f
JOIN flight_event landing ON f.call_sign = landing.call_sign 
    AND landing.event_type = 'Actual_Landing'
JOIN flight_event inblock ON f.call_sign = inblock.call_sign 
    AND inblock.event_type = 'Actual_In_Block'
WHERE f.operation = 'ARRIVAL'
GROUP BY f.aircraft_type
ORDER BY avg_taxi_in DESC;

-- Gate utilization
SELECT 
    location as gate,
    COUNT(*) as events
FROM flight_event
WHERE location LIKE 'Gate_%'
GROUP BY location
ORDER BY events DESC;
```

## Configuration

Edit `scripts/config.py`:

```python
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'YOUR_PASSWORD',  # Or use environment variable
    'database': 'aiplane',
    'port': 3306
}
```

Or use environment variables:
```bash
export DB_HOST=localhost
export DB_USER=root
export DB_PASSWORD=your_password
```

## Documentation

- [INSTALL.md](INSTALL.md) - Complete installation and import guide
- [Schema ERD](https://lucid.app/lucidchart/6121bb49-c697-4003-b0b7-ea7448717f1f/) - Visual diagram

## Requirements

- MySQL 8.0+ or MariaDB 10.5+
- Python 3.8+
- ~100MB storage