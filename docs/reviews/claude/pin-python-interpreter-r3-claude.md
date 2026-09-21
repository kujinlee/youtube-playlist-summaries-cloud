# pin-python-interpreter — round 3 — Claude half

**Verdict: NOT CONVERGED. 2 High, 3 Medium.** And the explicit answer asked for:
**the thrashing call was wrong, and your own pre-committed falsifier is how we know — it has fired
twice.** There is a fourth `declared_pins` defect at the named subject (you found it yourself,
uncommitted) and a **fifth that survives your in-flight fix for the fourth**.

Subject: `scripts/check-python-pin.py` at `pin-python-interpreter` HEAD `cfefc377`;
delta `git diff 1ff82198..cfefc377`. Control at that commit: **62/62 passed**.

## ⚠ PROOF OF SUBJECT, and a hazard in it

```
$ git rev-parse --abbrev-ref HEAD && git rev-parse --short HEAD
pin-python-interpreter
cfefc377
$ git status --porcelain
 M scripts/check-plan-code.py
 M scripts/check-python-pin.py          <-- the tree is DIRTY and AHEAD of the subject
 M scripts/mutations/check-python-pin.json
$ git show cfefc377:scripts/check-python-pin.py | grep -c _structural
0
$ grep -c _structural scripts/check-python-pin.py
2
```

**The working tree contains an uncommitted `_structural()` that is not in `cfefc377`.** So this
round has three code states, and every result below names which one it was measured on:

| tag | tree |
|---|---|
| **OLD** | `1ff82198` — before the redesign |
| **SUBJECT** | `cfefc377` — the named delta |
| **WIP** | the uncommitted working tree (`_structural` present) — copied to `mktemp -d`, never run in place |

I derived the block-scalar false pin from `_steps` before reading `_structural`; you found it first
and it is in your uncommitted work. I claim no discovery there — F2 below is a **confirmation**.
What is new is **F1**, which your fix does not close.

Constraints honoured: read-only git; every probe on copies in `mktemp -d`;
`check-plan-code.py --mutate .` never run against the working tree; `docs/reviews/` top level
untouched; this file is the only repo write.

---

## F1 — High — a FIFTH `declared_pins` defect, and it survives the in-flight fix for the fourth

One character separates it from the shape `_structural` was written for: the heredoc line carries a
list dash.

```yaml
      - name: write a workflow
        run: |
          cat > w.yml <<'EOF'
          - uses: actions/setup-python@v5
            with:
              python-version: '9.9'
          EOF
```

| fixture | OLD | SUBJECT | **WIP (with `_structural`)** |
|---|---|---|---|
| heredoc content, no dash (your F-4 shape) | `[]` | `['9.9']` | `[]` — fixed |
| **heredoc content, WITH a dash** | `['9.9']` | `['9.9']` | **`['9.9']` — NOT fixed** |

Mechanism, traced by printing `_steps` on the fixture:

```
STEPS FOR the dashed heredoc:
  indent=6   body=['  name: write a workflow', '        run: |', "          cat > w.yml <<'EOF'"]
  indent=10  body=['  uses: actions/setup-python@v5', '            with:', "              python-version: '9.9'"]
```

`_steps` splits at the dash **before** `_structural` ever runs, so the `run: |` key stays in the
*previous* step's body and the pseudo-step it created contains no block-scalar key at all.
`_structural` is given a body with nothing to strip and returns it unchanged. The fix is applied to
the wrong side of the split.

Direction: **false pin**. A job with no real `setup-python` step reads as pinned — r1's High family,
the direction this guard must never fail in — or, with a real pin present, a spurious `rc=1`
"disagreement" between `9.9` and the true pin.

This is not a regression (OLD has it too). It is the class, still open, after the repair whose own
docstring names the root cause correctly: *"this guard reads YAML by scanning lines, so text that
LOOKS like structure is indistinguishable from structure."* `_structural` acts on that insight for
one of the two ways line-scanning can be fooled and not the other.

---

## F2 — High (confirmation, fix in flight) — the fourth defect is live at the named subject

```yaml
      - name: write a workflow
        run: |
          cat > w.yml <<'EOF'
          uses: actions/setup-python@v5
          with:
            python-version: '9.9'
          EOF
```

`OLD → []`, **`SUBJECT → ['9.9']`**, `WIP → []`. A **regression introduced by the redesign**:
contents-matching promoted a line the opener-matching version could not see. Answering the brief's
question 2 directly — yes, the net is now too wide, and this is the shape.

Nothing to fix that you have not already fixed; it is recorded because the *named subject* is
`cfefc377` and a reader of this round must not conclude the delta was clean. **The commit that
lands `_structural` must land before this branch merges.**

---

## F3 — Medium — `_steps` silently DROPS lines, and a real pin can vanish again

The brief asked for a workflow where a line lands in the wrong step or is dropped. Here it is —
a step containing a nested list *before* its `uses:`:

```yaml
      - name: Set up Python
        env:
          LIST:
            - a
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
```

```
STEPS:
  indent=6   body=['  name: Set up Python', '        env:', '          LIST:']
  indent=12  body=['  a']
```

`declared_pins → []`. **The `uses:` line and the pin are in no step's body at all.**

Mechanism: `- a` opens a Step at indent 12; the next line (`        uses:`, indent 8) is `<= 12`, so
the close branch pushes `Step(-1, [])`; every later line fails `if out[-1].indent >= 0` and is
**discarded** until the next dash. The sentinel does not end a step — it ends the *file*, for
everything that follows at an outer indent.

Direction is fail-closed (job reads UNPINNED), which is the safer half — but the consequence is
exactly r2's H1: the author sees a pinned step, the guard says the job is unpinned, and the message
routes them to `EXEMPT_JOBS`. Legal YAML, rarer than `- name:` (a list-valued key before `uses:`),
so Medium rather than High. The `Step(-1, [])` sentinel is the part you said you trust least, and it
is the part that is wrong.

---

## F4 — Medium — seven of ten clauses in `_steps` are unfalsifiable, and an eighth is unattributable

Every clause mutated on a copy of SUBJECT, control green at 62/62 first:

| mutation of `_steps` | result |
|---|---|
| delete `out[-1] = Step(out[-1].indent, out[-1].body + [])   # closed` | **SURVIVED** — it is a literal no-op: `body + []` copies a list nothing else holds |
| delete the sentinel guard `if out[-1].indent >= 0:` | **SURVIVED** |
| **never push the sentinel `Step(-1, [])` at all** | **SURVIVED** |
| `[" " + m.group(2)]` → `[m.group(2)]` (drop the dash blanking) | **SURVIVED** — and `Step`'s docstring calls that equivalence *"the whole point of this type"* |
| close test `<=` → `<` | **SURVIVED** |
| drop the blank-line guard (`line.strip() and`) | **SURVIVED** |
| `return [s for s in out if s.indent >= 0]` → `return out` | **SURVIVED** |
| delete `if not out: continue` | rc=1, **RED BUT NO `[FAIL]` LINE** — a traceback; a manifest entry here would score unattributable |
| contents-match → opener-match (*your manifest entry 1*) | 2 red, attributed ✅ |
| dash line dropped from body (*your manifest entry 2*) | 26 red, attributed ✅ |

So the two new mutations cover the two clauses the redesign is *about*, and **the seven clauses that
make the partitioning work are held by nothing**. Three of them (the sentinel, its guard, the final
filter) are the mechanism F3 shows is wrong — you can delete the entire sentinel apparatus and the
suite stays green, which is why F3 was never going to be caught here.

---

## F5 — Medium — the heredoc negative case passes for an ambient reason, and that is precisely why F2 got through

```python
case("a named step whose heredoc CONTAINS a pin line is still not a pin",
     declared_pins("      - name: write a file\n        run: |\n"
                   "          cat > x <<'EOF'\n          python-version: '9.9'\n"
                   "          EOF\n"), [])
```

That fixture has **no `uses:` line and no `with:` block**. It is rejected by the contents test
before any heredoc question arises. Measured:

| mutation | does this case redden? |
|---|---|
| contents regex widened `actions/setup-python` → `actions/` | **no** |
| contents test removed entirely (every step qualifies) | **no** |

Nothing that touches heredoc handling can fail it, because heredoc handling is not what makes it
pass. Its label claims a property the code did not have at `cfefc377` — F2's fixture is this one
plus a `with:` block, and it returns `['9.9']`.

r2 named this exact pair as the thing to watch (*"the heredoc pair never reaches the step-boundary
clause"*). The case was re-written for the redesign and re-acquired the same defect.

For contrast, the sibling negative case is sound: widening the regex to `actions/` reddens
**only** `"a named step around an UNRELATED action is still not a pin"`. That one is a real
falsifier. Four of the five new cases are genuine; this is the fifth.

---

## F6 — the merge arithmetic is CORRECT, with one gap worth naming

Derived independently from the subject commit rather than read off the diff:

| check | derived | declared | verdict |
|---|---|---|---|
| `sum(EXPECTED_MUTATIONS.values())` | **856** | `case(... , 856)` | ✅ |
| `EXPECTED_MUTATIONS["scripts/check-python-pin.py"]` | 27 | entries in `check-python-pin.json` at `cfefc377` = **27** | ✅ |
| `check-fixture-variation.py` on a `git archive` of `cfefc377` | rc=0, 608 parameters / 57 files | — | ✅ |
| `EXAMINED_KEYS['check-python-pin.py']` vs `analyse()` | `pinned − derived = ∅` | — | ✅ nothing pinned has vanished |

⚠ **But `_steps.text` is not in the derived population at all.** `analyse()` returns no key for
`_steps` or `Step`, because the cases reach them only through `declared_pins`. So the redesign's
core new function is invisible to the fixture-variation gate: it is green because it never looked,
not because it checked. Not a defect in the merge resolution — a statement about what that green
means.

---

## The thrashing call — you asked for a plain answer

**Your call was wrong, and the falsifier you pre-committed is what shows it.**

You wrote: *"if a FOURTH `declared_pins` finding arrives in round 3, the redesign did not dissolve
the class and Phase 6 fires."* Round 3 has produced a fourth (F2, which you found first) **and a
fifth that survives the fix for the fourth** (F1). That is not a close reading of the condition; it
is the condition, met twice.

Being fair to the engineering, which is a separate question from the process one:

* the redesign is a **strict improvement** — H1 is genuinely dead, and column-0 steps and CRLF now
  work where OLD returned `[]` (measured, both);
* `docs/review-method.md`'s test — *can a redesign remove it?* — was answered against the wrong
  class. You scoped the class as **step identification**, and a redesign does remove that. The class
  is one level up, and your own `_structural` docstring states it exactly: *"this guard reads YAML
  by scanning lines, so text that LOOKS like structure is indistinguishable from structure."* No
  amount of step identification removes that, which is why the fix for the fourth defect did not
  survive contact with the fifth.

Reaching that sentence — *the class is the reading strategy, not the pattern* — and deciding what to
do about it is what Phase 6 is for. The difference between finding a structural defect and
**acting** on one is the whole reason the arming condition is not "has anyone named it".

I am not prescribing the remedy, but the shape of the decision Phase 6 would own is: parse the YAML
(PyYAML is absent, and that constraint is now load-bearing rather than incidental), or **refuse**
rather than guess — a step whose body contains a block scalar is a file this line scanner cannot
read, and `exit 2 = CANNOT RUN` already exists for exactly that.

---

## Verdict

| check | result |
|---|---|
| `_steps` partitions correctly | ❌ **F3** — lines silently dropped after a nested list; pin invisible |
| the net is not too wide | ❌ **F2** (fourth, fix uncommitted) and ❌ **F1** (fifth, survives that fix) |
| a fourth `declared_pins` defect exists | ❌ **yes — a fourth AND a fifth** |
| the 5 new cases | ❌ 4 sound, 1 (**F5**) passes for an ambient reason — the same one that missed F2 |
| the 2 new mutations | ✅ both attribute via the case they name |
| `_steps`' own clauses | ❌ **F4** — 7 unfalsifiable, 1 unattributable |
| merge arithmetic (856, 27) | ✅ derived independently, both correct |
| `EXAMINED_KEYS` vs `analyse()` | ✅ no pinned key lost — ⚠ `_steps` is outside the examined population |
| control at `cfefc377` | ✅ 62/62 |
| subject stability | ⚠ the working tree is dirty and ahead of the named commit |

**NOT CONVERGED.** The minimum before another round is worth running: land `_structural`, close F1
on the dashed shape (the split happens before the strip, so `_structural` has to run on the text
*before* `_steps`, not on each body after it), fix the sentinel in F3, and give the heredoc case a
fixture that can actually fail. And convene Phase 6 — by your own falsifier, not by my reading.

**REVIEW GAP: none for this half.** Codex is running concurrently on the same delta as round 3's
other half; if it does not land, this round has one half only and `check-review-rounds.py` will say
so.
