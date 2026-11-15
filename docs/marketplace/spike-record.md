# Packaging spike — GO

Spec §7 item 0; marketplace-inventory plan Task 4. **Result: GO**, recorded 2026-11-15 10:31 on branch
`harness-ships-elsewhere` at `e83bd3be` (the scripts measured are that commit's). The spike installed one skill and
one script from a throwaway local marketplace into a fresh stranger world, ran the script by its installed path from
an unrelated directory, and served a page from the world's own server, verified as the world's by all three of the
plan's conditions.

Machine: macOS (Darwin 25.5.0), `python3 -V` → `Python 3.14.4`, `claude --version` → `2.1.323 (Claude Code)`,
`git --version` → `git version 2.49.0` — each the output of that command in this session.

## How it was run

A driver in the session scratchpad (outside the repository) called the Task 2 and Task 3 functions directly:
`mkt_stage.stage([PackageSpec("spike", "0.0.1", [".agents/skills/explain-topic"], FILES)], <run>/mkt)`,
`mkt_isolate.build_world(<run>/world, ["python3", "git", "claude"])`, `mkt_isolate.preflight(world)`,
`mkt_stage.install(world, mkt, "spike")`, then `mkt_isolate.run_isolated(world, argv, <world>/elsewhere, 60)` for each
operation below. `<world>/elsewhere` is an empty directory inside the world, unrelated to the installed tree.

No model call was made: `claude plugin marketplace add` and `claude plugin install` need no login (Task 3's probe
measured that, and this run confirms it). The stranger token was not used.

## The payload, and the plan defect it corrected (run 1 → run 2)

The plan's Step 1 names three files (`explainer-serve.py`, `page_chrome.py`, `page_markup.py`). At `e83bd3be` the
script's closure for the spike's operations is **five**:

| File | Why it is in the closure | Found by |
|---|---|---|
| `scripts/explainer-serve.py` | the script | — |
| `scripts/page_chrome.py`, `scripts/page_markup.py` | imported at module load (`explainer-serve.py:102-103`) | the plan |
| `scripts/ask_answerer.py` | imported at module load (`explainer-serve.py:101`), added after the plan was written | reading the imports before run 1; run 1 included it. The plan's three-file payload was NOT run, so its `--help` failure is inferred from that import, not measured |
| `scripts/regen-pages.py` | loaded by `importlib` on `GET /` (`_regen()`, `explainer-serve.py:1420-1430`, called from `serve_state()`), added by backlog #627 after the plan was written. The plan's Step 1 places `regen-pages.py` only behind the standing-page routes; since #627 the index route needs it too | **run 1** |

**Run 1** (four files, world `run-103039`, 10:30): install rc 0, `--help` rc 0, preflight clear, `--status` rc 1,
start printed `serving <world HOME>/explainers`, world pidfile pid 48968 = listener pid 48968 — and `GET /` failed with
`RemoteDisconnected`. The world's `.serve.log` holds the cause: `FileNotFoundError: … /spike/0.0.1/scripts/regen-pages.py`
raised from `_regen()`. That is a payload missing a member of the script's closure — by the plan's own rule (Task 4,
*FAILS IF*) a PLAN defect, never the D3 falsifier — so the payload was fixed and the spike re-run from a fresh world.
The plan's stated staging falsifier (`--help` exiting with `ModuleNotFoundError`) is narrower than this case: the
missing member here is reached only by a route, so `--help` passed and the failure showed only at `GET /`.

**Run 2** (five files, world `run-103130`, 10:31) is the result below.

## Run 2 — the evidence

| Check | Result |
|---|---|
| `stage` | marketplace `mkt-local` written; 7 files in the installed tree: `.claude-plugin/plugin.json`, the five scripts under `scripts/`, `skills/explain-topic/SKILL.md` |
| `preflight` before install | one refusal: `port 7391 is already listening` (the owner's server) — expected; install needs no port |
| `install` | `claude plugin marketplace add` and `claude plugin install spike@mkt-local` rc 0; installed at `<world HOME>/.claude/plugins/cache/mkt-local/spike/0.0.1` |
| (a) `python3 <installed>/scripts/explainer-serve.py --help` from `elsewhere` | **rc 0**, stderr empty; 92 Python opens, none outside the world and the interpreter's stdlib |
| 7391 freed (see *Port*) | owner's server pid 49043 stopped 10:31:38; preflight then **empty** |
| `--status` | **rc 1**, `listening : NO on http://127.0.0.1:7391` — the plan's expected result on a free port |
| sentinel | `<world HOME>/explainers/2026-11-15-mkt-sentinel-<16 hex>.html`, token fresh from `secrets.token_hex(8)` |
| start (no flag) | rc 0; stdout begins `serving <world HOME>/explainers` — condition **(i) holds** |
| world pidfile vs listener | pidfile `50780`; `lsof -nP -t -iTCP:7391 -sTCP:LISTEN` → `50780` — condition **(ii) holds** |
| `GET /` | **200**, 6230-byte body containing the sentinel token — condition **(iii) holds**; the world's `.serve.log` reads `"GET / HTTP/1.1" 200 -` |
| `--stop` | rc 0, `stopped pid 50780`; nothing listened on 7391 afterwards |
| Python opens outside the world + stdlib | none for `--help`, `--status`, `--stop`; `/dev/null` only for start (`detach_streams`) |

Bound on the open counts: the audit hook sees Python only (`isolation-baseline.md`); `git`, which the world allows,
was never launched by these operations (each run's `executed` list is the world's `python3` alone).

## Port 7391 (plan Step 2, Human step H7)

At `e83bd3be` the stranger can only serve on 7391: the world's environment is built from `HOME`, `TMPDIR`, `PATH`,
`LANG`, `PYTHONPATH` (`mkt_isolate.ENV_KEYS`), and the server's default is 7391. H7 was not waited on: the owner gave
standing permission on 2026-11-13 03:09 to stop their server whenever work needs the port and restart it. It was
stopped twice (run 1 at 10:30:51, run 2 at 10:31:38) with `python3 scripts/explainer-serve.py --stop` in the main
checkout, and restarted from the same checkout about three seconds later each time; after run 2 it listened as pid
50846 and answered `GET /` with 200.

## Findings (recorded, not repaired — *Evaluate, never repair*)

1. **The plan's "hard-coded port" finding is out of date.** Since backlog #627, `explainer-serve.py` reads
   `EXPLAINER_SERVE_PORT` and `EXPLAINER_SERVE_ROOT` (`:106`, `port_from` at `:110`, `PORT` at `:130`). What remains
   true: unset, every user's server takes 7391, so two users of one machine still collide by default, and
   `start()` answers `already serving` with rc 0 when anything holds the port (`:2219-2223`).
2. **The serve closure grew twice after the plan was written** (`ask_answerer.py` at load, `regen-pages.py` on
   `GET /`), and the second is reached only by `importlib` from a route, so an import scan of the module's top level
   misses it. Task 6's shipping-set declaration and Task 8's file-set resolution have to account for a closure that
   static top-level imports do not show.
3. **Step 4 — what the skill text tells the model to run does not resolve from an unrelated directory**, as spec §4
   predicts. `skills/explain-topic/SKILL.md` says *Follow `../shared/explainer-delivery.md`*: absent in this payload
   (the spike does not stage `shared/`; Task 3 maps it to `skills/shared`, so it resolves once staged). The delivery
   procedure it points to names `python3 scripts/explainer-serve.py` and `python3 scripts/ask_answerer.py`: both
   exist at the plugin root and at neither the unrelated directory nor the skill directory (checked with
   `Path.exists()` from each). `scripts/check-explainer-delivery.py` and `scripts/brief-compose.py`, which the same
   texts name, are not in the payload at all. These are CWD-relative paths — a finding, not a spike failure.

## What GO allows

Slice C may proceed (plan *Ordering*). Task 1 is not split off (Step 5 splits it only on INCOMPLETE or NO-GO).
