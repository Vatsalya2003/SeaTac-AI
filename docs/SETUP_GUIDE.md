# Setup Guide — run SeaTac AI on your laptop

> **Repo layout:** this copy lives in `docs/`. Code is under `src/` (`src/backend`, `src/frontend`, `src/database`, `src/electron`). Files from the team's *OLD Data* folder are not in this repo.

> A step-by-step guide to get the app running locally. It takes about 15 minutes.
> Background: [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) · How the code works: [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) · Database: [DB_SCHEMA.md](DB_SCHEMA.md)
>
> **Tested on 2026-10-01** on macOS (Apple Silicon) with MySQL 8.4.8, Python 3.12 and Node 22. The installs, the backend start and the frontend start all worked. Windows steps are written out but **⚠️ not tested yet**; if you're on Windows, please fix anything that's wrong.

---

## What you'll end up with

```
Browser  http://localhost:3000   ← React frontend   (src/frontend/, npm run dev)
            │
            ▼
API      http://localhost:8000   ← Python backend   (src/backend/app_optimized.py)
            │            │
            ▼            ▼
MySQL "AIplane"      Claude API (Anthropic, needs a key)
```

**You need all three pieces** (MySQL, the backend and a Claude key) for questions to work. With only the frontend running, you can log in, but every question will fail.

---

## Step 0: Install the tools (one time)

| Tool | Version | macOS | Windows |
|---|---|---|---|
| **Git** | any | `xcode-select --install` | https://git-scm.com |
| **MySQL Server** | **8.0 or newer** (not MariaDB) | https://dev.mysql.com/downloads/mysql/ (installer) or `brew install mysql` | MySQL Installer from the same page. Choose "Server only" and remember the root password |
| **Python** | **3.11 or 3.12** | `brew install python@3.12` | https://python.org, and tick "Add to PATH" |
| **Node.js** | 18 or newer (22 tested) | `brew install node` | https://nodejs.org (LTS) |
| **Claude API key** | — | Get one at https://console.anthropic.com, or ask the team lead for the team key | same |

> ⚠️ **Avoid Python 3.13 or 3.14.** The backend pins older packages (`pydantic 2.6.0`, `fastapi 0.109.0`) that may not install on the newest Python. Check with `python3 --version`. If it's too new, use `python3.12` explicitly in Step 3.

---

## Step 1: Get the code

```bash
git clone https://github.com/Vatsalya2003/SeaTac-AI.git
cd SeaTac-AI
```

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

**Create `src/backend/.env`.** There's no template in the repo, so create the file with exactly these lines:

```env
CLAUDE_API_KEY=sk-ant-...your key...
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your MySQL root password
DB_NAME=AIplane
```

> 💡 **No Claude credit? You can use a Gemini key instead**, once the Gemini switch is committed. Add `LLM_PROVIDER=gemini` and `GEMINI_API_KEY=...` (from aistudio.google.com) to `.env`. Details are in [DEVELOPER_GUIDE.md §2.3](DEVELOPER_GUIDE.md#23-backend-environment-variables-full-reference).
>
> 💳 **Claude needs API credit**, which is separate from any Claude.ai or Claude Code subscription. The key must also be created *inside a workspace* (Console → Settings → Workspaces → API Keys). Otherwise you get "credit balance is too low" or "not scoped to a workspace" errors.

> 🔒 **Never commit `.env`.** It contains your API key. ⚠️ The original repo had **no `.gitignore`** at all. One was added on 2026-10-01; until it's committed and you've pulled it, `.env`, `venv/` and `node_modules/` aren't protected. Before every commit, run `git status` and make sure `.env` isn't listed.

**Start the backend** (keep this terminal open):

```bash
uvicorn app_optimized:app --reload --port 8000
```

**Check it:** open http://localhost:8000/api/health. You want both of these:

```json
"claude_enabled": true,  "database_status": "online"
```

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

Each question makes **2 paid Claude API calls** (one to write the SQL, one to summarise the result).

Some questions give wrong answers or no data because of known bugs. **Avoid these for now:**
- Questions starting with "Can you…", "Explain…" or "Help…" are treated as small talk and return no data.
- Questions with numbers ("top 10…") can get a wrong hour filter.
- Runway, taxiway and peak-hour questions are often wrong.

Details are in [DEVELOPER_GUIDE.md §6](DEVELOPER_GUIDE.md#6-known-issues).

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
| `/api/health` shows `"database_status": "offline"` | MySQL not running, wrong `DB_PASSWORD`, or `DB_NAME` isn't exactly `AIplane` |
| Every question returns **HTTP 503** "No SQL generator configured" | `CLAUDE_API_KEY` is missing from `src/backend/.env`. Add it and restart the backend |
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
- `QUICK_START.md`, `MODAL_API_KEY`, `GEMINI_API_KEY`: these don't exist or aren't used.
