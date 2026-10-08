# Project Plan — Fact Check

> **Repo layout:** this copy lives in `docs/`. Code is under `src/` (`src/backend`, `src/frontend`, `src/database`, `src/electron`). Files from the team's *OLD Data* folder are not in this repo.

> Each claim in our Project Plan, checked against the code, the data and the source documents.
> Related: [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) · [DB_SCHEMA.md](DB_SCHEMA.md) · [TECH_STACK.md](TECH_STACK.md)

**How this was checked (2026-10-06):**
- **Read-only.** Nothing in `SeaTac-AI/` was modified. No LLM API (Gemini or Claude) was called.
- **Code** is cited from the **committed** version (`git show 111fd5a:<file>`), because the plan describes the inherited system. Our local working copy has uncommitted edits (Gemini switch, version pins). Those shift line numbers in `app_optimized.py` after line 60 (+6 lines) and after line 1123 (+38 lines).
- **Data:** MySQL was **not running** (`mysqladmin ping` → "Can't connect"). So the 3 `INSERT` statements in `database/data/AIplane.sql` (unchanged since `111fd5a`, no backslash escapes) were loaded into a throwaway in-memory SQLite database and queried with SQL. **Queries are SQLite dialect**, and minutes are computed as `(julianday(b) - julianday(a)) * 1440`.
- **Behaviour checks** (claims 5–6) imported the committed `app_optimized.py` with `CLAUDE_API_KEY=` and `GEMINI_API_KEY=` empty. The log confirmed `claude_client is None`, so no LLM client existed.
- **Secrets** are reported as *present* or *absent*, never printed.

Status key: ✅ verified · ❌ false · ⚠️ partly true / needs a caveat · ❓ can't verify from code or data

---

## Phase 1 — Code claims

| # | Claim | Status | Evidence | Correct wording for the proposal |
|---|---|---|---|---|
| 1 | The written summary is generated from only the first 3 result rows | ✅ | `app_optimized.py:1726` `_generate_insights`; `:1737` `DATA SAMPLE: {json.dumps(data[:3] …)}`. The prompt (`:1734-1740`) contains only the question and those 3 rows, not the total row count | "The AI-written summary sees only the question and the first 3 result rows, not the row count or the rest of the result." |
| 2 | On SQL-generation failure, a fallback runs `SELECT * FROM flight LIMIT 10` or a prebuilt query, and the user isn't told | ✅ | `:1474-1481` falls back when generation returns nothing; `:1628-1635` keyword match to 2 templates, else `return "SELECT * FROM flight LIMIT 10"`. `sql_source` is returned (`:1838`) but the frontend **never displays it**. It's only `console.log`ged (`api/query.ts:50`) and stored in `metadata` (`App.tsx:252-258`); the `ChatMessage` props have no `metadata` field (`ChatMessage.tsx:12-19`). The summary step then describes the fallback rows as if they answered the question. Note the fallback triggers only when *generation* fails. If generated SQL errors or returns 0 rows, the user gets "SQL failed: …" or "No data found." (`:1676`, `:1684`) | "If the AI can't produce SQL, the app silently runs one of 2 templates or `SELECT * FROM flight LIMIT 10` and summarises that as the answer. The UI never shows that a fallback was used." |
| 3 | `DETAILED_SCHEMA` covers only 4 of 18 event types and 6 of 15 `flight` columns | ✅ | `:1068-1116`. **flight columns listed (`:1072`):** `call_sign, aircraft_type, operation, flight_number, origin_airport, destination_airport`. **Missing (9):** `id, flight_ID, aircraft_registration, departure_procedure, flight_origination_date, schedule_departure, actual_departure, schedule_arrival, actual_arrival`. **Event types listed (`:1079-1082`):** `Actual_Take_Off, Actual_Landing, Actual_Off_Block, Actual_In_Block`. **Missing (14):** `Scheduled_Off_Block, Movement_Area_Entrance, Runway_Entrance, Estimated_Take_Off, Scheduled_Take_Off, Estimated_Landing, Runway_Exit, Movement_Area_Exit, Estimated_In_Block, Boarding_Start, North_Ramp_Enter, North_Ramp_Exit, South_Ramp_Enter, South_Ramp_Exit` (the full enum is in `AIplane.sql`). Also `flight_event` lists 5 of 7 columns (no `id`, `event_source`), and `aircraft_type` lists all 5 | As claimed. Optionally add: "…so questions about runways, the movement area, schedules or delays rely on the model guessing column and event names." |
| 4 | The prompt doesn't explain which timestamp to use, join rules for duplicate call signs, the location trap, or airport terms | ✅ | What it **does** say (`:1076-1115`): exact-case event names for the 4 `Actual_*` events; the taxi-in and taxi-out formulas (`:1088-1099`); rules "ALWAYS match operation field in JOINs", "ALWAYS filter invalid times: BETWEEN 1 AND 120", "NEVER use NOW()", "ALWAYS include LIMIT clause" (`:1101-1106`); one example using `COUNT(DISTINCT f.call_sign)` joined on `call_sign` only (`:1108-1115`). The SQL instructions (`:278-292`) add 7 generic rules. **Absent:** scheduled vs ATC-estimate vs actual timestamps; that `call_sign` isn't unique; the location trap; definitions of in-block, off-block, wheels-up and movement area. ⚠️ Extra finding: the global "BETWEEN 1 AND 120" rule would drop early (negative) delays and bias delay statistics | "The prompt gives formulas only for taxi-in and taxi-out. It doesn't say which timestamp family to use, that call signs repeat, that some locations belong to the other airport, or what airport terms mean. Its single example counts flights with `COUNT(DISTINCT call_sign)`, which undercounts." |
| 5 | Hour-filter bug | ✅ | Ran `TemporalContextExtractor` directly (`:841-987`; regex at `:868`). "Show the top 10 aircraft types by taxi-out time" → `specific_hours: [10]`; on taxi-out SQL using the prompt's `offblock` alias it injected **`AND HOUR(offblock.event_time) = 10`**. "Which 5 gates are busiest?" → `specific_hours: [5]`; injected **`AND HOUR(fe.event_time) = 5`** when the SQL used `fe.event_time`, and nothing when the SQL had no `event_time` (`:915-917`). (Test SQL was written by the checker to mirror the prompt's aliases; no LLM involved) | "Any 1–2 digit number in a question is read as an hour. 'Top 10 …' silently becomes 'only 10 a.m. events' whenever the generated SQL uses an event-time alias the code recognises (`offblock`, `landing`, `takeoff`, `le`, `fe`)." |
| 6 | Small-talk bug | ✅ | `GreetingHandler.is_greeting_or_casual` (`:108-130`), run directly: "Can you show taxi-in times by aircraft type?" → **True**; "which gates busiest?" → **True** (≤3 words, contains "hi"); "Explain taxi-out delays" → **True**; "hi" → **True** (correct) | "Data questions starting with 'Can you', 'Explain', 'Help', 'Tell me about' or 'How do I', and short ones containing 'hi', 'yo' or 'sup', are treated as small talk and return no data." |
| 7 | No clarification flow and no conversation context | ✅ | `QueryRequest` has a single field, `query: str` (`:1131-1132`). The frontend sends only `JSON.stringify({ query })` (`api/query.ts:30`) via `queryAPI(userMessage)` (`App.tsx:236`). Chat threads live only in browser `localStorage`. No history, session ID or follow-up path reaches the backend; every LLM call is a single user message (`:154`, `:298`, `:1747`) | "Every question is answered in isolation: the backend receives only the current text, with no history and no way to ask a clarifying question." |
| 8 | User-facing error and empty-result messages | ✅ | **Backend:** `"SQL failed: {db error}"` (`:1676`); `"No data found."` (`:1684`); `"Found {n} results"` when no summary is shown or summarising fails (`:1372`, `:1732`, `:1751`); `"Error: {exception}"` (`:1722`); HTTP 400 `"Invalid query"` (`:1797`); HTTP 503 `"No SQL generator configured"` (`:1822`); HTTP 500 `"Error: …"` (`:1842`); greeting fallbacks (`:163-192`). **Frontend:** non-2xx is shown as `"HTTP {status}: {body}"` (thrown in `api/query.ts`, returned as the message); `"Cannot connect to backend at {url}. Please ensure backend is running."` (`:82`); `"Query failed"` (`:57`); `"No response"` (`App.tsx:247`); `"Error: …"` (`App.tsx:288`); table: `"No results found"` / `"No data available"` (`DataTableWithExport.tsx:243`) | List as above. Note that raw database errors are shown to users verbatim. |
| 9 | ChartGenerator: line if the label contains "hour", else bar; max points | ✅ | Label column = first key containing hour/type/class/airport/operation (`:1248-1251`); value column prefers `avg` (`:1254-1264`); **`chart_type = 'line' if 'hour' in label_field.lower() else 'bar'`** (`:1313-1314`); **max 24 points** (`data[:24]`, `:1296`). A chart is produced only if `OutputFormatClassifier` asks for one (`:1015-1061`; e.g. "chart", "plot", "compare", "by hour"). The table is always included (`:1707`) | "The backend picks a line chart when the label column mentions 'hour', otherwise a bar chart, capped at 24 points. Users can switch to bar, line or pie in the UI." |
| 10 | Chart and table features that work | ✅ | Bar/line/pie switch (`ChartVisualization.tsx:388,397,406`); PNG export: with summary, chart only, high-res (`:268,277,321`); copy image and text to clipboard (`:338-349`); CSV export (`DataTableWithExport.tsx:118-130`); search across columns (`:57-64`, `:191`); sort asc/desc/off (`:100-115`); paging, 15 rows per page (`:94`, `ChatMessage.tsx:113,132`) | As listed. Not run in a browser for this check; verified by code reading (they were seen working in the UI on 2026-10-01) |
| 11 | Which backend file runs; does the README quick start work? | ⚠️ / ❌ | **Railway runs `app_optimized.py`:** `Procfile:1` and `railway.json:7` (`uvicorn app_optimized:app`). **The README quick start runs the older file:** `README.md:74` `cd backend && python app.py` → `app.py:1758` `uvicorn.run("app:app")` (v7.4). It **doesn't work as written**: `cp .env.example .env` (`:63`), but the file is **missing**; `cd ../ && npm install` and `npm run dev` at the root (`:70,77`), but there's **no root `package.json`**; `QUICK_START.md` (`:80`) is **missing**; it says `DATABASE_PASSWORD` (`:64`), but the code reads `DB_PASSWORD` (`app_optimized.py:1170`, `app.py:1082`); it says `MODAL_API_KEY` (`:65`), but the code reads `MODAL_ENDPOINT`. **`backend/setup.sh`** has `set -e` and `cp .env.example .env` (`:69`) on a missing file, so the script stops there. It also asks for `GEMINI_API_KEY` (`:71,83`, unused by the committed code) and points at `database/AIplane.sql` (`:90`; the real path is `database/data/AIplane.sql`) | "The deployed backend is `app_optimized.py`. The README quick start would start the older `app.py` and fails as written (missing `.env.example`, root `package.json` and `QUICK_START.md`; wrong variable names)." |
| 12 | Are the validators called in the live path? | ✅ (not called) | **`app_optimized.py`:** `ClaudeSQLValidator` is created (`:1765`) and passed to the agent (`:1770`). Its only call (`:1516`) is **inside the commented-out string block `:1486-1588`**, so it's never executed. `SQLValidator` is only used inside `ClaudeSQLValidator` (`:601,612`). **`app.py`:** Stage 1, Modal-generated SQL, **is validated** (`:1369-1380`). Stage 4, fresh Claude SQL, is **not** validated (`:1404-1442`). Stage 5, prebuilt SQL, is **not** validated (`:1444`). Without `MODAL_ENDPOINT`, every query skips validation | "In the deployed backend, no generated SQL is validated before running. In the older `app.py`, only Modal-generated SQL was checked." |
| 13 | Security | ✅ | Default DB user `root` (`app_optimized.py:1169`, `app.py:1081`); default password empty (`:1170`). CORS `allow_origins=["*"]` with `allow_credentials=True` (`:51-52`). `database/scripts/config.py:16`: a **non-empty hard-coded fallback DB password is PRESENT** (value not reproduced). Demo logins are hard-coded in the browser: `App.tsx:112-113` (two accounts), also `useAuth.tsx:15-16` (unused) and `Login.tsx:99` (unused). Login is client-side only; the backend has no auth. `README.md:5-8`: a public Railway app URL wrapped in an Outlook safelink that **contains a personal university email address (PRESENT)**, plus the demo username and password (**PRESENT**) | "The API is public (CORS `*`, no backend auth), the login is a hard-coded client-side check, the database defaults to `root`, and the README publishes the live URL, demo credentials and a personal email. A fallback DB password is committed in `config.py`." |
| 14 | LLM calls per data question | ✅ | **`app_optimized.py`:** 2 per data question, writing the SQL (`:294`) and the summary (`:1743`). Only 1 if the SQL fails or returns 0 rows (returns before `:1691`). Greetings use 1 (`:150`) and no SQL. Validator call `:680` is never reached (claim 12); `:1558` is in the commented block. **`app.py`:** up to 4, namely Modal HTTP (`:356`), Claude validate (`:592`), Claude fresh SQL if validation fails (`:1422`), and summary (`:1605`) | "Each data question costs 2 LLM calls (SQL plus summary); greetings cost 1." |
| 15 | 91% accuracy in the README; any test or eval set? | ⚠️ | `README.md:29`: `\| Query Accuracy \| 91% \| 80% ✓ \|`. Introduced by commit `37563d8` (2026-04-26, "Revise performance metrics…"), which changed **78% → 91%**. `git ls-tree -r 111fd5a` has **no** test, eval, benchmark or ground-truth files (path matches were only `app.spec` and `ui/aspect-ratio.tsx`). `git grep` finds **no** `pytest`, `unittest`, `assert` or evaluation script. "Evaluate" appears only as text in training data | "Team 6's README reports 91% accuracy (changed from 78% in April 2026), but no test set, evaluation script or results exist in the repo, so the figure can't be reproduced." |
| 16 | Installed versions; deprecated model; does `LLM_PROVIDER=gemini` work? | ⚠️ | **Installed** (`node --version`, `require(pkg/package.json)`, `pip list`, `mysqld --version`): Node 22.8.0 · React 18.3.1 · TypeScript 5.9.3 (declared `^5.3.3`) · Vite 6.4.3 (declared `^6.3.5`) · Chart.js 4.5.1 (lockfile) · Python 3.12.12 · FastAPI 0.109.0 · **Pydantic 2.13.5** (committed pin is `==2.6.0`; our uncommitted change makes it `>=2.12.5,<3`) · MySQL server 8.4.8 (the dump was made with 9.5.0). **Model:** default `claude-sonnet-4-20250514` (`app_optimized.py:59`). Anthropic's model reference, as read on 2026-10-01 via the Claude API reference bundled with Claude Code, lists it under **Deprecated, retirement date TBD**. **Gemini:** `LLM_PROVIDER` occurs **0 times** in committed `app_optimized.py` and 5 times in our working copy. It worked end-to-end in our uncommitted copy on 2026-10-01 (e.g. "Which destination airports have the most departures?" → PANC 23, matching a direct DB count). It was **not re-tested today** (no LLM calls allowed) | "Stack: React 18 / TypeScript 5.9 / Vite 6 / Chart.js 4.5 on Node 22; Python 3.12 / FastAPI 0.109 / Pydantic 2.13; MySQL 8.4. The default Claude model is deprecated. Gemini support exists only in our uncommitted local changes." |
| 17 | Is the Electron app runnable? | ❌ | No root `package.json` at `111fd5a`, and no `electron` dependency anywhere. `electron/main.js:41` icon `frontend/public/airportlogo.png` (the real file is `aiportlogo.png`); `:53` production loads `../frontend/index.html` (the dev HTML; the Vite build goes to `build/`, `vite.config.ts:53`); `:17` spawns `backend/app.exe` (Windows-only, and `backend/app.spec` packages the **older** `app.py` with a stale `google.generativeai` import) | "The Electron desktop wrapper isn't runnable: no package manifest, wrong file paths, Windows-only backend launcher." |
| 18 | "2 of 10 priority questions have confirmed query support" | ✅ | See the table below. **Q1 and Q2 meet all three conditions (2 of 10).** Q8 meets (b) and (c) but has no template | As claimed: "2 of the Port's 10 questions (taxi-in by type, taxi-out by hour) have a fallback template, prompt guidance and complete data." |

### Claim 18 detail: the Port's 10 questions

(a) = prebuilt fallback template in `app_optimized.py:1402-1439`; (b) = covered by a formula or example in `DETAILED_SCHEMA` (`:1068-1116`); (c) = the needed events exist in the data (event coverage query in the appendix).

| # | Port question | (a) template | (b) prompt | (c) data | All 3 |
|---|---|---|---|---|---|
| 1 | Taxi-in performance by aircraft type | ✅ `use_cases["1"]` | ✅ taxi-in formula | ✅ 353 of 354 arrivals have landing + in-block | ✅ |
| 2 | Taxi-out performance by hour | ✅ `use_cases["2"]` | ✅ taxi-out formula | ✅ 361 of 361 departures have off-block + take-off | ✅ |
| 3 | Movement-area occupancy | ❌ | ❌ | ⚠️ `Movement_Area_Entrance` only on departures (366), `Exit` only on arrivals (357); no flight has both, so it needs a per-operation definition | ❌ |
| 4 | Runway occupancy time | ❌ | ❌ | ⚠️ no flight has both runway events (claim 23); per-operation proxies only | ❌ |
| 5 | Wheels-up delay | ❌ | ❌ | ✅ `Scheduled_Take_Off` + `Actual_Take_Off` on departures | ❌ |
| 6 | Weight-class comparison | ❌ | ⚠️ formulas plus `weight_class` listed, no example | ⚠️ only Medium (709 flights) and Heavy (16); **no Light** | ❌ |
| 7 | Taxiway utilisation (Tango/Hotel/Whiskey) | ❌ | ❌ | ⚠️ 13 `TaxiwaySegment_*` codes, only on departures' movement-area entry; no Tango/Hotel/Whiskey names | ❌ |
| 8 | Landing to in-block duration | ❌ | ✅ (same events as taxi-in) | ✅ | ❌ |
| 9 | Runway utilisation rate | ❌ | ❌ | ✅ if filtered by operation (otherwise the location trap doubles counts, claim 22) | ❌ |
| 10 | Peak-hour prediction | ❌ | ❌ | ⚠️ one day of history; no basis for prediction | ❌ |

---

## Phase 2 — Data claims (from `AIplane.sql` via in-memory SQLite)

| # | Claim | Status | Evidence | Correct wording for the proposal |
|---|---|---|---|---|
| 19 | Date range and counts | ✅ | 725 flights · 7,995 `flight_event` rows · 16 aircraft types. Events run from `2025-08-07 15:32:00` to `2025-08-09 11:12:53`; **7,728 of 7,995 (96.7%) are on 2025-08-08** (73 on Aug 7, 194 on Aug 9). `flight_origination_date` is 2025-08-08 (247) or 2025-08-09 (117) for departures, and NULL for all arrivals | "One operating day (8 Aug 2025, with overnight spill-over): 725 flight legs, 7,995 timestamped events, 16 aircraft types." |
| 20 | Airline codes | ✅ | Call-sign prefixes: **QTA 504, ZYX 221**, no others (`rtrim(call_sign,'0123456789')`) | "Two anonymised airline codes only (QTA, ZYX)." |
| 21 | Distinct call signs vs flights | ✅ | 725 flights, **660 distinct call signs**; 63 call signs appear more than once. **10 repeat within the same operation:** QTA1201 (ARR), QTA185 (DEP), QTA229 (ARR), QTA328 (DEP), QTA409 (ARR), QTA536 (DEP), QTA924 (DEP), ZYX328 (ARR), ZYX448 (DEP), ZYX652 (DEP) | "Call signs aren't unique: 660 for 725 legs. 10 repeat within the same direction, so joins on call sign + operation still duplicate rows." |
| 22 | Location trap | ✅ (the "other airport" reading is an inference; see the note) | **3,188 events** that occur at the *other* airport carry a location. That's DEPARTURE rows with `Estimated/Actual_Landing` and `Estimated/Actual_In_Block`, and ARRIVAL rows with `Boarding_Start`, `Scheduled/Actual_Off_Block` and `Scheduled/Estimated/Actual_Take_Off`. Of those, **1,784 are SEA runway designators** (16L/16C/16R/34L/34C/34R), **1,403 are SEA gates** and 1 is the `*ASCG1S` placeholder. **Example:** departure QTA1004 KSEA→KGEG takes off at 20:19:16 from `34R`, then has `Actual_Landing` 21:00:00 at **`34R`** and `Actual_In_Block` 21:04:00 at **`Gate_N5`**. That's 41 minutes later, consistent with landing in Spokane, but tagged with SEA locations. *Note:* "happened at the other airport" is inferred from the event sequence and timing; the export doesn't record the airport per event | "About 3,200 events that happened at the origin or destination airport are labelled with SEA runways or gates (e.g. a Seattle→Spokane flight's landing is tagged runway 34R), so location-based counts must filter by operation." |
| 23 | Runway events | ✅ | Flights (call_sign + operation) with **both** `Runway_Entrance` and `Runway_Exit`: **0**. Departures: 361 with entrance, 0 with exit. Arrivals: 354 with exit, 0 with entrance. Over unambiguous flights only (the 10 duplicate keys excluded): **departures `Actual_Take_Off − Runway_Entrance` average 1.29 min** (n=355, range 0.60–3.07); **arrivals `Runway_Exit − Actual_Landing` average 0.43 min** (n=350, range 0.20–1.38). ⚠️ An average arrival runway time of about 26 seconds is short for a runway exit, so the meaning of these timestamps needs Port confirmation | "No flight has both runway entry and exit; entry exists only for departures and exit only for arrivals. Proxies: about 1.3 min (entry → wheels-up) for departures and about 0.4 min (touchdown → exit) for arrivals, pending Port confirmation of the definitions." |
| 24 | Distinct gates | ✅ | **63** distinct `Gate_*` values in `flight_event.location` | "63 distinct gates appear in the data." |
| 25 | Late share at 0/5/15/30 min | ⚠️ | Unambiguous flights only; delay = actual − planned, in minutes; "late" means delay > threshold. **Departures, take-off** (`Actual_Take_Off` vs `Scheduled_Take_Off`, Aerobahn): n=350 → >0: **90.6%**, >5: **80.3%**, >15: **55.1%**, >30: **27.1%** (min −9.2, max 760.6 min). **Departures, off-block** (`Actual_Off_Block` vs `Scheduled_Off_Block`): n=352 → 84.4% / 63.9% / 39.8% / 20.7%. **Arrivals: no scheduled in-block time exists** (only `Estimated_In_Block` from ATC and `Actual_In_Block`; `flight.schedule_arrival` is also the ATC estimate). Against the ATC estimate: n=346 → 82.4% / 56.9% / 19.4% / 3.8%. ⚠️ The very high take-off "late" share and the 12-hour maximum suggest `Scheduled_Take_Off` isn't a published schedule; confirm with the Port | "Arrival punctuality against schedule can't be measured (no scheduled in-block time). Departure lateness depends heavily on which timestamp is used; definitions must be agreed with the Port before reporting on-time numbers." |
| 26 | UNKNOWN aircraft types and nulls | ✅ | `UNKNOWN_001` (2 flights), `UNKNOWN_002` (7 flights). Nulls in `flight`: aircraft_type 0 · registration 7 · origin 3 · destination 3 · schedule_departure 5 · actual_departure 6 · schedule_arrival 9 · actual_arrival 142 · flight_origination_date 361. Nulls in `flight_event`: call_sign 0 · event_time 0 · location 8 (plus 3 `*ASCG1S` placeholders) | As listed. |

---

## Phase 3 — Source claims (`OLD Data/`, read-only)

| # | Claim | Status | Evidence | Correct wording for the proposal |
|---|---|---|---|---|
| 27a | "$10.8M" SAMS investment | ⚠️ secondary source | Only in **`Port-of-Seattle-SEA-Airfield-Data-Intelligence.pdf` p.2**, Team 6's student mid-term deck: "$12M investment realizing only 25–35% of its potential · $10.8M SAMS Investment · $1.2M Annual Hosting Cost". No Port-authored document in `OLD Data/` states it | "≈$10.8M SAMS investment (figure from the Spring 2026 team's mid-term deck; original Port source not on file)." |
| 27b | "25–35%" of value realised | ⚠️ secondary source | Same PDF, p.2 ("25-35% Value Realized"). No Port-authored source on file | Same caveat as 27a. |
| 27c | "1–2 week" BI turnaround | ✅ (student sources, consistent) | `AIport Final Presentation.pptx` slide 2 ("Gate utilization reports take 1-2 weeks") and slide 13 ("Before: 1-2 weeks"); `AIport-main/README.md` ("Manual BI reporting takes 1-2 weeks"). The Spring 2026 PDF p.2 says "3-14 Days Time Per Report" and "Report takes days to 2 weeks" | "BI reports take roughly 3 days to 2 weeks (per both earlier teams' client interviews)." |
| 27d | "~$300K/yr" | ⚠️ projection | PDF p.3: "If fully realized, our solution could unlock close to $300,000 per year". Built from Team 6's own estimates (~$12K BI effort + ~$39K leadership time + ~$240K "SAMS value utilization increase") | "Team 6 estimated up to ~$300K/yr of potential value (a projection, not a measured saving)." |
| 27e | Number of gates (80 vs 88) | ⚠️ | **"88 gates"**: `technical/Seattle SAMS Saab User Conference.pdf` p.4, a Port-authored deck: "3 runways, 88 gates, & 22M sq. ft. of concrete" (a 2021-era statistic). **"80 gates" doesn't appear** in any PDF, PPTX, DOCX or MD in `OLD Data/`. The **dataset contains 63 gate codes** (claim 24) | "SEA has 88 gates (Port SAMS presentation, 2021); our one-day sample touches 63 of them." Drop "80" unless a source is found. |
| 28 | The Port's 10 priority questions | ✅ | `technical/Gate Query User Story.docx`, headed "Final 10 Questions". Persona for all: **Leadership**. Exact wording below | Use the exact wording below. |

### Claim 28: exact wording (`Gate Query User Story.docx`, typos preserved)

1. **Taxi In Performance**: "I want to compare average taxi times by aircraft type" / "To identify which types require additional buffer time"
2. **Taxi Out Performance**: "I want to view average Taxi-out times across different hours of the day." / "To pinpoint when the surface is most congested"
3. **Movement Area Occupancy**: "I want to analyze how many aircraft were in the movement area at any given time." / "To understand peak-hour ground saturation."
4. **Runway Occupancy Time**: "I want to calculate average runway occupancy times from entry to exit. (utilize "wheels up time" from data sheet)" / "To evaluate runway throughput efficiency"
5. **Wheels-Up Delay Tracker**: "I want to compare scheduled vs actual takeoff times." / "To recognize patterns in departure punctuality"
6. **Weight Class Comparison**: "I want to compare taxi duration between light, medium, & heavy aircraft." / "Asses' operational impact of aircraft weight categories."
7. **Taxiway Utilization**: "I want to see which taxiway segments (Tango, Hotel, Whiskey) are used most frequently." / "To evaluate traffic flow patterns and hotspots"
8. **Landing - In block duration**: "Determine the average duration between wheels down time - in-block time." / "Look into taxiway congestion."
9. **Runway Utilization Rate**: "I want to see how many takeoffs and landings occurred on each runway during a specific time period." / "To identify which runway carries the most operational load."
10. **Peak Hour Prediction**: "I want the system to predict future ground congestion based on historical patterns." / "Planning resource allocations."

*Bonus (not one of the 10):* **Metal on Ground Report**: "I want to see the number of aircraft on the ground at any given time. Includes breakdown of aircraft type and weight class." / "Monitors congestion levels and airfield capacity."

---

## Claims we must change in the plan

1. **The README's quick start "works"** → ❌. It starts the older `app.py`, and the referenced files and variable names are wrong (claim 11).
2. **The Electron desktop app** → ❌ not runnable (claim 17).
3. **"91% accuracy"** → can't be reproduced; present it as Team 6's unverified figure (claim 15).
4. **Gemini support** → exists only in our uncommitted local changes, not in the inherited code (claim 16).
5. **"80 gates"** → no source found; use 88 (Port, 2021) and "63 in our sample" (claims 24, 27e).
6. **$10.8M, 25–35% and ~$300K/yr** → cite as Team 6 mid-term estimates, not Port figures (claim 27).
7. **Any on-time or punctuality statistic** → arrivals have no scheduled in-block time; departure lateness depends on the timestamp chosen (claim 25).
8. **Runway occupancy "from entry to exit"** → impossible in this data; no flight has both events (claim 23).
9. **Weight-class comparison "light, medium & heavy"** → there are no Light aircraft in the data (claim 18, Q6).
10. **Wherever "flights" are counted** → state "725 flight legs (660 distinct call signs)" (claim 21).

## Questions only the Port can answer

1. **What is `Scheduled_Take_Off`?** A published schedule, or a derived target? It makes 90% of departures "late" (claim 25).
2. **Is there a scheduled in-block time** we could get for arrival punctuality?
3. **Runway timestamps:** does the export really record only entry for departures and only exit for arrivals? What's the official runway-occupancy definition (claim 23)? Is about 26 s from touchdown to exit plausible?
4. **Locations:** does Aerobahn tag other-airport events with the SEA gate or runway by design (claim 22)?
5. **Taxiways:** how do `TaxiwaySegment_*` codes map to Tango, Hotel and Whiskey (Q7)?
6. **The 10 duplicate call signs** within the same operation: real repeat flights, or export errors (claim 21)?
7. **Source for $10.8M / 25–35%** and the current gate count (88?).
8. **More data:** can we get more than one day, so "peak-hour prediction" (Q10) is meaningful?

---

## Appendix — key SQL (SQLite dialect, run on `AIplane.sql` loaded in memory)

```sql
-- 19 counts / range
SELECT (SELECT COUNT(*) FROM flight), (SELECT COUNT(*) FROM flight_event), (SELECT COUNT(*) FROM aircraft_type);
SELECT MIN(event_time), MAX(event_time) FROM flight_event;
-- 20 airlines
SELECT rtrim(call_sign,'0123456789') AS prefix, COUNT(*) FROM flight GROUP BY 1;
-- 21 same-operation repeats
SELECT call_sign, operation, COUNT(*) FROM flight GROUP BY call_sign, operation HAVING COUNT(*) > 1;
-- 22 location trap (other-airport events that carry a location)
SELECT COUNT(*) FROM flight_event
WHERE location IS NOT NULL AND (
  (operation='DEPARTURE' AND event_type IN ('Estimated_Landing','Actual_Landing','Runway_Exit','Movement_Area_Exit','Estimated_In_Block','Actual_In_Block'))
  OR (operation='ARRIVAL' AND event_type IN ('Boarding_Start','Scheduled_Off_Block','Actual_Off_Block','Movement_Area_Entrance','Runway_Entrance','Scheduled_Take_Off','Estimated_Take_Off','Actual_Take_Off')));
-- 23 both runway events per flight
SELECT operation, SUM(has_entr), SUM(has_exit), SUM(has_entr AND has_exit)
FROM (SELECT call_sign, operation, MAX(event_type='Runway_Entrance') has_entr, MAX(event_type='Runway_Exit') has_exit
      FROM flight_event GROUP BY call_sign, operation) GROUP BY operation;
-- 23/25 use only unambiguous flights:
--   (SELECT call_sign, operation FROM flight GROUP BY call_sign, operation HAVING COUNT(*) = 1)
-- and minutes = (julianday(later) - julianday(earlier)) * 1440
-- 24 gates
SELECT COUNT(DISTINCT location) FROM flight_event WHERE location LIKE 'Gate_%';
```
