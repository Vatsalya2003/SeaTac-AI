# AIport

> AI-powered conversational interface for airport gate utilization analysis at Seattle-Tacoma International Airport

## Overview

This system converts natural language queries into SQL for gate utilization analytics, reducing report generation time from **2 weeks to under 2 minutes**.

**Client:** Port of Seattle  
**Institution:** Northeastern University Capstone Project

### Problem
- Manual BI reporting takes 1-2 weeks
- AerobahnDW contains 600+ unclear columns
- 25+ weekly requests creating backlog

### Solution
ChatGPT-like desktop interface using Google Gemini API for NLP-to-SQL conversion.

## Performance Metrics

| Metric | Result | Target |
|--------|--------|--------|
| Query Accuracy | 91% | 80% ✓ |
| Response Time | <45 sec | <120 sec ✓ |
| Time Reduction | 99.8% | — |
| Supported Query Types | 11 | 10+ ✓ |

## Tech Stack

| Layer | Technology |
|-------|------------|
| Desktop App | Electron |
| Frontend | React 18 + TypeScript + Vite |
| Backend | FastAPI + Python 3.8+ |
| AI/NLP | CodeLlama-7B + Claude 4.5 Haiku validation |
| Database | MySQL 8.0 |
| UI Components | shadcn/ui + Tailwind CSS |

## Screenshot

Sample Query and Response

<img width="1470" height="956" alt="Screenshot 2026-03-17 at 8 53 05 PM" src="https://github.com/user-attachments/assets/42c8e405-603d-4547-9b63-85a545a44a8c" />


## Quick Start

Needs MySQL 8+, Python 3.11/3.12 and Node 18+. The full, tested walkthrough is in [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md).

```bash
# 1. Clone and load the chatbot's database (Team 6's sample data, AIplane)
git clone https://github.com/Vatsalya2003/SeaTac-AI.git && cd SeaTac-AI
mysql -u root -p -e "source src/database/data/AIplane.sql"

# 2. Backend: create src/backend/.env by hand with CLAUDE_API_KEY and DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME=AIplane
cd src/backend
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app_optimized:app --reload --port 8000          # check http://localhost:8000/api/health

# 3. Frontend (second terminal)
cd src/frontend && npm install && npm run dev           # open http://localhost:3000

# 4. Optional: load the Port's updated data into the new `seatac` database (file obtained privately)
cd src/database && python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cd scripts && python load_aerobahn.py --file /path/to/August_8_and_9_2025_Anonymized.xlsx && python check_seatac.py
```

> **Port of Seattle data is not in this repo.** The Port's updated export (`August_8_and_9_2025_Anonymized.xlsx`) contains real tail numbers and transponder codes. It is shared privately within the team and must never be committed, and neither may any dump of the `seatac` or `AIplane_v2` databases (`.gitignore` blocks the usual file names). The new database is documented in [docs/DB_SCHEMA.md](docs/DB_SCHEMA.md), and the differences from the old sample in [docs/DATA_CHANGES.md](docs/DATA_CHANGES.md). The chatbot still uses the old `AIplane` database until it is switched to the new views.

## Project Structure

```
AIport/
├── docs/                        # Project Plan, setup & developer guides
├── src/
│   ├── electron/
│   │   └── main.js              # Electron main process
│   ├── backend/
│   │   ├── app.py               # Flask API server
│   │   ├── requirements.txt     # Python dependencies
│   │   └── .env.example         # Environment template
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── api/             # API client
│   │   │   ├── components/      # React components
│   │   │   └── App.tsx          # Main component
│   │   └── package.json
│   └── database/
│       ├── data/
│       │   ├── AIplane.sql      # Database dump
│       │   └── field_mapping.xlsx
│       └── scripts/
│           ├── db_manager.py    # Database CLI tool
│           └── config.py        # Database configuration
├── package.json             # Electron configuration
├── QUICK_START.md
├── AI_USE.md                # How AI tools were used
└── README.md
```

## Supported Queries

The system supports 11 core query types:

| # | Query Type | Example |
|---|------------|---------|
| 1 | Taxi-In Performance | "Compare taxi-in times by aircraft type" |
| 2 | Taxi-Out Performance | "View taxi-out times across different hours" |
| 3 | Movement Area Occupancy | "Monitor aircraft in movement area" |
| 4 | Runway Occupancy | "Calculate runway occupancy times" |
| 5 | Wheels-Up Delay | "Identify delay patterns" |
| 6 | Weight Class Comparison | "Compare taxi duration by weight class" |
| 7 | Taxiway Utilization | "See which taxiway segments are most used" |
| 8 | Landing to In-Block | "Analyze landing to in-block duration" |
| 9 | Runway Utilization | "Show runway utilization rate" |
| 10 | Peak Hour Analysis | "Predict peak hours based on historical data" |
| 11 | Taxi Time Breakdown | "Compare taxi-in vs taxi-out by aircraft type" |

## Database Schema

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

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/query` | POST | Process natural language query |
| `/api/health` | GET | Health check |
| `/api/stats` | GET | Database statistics |

## Team

| Name | Role |
|------|------|
| Abhishek Ghaisas | AI/ML Lead |
| Nishant Kumar | Project Manager |
| Ishan Chaudhary | Backend and Data Lead |
| Zhiqi Zhang | Frontend and Data Lead |

## Acknowledgments

- **Port of Seattle** — Project sponsor and data provider
- **Northeastern University** — Capstone program

## License

- **Code:** MIT License
- **Data:** Proprietary to Port of Seattle
