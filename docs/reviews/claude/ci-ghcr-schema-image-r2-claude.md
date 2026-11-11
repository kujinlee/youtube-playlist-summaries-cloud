# ci-ghcr-schema-image — round 2 — Claude half

Subject: `git diff origin/master..f2431a61` on `ci/ghcr-schema-image` (worktree `wt-ghcr`).
Mandate: REFUTE. Read-only. No pulls from or pushes to ghcr.io were made.

## Findings

### LOW 1 — backlog #340, the item this change actually fixes, is left `pending`, while #310 is closed as "its duplicate"

- **Where:** `docs/backlog.md:324` (row 340, status cell still `pending — filed 2026-10-21; BLOCKS MERGE whenever it fires`)
  against `docs/backlog.md:294` (row 310, `✅ CLOSED 2026-10-23 — DUPLICATE of backlog #340 … both are fixed by remedy (a)`).
- **Input:** `python3 scripts/check-backlog-closure.py` run in the worktree.
- **What happens (ran it):**
  ```
  ⚠ #340: MERGED but its row does not carry ✅
      schema-gates pulls its database image from a digest-pinned GHCR mirror, not an anonymous ECR pull (backlog #340)
  ```
  The commit subject `7b3ed17e` ends in `(backlog #340)`, so the inverted-direction closure guard
  already fires on this branch. The delta closes the *duplicate* and leaves the *canonical* row open;
  a reader landing on #340 sees "pending, BLOCKS MERGE" after the fix shipped. `dev-process.md`
  → Phase 5: "Roadmap/backlog status ticks ride in the **same PR** as the work they describe", and
  "Write the merge tick BEFORE opening the PR".
- **Fix:** tick #340 `✅` with the same conditional wording #310 now carries (fixed by remedy (a);
  verified by this PR's own required `schema-gates` run going green, which requires the mirror to
  be reachable), and point #310's closure at it as it already does.

### Nothing else found — the mandate items, each with what was checked

**a. Digest reference through `start-schema-db.sh`.** Read the whole script. `$IMAGE` is used only
as a quoted argument to `docker image inspect` (pull_image, twice), `docker pull`, `docker run`, and
in three `echo` messages. There is no string parsing of the reference (no `${IMAGE%:*}`, no tag
split), so a `name@sha256:…` form with no tag has nothing to break. `docker image inspect <repo>@<digest>`
resolves by RepoDigest after a pull, so the final "honest re-check" does not false-fail on a digest
form. Self-test: `self-test: 23 cases, 23 passed, 0 failed` (none touch the image, correctly — it is I/O).

**Digest identity, independently checked:** the local ECR image on this machine reports
`RepoDigests: ["public.ecr.aws/supabase/postgres@sha256:ac581882596ed0e46937ea6dd53a627d09f53e005d7264c2082a7ff7b62eaaca"]`
— identical to the pinned digest. So the claim "the digest of the ECR original's image index" holds
against a source other than the author's own `imagetools inspect`.

**b. Env visibility.** `env:` is workflow-level (`schema-gates.yml:191-192`), before `jobs:`. Neither
job has a job-level `env:`; the only step-level `env:` blocks (`Fifteen schema gates`, the credential
step, `Has production drifted`) set other keys and do not shadow `SCHEMA_DB_IMAGE`. No `services:`
block. `Build the schema database` runs the script in a `run:` step, which inherits workflow env;
the prod-drift `run:` expands `"$SCHEMA_DB_IMAGE"` from the shell env. Remaining `public.ecr.aws`
mentions in CI-run files: `start-schema-db.sh:42` (the local default, intended), and comments in
`start-schema-db.sh` and two fixture `.sql` headers — prose only. `ci.yml` does not pull this image.
`scripts/m4-base-db.sh` names the image but is a local tool, not invoked by either workflow.

**c. Workflow-parsing guards.** All run read-only in the worktree, all green:
- `check-python-pin.py --self-test` → `111/111 passed`; normal run rc=0 (ADVISORY: local 3.14).
  Direct call on the edited file: `job_names → ['schema-gates', 'prod-drift']`, `unreadable_jobs → 0`,
  `job_blocks` keys the same two — the new top-level `env:` sits before `jobs:` and its line-scanner
  only opens on `^jobs:`, so it is invisible to it, as it should be.
- `check-guard-coverage.py --self-test` → `37/37 passed`; normal run ✅.
- `check-storage-independence.py` → `50 cases, 50 passed`; normal run ✅ (30 gate files).
- `check-ci-watched.py --self-test` → `82/82`. `check-merge-ready.py --self-test` → `74/74`.
- `check-ratchet-contract.py` rc=0, `check-docs.py` rc=0, `check-dashboard-entry.py` → `ok — an entry block was added`.

**d. Supply chain.** Strictly at least as safe as before. The old reference was a mutable TAG on a
registry the project does not control; the new one is content-addressed, and the Docker client
verifies the manifest against the digest, so a compromised `kujinlee` account can **delete** the
package (→ pull fails → rc=2) or push new tags (irrelevant — nothing reads a tag) but cannot make
this reference resolve to different bytes. The pin is on the image INDEX; the per-platform manifest
it selects is covered transitively by that digest. What is lost: silently picking up a re-push of
`17.6.1.147` upstream — which is the property a schema gate should *not* have. Upgrading is now an
explicit digest edit, which is the correct cost. Not measured: GHCR's anonymous-pull limits for
public packages; the change trades one registry's anonymous allowance for another's (UNVERIFIED —
not a finding, but the claim the gate is now immune to throttling is not made anywhere, which is right).

**e. Failure mode while private/deleted.** `schema-gates`: `docker pull` → 401/404 → five attempts
with backoff → `pull_image` false → `CANNOT RUN … return 2`. Fails CLOSED, never open; costs ~75s of
backoff on a non-transient 401, a cosmetic inefficiency, not a defect. `prod-drift` (the fold): the
`if ! docker run …; then … exit 2; fi` form is correct under Actions' default `bash -e` — the
`if` guard is exempt from `-e`, so the CANNOT RUN message and rc=2 are reached. (The next line,
`docker exec … psql --version`, would still exit 1 rather than 2 if it failed — pre-existing and
outside the delta's edited line.)

**f. #310 closure and dashboard entry.** The dashboard entry is accurate and now conditional (the
copy "has to be public"; the tech note says this PR's green run is the verification). The #310
closure is accurate except for the asymmetry in LOW 1. The workflow comment's "This check going
green on the PR that introduced this line is what verifies the mirror is reachable" is sound:
a fresh runner has no local image and the pull carries no login, so green is impossible unless an
anonymous pull of that exact digest succeeds.

## Round-1 fold, re-checked
- r1 LOW 2 (prod-drift CANNOT RUN): folded correctly, see (e).
- r1 LOW 3 (premature completion claims): folded — workflow comment, dashboard entry and #310 text
  all now state the requirement and name the verification instead of asserting public.
- r1 HIGH (package private): not re-reported; nothing new.

VERDICT: NOT CONVERGED
