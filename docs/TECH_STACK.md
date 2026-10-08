# Tech Stack

> **Repo layout:** this copy lives in `docs/`. Code is under `src/` (`src/backend`, `src/frontend`, `src/database`, `src/electron`). Files from the team's *OLD Data* folder are not in this repo.

> Every technology in the current repo, layer by layer: its version, where it's used, and **why it was chosen** (with a source) or "❓ No documented reason found".
> Related docs: [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) · [DB_SCHEMA.md](DB_SCHEMA.md) · [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) · [SETUP_GUIDE.md](SETUP_GUIDE.md) (run it locally)
>
> The tables in §1–6 describe the repo **as inherited** at commit `111fd5a`. A `^` means "this version or a newer compatible one". For what actually runs today, see the next section.

---

## Current local build (Team 3, verified 2026-10-05)

These are the versions installed and running on our machine, including our uncommitted changes.

| Layer | What we run | Version |
|---|---|---|
| Frontend | React + TypeScript + Vite, Chart.js, react-markdown | React 18.3.1 · TypeScript 5.9.3 · Vite 6.4.3 · Chart.js 4.5.1 · react-markdown 10.1.0 · Node 22 |
| Backend | Python + FastAPI + Uvicorn + Pydantic | Python 3.12 · FastAPI 0.109.0 · Uvicorn 0.27.0 · Pydantic 2.13.5 |
| Database | MySQL (driver: mysql-connector-python) | MySQL 8.4.8 · connector 8.2.0 |
| AI, active | **Google Gemini** via `google-genai` (`LLM_PROVIDER=gemini`) | `gemini-2.5-flash` · google-genai 2.27 |
| AI, available | Anthropic Claude via `anthropic` (set `LLM_PROVIDER=claude`; needs API credit) | `claude-sonnet-4-20250514` (deprecated model; see §4) · anthropic 0.125.0 |
| AI, off | Fine-tuned CodeLlama-7B on Modal | not used |

**Changes from the inherited repo** (all uncommitted):
- **Gemini option added.** There's a `GeminiClient` adapter in `app_optimized.py` and `google-genai>=2.0` in `requirements.txt`. Claude stays the default.
- **`anthropic>=0.21.0,<1`:** version 1.x removed the `temperature` argument the code passes, so every Claude call failed silently.
- **`pydantic>=2.12.5,<3`** (was `==2.6.0`): `google-genai` requires 2.12.5+. With the old pin, a fresh `pip install -r requirements.txt` fails. FastAPI 0.109 works with 2.13 (tested end to end).
- **`.gitignore` added**, so `.env`, `venv/` and `node_modules/` aren't committed.

---

## Overview diagram

```
 Browser (React app)  ──HTTP POST /api/query──►  FastAPI backend  ──SQL──►  MySQL "AIplane"
   frontend/                                     backend/app_optimized.py      database/data/AIplane.sql
        ▲                                               │
        └──────── JSON: answer + chart + table ─────────┤──► Anthropic Claude API (writes SQL, writes summary)
                                                        │
                                                        └╌╌► Modal: fine-tuned CodeLlama-7B (code present, switched OFF)
```

How a request moves through this is explained step by step in [DEVELOPER_GUIDE.md → How a question flows](DEVELOPER_GUIDE.md#3-how-a-question-flows-through-the-system-end-to-end).

---

## 1. Frontend (`frontend/`)

| Technology | Version | Where / what for | Why chosen |
|---|---|---|---|
| **React** | `^18.3.1` | The whole UI ([`src/App.tsx`](../src/frontend/src/App.tsx)) | "Simple agent web chat look and UI for simplicity and familiarity" (Spring 2026 mid-term PDF, p.6). The reason React specifically was picked over alternatives isn't recorded |
| **TypeScript** | `^5.3.3` | All source files | ❓ No documented reason found |
| **Vite** | `^6.3.5`, plugin `@vitejs/plugin-react-swc ^3.10.2` | Dev server (port **3000**) and build (output folder `build/`), set in [`vite.config.ts`](../src/frontend/vite.config.ts) | ❓ No documented reason found |
| **shadcn/ui + Radix UI** | Radix packages `^1.x`–`^2.x`; 48 files in `src/components/ui/` | Buttons, cards, inputs, scroll areas and so on | The UI was generated with **Figma Make**: [`src/Attributions.md`](../src/frontend/src/Attributions.md) says "This Figma Make file includes components from shadcn/ui". That also explains the odd version-suffixed import aliases in `vite.config.ts` (e.g. `'sonner@2.0.3'`) |
| **Tailwind CSS** | ⚠️ Precompiled **v4.1.3** CSS; `tailwindcss ^3.4.0` listed but not wired up | Styling via utility classes. [`src/index.css`](../src/frontend/src/index.css) is a 35 KB *pre-built* Tailwind output file | Came with the Figma Make export. ⚠️ **Gotcha:** there's no `tailwind.config` or `postcss.config` in the repo, so Tailwind doesn't run at build time. **A class not already in `index.css` won't work** (we haven't tested this in a browser) |
| **Chart.js** | `^4.5.1` | Charts, drawn directly with `new ChartJS(...)` in [`ChartVisualization.tsx`](../src/frontend/src/components/ChartVisualization.tsx), plus PNG export | ❓ No documented reason found. The backend returns chart configs in Chart.js format |
| **react-markdown + remark-gfm** | `^10.1.0`, `^4.0.1` | Renders the assistant's text as Markdown ([`ChatMessage.tsx`](../src/frontend/src/components/ChatMessage.tsx)) | ❓ No documented reason found |
| **lucide-react** | `^0.487.0` | Icons | Came with the Figma Make/shadcn template |
| **serve** | `^14.2.0` | `npm run serve` serves the built app on `$PORT` (used for the Railway deployment) | ❓ No documented reason found |
| Browser `localStorage` | — | Stores chat history (key `aiport_chat_threads_v7_0_fixed`) and the "logged-in" user (`aiport_user`) | ❓ No documented reason found. Chats never leave the browser |

**Listed in `package.json` but not used by our code:** `react-chartjs-2`, `recharts` (only in the unused shadcn `ui/chart.tsx`), `highlight.js`, `rehype-highlight`, `react-hook-form`, `embla-carousel-react`, `cmdk`, `vaul`, `input-otp`, `react-day-picker` and others. These are leftovers from the template.

**Other mismatches:** `@types/react ^19` is used with React 18; unlikely to matter, but noted. The frontend reads the backend address from **`VITE_API_URL`** ([`src/api/query.ts`](../src/frontend/src/api/query.ts)), while [`frontend/README.md`](../src/frontend/README.md) says `VITE_API_BASE_URL`. The code wins.

---

## 2. Backend (`backend/`)

The **live** server is [`backend/app_optimized.py`](../src/backend/app_optimized.py) (v8.0), started by [`Procfile`](../src/backend/Procfile) and [`railway.json`](../src/backend/railway.json). [`backend/app.py`](../src/backend/app.py) (v7.4) is an older version that uses the Modal model plus the Claude checker. Why there are two files is covered in [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md#two-backend-files-which-one-is-real).

From [`backend/requirements.txt`](../src/backend/requirements.txt):

| Technology | Version | What for | Why chosen |
|---|---|---|---|
| **Python** | ⚠️ 3.11 suggested | Language | [`setup.sh`](../src/backend/setup.sh) asks for 3.11+, and the Modal images use 3.11. The README says 3.8+ (probably stale) |
| **FastAPI** | `0.109.0` | HTTP API: `/`, `/api/query`, `/api/health`, plus automatic docs at `/docs` | "Introduced Pydantic type validation and enhanced request modeling, improving LLM integration reliability" (mid-term PDF p.10; also p.6). It replaced Fall 2025's Flask |
| **Uvicorn** | `0.27.0` (`[standard]`) | The server process that runs FastAPI | Standard choice for FastAPI. ❓ No specific reason documented |
| **Pydantic** | `2.6.0` (we changed it to `>=2.12.5,<3`; see the current-build section above) | Request and response models (`QueryRequest`, `QueryResponse`, `HealthResponse`) | Same reason as FastAPI (mid-term p.10) |
| **mysql-connector-python** | `8.2.0` | Database access (`DatabaseManager`) | ❓ No documented reason found (carried over from Fall 2025) |
| **anthropic** (Claude SDK) | `>=0.21.0` (no upper limit; we pinned it to `<1`, see the current-build section above) | Every LLM call (see §4) | See §4 |
| **python-dotenv** | `1.0.0` | Loads `backend/.env` | — |
| **requests** / **httpx** | `2.31.0` / `>=0.25.0` | `requests` calls the Modal endpoint (code switched off). `httpx` is needed by the anthropic SDK | Commit `57d0f1a`: "Updated anthropic and httpx package versions". ❓ No reason stated |

**Used in the repo but NOT in `requirements.txt`** (install them separately if you need these scripts):
- `pandas`, `openpyxl`, `pymysql`: used by [`database/scripts/db_manager.py`](../src/database/scripts/db_manager.py) (see [`database/INSTALL.md`](../src/database/INSTALL.md)).
- `modal`, `groq`, `jsonlines`: used by the fine-tuning and training-data scripts. They were in the Mar 11 `requirements.txt` (commit `ffcd4e8`) and later dropped.

**Removed since the Spring 2026 mid-term:** LangChain (`langchain==1.2.10`) and Google Gemini (`google-genai`, `langchain-google-genai`) were in the first FastAPI version (commit `ffcd4e8`, Mar 11) and are gone now. Dropping LangChain agents is explained: "Due to Langchain v1.2.10 compatibility issues, current approach is manual orchestration" (mid-term p.6, p.8).

---

## 3. Database

| Technology | Version | What for | Why chosen |
|---|---|---|---|
| **MySQL** | 8.0+ required; the dump came from **9.5.0** | Stores the 3 tables; see [DB_SCHEMA.md](DB_SCHEMA.md) | ❓ No documented reason found. The Fall 2025 deck just says "we used MySQL" (slide 8 notes), and the Fall 2025 architecture diagram (`technicalarch.drawio` (team's `OLD Data/technical/technicalarch.drawio`; not in this repo)) lists it without a reason. The final deck claims the design "supports any standard SQL database" (slide 11 notes); ⚠️ the SQL is MySQL-specific (`TIMESTAMPDIFF`, `HOUR()`), so that's optimistic |
| **Hosted database for Railway** | ⚠️ Unknown | The deployed backend reads `DB_HOST`/`DB_USER`/`DB_PASSWORD`/`DB_NAME`/`DB_PORT` from the environment | Where the production database lives isn't recorded anywhere in the repo. Ask Team 6 (Abhishek) |

---

## 4. AI / model layer

### What is live: Anthropic Claude (direct)

| Item | Value | Source |
|---|---|---|
| SDK | `anthropic >=0.21.0` | `requirements.txt` |
| Default model (live server) | `claude-sonnet-4-20250514`, overridable with the `CLAUDE_MODEL` env var | [`app_optimized.py:59`](../src/backend/app_optimized.py) |
| Default model (older `app.py`) | `claude-3-5-sonnet-20240620` | [`app.py:53`](../src/backend/app.py) |
| Model named in the README | "Claude 4.5 Haiku validation" | [`README.md`](../README.md). ⚠️ Doesn't match either code default; Railway may set `CLAUDE_MODEL`, which we can't see |
| What Claude does in the live server | (1) writes SQL (temperature 0.1), (2) replies to greetings and small talk (temperature 0.7), (3) writes a 2–3 sentence "insight" from the **first 3 result rows** (temperature 0.4) | `DirectClaudeSQLGenerator`, `GreetingHandler`, `SeaTacAgent._generate_insights` |

**Why Claude?**
- v7.4 (Apr 13): Claude was brought in as the "big brother" SQL checker. It "replaces OpenRouter" for its "superior validation and correction capabilities" ([`app.py`](../src/backend/app.py) header docstring).
- v8.0 (May 4): Claude now writes the SQL itself, for speed: "Single API call instead of Modal → Claude validation … ~2-3 seconds faster per query", explicitly for "PRESENTATION MODE" ([`app_optimized.py`](../src/backend/app_optimized.py) header).
- ❓ No documented cost analysis or budget approval for using a paid API. Fall 2025 chose Gemini *because* the API budget was $0 (final deck, slide 6).

⚠️ Model IDs get retired over time. Check that the configured `CLAUDE_MODEL` is still available before relying on the defaults.

### Present but switched off: fine-tuned CodeLlama-7B on Modal

| Item | Value | Source |
|---|---|---|
| Base model | `codellama/CodeLlama-7b-Instruct-hf` | [`modal_finetune.py`](../src/backend/modal_finetune.py) |
| Method | LoRA (r=16, alpha=32), 8-bit loading, 3 epochs, learning rate 2e-4, effective batch size 16, on an A10G GPU | same file |
| Libraries (inside the Modal image) | torch 2.1.2, transformers 4.36.0, peft 0.7.1, bitsandbytes 0.41.3, trl 0.7.10, datasets 2.16.0, accelerate 0.25.0 | same file |
| Serving | Modal web endpoint on a T4 GPU, 15-minute scale-down, model stored in the Modal volume `seatac-models` | [`modal_serve.py`](../src/backend/modal_serve.py) |
| Status | **Off.** `USE_MODAL = False` and a stub class in `app_optimized.py`. Only `app.py` can call it, via the `MODAL_ENDPOINT` env var | `app_optimized.py:64`, `:479` |

**Why fine-tune at all:** Gemini's free tier hit its limit ("20 requests/day"), and the team concluded "free tiers are not viable for development" (mid-term p.8).
**Why CodeLlama-7B instead of the Gemma 2-2B described at mid-term:** ❓ No documented reason found. Gemma doesn't appear anywhere in the repo.
**Why the docstring still says `modal_codellama_finetune.py`:** the file was renamed to `modal_finetune.py` but its setup instructions weren't updated.

### Training data

| File | Contents |
|---|---|
| [`generate_training_data.py`](../src/backend/generate_training_data.py) | Uses **Groq** (`llama-3.3-70b-versatile`, temperature 0.8) to write about 50 paraphrases of each of the **11 use cases** |
| `seatac_training_data.json`, `seatac_llama_training.json`, `seatac_gemini_training.jsonl`, `seatac_openai_training.jsonl` | The same **507 examples** in four formats |

⚠️ **Important limitations** of the fine-tuning setup. All were checked by reading `generate_training_data.py`, `modal_finetune.py` and `modal_serve.py` in full.

1. **Only 11 distinct answers.** The 507 examples contain only **11 distinct SQL answers**, one per use case. The model learned "which of 11 templates does this question mean?", not general SQL writing, so it will probably do poorly on anything else.
2. **Several of the "correct answers" are wrong** (the `USE_CASES` dict in `generate_training_data.py`):
   - **Use case 4 (runway occupancy) returns hard-coded numbers.** It reports `1.5` minutes for takeoffs and `1.2` for landings instead of calculating anything from the data.
   - **Use cases 9 (runway utilisation) and 10 (peak hour) fall into the location trap.** They count every `Actual_Take_Off`/`Actual_Landing` by location with no operation filter, so events at other airports are counted on SEA runways ([DB_SCHEMA.md issue 3](DB_SCHEMA.md#known-schema-issues)). Use case 10 does no prediction.
   - **Use cases 5, 6 and 11 join on `call_sign` without matching `operation`.** That mixes in the other leg's events, e.g. taxi-in at the destination airport for departures.
   - **Use case 7 (taxiway) only counts departures.** Arrivals' taxiway events are `Movement_Area_Exit`, which it leaves out.
   - **Use case 3 (movement area) counts distinct flights per hour**, which isn't true occupancy (how many aircraft are on the taxiways at the same moment).
3. **Training and serving use different prompts.**
   - Training used `[INST] {question} [/INST] {sql}`, with no schema; the `input` field is ignored.
   - Serving wraps the question in a long schema-and-examples prompt and pre-fills `SELECT`.
   - The model is also trained in **8-bit** but served in **4-bit**.
   - ⚠️ This probably explains why its output needed heavy clean-up code and a Claude "big brother" to correct it. That's our inference; it isn't documented.
4. **No validation split, and the loss counts padding.** Every example is padded to 1,024 tokens, and the loss is computed over the whole sequence, including padding and the question. So training loss says little about SQL quality.

Revive this path only after fixing the templates (2) and the prompt mismatch (3).

### Previously used, now gone

| Technology | When | Source |
|---|---|---|
| Google Gemini (2.5-flash / 2.0-flash / 2.5-pro) | Fall 2025, and Spring until about Mar 13 | Fall 2025 code; commit `ffcd4e8` |
| OpenRouter (as the SQL checker) | Mar 13 – Apr 13, 2026 | commits `f2dbd2c`, `eb0c669` |
| LangChain | Until about Mar 13, 2026 | commit `ffcd4e8`; mid-term p.6 |
| Gemma 2-2B fine-tune | Around Feb 2026 (mid-term only) | mid-term p.8. Not in the repo |

---

## 5. Desktop app (Electron): present but not runnable

| Item | Status |
|---|---|
| [`electron/main.js`](../src/electron/main.js) | Byte-for-byte identical to the Fall 2025 version |
| Root `package.json` with Electron dependencies | **Missing from this repo** (Fall 2025 had `electron ^28.0.0`, `electron-builder ^24.9.1`). So `npm run dev` at the root, as the README describes, can't work |
| Why Electron | ❓ No documented reason found. It appears in the Fall 2025 plan (`technicalarch.drawio` (team's `OLD Data/technical/technicalarch.drawio`; not in this repo)) with no stated reason. The Spring mid-term (p.11) says "Full stack running: Electron + React + FastAPI + MySQL", but ⚠️ that can't be reproduced from this repo |

---

## 6. Deployment and infrastructure

| Technology | What for | Why chosen |
|---|---|---|
| **Railway** (Nixpacks builder) | Hosts the backend: `uvicorn app_optimized:app --host 0.0.0.0 --port $PORT`, restart on failure up to 10 times ([`railway.json`](../src/backend/railway.json)). ⚠️ The frontend is probably also on Railway (the `serve` script, and the README's `*.up.railway.app` link) | ❓ No documented reason found |
| **Modal** | GPU fine-tuning and serving for CodeLlama (switched off) | Cheap GPU time: "Cost: $0.35 (Modal free credits)" (mid-term p.8) |
| **PyInstaller** spec ([`backend/app.spec`](../src/backend/app.spec)) | Stale. It's the Fall 2025 file and still references `google.generativeai` | — |
| CI/CD, tests, linting | **None** in the repo | — |
