# Adversarial review — the selection-card guard, ROUND 2 (Claude half)

**Subject:** `scripts/check-selection-card.py`, `.claude/hooks/enforce-selection-card.sh`,
`scripts/mutations/check-selection-card.json`, and the r1 edits to `docs/portable-practices.md` §19
and `docs/process-rationale.md`. `gen-backlog-page.py` is a different subject and was not reviewed.

## PROOF OF SUBJECT

```
$ git log --oneline -1
71f449a8 Fold r1 on the selection-card guard: two Blockings, one from each half

$ python3 scripts/check-selection-card.py --self-test | tail -1
42/42 passed

$ grep -n "MAX_OPTIONS\|MIN_DESCRIPTION_DENSE\|RECOMMENDED = " scripts/check-selection-card.py
76:RECOMMENDED = re.compile(r"\(\s*recommended\b[^)]*\)[\s*_`]*$", re.I)
84:MIN_DESCRIPTION_DENSE = 15
87:MAX_OPTIONS = 4
```

Two lines that exist only in this working tree (neither is in `4fe410ca`, the commit that created
the guard):

* `scripts/check-selection-card.py:84` — `MIN_DESCRIPTION_DENSE = 15`
* `.claude/hooks/enforce-selection-card.sh:52` — `print("other" if (name is not None and name != "AskUserQuestion") else "card")`

## METHOD

All mutation work was done on copies under
`…/scratchpad/card-r2/`; the repo's scripts were never edited. Confirmed after the fact:
`git status --porcelain` shows only the concurrent Codex half's verdict file.

1. **Anchor audit.** Every `edits` old-text in the manifest counted against the file on disk: 8/8
   resolve **exactly once**. No orphan. (r1's orphan is genuinely closed.)
2. **Manifest sweep on a copy.** All 8 entries applied over a control proved green (42/42):
   **8/8 killed, every one via the case it names.** §22 attribution holds.
3. **16 further mutations of my own** over the same control. **7 survived** (below).
4. **Unfalsifiability probe.** Three neuterings (`card_problems → []`, `payload_of → []`,
   `main → 0`) run against all 42 cases; 12 cases stay green under total deletion of the rule.
5. **Live hook matrix** — 15 stdin shapes plus a fake `python3` on `PATH`, exit codes measured.
6. **False-positive hunt** — 30 well-formed labels and descriptions fed to `card_problems`.

---

## Blocking

### B1 — §19's own "*Recommended*, **with its reason**" is still refused, and the message says "nothing is marked"

`scripts/check-selection-card.py:76`

```python
RECOMMENDED = re.compile(r"\(\s*recommended\b[^)]*\)[\s*_`]*$", re.I)
```

r1's Claude half (M2) opened this: §19 says *"Exactly one is marked Recommended, **with its
reason**"*, and the guard refused §19's own phrasing. The fold closed **one** rendering of that —
the reason **inside** the parenthesis — and left the other, which is the more natural one. Measured:

| label | verdict | message |
|---|---|---|
| `A — Ship it (Recommended — costs one review round)` | PASS | — (r1's fix) |
| `A — Ship it (Recommended) — it is reversible` | **REFUSED** | *"nothing is marked (Recommended)"* |
| `A — Ship it (Recommended).` | **REFUSED** | *"nothing is marked (Recommended)"* |
| `A — Ship it (Recommended):` | **REFUSED** | *"nothing is marked (Recommended)"* |
| `A — Ship it (Recommended: see ADR-0010 (v2))` | **REFUSED** | *"nothing is marked (Recommended)"* |

This is a **false positive that blocks a compliant card**, and the message is worse than the block:
the reader is told *nothing is marked (Recommended)* while looking at a label whose literal text is
`(Recommended)`. It is the failure r1's Blocking was about — block correctly, then misdirect the
repair — except here the block itself is wrong, so there is no repair to find. A person who trusts
the message will delete a marker that was already there.

The fold's own comment (`:68-75`) states the design goal as *"a reason may ride inside it"*. The
anchor was chosen to defeat prose-in-the-middle, and it does that job; it also catches a full stop.

**Change.** Let the anchor tolerate terminal punctuation and a trailing dash-clause. Validated
against every label the two r1 halves fought over — the Codex direction (prose mid-label) still
refuses, the Claude direction now passes:

```python
RECOMMENDED = re.compile(
    r"\(\s*recommended\b[^)]*\)[\s*_`]*([.,:;!]|\s+[—–-]\s+.*)?\s*$", re.I)
```

| label | want | current | proposed |
|---|---|---|---|
| `A — Ship it (Recommended)` | mark | ✓ | ✓ |
| `A — Ship it (Recommended).` | mark | ✗ | ✓ |
| `A — Ship it (Recommended) — it is reversible` | mark | ✗ | ✓ |
| `A — Ship it (Recommended — costs one round)` | mark | ✓ | ✓ |
| `A — Ship it **(Recommended)**` | mark | ✓ | ✓ |
| `A — Explain what (Recommended) means to a reader` | **no** | ✓ | ✓ |
| `A — Compare (Recommended) with (Preferred) wording` | **no** | ✓ | ✓ |

Nested parentheses (`(Recommended: see ADR-0010 (v2))`) remain refused under both; I would leave
that, but the message must stop asserting *nothing is marked* — see M5.

---

## High

### H1 — r1's H-3 fix is defeated by the exact interpreter H-3 was written about, and now blocks the wrong tool

`.claude/hooks/enforce-selection-card.sh:45-63`

```bash
DETECT=$(printf '%s' "$INPUT" | python3 -c '…' 2>/dev/null)
DETECT_RC=$?
if [[ $DETECT_RC -ne 0 || -z "$DETECT" ]]; then … exit 1; fi
[[ "$DETECT" == "other" ]] && exit 0
```

r1 H-3's measured threat list included *"a `python3` that prints a banner on stdout before
running"*. Only **stderr** is discarded (`2>/dev/null`), and the skip test is **exact string
equality**. A banner makes `DETECT` = `"pyenv: shim initialising\nother"`, which is neither empty
nor `"other"`, so:

* the cannot-run branch the fold built **never fires** — `DETECT_RC` is 0 and `DETECT` is non-empty;
* control falls through to the checker, which is handed a **`Bash` payload**, correctly reports
  CANNOT RUN, and the hook renders the **§19 selection-card panel** over it.

Measured with a two-line shim at the head of `PATH`:

```
$ printf '{"tool_name":"Bash","tool_input":{"command":"ls"}}' | PATH=…/fakebin:$PATH bash .claude/hooks/enforce-selection-card.sh
rc=2
╔══════════════════════════════════════════════════════════════════════════╗
║  ⛔ BLOCKED — this selection card does not follow portable-practices §19  ║
╚══════════════════════════════════════════════════════════════════════════╝
pyenv: shim initialising
```

The direction inverted rather than closed: before the fold this was a silent `exit 0`; now it is a
wrong **block** whose panel says nothing about the interpreter, with the banner spliced in as the
body. `.claude/settings.json` currently scopes the matcher to `AskUserQuestion`, which is the only
reason a real `Bash` call cannot hit this today — the hook is one matcher edit away, and the comment
at `:36-37` explicitly leans on that scoping. A well-formed card still passes under the same shim
(rc=0), so the guard is not wedged; it is mis-aimed.

**Change.** Do not compare against unbounded stdout. Take the last line and make the token
distinctive:

```bash
DETECT=$(printf '%s' "$INPUT" | python3 -c '…' 2>/dev/null | tail -n 1)
```

and have the detect script print `__card__` / `__other__` / `__unreadable__`, so stdout noise cannot
be mistaken for a verdict. Add a case that runs the hook with a banner-printing `python3` on `PATH`
— it is four lines and it is the fixture r1 already named.

### H2 — Undecodable stdin renders a Python traceback inside the refusal panel, and exits **1**, not 2

`scripts/check-selection-card.py:403`

```python
    raw = sys.stdin.read()
```

r1 L-5 closed the traceback-in-the-panel defect for the two paths it found (`payload_of`,
`card_problems`, both now wrapped at `:404-408` and `:410-418`). `sys.stdin.read()` sits **outside
both** try blocks. Measured:

```
$ printf '\xff\xfe garbage' | python3 scripts/check-selection-card.py ; echo rc=$?
Traceback (most recent call last):
  File ".../scripts/check-selection-card.py", line 427, in <module>
    sys.exit(main())
  File ".../scripts/check-selection-card.py", line 403, in main
    raw = sys.stdin.read()
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte
rc=1
```

Two separate defects:

1. **The traceback is back in the panel body.** The hook prints `$VERDICT_OUT` verbatim at `:78`, so
   the reader gets a stack trace where the §19 explanation belongs — the exact thing L-5 removed.
2. **The documented exit contract is broken.** The docstring's FAILS IF (`:49`) says *"the input is
   not readable as an `AskUserQuestion` payload -> exit 2, CANNOT RUN, never a pass."* This path
   returns **1**. The self-test case *"an unreadable payload exits 2, never 0"* (`:360-361`) asserts
   `== 2` for `{not json` and `""` only, so the one input class that returns 1 is the one no case
   looks at.

It fails **closed** — the hook treats any non-zero as a block — so this is High, not Blocking. But
`rc=1` is the hook's own "could not run" signal in the other branch, and having the checker emit it
for a different meaning is a collision waiting to be read wrong.

**Change.** Move the read inside a guard and give it the CANNOT-RUN grammar:

```python
    try:
        raw = sys.stdin.buffer.read().decode("utf-8")
    except Exception as exc:                                       # noqa: BLE001
        print(f"CANNOT RUN — stdin is not UTF-8 ({exc}). Treat this as NOT CHECKED.", file=sys.stderr)
        return 2
```

Extend the existing case with `_rc_for_bytes(b"\xff\xfe") == 2`.

### H3 — For a near-miss exit, the advice manufactures the two-options-same-work defect §19 exists to prevent

`scripts/check-selection-card.py:144-160`

The exit test is `QUESTION_EXIT.search(labels[-1])` — the literal `i have a question`. The advice
branch only asks *how many options are there*, never *is the last option already trying to be the
exit*. Measured:

```
input : C — I have questions about these        (plural — a near-miss)
output: the last option is 'C — I have questions about these', not a question-shaped exit.
        §19: add 'D — I have a question about these'.
```

Following that instruction produces a four-option card whose C is *"I have questions about these"*
and whose D is *"I have a question about these"*. Those are **the same work in different words** —
the defect §19 was written about, and the one the guard's own docstring (`:33-35`) says it cannot
see. So the resulting card **passes this guard clean** while violating the rule the guard enforces.
`C — Ask a question first` behaves identically.

This is r1's Blocking one layer out: the advice is schema-legal this time, but following it still
produces a second, different failure — and this one is invisible to the machine.

**Change.** When the last label is a near-miss (matches something like
`r"\b(question|ask|clarif|unclear)\b"` but not `QUESTION_EXIT`), say REWORD, not ADD:

```python
near = re.search(r"\b(question|questions|ask|clarify|unclear)\b", labels[-1], re.I)
fix = (f"REWORD option {len(labels)} to "
       f"'{chr(ord('A') + len(labels) - 1)} — I have a question about these' — it is already "
       f"reaching for the exit; adding a second one would give you two options doing the same work"
       if near else …)
```

### H4 — The dense-description floor is instance-not-class: one space re-imposes the ASCII floor, so every Korean description is refused

`scripts/check-selection-card.py:169`

```python
            floor = MIN_DESCRIPTION if len(desc.split()) > 1 else MIN_DESCRIPTION_DENSE
```

The comment at `:165-168` states the claim correctly — *"the floor's own claim is about
INFORMATION, not `len()`"* — and then implements a proxy that measures **spaces**, not information
density. r1 M-4's fixture had no spaces, so the fixture passes and the class does not. Measured:

| description | script | tokens | verdict |
|---|---|---|---|
| `今すぐ出荷する。巻き戻せるがレビューを一回失う。` | JA | 1 | PASS (r1's fixture) |
| `PR を今すぐマージする。巻き戻せるがレビュー一回分を失う。` | JA + one Latin term | 2 | **REFUSED** (30 chars) |
| `今すぐ出荷する。　巻き戻せるが一回失う。` | JA, ideographic space U+3000 | 2 | **REFUSED** (20 chars) |
| `지금 배포한다. 되돌릴 수 있다.` | KO | 5 | **REFUSED** (18 chars) |

Korean is space-delimited, so **no Korean description can ever reach the dense floor** — the
relaxation is unreachable for an entire script. Japanese loses it the moment a Latin product name or
an ideographic space appears, which is ordinary technical Japanese.

It also runs the other way: a **single 15-character token** clears the 40-character floor. A bare
URL passes:

```
description: https://github.com/anthropics/claude-code/pull/12345   → PASS
description: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa               → PASS
```

**Change.** Measure the thing the comment claims to measure — script width, not spaces:

```python
def _is_dense(s: str) -> bool:
    """East-Asian wide characters carry ~2.5× what an ASCII one does, so they clear a lower floor.
    ⚠ MEASURED BY SCRIPT, NOT BY SPACES (r2 H-4): Korean is space-delimited and dense, so a
    space-count proxy makes the relaxation unreachable for a whole writing system."""
    chars = [c for c in s if not c.isspace()]
    return bool(chars) and sum(
        unicodedata.east_asian_width(c) in "WF" for c in chars) * 2 > len(chars)
```

Validated against all seven descriptions above: every want-dense row is dense, every ASCII row
(including the URL and the 40-`a` token) is not. Keep both r1 fixtures as cases and add the Korean
one and the URL one — the URL is what pins the *other* direction.

---

## Medium

### M1 — `MIN_DESCRIPTION_DENSE = 15` is pinned only above 2 — r1's own L-2 defect, reintroduced on the new constant

`scripts/check-selection-card.py:84`. r1 L-2 found that `MIN_DESCRIPTION = 40 → 6` survived because
the only fixture was 5 characters, and fixed it with a boundary pair (`:310-313`). The fold added a
second floor constant and gave it a single 2-character fixture (`出荷`, `:306`). Measured on a copy:

```
KILLED-by-OTHER  MIN_DESCRIPTION_DENSE 15 -> 3    (killed by an unrelated case, not the named one)
       SURVIVED  MIN_DESCRIPTION_DENSE 15 -> 14
```

The number 15 — what the fold's own comment claims (*"24 CJK characters hold roughly what 60 ASCII
ones do"*) — is asserted by nothing. **Change.** Add the boundary pair the existing floor already
has: 14 dense characters refused, 15 accepted.

### M2 — The REPLACE branch's letter is unpinned, and the advice contradicts itself above four options

`scripts/check-selection-card.py:152-156`. The arithmetic is **correct** where it matters — I
checked every count:

```
n=3 : "add 'D — I have a question about these'"                        ✓
n=4 : "REPLACE option 4 with 'D — I have a question about these'"      ✓
n=5 : "REPLACE option 5 with 'E — …' — the tool accepts 4 options at most"
```

Two problems. First, dropping the `- 1` from `chr(ord('A') + len(labels) - 1)` **survives** — the
case at `:269-271` asserts `"REPLACE option 4" in …` and `"add 'E" not in …`, and the mutant emits
`with 'E`, which neither string sees. Second, at n≥5 the sentence tells you to keep five options in
the same breath as asserting the ceiling is four.

**Change.** Assert the letter, not just the verb: `"REPLACE option 4 with 'D —" in _exit_advice(4)`.

### M3 — `MAX_OPTIONS` shapes the advice but never enforces the ceiling; a 5-option card passes clean

`scripts/check-selection-card.py:87` is read only at `:153` and `:156`. Nothing refuses a card with
more than four options. Measured — a five-option card with letters A–E, a leading `(Recommended)`,
full descriptions and a proper exit:

```
problems: NONE
```

The tool then refuses it. That is r1's Blocking restated: the guard blocks at the point of use
precisely so the schema does not have to, and it knows the number. **Change.** Refuse above
`MAX_OPTIONS` with the same message the advice already carries, and add a case.

### M4 — Two declared counts went stale in the fold, in the two documents that point at this guard

* `docs/portable-practices.md:820-821` — *"(`scripts/check-selection-card.py` +
  `.claude/hooks/enforce-selection-card.sh`, **24 cases, 6 mutations**)"*
* `docs/dev-process.md:136` — *"(`--self-test`: **24 cases**)"*

Actual: **42 cases, 8 mutations**. The fold's commit message records `24 -> 42` and `6 -> 8`, and it
edited `portable-practices.md` in the same commit (the slot-cost paragraph) without touching the
count two lines above it. `dev-process.md` was not in the fold's file list at all.

The interesting part is that **`check-selftest-counts.py` cannot see either**, and passes:

```
$ python3 scripts/check-selftest-counts.py
self-test counts: 33 script(s) declare a count, every one verified by running it   rc=0
```

`check-selection-card.py` **is** pinned in its `POPULATION` (`:92-95`) and its own docstring
(`:5`) correctly says 42. The gate reads the *script's* declaration; the two prose declarations are
outside its corpus. `dev-process.md` calls itself *"the truth… these lines are pointers, not
restatements"* — a count in a pointer row is a restatement, and it drifted within one commit of
being written. This is the fourth declared-count drift the same table records.

**Change.** Fix both numbers. Then consider whether `check-docs.py` should read `--self-test: N` /
`N cases` claims out of `docs/*.md` and reconcile them against the same `count_drift` function —
that is the one direction nothing currently observes.

### M5 — The block panel's recipe no longer matches what the guard enforces

`.claude/hooks/enforce-selection-card.sh:80-86`. The panel is what the person sees at the moment of
the block, and r1's Blocking was entirely about that moment. Two mismatches introduced by the fold:

* **The 3-option minimum is absent.** r1 M-1 added a refusal (`check-selection-card.py:102-106`)
  whose message is *"2 option(s) … §19 wants a decision, not a confirm"*. The recipe under it lists
  five bullets and none mentions a minimum. Someone blocked for this reads a recipe that does not
  contain the rule they broke.
* **"EXACTLY ONE is marked (Recommended)"** is now false for the guard *and* for §19. r1 M-5
  relaxed multi-select to *at least* one (`:130`, and the case at `:230-232`), but neither the panel
  nor §19's "The rule" paragraph (`docs/portable-practices.md:812-814`) was updated. §19 still reads
  *"Exactly one is marked Recommended, with its reason."*

Also worth a line in the panel: since B1 shows the *"nothing is marked (Recommended)"* message can
be emitted about a label that visibly contains the marker, that message should say what it actually
tested — *"no label ENDS with a (Recommended) marker"*.

**Change.** Add a `* at least THREE options — the exit costs a slot` bullet; change the recommended
bullet to *"one is marked (Recommended) and placed FIRST (several may be marked on a multi-select
card)"*; update §19's rule sentence to match; reword the not-marked message.

### M6 — The hook has no self-test and no mutation entry; both r1 fixes that live in shell are unguarded

`scripts/mutations/check-selection-card.json` mutates `scripts/check-selection-card.py` only, 8/8.
`.claude/hooks/enforce-selection-card.sh` — which is where r1's **Blocking (Codex)** and **H-3**
were fixed — has no `--self-test`, no mutation entry, and is not reachable by `--mutate .`.
`check-ratchet-contract.py` passes (rc=0) because its population is `scripts/`, not `.claude/hooks/`.

H1 and H2 above are both in or reachable through that shell, and neither was caught by anything the
fold added. The sibling guard shows the shape that works: `enforce-handoff-path.sh` is a thin shim
over `check-handoff-path.py --self-test` (10 cases). Here the **detection logic itself** lives in
the shell, so the shim pattern does not apply as-is.

**Change.** Move detection into `check-selection-card.py` (a `--detect` mode over the same stdin),
leave the shell as a dispatcher, and give the detection its own cases — including the banner shim
from H1. That is the only way the r1 Blocking fix gets a falsifier.

### M7 — Three looseness survivors, one of them the r1 M-3 fix shipping without its case

Mutations run on a copy over a green control; all survived 42/42:

| # | mutation | survives | what it means |
|---|---|---|---|
| X8 | `LETTER` `\s+\S` → `\s*\S` | yes | r1 M-3 rewrote the docstring (`:63-66`) to say *"AT LEAST ONE SPACE — the trailing space is required"*. **No case asserts it.** `A —Ship it` is refused today and nothing would notice if it stopped being |
| X4 | `QUESTION_EXIT` → `re.compile(r"question", re.I)` | yes | the exit phrase is pinned only by a fixture with no `question` in it, so any label containing the word would pass as an exit |
| X5 | `LETTER` `[A-Z]` → `[A-Za-z]` | yes | caught downstream by the ordering check, so behaviour is unchanged — but the uppercase requirement itself is unasserted |

Related and **not** a survivor, but unresolved from r1: `A—Ship it (Recommended)` (closed-up em
dash, standard typography) is still refused. r1 M-3 documented the asymmetry; the fold rewrote the
comment and did not decide the question. I would accept the hyphenated form with no space
(`\s*[—–-]\s*\S` plus a guard that the letter is followed by a dash) — but whichever way it goes,
it needs a case, because right now both directions are free.

---

## Low

### L1 — 12 of the 42 cases are absence assertions that survive deleting the whole rule

Neutering `card_problems` to `return []` leaves **20/42** green. Twelve of those assert
`card_problems(…) == []`:

```
a card following §19 passes                          a hyphen is accepted, not just an em dash
an en dash is accepted too                           the marker is case-insensitive
markdown emphasis around the marker still counts     a reason may ride inside the marker
the question-exit ignores case and trailing words    the question-exit option needs no rationale
a dense description with no spaces clears the lower floor
on a MULTI-select card the recommendation need not be first
two recommendations on a MULTI-select card are allowed
two options that are the SAME WORK pass — this guard cannot see that
```

This is the class r1 L-1 fixed once, with `bool(probs) and` at `:324`. Each of these is falsifiable
*for its own clause* (loosening `LETTER` to `[—]` does kill the hyphen case), so this is Low, not
High — but the set is large enough that a future refactor which quietly empties `card_problems`
would keep 20 green cases and a green manifest. **Change.** Where a case asserts an acceptance,
pair it with the refusal of the same input under a one-token perturbation, so the pair cannot both
be satisfied by deletion.

### L2 — The "real choice(s)" arithmetic is unpinned

`:105` — `max(0, len(options) - 1)` → `len(options)` **survives**; the case at `:255-257` only looks
for the substring `real choice`. A one-option card would then say *"leaves 1 real choice(s)"*.

### L3 — `INPUT=$(cat)` silently drops NUL bytes

`.claude/hooks/enforce-selection-card.sh:29`. On bash 3.2 (the macOS system bash this ran under)
`$(cat)` discards NUL without a message. `{"tool_name":"Bash"}\x00extra` becomes
`{"tool_name":"Bash"}extra`, which does not parse, so `DETECT` is `unreadable`, the checker runs and
the §19 panel is printed over a `Bash` payload (rc=2). Fails closed and is not reachable through the
current matcher; noting it because it is a second route to H1's wrong-tool panel.

### L4 — `git show HEAD -- docs/process-rationale.md` is the only r1 item I could not falsify

M-6's claim was that retiring the `gh` row left two false sentences. The fold's replacement text
reads correctly against the current `dev-process.md`, but "these two sentences are now true" has no
observation that could make it fail. Not a defect — flagging that it is a decision wearing a
checkbox, per the project's own gate rule.

---

## What I checked and found clean

* **Manifest anchors: 8/8 resolve exactly once.** r1's orphan is closed and the re-audit held.
* **Manifest kills: 8/8, every one via the case it names** (§22 attribution), over a control proved
  green at 42/42 first.
* **`EXPECTED_MUTATIONS` bookkeeping.** Declared sum 407 = manifest total 407; the
  `399 → 405 → 407` narrative at `check-plan-code.py:2065-2068` matches the entries and states the
  reason for the rise. `check-selection-card.py` is in the `HARNESS_TREE` list (`:1933`) and in
  `check-selftest-counts.POPULATION` (`:92`).
* **Every gate green:** `check-ratchet-contract` `check-docs` `check-anchors` `check-review-rounds`
  `check-selftest-counts` all rc=0.
* **The r1 Blocking (Codex) fix works.** A bare card with no envelope now blocks:
  `{"questions":[…bad…]}` → rc=2. `tool_name: null` → rc=2. Empty stdin, `{not json`, `[]`, `"hello"`,
  `5`, `{"tool_name":"AskUserQuestion"}` → all rc=2. A named other tool → rc=0. No path through the
  hook reaches exit 0 without the checker having run, except the `"other"` skip — which is the one
  H1 is about.
* **The r1 Blocking (Claude) fix works** at the counts that matter: n=3 says ADD `D`, n=4 says
  REPLACE option 4 with `D`. The letters are right.
* Embedded newlines inside a JSON string label pass through the hook intact (rc=0 on a good card).
* 15 further mutations killed by the case that names them (multi-select handling, the `options[:-1]`
  exit exemption, the letter-ordering check, `.strip()`, the dense/ASCII split point, the empty-payload
  CANNOT RUN, the single-select multi-mark check, and the `MIN_DESCRIPTION` boundary).

---

## Verdict

Round 1 fixed real defects and its fold is honest about them. Round 2's findings are almost entirely
**the same classes one instance further out**: r1 M-2 fixed the reason-inside marker and left the
reason-after (B1); r1 H-3 fixed the silent-exit-0 and left the banner it named (H1); r1 L-5 fixed the
traceback in two paths and left the third (H2); r1 M-4 fixed the no-space CJK description and left
every spaced one (H4); r1 L-2 pinned `MIN_DESCRIPTION`'s number and the fold added a second
constant with the same weakness (M1). One finding, H3, is new: the advice manufactures a card that
passes this guard and breaks §19.

**Counts:** 1 Blocking · 4 High · 7 Medium · 4 Low.

**NOT CONVERGED**
