<!-- codex-review: model=gpt-5.5 -->

> **Editor's note — read before the findings.**
>
> **Subject:** plan **v4** (`619244e`). This is the Codex half of round 4, dispatched after round 3's
> Codex half was found never to have run.
>
> ⛔ **WHY ROUND 3's CODEX HALF DID NOT RUN — root cause, established by contrast, not guessed.**
> Round 3 used ONE shared brief for both halves, whose Output section said *"Write to the review path
> you were given."* That is right for the Claude subagent, which writes files, and **wrong for
> Codex**: `scripts/codex-review.py` captures the agent's FINAL MESSAGE
> (`codex exec --output-last-message`) and writes `--out` itself, only inside its success branch. So
> the agent dutifully wrote the file, its final message became *"I wrote the review to …"*, and the
> wrapper correctly rejected it — *"the final message NAMES ITS OWN OUTPUT FILE … a report of having
> written a review, not the review"* — four models in a row. **The wrapper never wrote the file at
> all; every version on disk came from the agents' own writes, each overwriting the last**, which is
> why the verdict flipped from NO to YES between reads.
>
> **The control:** round 2's brief, same wrapper and same model ladder, has an Output section that
> never mentions writing anything — and it captured cleanly. One sentence was the whole difference.
>
> ⛔ **AND I DID NOT NOTICE**, because the invocation ended `…; echo "WRAPPER_RC=$?"`, so the
> completion notification reported the *echo's* status. `WRAPPER_RC=1` sat in the log unread. That is
> the `$?`-after-the-wrong-command trap this repo has measured three times.
>
> **Three fixes, all in this dispatch:** the brief now states *your final message IS the review, write
> no file*; `--out` points OUTSIDE the repository, so a direct write cannot clobber a committed
> artifact and the file reaches `docs/reviews/` only when the wrapper reports success; and the exit
> code is captured on its own line. **This run: `WRAPPER_RC=0`, captured via `gpt-5.5`, and nothing
> touched `docs/reviews/` — verified by checksum.**
>
> The round-3 artifact of uncertain provenance is preserved as
> `plan-project-dashboard-r3-codex-STRAGGLER.md` rather than deleted. Its findings were independently
> confirmed by the Claude half and by `check-plan-code.py`, so the v4 fixes stand — but it was not a
> captured gate and is not evidence of one.
>
> REVIEW GAP: claude — round 4's Claude half has NOT run. The user asked specifically for the Codex
> half to be re-dispatched against v4. **v4 therefore has ONE confirmed reviewer, not two, and this
> round is not a convergence signal.** Round 3's Claude half (2B/4H/7M/7L) reviewed v3 and is folded
> in; nobody independent has read v4's fixes for those findings.

READY TO EXECUTE: NO

Must change:
1. Fix `_ordered()` for consecutive malformed blocks.
2. Either tag/remove/relabel the untagged Task 5 Python block, or stop claiming every Python block is assembled.
3. Fix Task 6 Step 5’s gate-hidden falsifier expectation.

Plan checker baseline I ran:

```text
15/15 passed
```

```text
scripts/check-dashboard-entry.py  4 blocks assembled -> 45/45 passed
scripts/gen-dashboard.py      8 blocks assembled -> 77/77 passed
mutations declared and run: 25, caught 25
OK — 2 file(s), 25 mutation(s), 0 survivor(s)
```

Task 1 Step 6 controls A-F, run from assembled scratch code:

```text
A rc=1
B rc=0
C rc=1
+## not-a-date
D rc=1
E rc=0
  ## 2026-08-28-foo                rc=1
  ## 2026-08-28.                   rc=1
  ## 2026-08-28 [needs-yo]         rc=1
  ## 2026-08-28 rambling title     rc=1
  ##2026-08-28                     rc=1
```

High — “a malformed block stays adjacent to its file neighbours” / “immediately after whichever of its two file-neighbours renders FIRST.”
What I checked: assembled `scripts/gen-dashboard.py`, `_ordered()` with malformed first, last, consecutive, entirely malformed, same-date ties, and both file orderings.
Actually true: consecutive malformed blocks reverse relative order when they share the same rendered anchor.

```text
two consecutive malformed middle appended => ['Newer.', 'ERR:Bad two.', 'ERR:Bad one.', 'Older.']
```

This is exactly the “several consecutive” splice case v4 asks reviewers to test, but there is no declared mutation for preserving malformed-file-order within a run. VERIFIED.

High — “Every Python block below is tagged with the file it belongs to and is assembled, run and mutated by a script.”
What I checked: Python fence scan plus `scripts/check-plan-code.py` extraction.
Actually true: the plan has 13 Python fences, but the checker extracts 12 tagged blocks. The untagged one is Task 5 Step 3 at line 1433.

```text
python fence at line 1433, previous line 1431: of `function restoreDetails()`:
files extracted: ['scripts/check-dashboard-entry.py', 'scripts/gen-dashboard.py']
block counts: {'scripts/check-dashboard-entry.py': 4, 'scripts/gen-dashboard.py': 8}
problems: []
python fences total: 13
tagged python blocks extracted: 12
```

So the v4 assembly machinery still cannot see one Python block. VERIFIED.

Medium — “with the gate file moved away, [no_entry_prs] must print `no-entry: None err: could not load …`.”
What I checked: assembled `scripts/gen-dashboard.py` with `scripts/check-dashboard-entry.py` renamed away.
Actually true: import fails before `no_entry_prs()` can run or return `(None, err)`.

```text
Traceback (most recent call last):
  File "/tmp/dashboard-plan-r4-review/assembled/scripts/gen-dashboard.py", line 37, in <module>
    _GATE = _gate_module()
...
FileNotFoundError: [Errno 2] No such file or directory: '/tmp/dashboard-plan-r4-review/assembled/scripts/check-dashboard-entry.py'
rc=1
```

This fails loud, which is good, but the stated falsifier output is unreachable as written. VERIFIED.

Checked and did not file:
- `fetch-depth: 0` shape with slash base ref: full-history checkout produced `origin/release/one rc=0` and ratchet `rc=1`; shallow-plus-bespoke-fetch reproduced `fatal: origin/release/one...HEAD: no merge base`, `rc=2`.
- `resolves` as list: two flags, three flags, duplicate, and self-plus-valid behaved as expected.
- `check-explainer-delivery.py --self-test`: `8/8 self-test cases passed`.
- `brief-compose.py --self-test`: `30/30 passed`.
- `check-docs.py`: `Documentation integrity OK`.

NOT RUN: browser/manual affordance probes, real GitHub PR red/green CI observation, and live reload fold behaviour.

NOT CONVERGED
