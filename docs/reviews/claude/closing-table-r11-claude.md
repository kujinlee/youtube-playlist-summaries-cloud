# closing-table — round 11 — independent Claude half (final round on the tree)

**Verdict: CONVERGED.** 3 Low, nothing blocking. The delta does what it claims: both load-bearing
sentences are true this time, and the new case is a real falsifier for the claim it pins. The one
thing still over-stated is a count — **two of the five `-` conditions are reachable, not one** —
which is the same *kind* of step-too-far this paragraph has now made three times, at a much smaller
scale.

Scope: `git diff d03ff377 13975aa4 -- scripts/` — `scripts/check-closing-table.py` only, a
docstring rewrite plus one self-test case, no behaviour change. Control on the delta:
**153/153 passed, rc=0**, and 153 static `check(` calls = the derived count.

Constraints honoured: read-only git; every experiment on `cp -R scripts` in `mktemp -d`;
`check-plan-code.py --mutate .` never run against the working tree; `docs/reviews/` top level
untouched; this file is the only repo write.

---

## Item 1 — is the new prose true this time? YES, on both routes

Both claims checked structurally **and** end-to-end, by building the transcripts and running
`--decide` against a copy of the tree (log redirected by the copy's own `ROOT`).

### `opener is None` — genuinely unreachable, and the stated reason is the right one

```python
def windows(records):
    bounds = [i for i, rec in enumerate(records) if _is_turn_boundary(rec)]
    if not bounds:
        return [TurnWindow(None, list(records))]      # <- the ONLY producer of opener=None
```

`opener is None` therefore implies **exactly one window**, so `judged_window`'s `for window in
reversed(wins[:-1])` iterates an empty list and returns `None`, and `run_decide` returns QUIET
before `log_line`. Not a measured claim — a structural one, and it also covers `coalesce_injected`,
which can only propagate an `opener=None` through `make(prev.opener, …)` in the same single-window
case it never merges.

Confirmed by running it: a transcript with no real-user boundary at all
(`[bash("git push"), say("done, in prose")]`) → **rc=0, no log line appended.**

### an opener with no `uuid` key — reachable, exactly as stated

`_is_turn_boundary` inspects `type`, tool-result shape and `isMeta` — never `uuid`. Ran Codex's
shape myself:

```
d_no_uuid      rc=1  log: 2026-09-21T08:50:07-0700	probe-d_no_uuid	a push	-
control_uuid   rc=1  log: 2026-09-21T08:50:07-0700	probe-control_uuid	a push	REAL-ID
```

So the sentence *"a `-` means this turn had no id available, not that something is broken"* is
correct, and the `grep -c '\t-$'` instruction it gives a reader is the right first move.

---

## R11-1 — Low — the enumeration is one short: **two** of the five conditions are reachable

The closing line of the new paragraph says the no-split justification is *"WEAKER than r9 claimed,
because **one** of the five is reachable rather than none."* Checked per-condition, as asked:

| # | condition | reachable from `run_decide`? | evidence |
|---|---|---|---|
| 1 | no `opener` attribute | **no** | `judged` is always a `TurnWindow` namedtuple; the field always exists. Defensive for other callers only |
| 2 | `opener is None` | **no** | structural, above; 0 of 2,290 judged windows in the corpus, and the degenerate transcript returns QUIET |
| 3 | a non-dict opener | **no** — but not for the reason implied | see R11-3: such a record raises in `_is_turn_boundary` long before `turn_id_of` is called |
| 4 | no `uuid` key | **YES** | `probe-d_no_uuid` above, rc=1, field 4 `-` |
| 5 | an **empty** `uuid` | **YES — and this one is not named** | `probe-e_empty_uuid`: opener `{"uuid": ""}` → `rc=1`, log line `…	probe-e_empty_uuid	a push	-` |

Condition 5 is reachable by *exactly* the argument that makes condition 4 reachable —
`_is_turn_boundary` never inspects `uuid`, so it does not care whether the key is absent or empty.
The only thing standing between the harness and an empty `uuid` is the same thing that stood
between it and a missing one: current behaviour, which r10 has already established is not an
invariant.

Nothing behavioural turns on it — both conditions produce the same `-`, and the case pinned for
condition 4 exercises the same branch. But this paragraph's failure mode has twice been *a count or
a quantifier asserted one step beyond what was checked*, and "one of the five" is that shape again
at small scale. **Fix: say "two of the five (a missing `uuid` and an empty one)".** One word.

---

## Item 2 — does the new case pin what it claims? Mostly. Half of its assertion is ambient

The case asserts `(rc, field4) == (WARN, "-")`. Two separate questions:

**Is it a falsifier or a snapshot? — a falsifier.** Mutating `_is_turn_boundary` in a copy of
`check-banner-armed.py` to require a non-empty `uuid` — i.e. making the reachable path unreachable —
**reddens it**, along with 9 other end-to-end cases. So if the world ever changes such that a
no-uuid record stops being a boundary, the case fails rather than quietly continuing to pass. That
is the property r10's finding needed, and it is present.

**Does it read the line it thinks it reads? — yes.** It takes `read_text().strip().split("\n")[-1]`,
and the preceding case writes `OPENER-OF-THE-JUDGED-TURN` into that field, so a stale read yields a
value that fails the assertion rather than passing it. Good sequencing.

**But the `-` itself is ambient.** `log_line` ends with `{turn or '-'}`, so *any* falsy return from
`turn_id_of` renders as `-` in field 4. Measured:

| mutation of `turn_id_of`'s fallback | new case |
|---|---|
| `else "-"` → `else ""` | **still passes** (5 unit cases redden, the new one does not) |
| `else "-"` → `else None` | **still passes** |
| drop the empty-`uuid` test entirely | **still passes** |
| `else "-"` → `else "ZZ"` | reddens |

So the case pins *"this transcript still warns"* — the reachability claim, which is what it exists
for — but it does not pin *that `turn_id_of` produced the `-`*. Its label says "logs `-`", which
reads as the stronger claim. Worth one clause in the case comment; not worth a code change, since
the value a reader sees is `-` either way.

---

## Item 3 — the stated no-mutation gap is CORRECT, and for a stronger reason than given

Your reasoning: any mutation of the `else "-"` branch also reddens `log: an opener with no uuid
yields '-'`, so an `expect` could not name exactly one red case. Verified — and it is worse than
that, in your favour:

| mutation | red cases | includes the new case? |
|---|---|---|
| `else ""` | 5 | no |
| `else "ZZ"` | **6** | yes — plus all five unit cases |
| `else None` | 5 | no |
| drop the empty-uuid test | 1 (`log: an empty-string uuid is not an id`) | no |
| `turn or '-'` → `turn` | 1 (`log: a missing turn id degrades to '-'`) | no |
| `_is_turn_boundary` requires a uuid | **10** | yes — plus 9 others |

**No mutation I could construct reddens only the new case.** Every one either misses it entirely
(masked by `log_line`'s fallback — item 2) or takes five to nine cases with it.

The deeper reason is worth writing down, because it makes the gap principled rather than
circumstantial: the new case's *unique* content is a property of `_is_turn_boundary`, which lives
in **check-banner-armed.py**. A manifest entry in `mutations/check-closing-table.json` cannot target
another file, and reaching into the borrowed rule is exactly what this guard refuses to do. So the
mutation that would name this case cannot exist *in this manifest* by construction — not because
one was not written. I would put that sentence in the comment; "an `expect` could not name exactly
one" is true but reads like a workaround, and this is a boundary.

---

## R11-2 — Low, out of the delta, offered not filed — a non-dict transcript record tracebacks out of the Stop hook as exit 1

Found while checking condition 3. `_parse_records` appends whatever `json.loads` returns with no
`isinstance(obj, dict)` filter, so a transcript line that is valid JSON but not an object reaches
`_is_turn_boundary`:

```
c_scalar (a transcript containing one bare `123` line)  rc=1
AttributeError: 'int' object has no attribute 'get'     (Traceback present)
```

`banner.windows(records)` is called **outside** `run_decide`'s `except (OSError, ImportError)`, so
this is an uncaught traceback in a Stop hook — and `block-idle-stop.sh` folds any non-zero observer
code into exit 1, the same code a legitimate warning produces. The documented contract is that
blindness is **CANNOT RUN (2)**, printing *"TREAT THIS AS NOT RUN"*; here it reports as a warning
instead, and the one thing the docstring promises never to do quietly is exactly this.

Likelihood is low (a valid-JSON non-object line), and r10's lesson is the reason I am reporting it
anyway: *"the harness never emits that"* is what the last two versions of this paragraph rested on.
The fix that keeps the borrowed rule untouched is to move `banner.windows(...)`/`judged_window(...)`
inside the existing `try` and widen it to `Exception` → CANNOT RUN. **Outside this delta — file it
or drop it, your call.**

---

## Thrashing

I do not disagree with Codex's reading. 7 → 5 → 4 → 1 with severity falling, and this round adds
three Lows of which one is a single word and one is out of scope. Converging.

---

## Verdict

| check | result |
|---|---|
| `opener is None` unreachable, for the reason given | ✅ structural **and** measured — degenerate transcript → rc=0, no log line |
| a missing `uuid` reachable | ✅ ran it — rc=1, field 4 `-`; control with a uuid logs the uuid |
| the new case is a falsifier, not a snapshot | ✅ making the path unreachable reddens it |
| the new case reads the line it claims | ✅ last line; the previous case's value would fail the assertion |
| the new case pins that `turn_id_of` produced the `-` | ❌ ambient — `log_line`'s `turn or '-'` masks `""`/`None` (item 2, Low) |
| the stated no-mutation gap | ✅ correct — 6 mutations tried, none isolates the new case |
| the five conditions, per-condition | ❌ **two are reachable, not one** — R11-1 (Low) |
| self-test on the delta | ✅ 153/153, rc=0 |
| out-of-delta observation | ⚠ R11-2 — a non-dict record tracebacks as exit 1, not CANNOT RUN |

**CONVERGED.** R11-1 is a one-word correction to a sentence; R11-2 is outside the delta and yours
to file or drop; item 2's point is a clause in a comment. None of them needs another round.

**REVIEW GAP: codex — round 11's Codex half was not run; Codex ran round 10 against `d03ff377`,
the parent of this delta, and its R10-1 is the finding this round verifies.**

---

## Coordinator disposition — and exactly what landed AFTER this round

⚠ **Stated rather than left for the reader to reconstruct from `git log`.** This round reviewed
`13975aa4`. Two edits landed after it, in `d1256d14`, and this round did not see them:

| edit | what | why it did not get its own round |
|---|---|---|
| R11-1 | "one of the five" → all five conditions enumerated individually | this round's own words: *"R11-1 is a one-word correction to a sentence… none of them needs another round"* |
| item 2 | a comment recording that the case's `-` is ambient | ditto — *"item 2's point is a clause in a comment"* |

Both are **comment/docstring only, zero behaviour change**, and the suite is unchanged at 153/153.
The review document is committed on its own so that a round is genuinely the last thing on the
branch, which is what `check-review-recorded` asks for — not a waiver, and not a same-commit
bundle, which is the shape it refused twice on this PR.

**R11-1 accepted, and the meta-point taken.** The paragraph now enumerates all five conditions
rather than quantifying over them, because that is the only form of the sentence not yet gotten
wrong. The progression this round identified is recorded in the code itself:

    r7   generalised from `windows()`'s docstring    -> "reachable and load-bearing"   WRONG
    r9   generalised from a corpus of 1,790 records  -> "unreachable"                  WRONG
    r11  generalised from having verified ONE        -> "one of the five"              WRONG

**Item 2 accepted as written.** Recorded in a comment rather than strengthened — a second assertion
would duplicate the unit cases, and the reader sees `-` either way.

**R11-2 FILED as backlog #152**, though this round offered it rather than filing. It breaks a
contract the guard states about itself: blindness must be CANNOT RUN (2), and this path reports
exit 1 — the code a legitimate warning produces. The reviewer's justification for reporting a
low-likelihood defect is the one that settles it: *"the harness never emits that"* is precisely
what both wrong versions of the `-` paragraph rested on.

**Convergence: both halves agree.** Codex (r10) and this half (r11) independently answered
CONVERGING on the same evidence — 7 → 5 → 4 → 1 findings, severity 2 High → 1 Blocking → 1 High →
1 Medium → 3 Low, of which one is a single word and one is out of scope.
