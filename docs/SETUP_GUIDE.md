# Setup Guide — run SeaTac AI on your laptop

> **Repo layout:** this copy lives in `docs/`. Code is under `src/` (`src/backend`, `src/frontend`, `src/database`, `src/electron`). Files from the team's *OLD Data* folder are not in this repo.

> A step-by-step guide to get the app running locally. It takes about 15 minutes.
> Background: [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) · How the code works: [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) · Database: [DB_SCHEMA.md](DB_SCHEMA.md)
>
> **Tested on 2026-10-01** on macOS (Apple Silicon) with MySQL 8.4.8, Python 3.12 and Node 22. The installs, the backend start and the frontend start all worked. **Baseline steps (Step 7) checked on 2026-10-20**: `build_aiplane_v2.py` output (1,061 flights, 11,975 events), the backend with Gemini (`gemini-2.5-flash`) connected to `AIplane_v2` (`/api/health` online), and the frontend loading. Windows steps are written out but **⚠️ not tested yet**; if you're on Windows, please fix anything that's wrong.

---

## What you'll end up with

```
Browser  http://localhost:3000   ← React frontend   (src/frontend/, npm run dev)
            │
            ▼
API      http://localhost:8000   ← Python backend   (src/backend/app_optimized.py)
            │            │
            ▼            ▼
MySQL "AIplane"      Claude or Gemini API (needs a key)
```

**You need all three pieces** (MySQL, the backend and an AI key, either Claude or Gemini) for questions to work. With only the frontend running, you can log in, but every question will fail.

---

## Step 0: Install the tools (one time)

| Tool | Version | macOS | Windows |
|---|---|---|---|
| **Git** | any | `xcode-select --install` | https://git-scm.com |
| **MySQL Server** | **8.0 or newer** (not MariaDB) | https://dev.mysql.com/downloads/mysql/ (installer) or `brew install mysql` | MySQL Installer from the same page. Choose "Server only" and remember the root password |
| **Python** | **3.11 or 3.12** | `brew install python@3.12` | https://python.org, and tick "Add to PATH" |
| **Node.js** | 18 or newer (22 tested) | `brew install node` | https://nodejs.org (LTS) |
| **AI API key** | — | **Gemini (free):** create your own key at https://aistudio.google.com (Get API key). **Claude (optional, paid):** https://console.anthropic.com, or ask the team lead for the team key | same |

> ⚠️ **Avoid Python 3.13 or 3.14.** The backend pins older packages (e.g. `fastapi 0.109.0`) that may not install on the newest Python. Check with `python3 --version`. If it's too new, use `python3.12` explicitly in Step 3.

---

## Step 1: Get the code

```bash
git clone https://github.com/Vatsalya2003/SeaTac-AI.git
cd SeaTac-AI
git checkout test_1
```

> **Use the `test_1` branch.** `main` doesn't have the new database scripts (`load_aerobahn.py`, `build_aiplane_v2.py`), the Gemini option or the baseline steps yet. Everything below assumes `test_1`.

---

## Step 2: Start MySQL and load the data

**2a. Start the MySQL server:**

| How you installed it | Start command |
|---|---|
| macOS official installer | `sudo /usr/local/mysql/support-files/mysql.server start`, or System Settings → MySQL → Start |
| macOS Homebrew | `brew services start mysql` |
| Windows | It usually starts automatically. If not, open Services → MySQL80 → Start |

Check that it's running: `mysqladmin -u root -p ping` should print `mysqld is alive`.

**2b. Load the database.** Run this from the `SeaTac-AI` folder; it works on macOS and Windows:

```bash
mysql -u root -p -e "source src/database/data/AIplane.sql"
```

**2c. Check the data loaded.** You should see **16, 725, 7995**:

```bash
mysql -u root -p -e "USE AIplane; SELECT COUNT(*) FROM aircraft_type; SELECT COUNT(*) FROM flight; SELECT COUNT(*) FROM flight_event;"
```

> 💡 *Optional but recommended:* make a read-only user so the app can't change data. The app runs whatever SQL the AI writes. The SQL for this is in [DEVELOPER_GUIDE.md §2.2](DEVELOPER_GUIDE.md#22-database).

---

## Step 3: Set up the backend

**macOS / Linux:**

```bash
cd src/backend
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

**Windows (PowerShell):**

```powershell
cd src/backend
py -3.12 -m venv venv
venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

**Create `src/backend/.env`.** There's no template in the repo, so create the file by hand. Pick **one** of these two options.

**Option A: Gemini (free; recommended for teammates and required for baseline testing)**

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=...your own key from aistudio.google.com...
GEMINI_MODEL=gemini-2.5-flash
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your MySQL root password
DB_NAME=AIplane
```

**Option B: Claude (paid)**

```env
CLAUDE_API_KEY=sk-ant-...your key...
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your MySQL root password
DB_NAME=AIplane
```

Without `LLM_PROVIDER`, the backend uses Claude. More settings are in [DEVELOPER_GUIDE.md §2.3](DEVELOPER_GUIDE.md#23-backend-environment-variables-full-reference).

> 💳 **Claude needs API credit**, which is separate from any Claude.ai or Claude Code subscription. The key must also be created *inside a workspace* (Console → Settings → Workspaces → API Keys). Otherwise you get "credit balance is too low" or "not scoped to a workspace" errors.

> 🔒 **Never commit `.env`.** It contains your API key. The repo's `.gitignore` excludes `.env`, `venv/`, `node_modules/` and the Port data files, but run `git status` before every commit and make sure none of them is listed.

**Start the backend** (keep this terminal open):

```bash
uvicorn app_optimized:app --reload --port 8000
```

**Check it:** open http://localhost:8000/api/health. With Option A (Gemini) you should see:

```json
{"status":"healthy","model":"gemini-2.5-flash","modal_enabled":false,"modal_endpoint":null,"claude_enabled":true,"database_status":"online","version":"8.0.0"}
```

- **`"database_status": "online"`** means MySQL is connected.
- **`"claude_enabled": true`** means an AI key is configured. The field has an old name: it's `true` for Gemini too.
- **`"model"`** shows the model actually in use (`gemini-2.5-flash`, or the Claude model with Option B).

The terminal also prints `🤖 LLM provider: gemini ✅` and `Model: gemini-2.5-flash` at startup. If it prints `LLM provider 'gemini': NOT CONFIGURED (missing API key) ❌`, the key is missing (see Troubleshooting).

---

## Step 4: Set up the frontend

Open a **second terminal**:

```bash
cd SeaTac-AI/src/frontend
npm install
npm run dev
```

Open **http://localhost:3000** and log in with one of the demo accounts (ask the team lead; they're defined in `src/frontend/src/App.tsx`). There's no real login.

---

## Step 5: Try it

Good first questions (the most reliable ones):
- `Compare taxi-in times by aircraft type`
- `Show taxi-out times by hour`

Each question makes **2 AI calls** (one to write the SQL, one to summarise the result). That's free with Gemini, within its limits, and paid with Claude.

Some questions give wrong answers or no data because of known bugs. For everyday use, **avoid these for now:**
- Questions starting with "Can you…", "Explain…" or "Help…" are treated as small talk and return no data.
- Questions with numbers ("top 10…") can get a wrong hour filter.
- Runway, taxiway and peak-hour questions are often wrong.

Details are in [DEVELOPER_GUIDE.md §6](DEVELOPER_GUIDE.md#6-known-issues).

> 🧪 **Baseline testing is different:** type the test spreadsheet's questions **exactly as written**, including the "Can you…" and number questions. Those failures are what we're measuring, so don't rephrase around them. See [Step 7](#step-7-baseline-testing-old-chatbot-on-the-new-data).

---

## Step 6 (optional): Load the Port's new data (`seatac`)

The Port's updated export is used for the new metric views. **The chatbot doesn't use it yet**, so skip this step if you only want to run the app.

**6a. Get the file privately.** Ask the team lead for `August_8_and_9_2025_Anonymized.xlsx` (shared through the team's private drive, never GitHub, Slack channels or email to outsiders). It contains real aircraft tail numbers and transponder codes.
- Save it **outside** the repo, or in the repo root, where `.gitignore` blocks `*Anonymized*.xlsx`.
- Never commit it, and never commit a database dump made from it.

**6b. Install the data-script packages** (a separate venv from the backend's):

```bash
cd SeaTac-AI/src/database
python3.12 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**6c. Load it** (MySQL must be running; the script uses the `DB_*` settings in `src/backend/.env`):

```bash
cd scripts
python load_aerobahn.py --file /path/to/August_8_and_9_2025_Anonymized.xlsx
# or: export SEATAC_DATA_FILE=/path/to/...xlsx && python load_aerobahn.py
```

It drops and rebuilds the `seatac` database every time (it never touches `AIplane`). It takes under a minute and ends with `Loaded into seatac: raw_flight_details 1061, flights 1061, aircraft_types 16`.

**6d. Verify:**

```bash
python check_seatac.py
```

You should see 1,061 legs (525 arrivals, 535 departures, 1 missed approach), `duplicate (flight_info_id, operation) pairs = 0`, every `sea_date` = 2025-08-08, and every view in `metric_rules.yaml` marked `exists`. The script prints counts and exclusions only, never metric averages. The full expected output is in [DB_SCHEMA.md → check results](DB_SCHEMA.md#check-results-2026-10-21-check_seatacpy).

**Baseline database:** `build_aiplane_v2.py` builds `AIplane_v2`, the new data in Team 6's old table layout, for testing the unchanged chatbot (see Step 7).

| Problem | Fix |
|---|---|
| `give --file or set SEATAC_DATA_FILE` | Pass the file path |
| `Missing expected columns: [...]` | It's a different export version; tell the team before changing the loader |
| `No space left on device` | Free disk space; MySQL needs room to create the database |
| `Access denied` | Check `DB_USER` / `DB_PASSWORD` in `src/backend/.env` |

---

## Step 7: Baseline testing (old chatbot on the new data)

We test the **unchanged** chatbot on the Port's new data to get our "before" score.

1. Complete Steps 1–6 on the `test_1` branch (6a and 6b are enough; you don't need `seatac`).
2. Build the baseline database (in the `src/database` venv):
   ```bash
   cd SeaTac-AI/src/database/scripts
   python build_aiplane_v2.py --file /path/to/August_8_and_9_2025_Anonymized.xlsx
   ```
   It should report **1,061 flights and 11,975 events**, printed as:
   ```
   Built `AIplane_v2` in Team 6's layout from August_8_and_9_2025_Anonymized.xlsx
     aircraft_type 18 | flight 1061 | flight_event 11975
   ```
   (The next lines report 3 `UNKNOWN_###` aircraft types covering 238 flights; that's expected.)
3. In `src/backend/.env`, set `DB_NAME=AIplane_v2`, `LLM_PROVIDER=gemini`,
   `GEMINI_API_KEY=` (your own free key) and `GEMINI_MODEL=gemini-2.5-flash`.
   Everyone must use the same model so results are comparable.
4. Start the backend and save its output (it shows the SQL for each question):
   ```bash
   cd SeaTac-AI/src/backend && source venv/bin/activate
   mkdir -p logs && PYTHONUNBUFFERED=1 uvicorn app_optimized:app --port 8000 2>&1 | tee logs/baseline_backend.log
   ```
   `PYTHONUNBUFFERED=1` is required: without it, Python holds the printed SQL in a buffer when output goes through `tee`, so it reaches the log late, or is lost when you stop the server. Check `/api/health` shows `"model":"gemini-2.5-flash"` and `"database_status":"online"`.
   Windows (PowerShell): `$env:PYTHONUNBUFFERED=1; uvicorn app_optimized:app --port 8000 2>&1 | Tee-Object logs\baseline_backend.log`
5. Start the frontend (Step 4) and type each question **exactly** as written in the test
   spreadsheet. Don't avoid the known-bug questions; they're part of the test.
6. Don't change any code, and never commit `.env` or `logs/`. The `logs/` folder is already git-ignored.

**Reading the log:** each question appears after `📥 Query:`, and the SQL it ran after `📋 EXECUTING SQL`. If you see `FALLBACK: Pre-built SQL` or `SQL generation error`, the AI call failed (often a Gemini "high demand" 503) and a fallback answered instead. Note it, and ask the question again.

```bash
grep -nE "📥 Query|EXECUTING SQL|FALLBACK|SQL generation error|Success:|FAILED" logs/baseline_backend.log
```

To go back to the old data afterwards, set `DB_NAME=AIplane` and restart the backend.

---

## Every day after the first setup

```bash
# Terminal 1: MySQL must be running (see Step 2a), then:
cd SeaTac-AI/src/backend && source venv/bin/activate      # Windows: venv\Scripts\Activate.ps1
uvicorn app_optimized:app --reload --port 8000

# Terminal 2
cd SeaTac-AI/src/frontend && npm run dev
```

Stop either server with **Ctrl + C**.

> If you edit `src/backend/.env`, **restart the backend**. `--reload` only watches `.py` files, not `.env`.

---

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| `Can't connect to local MySQL server through socket` | MySQL isn't running. Go back to Step 2a |
| `Permission denied` when starting MySQL on macOS | You need `sudo` for the official installer's server (Step 2a) |
| `/api/health` shows `"database_status": "offline"` | MySQL not running, wrong `DB_PASSWORD`, or `DB_NAME` isn't exactly `AIplane` (or `AIplane_v2` for baseline testing) |
| Every question shows `HTTP 500: {"detail":"Error: 503: No SQL generator configured"}` (Claude) | `CLAUDE_API_KEY` is missing from `src/backend/.env`. Add it and restart the backend |
| Same `HTTP 500 … No SQL generator configured` message with Gemini; the startup log says `LLM provider 'gemini': NOT CONFIGURED (missing API key) ❌`, and `/api/health` shows `"claude_enabled": false` | `GEMINI_API_KEY` is missing (or empty) while `LLM_PROVIDER=gemini`. Add your key and restart the backend |
| Backend won't start: `ModuleNotFoundError: No module named 'google'` | The Gemini package isn't installed. Run `pip install -r requirements.txt` in the `src/backend` venv (you need the `test_1` version of the file) |
| Answers look random (`Found 10 results.`) and the log shows `SQL generation error` | The AI call failed: a wrong or expired key, a Gemini "high demand" 503, or the free-tier limit. Check the log line, wait, and ask again |
| Questions return an authentication error | The Claude key is wrong or expired, or it's still a placeholder |
| `pip install` fails building `pydantic-core` | Your Python is too new. Recreate the venv with Python 3.12 (Step 3) |
| Frontend says "Cannot connect to backend at http://localhost:8000" | The backend isn't running, or it's on a different port. To point elsewhere, create `src/frontend/.env` with `VITE_API_URL=http://localhost:PORT` (note: `VITE_API_URL`, not `VITE_API_BASE_URL`) and restart `npm run dev` |
| `Address already in use` on port 8000 or 3000 | Another copy is running. macOS: `lsof -i :8000`, then `kill <PID>`. Windows: `netstat -ano \| findstr :8000`, then `taskkill /PID <PID> /F` |
| `Unknown database 'AIplane'` | Step 2b didn't run, or failed. Run it again from the `SeaTac-AI` folder |
| `Unknown collation: utf8mb4_0900_ai_ci` | You're on MariaDB or MySQL 5.x. Install MySQL 8+ |

## Things that look like setup steps but aren't

The project's own `README.md` mentions these. **Ignore them**:
- `cp .env.example .env`: the file doesn't exist. Create `.env` by hand (Step 3).
- `npm install` / `npm run dev` **in the root folder**: there's no root `package.json`. The Electron desktop app can't run yet.
- `QUICK_START.md`, `MODAL_API_KEY`: these don't exist or aren't used.
