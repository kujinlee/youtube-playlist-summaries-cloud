# The late-flush observation is an instrument, not a warning

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them —
> without reading the chat transcript.

**Backlog #97.** **v1, 2026-09-06.** Filed on the resume immediately after PR #229 merged, from the
live warn log rather than from a report.

**The measurement shipped correct and the response shipped wrong.** F11 — the runtime durability
check added in the #96 slice — observes something real and already answered that spec's one open
question. It then escalates the observation to a WARN, and the thing it observes is the *normal*
case, so the guard now warns on nearly every turn.

⚠ **Header order is load-bearing** — `check-anchors.py:61` sets `HEAD_LINES = 10`.

---

## 1. What is actually happening

Measured in `.claude/banner-warnings.log`: **ten consecutive warnings between 05:49:18 and
06:40:03 on 2026-09-06**, one per turn, on ordinary turns with no plan armed.

**The log's own grammar proves the escalation is the source, and this is stronger than
"these look wrong".** Nine of the ten read `unbannered` + `0 unticked`, which `decide()` cannot
produce:

* the banner-less WARN (`check-banner-armed.py:411`) fires only when `armed and unticked > 0 and edited`;
* the log derives its `unticked` field (`:813-814`) from the same `steps` object `decide()` was handed.

So `unbannered` with `0 unticked` is self-contradictory as a `decide()` verdict. The tenth reads
`unarmed` + `STEP 7 of 7`, and `:428-429` returns QUIET on `step >= total` **before `armed` is ever
read**. Both shapes therefore arrive by the only remaining route to `code == WARN`: the escalation at
`:754-755`. Journal state at the time agrees — `armed: False`, `steps: None`,
`sampled_turn_len: 5` against `prev_turn_len: 56`.

### 1.1 Two defects, and the second was not noticed when the first was

**D1 — cry wolf.** A late flush is backlog #96's own mechanism: the normal case, not an anomaly.
Warning on it is the exact failure #95 and #96 existed to remove.

**D2 — the log misfiles the class.** `log_line`'s docstring (`:460-462`) states that `reason`
discriminates the two warning classes; the WARN block (`:808-814`) derives it purely from *was there
a banner* and has no way to know the WARN came from the escalation. Every escalation is therefore
filed as a banner-less warning **that never fired**. That log is the stated evidence base for the
promote-to-blocking decision (`:451-454`) and was re-baselined on 2026-09-05 precisely so it could be
counted; it is now 10 of 15 entries mislabelled. **This is the second contamination of the same
evidence base** — #96 was the first — which is why the fix is not simply "stop warning".

### 1.2 What the instrument already bought, so nobody deletes it

Spec §7 F11 said durability at one turn's remove was *"an argument, not a proof"* and could not be
settled by any corpus, because a recorded transcript shows final file state and can never show what
was **readable** when a hook ran.

**It is now settled by observation, and negatively: records do arrive after a turn's own Stop has
read the file** (`sampled_turn_len: 17` for a turn earlier sampled at 7). The measurement is
load-bearing. Only the response to it is wrong.

---

## 2. The three changes

### 2.1 (a) The observation never changes the verdict

Delete the `if code == QUIET: code = WARN` promotion at `:754-755`.

The late-flush note stays in the printed message **only when a warning is already being emitted** —
appending a paragraph to an otherwise-silent turn is the same cry-wolf noise moved to another
channel. On a QUIET turn the guard prints nothing and records the observation to §2.2.

### 2.2 (b) The observation gets its own file

New: `.claude/banner-flush-observations.log`, same tab-separated grammar as the warn log —
`when \t session \t before \t after`.

**Why not a third `reason` value in `.claude/banner-warnings.log`.** That file is named for warnings,
and the guard's own message (`:451-454`) tells its reader to consult it as evidence *about warnings*.
A non-warning line in it is a category error whatever its frequency, and it is the identical shape to
D2 — a line filed under a class that did not fire. Keeping the file pure means `wc -l` remains a
valid warning count permanently.

**Nothing parses either file.** Re-verified 2026-09-06 by grep over the repo: outside this script and
the review documents, the only mention is one prose line at `docs/dashboard-entries.md:3287`
(*"Log: `.claude/banner-warnings.log` (gitignored)"*), carrying no column shape. Two prior review
rounds reached the same conclusion independently. A `.gitignore` entry is added; the existing
`.claude/banner-warnings*.log` glob deliberately does **not** match the new name.

### 2.3 (c) The predicate measures the verdict's own input

Today `sampled_turn_len` is `len(live.body)` — **every** record, so a tool result landing after the
Stop reads as a late flush even when the closing banner was plainly visible. It was, in the
`7 of 7` case. Growth is not evidence the banner was missed.

Replace it with `len(texts_of(live.body))`, and compare against `len(texts_of(judged.body))`.

**This is not a proxy for the durability question — it is the literal list `decide()` consumes**
(`:742`, `texts = texts_of(judged.body)`). Growth in it means the input the verdict is computed from
was incomplete at the turn's own stop; growth outside it cannot change any verdict this guard reaches.

**Key rename, and the one turn of blindness it costs, stated rather than hidden.**
`sampled_turn_len` → `sampled_text_len`, `prev_turn_len` → `prev_text_len`. A journal written by the
shipped code holds the old keys; the new code will not find them and `_late_flush` returns `None`, so
the first stop after this lands records no observation. That is fail-safe in the right direction —
a missing key yields silence, never a fabricated observation — and it is why the keys are renamed
rather than reused with a changed meaning, which would compare an all-records count against a text
count and silently under-report forever.

---

## 3. ⛔ F11 must be re-anchored, or it goes vacuous for the THIRD time

This is the part most likely to be got wrong, because the change that fixes D1 is the change that
breaks the falsifier.

F11's self-test discriminates purely on the exit code:

```
case("F11 a judged turn that GREW after its own stop is reported as a late flush",
     _flush_scenario(grow=True)  == WARN)
case("...and a turn that did NOT grow stays QUIET — the check is not vacuous",
     _flush_scenario(grow=False) == QUIET)
```

Once growth no longer changes the verdict, **both sides are QUIET and the pair asserts nothing.**
And `scripts/mutations/check-banner-armed.json` carries *"the late-flush comparison is inverted, so
growth after a turn's own stop is unseen"*, whose `expect` names that exact case as its killer — so
the mutation would survive at a green suite.

F11 was a tautology in spec v2 and v3 (1828 windows, 0 violations, true by construction). Note how
the failure recurs: each time, the assertion re-anchors onto something that cannot vary. **The
required response is that the observation record — not the exit code — becomes what F11 reads:**

* `grow=True` → exit **QUIET**, and `.claude/banner-flush-observations.log` gains exactly one line
  naming the before and after counts;
* `grow=False` → exit **QUIET**, and the observation log gains **nothing**.

The `grow=True` scenario must also be updated so its growth is in **assistant text**, which it
already is — the withheld record is a text block — but the scenario currently also proves nothing
about tool-only growth. A third case covers that (§4, F11c).

---

## 4. Falsifiers

| # | Fails if |
|---|---|
| **F11a** | a judged turn whose **assistant text** grew after its own stop exits QUIET **and** appends exactly one line to the observation log — fails if it warns, or if the log gains nothing |
| **F11b** | a judged turn that did not grow appends **nothing** to the observation log — fails if the check is vacuous and fires unconditionally |
| **F11c** | a judged turn that grew only by a **tool result** appends nothing and exits QUIET — this is the live false positive; fails if all-record growth still counts |
| **F97a** | an ordinary unarmed turn with no banner adds **no** line to `.claude/banner-warnings.log` under any amount of growth — fails if the escalation survives anywhere |
| **F97b** | when a real warning fires **and** a late flush is observed, the warning is still logged with its own true `reason` (`unarmed`/`unbannered`) and the flush note appears in the message — fails if the observation displaces or renames the warning |
| **F97c** | the shipped mutation *"the late-flush comparison is inverted"* is killed by the case it names — fails if it survives after the re-anchoring |

F97a is the defect this slice exists to remove. F11c is the predicate fix. F11a/F11b are F11 kept
alive across the change that would otherwise have hollowed it out.

---

## 4.1 Code review r1 fold — the falsifier was half-anchored, not fully

`docs/reviews/coordinator/late-flush-escalation-code-r1-codex.md`, NOT CONVERGED, one Medium,
folded here rather than argued with.

**The finding:** §3's re-anchoring moved F11 off the exit code and onto *whether a line was
appended* — and stopped there. It never read the line. Measured by the reviewer on a mutated copy:
`flush_line` rewritten to return a constant string passed **94/94**.

That is this slice's own thesis applied one layer in. The counts **are** the evidence; a line that
has lost them records that something happened while destroying what was measured — the recorded
rule *a guard's own output is a CONTRACT with whatever parses it*, which is exactly what D2 was.
Half-anchoring is how F11 became vacuous the first two times, and it nearly happened again inside
the fix for it.

**Response:** case `Cx-M1` asserts the recorded line's trailing fields are `["fl-text", "1", "2"]` —
the judged turn held one text block at its own stop and two one stop later. A manifest entry
(`EXPECTED_MUTATIONS` 7 → 8) blanks the counts and must die through that case. Verified: control
95/95, mutant 94/95 with **only** `Cx-M1` red, so the kill is attributable and no sibling case
takes credit for it.

---

## 5. Out of scope — named, not hidden

* **`highest_banner` conflates sequences with different totals.** Named in #96 spec §8, still open,
  still a separate falsifier and a separate slice.
* **The promote-to-blocking decision.** This slice restores the warn log's ability to be counted; it
  does not spend that evidence.
* **Retro-classifying the ten contaminated lines.** They cannot be separated from real warnings after
  the fact — the same reason the log was re-baselined on 2026-09-05. The log is re-baselined again as
  part of this slice, and the reason is recorded rather than the lines silently deleted.
