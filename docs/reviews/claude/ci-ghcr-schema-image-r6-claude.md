# ci-ghcr-schema-image — round 6 — Claude half

Subject: `git diff origin/master...8b675b3e` (20 files, +485 / -6). `git merge-base --is-ancestor
origin/master 8b675b3e` → true, so master (incl. PR #389, `c7c6672f`) is contained. Mandate: REFUTE.

## What was run (read-only, plus the one permitted ghcr.io contact)

| Check | Result |
|---|---|
| Anonymous `docker pull ghcr.io/kujinlee/supabase-postgres@sha256:ac58…aaca` | rc=0, `Digest: sha256:ac581882…aaca`. Anonymity checked: `credsStore` is `desktop`, and `docker-credential-desktop get` for `ghcr.io` → `credentials not found in native keychain`; no `ghcr.io` key in `~/.docker/config.json` `auths` |
| `docker image inspect --format '{{.RepoDigests}}'` on it | `[ghcr.io/kujinlee/supabase-postgres@sha256:ac58…aaca public.ecr.aws/supabase/postgres@sha256:ac58…aaca]` — the mirror and the ECR original are the SAME digest, which directly confirms the "imagetools create preserved the index digest" claim |
| Ruby YAML parse of `schema-gates.yml` | top-level `env` = `{"SCHEMA_DB_IMAGE"=>"ghcr.io/…@sha256:ac58…aaca"}`; neither job declares a job-level `env` (`["schema-gates", nil]`, `["prod-drift", nil]`), and `grep SCHEMA_DB_IMAGE` finds no step-level override |
| `bash scripts/ci/start-schema-db.sh --self-test` | `23 cases, 23 passed, 0 failed` |
| `python3 scripts/check-storage-independence.py` | `no gate reads storage.* … (30 gate files checked)`, rc=0 |
| `python3 scripts/check-docs.py` | `Documentation integrity OK`, rc=0 |
| `python3 scripts/check-backlog-closure.py` | WARN on #117 and #159 only — both pre-existing on master, neither touched here; rc=0 |
| `python3 scripts/check-dashboard-entry.py` | `ok — an entry block was added` |

## (a) The #340 tick

- `docs/backlog.md` row 340 status: `✅ CLOSED 2026-10-23 — FIXED by remedy (a) … Verified by this
  PR's own required schema-gates run going green …`. Accurate against the tree: the env var, the
  digest, the `imagetools` provenance (now confirmed by RepoDigests above), and the fail-closed
  claim (`start-schema-db.sh` `pull_image` → `return 2`; prod-drift `if ! docker run … exit 2`).
- The condition is the right one for the `schema-gates` job: a fresh runner has no local image,
  `pull_image`'s `docker image inspect "$IMAGE"` short-circuit cannot fire, so green ⇒ the digest was
  pulled from ghcr. It does not cover `prod-drift` (runs only on `schedule`/`workflow_dispatch`);
  that gap was already recorded in r4 Claude (lines 51–52) as not-a-finding, and it shares the exact
  image reference, so I do not re-raise it. A `gh workflow run schema-gates.yml --ref
  ci/ghcr-schema-image` before merge would exercise it if the coordinator wants that half observed
  rather than inferred — optional.
- Row 310 status is closed as the duplicate with the same evidence; consistent with 340.
- Other places still claiming ECR is the CI path: `grep -rln 'ecr.aws\|17.6.1.147'` over
  `scripts tests lib docs/*.md .github` → `start-schema-db.sh` (line 42 = the local default, line
  160 = history of the throttle, both accurate), `auth-service-fixture.sql:3` (describes what the
  image *ships*, true of the byte-identical mirror too — not a path claim), `storage-service-fixture.sql`
  (now describes both paths correctly after the r5 fold), and `backlog.md`/`dashboard-entries.md`
  history. None asserts CI pulls from ECR.

## (b) The merge

- Two-dot `git diff origin/master 8b675b3e`: `dashboard-entries.md` −0/+18, `decision-log.jsonl`
  −0/+4, `backlog.md` −2/+2 (only rows 310 and 340). Nothing from #389 was dropped or duplicated;
  repeated `## <date>` headers in the dashboard are the file's normal shape (348 headers, one per
  entry).

## (c) The delta, fresh

- Workflow env: workflow-level `env` is visible to every step's shell, so both
  `start-schema-db.sh`'s `${SCHEMA_DB_IMAGE:-…}` and prod-drift's `"$SCHEMA_DB_IMAGE"` resolve to the
  pin. Quoted; a digest reference contains no shell metacharacters anyway.
- `pull_image` with a digest reference: `docker image inspect name@sha256:…` resolves via
  RepoDigests (verified above), so the post-pull "honest re-check" works with this reference form.
- prod-drift wrapper: correct; `docker run` pulls implicitly with no retry, as before this branch —
  not a regression.
- No finding at Medium or above. Nothing at Low that the r6 `defer` bet does not already cover; the
  workflow comment's `start-schema-db.sh:42` is a vendored line number (it is correct today, and r2/r4
  saw it), which I note only for the record.

## Findings

None.

VERDICT: CONVERGED
