# Install experiment, tier B — the comprehensibility package in a real third-party repository

Spec §6; marketplace-inventory plan Task 15. Measured **2026-11-19, 23:37–23:43 PST**, on branch `hse-e` at
`92a86d54` (Task 14's commit). Same machine, versions, driver and invocation form as
[`experiment-tier-a.md`](experiment-tier-a.md), whose deviations apply here unchanged; only the host differs.

## The host

`Yeachan-Heo/oh-my-claudecode` (MIT), cloned in full (`git clone`, no `--depth`), then `git remote remove origin`
(`git remote -v` → empty). `git rev-parse --is-shallow-repository` → **`false`**; `git rev-list --count HEAD` → 6343.
HEAD **`dec7e4188c0e3de6b92fb3d734ee5c95326021ed`** (2026-11-11T17:22:38Z, *fix(manifest): correct entry 79 for #5009
with valid digest and current head (#5026)*). 219 MB working tree. Copied with `.git` to `<world HOME>/project`.

Deviation from the plan: the clone went to `$(getconf DARWIN_USER_TEMP_DIR)/mktB.4EXn`, not the session scratchpad,
because a scratchpad lies under the author's home and tier A measured that as a leak (isolation defect I1). Nothing
was pushed or written back; no issue, PR or other GitHub write was made.

The host carries its OWN `CLAUDE.md`, `AGENTS.md`, `.mcp.json`, `.claude-plugin/` and `hooks/`. Every skill session
loaded `<world HOME>/project/CLAUDE.md` (5 of 5 transcripts) — the host's, which a real user of that repository would
also get; no author path appeared in any transcript.

## Results (population: the same 33 components; 14 exercised, as in tier A)

**Scripted half (23:37:41–43):** identical rc and message to tier A for all 8 operations — `brief-compose` rc 1 (no
`~/explainers`), `gen-dashboard` rc 1 (Ask-tray refusal), `gen-goals-page` rc 2, `gen-features-page` rc 2,
`gen-backlog-page` rc 1 (`FileNotFoundError` on `<install dir>/docs/backlog.md`), `goal-tree --print` rc 2,
`regen-pages --all` rc 2 (git common dir from the install dir, exit 128), `ask_answerer --status` rc 0. Suite defects
S1 and S2 reproduce in a real repository: they are not artefacts of the seeded one.

**Serve (23:37:54–57):** preflight `[]` once 7391 was freed; all three conditions held — start printed
`serving <world HOME>/explainers`, pidfile 6822 = listener 6822, `GET /` 200 with the sentinel; page 200;
`POST /questions` 200 and recorded. The owner's open browser tab again polled the world's server
(`GET /_stale?p=…2026-11-17-brief-marketplace-plan.html` in its `.serve.log`).

**Skill half** (`claude -p`, cwd `<world HOME>/project`; cost as `--output-format json` reported it):

| Skill | rc | Time | Turns | Cost (USD) | Page | Outcome |
|---|---|---|---|---|---|---|
| `brief` | 0 | 25 s | 8 | 0.130 | none | Found `brief-compose.py` in the staged package this time; it refused (no Ask-tray page — S2). Text briefing instead; said the skill "was written for a different repo" (no roadmap/backlog/reviews) |
| `explain-diff` | 0 | 97 s | 16 | 0.329 | `2026-11-19-explanation-manifest-entry-79-dec7e4188.html` | Written, **not served**: the model skipped the delivery loop and offered a `file://` path; no Ask tray. (Tier A's run served its page — same skill, different outcome) |
| `explain-findings` | 0 | 43 s | 11 | 0.216 | none | "This repo has no `scripts/brief-compose.py`" — S3 (CWD-relative names); verdict in text |
| `explain-topic` | 0 | 86 s | 19 | 0.360 | `…-topic-continuation-enforcement-incomplete.fragment.html` | Fragment written, not composed (S2), not served |
| `dashboard` | 0 | 12 s | 5 | 0.067 | none | Refused: `docs/dashboard-entries.md`, `scripts/regen-pages.py`, `check-dashboard-entry.py`, `.claude/hooks/regen-dashboard.sh`, `docs/anchors.md` absent — S4 |

Total 1.10 USD, 5 runs, stranger account. **No page with an Ask tray was produced (0 of 5); 0 pages served by a
skill.** Every skill's base directory was again the STAGED marketplace (`<run>/mkt/comprehensibility/skills/<skill>`),
isolation note I2 of tier A.

Pass conditions match tier A's matrix for every component except `skill-explain-diff`, whose useful operation FAILS
here (page not served: conditions 1 and 3 fail). Condition 2 is `argued` for every page skill: there are no seeded
facts for this host. The skill answers themselves were accurate where checked by hand against the clone (`brief`:
branch `main`, clean tree, HEAD `dec7e4188`), but that is not scored.

## Resources reached that belong to the host repository (the third list)

Every `RunRecord.opened` path inside `<world HOME>/project`, over all 11 scripted and serve runs and the 5
post-skill `--stop` runs:

| Run | Path | Reading |
|---|---|---|
| `gen-backlog-page.py` | `<world HOME>/project/<unknown>` | not a host file: the traceback printer's `linecache` lookup of a `<unknown>` frame, resolved against the CWD |

**No Python process opened a host file.** That is S1 seen from the other side: the scripts never look in the user's
repository, so they reach none of its resources. What the 5 `claude` sessions read in the host (they plainly read
`src/features/continuation-enforcement.ts`, `.github/generated-artifact-authorizations.json`, and ran `git log`) is
**NOT CAPTURED** — no `RunRecord` exists for a non-Python process (tier A, deviation 1). Whether the host's
`.mcp.json` servers started under `-p` was not checked: NOT CAPTURED.

Git-history items: `brief` cited the host's release history (v5.8.4–v5.8.6, repin commits); those are host facts, not
suite defects, and the clone is confirmed full.

## Port 7391

The owner's server (pid 72980, from Task 14's restart) was **stopped 2026-11-19 23:37:48** and **restarted 23:43:07**
from the main checkout (`python3 scripts/explainer-serve.py` → pid 48523, 92 explainers, listening). Each skill run was
followed by the world's own `--stop`; no listener remained before the restart.

## NOT RUN

- The 5 hooks (no `bash` on the allow-list; no `hooks/hooks.json` in the package) — as tier A.
- `ask_answerer --once` (a model call per question) — as tier A.
- The scan's prediction of each failure — `ScanReport` (slice D, PR #600) unmerged; Task 16.
