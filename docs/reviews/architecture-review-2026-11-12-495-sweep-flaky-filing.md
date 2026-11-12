# Phase 6 architecture review — the sweep-flaky filing path (backlog #618)

- Subject: PR #564, branch `495-survivor-retry`, worktree head `6546cb63`.
- Read-only. Nothing was edited, committed, pushed or filed.
- Scope: `scripts/sweep-red-alert.py`; the FLAKY steps in `.github/workflows/ci.yml` (grep 1412, upload 1422-1430, download 1504-1510, alert 1514-1524); the re-run in `scripts/check-plan-code.py` (`rerun_snapshot` 2235, `rerun_fresh` 2263, `rerun_kill` 2291, the FLAKY branch 2496-2512).
- Read first: the round documents r1-r4 (coordinator, Claude, Codex), backlog #495, #617, #618, and ADR-0014. No ADR covers this path. ADR-0014 is touched lightly (F6).

## Verdict

**Yes. The defect class is structural, and one redesign removes it.** Four parts of the handoff are each a separate inference, and every finding so far sits on one of them:

| Part | What the consumer infers | Findings it produced |
|---|---|---|
| Text parse | a name from a human report line (marker + `FLAKY_TAIL`) | r2 X3; F1 below |
| File presence | "this shard was scanned" from "this file exists" | r2 X2; F3 below |
| Shard count | how many shards ran, parsed from the YAML text of `ci.yml` (`shard_count`) | r2 X2 fold; F2 below |
| Identity | the mutation name as a unique key | m3 (#617); F4 below |

The r3 M1 finding came from patching the presence part, and m2 is the coupling between the presence and count parts.

The harness already holds the true data. The re-run sets a structured flag (`ev_muts[-1]["flaky"] = True`, check-plan-code.py:2504). It then flattens that flag into prose (2505), and the workflow re-parses the prose with a second copy of the marker (ci.yml:1412). The redesign moves the machine interface off the prose.

## Findings

### F1 — HIGH (fail-OPEN). The grep literal in `ci.yml` is tied to nothing; if it drifts, every FLAKY name is lost silently
- **Where:** `.github/workflows/ci.yml:1412`, `grep -F 'mutation FLAKY — ' ... > shard-$SHARD_INDEX.txt`.
- **The marker exists in three copies:**
  - the producer, check-plan-code.py:2505;
  - the consumer, sweep-red-alert.py:46 (`FLAKY_LINE`);
  - the grep literal at ci.yml:1412.

  The self-test pins the producer against `FLAKY_LINE`. Nothing pins the ci.yml literal.
- **Reproduced:** I copied the scripts and `ci.yml` to the scratchpad and replaced the em dash with `-` in the grep literal. Result: `sweep-red-alert.py --self-test` still passes 33/33.
- **What happens on CI:** every shard's grep finds no match (rc 1, which the step accepts at 1413-1416). Every `shard-<i>.txt` exists and is empty. `read_flaky` returns `([], [])`, measured. `main` then prints "no FLAKY mutation in this sweep" and exits 0.
- **Why it matters:** this is the "a scan that found nothing reads as no FLAKY" defect that r2 X2 was about. That fold closed it for a missing file, not for an empty one.
- **Fix:** a redesign (R1). Patching it would mean a fourth copy of the literal plus a pin.
- **Not in #617.** #617's m2 covers the file name and `merge-multiple`, and both of those fail CLOSED.

### F2 — MEDIUM (fail-OPEN). A shard file beyond the parsed count is never read
- **Where:** sweep-red-alert.py:110 reads `files = [... f"shard-{i}.txt" for i in range(shards)]`, with `shards` coming from `shard_count`, which parses only the `shard: [...]` line (89-98).
- **How a shard gets past the count:** the shard index is `strategy.job-index` (ci.yml:1370). A matrix grown any other way — an `include:` entry, or a second matrix axis — produces jobs whose index is at or above the count.
- **Measured:** with `shard-0..2.txt` empty and `shard-3.txt` holding a FLAKY name, `read_flaky(d, 3)` returns `([], [])`. The name is dropped and nothing is reported missing.
- **The deeper issue:** the consumer learns N from YAML text instead of from the producers. `strategy.job-total` (ci.yml:1371) is the real count, and it is already passed to the harness.
- **Fix:** a redesign (R1). Each record states its own `index/total`.

### F3 — LOW (fail-OPEN, rare). A file proves the grep ran, not that the log was complete
- **Where:** `RC=${PIPESTATUS[0]}` (ci.yml:1411) takes the harness's exit code. `tee`'s exit code is never read.
- **Failure:** if `tee` hits a write error (for example a full `$RUNNER_TEMP`), the log is truncated. The grep then exits 0 or 1 on the partial log, and the file reads as a complete scan.
- **Fix:** a redesign (R1). The record is written by the harness itself, atomically, and carries `complete`. Its presence then means the scan finished.

### F4 — MEDIUM (already filed as #617 m3; confirmed, and it is structural). A mutation name is not an identity
- **Measured:** 4,670 entries, 4,662 distinct names. 6 names are shared, by 2 or 3 manifests each, and every shared name targets a different file. Example: `the main session is gated too` belongs to both `check-agent-long-call` and `check-agent-large-read`.
- **Effect:** `flaky_names` (sweep-red-alert.py:76) collapses two such names into one. Measured: two lines in, one name out. The FLAKY line (check-plan-code.py:2505) carries no file, so the issue cannot say which script has the weak case.
- **The real key:** within one run, each mutant belongs to exactly one shard. The de-duplication therefore only ever merges DISTINCT mutants. It never removes a true duplicate.
- **Fix:** a redesign (R1). The record carries the key `(manifest, file, name)`.

### F5 — LOW (a second consumer of the same text contract)
- **Where:** `scripts/batch-ci.py:540-543`, `failures`, drops every log line containing `"mutation FLAKY — "` (a fourth copy of the marker). It then matches `— <name>: ` against the prose to find failures.
- **Why it is the same class:** report prose is used as a machine interface. Its r1 Codex 5 defect (a FLAKY line read as a failure) came from that.
- **Status:** outside #618's scope. R1's record would serve batch-ci too, but adopt it there separately.

### F6 — LOW. `main` reads the module global `WORKFLOW` (sweep-red-alert.py:49 and 148)
- **The rule:** ADR-0014 says a guard's `main` takes its world as a parameter.
- **What happens instead:** the self-test copies the script and `ci.yml` into a fake repo to steer that global (352-361).
- **Fix:** R1 deletes `shard_count` and the global with it. No separate fix is needed.

### F7 — LOW / a decision for the owner, not a defect. FLAKY is filed only from master full sweeps
- **Where:** the upload, download and alert steps are skipped on `pull_request` (1423, 1505, 1515). `batch-ci` discards FLAKY lines (F5).
- **Effect:** most sweeps run on PRs and batches. A FLAKY seen there is named in that run's log and tally line (check-plan-code.py:2627), then it is gone unless master happens to reproduce it.
- **The owner's wording:** backlog #495 says "named in the output and in the summary line". "Filed" is the r1 reviewers' reading of the owner's 11-11 19:25 sentence.
- **For the owner:** is a PR-observed FLAKY meant to be filed as well? R1 makes that cheap, because a PR's records can be read the same way. It does not need deciding to land R1.

### F8 — LOW (survivor-retry, noted only). A first-run survival caused by earlier mutants' leftovers reads as FLAKY
- **Cause:** a mutant's first run shares `d` with earlier mutants (the `seed_trees` exposure, which the docstring at 2249-2250 states as a bound). Its re-run is in a fresh snapshot.
- **Effect:** a case that is deterministic in a clean tree, but was masked by contamination, comes back FLAKY with the advice "make the case deterministic". The not-red outcome is defensible, since the mutant is killable. The diagnosis is wrong.
- Also noted, as cost rather than correctness: the number of re-runs has no cap (no `MAX_RERUN` or similar in check-plan-code.py). A suite that goes always-green turns N survivors into 2N suite runs. That can push a shard into a budget stop, which replaces N clear SURVIVED lines with a NOT MEASURED tail.

## Recommended redesign (R1): the harness writes a structured shard record; the alert reads only records

**Producer: check-plan-code.py.** A new flag, `--record <path>`, written once at the end of `main` from `verdict.mutations` / `ev_muts`. The write is atomic: a temp file, then `os.replace`. The record looks like this:

```json
{"schema": 1, "shard": 4, "total": 38, "complete": true, "declared": 123,
 "flaky":    [{"manifest": "scripts/mutations/x.json", "file": "scripts/x.py", "name": "...", "by": ["case"]}],
 "survived": [...], "nondeterministic": [...]}
```

- `complete` is false on a budget stop or a `NotMeasured`. If the harness is killed, no record is written.

**One schema module, for example `scripts/sweep_record.py`.** It holds `write`, `read`, and the field list. The harness and `sweep-red-alert.py` both import it, so there is one copy of the contract and no literal to drift (F1).

**ci.yml.**
- The shard step passes `--record "$RUNNER_TEMP/sweep-record/shard.json"`. The `grep`, its rc handling (1412-1417) and the `mkdir` go.
- The upload stays, with `if-no-files-found: error`.
- The download may keep `merge-multiple: true` or drop it, because the reader globs `**/*.json` and identifies each record by its contents, not by its file name. That removes #617 m2.

**sweep-red-alert.py.** `read_records(dir)` works as follows:
- Parse every `*.json` file. A parse or schema error is NOT RUN for that file.
- Take `total` from the records, and require them all to agree.
- Report `missing = {0..total-1} − {indices present}`, any index outside that range (removes F2), and any duplicate index.
- Report `incomplete` = records with `complete: false`.
- Then apply today's ordering, which stays: file the FLAKY entries from the present records first, then go red naming the missing and incomplete shards.
- Each issue line is keyed `file: name` (removes F4 and #617 m3).
- If no record is present, the count is unknown, so the result is NOT RUN. That is the same outcome as today, without parsing YAML.

**What it deletes:**

| Removed | Where |
|---|---|
| `flaky_names`, `FLAKY_LINE`, `FLAKY_TAIL` | sweep-red-alert.py |
| `shard_count` and the `WORKFLOW` global's use in `main` | sweep-red-alert.py |
| The fixed-name `shard-<i>.txt` loop | sweep-red-alert.py |
| The self-test cases for the tail, the matrix line, and the producer's print shape | about 8 of the 33 |
| The mutation pins on the above | about 8 of the 23 |
| The grep block | ci.yml |

The human report line at check-plan-code.py:2505 stays as prose for people and stops being an interface.

**What it does not remove:**
- The artifact handoff itself. A matrix cannot hand data to a downstream job any other way: job `outputs` from a matrix keep only the last writer.
- Missing records still mean NOT RUN, exactly as today.

What changes is that completeness is proved by the producers' own statements, not inferred from file names, a YAML count and a grep exit code.

**Producer–consumer tie (removes the "a pin on a copy" pattern).** One self-test case runs the real harness `main` on a fixture that FLAKYs, with `--record`, and feeds the written file to `read_records`. Only the harness's own output ever reaches the reader, so no hand-written fixture stands in for it.

**Rejected alternative (R2): each shard files its own names.**
- It removes the aggregation, but gives `issues: write` to jobs that execute mutated code. `actions/checkout` persists the job token in `.git/config` by default.
- It also races: N shards each do `issue list` then `issue create` with no atomicity. Today the concurrency group (ci.yml:35-37, `cancel-in-progress` false on master) serialises master runs, so the single aggregator never races.
- Missing or NOT RUN shards would still need an aggregator.

## Checked and found sound

- `sweep-red-alert.py --self-test`: **33/33 passed** (run on this worktree).
- Order in `main` (142-160): the red alert comes before the FLAKY read, so a FLAKY failure cannot cost a red sweep its issue. Present names are filed before the missing-file raise. Nothing is filed when files are missing and no name was read. This matches Codex r4's driven table.
- The alert job's step conditions (1505, 1515, `!cancelled()`, no `success()`): the download and alert still run after the aggregate step goes red. The download is not `continue-on-error`.
- `merge-multiple: false` or a renamed upload artifact: the shard files are missing, so the result is NOT RUN (fails CLOSED). I confirmed the self-test stays green under an upload-name mutant (it does not cover it, as #617 m2 says), and that the outcome is a red step, not a silent pass. Note: I did not verify that download-artifact@v4 accepts a zero-match pattern without erroring; either way the step goes red.
- `rerun_kill` (2291-2323) holds a re-run kill to the first-run rule, plus a completed summary line, plus no seed split. The re-run tree is a dereferenced snapshot (2253-2260). I found no route from a crash or an unrelated red to FLAKY.
- Hazard scan of the manifest names: no name contains a newline, `mutation FLAKY — ` or `FLAKY_TAIL` (4,670 entries scanned), so the tail parse is sound for today's corpus. F1 is about the copies of the marker, not the names.
- The concurrency group serialises master runs, so two alert jobs cannot both create a `sweep-flaky` issue.

## Bound of this review

- Static reading plus the measured probes above.
- No CI run was triggered.
- GitHub Actions timeout and `cancelled()` semantics for a timed-out matrix job are taken from the round-3 record, not re-verified.
- The scratchpad copies used for the mutants are under `.../scratchpad/p618/`.
