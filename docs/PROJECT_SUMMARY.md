# Project Summary — SeaTac Airfield Data Intelligence

> **Repo layout:** this copy lives in `docs/`. Code is under `src/` (`src/backend`, `src/frontend`, `src/database`, `src/electron`). Files from the team's *OLD Data* folder are not in this repo.

> **Read this first.** It explains what the project is, how it got here, and where our team picks up.
> Related docs: [TECH_STACK.md](TECH_STACK.md) · [DB_SCHEMA.md](DB_SCHEMA.md) · [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) · [SETUP_GUIDE.md](SETUP_GUIDE.md) (run it locally)
>
> Written 2026-09-29 from `OLD Data/` and the `SeaTac-AI` repo at commit `111fd5a`. When something is uncertain, it is marked **⚠️ Unverified** or **❓ No documented reason**.

---

## 1. What this project is, in one paragraph

This is a **chat app for airport data.** A manager at Seattle-Tacoma International Airport (SEA) types a question in plain English, such as *"What's the average taxi-in time by aircraft type?"*. The system turns that question into a SQL query, runs it against a database of flight events, and replies with a short written answer plus a chart and/or a table. The client is the **Port of Seattle**, which runs SEA. The project is a Northeastern University capstone (the "Experience Expo" course), and a new student team has picked it up each semester.

## 2. Why it exists (the problem)

- The Port spent about **$10.8M on SAMS**, a surface management system from Saab that tracks aircraft on the airfield. It pays about **$1.2M/yr** to host it. The Port estimates it gets only **25–35%** of the system's value. (Source: `OLD Data/Port-of-Seattle-SEA-Airfield-Data-Intelligence.pdf` (in the team's OLD Data folder; not in this repo), p.2)
- SAMS data lands in a warehouse called **AerobahnDW**. One sample export has **593 columns** with cryptic names. See `AerobahnDW_sample_anonymized.xlsx` (team's `OLD Data/technical/AerobahnDW_sample_anonymized.xlsx`; not in this repo).
- When leadership has an operations question, today it goes to the BI team as a ticket. A Tableau report then takes **3 days to 2 weeks**, which is often too late to act on. (Sources: the same PDF, p.2; `AIport Final Presentation.pptx` (team's `OLD Data/AIport Final Presentation.pptx`; not in this repo), slide 2)
- **The goal:** let non-technical leaders get those answers themselves, in seconds.

### The "10 core questions"

The client wrote these (`OLD Data/technical/Gate Query User Story.docx` (in the team's OLD Data folder; not in this repo)). Every generation of the project has been scoped around them. For what the terms mean (taxi-in, off-block, and so on), see the event glossary in [DB_SCHEMA.md → Event types](DB_SCHEMA.md#event-types-what-each-one-means).

| # | Question | Why leadership wants it |
|---|---|---|
| 1 | Taxi-in performance: average taxi-in time by aircraft type | Know which aircraft types need extra buffer time |
| 2 | Taxi-out performance: average taxi-out time by hour of day | Find when the airfield surface is most congested |
| 3 | Movement-area occupancy: how many aircraft are on the taxiways at any moment | Understand how crowded the ground gets at peak hours |
| 4 | Runway occupancy time: average time from entering to leaving the runway | Measure how efficiently the runways are used |
| 5 | Wheels-up delay: scheduled vs actual takeoff times | Spot patterns in on-time departures |
| 6 | Weight-class comparison: taxi times for light vs medium vs heavy aircraft | See how aircraft size affects operations |
| 7 | Taxiway utilisation: which taxiway segments get the most use | Find traffic hotspots |
| 8 | Landing to in-block duration: time from touchdown to arriving at the gate | Look for taxiway congestion |
| 9 | Runway utilisation rate: takeoffs and landings per runway | See which runway carries the most load |
| 10 | Peak-hour prediction: forecast congestion from history | Plan resources |
| Bonus | "Metal on ground" report: aircraft on the ground at any time, by type and weight | Monitor capacity |

Later generations added an 11th type, **taxi-time breakdown** (taxi-in vs taxi-out combined). It is in the training data; see [TECH_STACK.md → AI layer](TECH_STACK.md#4-ai--model-layer).

---

## 3. History at a glance

| When | Who | What happened |
|---|---|---|
| Sep–Dec 2025 | **Fall 2025 team "AIport"**: Aurora Ouyang, Anqi Yu, Dora Ren, Yuwei Ma, Xiaoya Wang | Built the first working system: Electron + React + Flask + Gemini + MySQL. Final presentation Dec 4, 2025 |
| Jan–May 2026 | **Spring 2026 "Team 6"**: Abhishek Ghaisas, Nishant Kumar, Ishan Chaudhary, Zhiqi "Jo" Zhang | Rewrote the backend in FastAPI and experimented with LLMs (Gemini → fine-tuned CodeLlama plus a validator → Claude). Added login and CSV export, and deployed to Railway. Last commit May 7, 2026 |
| Fall 2026 | **Us (Team 3)** | Forked Abhishek's repo into [`github.com/Vatsalya2003/SeaTac-AI`](https://github.com/Vatsalya2003/SeaTac-AI). **No changes made yet** (see §6) |

---

## 4. Fall 2025 — "AIport" (the first generation)

The code is in `OLD Data/AIport-main/` (in the team's OLD Data folder; not in this repo), and the final deck is `AIport Final Presentation.pptx` (team's `OLD Data/AIport Final Presentation.pptx`; not in this repo).

### What they built

- A **desktop app**: Electron wrapping a React chat UI that looks like ChatGPT.
- A **Flask backend**. It first matched the question to one of about 12 *intents* by keyword. It then asked **Google Gemini** to write SQL, ran the SQL on **MySQL**, and filled in a **Python text template** with the results. If Gemini failed, it fell back to a **hand-written SQL template** for that intent.
- The **database design** that is still in use today: three tables built from one Excel export (725 flights, one operating day, 2025-08-08). Full details in [DB_SCHEMA.md](DB_SCHEMA.md).

### Key decisions they documented

| Decision | Reason given | Source |
|---|---|---|
| Build a chatbot instead of BI dashboards | The client said "We need answers, not dashboards" in week 4 | Final deck, slide 4 |
| Use Gemini's free tier instead of Claude | A $0 budget for APIs | Final deck, slides 4 and 6 |
| Limit scope to the 10 client questions | The original scope ("all aircraft data") was too broad | Final deck, slide 6 |
| Build a "semantic mapping layer" (rename the cryptic columns) | 600+ undocumented columns | Final deck, slides 6 and 11 |
| Keep hand-written SQL templates as a fallback | Keep working when the LLM fails or hits a rate limit | `AIport-main/QUICK_START.md` (team's `OLD Data/AIport-main/QUICK_START.md`; not in this repo) §8; final deck, slide 11 |

### What they got right

- **They narrowed the scope to real questions** from the client. Every later team kept this.
- **The data model.** Turning one wide spreadsheet into "one row per event" (`flight_event`) makes every question a simple time difference between two events. The schema survived two more generations unchanged except for additions.
- **A fallback path** when the LLM is unavailable.

### What they got wrong or left unfinished

- **Accuracy: 78%, short of their own 80% target.** Their README reports this (`AIport-main/README.md` (team's `OLD Data/AIport-main/README.md`; not in this repo)); the final slides leave accuracy out.
- **Answers were template text, not LLM summaries.** The slides say answers were "powered by Gemini 2.5 pro". In the code, Gemini only writes SQL (`AIport-main/backend/app.py` (team's `OLD Data/AIport-main/backend/app.py`; not in this repo)).
- **No real SQL safety.** A SELECT-only check exists (`validate_query`) but is never called.
- **The docs disagree with each other**: which Gemini model, which port, the "11th query type", script names. The full list is in [DEVELOPER_GUIDE.md → Inherited from Fall 2025](DEVELOPER_GUIDE.md#inherited-from-fall-2025-still-present).
- **The desktop packaging was never finished.** Icon paths are wrong, the build-output folders don't match, and the backend launcher expects a Windows-only `app.exe`.
- **The early UI demo videos** (`user interface demo.mp4` (team's `OLD Data/user interface demo.mp4`; not in this repo), `UIdemo-new.mp4` (team's `OLD Data/UIdemo-new.mp4`; not in this repo)) show canned answers about gates ("A1, A3, B5") that aren't in the data. ⚠️ They appear to be UI mock-ups, not the working system.

---

## 5. Spring 2026 — "Team 6" (the generation we inherited)

Sources: the mid-term deck `OLD Data/Port-of-Seattle-SEA-Airfield-Data-Intelligence.pdf` (in the team's OLD Data folder; not in this repo) (around late Feb 2026), plus **git history**. Most commit messages are just "Add files via upload", so the history shows *what* changed and *when*, rarely *why*.

### What they said at mid-term (around Feb 26)

- Move from **Flask to FastAPI** for "Pydantic type validation … improving LLM integration reliability" (PDF p.6, p.10).
- A **hybrid engine**: a keyword classifier answers about 60% of questions from 10 SQL templates, with Gemini 2.5 as the fallback. SQL injection would be blocked by allowing only SELECT (PDF p.5).
- They **hit Gemini's free-tier limit (20 requests/day)**, so they fine-tuned **Gemma 2-2B** on Modal for $0.35 (PDF p.8).
- They **dropped LangChain agents** because of breaking changes in LangChain v1.2.10 and orchestrated the steps by hand instead (PDF p.6, p.8).
- **Targets:** at least 90% accuracy and answers in 5 seconds or less. **Status:** 4 of the 10 questions working end-to-end (PDF p.10–11).
- **Data finding:** about **50% of runway events are missing in the source data** (not an ETL bug). This affects Q3, Q4 and Q9 (PDF p.4). ⚠️ When we checked, the pattern looks structural, not like missing data: departures only have a runway *entrance*, and arrivals only a runway *exit*. See [DB_SCHEMA.md → issue 4](DB_SCHEMA.md#known-schema-issues).

### What the code actually became (from git)

| Date | Commit | Change |
|---|---|---|
| Mar 11 | `ffcd4e8` | First FastAPI backend: LangChain plus **Gemini 2.5-flash** |
| Mar 13 | `f2dbd2c` | "Modal Edition v7.0": a **fine-tuned CodeLlama-7B** on Modal writes the SQL, and **OpenRouter** (Gemini 2.0 flash) checks it |
| Mar 18 | several | Frontend and database files uploaded to this repo |
| Mar 24 | `7c13e84`, `7feb7e9` (Jo) | Four **ramp event types** added to the schema and the import script (details in [DB_SCHEMA.md](DB_SCHEMA.md#known-schema-issues)) |
| Apr 13 | `90b73ee` | "Claude Validator v7.4": **Claude replaces OpenRouter** as the SQL checker. Saved as `backend/app.py` |
| May 4 | `bd96976`, `a1bd9f2` | **`backend/app_optimized.py` v8.0**: Claude writes the SQL directly and Modal is switched off "for presentation speed". **Railway deployment** config added |
| May 5 | many | Frontend: login screen, CSV export, chart/table toggle |
| May 7 | `111fd5a` | README updated with the live Railway link and demo login. **Last commit** |

**Important:** the mid-term plan and the final code differ.
- **Gemma 2-2B** doesn't appear anywhere in the repo. The fine-tuned model in the code is **CodeLlama-7B**. ❓ No documented reason for the switch.
- The **keyword classifier/hybrid engine** described at mid-term is **not in the deployed code**. There are only 2 hard-coded fallback templates.
- The **SELECT-only guard** described at mid-term is **not enforced** in the deployed pipeline. See [DEVELOPER_GUIDE.md → Known issues](DEVELOPER_GUIDE.md#6-known-issues).
- The README says the model is "CodeLlama-7B + **Claude 4.5 Haiku** validation". The deployed code defaults to **Claude Sonnet 4 (`claude-sonnet-4-20250514`)** and doesn't use CodeLlama at all. ⚠️ Railway may override the model with an environment variable; we can't see that setting.

### The state Team 6 left it in (May 2026)

- **Deployed:** the backend (`app_optimized.py`) runs on Railway, and the frontend probably does too. The README links to it with a shared demo login. ⚠️ Not verified that it's still live.
- **Pipeline in use:** the question goes to Claude, which writes SQL. The SQL gets an automatic fix for common event-name mistakes, a time filter is added, the query runs on MySQL, and Claude writes a 2–3 sentence "insight". Walkthrough in [DEVELOPER_GUIDE.md → How a query flows](DEVELOPER_GUIDE.md#3-how-a-question-flows-through-the-system-end-to-end).
- **Kept but switched off:** the CodeLlama fine-tune (`modal_finetune.py`, `modal_serve.py`), the training data (507 examples) and the Claude validator.
- **Claimed:** 91% accuracy ([`README.md`](../README.md)). Commit `37563d8` (Apr 26) changed the README figure from 78% to 91% with the message "Updated performance metrics". ⚠️ The repo has no test set, evaluation script or results, so we can't reproduce it. It's also unclear which pipeline was measured (CodeLlama + Claude, or Claude alone).
- **Not done** (compared with their own plan): user testing with the operations team, measured accuracy across all 10 questions, a working desktop (Electron) build, and real-time data.

---

## 6. Where we (Team 3) pick up

**What changed since we forked:** nothing. `git status` is clean, and the last commit (`111fd5a`, May 7, 2026) is Abhishek's. The only difference is the remote (`origin` now points to `Vatsalya2003/SeaTac-AI`).

**What we inherit:**
- A working web chat app, as long as you have a Claude API key and a MySQL database. See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for setup.
- Data for **one day** of anonymised flights (the airlines "QTA" and "ZYX"), not live data.
- A list of real bugs and risks, the most important being **no SQL safety** and a **time-filter bug that silently changes answers**. See [DEVELOPER_GUIDE.md → Known issues](DEVELOPER_GUIDE.md#6-known-issues).
- The roadmap from earlier teams: *Phase 2* is real-time data and predictive alerts; *Phase 3* is all aircraft operations plus network deployment (Fall 2025 deck, slide 14).

**Questions to settle with the client and advisors early** (these are open questions, not decisions):
1. Which LLM path should we keep: Claude direct (costs money, currently used), the fine-tuned CodeLlama on Modal (cheaper, currently off), or something else? What is the budget?
2. Is the 91% accuracy figure trusted? If not, we need an evaluation set first.
3. Will the Port provide more data, or live access to AerobahnDW?
4. Is the desktop (Electron) app still wanted, or is the web app enough?

---

## Source material index

| File | What it's good for |
|---|---|
| `OLD Data/technical/Gate Query User Story.docx` (in the team's OLD Data folder; not in this repo) | The 10 questions and the columns each one needs |
| `OLD Data/technical/700-041227_Data_Dictionary V2.xlsx` (in the team's OLD Data folder; not in this repo) | Official definitions of the Aerobahn/SAMS fields |
| `OLD Data/technical/cleaned_user_story_columns.xlsx` (in the team's OLD Data folder; not in this repo) | The raw columns filtered per question (one sheet per question) |
| `OLD Data/technical/AerobahnDW_sample_anonymized.xlsx` (in the team's OLD Data folder; not in this repo) | The raw 593-column export |
| `OLD Data/technical/aerobahn_thematic_tables.xlsx` (in the team's OLD Data folder; not in this repo) | An alternative split into flights/aircraft/assignments/events. ⚠️ It seems to be what Jo's import script expects; see [DB_SCHEMA.md](DB_SCHEMA.md#known-schema-issues) |
| `OLD Data/technical/Arrival Hold Visual.jpg` (in the team's OLD Data folder; not in this repo) | Picture defining hold time, taxi time and gate-rest time |
| `OLD Data/technical/Seattle SAMS Saab User Conference.pdf` (in the team's OLD Data folder; not in this repo) | Background on SAMS, gate holds and predicted off-block time. SEA has 3 runways and 88 gates |
| `OLD Data/technical/Airport Operations Database as of 9Aug2022.pdf` (in the team's OLD Data folder; not in this repo) | Where the Port's data comes from (a diagram of the systems feeding its operations database) |
| `OLD Data/technical/technicalarch.drawio` (in the team's OLD Data folder; not in this repo) | Fall 2025's *planned* architecture. It includes an auth service and "semantic views" that were never built |
