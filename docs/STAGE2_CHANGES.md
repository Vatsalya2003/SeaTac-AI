# Stage 2 (templates mode): what changed, why, and what's next

> Branch `stage2-templates` (from `backend-views`). Built and tested 2026-11-13/14 on Windows 10.
> How to run it: [SETUP_GUIDE.md, Step 8](SETUP_GUIDE.md#step-8-templates-mode-stage-2-tested-answers-for-the-ports-10-questions). How the code works: [DEVELOPER_GUIDE.md §3](DEVELOPER_GUIDE.md#the-templates-mode-path-query_modetemplates-stage-2).

## 1. In one minute

**The problem.** In Stage 1 (views mode), the AI wrote new SQL for every question. The same question could get different SQL on different days, so the answers were sometimes wrong, and every answer cost 2 AI calls.

**What Stage 2 does.** A new mode, `QUERY_MODE=templates`:

1. The AI only decides **which of the Port's 10 questions** was asked. It replies with JSON: `{"question": "Q1".."Q10" or "other", "date": ...}`. It never writes SQL.
2. Our code runs a **pre-written, tested query** for that question as the read-only user `seatac_reader`.
3. The answer text is written in code, from the full result.

**The result.**
- All **10 answers match `TEN_GROUND_TRUTH_ANSWERS.md`**, except for 2 rules the team changed on purpose for Q7 and Q10 (§4). This holds both in the tests and when asked live in the chatbot.
- The same question always gives the same SQL and the same answer.
- Each question uses at most 1 AI call. If Gemini is down or over its limit, a keyword match picks the question instead.
- Questions outside the 10 still work: they fall back to Stage 1 (views mode).
- **174 backend tests pass.** Legacy mode and views mode are unchanged.

## 2. What changed, file by file

| File | New or changed | What it does | Why |
|---|---|---|---|
| `src/backend/templates.py` | New | The tested SQL for Q1–Q10 and the code that writes each answer: a headline sentence, a table, the sample size, the Port's definition and notes | The fixed SQL makes answers repeatable and checkable against the ground truth |
| `src/backend/intent.py` | New | One AI call picks Q1–Q10 or "other". Every field of the JSON reply is validated, and anything invalid returns `None`. Uses a keyword match if the AI call fails | The AI does the part it's good at (understanding the question), not the part it gets wrong (SQL) |
| `src/backend/app_optimized.py` | Changed (guarded) | Accepts `QUERY_MODE=templates`; adds `_process_template_query` and `_template_fallback`; the response gets 4 new optional fields: `metric`, `definition`, `included_count`, `excluded` | Wiring. Every change sits behind `if TEMPLATES_MODE`, so legacy and views behave exactly as before |
| `src/backend/tests/test_templates.py` | New | 62 tests: every ground-truth number, determinism, parameters, invalid intents, other dates, answer layout, intent parsing, keyword routing for all 20 ground-truth phrasings, fallback | Proves the answers are right without calling the AI (fake intent clients) |
| `src/database/sql/question_queries.sql` | New | The same 10 queries as plain SQL, with the expected numbers in comments, to run in MySQL Workbench: select seatac as the default schema first (the file has no USE line) | So anyone can check or reuse the queries by hand |
| `src/backend/.env.example` | New | `.env` template with blank secrets | New teammates had no template; real keys must never be shared |
| `docs/SETUP_GUIDE.md`, `docs/DEVELOPER_GUIDE.md` | Changed | Step 8 (templates mode), the Windows fixes, troubleshooting, the test list, the templates-mode flow | The Stage 2 guide asks for it (step 6) |
| `docs/STAGE2_CHANGES.md` | New | This file | So the whole group knows what changed |

### How an answer looks

The answer follows the same layout as views mode, so the frontend needed no change:

```
**Answer:** Average time from wheels down to parking: **12.20 minutes**, one overall average across 525 arrivals.
**Answer** (N rows): <table>                       (when there is a table)
**Sample:** based on 525 of 525 arrivals (none excluded).
**Definition (taxi in):** Taxi-in time is the time from wheels down ... in minutes.
_Note: ..._                                         (Port caveats, for example PENDING PORT CONFIRMATION)
_Times are SEA local (PDT). Averages are rounded to 2 decimals._
```

Averages are calculated at full precision in SQL and rounded half-up to 2 decimals only in the text. An empty average shows **"No data"**, never 0.

## 3. The 10 answers

Q1–Q6, Q8 and Q9 match the ground truth exactly. Q7 and Q10 follow the team rules in §4.

| Q | Question | Main result |
|---|---|---|
| Q1 | Taxi-in by aircraft type | 16 groups, 525 arrivals: B738 14.53 min (81), B737 14.20 (9), A359 7.29 (3), Unknown 99.00 (1) |
| Q2 | Taxi-out by hour | 15.66 min overall (528). Longest 12:00 = 22.26. 03:00 and 04:00 "No data" |
| Q3 | Movement area, most aircraft at once | 10:00 = 22, 12:00 = 20, 22:00 = 19, 03:00 = 0 (1,052 intervals, 8 excluded). *Provisional* |
| Q4 | Runway occupancy | Arrivals 25.69 s (521), departures 76.50 s (532) |
| Q5 | Take-off delay | 25.71 min (533, 2 excluded, early departures kept) |
| Q6 | Taxi by weight class | Medium 12.25 in / 15.65 out; Heavy 8.62 in / 16.12 out; Light, Super and Unknown "No data" |
| Q7 | Taxiway usage | 1,053 flights. B_28 512, E_5 363, B_15 224. Letter B 1,032. *Provisional* (team rule) |
| Q8 | Wheels down to parking | 12.20 min (525) |
| Q9 | Runway activity | 34R busiest (512 take-offs + 23 landings). 1,059 operations. 1 missed approach on 34L, reported separately |
| Q10 | Peak hours | 10:00 = 74 (rank 1), 08:00 = 69, 14:00 = 68, 18:00 = 66, 12:00 & 16:00 = 64 (rank 5). 19:00 = 58 (team rule). 1,060 operations. History only, not a forecast |

## 4. Decisions we made (and why)

1. **Q10 counts every take-off and completed landing** (`v_peak_hours`), including the one take-off with no runway, so 19:00 = **58** and the day has 1,060 operations. *Team rule, 2026-11-14.*
   - **Why:** the Port defines busy hours as "take-offs + completed landings", and `metric_rules.yaml` says "a runway is not needed for this count".
   - **Ground truth:** the file left this take-off out "for consistency with Q9" (57). It also says that including it changes only 19:00 (57 → 58), with no rank change. Q9 still leaves it out, because Q9 counts per runway.
2. **Q7 selects the reporting day by the proxy time.** It counts `exclusion_reason IS NULL` and `selection_time` inside Aug 8, which gives **1,053 flights**. Of the 1,061 legs, 8 are not counted: 1 has its proxy time outside Aug 8, 1 has no time, and 6 have no taxiway recorded (including the missed approach). *Team rule, 2026-11-14.*
   - **Why:** the Port says to "use section-entry time to select the reporting period". The export has none, so we use the team's proxy time from `metric_rules.yaml`. This also matches how every other question filters to Aug 8.
   - **Ground truth:** the file's older working assumption counted all 1,055 flights with a taxiway and no date filter.
3. **Hours with no flights are still shown** (Q2, Q10): "No data" for averages, 0 for counts. The ground truth lists 03:00 = 0 as the quietest hour, so the SQL fills all 24 hours.
4. **Q6 shows a "Super" row as "No data"**, so every ICAO class appears even when there are no flights.
5. **Any date other than 2025-08-08 answers "No data for <date>"**, because the data covers one operating day.
6. **If the AI is unavailable, a keyword match picks the question.** The 10 questions still work on a bad Gemini day. A real "other" answer from the AI goes to views mode.

## 5. Review of a teammate's version of `question_queries.sql`

A teammate sent an edited copy of the SQL file. Every query in it runs, and Q1–Q6, Q8 and Q9 give the same numbers as ours.

| Their change | What we did | Why |
|---|---|---|
| Added **Q6c** (taxi-in and taxi-out by weight class in one table) and **Q9c** (take-offs, landings and missed approaches per runway in one table) | **Added both** (full precision, our date filter) | Correct and useful |
| `selection_time >= '2025-08-08' AND < '2025-08-09'` instead of `selection_date = '2025-08-08'` | Kept `selection_date` | Same rows and same results. `selection_date` matches `templates.py` |
| `ROUND(..., 2)` inside the SQL | Kept full precision in SQL | The Stage 2 guide says round only in the answer text |
| Q2a and Q10 return only the hours that have flights | Kept all 24 hours | The ground truth shows 03:00 = 0 and "No data" hours |
| **Q7:** strict reporting window and no 'missing time' row → 1,053 flights, B_28 512, B_15 224, B 1,032 | **Adopted** (team decision, 2026-11-14) in the chatbot, the SQL file and the tests | Follows the Port's "select by section-entry time" rule, using the proxy time (§4) |
| **Q10:** `v_peak_hours` → 19:00 = 58 | **Adopted** (team decision, 2026-11-14). All 24 hours are still listed | The Port's definition doesn't need a runway (§4) |

The SQL file and the chatbot use the same rules and pass all 31 checks (the ground truth, with the Q7 and Q10 team rules).

## 6. Still open

| # | Item | What to do | Who |
|---|---|---|---|
| 1 | **`TEN_GROUND_TRUTH_ANSWERS.md` still lists the old Q7 and Q10 numbers** (1,055, B_28 513, B_15 226, B 1,037; 19:00 = 57) | Update the file to the team rules (1,053, B_28 512, B_15 224, B 1,032; 19:00 = 58, 1,060 operations), so it agrees with `metric_rules.yaml`, the chatbot and the tests | Ground-truth owner (Vatsalya / team) |
| 2 | **Q7's 1,053 needs an independent hand check** | Count from the Excel file by hand (or pandas) under the new rule. The test numbers came from the team's review of the SQL, not from an independent calculation | Anyone with the Excel file |
| 3 | Q3 and Q7 are **provisional** (hatched-area mapping, taxiway proxy time) | Keep the "provisional" notes in the answers until the Port confirms | Port confirmation |

To go back to the old ground-truth rules, change one filter (Q7) or one view (Q10) in `templates.py` and `question_queries.sql`, and the expected numbers in `test_templates.py`. The old SQL is described in the comments of `question_queries.sql`.

## 7. Windows setup fixes (found while testing)

The Stage 2 guide was written on macOS. On Windows:

- Run backend pytest with **`PYTHONUTF8=1`**. Otherwise `test_legacy_unchanged.py` fails decoding emoji in `git show` output.
- **Don't put `QUERY_MODE` in `.env`.** `load_dotenv()` puts it back during the legacy test, and 5 tests fail. Set it on the command line when you start the server.
- With both fixes: database tests show 99 passed and 1 skipped; backend tests show 174 passed.

## 8. Rules we kept

- Legacy and views modes behave exactly as before (`test_legacy_unchanged.py`, `test_views_mode.py`).
- Templates mode reads only through **`seatac_reader`** (SELECT on the views only).
- Filter values go in as **`%s` parameters**, never pasted into SQL text.
- **Tests never call the AI API**: they use fake intent clients.
- **Never commit or share** `.env`, the Port Excel file (it has real tail numbers), database dumps or logs. Share the Excel file only through the team's approved place.
- Commits go under the author's own name, with no Co-Authored-By lines.

## 9. What's next

- [ ] **Update `TEN_GROUND_TRUTH_ANSWERS.md`** for the Q7 and Q10 team rules, and **hand-check Q7 = 1,053** from the Excel file (§6).
- [ ] **Review `templates.py`**, especially the Q3 and Q7 provisional rules.
- [ ] **Commit and push** `stage2-templates` in small commits, then open a pull request into **`backend-views`** (not `main`).
  - Before committing, run `git status` and check that `.env`, logs and the Excel file are not listed.
  - Don't commit `src/frontend/frontend.log` or the local `package-lock.json` change.
- [ ] **Each teammate:** follow SETUP_GUIDE Step 8 on your own laptop, with your own Gemini key, ask the 10 questions, and report anything that differs from §3.
- [ ] **Test more phrasings** of the 10 questions in the chatbot (the ground truth has 2 per question). Note any that go to views mode by mistake, and we'll add keywords or menu text.
- [ ] **Ask the Port to confirm** the provisional items (Q3 hatched area, Q7 section-entry time, off-block time source for Q2).
- [ ] Later: extend the templates beyond the 10 questions (other groupings, filters such as runway or hour), using the same pattern: tested SQL, ground-truth tests, then intent menu entry.
