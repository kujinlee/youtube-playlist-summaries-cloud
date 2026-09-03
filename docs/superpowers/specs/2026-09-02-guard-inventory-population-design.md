# The guard inventory declares its population — Design Spec

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

**Backlog:** #72 (and #73, which closes with it).
**Status: v2 — round 1 folded in, BOTH halves.** Design shape (declare-out) approved by the user
2026-09-02 and unchanged; every change below is an accuracy or mechanism repair.

| Round | Codex (`gpt-5.5`) | Claude |
|---|---|---|
| 1 | 1 Blocking, 2 High, 2 Medium — **NOT CONVERGED** | 1 Blocking, 5 High, 5 Medium, 4 Low — **NOT CONVERGED** |

Reviews: [`spec-guard-inventory-population-r1-codex.md`](../../reviews/spec-guard-inventory-population-r1-codex.md),
[`spec-guard-inventory-population-r1-claude.md`](../../reviews/spec-guard-inventory-population-r1-claude.md).

> ⚠ **The halves disagreed once, and the disagreement was the signal.** Codex found
> `build-m4-schema.py` misclassified; the Claude half independently listed it among conforming OUT
> files and never questioned it. Codex was right (§4.1). This repo's record is that when the halves
> split, the finding-half has been right every time.

> ⚠ **v2's §3 is a MECHANISM change, not a wording change.** v1's grammar let the guard delete itself
> from its own population *by documenting its own rule* — demonstrated by execution, not argued. §5
> item 2 instructed the implementer to write exactly that sentence. See §3.1.

**Anchor fit, stated rather than assumed.** `status-visibility` is the anchor **most** tooling specs
here use, including `2026-08-29-mutation-manifest-retarget-design.md`. ⚠ Not all: the pure-tooling
`2026-08-19-prod-readonly-smoke-design.md:3` allocated its own `prod-smoke`, so "every tooling spec"
(v1) was false. The fit here is analogical — a guard inventory exists to make guard coverage visible,
and the defect below is a case of it reporting coverage it did not have. No new anchor is allocated;
a name in `docs/anchors.md` is permanent and allocating one is the user's call.

---

## §1 — The defect, as measured against `77c5676d`

`scripts/check-ratchet-contract.py` polices every guard in the repo: each must have a `--self-test`
(R1), must not return `0` from an `except` handler (R2), and must have a caller or a written
`NO-CALLER:` reason (R3). Its value depends entirely on **which files it looks at**.

It looks at 26 of 45. And it says otherwise, in two places:

| Where | The claim | What the code does |
|---|---|---|
| `discover_ratchets:67` (dead) | discovery from *"TWO independent sources"* — CI step names, and a docstring self-declaring via `RATCHET_DOCSTRING_RE` | Source 2 is **unreachable**. No caller ever offers it a non-`check-*` file |
| **`discover_guards:132` (live)** | **"EVERY guard on disk. The population is the FILESYSTEM."** | It is only ever handed a name-filtered list |

The second row is the sharper one and is **not** in backlog #72 as filed. The row is about a function
nothing calls; the same false claim is in the function that runs.

⚠ **There is exactly ONE narrowing site, and naming it precisely matters** (v1 blurred this):
`main:395` — `for p in sorted((ROOT / "scripts").glob("check-*.py")):` — builds `texts`.
`evaluate:174` does **not** glob; it forwards whatever `main` handed it. `GUARD_PATH_RE`
(`scripts/check-[\w.-]+\.py`, `:108`) then filters an already-filtered list — a second sieve with the
same mesh, which is why the narrowing is invisible when reading `discover_guards` alone.

**Measured 2026-09-02, reproduced independently by both review halves:** `scripts/*.py` = 45;
`check-*.py` = 26; live run reports `guards discovered (26)`, exit 0; `--self-test` 21/21.

### 1.1 — Why the row's first proposed shape does not work

Backlog #72 offers *"widen the population to `scripts/*.py` and let `RATCHET_DOCSTRING_RE` do the
selecting it already claims to do."* **Measured: that enrolls 6 files, of which 1 is a genuine
self-declaration.** Both halves reproduced all six.

| File | The line that matches `\bratchet\b` | Verdict |
|---|---|---|
| `gen-m4-manifest.py` | *"regenerate and FAIL if it differs (ratchet)"* | genuine declaration |
| `explainer-serve.py` | *"NOT a ratchet, and deliberately not claiming to be."* | **denial** |
| `page_markup.py` | *"THIS FILE IS **NOT** IN THE RATCHET INVENTORY, AND CANNOT BE."* | **denial** |
| `prior-art.py` | *"NOT a ratchet — a research tool."* | **denial** |
| `gen-backlog-page.py` | *"…this page and the marker ratchet…"* | citation |
| `subject_status.py` | *"Tell a ratchet's reader what its SUBJECT is…"* | citation |

A bare-word regex cannot distinguish a declaration from a denial. `page_markup.py`'s docstring
*predicted this outcome* on 2026-08-30 and the sentence that predicted it is the sentence that would
enroll the file. Same emphasis- and context-blindness class as `**Decide:**` (backlog #81),
`NO-ENTRY:` and `REVIEW GAP:`.

### 1.2 — Why the fact was known and did not travel

`scripts/explainer-serve.py:68-73` already records the exact mechanism — *"that script discovers by
globbing `scripts/check-*.py`, so this file is never even read"*. **A true statement in a neighbour's
comment did not correct the false one at the source.** That is the same shape as the defect itself,
and it is why §7 exists: the fix is not complete until every site stating the old population is
corrected.

---

## §2 — The decision: declare-out

**The population is every `scripts/*.py`. A file leaves the inventory only by saying so in writing.**

Two alternatives were costed and rejected:

**Honesty-only (rejected).** Correct both docstrings to say the population is `scripts/check-*.py`,
delete the dead function, change no behaviour. XS, and honest — but it closes the row by retiring the
ambition rather than meeting it, and leaves the next unconventionally-named guard invisible.

**Declare-in with an unambiguous marker (rejected).** Widen the population, select on an explicit
token such as `GUARD: yes`. It fixes §1.1's false positives cheaply, but **a central roster is
evadable by omission**: a guard nobody adds is a guard nobody polices, and the inventory's whole job
is noticing what nobody is looking at.

> ⛔ **v1 attached a false cause to that argument and it is deleted.** v1 said non-registration is
> *"precisely how `gen-m4-manifest.py` came to be missed"*. **That is refuted by §1.1's own table**,
> where `gen-m4-manifest.py` is the one row marked *genuine declaration* — it **did** register. It was
> missed **by the population**, which is the whole of §1. Struck rather than quietly removed, because
> writing a persuasive causal sentence that the same document refutes two pages earlier is exactly the
> failure mode this spec is about.
>
> ⚠ Second correction to the same paragraph: `discover_ratchets`'s docstring objects to *"a registry
> **list**"* (`:70`) and offers per-file self-declaration as the **defence against** it (`:71-72`).
> v1 cited that docstring against a per-file marker, inverting what it says. The general evadability
> argument stands on its own; the borrowed authority does not.

**Declare-out (chosen)** is the only shape where **omission fails**. A new script that declares
nothing is in the inventory and stays red until someone decides which it is. It is also not a new
idea in this file: `NO-CALLER: <reason>` is the same move one level down.

---

## §3 — The declaration grammar

One line in the **module docstring**, written **flush left**:

```
NOT-A-GUARD: <reason>
```

```python
NOT_A_GUARD_RE = re.compile(r"(?m)^NOT-A-GUARD:[ \t]*(\S[^\n]*)")
```

### 3.1 — Why flush-left, and why v1's grammar was a Blocking defect

v1 used `NOT-A-GUARD:[ \t]*(\S[^\n]*)`, unanchored, searched over the whole docstring. That matches
**any occurrence anywhere**, including prose describing the rule and indented examples demonstrating
it.

⛔ **The consequence was demonstrated by execution in round 1, not argued.** v1 §5 item 2 *instructs*
the implementer to rewrite `check-ratchet-contract.py`'s docstrings to describe the new mechanism.
Doing so:

```
=== SELF-EXCLUSION: the guard documents its own rule in its module docstring ===
EXIT=0
guards discovered (27): scripts/check-anchors.py, …
occurrences of "check-ratchet-contract" in the discovered list: 0
```

**The guard that polices every guard removed itself from its own population, and reported success.**
A mechanism whose stated advantage is inevitability must not have an evasion its own change list walks
into.

**The anchor was MEASURED, not assumed** — this repo's `^marker` cannot see `**marker**` lesson says
an anchoring claim is a measurement, and `ast.get_docstring` *dedents*, which changes what "line
start" means. Three candidates over five realistic docstrings:

| Case | v1 unanchored | `^[ \t]*` | **`^` flush-left** | Wanted |
|---|---|---|---|---|
| genuine declaration, flush left | EXCLUDE | EXCLUDE | **EXCLUDE** | EXCLUDE |
| prose describing the rule | EXCLUDE ❌ | in | **in** | in |
| indented example of the rule | EXCLUDE ❌ | EXCLUDE ❌ | **in** | in |
| bare colon, reason on next line | in | in | **in** | in |
| mid-sentence mention | EXCLUDE ❌ | in | **in** | in |

Only flush-left gets all five. `^[ \t]*` — the obvious anchor — still swallows the indented example,
because dedenting preserves *relative* indent: a real declaration ends up flush left, a demonstrated
one does not.

⚠ **`[ \t]`, never `\s`**, retained verbatim from `NO_CALLER_RE` (`:117`) and for the reason recorded
above it: `\s` crosses the newline and adopts the *next* docstring line as the reason, turning the
opt-out into a rubber stamp. Row 4 above is that near-miss holding.

⚠ **Lowercase `not-a-guard:` does not match.** It fails closed (the file stays IN), so it is safe, but
it is stated here rather than discovered.

### 3.2 — The same fix applies to `NO-CALLER:`, and it is free

Answering *"what else is this true of?"* with a grep rather than a recollection: `NO_CALLER_RE` is
unanchored and has the identical hazard. **Measured: zero of the 26 current guards carry a
`NO-CALLER:` declaration**, so anchoring it breaks nothing that exists. It ships in this change.
Leaving one anchored and one not would be two grammars for one concern — the shape
`scripts/check-vocabulary-collisions.py` exists to catch.

### 3.3 — The guard must be in its own population, permanently

A one-shot count taken at implementation time cannot detect a later self-exclusion. **A standing
self-test case asserts that `scripts/check-ratchet-contract.py` appears in its own discovered
population.** Precedent, verbatim: `scripts/check-selftest-counts.py:20` — *"⚠ IT CHECKS ITSELF. This
script is in `POPULATION`, so its own declared count is verified by the same external run."*

### 3.4 — Files that do not parse

`check_caller` already has a policy (`:148-151`): on `SyntaxError`, `doc = text` — the **whole file**
becomes the searched text, so a token in a comment counts. Inherited unchanged, `NOT-A-GUARD:` in a
comment of a broken file would remove it from the population entirely.

**Decision: `NOT_A_GUARD_RE` reads the module docstring only, and a file that does not parse is IN.**
An unparseable file is exactly the sort of thing an inventory should not lose. Today's population is
26 files all known to parse; widening to 45 triples the surface, so this is stated rather than left to
the `SyntaxError` fallback.

⚠ A file that does not parse currently ends the run with a **raw Python traceback** from
`fail_open_handlers:92`, where `docs/process-checklists.md` rule 1 requires *"exit non-zero and say
treat this as NOT RUN."* It is fail-closed, so not a false green — but it is repaired here and given a
case.

### 3.5 — What a declaration does

It removes the file from the inventory **entirely** — not listed, and R1/R2/R3 are not applied. It is
a statement about the *population*, not an opt-out from one rule.

---

## §4 — The criterion, and the 19 verdicts derived from it

> ⛔ **v1 had no criterion.** It sorted the 19 into "generators / library modules / tools / builders"
> and asserted 2 IN / 17 OUT. Round 1 found `build-m4-schema.py` on the wrong side, and the real
> defect was that **nothing in the document could decide the next case either**. A count derived from
> an unstated rule is not a measurement.

**A script is a guard if it has a mode whose only product is a VERDICT about a subject other than
itself.**

The tempting criterion — *"exits non-zero on a defect"* — is useless here: nearly every script in this
repo is fail-closed, because that is the house style. It would sweep in almost all 45. What
discriminates is the **product**: a guard's is a verdict; a generator's is an artefact; a library's is
functions for other code; a tool's is information for a human. Assertions that protect a script's own
output are **self-protection, not policing**.

### IN the inventory (3) — all three already satisfy R1+R2+R3, measured

| File | Derivation |
|---|---|
| `verify-exclusion-reasons.py` | *"EXECUTE the written reasons in `check-catalog-coverage.py`, instead of re-reading them"* — subject is another file's claims |
| `gen-m4-manifest.py` | `--check` is a verdict-only mode: *"regenerate and FAIL if it differs (ratchet)"*. Subject is the committed manifest |
| **`build-m4-schema.py`** | ⟳ **Moved IN by round 1 (Codex).** `assert_end_state`'s own docstring says *"The verdict"* (`:186`); `main` reports *"the spec is in neither the pre- nor the post-ADR-0011 state"* (`:381-385`) — a verdict about **the spec files**, not its own output. Its docstring adds that it *"can be reduced to its assertions"* (`:28-30`) — it is becoming a pure guard |

**Swept for others misclassified the same way:** `gen-m4-manifest.py` is the **only** non-`check-*`
script with a verdict-only mode flag (`--check`/`--verify`/`--assert`/`--audit`). No fourth surprise.

**Count after the change: 26 + 3 = 29.** ⚠ v1 said 28; that number was produced by the unstated
criterion and is corrected here rather than defended.

### OUT (16) — each gets one flush-left `NOT-A-GUARD:` line

| Category | Files |
|---|---|
| Page generators (product: an artefact) | `gen-backlog-page.py`, `gen-dashboard.py`, `gen-goals-page.py`, `brief-compose.py`, `regen-skills-doc.py` |
| Library modules (product: functions) | `page_markup.py`, `page_chrome.py`, `subject_status.py`, `m4_catalog.py`, `m4_base_db.py` |
| Tools (product: information for a human) | `explainer-serve.py`, `prior-art.py`, `codex-review.py`, `codex-frontier-model.py` |
| Reporters | `session-skill-report.py`, `skill-usage-audit.py` |

**Net: 16 declarations, 3 files join, zero code repairs, `BASELINE` stays at its hard floor of 0.**

The zero is not luck: of the 10 non-`check-*` scripts failing R1/R2/R3 today, **all 10 are in the OUT
set** — independently reproduced by both review halves — so each resolves to a declaration, not work.

### 4.1 — `codex-review.py` stays OUT, and it was the closest call

It exits `1` for *"gate did NOT run"* and `2` for *"REFUSED"*, which is gate-shaped, and
`docs/plugins.md` treats its failure modes as safety-critical. Under the criterion it is OUT: its
product is a **review file**, and its exit codes report on **its own run**, not a verdict about the
repo. Confirmed with the user 2026-09-02.

### 4.2 — Library modules are OUT rather than a rule change

`page_markup.py`, `page_chrome.py`, `subject_status.py`, `m4_catalog.py` and `m4_base_db.py` are
imported by other scripts and never invoked as programs. R3's `invocation_re` (`:121-129`) matches an
*invocation*, not a mention or an import — so an imported module reads as caller-less. **That is R3
behaving correctly.** The answer is not to teach R3 about imports; it is that a library is not a guard.
Backlog #72 warns against the mirror error — *"a renderer belongs in a guard inventory only if we
decide guards and subjects are the same population"* — and this spec decides: **they are not.**

⚠ **Measured importers, self excluded:** `page_markup` 4, `m4_catalog` 5, `subject_status` **3**,
`m4_base_db` **3**. v1 said "4–5 each"; wrong for half the set.

### 4.3 — How many OUT files already satisfy R3: EIGHT, not three

⛔ **v1 said three, and the error is instructive.** It named `page_markup.py`, `page_chrome.py` and
`gen-dashboard.py` *"because CI invokes their `--self-test`"* — enumerating from **one reason** rather
than from **the rule**. Running `check_caller` over all OUT files with the live caller blob:

```
OUT files that SATISFY R3 today: 8
   gen-backlog-page.py  gen-dashboard.py  gen-goals-page.py  regen-skills-doc.py
   page_markup.py  page_chrome.py  explainer-serve.py  build-m4-schema.py
```

(`build-m4-schema.py` has since moved IN, leaving seven in the OUT set.) Every file whose caller is a
shell gate or another script was missed. That is *"a measurement is only as good as its corpus"*, in
the one ⚠ note whose job was honesty about the OUT set. **They are still declared out:** satisfying a
rule is not membership of the population, and the difference between those two is this spec's subject.

---

## §5 — The complete change surface

> ⛔ **v1's §5 was wrong in three ways** — it declared `evaluate` untouched while requiring a change
> that forces it, omitted the single line where the narrowing physically happens, and listed a change
> surface that §9 then contradicted. All three are round-1 findings.

### In `scripts/check-ratchet-contract.py`

1. **`main:395` — the narrowing site.** `glob("check-*.py")` → `glob("*.py")`. **This is the
   load-bearing edit.** Widening `GUARD_PATH_RE` without it is a no-op, because `texts` would still
   only ever contain `check-*.py`.
2. **`GUARD_PATH_RE`** widens from `scripts/check-[\w.-]+\.py` to `scripts/[\w.-]+\.py`.
3. **`discover_guards`** takes the `texts` mapping, not a path list, and excludes any file whose
   module docstring matches `NOT_A_GUARD_RE`.
4. **`evaluate:174`** passes `texts`, not `list(texts)`. ⚠ **`evaluate` IS touched** — v1 said
   otherwise. `main:403` changes the same way.
5. **`NOT_A_GUARD_RE` added; `NO_CALLER_RE` anchored** (§3.2).
6. **Both false docstrings corrected in place**, keeping what made them false, per this repo's
   practice of correcting rather than deleting.
7. **`discover_ratchets` and `RATCHET_DOCSTRING_RE` deleted**, with their `DISCOVERY_CASES` (§8).
8. **`POPULATION_CASES` (`:296-304`) rewritten.** ⚠ All three existing cases pass `list[str]` and
   break on the signature change, and the third —
   `("a non-guard script is not in the population", ["scripts/gen-dashboard.py", "scripts/check-a.py"], ["scripts/check-a.py"])`
   — asserts the **opposite** of the new payload case. An implementer who does not know this hits a
   red suite at the moment when the tempting repair is to weaken the new case.
9. **The `SyntaxError` policy** (§3.4) stated in code, and the traceback replaced with a
   CANNOT-RUN exit.
10. **The stale sanity comment** at `:404` — `"This project has 24"` (already wrong; it is 26) —
    reworded as a **magnitude**, not a count. ⚠ Pinning it to a number that now moves with every
    declaration would re-create the same staleness on a faster clock.

### Outside that file

11. **16 flush-left `NOT-A-GUARD:` docstring lines** (§4).
12. **Every site that states the old population as fact** — §7. This is not optional tidying; leaving
    it is §1.2 reproduced by the fix.
13. **Mutation manifest and `EXPECTED_MUTATIONS`** — §9.

---

## §6 — What this does NOT do

**Held to a higher bar than most, because this spec's subject is overclaiming.** v1's version was
honest about scope and silent about every failure mode round 1 then found; that silence read as a
completeness claim it had not earned.

- **It does not make lying impossible.** Nothing stops `NOT-A-GUARD:` being written on a real guard.
  It is a written, reviewable claim — the same trade already accepted for `NO-CALLER:`. What changes
  is that **silence is no longer an option**.
- **It reduces, but does not eliminate, accidental declaration.** §3.1 measured five cases; a
  flush-left `NOT-A-GUARD:` inside a docstring for some other purpose would still exclude. The
  standing self-check (§3.3) covers only the contract itself.
- **It does not verify that an IN file is a GOOD guard**, only R1/R2/R3.
- **It does not reach outside `scripts/`.** Guards under `.claude/hooks/` are still discovered only as
  *callers*, never as subjects. Moving a guard out of `scripts/` remains an evasion, and no gate sees
  it.
- **It does not police `scripts/*.sh`.** The population is `*.py`.
- **After the count is checked once, only the self-check (§3.3) re-verifies membership** — and only
  for `check-ratchet-contract.py`. There is no standing assertion of the total; §9 explains why a
  count assertion was rejected.
- **`gen-m4-manifest.py`'s own `--self-test` is never executed by anything** (`:260`: *"the
  fourteen-gate suite runs `--check` and never `--self-test`"*) and it is not in
  `check-selftest-counts.POPULATION`. So one newly-enrolled guard satisfies R1 on the existence of an
  entry point nothing runs. R1 is unchanged by this spec; the gap is recorded, not fixed.

---

## §7 — Blast radius: every site that states the old population as fact

Round 1 (Claude) found nine. v1 corrected two. **§1.2 is the section that says a true statement in a
neighbour did not correct the false one at the source** — shipping with these live reproduces that
shape in the documents that define the convention.

| Site | Today | After |
|---|---|---|
| `docs/process-checklists.md:294-296` | *"discovers ratchets from two independent sources … so neither a forgotten registry entry nor an unwired script can evade it"* | wholly false; describes the deleted function |
| `docs/process-checklists.md:283-288` | *"There are EIGHT"* + *"prints it, from two independent sources"* | already stale; becomes 29, one source |
| `docs/process-checklists.md:298` | *"Currently 4 violations, all rule 4"* | already false — `BASELINE = 0`, live run 0 |
| `docs/dev-process.md:145` | *"the population is the FILESYSTEM … `--self-test`: 21 cases"* | the false claim §1 hunts, **in the process spine**; the count also moves |
| `scripts/page_markup.py:42-45` | names `discover_ratchets:67` and the `check-*` glob | false, and names a deleted function |
| `scripts/explainer-serve.py:68-73` | *"this file is never even read"* | false — it **is** read, for its declaration |
| `.github/workflows/ci.yml:212-215`, `:220-223` | *"its population is `glob("check-*.py")"* (×2) | false for both steps |
| `docs/roadmap-to-launch.md:1692-1693`, `:1530`, `:1599` | same claim; *"25 guards"* | false / already stale |
| `docs/superpowers/specs/2026-08-30-inline-renderer-seam-design.md:176,183` | same claim, in a **living** spec | false |

⚠ **F6's grep cannot see most of these** — it searches `scripts/ .github/ .claude/`, and the canonical
description lives under `docs/`. Widened in §8.

---

## §8 — Backlog #73 is settled as DELETE, and closes here

Backlog #73 (*"`discover_ratchets` is dead production code, kept alive only by its own self-test"*)
was filed deliberately blocked on this decision: *"if #72 is resolved by widening the population,
`discover_ratchets` may be the right implementation to restore rather than delete."*

**It is not the right implementation.** The chosen mechanism is declare-*out*; `discover_ratchets`
implements declare-*in* via a bare-word match, which §1.1 measured as unable to tell a declaration
from a denial. Restoring it would ship the defect. It is deleted with its `DISCOVERY_CASES`.

Both rows close in this PR. Per the convention from PR #213, each closed row must **lead**
`✅ (was 🟠)`, and its `GROUPS` tuple in `scripts/gen-backlog-page.py` must be deleted — the coverage
check is bidirectional and refuses prose describing a closed item.

---

## §9 — Falsifiers

Each states the observation that would make it FAIL.

| # | Falsifier | Fails if |
|---|---|---|
| F1 | `gen-m4-manifest.py`, `verify-exclusion-reasons.py` **and** `build-m4-schema.py` appear in the `guards discovered (…)` line | any is absent |
| F2 | Count is exactly **29** | any other number — the criterion was applied wrongly, or a file was missed |
| F3 | `scripts/zz-probe.py` with no `--self-test` and no declaration → **`zz-probe.py` appears in the discovered list** AND the run exits 1 | it is absent, or exits 0 |
| F4 | Add a flush-left `NOT-A-GUARD: a probe` → contract exits 0 and `zz-probe.py` is absent from the list | it stays IN |
| F5 | `NOT-A-GUARD:` with the reason on the *next* line → file still IN | excluded — the `\s` rubber-stamp regression |
| **F6** | A docstring that **documents** the rule, and one that shows it as an **indented example**, both leave the file IN | either is excluded — v1's Blocking, returned |
| **F7** | `scripts/check-ratchet-contract.py` appears in its own discovered population | absent — the guard excluded itself |
| F8 | `grep -rn discover_ratchets scripts/ .github/ .claude/ docs/` returns nothing | any hit — #73 not closed, or §7 incomplete |
| F9 | `BASELINE` is still `0` and the run is green | a raised baseline would launder the 10 failures |

> ⛔ **F3 and F9 were repaired, not merely renumbered.** v1's F3 asserted **exit code 1 only** — which
> `check-ratchet-contract.py:388-392` also returns when `.github/workflows/ci.yml` is simply absent
> from the temp copy, and `:417-419` when there are fewer than three caller sources. The falsifier
> carrying *"omission still escapes, which is the whole point"* passed for the wrong reason.
> v1's F7 (now F9) *"`BASELINE` is 0 and the run is green"* holds on the **unchanged** repo, so it is
> vacuous as evidence of the change; it is kept, relabelled as the anti-laundering check, and paired
> with F2.

**Why no standing count assertion.** F2 is a one-shot check at implementation time. A permanent
`assert len(guards) == 29` would go stale on the next legitimate script and train people to bump it —
the failure mode `docs/dev-process.md` records for hand-maintained counts. F7 is the standing
membership check instead, and §6 states plainly that the total is not re-verified.

F3–F7 run against a temp copy of the repo, never the live tree: an instrument that edits the repo
corrupts its peers. ⚠ **The temp copy must include `.github/workflows/ci.yml` and the full caller
sources**, or F3 passes for the wrong reason.

---

## §10 — Test and mutation coverage

- **Self-test cases** for `discover_guards`: a `check-*` file (IN); a non-`check-*` file with no
  declaration (IN — the payload); a flush-left declaration (OUT); the bare-colon near-miss (IN); a
  docstring documenting the rule (IN); an indented example (IN); an unparseable file (IN, §3.4); the
  standing self-inclusion case (§3.3).
- **`POPULATION_CASES` rewritten** — §5 item 8. Its third case currently asserts the opposite of the
  payload case.
- ⛔ **v1's claim that `check-selftest-counts.py` ratchets this script's total is FALSE and is
  deleted.** Its `POPULATION` (`:83-92`) pins exactly nine scripts and `check-ratchet-contract.py` is
  not among them; the contract declares `--self-test` without the canonical `# N cases` form
  (`:23-26`). **Nothing ratchets it today.** Worse, acting on v1 as written turns CI red: adding the
  declaration without a `POPULATION` edit trips `check-selftest-counts.py:176-179` (*"declares a case
  count but is not in POPULATION, so nothing checks it"*). **Decision: add the `# N cases`
  declaration AND add the file to `POPULATION`, in the same commit.** That is a real gain — the
  contract has never had its self-test count ratcheted.
- **Mutation manifest.** ⛔ v1 warned that *"existing mutation anchors may target `discover_guards`"*.
  **There are none.** No `scripts/mutations/*.json` mentions this file, and `EXPECTED_MUTATIONS`
  (`scripts/check-plan-code.py:432-497`) has **no key for it**. The true state: the repo's most
  structurally important guard ships today with **zero** mutation coverage. This change gives it its
  first, via a new `scripts/mutations/check-ratchet-contract.json` and a new `EXPECTED_MUTATIONS` key:
  - `GUARD_PATH_RE` / `main`'s glob narrowed back to `check-*` → red via the **payload discovery
    case**, not a count assertion.
  - `NOT_A_GUARD_RE`'s `[ \t]` widened to `\s` → red via the bare-colon near-miss case.
  - `NOT_A_GUARD_RE`'s `(?m)^` anchor dropped → red via the rule-documenting case (F6).
  - ⚠ Each `expect` entry must name **exactly one** red case (`check-plan-code.py:739-746`); `expect`
    is a list, and each entry is matched individually.
- ⚠ **The 16 docstring insertions touch `page_markup.py`, `page_chrome.py` and `gen-dashboard.py`,
  which DO have mutation manifests.** Anchors bind by text. Round 1 (Claude) explicitly did **not**
  measure whether the insertions collide with existing anchors — `--mutate .` must run before the PR.

---

## §11 — Delivery

One branch, `fix/guard-inventory-population`, one PR, closing backlog **#72** and **#73**. The merge
tick is written before the PR is opened. A dashboard entry is required, and row status ticks ride in
the same PR as the work.

## §12 — Round 1 record

**Both halves NOT CONVERGED.** Every finding was re-verified against the code by the author before
acceptance; all sixteen reproduced and none was disputed.

- **Codex** found the `evaluate` contradiction, the grammar hole, `build-m4-schema.py`'s
  misclassification, the missing mutation-manifest surface, and the false `check-selftest-counts`
  claim.
- **Claude** additionally executed the self-exclusion, corrected "three" to eight, found the §2
  causal claim refuted by §1.1, mapped the nine-site blast radius, and found the vacuous F3/F7, the
  contradictory `POPULATION_CASES`, the `SyntaxError` policy gap, and that `gen-m4-manifest.py`'s
  enrolment changes no verdict today.
- **They disagreed on `build-m4-schema.py`** and the finding-half was right — recorded because this
  repo's memory says disagreement is the signal, not noise.
- The Claude half disclosed that a repo-wide grep surfaced ~6 lines of the Codex review written into
  the tree while it worked; it did not open the file. Recorded so overlap is discounted rather than
  read as independent corroboration.

**Round 2 will be scoped to round 1's own fixes** — §3's new grammar, §4's criterion, §5's change
list, §7, and the repaired falsifiers. In this repo's recent slices, round 2's Blockings have
repeatedly been regressions introduced by round 1's fixes.
