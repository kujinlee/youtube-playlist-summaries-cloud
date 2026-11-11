# ci-ghcr-schema-image — round 4 — Claude half

Subject: `git diff origin/master...1014d7b2` (origin/master = `c7c6672f`, PR #389). Branch head
`1014d7b2` adds only the r3 review files over `3e82880e`. Mandate: REFUTE. Nothing written except
this file; no git writes; ghcr.io not touched.

## Findings

### LOW 1 — backlog #340 is closed with a FUTURE date, and disagrees with #310 closed in the same commit

- **File:** `docs/backlog.md:324` (row 340, Status cell), against `docs/backlog.md:294` (row 310).
- **Input:** the Status cell written by `3e82880e`:
  `✅ CLOSED 2026-10-24 — FIXED by remedy (a): ...`
- **What happens (run):** `date '+%m-%d %H:%M %Z'` → `10-23 23:25 PDT`; `git log` dates `3e82880e`
  at `10-23 23:22`. Row 310, closed in the same fold for the same fix, reads `✅ CLOSED 2026-10-23`,
  and the dashboard entry for this change is headed `## 2026-10-23`. So the tick on the item this
  branch actually fixes carries a date that has not happened yet, and the two closures of one fix
  disagree by a day. (Plausibly a UTC date — 06:25 UTC on 10-24 — but every other date in this
  change is local; UNVERIFIED as to cause.)
- **Why it matters (small):** the closure date is the record a later audit (as #389 just did) reads
  to order events against `git log`; a closure dated after the merge it describes reads as a
  retroactive edit.
- **Fix:** `CLOSED 2026-10-24` → `CLOSED 2026-10-23` in row 340's Status cell. One token.

### LOW 2 — the two ci-ghcr decision-log bets state a "written at" time LATER than the commit that contains them

- **File:** `docs/reviews/decision-scheme/decision-log.jsonl`, last two rows.
- **Input:** the `accrete` row says `Written 2026-10-23 23:20, BEFORE round 2`; it was committed in
  `f2431a61` at `10-23 23:18`. The `redesign` row says `Written 2026-10-23 23:25, BEFORE round 3`;
  it was committed in `3e82880e` at `23:22`, and round 3 itself was committed in `1014d7b2` at
  `23:23` — so the text claims it was written two minutes AFTER the round it says it precedes.
- **What happens:** the pre-registration still HOLDS on the evidence that matters — git order:
  each bet is in an ancestor of the round it predicts (`f2431a61` before the r2 files, `3e82880e`
  before `1014d7b2`). Only the prose clock is wrong, i.e. it was not taken from `date`. No guard
  reads these times (none found by grep of `scripts/` for the prediction text format), so nothing
  fails; a reader auditing the scheme by the stated times would conclude the round-3 bet was
  written after the fact.
- **Fix:** none required for this branch's deliverable; if touched, take the stamp from `date` at
  write time. Recorded so it is not mistaken for a hindsight bet. ⚠ This is in a process record,
  not the deliverable; I do not count it toward the verdict on its own.

## Mandate items — what was checked and found clean

**(a) The #340 tick.** Accurate in substance: it names the workflow-level `SCHEMA_DB_IMAGE`, the
digest pin, `imagetools create`, and fail-closed behaviour in both jobs, all of which match
`.github/workflows/schema-gates.yml:191-192` and `:309-315`. Its verification claim ("this PR's
own required `schema-gates` run going green") is a forward claim — no PR exists yet
(`gh pr list --head ci/ghcr-schema-image --state all` → `[]`) — but it is conditional on the right
thing and self-enforcing: `gh api .../branches/master/protection/required_status_checks` lists
`schema-gates` as REQUIRED, so the row cannot reach master unless the claim became true. One
gap in that claim, not a finding: the PR run exercises only the `schema-gates` job; `prod-drift`
runs only on `schedule`/`workflow_dispatch` (`:261`). It pulls the same digest, so reachability
is the same fact; nothing more is claimed. No other row or doc still claims the anonymous ECR pull
is the CI path: `grep -rln public.ecr.aws` outside reviews/explainers hits only `backlog.md` (rows
310/340, both now historical inside "Previously:"), two historical dashboard entries
(`:8161`, `:16510`), the workflow comment explaining the move, and `start-schema-db.sh:42` — the
local default, which the workflow comment correctly says is kept.

**(b) The merge `ad685b78`.** Nothing dropped or duplicated. `git diff origin/master...HEAD --
docs/dashboard-entries.md` is a pure 21-line append at the end (the new 2026-10-23 entry); every
master entry, including #389's, is untouched. Rows 310 and 340 compared cell by cell against
`origin/master` using `check-docs.CELL_SPLIT` (not an ad-hoc split): both keep 8 cells; only
cell 2 (the `✅ (was 🟠)` title prefix, the convention row 341 already uses) and cell 6 (Status)
differ, and in both the OLD content survives inside the new text — including #389's
`audit 2026-10-23, master 92c78bff — STILL FIRING` note on #340, now under "Previously:". ⚠ The
brief's "status cell only" is slightly off: the title cell gained the `✅ (was 🟠)` prefix too;
harmless and conventional.

**(c) The whole delta, fresh.**
- `start-schema-db.sh` uses `$IMAGE` only via `docker image inspect`, `docker pull` and
  `docker run` (`:110`, `:113`, `:125`, `:174`); all accept a `repo@sha256:` reference. Nothing
  parses a `:tag` out of it.
- The prod-drift wrapper: `if ! docker run ...; then echo CANNOT RUN ...; exit 2; fi` is correct
  under Actions' default `bash -e`; the `if` suppresses `-e` for the guarded command only.
- No mutation manifest anchors on the replaced prod-drift text (`grep` of `scripts/mutations/*.json`
  for `schema-gates.yml`/`m4_prod_client`/`ecr`: the only hit is an unrelated `expect` string in
  `check-function-revokes.json`), so no anchor was orphaned.
- Run read-only: `check-docs.py` rc=0, `check-review-rounds.py` rc=0, `check-dashboard-entry.py`
  rc=0, `check-backlog-closure.py` WARN on #117 and #159 only — both pre-existing, neither touched
  here.
- Not verifiable under this mandate: whether the GHCR package is public now (would require
  touching ghcr.io). The tick's correctness rests on that, and the required check is what tests it.

## Verdict reasoning

No Blocking, High, Medium or mechanism defect. One Low in the deliverable's record (LOW 1, a
one-token date fix) — by round 2's precedent, where a single record Low was NOT CONVERGED, this
is the same class. LOW 2 is process-record only and would not on its own withhold convergence.

VERDICT: NOT CONVERGED
