# ffmpeg-deb-cache — round 1, Claude half

Subject: branch `ffmpeg-deb-cache`, PR #407, `git diff origin/master...HEAD` at `35e7fdd3`
(`.github/workflows/ci.yml` + `docs/dashboard-entries.md`). Mandate: refute.

Evidence base:
- **CI, executed (read from the logs):** run 40397292037 (`09ed8c4d`): key step printed `ffmpeg's package set: 81 file(s)`,
  key `ffmpeg-debs-e3f84e9a9797c797eb3e1d5fa99b2f50`, `Cache not found`, `Need to get 66.4 MB`, `Fetched 66.4 MB in 2s`,
  `Cache saved` (66,349,826 B). Run 40400167030 (`35e7fdd3`): same key, `Cache restored from key: ffmpeg-debs-e3f8…`,
  `ffmpeg cache: restored 81 package(s)`, `Need to get 0 B/66.4 MB of archives.`, Save `skipped`. Install step 11s (miss)
  vs 19s (hit). Runner image `ubuntu-26.04` 20261012.163.1. Both runs' `verify` went red on unrelated steps
  (`reference namespaces are qualified` on `docs/backlog.md` rows on the pre-merge ref; `check-review-recorded` on the
  second — expected until this review is filed).
- **Container, executed:** `ubuntu:26.04` (apt 3.2.0, the same series as the runner image), using `jq` (3 debs) as a
  stand-in for ffmpeg's 81. Scripts and output are in the reviewer's scratchpad, not the repo.

So the happy path is **proven**: miss → save, hit → restore → zero-byte download → install. Every finding below is about
the claims and the failure paths.

## Findings

### F1 — Medium — the safety claim "apt still verifies every package at install" is FALSE for a restored file — `ci.yml:152-155`, PR body step 3, dashboard entry
**Executed.** In `ubuntu:26.04`/apt 3.2.0 I downloaded `jq`'s debs, then overwrote `libjq1_…deb` with random bytes of
the **same size** (146,208 B):
- `apt-get install --download-only jq` → `Need to get 0 B/393 kB of archives.`; `cmp` shows the poisoned file was KEPT.
- `apt-get install --no-download jq` → apt handed the file straight to dpkg; the failure was dpkg's
  (`Errors were encountered while processing: …libjq1…deb`, rc 100), **not** a hash mismatch. A same-size file that
  *is* a valid .deb would have been installed as root.
- Control: a **truncated** file (1,000 B) IS refetched (`Get:1 … libjq1 … [146 kB]`, `cmp` equal afterwards).

So apt checks an existing archive's **size**, not its hash, in both phases. The comment's "SKIPS a .deb … whose hash
matches the signed index" and "apt still verifies every package at install" — repeated in the PR body ("apt still
verifies every package at install") and the dashboard tech note — are false, and they are the whole of the PR's
answer to "can a cache hit install a package the signed index did not name".

Practical exploitability is bounded by GitHub's cache scoping (reasoned): a PR run can write only its own
`refs/pull/N/merge` scope, and the master scope only by a master push, so injecting a poisoned entry needs write access
the attacker would not otherwise lack. The defect is the false claim plus a **durable** failure mode: a bad same-size
entry fails dpkg on every run under that key, and `cannot_run`'s "Re-run the job." does not help.

**Fix (cheap, and the data is already in hand):** run `--print-uris` with `-o Acquire::ForceHash=SHA256` (executed:
the line then ends `SHA256:050ad79c…` instead of `MD5Sum:…`), and in the install step copy into
`/var/cache/apt/archives` only the restored files whose `sha256sum` matches their `--print-uris` line; drop the rest.
Then the claim becomes true by construction rather than attributed to apt.

### F2 — Medium — the 29-minute worst case omits the two cache steps, which have no bound — `ci.yml:143-145, 178-184, 273-278`
**Reasoned (from the YAML and the `actions/cache` documented defaults).** The budget sums the key step's 4 min and the
install step's 20 min plus ~5 min for the rest (measured: run 40397292037's `verify` took 5m45s in total, so the
remainder is ~5.3 min — 20 + 4 + 5.3 = 29.3, already tighter than "29"). Neither `Restore` nor `Save` has
`timeout-minutes`, and `actions/cache` v4's own segment download timeout defaults to 10 minutes
(`SEGMENT_DOWNLOAD_TIMEOUT_MINS`). A stalling cache backend therefore puts the job over 30 and it is CANCELLED — exactly
the backlog #343 shape (an external service consuming the job, every later check reporting nothing), moved from the
apt mirror to the cache service. The comment's arithmetic is presented as the bound and is not one.

**Fix:** `timeout-minutes` on both cache steps (e.g. 2), `continue-on-error: true` on both (a step that hits its own
timeout otherwise FAILS the job — see F3), `SEGMENT_DOWNLOAD_TIMEOUT_MINS` below the step cap, and re-derive the sum.

### F3 — Low — "ANY failure here leaves the key empty … the install runs exactly as it did before" is not true of the step's own timeout — `ci.yml:156-160`
**Reasoned.** The script's failures are all caught (`set +e`, `exit 0` on every path), but `timeout-minutes: 4` is a
step-level cap with no `continue-on-error`: if it fires, the step fails, the default `success()` condition skips every
later step **including the install**, and the job fails with a generic timeout rather than the CANNOT RUN wording the
comment block promises for every phase. Reaching it needs the 130s-bounded `apt-get update` to outlive SIGKILL or the
unbounded `--print-uris` to hang, so it is unlikely — but the sentence is absolute and the prompt's own question
("can a failed key step skip the INSTALL?") has the answer *yes, by this route*. Fix: `continue-on-error: true` on the
key step (and the two cache steps, per F2).

### F4 — Low — the key is not a hash of "file name, size and SHA256" — `ci.yml:155`, PR body step 1
**Executed (container; same apt series as the runner, but the runner's own `--print-uris` lines are not logged, so not
observed there).** apt 3.2.0's `--print-uris` prints `'<uri>' <file> <size> MD5Sum:<md5>`. The key is still exact in
practice (the filename carries the version, and the size and MD5 change with any rebuild), so this is a prose error,
not a collision risk. `-o Acquire::ForceHash=SHA256` (F1's fix) makes the sentence true.

### F5 — Low — the dependence is reduced, not removed: every package-set change is a full cold download — `ci.yml:178-184`
**Reasoned.** With no `restore-keys`, one updated package among the 81 (or a runner image that changes what is already
installed) misses the whole entry and refetches all 66.4 MB from the mirror that was crawling — the very condition the
comment says this "removes the dependence" on (`ci.yml:151-152`). A `restore-keys: ffmpeg-debs-` fallback would let apt
reuse the unchanged files and fetch only the changed one; it is only safe to add **after** F1's verification (a
prefix restore is a stale entry by definition), and the copy-back at `ci.yml:263` would then need to copy only the
files named in the current `--print-uris` set so the cache does not accumulate stale versions. Not blocking: the
owner's option A is an exact-key cache and works as specified; the prose overstates it.

### Checked and not a finding
- **Empty list / ffmpeg pre-installed:** `--print-uris` printing nothing → warning, key empty, cache steps skip,
  install runs (`ci.yml:171-175`). Executed in the container: `--print-uris` with every file already in archives also
  prints **0** lines — harmless here because the key step runs before the restore copy.
- **`--print-uris` as non-root:** works (container, executed; and CI printed 81 files without `sudo`).
- **Empty glob:** the restore uses `compgen -G` guard; the copy-back is `2>/dev/null || true`. On a miss the archives
  held exactly this run's downloads (66,349,826 B saved vs 66.4 MB fetched), so "unrelated packages" are not saved on
  this image.
- **PR-scope leakage:** a PR saves into its own scope; master pushes (the workflow runs on `push: master`) seed the
  scope every PR can read. `actions/cache/save` does run on `pull_request`; observed it saving in run 40397292037.
- **Hit-case speed:** 19s on the hit vs 11s on the (fast-mirror) miss — the hit is not faster on a good day, it is
  immune to a bad one. The PR's "short step" holds; nothing claims more.

## Summary
The mechanism works in CI in both directions. Not converged because its stated integrity guarantee is false (F1,
executed) and its stated time bound omits two unbounded steps (F2); both have small, specific fixes.

VERDICT: NOT CONVERGED
