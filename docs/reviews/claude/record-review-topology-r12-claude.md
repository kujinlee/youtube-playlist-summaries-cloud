# record-review-topology — round 12, Claude half

Subject: worktree `/Users/kujinlee/code/agentic-ai-docs/.yps-worktrees/review-topology`, branch
`record-review-topology`, HEAD `dc9fe107` **plus the uncommitted delta**, which is the shipping
state. Everything below was run from an isolated `cp -R` with its `.git` pointer file deleted
(asserted gone before anything ran); no git command was run with a `GIT_*` variable exported, and
no mutating git ran anywhere.

**The r11 Blocking repair works, and I verified it by execution: all 44 entries across both
manifests are now ATTRIBUTED, over green controls, yielding a `Measured` verdict.** The defect I
found is the one the brief predicted — the fix is an instance, and the class is still open **in the
same function, 21 lines above the fix**.

---

## Blocking

None.

---

## High

### H1 — `codex-review.py:907` still prints `got={got}`: the printer fix landed on one of the file's TWO `[FAIL]` printers, leaving 17 of its 79 printed cases unattributable

**Claim.** The r12 delta fixed `chk`'s printer at `:928` and left the sibling printer at `:907`
emitting the exact broken shape the round exists to repair — so the entire `classify` half of
`codex-review.py`'s self-test, the half that decides whether a review gate ran, remains invisible to
`parse_fail_names`.

**Evidence.** Both printers are inside `self_test()`, 21 lines apart:

`scripts/codex-review.py:907` — untouched by the delta:
```python
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got={got} ({reason})")
```

`scripts/codex-review.py:928` — the delta:
```python
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got {got!r} want {want!r}")
```

The consumer, `scripts/check-plan-code.py:1475-1476`:
```python
    return [l.strip()[7:].rsplit(": got ", 1)[0].strip()
            for l in out.split("\n") if l.strip().startswith("[FAIL] ")]
```
and attribution at `scripts/check-plan-code.py:1254`:
```python
        unnamed = [(w, [f for f in fails if w == f]) for w in wants]
```
`": got="` does not contain `": got "`, so the `rsplit` never fires and `w == f` can never hold.

**What makes this a High rather than a Low.** The delta's own comment, `scripts/codex-review.py:919`,
states the claim for the whole file:

```
        # ⛔ THE CANONICAL LINE, AND IT USED TO BE `got={got!r}` — r11 Blocking (Codex half).
```

and `docs/reviews/coordinator/record-review-topology-r11-coordinator.md:46` records it as settled:
*"The printer is now canonical."* Both sentences are false about `scripts/codex-review.py`. This is
the branch's own recorded failure mode — fixing the instance and calling it the class — committed in
the round whose brief names that question as the highest-value one.

It also lands on a file that **just left the manifest-debt list**. `scripts/check-ratchet-contract.py:337`
now reads `codex-review.py … debt PAID 2026-09-14`, and `:374-375` records the removal. The debt is
recorded as paid while 21.5% of the file's cases cannot be measured at all.

**Concrete failure scenario.** Any future mutation aimed at `classify()` — the function that decides
`OK` / `TRY_NEXT`, i.e. whether the adversarial review gate ran — is killed by its case and reported
by the harness as `matched 0 red case(s) — it was caught by something else: [<garbled names>]`. The
entry is unattributable, `ok` is False, and `--mutate .` reds with a message pointing at the expect
rather than at the printer. The nine entries shipped today all target `chk` cases, so this is latent,
not a live break — which is precisely how the `:928` defect survived for as long as it existed.

**Verified by execution.** Forcing exactly one `classify` case red, without touching the printer:

```
$ python3 scripts/codex-review.py --self-test | grep FAIL
  [FAIL] r7: a REAL review that never names the output path still passes: got=ok (478 chars)

$ # what parse_fail_names makes of that line
PARSED NAME: 'r7: a REAL review that never names the output path still passes: got=ok (478 chars)'
```

Note the tail carries a run-dependent `(478 chars)`, so even a hand-transcribed `expect` would be
brittle as well as wrong.

Then the whole population, by swapping the marker on the green run and parsing it:

```
cases seen: 79
DUPLICATE parsed names: none
names still carrying a got-tail: 17
    'unsupported model — no message written: got=try_next (CLI reported HTTP 400)'
    'successful review: got=ok (323 chars)'
    'empty message file — the silent no-op: got=try_next (final message was only 0 chars …)'
    'timeout, no message: got=try_next (timed out — any partial message is an incomplete review)'
    'codex missing: got=try_next (CLI wrote no final message (exit 127))'
    'v3-High: TIMED OUT with a long partial message must NOT pass: got=try_next (…)'
    'r7-Blocking: a final message that NAMES ITS OWN OUTPUT FILE is a report, not a review: got=… '
    … 10 more
```

**17 of 79.** By contrast, the fixed `chk` half is clean — see the coverage section.

**Fix.** One line, same shape as `:928`:
```python
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got {got!r} want {want!r} ({reason})")
```
`({reason})` after `want` is safe: `parse_fail_names` truncates at the LAST `": got "`, which is
still the one this line writes, and `reason` contains no `": got "` (verified across all 17 cases
above). Put it in the same commit as the `:928` fix, and make the comment at `:919` say *both*
printers.

---

## Medium

### M1 — `codex-review.py:1249` counts 13 self-test cases that have no assertion behind them and print nothing; `check-selftest-counts.py` structurally cannot see it

**Claim.** The suite's declared total of 92 is inflated by a bare literal. 13 of the 92 cannot fail,
cannot print a `[FAIL]` line, and correspond to no assertion I could find.

**Evidence.** `scripts/codex-review.py:1249-1252`:
```python
    extra += 13

    total = len(cases) + extra
    print(f"\n{total - failures}/{total} passed")
```
`extra` is otherwise incremented once per `chk` call (`:917`). Measured by instrumenting the total:

```
DIAG cases=17 extra=75
92/92 passed
```

So `75 = 62 chk calls + 13`, and `92 = 17 + 62 + 13`. The suite prints exactly **79** per-case
lines. `failures` is incremented at exactly two sites in the file, both inside the two printers
(`:909`, `:930`) — so nothing else in `self_test()` can register a failure. I state that as what I
could not find, not as a claim about intent.

**Why the guard cannot catch it.** `scripts/check-selftest-counts.py:283-306` (`printed_total`) reads
the denominator of the suite's own `N/M … passed` line and compares it to the `--self-test  # N cases`
declaration in the same file's source. Both numbers are authored by the subject. A literal added to
`extra` moves them together, so the gate stays green on a count that is 14% fiction — the
declared-count-drift class this project has already paid for three times, one layer in.

**Provenance.** `git log -S"extra += 13" -- scripts/codex-review.py` → `dc9fe107`; the diff shows
`- extra += 8` / `+ extra += 13`. The idiom predates this branch, but r11's fix grew it, and
`check-selftest-counts.py:126` pins the inflated number. Not on the do-not-refile list and not raised
in either r11 half.

**Fix.** Either delete the literal and let `total` be `len(cases) + chk_calls`, adjusting the pinned
92 in the same commit, or give the 13 real `chk` calls so they can go red and print a name.

---

## Low

### L1 — the duplicate-anchor refusal compares exact tuples, so the repair satisfied it by splitting one expression into two disjoint substrings

`scripts/check-plan-code.py:966-968` refuses `anchors in seen_anchors` where
`anchors = tuple(f for f, _ in e.get("edits", []))` — **exact tuple equality**. The r12 repair for
`check-review-recorded.json` entries 24 and 25 replaced two identical full-line anchors with
`"(set(after) | set(reviewed))"` and `" & set(branch_delta))"`, which are two non-overlapping
substrings of the *same* return line (`scripts/check-review-recorded.py:327`). For
`codex-review.json` entries 4 and 5, entry 5's anchor `'f"{parts[1]} {parts[3]}"'` is a strict
substring of entry 4's.

Here that is legitimate and I verified it by execution — both pairs mutate genuinely different
behaviours and both were attributed (see coverage). But the rule's stated reason, *"it measures
nothing new"*, is not the property it tests: a pair aimed at the same behaviour can clear it by
shortening one anchor. The property is actually carried by the exact-`expect` rule at `:1254`, which
is the thing that would catch it. Worth a sentence in the comment at `:954-968` so the anchor rule is
not read as doing work it does not do.

---

## What I verified, and how

**Everything in this section was run, not read.** Driver:
`mutate_delivered()` imported from the isolated copy's own `check-plan-code.py`, with
`load_manifests` filtered and `EXPECTED_MUTATIONS` narrowed to one target at a time — the real
staging, real `child_env` `$HOME` redirect, real before/after controls, real `run_mutations`.

| Question (brief) | Result |
|---|---|
| **1.** Does any anchor occur more than once in its target? | **No.** Every new anchor: count `1`. Measured with `str.count` on both targets. |
| **1.** Does any entry repeat another's anchor tuple? | **No.** `mutate_delivered` reached the mutation loop, and `declared == len(mutations)` held (9/9, 35/35), so nothing was refused or skipped. |
| **1.** Does each `expect` equal EXACTLY ONE red case under the real `parse_fail_names`? | **Yes — 44/44 `attributed: True`.** |
| **1.** Did making the anchors distinct make one vacuous? | **No.** Entry 24 `(set(after) \| set(reviewed))` → `set(after)` yields `sorted(set(after) & set(branch_delta))` — exactly the pre-union code. Entry 25 ` & set(branch_delta))` → `)` yields `sorted((set(after) \| set(reviewed)))` — exactly the pre-intersection code. Both caught, both attributed. |
| **2.** Is the canonical line exactly right? | **Yes for `chk`.** Forced all 62 `chk` cases red: 62 names parsed, **0** carrying a got-tail, **0** duplicates — so `w == f` and `len(m) == 1` both hold for every case in that half. |
| **2.** Does anything else parse that suite's output? | **Only `check-selftest-counts.py`**, which reads the `N/M … passed` line — untouched. `check-fixture-variation.py` reads parameters, not output: `OK — 506 parameter(s) across 50 file(s)`. Nothing else in `scripts/`, `.github/workflows/`, or `.claude/hooks/` reads it. |
| **2.** Is debugging information lost? | **No.** The removed `expected {want!r}` line is subsumed — `want` now appears on the same line, and `got` is unchanged. |
| **3. THE CLASS** | **Swept all 44 manifests against their targets' failure printers. Exactly one is broken: `codex-review.py:907` (H1).** |
| **4. Regression** | **Clean.** `git status --porcelain` → 3 modified, all under `scripts/`; the 3 untracked files are the r11 codex/coordinator docs and verdict. `git diff -- scripts/` has exactly one hunk in `codex-review.py`, `@@ -916,9 +916,17 @@`, inside `chk`. `reviewed_state`, `unredirected`, `verdict_record` and every self-test case are byte-identical to `dc9fe107`. |

### The class sweep, in full

For each of the 44 files in `scripts/mutations/`, I located its target's `[FAIL]` printer and
classified it against `parse_fail_names`' two clauses. Grouped by shape:

- **canonical `[FAIL] {name}: got {x!r} want {y!r}`** — the majority. Parses.
- **`[FAIL] {name}: got {x!r}, want {y!r}`** (comma) — `check-backlog-closure.py:237`,
  `check-group-claims.py:278`, `check-storage-independence.py:344`. The `rsplit` fires on `": got "`
  regardless of what follows. Parses.
- **`[FAIL] {name}` with no got** — `check-selection-card.py:542`, `gen-backlog-page.py:3273`,
  `gen-goals-page.py:809`, `brief-compose.py:966`. No `": got "`, so the whole tail is the name.
  Parses.
- **name on its own line, detail on continuation lines** — `check-ratchet-contract.py:721/726/731/736`,
  `gen-dashboard.py:1457`. Only line 1 starts with `[FAIL] `. Parses.
- **assembled marker** — `check-handoff-path.py:109` (`f"  [{'ok' if ok else 'FAIL'}] …"`),
  `check-storage-grant-pin.py:151` (`f"  {'ok  ' if ok else '[FAIL]'} …"`). Both render to
  `[FAIL] {name}: got …` after `.strip()`. Parses. (These are two of the four the abandoned static
  pre-flight false-positived on — see below.)
- **not printed directly** — `page_markup.py:273` appends to `failures`, printed at `:422-423`.
  Parses.
- **per-row, plus a conforming self-test printer** — `check-producer-enumeration.py:184-217` are
  main-path row reports, not cases; its self-test printers at `:271/281/293/302` are canonical.
- **one unattributable-but-harmless case** — `coverage_verdict.py:273` prints
  `[FAIL] H1 clause 1 has no default…: constructed without controls_green` with no `": got "`, so
  the name parses as that whole string. No manifest entry names it (all six `coverage_verdict.json`
  expects are short `chk` labels), so nothing depends on it.
- **BROKEN** — `codex-review.py:907`. **H1.**

I also checked the inverse hazard flagged in `parse_fail_names`' own docstring — a case name that
itself contains `": got "`, which would be silently truncated. Across all 44 manifests, **zero**
`expect` values contain it.

### On the abandoned pre-flight

`scripts/check-plan-code.py:3088-3136` records that a static guard for this contract was attempted
and **deliberately abandoned**, because `"[FAIL] " in source` is unfalsifiable (the explanatory prose
satisfies it) and `print(...[FAIL] ...)` false-positives on four conforming files. I am **not**
re-filing that decision — it is reasoned, measured, and correct. H1 is not a request for that guard;
it is a live instance the human sweep the project chose instead did not perform on the file it was
fixing.

### Suites run on the shipping tree (isolated copy)

```
codex-review          rc=0  92/92 passed
check-review-recorded rc=0  117/117 passed
check-plan-code       rc=0  128/128 passed
check-ratchet-contract rc=0 self-test: 41/41 passed
check-selftest-counts rc=0  18/18 self-test cases passed
check-guard-coverage  rc=0  37/37 passed
check-fixture-variation  OK — 506 parameter(s) examined across 50 file(s)
```

### Mutation runs (isolated copy, real harness)

```
scripts/codex-review.py            declared 9   ok: True   verdict: Measured   9/9 ATTR
scripts/check-review-recorded.py   declared 35  ok: True   verdict: Measured   35/35 ATTR
```

Both with green before- and after-controls; no survivors, no unmeasured entries, no report lines.

**Claims I did not verify by execution:** the intent behind `extra += 13` (M1 states only what the
arithmetic shows and what I could not find); and I did not run `--mutate .` over all 618 mutations —
the coordinator has one in flight, and the two changed manifests were run in full instead.

---

## Verdict

H1 is the class left open inside the instance's own function, in the round whose brief names that as
the question to answer, and it is asserted as closed by both the code comment and the r11
coordinator document. It is a one-line fix.

VERDICT: NOT CONVERGED
