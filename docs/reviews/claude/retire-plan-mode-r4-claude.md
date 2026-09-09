# Adversarial code review — ROUND 4, Claude half

## PROOF OF SUBJECT

```
$ git rev-parse HEAD
259dfa15816fecd03ffc22329b8ab3f7ca409e08

$ git log --oneline -1
259dfa15 Fold round 3 — the inert discriminator gets a consumer, not a deletion

$ git diff --stat f9d2c498..259dfa15 -- scripts/
 scripts/check-plan-code.py                  |   6 +-
 scripts/check-plan-file-tags.py             | 195 ++++++++++++++++++++++++----
 scripts/mutations/check-plan-file-tags.json |  42 ++++--
 3 files changed, 204 insertions(+), 39 deletions(-)

$ git status --porcelain     # before and after all work: empty
```

I read nothing under `docs/reviews/`. Every experiment ran in a `mktemp -d` copy.

---

## VERDICT: NOT CONVERGED — 1 Medium, 3 Low.

**Nothing here breaks the fence.** The live run is green over the real corpus, all 43 cases pass,
all 16 manifest entries kill via the case they name with the control green either side, and the
central item the coordinator asked about — `any(not f.unreadable …)` — is **correct on every
finding mix I could construct**. The Medium is about the new test scaffolding, not the guard:
`_drive_main` opens a door to the exact "crash instead of red" failure this file bans twice in its
own comments. The Lows are prose claims in the fold that do not survive measurement.

---

## F1 — Medium: `_drive_main` reintroduces the crash-instead-of-red shape the file bans twice

**Observation.** Before this fold, no case invoked `main()`, so a mutation could not make the suite
raise from production code. `_drive_main` calls `main([])` with no exception handling, so **any**
exception inside `main()` now propagates out of `self_test()` and terminates the suite: no
`[FAIL]` line, no `N/M self-test cases passed` line. `run_mutations` (check-plan-code.py:1219-1220,
1239) reads that as `rc == 1 → caught=True` with `fails == []`, and reports
`matched 0 red case(s) — it was caught by something else: []` — the reading this file calls "the
worse of the two readings" at `:338-343`, and that r3's own F3 fixed at `:499-504`.

Measured — a `raise` injected into `main()`'s findings path, in a temp copy:

```
  File ".../scripts/check-plan-file-tags.py", line 525, in self_test
    rc, out = _drive_main(tmp, "m1", {"p.md": "<!-- file: gen.py -->\n"})
  File ".../scripts/check-plan-file-tags.py", line 308, in _drive_main
    rc = main([])
  File ".../scripts/check-plan-file-tags.py", line 576, in main
    raise RuntimeError("injected: main() raised mid-case")
RuntimeError: injected: main() raised mid-case
RC=1
```

No summary line. No `[FAIL]`. Cases m2, m3, m4 never ran and were never reported.

This is latent, not live: I verified all 16 current entries are crash-free (see *What I ran*). But
`main()` reaches an unguarded index at `coverage_shortfall:194` (`sorted(…)[0]`, guarded only by
`if stray:`) and a narrow `except (UnicodeDecodeError, OSError)` at `audit:217` — a mutation to
either condition raises rather than reddens, and the file's whole discipline is to make that shape
impossible rather than currently-absent.

**Fix direction, measured working.** Convert the raise into a distinguishable return inside
`_drive_main`:

```python
try:
    rc = main([])
except Exception as exc:
    return -1, f"main() RAISED {exc!r}"
```

Same injected raise, with that change:

```
  [FAIL] a TAG finding gets the backticks remedy: got (-1, False, False) want (1, True, False)
  [FAIL] an UNREADABLE-only run gets the not-checked remedy, NOT the backticks one: got (-1, False, False) want (1, False, True)
  [FAIL] a MIXED run still gets the backticks remedy — a tag is present: got (-1, False, False) want (1, True, False)

40/43 self-test cases passed
```

Three named red cases and a summary line — exactly what the harness needs to attribute.

---

## F2 — Low: the `finally` restore is inert, and its stated reason cannot happen

**Observation.** `_drive_main`'s docstring says the restore is in a `finally` "because a raising
case must not leave the rest of the suite pointed at a temp directory that no longer exists."
Per F1, **there is no rest of the suite** — a raising case terminates it. The stated beneficiary
does not exist.

And the restore is unfalsifiable. Removing it entirely in a temp copy:

```
$ python3 $W/scripts/check-plan-file-tags.py --self-test   # `finally: pass`
43/43 self-test cases passed
RC=0
```

No case fails, because the four `_drive_main` cases are the last four in the suite and each sets
`ROOT`/`DOCS` itself. This is r3's own F1 shape — a mechanism nothing reads, carrying a stated
reason that is false — inside the fix for r3's F1.

**Fix direction.** F1's fix makes the restore *reachable* (the suite survives, so a stale global
could genuinely leak forward). To make it *falsifiable*, add one case after the `_drive_main`
block asserting `(ROOT, DOCS) == (Path(__file__).resolve().parent.parent, ROOT / "docs")` — or,
if the restore is to stay prophylactic, say so instead of naming a beneficiary that cannot exist.

---

## F3 — Low: the new header prose states something about round 2 that round 2 did not do

**Observation.** Lines 41-43, in the paragraph arguing that a false stated reason is dangerous:

> Round 2 accepted this same class as a finding (Cx-L1) and fixed it by dating the measurement —
> but only in `coverage_shortfall`'s docstring, so the instance a reviewer happened to open was
> repaired and the class was not.

Both halves are false. `coverage_shortfall`'s docstring contains no date, in either revision:

```
$ sed -n '148,172p' scripts/check-plan-file-tags.py | grep -n "2026-"
  NO DATE PRESENT

$ git show f9d2c498:scripts/check-plan-file-tags.py | sed -n '/^def coverage_shortfall/,/^    """$/p' | grep -n "2026-"
  (no match; the only measurement line is "MEASURED on this tree:", undated)
```

And round 2 added no dated line anywhere in the file:

```
$ git diff 6e5b2b78..f9d2c498 -- scripts/check-plan-file-tags.py | grep "^+" | grep "2026-\|Cx-L1"
  no dated line added by round 2
```

Every date in the delivered file was added either by `71f86f9a` (the original commit) or by this
fold. **Fix direction:** drop the sentence, or replace it with what round 2 actually did.

---

## F4 — Low: the fold corrected the count-drift instances r3 named and not the class in the same file

**Observation.** Line 44 makes a completeness claim: *"Both numbers in this header now carry the
date they were taken."* The module docstring runs `:2-96` and contains a **third** corpus-size
number, undated, which disagrees with the dated one 64 lines above it:

- `:15` — "2026-09-08 across 1,115 documents" (dated ✅)
- `:27` — "**19 documents on 2026-09-09**" (dated ✅, and I re-measured it as exactly 19 today)
- `:79` — "indistinguishable from the same sentence over **1,116**" (undated; today's count is 1121)

Outside the header, two more live-sounding numbers went stale when the suite grew 39 → 43 and were
not swept:

- `:443` — "Without this, deleting the rglob would pass **15/16**." The suite is 43 cases.
- `:156` — `--self-test rc=0   "29/29 self-test cases passed"`, undated.

`:86` (220 documents / 92 plans) I re-measured and both are still exactly right today
(220 non-review docs, 92 plans), so those are fine. **Fix direction:** either sweep the three, or
weaken `:44` from "both numbers in this header" to name the two it means. The file's own memory
line for this is *"After fixing, SEARCH for the class"*.

---

## Attack targets 1-7, answered

**1 — `_drive_main` mutating module globals.** The restore capture (`keep_root, keep_docs = ROOT,
DOCS`) is correctly **before** the `try`, and the swap is inside it — verified by reading `:303-310`
and by the temp-copy experiments above. `contextlib.redirect_stdout` does not interact with the
`case()` printer: `case()` is only ever called after `_drive_main` returns, outside the redirect.
Case order is not load-bearing today (the four are last, and each sets both globals itself). The
two real findings are F1 and F2.

**2 — is `any(not f.unreadable …)` right, not just covered?** Yes, on every mix. `audit` can only
produce two finding kinds: tag findings (`unreadable` defaults `False`, pinned by the case at
`:516`) and read failures (`unreadable=True`, `:220-221`). So `any(not f.unreadable …)` is exactly
"at least one tag is present", and `any` is the correct quantifier:

| mix | branch taken | correct? |
|---|---|---|
| tags only | backticks | ✅ the advice applies |
| unreadable only | NOT CHECKED | ✅ the C1 defect, fixed |
| both | backticks | ✅ — see below |
| neither | block not entered (`if findings:`) | ✅ |
| tag with `unreadable=True` | unreachable from `audit` | n/a |

I checked the mixed case by hand against the real entry point rather than assuming. The remedy
addresses only the tag, but the *per-finding* line above it already says
`could not be read, so it was NOT checked: …`, so nothing is hidden, and after the tag is fixed the
next run is unreadable-only and gets the NOT-CHECKED message. **Considered and not filed.**

**3 — did wiring it create a new inert thing?** Yes, one: the `finally` restore (F2), proved inert
by deleting it. Everything else the fold added has a killing edit that I ran:

| added thing | killed by | red cases |
|---|---|---|
| the `else` branch | entry 12 (`if True`) | exactly 1, the case it names |
| the `any` quantifier | entry 13 (`any`→`all`) | exactly 1, the case it names |
| case m1 (tag → backticks) | entries 6, 10, 14 | — |
| case m2 (unreadable → NOT CHECKED) | entries 6, 7, 10, 11, 12 | — |
| case m3 (mixed) | entries 6, 10, 11, 13, 14 | — |
| case m4 (clean tree, rc 0) | entries 6, 10 | — |
| `finally` restore | **nothing** | F2 |

**4 — the retargeted r2-H1 entry (index 11).** It now models its name — `visited.add(md)` moved to
after a successful read is literally the pre-r2 code. It kills its named case, **without crashing**:
`rc=1, caught=True, named=True, summary="…passed" present, traceback=False, redcases=3`. The two
extra red cases are m2 and m3, which is honest (moving the add makes `main()` return 2 on the
shortfall before the remedy prints).

**5 — the two-line anchor.** Unique (verified: no duplicate anchors across the 16 entries except a
pre-existing `FILE_TAG = …` shared by entries 3 and 4, which is not from this fold and which
`run_mutations:1191` would refuse only if it matched twice *within the file* — it does not). It is
more fragile than its sibling: rewording the `print("\nPlan mode was retired…` line orphans entry 13
while entry 12 survives. But orphaning **fails loudly** — `run_mutations:1199-1204` sets `ok=False`
with `anchor NOT FOUND — it was not applied, so its 'caught' verdict would be meaningless`.
Confirmed by rewording the line in a temp copy: entry 13 and only entry 13 reported not-found.
Coverage cannot shrink silently. **Not a finding.**

**6 — are the new numbers right?** Two of three yes, one class missed.
- **19 documents** — re-measured today: exactly 19 `.md` under `docs/` contain `<!-- file:`. ✅
- **8 of 9 / 0 of 9 separators** — re-measured by routing both readers through one `read_text` and
  comparing each against the real `check-plan-code.extract()`. Reproduced exactly, including the
  `\r` explanation: `\r` is the one where `extract()` itself returns `files=[]`, because
  universal-newline translation has already rewritten it. ✅

  ```
  sep      extract files    split(nl)  splitlines  disagree_split disagree_splitlines
  0x000b   ['m.py']         [2]        []          False          True
  0x000c   ['m.py']         [2]        []          False          True
  0x001c   ['m.py']         [2]        []          False          True
  0x001d   ['m.py']         [2]        []          False          True
  0x001e   ['m.py']         [2]        []          False          True
  0x0085   ['m.py']         [2]        []          False          True
  0x2028   ['m.py']         [2]        []          False          True
  0x2029   ['m.py']         [2]        []          False          True
  0x000d   []               []         []          False          False

  splitlines disagreements: 8 of 9
  split("\n") disagreements: 0 of 9
  ```
- **counts** — 43 cases, 16 manifest entries, `EXPECTED_MUTATIONS["…file-tags.py"] == 16`, declared
  sum 390 == `sum(EXPECTED_MUTATIONS.values())` == 390. All ✅.
- The misses are F3 and F4.

**7 — anything broken elsewhere?** No.
`check-selftest-counts.py` → `30 script(s) declare a count, every one verified by running it`.
`check-plan-code.py --self-test` → `229/229 passed`.
`check-ratchet-contract.py --self-test` → `22/22 passed`.
`check-docs.py` → `Documentation integrity OK`.
Live guard run → `plan-mode tags: 0 across 1121 documents under docs/`, rc 0.
The guard has real callers: `.github/workflows/ci.yml:166` (live) and `:169` (`--self-test`).

---

## What I ran

1. `git rev-parse HEAD`, `git log --oneline -1`, `git diff --stat f9d2c498..259dfa15 -- scripts/`,
   `git status --porcelain` (clean before and after), full `git diff` of the fold.
2. `python3 scripts/check-plan-file-tags.py --self-test` → 43/43.
3. `python3 scripts/check-plan-file-tags.py` (live, real corpus) → rc 0, 1121 documents.
4. Manifest integrity: 16 entries, 16 unique names, 16 unique edit-tuples, one pre-existing shared
   anchor identified and cleared.
5. **All 16 mutations applied and run**, in a `mktemp -d` copy of `scripts/` with `HOME` redirected
   to a temp dir, replicating `run_mutations`' own attribution rule
   (`l.strip()[7:].rsplit(": got ", 1)[0]` over lines starting `[FAIL] `) **and additionally
   checking for the `N/M self-test cases passed` summary line and for a traceback**, per the
   coordinator's rule 4. Control green before and after the sequence.
   Result: `16/16 entries killed via the case they name (no crash, summary present)`.
6. F1: injected a `raise` into `main()`; observed the traceback, absent summary, absent `[FAIL]`.
7. F1 fix: added the `try/except` to `_drive_main` with the same injected raise; observed three
   named `[FAIL]` lines and `40/43 self-test cases passed`.
8. F2: deleted the `finally` restore; observed 43/43 still green.
9. F3: `sed`/`grep` for dates in `coverage_shortfall`'s docstring at HEAD and at `f9d2c498`;
   `git diff 6e5b2b78..f9d2c498` for dated lines added by round 2; `git log -S` for the provenance
   of `1,115` and `1,116`.
10. F4/attack 6: re-measured the backticked-mention corpus (19), the 220/92 corpus split, and the
    separator disagreement across all nine, each against the real `extract()`.
11. Neighbouring gates: `check-selftest-counts.py`, `check-plan-code.py --self-test`,
    `check-ratchet-contract.py --self-test`, `check-docs.py`.
12. Attack 5: reworded the anchored `print` line in a temp copy and confirmed exactly one entry
    orphans, loudly.

## What I could NOT check, and why

- **`python3 scripts/check-plan-code.py --mutate .` in full — NOT RUN.** I ran a targeted per-entry
  equivalent (item 5). What that does **not** cover: the other 374 mutations across the other 32
  manifests; `stage_tree`'s `HARNESS_TREE` staging (I staged `scripts/` only — sufficient here
  because every case in this file builds its own temp corpus, and I proved the control green, but
  it would give a red control for the four guards that resolve their subject from the repo root);
  `mutate_delivered`'s cardinality reconciliation against `EXPECTED_MUTATIONS`; and the
  `Measured`/`NotMeasured` verdict construction. I did separately confirm the declared sum matches
  (390 == 390) and that `check-selftest-counts.py` is green. The coordinator states CI `verify` is
  green on this SHA; I did not independently verify that claim against GitHub.
- **Whether a *future* mutation triggers F1.** I proved the door is open and that none of the 16
  current entries walks through it. I cannot prove no future one will — that is the point of the
  finding.
- I did not exercise `main()`'s `not DOCS.is_dir()` branch (`:557`) through `_drive_main`; no case
  covers it and none is claimed to. Not a regression from this fold.

---

# DISPOSITIONS — folded 2026-09-09. All four accepted.

| # | Sev | Disposition |
|---|---|---|
| **F1** | Med | **ACCEPTED AND FIXED — and the coordinator was WRONG to dismiss it.** The coordinator filed this same shape as "pre-existing and inherent, not introduced by the fold" and declined to act. That fails on the fact this half identified: **before the fold, no case in this file invoked `main()`** — every case drove pure functions over an explicit root. The fold added the first four that call the entry point, so it genuinely enlarged the surface. "Inherent" was a justification for not fixing something fixable in four lines. `_drive_main` now returns `(-1, "main() RAISED …")`. Re-measured with an injected raise: **3 named `[FAIL]` lines + `41/44 self-test cases passed`**, no traceback — where before there was no summary and no `[FAIL]` at all. Guarded by a new manifest entry. |
| **F2** | Low | **FIXED, and F1's fix is what made it fixable.** With the suite surviving a raise, the `finally` restore acquires the beneficiary its docstring claimed. A new case — *"…and `_drive_main` RESTORES the module globals it swapped"* — is placed after the block as its only observer, plus a mutation that deletes the restore. The docstring no longer names a beneficiary that cannot exist. |
| **F3** | Low | **FIXED by deletion, and recorded as a correction rather than silently removed.** The claim that round 2 dated a measurement in `coverage_shortfall`'s docstring was false in both halves — verified independently: no date there at any revision, and round 2 added no dated line to the file at all. The header now carries the correction *and* names the mechanism: the claim came from round 2's REVIEW DOCUMENT rather than the code, which is the exact substitution this file exists to prevent, made in a paragraph about false stated reasons. |
| **F4** | Low | **FIXED, all four instances.** "Both numbers in this header" → the count is gone entirely (see Cx-L1). `1,116` → "a thousand", since the exact figure was never the point. `29/29` → a description. `15/16` → a description, with a note that the count moves. |

## Counts after the fold

Cases **44** (was 43) · manifest entries **18** (was 16) · `EXPECTED_MUTATIONS` entry **18**,
declared sum **392** (was 390). Rising, which is the permitted direction.
