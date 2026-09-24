# observer-log-owner — round 1, Claude half

**Branch:** `observer-log-owner` (staged, uncommitted — `master...HEAD` is empty; everything below is
measured against `git diff --cached`).
**Subject:** backlog #166 + #170 + #168 + #169 — `scripts/observer_log.py` as the ONE owner of the
observer-log record grammar, three producers rewired onto it.
**Verdict: NOT CONVERGED.** 2 Blocking, 3 High, 4 Medium, 2 Low.

⛔ **The headline is not any one defect. It is that the gate which would have found most of them
never executed on this branch, and the slice was reported as green anyway.**

Everything below was produced by running code. Probe scripts are reproduced inline so each
measurement can be re-taken.

---

## What passes

Stated explicitly rather than padded — these were attacked and held.

| Attacked | Result |
|---|---|
| `col()` strictness — a value that still breaks the record | **None found.** `\t \n \r \r\n \v \f \x1c \x1d \x1e \x85    ` all flattened. The only escape is an *encoding* failure, not a structure break (Medium 6) |
| `record()` sanitising `when` corrupts a legitimate timestamp | **No.** Neither ISO spelling (`-0700`, `-07:00`) contains a separator `splitlines()` honours; both round-trip byte-identical |
| `EMPTY` substituting for real content — `0`, `False`, `""` | **No.** `col(0) == "0"`, `col(False) == "False"`, both truthy. Only genuinely empty output degrades to `-`. `flush_line(0, 0, …)` is safe |
| Backwards compatibility with pre-v1 records | **Nothing breaks.** Re-measured across `*.py *.sh *.ts *.js *.yml *.yaml *.md *.json` (excl. `node_modules`, `.git`): the four logs have **zero readers**. Every hit is a writer, a self-test against a redirected temp copy, or prose. No fixture, self-test or doc parses a record |
| A missed producer | **None.** The only append-mode writers under `scripts/` and `.claude/hooks/` are the four log sites plus `explainer-serve.py:1299` (`QUESTIONS`, a different grammar). `check-anon-exposure.py` parses tab rows, but from `psql` output |
| The 27 rewritten `split("\t")` assertion lines | **Every one lands on the column its name claims.** Traced each absolute index against the emitted record; the negative-index reads (`[-2:]`, `[-3:]`, `[2:]`) are unaffected by the new prefix. Two *names* drifted (Low 10); none passes for the wrong reason |
| Retargets 2 and 3 (banner flush counts, closing turn id) | Accurate, and each dies via its named case |
| Backlog #168 (claim 4) | Correct and well-targeted. No finding |
| `check-fixture-variation` `EXAMINED_KEYS` entry | All six parameters genuinely varied; guard green |

Self-tests, all green: `observer_log` 37/37 · `check-banner-armed` 159/159 · `check-ci-watched` 57/57 ·
`check-closing-table` 153/153 · `check-dashboard-entry` 148/148 + 13/13 · `check-fixture-variation`
67/67 · `check-ratchet-contract` 41/41 · `check-selftest-counts` 18/18 · `check-docs` 22/22 ·
`check-guard-coverage` 37/37 · `check-producer-enumeration` 11/11 · `check-anchors` 15/15 ·
`check-review-rounds` 29/29.

**A green suite is exactly what made findings 2–5 survivable.** Every one of them is invisible to
`--self-test` by construction.

---

## BLOCKING 1 — CI is red on both `check-plan-code` steps, and the 963-mutation sweep never ran

`EXPECTED_MUTATIONS` was updated. The **two literals that exist to make a silent count change
impossible** were not.

```
scripts/check-plan-code.py:3434
    case("the declared counts are the real ones", sum(EXPECTED_MUTATIONS.values()), 954)

scripts/check-plan-code.py:2718-2719
    case("the declared counts name every manifest that ships",
         sorted(EXPECTED_MUTATIONS), ["scripts/begin-plan.py", …])   # literal list, 52 entries
```

Measured:

| | declared sum | keys | `observer_log` in the pinned list |
|---|---|---|---|
| `HEAD` | 954 | 52 | no |
| branch | **963** | 53 | **no** |

`45−47 = −2`, `27−29 = −2`, `46−47 = −1`, `+14` → `954 + 9 = 963`. The arithmetic is right; the two
pins were not carried.

**Both CI steps fail.** `ci.yml:442` (`--self-test`) → `126/128 passed`, rc=1. `ci.yml:436`
(`--mutate .`) → rc=1:

```
[50/53] control scripts/observer_log.py
  ✗ CANNOT RUN — control run of scripts/check-plan-code.py did not prove the suite works
    (exit 1) BEFORE any mutation was applied. Every verdict below would be an artefact.
    Treat this as NOT CHECKED.
NOT MEASURED — the mutation harness produced no coverage verdict. Treat this as NOT CHECKED.
```

⭐ **This is the finding that produced the other four.** Because the control is red, *not one of the
963 mutations was applied* — including all 14 new `observer_log` entries. The slice's claim 5 ("5
retired and 3 retargeted, each retired entry's property mutation-covered in `observer_log.json`") was
**never measured by anything**. Findings 2, 3 and 5 are what the sweep would have said.

I verified the fix is exactly these two literals: patching `954 → 963` and adding `observer_log.py`
to the pinned list in a temp copy leaves only three failures, all of them
`HARNESS_TREE`-completeness artifacts of my incomplete probe tree (`supabase`, `docs`,
`node_modules/typescript`, `.claude/hooks` absent) and none related to this branch.

> ⚠ The repo's own rule applies to how this was reported: *"Cannot run" is a FAILURE, never a pass.*
> The gate said `NOT CHECKED` in those words and the slice came to review as green.

---

## BLOCKING 2 — the version marker is unfalsifiable. Its own mutation SURVIVES

This is the single load-bearing property of backlog #170, and it has no falsifier.

`scripts/mutations/observer_log.json` → **"VERSION is blanked rather than removed"**
(`VERSION = "v1"` → `VERSION = ""`). Measured against `observer_log.py --self-test`:

```
SURVIVOR — 37/37 passed, rc=0, zero [FAIL] lines
```

Root cause, `scripts/observer_log.py:179`:

```python
case("record starts with the VERSION column", r.split(SEP)[0], VERSION)
```

The assertion compares the record against **the very constant under test**. Blank `VERSION` and both
sides become `""`, so the case is structurally incapable of observing it. Every other case survives
too: the column count is unchanged (an empty cell is still a cell), `[1]` is still `when`, `[2]` is
still `session`.

So the shipped state is: a record can go out carrying an empty leading cell — indistinguishable from
a pre-v1 record with an extra empty column — and nothing in the repo notices. The module's docstring
says *"`VERSION` below is the load-bearing part of this module and the sanitiser is the cheap part"*,
and the sanitiser is the half that is actually covered.

This is the recorded *a test that cannot fail* shape. **Fix:** assert the literal `"v1"`, not the
symbol, and add a case asserting the cell is non-empty. Note the sibling mutation "the record loses
its VERSION column" (`cells = [VERSION, ts, sess]` → `[ts, sess]`) *is* killed — it changes the
column count. Only the blanking is invisible, which is the subtler and more likely edit.

---

## HIGH 3 — "the EMPTY sentinel is blanked" dies via a different case than it names

Same self-referential root cause, second instance.

Entry declares `expect: ["an empty session becomes the sentinel"]`. Measured actual red case:

```
declared expect : ['an empty session becomes the sentinel']
actual failures : ['an empty field becomes the sentinel']
```

`scripts/observer_log.py:203` compares against the constant again:

```python
case("an empty session becomes the sentinel", record("", "f", when="T").split(SEP)[2], EMPTY)
```

With `EMPTY = ""`, `col("") or ""` is `""` and `EMPTY` is `""` → passes. The mutation only dies at
all by accident, through `:205`, which asserts the **literal** `"-\n"` and is therefore the only
case in the block with a real falsifier.

The harness's attribution rule is exact case-name equality (`check-plan-code.py:1469-1471` —
*"EXACT case names, not substrings"*), so `attributed` is `False` and `--mutate .` refuses this
entry. It is Blocking-adjacent; it is only not Blocking-1 because finding 1 already stops the run.

---

## HIGH 4 — a retired property is genuinely uncovered: freezing the timestamp column survives

`check-plan-code.py`'s new comment asserts each retired entry's property is covered in its new home:

```
#   banner  flush_line freezes timestamp -> observer_log "record puts `when` second"
#   banner  flush_line freezes session   -> observer_log "record puts `session` third"
```

⛔ **Those name CASES, not MUTATIONS.** No entry in `observer_log.json` freezes either column. The
retired entries were mutations; nothing replaced them as mutations.

For the timestamp, the property is not covered by the *cases* either. Measured —
`ts = col(stamped) or EMPTY` → `ts = "T"`:

```
SURVIVOR — 37/37 passed
```

It survives because every case reading `[1]` uses `when="T"` (`:180`), and the one case that could
have caught it is itself vacuous:

```python
scripts/observer_log.py:214
    case("record defaults `when` to now() when omitted",
         record("s", "f").split(SEP)[1] != "", True)
```

`ts` is `col(stamped) or EMPTY`, so it is **never** `""` — the assertion is true for every possible
implementation, including `when=""`. It cannot fail. That is the retired R5-646c property
(*"a `when` that is the same string at every call site leaves any clause reading it unguarded"*)
reintroduced in the module that was supposed to inherit it.

The other two retirements are weaker but real: freezing the session (retired entry A) and emptying
the sanitiser (retired ci entry D) are both killed by the *suite*, but **neither has a manifest
entry** — so the ratchet count fell by 5 while only 3 of those 5 properties gained a replacement
mutation.

Net of the 5 retirements: **1 property uncovered outright, 2 lost their manifest entry.**

---

## HIGH 5 — "append lets the OSError escape" kills by CRASH, and hides every case after it

Entry: `except OSError:` → `except NotADirectoryError:`. Measured:

```
  ✓ append creates missing parents and writes
  ✓ append is additive
Traceback (most recent call last):
  File ".../observer_log.py", line 227, in _self_test
    case("append returns False on OSError rather than raising", append(d, "x\n"), False)
IsADirectoryError: [Errno 21] Is a directory: '.../adir'
RC=1
```

Zero `[FAIL]` lines. `caught = rc == 1` is `True`, `fails` is empty, so `attributed` is `False` and
the gate refuses it — and a crash at `:227` means every case after it never runs.

⚠ **This exact trap is documented three times in the code this module was extracted from** —
`check-closing-table.py:1376-1382` (*"a bare index is a raise waiting for the mutation that proves
the case matters"*), and `_logtext`/`_flushtext`'s docstrings in `check-banner-armed.py` (*"killed BY
A CRASH names no guard"*). The new module has no `safe()`/`_safe()` wrapper at all: `:227` is a bare
`append(d, "x\n")`. The consolidation inherited the grammar and left the hard-won harness discipline
behind.

---

## MEDIUM 6 — `append` promises "NEVER raises" and does raise, on the one field that comes from outside

`scripts/observer_log.py:124-126`:

> *"Best effort. -> True on success, False on any failure. **NEVER raises.**"*

`:141` catches `OSError` only. Measured:

```python
payload = json.loads(r'{"session_id": "sess-\ud800-bad"}')   # lone surrogate — valid JSON
line = observer_log.record(payload["session_id"], "unwatched", "detail", when="T")
# -> 'v1\tT\tsess-\ud800-bad\tunwatched\tdetail\n'   (col() only strips separators)
observer_log.append(p, line)
# -> UnicodeEncodeError: 'utf-8' codec can't encode character '\ud800': surrogates not allowed
```

`UnicodeEncodeError` is a `ValueError`, not an `OSError`. The observer becomes a traceback — the one
outcome the docstring says is *"strictly worse than staying silent"*.

This is the same *contract hole, not live corruption* class as the original `_col` finding (a real
`session_id` is a UUID), and the pre-consolidation code had it too. But the docstring now makes the
**stronger** claim, and three observers depend on it. Widening to `except (OSError, ValueError)` — or
`errors="replace"` on the open — closes it in one line.

---

## MEDIUM 7 — claim 3 is false: only 1 of 4 producers uses `observer_log.now()`

The slice claims *"One timestamp spelling … Now all use `observer_log.now()`."* Measured:

```
scripts/check-closing-table.py:931    when = observer_log.now()          ← the only one
scripts/check-banner-armed.py:959     when = _dt.datetime.now().astimezone().replace(microsecond=0).isoformat()
scripts/check-banner-armed.py:1179    when = _dt.datetime.now().astimezone().replace(microsecond=0).isoformat()
scripts/check-ci-watched.py:393       when = _dt.datetime.now().astimezone().replace(microsecond=0).isoformat()
scripts/check-ci-watched.py:435       now  = _dt.datetime.now().astimezone().replace(microsecond=0).isoformat()
```

The expression is byte-identical to `observer_log.now()`'s body (`:102`), so **no value diverges
today and nothing is broken**. But four copies of the spelling remain, which is precisely the shape
that produced the `-0700`/`-07:00` split this slice exists to remove. The divergence was fixed; the
mechanism that permits it was not. Either route the remaining four through `now()`, or drop the claim
— as written it would let the next reader believe a check exists that does not.

---

## MEDIUM 8 — a retargeted mutation's name no longer describes its edit

`scripts/mutations/check-ci-watched.json`, entry **"the log line drops its SESSION column, so entries
stop being attributable to a session"**:

```
OLD edit: f"{_col(when)}\t{_col(session) or '-'}\t{_col(reason)}\t{_col(detail)}\n"
       -> f"{_col(when)}\t{_col(reason)}\t{_col(detail)}\n"          ← really drops session
NEW edit: observer_log.record(session, reason, detail, when=when)
       -> observer_log.record(session, detail, when=when)            ← drops `reason`
```

Measured:

```
intact  : 'v1\tT1\ts1\tunwatched\t3 unresolved\n'
MUTATED : 'v1\tT1\ts1\t3 unresolved\n'      column[2] == 's1'  — the session cell is INTACT
```

It still dies via its named case (which asserts the full five-element list), so the gate would pass
it. But the manifest now documents a property it does not test, and **no entry anywhere drops the
session cell** — that property went the same way as HIGH 4's. Rename the entry to what it does, and
add `cells = [VERSION, ts, sess]` → `[VERSION, ts]` to `observer_log.json` if the session-column
property is meant to stay covered.

---

## MEDIUM 9 — "ONE owner" owns the grammar, but the family still has FOUR write implementations

| Site | `encoding=` | Handler | Shape |
|---|---|---|---|
| `observer_log.py:136-142` (`append`) | `utf-8` | `OSError` → `False` | shared; used by **one** caller |
| `check-ci-watched.py:416` | `utf-8` | `OSError` → message | inline, **justified in a comment** |
| `check-banner-armed.py:1182` | **none** | `OSError` → message | inline, same justification, unstated |
| `check-banner-armed.py:962` | **none** | `OSError` → `True`/`False` | inline, **byte-identical contract to `observer_log.append`** |

The last row is the finding. `check-banner-armed.py:960-966` is mkdir / open-append / write /
`return True` / `except OSError: return False` — the *same function* as `observer_log.append`. It is
also the same function as `check-closing-table._append_log`, which this slice **did** migrate, on the
stated ground that *"this caller only ever wanted a bool, so … there was nothing here to lose by
sharing it"*. That reasoning applies verbatim to `:962`, which was left alone with no reason given.

The `check-ci-watched` exemption is well argued and I would keep it. The two `check-banner-armed`
sites additionally drop `encoding=`, so they depend on the ambient locale where their siblings do
not — a difference the consolidation is the natural moment to remove.

---

## LOW 10 — two case names no longer match what they assert

- `check-closing-table.py:1360` — *"log: the line carries FOUR tab-separated fields"*. The line now
  carries **five**; the assertion slices `[1:]` to measure the payload. The in-file comment says the
  name *"is pinned by a mutation `expect`, so it must not be reworded"* — that is the tail wagging the
  dog. A mutation `expect` is a string in a JSON file editable in the same commit; a case name that
  states a false count outlives the person who knew why.
- `check-ci-watched.py:590` — *"log_line carries all FOUR columns it is given, at two distinct inputs
  each"* now asserts a five-element list including `"v1"`. The assertion is strictly stronger; the
  name is stale.

Neither is a correctness defect. Both are the kind of drift backlog #170 is about, one layer up.

## LOW 11 — the manifests were re-serialised with `\uXXXX` escapes, burying the ratchet change

All three manifests came back from `json.dump` with `ensure_ascii=True`, converting every em-dash to
`—`. Functionally identical after `json.load`. But it turns a 3-entry semantic change into
~230 diff lines across three files, and the ratchet manifests are precisely the files a human is
expected to read line by line. I had to reconstruct the real change with a parse-and-compare script
before I could review it. Re-emit with `ensure_ascii=False` to match the rest of the repo.

---

## What I would do, in order

1. **Fix BLOCKING 1 first and re-run `--mutate .`.** Two literals: `check-plan-code.py:3434` `954 →
   963`, and add `"scripts/observer_log.py"` to the list at `:2719`. Nothing else in this review is
   safely actionable until the sweep has actually run once — findings 2, 3 and 5 are its output, and
   there may be more behind them across the other 949 mutations.
2. **De-self-reference the two constants** (BLOCKING 2, HIGH 3): assert the literals `"v1"` and
   `"-"`, not `VERSION` and `EMPTY`.
3. **Wrap the raising assertions** (HIGH 5) in a `safe()` helper, matching the three consumers.
4. **Add the missing mutations** (HIGH 4, MEDIUM 8): freeze `ts`, freeze `sess`, drop the `sess`
   cell, empty `col`. Fix the vacuous case at `:214` while there — it is the reason the freeze is
   invisible.
5. Mediums 6–9 and the Lows are ordinary follow-ups and could ride in the same PR.

**The slice's design is right** — one owner, a leading per-record version token, sanitising every
field rather than the ones the caller thinks are risky, and the decision to leave `check-ci-watched`'s
write alone is correctly argued. The defects are all in the *evidence*, not the design: a gate that
did not run, two assertions that cannot fail, and a set of retirement claims that were written down
rather than measured.

---

## Coordinator fold — 2026-09-23

**Round 1 verdict accepted in full. NOT CONVERGED; round 2 is owed.** Both halves are filed;
Codex (`docs/reviews/codex/observer-log-owner-r1-codex.md`) found the SAME two Blockings
independently, by a different method, and reported High/Medium/Low empty.

| # | Finding | Folded? | What changed |
|---|---|---|---|
| B1 | the 963-mutation sweep never ran | ✅ | ran it. Refused 3× for correct reasons, then **964 killed, 964 attributed, 0 survivors, controls green before AND after** |
| B2 | the version marker's own mutation SURVIVED | ✅ | asserts the literal `"v1"`, not the symbol; plus a non-empty case |
| H3 | `EMPTY` sentinel, same self-referential shape | ✅ | literals |
| H4 | a retired property genuinely uncovered (frozen timestamp) | ✅ | new case at two distinct inputs + new mutation (`stamped = …` → `"T"`); pin 14 → 15 |
| H5 | a mutation killed by CRASH, hiding later cases | ✅ | now `return False` → `return True`: fails cleanly, via the case it names |
| M7 | "all four use `observer_log.now()`" was FALSE | ✅ | it is true now — 4 copies routed through it |
| M8 | a retargeted mutation's name did not describe its edit | ✅ | renamed to *"the log line drops a PAYLOAD column"* |
| L10 | two case names stated a false column count | ✅ | **renamed, and their `expect`s with them.** The review is right that "the name is pinned by a mutation" was the tail wagging the dog — a `expect` is a string in a JSON file editable in the same commit |
| L11 | manifests re-serialised with `\uXXXX`, burying the change | ✅ | re-emitted with `ensure_ascii=False` |
| **M9** | **"ONE owner" owns the grammar; FOUR write implementations remain** | ⛔ **NOT FOLDED — round 2** | see below |

### M9 — deferred, with the measurement, so round 2 does not re-derive it

```
observer_log.py:138        path.open("a", encoding="utf-8")   shared; 1 caller
check-closing-table.py:878 observer_log.append(...)           delegates  ✅
check-ci-watched.py:416    WARN_LOG.open("a", encoding="utf-8")  own, DELIBERATE
check-banner-armed.py:962  FLUSH_LOG.open("a")                ⚠ NO encoding=
check-banner-armed.py:1182 WARN_LOG.open("a")                 ⚠ NO encoding=
```

⚠ **The review's table flagged an `encoding=` column and it was right to.** `check-banner-armed`'s
two writes take the **platform default encoding**, while the shared `append` specifies `utf-8`. On a
non-UTF-8 locale a non-ASCII field would raise `UnicodeEncodeError` from one producer and not the
others — a divergence in exactly the dimension this slice exists to remove. Live risk is low (the
fields are a constant `reason` and an ASCII `STEP n of m`), which is why it is Medium and not High.

`check-ci-watched.py:416` keeping its own write is **deliberate and documented at the call site**: it
puts the `OSError` text into its warning, and `append` returns a bool. That one is not a defect.

⛔ **Deferred rather than rushed** because the fold above already changed code, and a round that
never reviews the FIXES is the failure this repo has measured twice. Round 2 takes M9 plus a re-run
of both halves over the folded tree.
