# SeaTac AI

> A natural-language assistant that answers airport operations questions from Seattle-Tacoma International Airport (SEA) airfield data.

**Industry partner:** Port of Seattle, Aviation Operations
**Program:** Northeastern University, Experience Expo, Fall 2026 (Team 2)
**Faculty advisor:** Prof. David Fannin

---

## Overview

SeaTac has limited space to grow, so the Port relies on data to run its runways, taxiways and gates efficiently. Airport leaders often need quick answers, such as how long aircraft take to taxi or which hours are busiest. Today, getting those answers means asking IT or business intelligence staff to write queries and build reports.

This project lets leaders ask those questions in plain English. The goal for this term is **trust**: every answer must either be correct, with the definition and sample size it used, or clearly explain why the data can’t answer the question.

## Current status (October 2026)

| Area | Status |
|---|---|
| Chatbot (web app + API) | Runs locally on the previous cohort’s database (`AIplane`). Not yet switched to the new views |
| New database (`seatac`) | Built from the Port’s updated export: raw table, clean `flights` table, `aircraft_types` and 7 metric views (plus one helper view) |
| Baseline database (`AIplane_v2`) | The new data in the previous cohort’s table layout, so the unchanged chatbot can be tested fairly |
| Question definitions | Confirmed by the Port for all 10 priority questions; Q3 boundary and Q7 details (section-entry timing, Tango/Hotel/Whiskey, `B_SSR`) still pending |
| Expected answers | Being calculated by hand by the team |
| Accuracy testing | Not started; baseline run next |

## The Port’s 10 priority questions

| # | Question |
|---|---|
| Q1 | Taxi-in time by aircraft type |
| Q2 | Taxi-out time by hour |
| Q3 | Movement area occupancy |
| Q4 | Runway occupancy time |
| Q5 | Takeoff (wheels-up) delay |
| Q6 | Taxi times by weight class |
| Q7 | Taxiway usage |
| Q8 | Wheels-down to parking time |
| Q9 | Runway activity |
| Q10 | Peak hours (historical only) |

The definition of each question is in [`src/database/metric_rules.yaml`](src/database/metric_rules.yaml) and [`docs/DB_SCHEMA.md`](docs/DB_SCHEMA.md).

## How it works

**Today:** the user types a question → the backend asks an LLM to write SQL → the SQL runs on MySQL → the LLM writes a short summary → the app shows text, a table and a chart.

**Planned for this term:** the chatbot will query only the new metric views, which have the Port’s definitions and exclusion rules built in. Each answer will state the definition used and how many flights were included or excluded.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Chart.js |
| Backend | Python 3.12, FastAPI |
| Database | MySQL 8 (`AIplane`, `seatac`, `AIplane_v2`) |
| Data loading | pandas, openpyxl, PyMySQL |
| LLM | Anthropic Claude (Gemini support in progress) |

The Electron desktop wrapper from Fall 2025 is still in `src/electron/` but can’t be built or run.

## Repository structure

```
SeaTac-AI/
├── AI_USE.md                 How AI tools were used, and how we verified the output
├── LICENSE
├── README.md
├── docs/
│   ├── PROJECT_SUMMARY.md    Background and history
│   ├── TECH_STACK.md         Technologies and versions
│   ├── DB_GUIDE.md           Start here for the new database: layers, views, rules, how to contribute
│   ├── DB_SCHEMA.md          The new database: tables, views, keys, checks
│   ├── seatac_schema.sql     Structure-only schema export (no data), for ER diagram tools
│   ├── DATA_CHANGES.md       Old sample vs the Port’s updated data
│   ├── DEVELOPER_GUIDE.md    How the code works, known issues
│   ├── SETUP_GUIDE.md        Step-by-step local setup
│   ├── PROPOSAL_FACT_CHECK.md
│   ├── QUERY_EXAMPLES.md
│   ├── legacy/               The previous cohort’s schema doc
│   └── SeaTac-AI_Project_Plan_V3.pdf
└── src/
    ├── backend/              FastAPI chatbot (app_optimized.py is the live server)
    ├── frontend/             React web app
    ├── database/
    │   ├── data/AIplane.sql  The previous cohort’s sample database
    │   ├── scripts/          load_aerobahn.py, check_seatac.py, build_aiplane_v2.py, create_reader.py
│   ├── tests/            Automated tests for the seatac database (pytest -q)
    │   ├── sql/              seatac_views.sql (the metric views)
    │   ├── metric_rules.yaml Definitions for the 10 questions
    │   └── requirements.txt
    └── electron/             Fall 2025 desktop wrapper (not runnable)
```

New to the database? Start with [docs/DB_GUIDE.md](docs/DB_GUIDE.md), then [docs/DB_SCHEMA.md](docs/DB_SCHEMA.md) for the full column reference.

## Quick start

Needs MySQL 8+, Python 3.11/3.12 and Node 18+. The full, tested walkthrough is in [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md).

```bash
# 1. Clone and load the chatbot's current database (AIplane)
git clone https://github.com/Vatsalya2003/SeaTac-AI.git && cd SeaTac-AI
mysql -u root -p -e "source src/database/data/AIplane.sql"

# 2. Backend: create src/backend/.env by hand with your LLM key and DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME=AIplane
cd src/backend
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app_optimized:app --reload --port 8000     # check http://localhost:8000/api/health

# 3. Frontend (second terminal)
cd src/frontend && npm install && npm run dev      # open http://localhost:3000

# 4. Optional: build the new seatac database from the Port's file (obtained privately)
cd src/database && python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cd scripts && python load_aerobahn.py --file /path/to/August_8_and_9_2025_Anonymized.xlsx && python check_seatac.py
```

## Data

The Port’s updated export **is not in this repo**. It contains real aircraft tail numbers and transponder codes, so it is shared privately within the team. Never commit it, or any dump of the `seatac` or `AIplane_v2` databases. `.gitignore` blocks the usual file names.

## Known issues

The inherited chatbot has several known accuracy issues, which this term’s work addresses. They are listed in [docs/DEVELOPER_GUIDE.md §6](docs/DEVELOPER_GUIDE.md#6-known-issues).

---

## Project history

This is the third generation of the project. Each cohort built on the one before.

### Fall 2025: AIport

- **Team:** Aurora Ouyang, Anqi Yu, Dora Ren, Yuwei Ma, Xiaoya Wang
- **Built:** a desktop app (Electron + React + Flask) using Google Gemini to turn questions into SQL over a MySQL sample of one operating day.
- **Key decisions:**
  - pivoted from BI dashboards to a chatbot, after the client asked for “answers, not dashboards”
  - narrowed the scope to the Port’s 10 priority questions
  - used Gemini’s free tier because the API budget was $0

### Spring 2026: Team 6

- **Team:** Abhishek Ghaisas, Nishant Kumar, Ishan Chaudhary, Zhiqi Zhang
- **Built:** moved the backend from Flask to FastAPI and deployed the React app as a web app on Railway.
- **AI approach:**
  - tried LangChain and Gemini, then a fine-tuned CodeLlama-7B model on Modal (now switched off)
  - the final version uses Claude to write the SQL directly
- **Deployment:** the app was hosted on Railway. That deployment is no longer live.
- **Reported results:** the previous README reported 91% query accuracy. The repository has no test set or evaluation script, so this figure couldn’t be verified.

### Fall 2026: Team 2 (current)

- **Starting point:** forked from Team 6’s repository and documented the inherited code and data (see [docs/](docs/)).
- **Definitions:** the Port confirmed definitions for the 10 priority questions (Q3 and Q7 details still pending).
- **New data:** the Port provided an updated, more complete export (1,061 flight legs vs 725 in the old sample). We built a new database around it, with the definitions in metric views.
- **This term’s focus:** answer accuracy, honest limits when data is missing, and a measured before/after comparison.

## Team (Fall 2026)

Vatsalya Dabhi, Yani Hu, Jinghan Liang, Tianqing Mao, Shamali Pachpande, Hanyu Xu, Luwei Yang

## Acknowledgments

- **Port of Seattle:** Samer Tirhi (Technology Manager, Aviation Operations) and Samad Aidane (Senior IT Project Manager), for the data, definitions and guidance
- **Northeastern University:** Prof. David Fannin and the Experience Expo instructors
- **Previous cohorts:** the Fall 2025 and Spring 2026 teams, whose work this project builds on

## License

- **Code:** Apache 2.0 (see [LICENSE](LICENSE))
- **Data:** proprietary to the Port of Seattle
