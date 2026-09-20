<!-- claude half of code round 3 -->

# Code review round 3 — Claude half

**Subject:** `git diff c84374c8..d1682707` — commits `8b0731f0` (comment/message repairs) and
`d1682707` (the per-field-kind duplicate remedy + `LIST_FIELDS`). Branch `feature-hub-spec`,
HEAD `d1682707`. Rounds 1 and 2 covered the rest of the branch.

**Verdict: safe to merge.** The `setattr` refactor is behaviour-identical, the new remedy is true
for all five fields and works when followed literally, and every comment sentence I checked is true
against what runs. Two findings, neither a live behaviour defect: the newest fix has **no
falsifier** (Medium), and the refactor couples `LIST_FIELDS` membership to attribute spelling in a
way that fails silently for the one field whose spellings differ (Low, latent).

---

## Findings

### 1 — Medium: `d1682707`'s fix can be reverted and every gate stays green

Measured on a copy of HEAD. I replaced the new conditional

```python
remedy = ("Put every value on ONE comma-separated line. " if key in LIST_FIELDS
          else f"`{key}` holds a single value — keep the one you mean and delete the other. ")
```

with the pre-fix string `remedy = "Put every value on ONE comma-separated line. "` — i.e. I put the
exact defect Codex reported back into the code — and ran the suite:

| Command | Result |
|---|---|
| `check-features.py --self-test` | **30/30 passed, rc=0** |
| `check-features.py` (live tree) | rc=0 |

No self-test case and no entry in `scripts/mutations/check-features.json` reads the remedy text.
Grepping the 20 mutation `expect` strings confirms it: the duplicate-field mutations pin *that a
duplicate is refused* and *that the first value stands*, and nothing pins **what the author is
told**. The same is true of `8b0731f0`'s rewritten field-grammar message (`A field starts at
COLUMN 0 …`): no case asserts any of it.

Why this is worth a Medium on an otherwise clean fix: **this message is now on its fourth
iteration**, all four driven by review rather than by a gate, and the thing each iteration changed
is the one thing nothing measures. `check-ratchet-contract.py` is satisfied because the *script*
has a `--self-test`; it cannot see that this branch of it is unfalsifiable. The repair is two
cases — one asserting a duplicate `state` yields `holds a single value`, one asserting a duplicate
`areas` yields `ONE comma-separated line` — plus a mutation flipping the conditional. Not required
for correctness today; required for the fix to survive the next edit.

### 2 — Low (latent, not live): `setattr(n, key, …)` silently accepts a name `Node` does not have

For `areas` and `anchors` the refactor is exactly equivalent (finding-free; see below). The hazard
is the coupling it introduces: `LIST_FIELDS` membership is now also an assertion that the field
name *is* the attribute name. Four of the five field names satisfy that; `expected-because` does
not — its attribute is `expected_because`. Measured on a `Node` instance:

```
setattr(n, "expected-because", ["a"])  ->  succeeds; getattr(n,"expected-because") == ["a"]
                                           n.expected_because is still None
```

A dataclass without `__slots__` takes the hyphenated name happily, so adding `expected-because` to
`LIST_FIELDS` would write a dead attribute and drop the value with no error. The explicit
`elif key == "areas": n.areas = …` chain it replaced could not express that mistake.

**Related, same root:** `FIELD_NAMES` now owns the matcher and the grammar message, but **not** the
assignment chain. A sixth name added to `FIELD_NAMES` alone would match, be dedup-tracked, and then
be silently discarded — no attribute, no problem reported. The `FIELD_NAMES` comment scopes its
claim to the matcher and the message, so it is **not** a false claim; but making the grammar derived
while the assignments stayed hand-written is what creates the silent path. A one-line
`else: raise AssertionError(f"no assignment for field {key}")` after the chain would make both of
these loud.

---

## Checked and TRUE — no finding

**The `setattr` refactor is byte-identical for every input.** The `elif` chain reaches
`key in LIST_FIELDS` only when `key ∈ FIELD_NAMES` and is not `state`/`for`/`expected-because`,
i.e. exactly `{areas, anchors}` — the same set, and `setattr(n,"areas",X) ≡ n.areas = X`. Measured
across the edge cases asked about:

| `areas:` value | Parsed |
|---|---|
| empty | `[]` |
| `   ` (whitespace only) | `[]` |
| `(a),` (trailing comma) | `['(a)']` |
| `,,` | `[]` |
| ` (a) , , (b) ,` | `['(a)', '(b)']` |

**The remedy is true for all five fields, and following it literally resolves the error.** I
triggered a duplicate of each and then did what the message says:

| Field | Message given | Following it literally |
|---|---|---|
| `state` | `holds a single value — keep the one you mean and delete the other` | CLEAN |
| `for` | `holds a single value — …` | CLEAN |
| `expected-because` | `holds a single value — …` | CLEAN |
| `areas` | `Put every value on ONE comma-separated line` | `areas: (product), (cloud)` → CLEAN |
| `anchors` | `Put every value on ONE comma-separated line` | `anchors: a, b` → CLEAN |

And the **old** advice still reproduces the reported defect, which is the control this fix needed:
`state: built, absent` → `has state 'built, absent'; expected 'built' or 'absent'`. The fix does
what it claims.

**Comments — every new sentence checked against what runs.**

- `LIST_FIELDS`' "read in two places that must not disagree: the comma-split in `parse_features`
  and the duplicate-field REMEDY" — **true**, both read it (`:97`, `:108`).
- `FIELD_NAMES`' "the matcher and the error message … are both derived from this tuple" — **true**
  (`:26`, `:80`). The claim is scoped to those two and does not overstate (see finding 2).
- The three-prefix fixture comment's measured claim — "with the tokens deleted, and with a bare
  `>`, all three stay green" — **verified by running it**: I stripped `currently`/`#322` from all
  three fixtures and reduced the blockquote to a bare `>` on a copy; **30/30 passed**. The comment
  now describes its own coverage accurately.
- `gen-features-page.py` / `check-plan-code.py` narrowing of the `regen-backlog-page.sh` precedent
  — **true**: the backlog cases extract the awk program from the shell file and run `awk`
  (`gen-backlog-page.py:2818`, `_hook_awk`), while the three features cases run
  `subprocess.run(["bash", str(_HOOK)], …)` (`gen-features-page.py:621`). "Strictly stronger" holds,
  and the counts ("four" backlog, "three" features) are right.

**Mutation manifest.** Re-verified independently of the controller: all 20 entries, every `edits`
anchor resolves in the delivered source **exactly once** (0 bad). The one anchor `d1682707` had to
re-cut (the duplicate-field `continue`) resolves.

## Gates — all rc=0

| Command | rc | Last line |
|---|---|---|
| `check-features.py` | 0 | 26 nodes (24 built, 2 declared absent); 13 anchors and 21 backlog areas all claimed exactly once |
| `check-features.py --self-test` | 0 | 30/30 |
| `gen-features-page.py --self-test` | 0 | 12/12 |
| `check-selftest-counts.py` | 0 | 42 scripts declare a count, every one verified by running it |
| `check-fixture-variation.py` | 0 | 564 parameters across 54 files |
| `check-plan-code.py --self-test` | 0 | 128/128 |
| `check-ratchet-contract.py` | 0 | ratchet contract OK |
| `check-docs.py` | 0 | Documentation integrity OK |

`--mutate .` was not run (764 mutations, excluded by the brief); CI runs it.

## Out of scope

Nothing observed outside `c84374c8..d1682707` that bears on this verdict.
