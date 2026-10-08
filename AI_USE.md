# AI Use Log

We record every AI tool used for project work, what it was used for, and how we checked its output before using it.

| Date | Tool | Purpose | How we verified it |
|---|---|---|---|
| 2026-09-29 | Claude Code | Reviewed the past cohorts' files and the inherited code; drafted the docs in /docs | Checked key facts (file paths, row counts) against the code and database |
| 2026-10-01 | Claude Code | Set up the app locally and added an optional Gemini provider | Ran the app end to end; changes not committed until reviewed |
| 2026-10-06 | Claude | Helped with structure, wording and editing of the Project Plan and partner emails | The team wrote and revised the content, checked every fact against the code and data, and incorporated feedback from Samer and Samad |
| 2026-10-07 | Claude Code | Fact-checked every claim in the Project Plan (read-only) | Reviewed the report; corrected or removed claims that didn't hold up |
| 2026-10-08 | Claude Code | Restructured the repo into /docs and /src | Ran the backend health check and loaded the frontend |
| Ongoing | Google Gemini | Used inside the chatbot to write SQL and summaries | Answers checked against our hand-calculated test set |

**How we verify:** code is reviewed by a second team member before merging; facts in documents are checked against the code, the data or a cited source; anything we can't verify is removed or labelled as an estimate.