<!-- claude-review: round=17 writer=claude subject=backlog-249-260 head=3add5c2e -->

## Blocking

None established. **0 Blocking / 2 High / 3 Medium / 3 Low — NOT CONVERGED.**

The round-17 remedy is right about polarity and wrong about reach. `_REFUSAL`'s *text* is now
pinned by an oracle nothing can forge, and every attack on the text died. What is not pinned is
the *emission*: it is asserted at exactly ONE report, with exactly ONE head count, so the refusal
can be made conditional and vanish from the single-quoted-line report — the one a reader is most
likely to misread — with the suite green. And the refuted wordings this component has spent six
rounds deleting can still RETURN beside the refusal, because no case reads the sentence they would
replace.

⛔ **NEITHER REMEDY IS AN EIGHTH DESCRIPTION OF THE STREAM.** H1's is a second fixture for an
existing assertion; H2's is a DELETION. Nothing below asks for a new sentence about where lines
sit, and the two Mediums are both deletions as well.

## High

**H1 — THE REFUSAL'S EMISSION IS EXERCISED AT ONE HEAD COUNT, SO IT CAN BE MADE CONDITIONAL AND
DISAPPEAR FROM EXACTLY THE REPORT THAT NEEDS IT MOST — 297/297 GREEN.**
`scripts/check-plan-code.py:3129` (the emission), `:4003` (its only case)

The oracle at `:3997` is pure and I could not defeat it. The second case is the whole of the
emission's coverage:

```python
case("...and the report still EMITS the refusal", any(_REFUSAL in r for r in _repq), True)
```

Measured: `_repq` is **one** report carrying **two** heads
(`RuntimeError: FIRST_KILLER · ValueError: SHUTDOWN_SECOND`). One input, one head count. So a
mutation that keeps the refusal for multi-line reports and drops it for single-line ones is
invisible.

Sever at `:3129`, on a complete isolated tree over a green control:

```python
-                        + ". " + _REFUSAL)
+                        + ". " + (_REFUSAL if len(heads) > 1 else ""))
```

| Experiment | Result |
|---|---|
| Control (complete copy) | **297/297** |
| Sever applied (`grep -c 'len(heads) > 1'` → 1; probe reports `SEVER VISIBLE TO THIS MODULE: True`) | **297/297 GREEN** |
| Restore (sha256 back to `b5748491…`) | **297/297** |

The harm, rendered through production `run_mutations` with real children under the same sever:

```text
TWO-head  refusal=True   RuntimeError: FIRST_KILLER · ValueError: SHUTDOWN_SECOND. ⛔ THIS HARNESS DOES NOT CLAIM …
ONE-head  refusal=False  RuntimeError: ONLY_KILLER.
```

A report quoting **one** line, with no refusal attached, is precisely the shape
`is_exception_heading` was deleted for: a lone quoted line reads as *the* exception. On the
unmutated tree both worlds carry it (verified first, as the known positive).

⚠ The polarity half of the remedy is sound — see *Checked and found SOUND*. This is the other half.

**Remedy — a SECOND INPUT, not a sentence.** Assert the emission at a one-head fixture as well
(`raise RuntimeError("ONLY_KILLER")` reaches it in one edit), so the pair exercises the producer at
two distinct inputs. ⭐ This is the repository's own rule — *a case is otherwise satisfied by the
constant its own fixture supplies* — applied to a producer rather than a value. It writes no
structural claim, so the thrashing arming does not reach it. If the owner prefers not to add code
to this component at all, the alternative is a backlog row beside **#276**, whose subject is
exactly *a message that selects between worlds and no case asserts which*.

---

**H2 — THE SIX REFUTED WORDINGS CAN RETURN AS THE REPORT'S PREFIX, WITH THE REFUSAL STILL ATTACHED
— 297/297 GREEN AND `--binding` rc=0.**
`scripts/check-plan-code.py:3126-3128`

`:3979-3985` states the r16 harm as a conjunction: *"all six withdrawn wordings could return **AND**
the disclaimer … could go with them, unnoticed."* Rounds 16 and 17 closed the second conjunct. The
first is still open, and the refusal's presence does not close it — it produces a report that
asserts and refuses in one breath.

Sever at `:3126-3128`, complete tree, green control:

```python
-                said = ("stderr printed these lines, in stream order, each "
-                        "STRIPPED of surrounding whitespace — "
+                said = ("CPython SAID THE FOLLOWING KILLED THE CHILD, at column zero "
+                        "after a block it labelled, in reverse order, each one a "
+                        "VALIDATED exception class — "
```

| Experiment | Result |
|---|---|
| Control | **297/297** |
| Sever (known positive: `grep -c "VALIDATED exception class"` → 2) | **297/297 GREEN** |
| `--binding` under the sever | **rc=0** |
| Restore | **297/297** |

What a reader gets, rendered through production `run_mutations` with a real child:

```text
⚠ WHAT THE CHILD ITSELF SAID — CPython SAID THE FOLLOWING KILLED THE CHILD, at column zero after
a block it labelled, in reverse order, each one a VALIDATED exception class — RuntimeError:
ONLY_KILLER. ⛔ THIS HARNESS DOES NOT CLAIM ANY OF THEM IS THE EXCEPTION, NOR THAT IT KILLED THE
CHILD, NOR THAT CPYTHON WROTE ANY OF IT, NOR ANYTHING ABOUT WHERE IN THE STREAM THEY APPEARED: …
```

Every claim #279 and #280 were filed to delete — causal attribution, column zero, reverse order,
"VALIDATED exception class" — is back, in the first sentence, and nothing on disk notices. The
`" · "` join case (`:3977`) and the order case (`:4022`) both pass, because the join and the order
survive the rewrite; neither reads the sentence.

⛔ **This is NOT an argument for re-adding a phrase case.** `:4014-4021` already measured that a
phrase case cannot police a claim, and it is right.

**Remedy — DELETE, do not describe.** The prefix sentence asserts three things; two already have
falsifiers (`in stream order` → `:4022`; the join → `:3977`) and the third (`STRIPPED of
surrounding whitespace`) has none. Cut it to the text those two cases actually prove and let the
quoted lines stand with the refusal — the same move r16 made on the narration and r17 made on the
heading definition. ⚠ A blacklist of refuted tokens is the *extend the list* shape #279 exists to
reject and should not be the answer here.

## Medium

**M1 — THE SOURCE SPLIT AFTER "DOES NOT CLAIM" IS NOT LOAD-BEARING, AND THE COMMENT SAYING IT IS
CARRIES "Measured r17". THE REFUTATION OF THE REVIEWER'S SOUND CLAIM DOES NOT LAND.**
`scripts/check-plan-code.py:584-586`, `:2455`, `:1100-1106`

The comment:

> ⚠ THE SPLIT AFTER "DOES NOT CLAIM" IS LOAD-BEARING, not formatting: `--binding` REFUSES two
> entries that share an edit anchor ("it measures nothing new"), and the POLARITY mutation and the
> exception-hood mutation would otherwise both anchor on one line. Measured r17.

The first clause is true. The inference is false, and the escape is documented five hundred lines
away in the same file (`:584` vs `:1100`). `scripts/check-plan-code.py:2455`:

```python
nm, anchors = e.get("name"), tuple(f for f, _ in e.get("edits", []))
```

`seen_anchors` is keyed on the **find-strings alone**, by exact tuple equality (`:2483`). Two
entries on one line therefore collide only if their find-strings are *identical* — and `:1104-1106`
says so in the file's own words: *"its `EXACT TUPLE EQUALITY` note names the escape — a distinct
substring each … different substrings of one line ARE accepted."*

Measured, complete tree: `_REFUSAL`'s first two chunks joined onto ONE line, entries 733 and 737
retargeted onto two distinct unique substrings of that line —

| Experiment | Result |
|---|---|
| `--self-test` | **297/297** |
| `--binding` | **rc=0** — "binding OK — 1558 anchor(s) across 1550 entries each resolve to exactly one site" |
| shard0 733 | 1 killed, 1 attributed to the case it names, 0 survivors |
| shard0 737 | 1 killed, 1 attributed to the case it names, 0 survivors |
| Restore | 297/297, `--binding` rc=0, sha256 `b5748491…` |

⚠ **My first attempt was a bad instrument and I am recording it**: I picked
`"⛔ THIS HARNESS DOES NOT CLAIM ANY` for 737, which resolves to **2 sites** (the self-test
literal at `:3999` begins identically), so `--binding` went rc=1 for *ambiguity*, not duplication —
a red that would have read as confirming the comment. The second attempt anchored past the point
where the two lines diverge.

⛔ **And the fold's refutation of the reviewer therefore fails.** The commit says *"That also
REFUTES one of this review's own SOUND claims — it reports the refusal scope as the 'complete
anchor tuple', and the guard rejected two entries that differed in their replacement text."* In
this codebase "anchor" IS the find-string (`:1103` "builds `seen_anchors` from the find-strings
ALONE"; `:2484` "repeats the edit anchors"). "Complete anchor tuple" is an accurate name for
`tuple(f for f, _ in edits)` — the *whole tuple* as against any single anchor, which is what the
reviewer's next sentence goes on to distinguish. The two statements never disagreed; the fold read
"anchor" as including the replacement half and published a refutation on that reading, in a commit
body and in a source comment.

**Remedy, two deletions.** Delete the "LOAD-BEARING" claim at `:584-586` (the split may stay as
formatting — it is readable; what must go is the assertion that `--binding` compels it), and
withdraw the refutation of the r17 Codex SOUND item. ⚠ Filed testimony is not edited, so the
withdrawal belongs where the claim is live: the source comment and the next commit body.

---

**M2 — r17 M1's NARROWING MISSED ITS SIBLING FIFTY LINES BELOW, IN THE SAME FUNCTION. THE
GENERALISATION THE DOCSTRING WITHDREW IS STILL ASSERTED IN THE BODY.**
`scripts/check-plan-code.py:712-714`

Withdrawn at `:601-604`: *"a line led by ANY other whitespace is returned here with that whitespace
`.strip()`ped away"* — false, because a line that is ONLY such whitespace is consumed.

Still standing at `:712-714`:

> ⛔ r16 M1: this comment said "at column zero" TWICE and both were false — the run test reads only
> space and tab, so **any other whitespace lead is stripped out of the quotation**. Measured:
> `　END` is reported as `END`.

Same universal, same witness attached, same refutation: for a `　`-only line there is no
quotation at all, so no lead is "stripped out of" one. Measured, production function:

```text
lines_after_frame_runs('  File "f"\n　\n')     -> []        # consumed, not quoted
lines_after_frame_runs('  File "f"\n　END\n')  -> ['END']   # the one witness
```

⭐ This is r17's own M3 one round later: *"that sweep reported itself complete; it was not."* M1's
narrowing was applied at the docstring site and nowhere else, and the enumeration M3 demands was
not run for M1's vocabulary.

**Remedy — DELETE the `so any other whitespace lead …` clause**, leaving the "column zero" history
and the measured witness. No replacement sentence; `:3116-3117` already states the mechanism
accurately for anyone who wants it (*the run test reads only `" "`/`"\t"` while `.strip()` removes
every `isspace()`*), and that one is a quotation of a withdrawal, not a live claim.

⚠ Borderline, recorded rather than filed: `docs/roadmap-to-launch.md:3088` says *"any other
whitespace is neither at column zero nor treated as indent"*. A `　`-only line is consumed by
the run loop's `not lines[i].strip()` disjunct, so it continues the run exactly as an indented line
would — the sentence is defensible if "indent" means the `startswith` test, and misleading
otherwise. I am not filing it; if M2's clause is deleted, sweep this one in the same pass.

---

**M3 — THE COUNT TRAIL IN BOTH LIVING ROWS AND THE ROADMAP STOPS AT ROUND 15 AND READS AS CURRENT.
THREE OF ITS FOUR FIGURES ARE STALE — THE SAME CLASS AS L1, IN THE SAME PARAGRAPH.**
`docs/backlog.md:294`, `:295`; `docs/roadmap-to-launch.md`

The last count step in rows #279 and #280 is:

> ⟳⟳⟳ **AND r15's CLAUDE half then took entries 144 → 145, the declared sum 1546 → 1547, binding
> 1555 anchors / 1547 entries, and the suite 296 → 297 cases**

Nothing after it marks those figures superseded — the next sentence explicitly labels the
*following* paragraph as historical, which leaves this one reading as the current state. Re-derived
from `sorted(glob("scripts/mutations/*.json"))` and `EXPECTED_MUTATIONS` at `3add5c2e`:

| Figure | Row says | Measured at HEAD | |
|---|---:|---:|---|
| `check-plan-code.json` entries | 145 | **148** | stale |
| declared sum | 1547 | **1550** | stale |
| binding | 1555 / 1547 | **1558 / 1550** | stale |
| suite cases | 297 | **297** | current |

Round 16 moved entries 145 → 148 and the sum 1547 → 1550; round 17 held both. Neither fold swept
the trail. ⭐ L1's remedy — *"the row now cites no current figure, because the partition moves with
every manifest change"* — is exactly right and was applied to the shard figure only, while its
three neighbours in the same sentence kept citing a value three rounds old.

**Remedy.** Either carry the trail forward in the same commit that moves it, or apply L1's own
answer to all four: drop the figures and name the command that prints them
(`check-plan-code.py --binding`). `check-withdrawal.py` cannot see this — its subject is figures
removed by a `docs/` diff, and these were never removed.

## Low

**L1 — "no polarity edit survives it" is overstated: ONE mechanical sweep rewrites the constant AND
its test literal, and the suite stays green. What catches it is `--binding`, not the oracle.**
`scripts/check-plan-code.py:578-579`, `:3994-3996`

A single find/replace of `THIS HARNESS DOES NOT CLAIM ` → `THIS HARNESS DOES CLAIM ` hits exactly
**2 sites** — `:588` (the constant) and `:3999` (the self-test literal) — so exact equality still
holds:

| Experiment | Result |
|---|---|
| `--self-test` under the sweep | **297/297 GREEN**; the report now reads `⛔ THIS HARNESS DOES CLAIM ANY OF THEM IS THE EXCEPTION, NOR …` |
| `--binding` under the sweep | **rc=1** — "its anchor is GONE … this mutation now measures nothing" |
| Restore | 297/297, `--binding` rc=0 |

⭐ So the system does catch it, and it is in CI (`.github/workflows/ci.yml:756`) — but the credit
belongs to mutation entry 737's anchor, not to the equality case. Narrow the two sentences to say
so; a maintainer who believes the oracle is self-sufficient will not know that deleting the
polarity entry removes the only protection against a coordinated edit. (⚠ I read `$?` after a pipe
on the first attempt and recorded `binding rc=0`; the figure above is from a direct exit code.)

---

**L2 — The else-arm's bound can be suppressed in exactly the world it describes, 297/297 green.**
`scripts/check-plan-code.py:3131-3133`, `:3940`

The arm's *deletion* IS covered — severing the bound clause away reds `⭐ #280: ...and it states
the no-frame traceback BOUND rather than hiding it` (296/297), so M4's "nothing is lost" is true.
But `_w3` is the only fixture reading it, and `_w3` reaches the arm via prose, not via a no-frame
traceback. Sever:

```python
said = (("read the window — ⚠ and note a traceback with NO frames …")
        if ":" not in se else "read the window")
```

`_w3`'s stderr is `a plain note, carrying no exception line` (no colon) → case green, **297/297**;
a real `sys.tracebacklimit = 0` child's stderr is `RuntimeError: QUOTABLE` → the sentence stating
the bound disappears from the only world the bound is about. Same shape as H1 and the same remedy
family; filed Low because the deletion direction is genuinely covered.

---

**L3 — The commit says "Corrected at all three sites" and then names four.**
`git log -1 3add5c2e`

M2's narrow claim is live at **four** sites, measured:
`docs/backlog.md:294`, `docs/backlog.md:295`, `docs/roadmap-to-launch.md:3084`,
`scripts/check-plan-code.py:556` — which is also exactly what the parenthetical enumerates ("two
backlog rows, the roadmap, the script comment"). The count word is wrong, not the work.

## Checked and found SOUND

**The refusal oracle, attacked five ways.** Over a green control in a complete isolated tree, each
with restore verified by sha256:

| Attack at the emission / constant | Result |
|---|---|
| DROP the emission (`+ ". " + _REFUSAL` → `+ ". "`) | **296/297** — `...and the report still EMITS the refusal` fires |
| TRUNCATE (`_REFUSAL[:60]`) | **296/297** — same case fires |
| POLARITY, shipped entry 737 (`DOES NOT CLAIM` → `DOES CLAIM`) | killed, attributed to `⭐⭐ r17 H1: the refusal text is EXACTLY this, polarity included` |
| Each of the four clause deletions, entries 733–736 | killed, each attributed to the case it names |
| Rendered on a branch the fixture never reaches | n/a — `:3129` is the single emission site, and `_repq` reaches it |

So the fold is right that the *text* is pinned: no edit to `_REFUSAL` alone survives, and a
substring test has been replaced with an oracle that cannot be satisfied by anything the child
writes. H1 and L1 are about emission and coordination, not about the text.

**The stated BOUND at `_REFUSAL`, both halves, measured.** 280 characters / **282 UTF-8 bytes**;
`"/" in _REFUSAL` is **False**. `getconf NAME_MAX .` and `os.pathconf` both give **255**. Direct
test, not inference: `mkdir` with the exact constant as one component is **refused — "File name too
long"**; a 255-byte prefix succeeds but `_REFUSAL in prefix` is **False**, so it cannot satisfy the
emission case. The stated concession (a child writing the whole string to stderr would satisfy it)
is the real residual and the fold states it rather than hiding it.

**The five mutations.** shard0 **733, 734, 735, 736, 737** of 1550, each run separately in the
complete tree: all five `1 killed, 1 attributed to the case each names, 0 survivor(s)`, each over a
green control and re-control. Indices verified against
`sorted(glob("scripts/mutations/*.json"))` — 733–737 are exactly the four retargeted refusal
entries plus the new polarity entry.

**Counts, re-derived rather than read.** At `3add5c2e`: 62 manifests, **1550** entries,
`EXPECTED_MUTATIONS` sum **1550** over **62** keys, `check-plan-code.json` **148** entries, suite
**297/297**, `--binding` **1558 anchors / 1550 entries, 0 unbound**. The rise/fall accounting holds
in both directions: the diff retires one case (`the no-lines world is named as well…`) and replaces
one with two, net 0 → 297 (and `5fb42985` measures **297/297** independently); it retires one
manifest entry (the no-lines mutation) and adds one (polarity), net 0 → 148.

**L1's shard re-derivation reproduces exactly.** 0-based `--shard0`, `muts[index-1::total]`:

| Revision | Entries | shard 7/8 | shard 8/8 |
|---|---:|---:|---:|
| `2c33738c` | 1547 | **19** | **18** |
| `5fb42985` (r16 fold) | 1550 | **19** | **19** |
| `3add5c2e` (HEAD) | 1550 | 19 | 19 |

So "19/18" and "19/19" are both correct, and "18 at this commit" is indeed unsupported at HEAD.

**M2's narrow claim is TRUE.** I surveyed the live path for anything deciding exception-hood:
`FRAME_LINE` (`:531`) decides frame-shape — `match('  File "f", line 1')` True,
`match('  prose')` False; `parse_fail_names` (`:3322`) decides only a stripped `[FAIL] ` prefix;
`diagnostic_tail` (`:455`) is pure slicing with no predicate; `_is_type_name` and
`is_exception_heading` survive only in comments; no `isidentifier()` and no `*Error` string test
exists outside `_self_test` expectations; the four `except SyntaxError:` clauses catch the
harness's own `ast.parse` failures, which is not a line classification. Nothing left decides
whether a line is an exception.

**M1's two narrowed witnesses both reproduce**, through the production function:
`lines_after_frame_runs('  File "f"\n　\n')` is `[]` and `　END` is returned as `END`.
I also derived the rule myself from `:690-717` and state it here as the contract a reader needs, so
the "recoverable from the code" claim is tested rather than assumed: *a run opens at a line that is
non-blank after `.strip()` and begins with `" "` or `"\t"`; it extends over every following line
that is either blank after `.strip()` or begins with `" "`/`"\t"`; the run must contain at least one
`^[ \t]+File "` line; the first line not consumed is appended `.strip()`ped, and EOF appends
nothing.* Eleven inputs confirm it, including indented prose inside a run, blank-line absorption,
NBSP and vertical-tab leads, two separated runs preserving order, and no-frame streams returning
`[]`. The surviving prose does not contradict that rule — except at `:712-714`, which is M2.

**M4's new else-arm text is TRUE, verified with a real child**, not by reading:
`sys.tracebacklimit = 0; raise RuntimeError("QUOTABLE")` through production `run_mutations` renders

```text
⚠ WHAT THE CHILD ITSELF SAID — read the window — ⚠ and note a traceback with NO frames (for
example under `sys.tracebacklimit = 0`) also lands here:
    RuntimeError: QUOTABLE
```

— so the arm is reached, the bound is stated, and the window does quote a line, which is exactly
why the deleted "read no line it could quote" was false. The retirement of the world-naming case is
also sound: deleting the bound clause reds the surviving case (296/297), and `_w3`'s child writes no
`sys.tracebacklimit = 0` token, so that case is not ambiently satisfied the way the r16 refusal case
was.

**M3's sweep, re-run over all three spellings, whitespace-insensitively** (so wrapped lines count),
across `scripts/` and `docs/` plus top-level `*.md`: **84** hits, **15** of them in living documents
or scripts, **69** in frozen `docs/reviews/` testimony. Of the 15: 6 in `docs/backlog.md` (2
quoting the r17 M3 withdrawal, 2 in #280's explicitly superseded-and-critiqued remedy proposal, 2
the `column_zero_after_frames` rename history), 3 in the roadmap (rename history and withdrawal
explanation), 6 in the script (5 quoting withdrawals or the refuted claim, 1 the rename). **Exactly
one is ASSERTING rather than QUOTING** — `:712-714`, which is M2 above. Both of the live assertions
r17 M3 named are gone; the classification of the two hyphenated #280 remedy references as
superseded matches what the row's own following sentences say.

**The 294/297 partial-copy control reproduces.** A `scripts/`-only tree gives **294/297**, the three
reds being the HARNESS_TREE-completeness cases naming `supabase`, `docs`,
`node_modules/typescript`, `.claude/hooks`, `.github/workflows` as missing. A red control is a
CANNOT RUN, so discarding that run rather than reporting it was correct.

**The guard population reproduces exactly**: **46** `scripts/check-*.py` on disk; **34** distinct
`check-*.py` referenced in `ci.yml`; 2 in `schema-gates.yml`; union 35; **11** on disk referenced by
neither workflow (`check-anon-exposure`, `check-catalog-coverage`, `check-ci-watched`,
`check-closing-table`, `check-handoff-path`, `check-merge-ready`, `check-paid-caller-arrival`,
`check-plan-progress`, `check-review-decision`, `check-selection-card`, `check-sentinel-meanings`);
zero referenced but absent. The 53-command set decomposes reproducibly: `ci.yml` carries **25**
distinct no-argument invocations, **25** distinct `--self-test` invocations, plus the three
additional forms (bare `check-provenance`, bare `check-withdrawal`, `check-plan-code --binding`) =
**53**, with `--base origin/master` on the two base checks run beside it.

**THE GUARD SET, RUN INDEPENDENTLY, REPRODUCES "52 GREEN / 1 RED" EXACTLY — and the one red is
this half's own absence, which is now gone.** I reconstructed the set from `ci.yml` by regex rather
than by retyping the fold's list, so the denominator is derivable and not asserted:

| | commands | result |
|---|---:|---|
| My raw reconstruction | **55** (27 default / 25 `--self-test` / 3 extra) | 53 green / 2 red |
| ⚠ minus two forms CI never runs bare | **53** | **52 green / 1 red** |
| …after this file existed | 53 | **53 green / 0 red** |

⚠ **The correction is mine, not the fold's.** My regex stopped at the line continuation in
`ci.yml:552` and `:577`, so it manufactured bare `check-dashboard-entry` (green) and bare
`check-review-recorded` (red) as if CI invoked them with no arguments. CI invokes both only as
`--self-test` (`:496`, `:174`) and in PR-only multi-line forms. Dropping those two gives **25
distinct no-argument + 25 distinct `--self-test` + 3 additional = 53**, which is the fold's set and
the fold's tally. The single red was `check-review-rounds` rc=1 for the missing round-17 Claude
half; re-run after writing this file it is **rc=0** — *"408 parsed, 18 pre-existing exemptions, 0
silent gaps; 255 codex-review verdict(s) read, none contradicted."*

`check-review-recorded` bare is **rc=1** at `3add5c2e` — pre-declared, by design, and not filed:
*"17 round(s) ran and guarded code was committed after every one of them."* The green point is
`db96e31f`. `check-memory-link.py` exits 0 while its corpus is absent — recorded under CANNOT RUN,
not counted as a measurement.

⚠ **The guard run changed nothing**: 0 dirty paths before, 0 after, `git status --porcelain`
identical.

## CANNOT RUN

**These are verification failures. Treat each as NOT RUN, never as a pass.**

- **A full local `--mutate .` and the eight-shard matrix.** Six single-entry shards verify six
  entries; they say nothing about the population of 1550. The local eight-shard form is known to
  time out here, so this cannot be closed on this machine — it is CI's to answer.
- **`check-test-counts.py` against a real `jest-results.json`.** Only its `--self-test` ran; its
  live subject did not.
- **The PR-event forms of the PR-only guards, and a fresh CI replay.** `check-merge-ready` and the
  PR-event paths are unreachable from a local worktree.
- **`check-memory-link.py`'s live subject.** It exits 0 while printing that its corpus is absent
  here; the self-test ran, the measurement did not.
- **`--mutate .` for H1's and H2's severs.** Both findings are established by direct sever over a
  green control, which is sufficient for the finding; neither was run through the manifest harness,
  so no attribution figure is claimed for them.
- **The child-via-filename attack as the reviewer ran it.** I measured the *bound* instead
  (`mkdir` refusal at 282 bytes), which refutes the filename channel; I did not reconstruct the
  reviewer's directory-named child, so that specific reproduction stands on their testimony.

## Instruments

Venv-first `PATH`, **Python 3.12.9** (`$PWD/.venv/bin`), **stdin closed (`</dev/null`,
`subprocess.DEVNULL`) for every guard and every probe**. Every sever ran on a **complete** tree
copy built with `tar` plus a `node_modules` symlink, never on a tracked file: `297/297` proved on
the copy before any sever, sha256 compared before and after every restore
(`b57484911f952e62b6bf4f4f8653bed30bbf2ac1cdb78f7efc0d3384b4045a48`), and a green re-control after
each. Production `run_mutations` and real children throughout; `ast` for constant extraction and
for the entry/sum accounting, `git ls-tree`/`git show` for historical revisions. No `git` command
was run in the primary working directory.

⚠ **Three instrument failures, recorded because a silent one is how a negative gets believed:**

1. `python3 - <<'EOF' … EOF </dev/null` — the later redirect wins, so the heredoc program was never
   read and a sever silently did not apply. The run that followed showed 297/297 and a probe
   reporting the refusal present, which looked like a *result*. Caught by a `grep -c` known-positive
   on the severed text returning **0**. Every sever after that reports its own known positive, and
   `probe2.py` prints `SEVER VISIBLE TO THIS MODULE:` from `inspect.getsource` of the loaded module.
2. bash `printf '%s'` interpreted `—` into an em dash, so a sever text did not match the source
   (which holds the six-character escape). Caught by the sever script refusing on
   `occurrences == 0` rather than proceeding. Sever texts are written with a tool that does not
   process escapes.
3. `--binding` rc read after a pipe (`| tail`) reported **0** on a run that actually exited **1**.
   Re-measured directly. This is the repository's own *never read `$?` after a pipe*.

⚠ A fourth, in a finding rather than an instrument: M1's first `--binding` experiment used an
ambiguous anchor (2 sites) and went rc=1 for the wrong reason — a red that would have *confirmed*
the claim under review. Recorded in M1.

**Worktree:** 0 dirty paths before this review; this file is the only change. No commit, no push,
no merge.
