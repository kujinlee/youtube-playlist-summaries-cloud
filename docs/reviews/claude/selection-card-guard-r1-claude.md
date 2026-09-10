# Adversarial review — the selection-card guard, round 1 (Claude half)

## PROOF OF SUBJECT

```
$ git rev-parse HEAD
4fe410caee3545db4055cc906c667111b765b5ff

$ git show --stat HEAD | tail -10
 .claude/hooks/enforce-selection-card.sh     |  71 +++++++
 .claude/settings.json                       |   9 +
 docs/dev-process.md                         |   2 +-
 docs/portable-practices.md                  |  10 +
 scripts/check-plan-code.py                  |   9 +-
 scripts/check-selection-card.py             | 288 ++++++++++++++++++++++++++++
 scripts/check-selftest-counts.py            |   4 +
 scripts/mutations/check-selection-card.json |  68 +++++++
 8 files changed, 459 insertions(+), 2 deletions(-)

$ python3 scripts/check-selection-card.py --self-test | tail -2
24/24 passed

$ shasum -a 256 scripts/check-selection-card.py .claude/hooks/enforce-selection-card.sh
dc09897adb55f3924aebafcf311a11867a7f5c334e03edc0f1303a6b27e56e37  scripts/check-selection-card.py
21a3a61a3ab24f70a4b7ef07b3f93167e8466df2437dccd80b8d024d5f4fdf27  .claude/hooks/enforce-selection-card.sh
```

Two exact lines from `scripts/check-selection-card.py`:

```
:62   LETTER = re.compile(r"^([A-Z])\s*[—–-]\s+\S")
:126          if len(desc.strip()) < MIN_DESCRIPTION:
```

Everything earlier on `fix/backlog-110-parser-completeness` (`gen-backlog-page`) was **not** reviewed.

## METHOD — and the corpus that made it worth doing

Every finding below is an input I constructed and an exit code I observed. Nothing is reasoned about
the code without running it. Scratch work is outside the repo; the repo's copies of both scripts were
never modified (mutations were applied to a copy under `scratchpad/card-r1/work/`).

**The population I measured against is real, not invented.** I extracted every `AskUserQuestion`
tool-use input this machine has ever emitted from `~/.claude/projects/*/*.jsonl`:

```
cards: 32   (49 questions, 172 options, deduplicated)
$ python3 runcorpus.py | tail -1
PASS: 5 of 32
```

That corpus is what turns finding **B1** below from a hypothetical into a number, and it is also how I
learned the tool's own schema, which no part of this commit accounts for. Extracted verbatim from the
Claude Code binary (`~/.local/share/claude/versions/2.1.267`):

> The available choices for this question. **Must have 2-4 options.** Each option should be a
> distinct, mutually exclusive choice (unless multiSelect is enabled). **There should be no 'Other'
> option, that will be provided automatically.**

> `label`: The display text for this option that the user will see and select. **Should be concise
> (1-5 words)** and clearly describe the choice.

---

## Blocking

### B1 — The block message prescribes a fix the tool's own schema forbids, for 22 of 49 real questions

`scripts/check-selection-card.py:118-121`:

```python
            problems.append(
                f"{where}: the last option is {labels[-1][:48]!r}, not a question-shaped exit. "
                f"§19: add '{chr(ord('A') + len(labels))} — I have a question about these'. "
```

Observed, on a card that is otherwise perfect and in the shape 29 of 49 historical questions use:

```
$ printf '%s' "$FOUR_OPTION_CARD" | python3 scripts/check-selection-card.py
  ✗ question 1 ('Next slice'): the last option is 'D — Triage the review files', not a
    question-shaped exit. §19: add 'E — I have a question about these'.
rc=2
```

The tool will not accept an `E`. `Must have 2-4 options` is a schema constraint, so an agent that
does what the block message says gets a *second* failure — a validation error from the tool this
time — and has to work out unaided that the real repair was to *replace* option D, not add option E.

Measured over the real corpus:

```
questions total: 49
questions with 4 options (the schema MAXIMUM): 29
  ... of those, no question-shaped exit -> guard says add a 5th: 22
```

**Why this is Blocking and not a nit.** The whole argument of the commit is that the rule was
*recalled instead of read*, and that a machine at the point of use fixes that. The block message **is**
the reading. For the modal card shape it reads out an instruction that cannot be carried out. A guard
that blocks correctly and then misdirects the repair is worse at the moment of use than the prose it
replaced, because the prose at least did not assert a wrong next step.

**Change I would make** — make the advice conditional on the count, and say why:

```python
            add_letter = chr(ord("A") + len(labels))
            fix = (f"add '{add_letter} — I have a question about these'"
                   if len(labels) < 4 else
                   f"REPLACE option {len(labels)} with "
                   f"'{chr(ord('A') + len(labels) - 1)} — I have a question about these' — "
                   f"AskUserQuestion accepts 2-4 options, so an exit costs you a choice")
```

The same 4-option ceiling deserves a sentence in §19 and in the hook's recipe block, because it
silently converts "up to four options" into "up to three real choices". That is a design consequence
of making §19 mandatory, and the human should be told it rather than discovering it.

---

## High

### H2 — `main()`'s exit code has no case; the guard can be turned into a no-op with 24/24 still green

The hook reads exactly one thing from this script: its exit code (`enforce-selection-card.sh:43-46`).
Nothing in the 24 cases executes `main()`. I mutated the delivered file on a copy:

```
  SURVIVED   p  main() returns 0 instead of 2 on problems
      24/24 passed  red=[]
```

`scripts/check-selection-card.py:284`, `return 2` → `return 0`, and the self-test is fully green, so
`check-plan-code.py --mutate .` is green, so **CI is green while every malformed card is admitted.**
The manifest's sixth entry is careful about the *library's* fail-open (`payload_of` returning `[]`)
and its comment says exactly the right thing —

```json
  "name": "an unreadable payload returns empty instead of raising (fail-open)",
```

— but the fail-open one layer out, in the only function the hook calls, is unguarded. The same is
true of the CANNOT-RUN `return 2` at `:277`.

**Change:** add two cases that run the entry point, e.g. via `subprocess` on `__file__` or by
refactoring `main()` to take `raw` and return an int:

```python
case("a bad card exits 2, because the hook reads only the exit code",
     lambda: _rc_for(json.dumps({"questions": card(["A — One", "B — Two", "C — Three"])})) == 2)
case("an unreadable payload exits 2, not 0", lambda: _rc_for("{not json") == 2)
case("a good card exits 0", lambda: _rc_for(json.dumps({"questions": card(GOOD)})) == 0)
```

and add the `return 2 → return 0` mutation to the manifest (`EXPECTED_MUTATIONS` 6 → 7, 405 → 406).

### H3 — The hook's CANNOT-RUN path is `exit 0`, silently, and I reached it with an ordinary broken `python3`

`.claude/hooks/enforce-selection-card.sh:32-41`:

```bash
IS_CARD=$(echo "$INPUT" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print("no"); sys.exit()
print("yes" if d.get("tool_name") == "AskUserQuestion" else "no")
' 2>/dev/null) || IS_CARD="no"

[[ "$IS_CARD" == "yes" ]] || exit 0
```

Measured, all with a **bad** card on stdin:

| stdin / environment | rc | outcome |
|---|---|---|
| malformed JSON envelope | **0** | card admitted, no message |
| JSON array envelope (`d.get` raises outside the `try`) | **0** | card admitted, no message |
| empty stdin | **0** | card admitted, no message |
| `python3` is a pyenv-style shim that exits 1 | **0** | card admitted, no message |
| `python3` prints a banner on stdout before running | **0** | card admitted, no message |
| `python3` absent entirely | 127 | not a pass, but by accident (`cat` was gone too) |

The last two are not exotic: a pyenv/asdf shim with no version selected, a conda activation banner, a
`sitecustomize` that warns on stdout. Any of them silently disarms the guard for a whole session, and
the hook says nothing — the failure is indistinguishable from a compliant card.

This is the project's own bolded rule inverted: *"'Cannot run' is a FAILURE, never a pass. If a check
cannot reach what it measures … it must fail loudly and say treat this as NOT RUN."* The **script**
obeys that rule scrupulously (`:276`, `CANNOT RUN — …. Treat this as NOT CHECKED, never as a pass.`);
the four lines of shell above it throw the verdict away.

Note the asymmetry: the *verdict* half already fails closed. I verified that a missing script, a
missing interpreter and an uncaught exception all yield a non-zero `VERDICT_RC` and therefore a block.
Only the *detection* half fails open — and detection is redundant, because
`.claude/settings.json:41` already restricts the hook to `"matcher": "AskUserQuestion"`.

**Change:** distinguish "not a card" from "cannot tell". Do not block (blocking every card when
python is broken wedges the session), but do not be silent either:

```bash
IS_CARD=$(printf '%s' "$INPUT" | python3 -c '...' 2>/dev/null)
DETECT_RC=$?
if [[ $DETECT_RC -ne 0 ]]; then
  echo "⚠ enforce-selection-card.sh: could not read the hook envelope (python3 rc=$DETECT_RC)." >&2
  echo "  The §19 card check DID NOT RUN. Treat this card as NOT CHECKED." >&2
  exit 1     # non-blocking error; stderr reaches the user
fi
```

⚠ **Scope note, stated rather than smuggled in:** `.claude/hooks/enforce-handoff-path.sh:32-42` has
the identical four lines and the identical hole. This commit copied a precedent, so the *class* is
pre-existing; the *instance* is new and is in the subject. Fix the instance here, file the sibling.

---

## Medium

### M1 — A card whose only alternative is the exit passes: the fake choice §19 exists to stop

```
$ printf '%s' '{"questions":[{"header":"H","options":[
    {"label":"A — Ship it (Recommended)","description":"<46 chars>"},
    {"label":"B — I have a question about these","description":"ask"}]}]}' \
  | python3 scripts/check-selection-card.py ; echo rc=$?
rc=0
```

`:81` is `if len(options) < 2:` — written before the exit option became mandatory. Once every card
must end with the exit, a two-option card offers **one** course of action. That is a confirmation
dialog wearing a selection card, and "an option list that is not really a choice" is the defect the
whole of §19 is about. `< 3` is the correct floor and it is exactly decidable, unlike the
same-work clause the docstring correctly disclaims.

### M2 — `(Recommended)` must be that literal string, so §19's own "with its reason" is refused as *no recommendation at all*

`:63` `RECOMMENDED = "(Recommended)"`, tested with `in` at `:101`. Measured:

| label | rc | message |
|---|---|---|
| `A — Ship it (recommended)` | 2 | "nothing is marked (Recommended)" |
| `A — Ship it (Recommended — it is reversible)` | 2 | "nothing is marked (Recommended)" |
| `A — Ship it **(Recommended)**` | 0 | — |
| `B — Keep the (Recommended) default from v2` (prose collision, A also marked) | 2 | "2 options marked (Recommended) on a single-select card" |

Row 2 is the one that matters: §19 says *"Exactly one is marked Recommended, **with its reason**"*, so
putting the reason beside the marker is a plausible reading of the rule the guard is enforcing, and it
is rejected with a message asserting the marker is absent when it is visibly present. The dash
handling is deliberately generous (`[—–-]`, three spellings, and the docstring explains why); the
recommendation token is the opposite and nothing explains why.

**Change:** match `re.compile(r"\(\s*recommended\b", re.I)` and keep the message literal as the
canonical spelling. That also removes the "2 options marked" false positive for any label whose
*prose* uses the word, because the marker then has to open a parenthesis.

### M3 — The dash rule is asymmetric, and the docstring documents the wrong half

`:62` `r"^([A-Z])\s*[—–-]\s+\S"` — `\s*` **before** the dash, `\s+` **after**. The docstring at `:43`
says *"(any dash, one letter, one space)"* and does not say the trailing space is mandatory.
Measured refusals of things a careful writer types:

| label | rc |
|---|---|
| `A—Ship it (Recommended)` (closed-up em dash — standard typography) | 2 |
| `A. Ship it (Recommended)` | 2 |
| `A) Ship it (Recommended)` | 2 |
| `A: Ship it (Recommended)` | 2 |
| ` A — Ship it (Recommended)` (one leading space) | 2 |

All five report *"option 1 is not lettered"* about a label that is plainly lettered, which is the
cry-wolf failure the `[—–-]` generosity was written to avoid — the generosity just stopped one
character early. `r"^\s*([A-Z])\s*[—–.):-]\s*\S"` covers every row above and still refuses a genuinely
unlettered label. Measured over the 172 real labels in the corpus, the proposal weakens nothing:

```
labels: 172   refused by OLD: 130   refused by NEW: 130
newly ACCEPTED by the proposal (0):
```

### M4 — The 40-character floor counts characters, so a dense non-ASCII description is refused

```
$ ... "description":"今すぐ出荷する。巻き戻せるがレビューを一回失う。" ...
  ✗ question 1 ('H'): option 1 carries 24 characters of description.
rc=2
```

24 CJK characters carry roughly what 60 ASCII characters carry, rationale and trade-off included. The
floor's own comment (`:65-68`) says it exists to tell *nothing at all* from *a real rationale* — which
is a claim about information, not about `len()`. A cheap improvement that keeps the intent: count
whitespace-separated tokens as well, and pass on either (`len(desc) >= 40 or len(desc.split()) >= 6`),
or scale the floor when the string has no ASCII spaces.

### M5 — On a multiSelect card, "recommended goes first" draws an arbitrary line

`:107-114`. With `multiSelect: true` and several options legitimately advised together:

* recommended = {A, C} → **rc 0**
* recommended = {B, C}, with A being "Neither" → **rc 2**, *"the recommended option is #2, not first"*

The relaxation at `:107` correctly recognises that "exactly one" is wrong for multi-select, then the
`elif` at `:111` applies a single-select rule to the same card. On a multi-select card the natural
first slot is often a "none of these" or the options have an intrinsic order (chronological, cheapest
first). The rationale in the message — *"so the reader meets the answer before the alternatives"* —
does not survive an answer that is a *set*. Either require only that **some** recommendation exists on
a multi-select card, or state in §19 that a multi-select card must lead with a recommended option.

### M6 — Retiring the `gh` row left two now-false sentences in the file that inherited it

Scope item 6, checked: `docs/process-rationale.md:292` does hold the full account
(*"### The `gh` two-remotes footgun — RESOLVED 2026-08-04"*, remote removed, `--repo` habit retained),
and nothing cites the *spine row* — the four other hits are historical plan docs citing the footgun
itself, which still lives in rationale. So the retirement is safe. **But `docs/process-rationale.md:262-263` now reads:**

```
here, because it is read only when someone questions a rule. Nothing was retired — see
*Rules flagged for review* at the end of the spine for the four candidates awaiting a decision.
```

One row *was* retired, by this commit, and the table now holds **three** rows
(`docs/dev-process.md:218-220`). Both halves of that sentence are false as of `4fe410ca`. This is the
"qualifying numbers in prose" class the checklists doc names, and no script owns it.

**Change:** in the same commit — `Nothing was retired` → `One row was retired 2026-09-10 (the `gh`
two-remotes footgun, whose account is below); the rest await a decision`, and `four` → `three`.

---

## Low

### L1 — A self-test case is vacuous: `all([])` is `True`

`:214-216`:

```python
    case("the problem names WHICH question, so a two-question card is actionable",
         lambda: all(p.startswith("question ") for p in card_problems(
             card(["A — One", "B — Two", "C — Three"]))))
```

Measured — I neutered `card_problems` to `return []` unconditionally and this case stayed **green**:

```
### card_problems returns [] ALWAYS (the whole rule deleted): 13/24 passed
STILL GREEN … the problem names WHICH question, so a two-question card is actionable
```

This is the exact shape in `fixing-a-premise-is-not-covering-the-branch`: an assertion that deleting
the subject also satisfies. (The other twelve that stayed green are the positive-pass controls and the
`payload_of` cases, which *should* be green when `card_problems` is gone — I checked each.)

**Change:** `probs = card_problems(...); return bool(probs) and all(p.startswith("question ") for p in probs)`.

### L2 — Three more mutation survivors; the manifest picked the weakest kill for the floor

Applied to a copy of the delivered file, self-test still 24/24:

| mutation | survives |
|---|---|
| `len(desc.strip())` → `len(desc)` | yes — a 45-space description would pass |
| `MIN_DESCRIPTION = 40` → `6` | yes — the declared floor is pinned only above 5 |
| `return [q for q in questions if isinstance(q, dict)]` → `return list(questions)` | yes |

The manifest's own entry sets `MIN_DESCRIPTION` to **0**, the weakest mutation that still dies (the
bare-label fixture is `"short"`, 5 characters). `promoting-a-mutation-leaves-its-protection-behind`
argues for the weakest mutation *that fails via the case it names*; here the consequence is that the
number 40 — which is what §19's floor actually claims — is untested. A boundary pair fixes all three
rows: a 39-character description refused, a 40-character one accepted (I confirmed the boundary is
where the code says: 39 → rc 2, 40 → rc 0).

### L3 — A case name claims more than the case asserts

`:198-200`, *"the question-exit is matched loosely, not by exact wording"*, asserts only that
`"C — I Have A Question, actually several"` passes — i.e. case-insensitivity plus trailing words. A
*differently worded* exit is refused, measured:

| last option | rc |
|---|---|
| `C — Let's talk it through first` (used twice in the real corpus) | 2 |
| `C — Ask me something first` | 2 |
| `C — Questions?` (which is what the tool's own "concise, 1-5 words" guidance invites) | 2 |

Mandating the literal is defensible — §19 says the last option is *always* "I have a question about
these" — but the case name asserts a looseness that does not exist, and a reader auditing coverage
would believe the wording is flexible. Rename it *"the question-exit ignores case and trailing words"*.

### L4 — `echo "$INPUT"` and the `d.get` outside the `try`

`enforce-selection-card.sh:32` and `:43` use `echo "$INPUT"`; `printf '%s'` is the form that cannot be
reinterpreted. And in the embedded snippet, `json.load` is inside the `try` but `d.get("tool_name")` is
not — a JSON array envelope raises `AttributeError`, which `2>/dev/null` swallows into the silent
`exit 0` of **H3**. Both are one-line changes and both point at the same repair.

### L5 — An uncaught exception prints a Python traceback inside the ⛔ box

`options` as a dict, or a list of strings, gives `AttributeError` → rc 1 → the hook blocks (correct
direction) and renders the traceback as the body of the refusal panel. Wrapping the `card_problems`
call in `main()` the way `payload_of` already is, and emitting the CANNOT-RUN sentence instead, keeps
the fail-closed behaviour and loses the traceback.

---

## What I verified and found CORRECT — worth recording so a later round does not re-litigate it

* **All 6 manifest mutations kill via the case they name**, reproduced independently against a copy of
  the delivered file over a control proved green first. Red-case counts `1/4/1/2/1/1`, matching the
  commit message exactly. No manifest mutation survived, and no anchor missed.
* **`payload_of` has no fail-open path that I could find.** I traced every branch: non-dict top level,
  `tool_input` absent / non-dict / a string, `questions` absent / non-list / empty / containing
  non-dicts, empty stdin, malformed JSON. Every one is rc 2 with the CANNOT-RUN sentence, except the
  non-dict-entries filter (L2), which drops junk silently but cannot admit a bad card.
* **The verdict half of the hook fails closed** — missing script, missing interpreter, and uncaught
  exceptions all block. Only detection fails open (H3).
* **The hook is a faithful clone of `enforce-handoff-path.sh`**, including the fast `exit 0` for other
  tools (verified: `Bash` envelope → rc 0) and silence on the happy path (verified: good card → rc 0,
  no output).
* **Every gate is green** at `4fe410ca`: `check-docs.py` 0, `check-selftest-counts.py` 0 (33 scripts,
  each count verified by running it), `check-ratchet-contract.py` 0 (32 guards, the new one
  discovered), `check-gate-falsifiability.py` 0, `check-plan-code.py --self-test` 89/89.
  `docs/dev-process.md` is 220 lines, at budget.
* **The `--self-test` does run in CI** — `ci.yml:275` runs `check-selftest-counts.py`, which executes
  each declared count, and `ci.yml:359` runs `--mutate .`. So the 24 cases and the 6 mutations are
  genuinely enforced; H2's survivors are outside both, which is the whole of the H2 complaint.

⚠ **One thing I could NOT verify, and it should not be recorded as verified.** Nothing I ran proves
that Claude Code dispatches `PreToolUse` hooks for `AskUserQuestion` at all. The commit's falsifier
(*"bad card rc=2, good card rc=0"*) measures the script and the hook invoked **by hand** — the same
"green check over the wrong subject" shape this repo has paid for. The binary documents
`| PreToolUse | Tool name | Run before tool, can block |` with no exclusion list, so it very likely
works, but *likely* is not measured. **The falsifier is one live action:** offer a deliberately
malformed card in a fresh session in this repo and observe the ⛔ panel. Until someone does, the
dev-process row added at `:136` claims enforcement that has not been observed end to end.

---

## Counts

| Severity | Count |
|---|---|
| Blocking | 1 |
| High | 2 |
| Medium | 6 |
| Low | 5 |

**VERDICT: NOT CONVERGED**
