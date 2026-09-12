# Claude adversarial review — branch `mutation-coverage-gate`, round 3

**Subject:** `git diff c6d62f6c..7684c965` — the round-2 fixes. Branch head `7684c965`, base
`7674fe87`. All evidence below was taken against a `git archive HEAD` copy at
`…/scratchpad/mcgr3`, never the dirty checkout; mutations were applied to staged copies in
`$TMPDIR`. `--mutate .` was not run.

## PROOF OF SUBJECT

(1) The current `NO_MUTATIONS_RE`, `scripts/check-ratchet-contract.py:256`:

```python
NO_MUTATIONS_RE = re.compile(r"NO-MUTATIONS:[ \t]+(?!<)(\S[^\n]*)")
```

(2) `self_exemption()`'s body, `:534-546`:

```python
def self_exemption() -> tuple[bool, bool]:
    """(exempt-from-R4, exempt-from-R3) for THIS file's own source.

    ⛔ CALLS THE REAL RULES, never a copy of them. An earlier version re-applied the two regexes
    directly and was already drifting from the rules by round 2 — `check_manifest` parses the
    docstring, and a case matching the whole file would have failed for a reason the rule does not
    care about. Asking the shipped functions is the only version that cannot disagree with them.
    `manifest_stems` is empty and `caller_blob` is "" on purpose: this asks whether the ESCAPES
    would exempt it, not whether it happens to have a manifest or a caller today.
    """
    own = Path(__file__).read_text(errors="ignore")
    rel = "scripts/check-ratchet-contract.py"
    return (not check_manifest(rel, own, set()), not check_caller(rel, own, ""))
```

(3) Manifest entry count: `len(json.load(open("scripts/mutations/check-ratchet-contract.json")))`
→ **9**.

STATUS: COMPLETE

---

## Findings

### Medium — round 2's fix carries a `except SyntaxError: doc = text` fallback that restores WHOLE-FILE scoping, and on the widened population it is reached, silent, and covered by no case

**Where:** `scripts/check-ratchet-contract.py:292-297` (the block round 2 added), reached through
`evaluate()` `:207-210`, which applies `check_manifest` — and **only** `check_manifest` — to the
non-guard population.

**What:** Round 2's Blocking was *"an escape is a DECLARATION; a declaration has a place"*, and the
fix parses the module docstring. But the fix wraps the parse in a handler whose fallback is the old
rule verbatim:

```python
    try:
        doc = ast.get_docstring(ast.parse(text)) or ""
    except SyntaxError:
        doc = text
    if NO_MUTATIONS_RE.search(doc):
        return []
```

If `ast.parse` fails, `doc` becomes the entire source and an ordinary comment grants the exemption
again — the exact defect round 2 removed, restored on the "could not run" path. It is a fail-open
handler inside the guard whose own R2 rule exists to forbid *"'could not run' reported as
success"*, and no `SCOPE_CASES` row supplies an unparseable fixture, so nothing reddens.

For **guards** this is unreachable: `check_contract` runs first in the same loop and its
`fail_open_handlers` calls `ast.parse` bare, so the whole gate dies with a traceback first
(measured — see Evidence). The widened non-guard population never sees `check_contract`, so there
the fallback is live.

**Failing scenario:** a new self-tested helper under `scripts/` that is not named `check-*` — the
population `discover_self_tested_nonguards` was widened to reach this round — acquires a UTF-8 BOM
(a Windows editor, a copy-paste, `iconv`). Python itself still runs it, its suite still passes, and
an ordinary implementation comment mentioning the marker now exempts it from R4 permanently and
silently. Round 2's own comment at `:289` names that comment as the realistic authoring route, and
`check-ratchet-contract.py` itself contains exactly such a line.

**Evidence:** one file, `scripts/widget-helper.py`, added to two otherwise identical copies of
`HEAD`. Its body is a docstring, an import, `# NO-MUTATIONS: note to self, we will declare this
properly later`, and a `--self-test` `main()`. The only difference is three leading bytes.

```
=== plain non-guard (control): rc=1
  |   scripts/widget-helper.py  [R4W_no_mutation_manifest]
=== BOM-prefixed non-guard: rc=0
  | NO MENTION of widget-helper.py anywhere in output
  | tail: ratchet contract OK
```

The unit-level matrix over `check_manifest` / `check_caller` directly (assembled markers, so this
review's own fixtures cannot grant anything):

```
  R4 exempt= True   module docstring (baseline true)
  R4 exempt=False   comment only (baseline false)
  R4 exempt= True   SYNTAX ERROR + comment
  R4 exempt= True   BOM + comment
  R4 exempt= True   null byte + comment
```

**Bound on the blast radius, measured rather than assumed.** I expected the debt-drift arm to make
this loud and it does *not* in the general case — a pinned entry that merely stops parsing stays in
`violating` and stays suppressed:

```
scripts/prior-art.py, BOM only:            rc=0, no mention
scripts/prior-art.py, BOM + the comment:   rc=1  scripts/prior-art.py [R4W_debt_paid_not_recorded]
```

So the eight pinned entries fail loud *if* they also carry the marker, and a **new, unpinned**
self-tested non-guard is the silent case. Today nothing is affected: all 55 files under `scripts/`
parse (measured), so this is a latent route, not a live miss.

**Fix:** `doc = ""` on the `SyntaxError` path (an unparseable file cannot have made a declaration,
so refusing the escape is the fail-closed reading), plus one `SCOPE_CASES` row — an unparseable
fixture carrying the marker in a comment, expecting `False`. Apply the same to `check_caller:167-169`,
which has the identical handler; that one is pre-existing, not this round's, but it is the same
rule and *instance-not-class* is the mistake this branch has already paid for twice.

---

### Low — three comments in `check-ratchet-contract.py` state a rule the code no longer implements, and the fix that widened the pattern is what made them false

**Where:** `:244`, `:255`, `:531-532` (and `:129-136`).

**What:** Closing round 2's Medium deliberately replaced `[A-Za-z]` with `(?!<)`, so any non-`<`
non-space character now opens a reason. Four claims were left describing the old rule:

- `:244` — `# ⛔ THE REASON MUST BEGIN WITH A LETTER, AFTER AT LEAST ONE SPACE` — false.
- `:255` — ``# `[ \t]+` rejects "NO-MUTATIONS:`" (no space); `[A-Za-z]` rejects "NO-MUTATIONS: <why>".``
  — `[A-Za-z]` is not in the file; `(?!<)` is what rejects the placeholder.
- `:531-532` — the `self_exemption` block claims the case asserts the source does not satisfy either
  escape *"by ANY route: prose, fixture, or a comment explaining the defect"*. It now reads the
  module docstring only.
- `:129-136` — *"That is the only thing standing between this file and granting itself the two
  opt-outs it exists to police"*, of the assembled `_NM`/`_NC` markers. Docstring scoping is now
  what stands between them; the assembly is no longer load-bearing for the suite.

These matter because `:244` and `:255` are what a guard author reads to learn what to write, and
`:531` is the stated warrant for the only case that keeps this file honest.

**Evidence:** acceptance today, via the shipped functions on staged fixtures —

```
R4      R3       reason
ACCEPT  ACCEPT   `evaluate()` is pure; a mutation would only restate the self-test
ACCEPT  ACCEPT   3 lines of glue, no branches to weaken
ACCEPT  ACCEPT   "pure wrapper" - nothing to weaken
ACCEPT  ACCEPT   ⚠ prose match only; there is no suite
ACCEPT  ACCEPT   — the regex matched prose; there is no suite
ACCEPT  ACCEPT   the regex matched prose; there is no suite
REFUSE  REFUSE   <why>
divergent rows: 0
```

Six of seven begin with something that is not a letter and are accepted. The reach of the
self-exemption case, on staged copies of the file with one line appended:

```
  control                            rc=0  self-test: 40/40 passed
  + a COMMENT granting R4            rc=0  self-test: 40/40 passed
  + a FIXTURE string granting R4     rc=0  self-test: 40/40 passed
  + a COMMENT granting R3            rc=0  self-test: 40/40 passed
  + a DOCSTRING line granting R4     rc=1  [FAIL] this file does not exempt ITSELF … 39/40
```

And the markers written as plain literals instead of `"NO-" "MUTATIONS:"`:

```
markers written as PLAIN literals (assembly removed): rc=0  self-test: 40/40 passed
```

I am **not** proposing the assembly be removed — it is cheap defence in depth against a future
re-widening. Only the sentence claiming it is the sole barrier is now false.

---

### Low — `check-plan-code.py:2988` "The six cover …" was filed in round 2, the fix edited the two lines directly above it, and it now mis-describes NINE entries

**Where:** `scripts/check-plan-code.py:2986-2991`.

**What:** Round 2's Low reported this paragraph saying "six" over eight entries. The round-2 fix
changed `549 -> 557` to `549 -> 558` and `EIGHT` to `NINE` on the two lines immediately above, and
left the third number. The enumeration that follows still lists exactly the original six
mechanisms; neither the R3-escape entry, the debt-PAID entry, nor this round's docstring-scope
entry appears in it.

**Failing scenario:** a reader auditing coverage counts the enumerated mechanisms, gets six against
a declared nine, and concludes three entries are undocumented duplicates. Nothing mechanical reads
this prose, so it stays wrong; it has now survived a round in which it was named.

**Evidence:** verbatim at `HEAD`:

```
    # ⟳ 2026-09-12, SAME DAY, second slice: 549 -> 558. `check-ratchet-contract.py` joins with
    # NINE — the guard enforcing R4 had exempted itself since it was written, because the regex for
    # the written escape matched its own documentation of that escape. The six cover the widened
    # population (guards excluded, self-test required), the debt pin in both directions, the
    # NOT-EXAMINED clause that keeps an empty corpus from reading as paid, the evaluate() wiring,
    # and the escape regex itself.
```

---

## Round 2 findings — closed or not

| # | Round 2 finding | Status |
|---|---|---|
| Codex Blocking / Claude High | R4 whole-file scoped; a comment or literal exempts any other guard | **CLOSED.** `check_manifest` parses the module docstring. Measured on staged fixtures: docstring → exempt; comment → not exempt; string literal → not exempt; **class docstring, nested-function docstring and `__doc__ =` assignment are all not exempt** (module-only, the tight direction). Residual: the `SyntaxError` fallback, filed above |
| Claude Medium | both refusal messages print an example the guard itself refuses; siblings refuse five of seven plausible reasons | **CLOSED.** All three messages rewritten and none now prints a refused form; the probe table above shows 6/7 accepted, 0 divergent rows. The only refusal is the angle-bracket placeholder, which each message names explicitly |
| Claude Low | `check-plan-code.py:2988` "The six cover …" | **NOT CLOSED** — see the Low above |
| Claude Low | `total`'s hand-written `+ 1` lets the self-exemption assertion be deleted silently | **CLOSED.** Now `len(SELF_EXEMPTION_CASES)`, derived like every other group. Verified that defence-in-depth still holds: with the loop deleted and the length term kept, the suite prints 40/40 — but manifest entry 7 then **survives** (`rc=0`), so `--mutate .` goes red, exactly as round 2 argued |
| Claude Low | two comments disagree about where `_NC` is defined | **CLOSED.** `:434` now says "defined beside the patterns near the top", which matches `:136` |

## Round 1 findings — still closed at HEAD

R4 self-exemption (closed, and now closed as a class), `NO_CALLER_RE`'s identical hole (closed — no
match anywhere in this file's docstring), the "TENTH file" ordinal (absent; `check-plan-code.py:672`
records it as a retired number), "seven printers" (`:668` says FIVE), `m4_catalog.py rc=0` recorded
honestly as zero bytes / no suite (`:322`, `:326`), and the `R4W_debt_paid_not_recorded` mutation
(present, kills via its named case).

---

## Checked and found sound

**The nine mutations.** All nine anchors occur **exactly once** in `HEAD`'s source, names are
unique, and every one is killed **via the case it names**, over a control proved green first
(`self-test: 40/40 passed`). `parse_fail_names` was imported from the shipped
`scripts/check-plan-code.py`, not reimplemented:

```
CONTROL rc 0 | self-test: 40/40 passed
KILL  ×9 — each rc=1 with its `expect` string among the failing case names
```

Two kill through their named case alone; the rest also redden neighbours, none incidentally.

**The orphaned-anchor account is exact.** Comparing the manifest at `c6d62f6c` against `HEAD`'s
source: **exactly two** anchors — the `NO_MUTATIONS_RE` and `NO_CALLER_RE` lines — no longer occur
(`new_count 0`), and both were re-pointed in the same commit. No third anchor was orphaned.

**"The right answer was a missing case" is exact.** At `c6d62f6c`, replacing `check_manifest`'s
`if Path(path).stem in manifest_stems: return []` body with a `raise` leaves the suite at
**35/35 passed, rc=0** — nothing drove that branch. At `HEAD` the same probe raises
(`BRANCH REACHED`), and deleting the clause reddens *"a manifest exempts regardless of the
docstring"* — so `MANIFEST_BRANCH_CASES` covers the branch, not just the function.

**The retained `check-fixture-variation` exemption is live, and a dead one would be refused.**
Removing `check-ratchet-contract.py:check_manifest.text` makes that guard red with
*"passed the SAME value at every call site in the suite (2x `text_`)"* — the exemption's stated
reason ("two table loops, one argument expression each") is literally what the tool reports. Adding
a bogus key produces *"the exemption … is DEAD"*, rc=1, so removing the `.path` entry was
mechanically forced, not discretionary.

**"No file under scripts/ has a declaration today."** True. Across all 55 `scripts/*.py`, zero
module docstrings match either escape under the old `[A-Za-z]` pattern or the new one. The single
whole-file match anywhere is `check-ratchet-contract.py:289` — the round-2 comment itself, which
docstring scoping correctly ignores. Nothing legitimate was lost by requiring the docstring.

**`self_exemption()` is still meaningful.** With `manifest_stems=set()` and `caller_blob=""`,
`check_manifest` can return `[]` only via the escape, and `check_caller` can return `[]` only via
the escape (the empty blob can never match `invocation_re`). So `(False, False)` means precisely
"neither escape matched", not an accident of having a manifest or a caller. It reads its own
`__file__`, so under a staged mutation copy it checks the copy — proven by manifest entry 7, which
reddens that case and nothing else.

**`(?!<)` does not refuse anything a real author would plausibly write**, with one edge: a reason
that genuinely begins with `<`, e.g. ``NO-MUTATIONS: <1% of this file is branching logic``, is
refused. Both refusal messages name the cause ("an angle-bracket placeholder is refused — write the
actual reason"), so the author is one rephrase away. Backtracking is handled: two spaces then
`<why>` is still refused, two spaces then a letter is accepted.

**Arithmetic, all verified by running.** Manifest length **9**;
`EXPECTED_MUTATIONS["scripts/check-ratchet-contract.py"] == 9`; declared sum **558** —
`check-plan-code.py --self-test` → **128/128 passed** (it needs `node_modules/typescript`, so the
scratch tree was given a symlink; without it three cases correctly report CANNOT RUN).
`check-ratchet-contract.py --self-test` prints **40**, matching `# 40 cases` at `:30`;
`check-selftest-counts.POPULATION` has **37** members including `check-ratchet-contract.py`, and
`check-selftest-counts.py` → *"37 script(s) declare a count, every one verified by running it"*.
`check-fixture-variation.py` → OK, 460 parameters across 49 files, 7 exempt.
`check-guard-coverage.py`, `check-gate-falsifiability.py`, `check-selftest-counts.py --self-test`
all green. `check-ratchet-contract.py` itself → `ratchet contract OK`, 34 guards.

**Dashboard claims check out.** "9/9 mutations kill via the case each names" ✅; "Suite 40 cases" ✅;
"`EXPECTED_MUTATIONS` 549 → 558" ✅; "a comment no longer exempts, a string literal no longer
exempts, a docstring declaration still does" ✅; "accepts reasons starting with a backtick, digit,
glyph, dash or quote" ✅ (all five measured); "in any of the other 33 guards" ✅ (34 discovered);
"two mutations were ORPHANED by that fix" ✅ (exactly two); "nothing drove `check_manifest`'s
`stem in manifest_stems` branch at all" ✅.

**Noted, not filed (pre-existing, and fail-loud).** An unparseable *guard* does not produce a
NOT-RUN message — it produces a raw `SyntaxError` traceback out of `fail_open_handlers:97`, which
also calls `ast.parse` bare. That is loud, so it is not the hole above, but it means this one file
now has three `ast.parse(text)` sites (`:84`, `:97`, `:294`) with three different behaviours on the
same bad input: crash, crash, and silently-read-the-whole-file. If the Medium is fixed, giving all
three one answer is the cheap version.

---

## Verdict

**CONVERGED**, by this project's stated criterion — no new Blocking or High. Rounds 1 and 2 each
produced a Blocking; round 3 produces none. The round-2 fix does what it claims: R4 and R3 are now
the same rule, read from the same place, the self-exemption case asks the shipped functions rather
than a copy of them, all nine mutations attribute to their named case, and every numeric claim the
branch makes survives being re-measured.

The Medium should still land on this branch rather than the backlog — it is a two-line change
(`doc = ""`) plus one `SCOPE_CASES` row, and leaving it means shipping a silent route back to the
exact defect the branch was written to close, in the population it widened R4 to reach.
