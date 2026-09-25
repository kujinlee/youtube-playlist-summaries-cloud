# Round 2, Claude half — `2026-09-25-round-record-substrate-design.md` (backlog #117)

**Subject:** `docs/superpowers/specs/2026-09-25-round-record-substrate-design.md`
**Branch:** `backlog-117-parser-substrate` · **HEAD reviewed:** `97bfcb8c` · **Date:** 2026-09-25
**Mandate:** refute the folds. r1 folded at `bef49007`; r2's Codex half folded at `97bfcb8c`.

**Verdict: NOT CONVERGED. The spec must not pass its Phase 1 gate.**
**3 Blocking, 3 High, 4 Medium, 2 Low. 10 of 12 are `fix_induced: true`** — created by the r1 or r2
fold, not present in the draft they repaired. ⛔ **The recorded pattern holds for a fourth round: the
central Blocking is the same defect one layer deeper.**

---

## B1 — the field table is produced by the reader it is supposed to audit, so it MATCHES on the one case it was built to catch

- **severity:** Blocking · **component:** `conversion-falsifiers` · **aim:** deliverable
- **fix_induced:** ⛔ **true** — this is r2 Codex's Blocking, folded, landing one layer deeper.

§2 now says the falsifier is *"the converter emits, per document, a **side-by-side field table** —
source text vs converted JSON, every top-level key and every finding field"*, read by a human, and
that *"any automated comparator must itself decide what a field is … **A reviewer reading 31 tables
does not**."* (`:262-264`).

⛔ **It does, and the table hides that it did.** §2's own residual-risk paragraph (`:220`) states the
converter **reads through the broken parser**. A table whose *source* column is that reading is
self-consistent with its JSON column by construction. Measured, on the exact shape §2 names:

```
$ # source header line, verbatim:
$ #   - {id: H1, severity: High, aim: deliverable, fix_induced: false,
$ #      component: "check-docs, check-backlog", disposition: fixed}
$ python3 - <<'PY'   # parse_header over that document
parse_header : {"aim": "deliverable", "component": "check-docs", "disposition": "fixed",
                "fix_induced": false, "id": "H1", "severity": "High"}

A field table whose SOURCE column is produced by the same reader:
   aim            | source: 'deliverable'  | json: 'deliverable'  -> MATCH
   component      | source: 'check-docs'   | json: 'check-docs'   -> MATCH
   disposition    | source: 'fixed'        | json: 'fixed'        -> MATCH
   fix_induced    | source: False          | json: False          -> MATCH
   id             | source: 'H1'           | json: 'H1'           -> MATCH
   severity       | source: 'High'         | json: 'High'         -> MATCH
_validate on it -> PASSED
```

**Six rows, six MATCH, zero signal.** The human reads a clean table and signs off on a `component`
truncated from `check-docs, check-backlog` to `check-docs` — permanently, into the field §2 itself
calls *"the thrashing axis"*. **This is the third falsifier design in three rounds and it fails the
same way the first did: it cannot fire on the case it was written for.** r1's could not fire; r2's
could not be built; r2's fold replaced *"a comparator that must parse"* with *"a table generator that
must parse"* — the same component, with a human placed downstream of it who cannot see what it did.

⚠ **And the crux the fold never states:** the escape exists and is one sentence long — **the source
column must be the RAW SOURCE TEXT of the header region, never the converter's reading of it.** Then
a human really does see `component: "check-docs, check-backlog"` beside `"component": "check-docs"`.
But that check is a **whole-header** read, not a *field-level* one — the human performs the field
alignment, which is precisely why it is sound and precisely what the table removes. The spec chose the
one form of the check that cannot work, and argued for it on the grounds that a human cannot be a
parser, which is the opposite of the property that makes the check work.

**Fix:** state that the table's left column is the verbatim source text of the header block (or of
each source line), and that nothing derived from the converter's parse may appear in it.

---

## B2 — "the converter is DELETED" is the whole warrant for letting it parse, and the same fold makes it SURVIVE

- **severity:** Blocking · **component:** `migration-cutover` · **aim:** deliverable
- **fix_induced:** ⛔ **true** — both halves of the contradiction were written in the r2 fold.

Two statements, 35 lines apart, both added at `97bfcb8c`:

| where | text |
|---|---|
| `:251-256` | **"The resolution: the converter MAY parse, because the converter is DELETED"** … *"written once, reviewed once, run once, **deleted with the migration**, and never consulted by `decide()`"* |
| `:288-290` | **"The converter ships as a script that survives the migration"** — `scripts/migrate-round-headers.py`, idempotent … *"It is the **reader** that is deleted, **not the converter**"* |

⛔ **The first is the entire argument that #117 permits a hand-rolled YAML reader here.** Remove
*deleted* and the argument evaporates: what ships is a **standing** hand-rolled YAML-subset reader,
living in `scripts/`, named in a CI failure message, and run by every in-flight branch. That is #117's
subject relocated and renamed — the outcome the spec's own *How we would know it failed* list calls
*"a fallback YAML reader appears in a later commit → #117 was postponed, not discharged"* (`:367`).

**And nothing in this repository would oblige that survivor to be tested.** Measured:

```
$ grep -n "GUARD_PATH_RE = " scripts/check-ratchet-contract.py
113:GUARD_PATH_RE = re.compile(r"scripts/check-[\w.-]+\.py")
```

`check-ratchet-contract.py` discovers its population by that pattern (`:164`), so
`scripts/migrate-round-headers.py` is **outside it**: no `--self-test` obligation, no caller
obligation, no fail-open rule. A permanent YAML reader with no ratchet, introduced by the fold that
removed a YAML reader.

**Fix:** pick one. Either the converter is genuinely deleted in the same PR (and the cutover needs a
different forcing function — see B3), or it survives and the spec must say plainly that a hand-rolled
reader survives, justify it against #117, and place it under a ratchet.

---

## B3 — the new CI refusal and the #187 deferral were decided in the same fold and are incompatible: 5 committed documents become permanently red

- **severity:** Blocking · **component:** `migration-cutover` (also `scope-entanglement`) · **aim:** deliverable
- **fix_induced:** ⛔ **true** — the refusal is r2 Codex's High, folded; the deferral is r2 Codex's
  other High, folded. Neither existed at `bef49007`; each refutes the other's stated cost.

§2 `:291-293`: *"`check-review-rounds.py` gains a refusal: **a round document under
`docs/reviews/coordinator/` carrying a `yaml` header after the cutover fails**"*.
`:350` (the #187 decision): those three documents *"stay unreadable one row longer, **which is the
status quo, not a regression**."*

**Measured — every yaml-carrying document in that directory that the converter cannot produce JSON
for, because §2 says the converter reads through `parse_header`:**

```
$ python3 - <<'PY'   # parse_header over docs/reviews/coordinator/*.md carrying ```yaml
  merge-ready-r1-codex.md                | header has no `round:` line
  merge-ready-r2-codex.md                | header has no `round:` line
  ship-src-root-alone-r1-coordinator.md  | finding 'L4' has disposition='refuted', not one of [...]
  ship-src-root-alone-r2-coordinator.md  | finding 'H1' has disposition='redesigned', not one of [...]
  ship-src-root-alone-r3-coordinator.md  | finding 'B1' has disposition='retreat', not one of [...]
```

⛔ **"Status quo" is false.** Today these five are inert: unreadable, and nothing fails over them
(`check-review-rounds.py --self-test` → `77/77`, and the repository is green). After the refusal they
are **CI-red on every PR**, with no remedy inside this spec — the converter cannot emit them and the
spec explicitly declines to widen `disposition`. The cost of the #187 decision was priced against a
world that the other fix in the same commit removes.

⚠ **And the escape is the thing that was declined.** Measured:

```
$ # REQUIRED["disposition"] |= {"refuted","redesigned","retreat","moot"}
  ship-src-root-alone-r1-coordinator.md -> 10 findings
  ship-src-root-alone-r2-coordinator.md ->  9 findings
  ship-src-root-alone-r3-coordinator.md ->  7 findings
```

(The spec's 10/9/7 reproduce exactly — see *clean*, below. The two `merge-ready-r*-codex.md` files
are a separate problem: see M3.)

**The mandate asks whether the refusal turns the 39 headerless documents into failures. It does
not** — measured, all 39 carry no ` ```yaml ` block, so a refusal keyed on *carrying a yaml header*
cannot see them. **The damage is the 3 `disposition` documents plus 2 misfiled halves.**

**On #187's stated reason — it is a rationalisation, and the spec refutes it itself.** The reason
given (`:347-349`) is that widening *"would enlarge the migration corpus mid-migration"* (31 → 34).
But §2 `:294-295` already establishes the opposite rule: *"The conversion runs over whatever exists at
merge time — **no count is pinned now**."* A rule that makes the corpus size explicitly irrelevant
cannot also make a +3 change to it a reason. **What it costs to do it the other way:** four strings
added to one constant, measured above, and three documents move from CI-red to converted.

**Fix:** either widen `REQUIRED["disposition"]` in this PR (small, measured, and it removes B3
entirely), or scope the refusal to documents the decision procedure actually reads AND name what
happens to the ones it cannot convert.

---

## H1 — `_validate` is declared "kept, unchanged" but was written for a reader that could only ever produce `str` and `bool`; JSON hands it ints, lists, dicts and `null`

- **severity:** High · **component:** `header-schema` · **aim:** deliverable · **fix_induced:** false

The mandate asks for a check performed today that has no owner in the three-layer model. **This is
it, and it is a fail-open, not an omission.** Layer 3 is *"`_validate` + `REQUIRED` — a finding with
`severity: "Wrong"` still raises · ✅ kept, unchanged"* (`:123`). Today `_scalarise:302-311` maps only
the literal strings `true`/`false` to booleans; every other scalar stays a `str`. So the value domain
reaching `_validate` is `str | bool`. **`json.loads` removes that restriction and nothing replaces
it.** Measured:

```
$ # today, through the YAML reader:
YAML today, fix_induced: 0 -> REFUSED: ValueError finding 'H1' has fix_induced='0',
                                       not one of ['False', 'True']
$ # after the swap, the same value as JSON, through the KEPT _validate:
fix_induced is 0 (JSON int)      -> _validate RETURNED (no refusal)
component is a list              -> _validate RETURNED (no refusal)
$ python3 -c "print(0 in {True, False}, 1 in {True, False})"
True True
```

⛔ **`"fix_induced": 0` is refused today and accepted after the change**, silently meaning *not
fix-induced* — in the one field that arms `ARCHITECTURE_REVIEW`. Same for `"round": true`
(`isinstance(True, int)` is `True`, so an `int` type rule in layer 2 accepts a boolean, and
`sequence_error:157` already tests exactly that predicate).

**And the other direction is worse than a fail-open — it is a crash wearing `ROUND_OWED`'s exit
code.** Measured:

```
finding is an int      -> ⛔ TypeError: argument of type 'int' is not a container or iterable
finding is a string    -> ⛔ AttributeError: 'str' object has no attribute 'get'
finding is null        -> ⛔ TypeError: ...
severity is a list     -> ⛔ TypeError: cannot use 'list' as a set element (unhashable type)
```

`main()` wraps `rounds_for` in `except ValueError` **only** (`:629`). A `TypeError` propagates:

```
$ python3 -c "raise TypeError('x')" ; echo $?        -> 1
$ exit_code_for("ROUND_OWED") -> 1      exit_code_for("CANNOT_RUN") -> 2
```

**An uncaught type error exits 1 — byte-identical to *a round is owed*, not 2.** This repository's own
rule is that cannot-run is a failure and must say so. The new substrate makes that reachable and no
layer owns it.

**Fix:** layer 2 must type-check by `isinstance` (excluding `bool` where an `int` is meant), must
require `findings` to be a list **of objects**, and layer 3 must be stated as *changed* — or the
substrate swap smuggles a wider value domain past a validator written for a narrower one.

---

## H2 — the human read has no recorded output, so nothing can observe that it did not happen

- **severity:** High · **component:** `conversion-falsifiers` · **aim:** deliverable
- **fix_induced:** ⛔ **true** — the human read is r2's fold.

`:263`: *"the falsifier | **a human reads all of them.** At **31** documents that is a bounded,
one-time read, not a standing cost"*. **Name the observation that makes this FAIL.** There is none:
no artifact, no file, no place the result is written, no statement of who reads it or what they
record. A migration PR that skips the read is indistinguishable from one that performs it — and this
is the *only* remaining defence, since parity is dropped and verdict invariance is demoted to a smoke
test by the same fold.

⚠ **Compare what the spec demands of everything else.** It refuses a "stated intention" as a
scheduler (`:284`), it refuses a falsifier that cannot fire (`:225`), and it insists a count fall be
*"recorded at both sites with the count and the reason"* (`:387`). The one check it now rests on is a
promise with no record.

**And the bound is a number the spec forbids pinning.** §2 opens *"**No count is pinned here on
purpose** — it was 28, then 30, then **31**"* (`:194`) and then pins **31** four times as the
feasibility argument (`:263`, `:264`, `:324`, `:376`). Measured, the number is still moving inside the
set it measures: `docs/reviews/coordinator/round-record-substrate-r1-coordinator.md` is **already one
of the 31**, and this round's and the next round's coordinator documents will join it before merge.

**Fix:** the converter writes the tables to a committed artifact, and the PR records that a named
reviewer read all of them at a named commit — the spec's own standard for a manual check.

---

## H3 — the population table reintroduces the population confusion it was written to fix

- **severity:** High · **component:** `header-schema` · **aim:** instrument
- **fix_induced:** ⛔ **true** — the table is r2 Codex's High, folded.

`:177-181`, written because *"TWO DIFFERENT POPULATIONS WERE USED IN ADJACENT SENTENCES"*:

| population | count |
|---|---|
| round-shaped files by name | **73** |
| **of those**, carrying a `yaml` block | **34** |
| **of those**, parseable by `parse_header` | **31** (**42 not**) |

⛔ **"of those … 31 (42 not)" reads as 42 of 34.** The three counts are correct — I reproduced all of
them (below) — but `42` is `73 − 31`, taken against the **first** row's denominator while the row
label says the **second**'s. `34 − 31 = 3`. The parenthetical that belongs to row 1 is printed inside
row 3, in the table built specifically so a reader cannot confuse two denominators.

This is not cosmetic here: `42` is then carried into §2 `:300-303` as *"The 42 round-shaped documents
that do not parse today (39 with no header block at all)"*, where `39 = 73 − 34` — correct, and
correct only against 73. A reader who takes the row label literally has the wrong denominator for
both.

**Fix:** move `(42 not)` to its own row against the 73, or restate it as `73 − 31 = 42`.

---

## M1 — the sweep declared itself complete and left three live stale claims of the class it names

- **severity:** Medium · **component:** `defect-inventory` · **aim:** instrument · **fix_induced:** **true**

The appended sweep section (`:424-440`) fixed eight sites, then records *"AND THE SWEEP ITSELF MISSED
ONE"* and states the rule: **"grep for the OLD value, not for the new one."** ⛔ **The rule was not
run over `six` or `30`.** Grepped at `97bfcb8c`:

| line | live text | why it is stale |
|---|---|---|
| `:55` | *"two of the **six** reached `CONVERGED`"* | the inventory table 15 lines above now lists **seven** |
| `:198` | *"the **six** fail-open shapes remain reachable"* | wrong twice: the inventory is 7, and the spec's own split at `:50` says **5** read as a pass and 2 as a false refusal — the fail-open subset is 5 |
| `:230` | *"**Measured: 0 disagreements across all 30**"* | `30` is the population §2 `:194` explicitly retires as stale ("it was 28, then 30, then 31") |

The `:198` case is the sharper one: it survives a correction the spec states *twice*, and it is the
sentence that justifies refusing a fallback reader.

**Fix:** `grep -n "six\|\b30\b" ` the spec and restate each against the corrected inventory.

---

## M2 — the refusal keys on the DIRECTORY while every existing mechanism keys on the FILENAME

- **severity:** Medium · **component:** `migration-cutover` · **aim:** deliverable · **fix_induced:** **true**

§2 `:291`: *"a round document **under `docs/reviews/coordinator/`** carrying a `yaml` header … fails"*.
But nothing else in this system decides *"is this a coordinator round document"* from the directory:

- `check-review-decision.rounds_for():356` globs **`{subject}-r*-coordinator.md`** — by name.
- `check-review-rounds.parse():112` takes `who` from the **filename** regex (`:75-76`).

Measured, the two rules disagree over real files:

```
$ ls docs/reviews/coordinator/*.md | wc -l                        -> 136
$ # of these, carrying a ```yaml block                            -> 36
$ ls docs/reviews/coordinator/*-r*-coordinator.md | wc -l         ->  73   (34 carry yaml)
```

**Two of the 36 are `merge-ready-r1-codex.md` and `merge-ready-r2-codex.md`** — codex halves filed in
the coordinator directory. `rounds_for()` never reads them; no decision depends on them. The
directory-keyed refusal fails them anyway, for no benefit (they are 2 of B3's 5). **A second
implementation of one rule, drifting from the rule's owner** — the class this repository has recorded
seventeen times, arriving inside the fix for a different finding.

**Fix:** key the refusal on the same glob `rounds_for()` reads, and cite it rather than restate it.

---

## M3 — no layer owns "there is a ```json block at all"

- **severity:** Medium · **component:** `header-schema` · **aim:** deliverable · **fix_induced:** **true**
  (the r2 fold added the key-by-key ownership list and stopped at top-level keys)

`parse_header:205` raises `no ```yaml header block` when the fence is absent — a check, inside the
deleted region, that `json.loads` cannot perform because it never receives a document with no fence.
The three-layer table (`:119-123`) is presented as exhaustive (*"named so they cannot be merged
again"*), and the r2 fold then enumerated an owner for all nine top-level keys and for `halves` — but
the fence itself is unowned in both passes. It is the same shape as r3's Blocking (*"an absent thing
is a silence"*) one level further out.

**Fix:** name it in layer 1 — *extracting the ```json block, and refusing when there is none*.

---

## M4 — the `--self-test` direction is now honest, but the sizing section still asserts a corpus-dependent number

- **severity:** Medium · **component:** `selftest-retirement` · **aim:** instrument · **fix_induced:** **true**

The direction refusal (`:382-388`) is correct and I verified its two load-bearing claims (below).
But `:376` still sizes the work as *"a human reading ~**31** side-by-side tables"*, and `:263-264`
pin 31 twice — the same pinning §2 `:194` forbids, three paragraphs apart. This is H2's bound seen
from the sizing side; recorded separately because the fix is different: **sizing may name a snapshot,
so long as it names the commit**, exactly as `:89` now does for the 109 lines.

**Fix:** `~31 at bef49007` / `at 97bfcb8c`, or state the rule instead of the count.

---

## L1 — §2 states the same demotion three times, in a document that asserts "no mechanism appears twice"

- **severity:** Low · **component:** `conversion-falsifiers` · **aim:** instrument · **fix_induced:** **true**

`:265` (table row), `:267-268` (the ⚠ line), and `:270-272` (the r1 paragraph the fold left standing)
all say *verdict invariance is demoted to a smoke test and parity is dropped*. The last is a near-
verbatim duplicate of the second. The concern table closes with *"One mechanism per concern; no
mechanism appears twice"* (`:327`). A fold artefact, but it is the same *downstream copy left
standing* the sweep section exists to record.

---

## L2 — two line citations name the wrong statement

- **severity:** Low · **component:** `defect-inventory` · **aim:** instrument · **fix_induced:** false

In a spec whose argument is *which checks live inside the deleted region*, the citations are the
evidence. Two of them land on a neighbour:

| spec says | actually at |
|---|---|
| *"`round:` present and an int — `:203-205`"* (`:99`) | **`:209`** — `rm = re.search(r"^round:\s*(\d+)\s*$", ...)`. `:205` is the ` ```yaml ` fence regex |
| *"`parse_header:243-246` already refuses unless the list-marker count equals the parsed finding count"* (`:228`) | **`:235-236`** — `declared = len(...)` / `if declared != len(findings)`. `:243-246` is the `ROUND_REQUIRED` loop |

Verified with `grep -n`. The other five citations in that table are exact (below).

---

## What I checked and found clean

Everything here was run at `97bfcb8c`; commands are reproducible from the repo root.

1. **`61/61` reproduces.** `python3 scripts/check-review-decision.py --self-test` → `61/61 self-test
   cases passed`.
2. **⭐ r1's `_validate` claim reproduces exactly.** I replaced `_validate`'s missing-field `raise`
   with `continue` and re-ran: **`61/61 self-test cases passed`**; restored → `61/61`. The spec's
   *"gutting `_validate`'s missing-field refusal leaves 61/61 GREEN"* (`:379`) is measured, not
   inferred. `_validate` is genuinely unfalsified.
3. **"no case exists for a missing `fixes_nontrivial`" reproduces.** Every occurrence of
   `fixes_nontrivial` in `_self_test` supplies it (10 sites, `:549-601`); none omits it.
4. **The 109 lines reproduce, by AST span, at HEAD** — `parse_header` 198-251 (54) + `_findings_span`
   287-299 (13) + `_scalarise` 302-311 (10) + `_block_findings` 314-345 (32) = **109**, `_validate`
   273-284 (12) excluded as the spec says. The `121` the sweep caught is gone from `:89`.
5. **73 / 34 / 31 / 39 / 42 all reproduce**, against `docs/reviews/coordinator/*-r*-coordinator.md`
   — which is exactly the set `rounds_for()` globs, so the corpus choice is right, not merely
   consistent. (`73` ≠ the 100 coordinator-named documents that exist once the legacy flat layout is
   included; the flat 22 carry **zero** yaml blocks, so the narrower corpus loses nothing here.)
   The defect is the placement of `(42 not)` — H3, not the numbers.
6. **The #187 measurement reproduces exactly:** widening `REQUIRED["disposition"]` with
   `refuted, redesigned, retreat, moot` makes all three `ship-src-root-alone` documents parse, with
   **10, 9 and 7** findings.
7. **The inline-comment document reproduces:** `seed-explainer-serve-manifest-r2-coordinator.md`,
   header line 7 — `codex: standin-by-claude   # round 1's Codex half timed out; …`. **1**, inline,
   as stated.
8. **"it runs in CI" is true** for the refusal's host: `.github/workflows/ci.yml:203` runs
   `check-review-rounds.py`, `:206` its `--self-test` (`77/77` green at HEAD). The forcing function is
   placeable; B3 is about *what it fires on*, not whether it can exist.
9. **The refusal does NOT endanger the 39 headerless documents** — they carry no ` ```yaml ` block.
   The mandate's alternative reading is refuted.
10. **Five of seven code citations are exact:** `:232` (`findings:` key), `:245-251` (`ROUND_REQUIRED`
    loop), `:263` (`ROUND_REQUIRED` constant), `:273-284` (`_validate`), `:302-311` (`_scalarise`).
    The two external ones hold too: `round-header-template.md:3` and `:39` say what `:413-414` quotes,
    `check-review-rounds.py:81` is `HALVES = ("codex", "claude")`, and
    `architecture-review-2026-09-25-decision-family.md:180` and `:337` carry the quoted phrases.
11. **The `NO-CALLER:` framing is accurate** — `check-review-decision.py` is not executed by CI, so
    the severity bound at `:55-57` is real.

---

## Standing hazards — result of each

| hazard | result |
|---|---|
| a number stated as MEASURED that was inferred | **clean** — every number I re-derived reproduced (109, 61, 73/34/31, 10/9/7, the comment). The defect is denominator *placement* (H3), not fabrication |
| a falsifier that cannot fail | ⛔ **B1** (matches on its own case) and ⛔ **H2** (no observable output) |
| a falsifier that removes its own signal | ⛔ **B1** — the table generator launders the misread before the human sees it |
| fixing a PREMISE rather than covering the BRANCH | ⛔ **H1** — layer 2 covers the three keys the r1 Blocking named; the *branch* is the widened value domain, uncovered |
| a second implementation of one rule drifting | ⛔ **M2** — "is this a coordinator round document", directory vs filename |
| a measurement whose CORPUS is the wrong set | **clean** — the corpus is `rounds_for()`'s own glob, verified |
| true of the NAME, silent about the LAYER | ⛔ **H1** — `_validate` is "kept, unchanged" about the *function*; the *substrate under it* changes what can reach it |

---

## Verdict

⛔ **NOT CONVERGED.** **3 Blocking, 3 High, 4 Medium, 2 Low.** The spec **must not pass its Phase 1
gate**.

**10 of 12 findings are `fix_induced: true`**, and the three Blockings are all creatures of the last
two folds:

- **B1** is r2's Blocking re-entering through the fix for r2's Blocking — *the comparator must parse*
  became *the table generator must parse*. **Third falsifier, third failure, same component.**
- **B2** is two sentences of the same commit contradicting each other on the single fact that
  authorises the design.
- **B3** is two folds of the same commit each pricing its cost against a world the other removes.

⚠ **On thrashing (`docs/review-method.md`).** The arming condition — *two consecutive rounds whose
findings came from the previous round's fix, in one component* — **is now met for
`conversion-falsifiers`**: r1 Blocking (vacuous parity), r2 Blocking (unbuildable comparator), r2/r3
Blocking B1 (self-consistent table). **Three consecutive rounds, one component, each defect created by
the previous round's fix.** I am recording the observation, not convening the review: the honest
question the method requires — *can a redesign remove it, or is this a prose floor?* — has a concrete
answer here that a fourth round can act on (**B1's fix is one sentence: the left column is raw source
text**), so `conversion-falsifiers` is not yet a floor. ⛔ **But if r3's fold produces a fourth
falsifier design that fails a fourth way, that is the architecture review, and it should be convened
rather than re-argued.**

**Cheapest path to a r3 that can converge**, in dependency order:

1. **B1** — one sentence: the table's source column is the verbatim header text.
2. **B2** — decide deleted-or-surviving, and if surviving, justify it against #117 and ratchet it.
3. **B3** — widen `REQUIRED["disposition"]` in this PR (4 strings, measured) and B3 disappears along
   with the #187 fork.
4. **H1** — layer 2 type-checks by `isinstance`; layer 3 is restated as *changed*, not *kept*.
5. **H2** — the tables are committed and the read is recorded at a named commit.
6. **H3, M1–M4, L1–L2** — editorial, but M1 is the sweep's own rule applied to `six` and `30`.
