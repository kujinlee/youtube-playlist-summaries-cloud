Reviewed head: 3b92459537732120bca1bded9d89925d8a402d60

# subject-status-386 — round 1, Claude half

Subject: `git diff origin/master...HEAD` on branch `subject-status-386` (PR 650), HEAD `3b924595`.
Mandate: refute. Read-only except this file; every mutation was applied to a scratch clone, never the repo file.

## What was run

| Command | Result |
|---|---|
| `python3 scripts/subject_status.py --self-test` | 18/18, rc 0 |
| `python3 scripts/check-shipping-sets.py --self-test` | 173/173, rc 0 (2m18s) |
| `git grep` of the stable-blob tables in `lib app components worker supabase/migrations` at `c517faa0^`, `c517faa0`, `HEAD` | 0 files, then `0027_stable_blob_addressing.sql` alone, then the same one file |
| Each of the 5 new or re-bound manifest entries, applied to a scratch `git clone` with `node_modules` symlinked, full self-test | all 5 red on the case `expect` names (table below) |

The stale-premise diagnosis holds. Before c517faa0 no runtime file named any of the five tables the
spec schema creates (`workspaces`, `workspace_videos`, `video_generations`, `video_artifacts`,
`video_artifact_sources`). From c517faa0 on, exactly one does: migration 0027. So the old case went red
because the subject really did ship, and the banner logic did not regress. The control in the backlog
row ("breaking the UNSHIPPED branch turns it red") also holds: replacing `elif refs == 0:` with
`elif False:` in a copy turns exactly "the parked schema reports UNSHIPPED, not SHIPPED" red (17/18).

Mutation results (scratch clones `m0`..`m4`):

| Manifest entry | Case named in `expect` | Red? |
|---|---|---|
| any effort is accepted (re-bound) | an effort outside 1-3 is refused | yes (and the bool case) |
| a package not in packages is accepted (re-bound) | a component whose package is not a key in packages is refused | yes (and `package: []`) |
| shared_with may name no package (re-bound) | a shared_with naming no package is refused | yes |
| a boolean effort is accepted (new) | a boolean effort is refused (True == 1 …) | yes |
| an unhashable package reaches the dict membership test (new) | `package: []` is refused by name | yes (and the totality case) |

`ci.yml`: the new step sits in job `verify` (line 434), which has no `if:` and runs on `pull_request`
to master, on push to master and `batch/**`, and on the schedule. It runs on PRs. The job checks out with
`fetch-depth: 0`, so `last_commit` has history.

## Findings

### MAJOR

**C1. `load_map` is still not total: deep nesting raises `RecursionError`, which is a traceback that exits rc 1, the same code as a refusal.**
`scripts/check-shipping-sets.py:773-835` (`load_map`); the new totality case starts at `:1498`.
Backlog row 700's FAILS IF is "any wrong-typed value in `components.json` makes `check-shipping-sets.py`
exit with a traceback". Its stated Fix is the bounded reader plus declared-shape walk that backlog
#699 gave `check-inventory.py` (`_read_json` with `MAX_DEPTH = 32`, `scripts/check-inventory.py:444-475`).
That was not done. Only the membership tests were type-guarded. This is the same class backlog #699 measured (a `repr` of deep JSON
raising `RecursionError`).
Reproduction: make a valid map whose `effort` is `"[" * 100000 + "]" * 100000`, then run
`python3 scripts/check-shipping-sets.py --map <that file>`. It fails with
`RecursionError: Stack overflow … while getting the repr of an object`, raised from the `Refused` message's
`{c.get('effort')!r}`, and exits **rc=1**. At 200 000 levels it fails inside `json.loads`, which
catches only `(OSError, ValueError)`, so `RecursionError` escapes, again rc=1. These positions all raise:
`effort`, a component's `id`, a component with no id (`{c!r}`), an exclusion (`{e!r}`), and the whole file
at 200k. rc 1 is the code for a REFUSED map or for gaps, so the traceback is not even
distinguishable by exit code. The 9-value corpus in the new case has nothing deeper than `[[]]`, so it
cannot see this. Fix: read through a bounded reader (depth cap means CANNOT RUN, rc 2). The simplest is to reuse
`check-inventory._read_json` or move it into a shared module. Also catch `RecursionError` at
`json.loads`. Add a deep-nesting value to `wrong`.

**C2. The UNSHIPPED fixture can no longer catch the banner's flagship defect: counting tables the subject only REFERENCES.**
`scripts/subject_status.py:195-210`. The ⭐ comment directly above the case still says it guards the
defect where the banner "counted references to the CALLER's scan list (which includes shipped tables like
`jobs`)". The old case caught that because the real spec schema references `jobs`, `playlists` and
`profiles`. The new fixture is `create table zzq_parked_probe_t386 (id int);`. It references no shipped
table, so a banner that also counts referenced tables still prints UNSHIPPED for it.
Reproduction (copy of the script with `ROOT` pinned to the worktree): replace
`tables = subject_tables(subject)` in `subject_banner` with the same plus every `references X` and
`alter table X` name in the subject's SQL. The real schema's banner becomes
`SHIPPED — 122 runtime file(s) reference …, jobs, playlists, profiles, …`, but the self-test stays
**18/18 green**. With the fixture changed to
`create table zzq_parked_probe_t386 (id int references jobs(id));\nalter table jobs add column zzq int;\n`,
the clean script is still 18/18 and the mutant goes red on "the parked schema reports UNSHIPPED, not SHIPPED"
(17/18). The `subject_tables`-level case ("does NOT include tables the schema merely references") still
guards that function. It does not guard a banner that derives its list some other way, which is exactly the shape
of the original bug (a list the caller passed in). Fix: put a reference to a shipped table into the fixture, as
above. Optionally, add a manifest for `subject_status.py`, which has none today.

### MINOR

**C3. The totality case's name overclaims, and so does the backlog row: it accepts `ACCEPTED`, and it skips `measured_at`.**
`scripts/check-shipping-sets.py:1498-1524`. The case is named "every wrong-typed value … is refused, never a
traceback", and the comment says "load_map is TOTAL — every wrong-typed value is refused". But the predicate
passes any result starting with `ACCEPTED`. The top-level loop covers `packages`, `components` and
`exclusions`, not `measured_at`. `measured_at: [[]]` (or `{}`, `1.5`) is ACCEPTED and coerced through
`str()` at `:835` into `ComponentMap.measured_at: str`.
Reproduction: with the type check removed (mutation m3), this case stays green and only the dedicated bool case
goes red. Fix: either rename it to "never a traceback" (which is what it asserts), or split it so that
values known to be wrong must be REFUSED. Then refuse a non-string `measured_at`, or say why it may be anything.

**C4. The `shared_with` entry's new `isinstance(p, str)` clause has no manifest entry.**
`scripts/check-shipping-sets.py:810`. The re-bound entry ("shared_with may name no package") deletes the whole
`not isinstance(p, str) or p not in packages or ` prefix, so it never isolates the type check.
Reproduction (scratch clone m5): replace `any(not isinstance(p, str) or p not in packages` with
`any(p not in packages`. The totality case goes red with
`('shared_with', [[]], "RAISED TypeError: cannot use 'list' as a dict key …")` (172/173). The clause is
load-bearing and killable, but unpinned, while its sibling `package` clause got its own entry. Fix: add the entry
(`expect`: the totality case) and pin 218.

### NIT

**C5. The module docstring is stale, and part of it was already stale.**
- `scripts/subject_status.py:7-8`: "read `…/stable-blob-addressing/schema/` — an UNSHIPPED spec". Per this
  PR's own new case it now reports SHIPPED. A dated "⟳ 2026-11-27: promoted as migration 0027" note would
  stop a reader trusting it.
- `:10-11`: "these need a live Postgres, so they are not in CI". The schema gates have run in CI since
  2026-09-13 (`docs/dev-process.md`, *Not yet in CI*). This was already stale before this PR.
- `:32`: the usage example calls `subject_banner(SCHEMA, Path(__file__), TABLES)`, but the signature takes 2
  arguments (`:116`) and all three callers pass 2. This was already stale before this PR. The 3-argument form is the scan-list
  shape C2 is about, so the docstring still advertises the bug.

## Verdict

The diagnosis for row 386, the CI placement and all five manifest bindings check out. Row 700's own
FAILS IF still fires (C1), and the row 386 rewrite dropped the banner-level guard its comment claims to keep (C2).

VERDICT: NOT CONVERGED
