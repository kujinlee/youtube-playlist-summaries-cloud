# The guard inventory declares its population — Design Spec

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

**Backlog:** #72 (and #73, which closes with it). **Status:** v1 — design approved by the user
2026-09-02, not yet reviewed.

⚠ **Anchor fit, stated rather than assumed.** `status-visibility` is the anchor every tooling spec in
this repo has used, including `2026-08-29-mutation-manifest-retarget-design.md`, which is pure test
infrastructure. The fit is real rather than clerical: a guard inventory exists to make the true state
of guard coverage visible, and the defect below is precisely a case where it reported coverage it did
not have. No new anchor is allocated — a name in `docs/anchors.md` is permanent, and allocating one is
the user's call.

---

## §1 — The defect, as measured against `77c5676d`

`scripts/check-ratchet-contract.py` polices every guard in the repo: each must have a `--self-test`
(R1), must not return `0` from an `except` handler (R2), and must have a caller or a written
`NO-CALLER:` reason (R3). Its value depends entirely on **which files it looks at**.

It looks at 26 of 45. And it says otherwise, in two places:

| Where | The claim | What the code does |
|---|---|---|
| `discover_ratchets:67` (dead) | discovery from *"TWO independent sources"* — CI step names, and a docstring self-declaring via `RATCHET_DOCSTRING_RE` | Source 2 is **unreachable**. No caller ever offers it a non-`check-*` file |
| **`discover_guards:132` (live)** | **"EVERY guard on disk. The population is the FILESYSTEM."** | Both callers (`:174`, `:403`) build the list from `(ROOT/"scripts").glob("check-*.py")` before handing it over |

The second row is the sharper one and is **not** in backlog #72 as filed. The row is about a function
nothing calls; the same false claim is in the function that runs. `GUARD_PATH_RE`
(`scripts/check-[\w.-]+\.py`, `:108`) then filters a population that was already name-filtered — a
second sieve with the same mesh, which is why the narrowing is invisible when reading `discover_guards`
alone.

**Measured 2026-09-02:** `scripts/*.py` = 45; `check-*.py` = 26; the live run reports
`guards discovered (26)`, exit 0; `--self-test` 21/21.

### 1.1 — Why the row's first proposed shape does not work

Backlog #72 offers *"widen the population to `scripts/*.py` and let `RATCHET_DOCSTRING_RE` do the
selecting it already claims to do."* **Measured: that enrolls 6 files, of which 1 is a genuine
self-declaration.**

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
enroll the file. This is the same emphasis- and context-blindness class this repo has recorded for
`**Decide:**` (backlog #81), `NO-ENTRY:` and `REVIEW GAP:`.

### 1.2 — Why the fact was known and did not travel

`scripts/explainer-serve.py:68-73` already records the exact mechanism — *"that script discovers by
globbing `scripts/check-*.py`, so this file is never even read"* — written while correcting a false
self-description. **A true statement in a neighbour's comment did not correct the false one at the
source.** That is the same shape as the defect itself, and it is why the fix must be in the code's
behaviour rather than in more prose.

---

## §2 — The decision: declare-out

**The population is every `scripts/*.py`. A file leaves the inventory only by saying so in writing.**

Two alternatives were costed and rejected:

**Honesty-only (rejected).** Correct both docstrings to say the population is `scripts/check-*.py`,
delete the dead function, change no behaviour. XS, and honest — but it closes the row by retiring the
ambition rather than meeting it. It leaves `gen-m4-manifest.py --check`, a real ratchet, unpoliced,
and leaves the next unconventionally-named guard invisible.

**Declare-in with an unambiguous marker (rejected).** Widen the population, select on an explicit
token such as `GUARD: yes` instead of the bare word. It fixes §1.1's false positives cheaply, but it
is a registry — and `discover_ratchets`'s own docstring already rejected registries as *"evadable by
simply not registering"*. That is precisely how `gen-m4-manifest.py` came to be missed. Rebuilding the
rejected mechanism under a new name is not a fix.

**Declare-out (chosen)** is the only shape where the inventory's stated purpose — noticing things
nobody is looking at — survives contact with its implementation. **Omission fails.** A new script that
declares nothing is in the inventory, and stays red until someone decides which it is.

It is also not a new idea in this file. `NO-CALLER: <reason>` is the same move one level down: a
machine-readable written claim, reviewable in a diff, that cannot be made by accident or by silence.

---

## §3 — The declaration grammar

One line in the **module docstring**:

```
NOT-A-GUARD: <reason>
```

```python
NOT_A_GUARD_RE = re.compile(r"NOT-A-GUARD:[ \t]*(\S[^\n]*)")
```

⚠ **`[ \t]`, never `\s`** — copied verbatim from `NO_CALLER_RE` (`:117`) and for the reason recorded
in the comment above it: `\s` crosses the newline and adopts the *next* docstring line as the written
reason, turning the opt-out into a rubber stamp for any file whose docstring happens to continue. The
`\S` then requires the reason to be non-empty on that same line. This project has already
mutation-tested that distinction once; the new rule inherits it rather than re-deriving it.

Declaring out removes a file from the inventory **entirely** — it is not listed, and R1/R2/R3 are not
applied to it. This is a statement about the *population*, not an opt-out from one rule.

---

## §4 — The verdict on all 19 non-`check-*` scripts

### IN the inventory (2) — both already satisfy the contract

| File | Why it is a guard |
|---|---|
| `verify-exclusion-reasons.py` | *"EXECUTE the written reasons in `check-catalog-coverage.py`, instead of re-reading them"* — its entire purpose is to fail when a written reason stops being true |
| `gen-m4-manifest.py` | carries `--check`: *"regenerate and FAIL if it differs (ratchet)"* |

`gen-m4-manifest.py` **is the payload of this change**. It is the one genuine guard the current
inventory cannot see, and the concrete answer to "what does widening actually buy".

### OUT (17) — each gets one `NOT-A-GUARD:` line

| Category | Files |
|---|---|
| Page generators | `gen-backlog-page.py`, `gen-dashboard.py`, `gen-goals-page.py`, `brief-compose.py`, `regen-skills-doc.py` |
| Library modules (imported, not executed) | `page_markup.py`, `page_chrome.py`, `subject_status.py`, `m4_catalog.py`, `m4_base_db.py` |
| Tools | `explainer-serve.py`, `prior-art.py`, `codex-review.py`, `codex-frontier-model.py` |
| Builders / reporters | `build-m4-schema.py`, `session-skill-report.py`, `skill-usage-audit.py` |

**Net: 26 → 28 guards. 17 declarations. Zero code repairs. `BASELINE` stays at its hard floor of 0.**

That last number is the one that makes this S rather than M, and it is worth stating why it is not
luck: of the 10 non-`check-*` scripts that fail R1/R2/R3 today, **all 10 are in the OUT set**, so each
resolves to a declaration rather than to work.

### 4.1 — The closest call, recorded because it was close

`codex-review.py` is **OUT**, and it was the one file the user was asked to confirm. It exits `1` for
*"gate did NOT run"* and `2` for *"REFUSED"*, which is gate-shaped, and `docs/plugins.md` treats its
failure modes as safety-critical. It is out because it **runs** a gate rather than **being** one: the
contract's three rules do not describe what makes it trustworthy, so enrolling it would add a file the
inventory cannot actually police. Confirmed by the user 2026-09-02.

### 4.2 — Why library modules are OUT rather than a rule change

`page_markup.py`, `subject_status.py`, `m4_catalog.py` and `m4_base_db.py` are `import`ed by 4–5
scripts each and never invoked as programs. R3's `invocation_re` deliberately matches an *invocation*
(`python3 foo.py`, `./foo.py`), not a mention — so an imported module reads as "nothing executes it".

That is R3 behaving correctly. The answer is not to teach R3 about imports; it is that **a library is
not a guard**. Backlog #72 warns against the mirror-image error — *"a renderer belongs in a guard
inventory only if we decide guards and subjects are the same population, which is a separate call"* —
and this spec decides it: **they are not the same population.**

⚠ Three files in the OUT set — `page_markup.py`, `page_chrome.py` and `gen-dashboard.py`, two library
modules and a generator — *do* satisfy R3 today, because CI invokes their `--self-test` and
`invocation_re` sees that as a caller. They are still declared out. Passing a rule is not membership of
the population, and this spec's whole subject is the difference between the two.

---

## §5 — What changes in `scripts/check-ratchet-contract.py`

1. **`discover_guards`** takes the script *texts*, not just paths, and returns every `scripts/*.py`
   whose docstring carries no `NOT-A-GUARD:` line. `GUARD_PATH_RE` widens from
   `scripts/check-[\w.-]+\.py` to `scripts/[\w.-]+\.py`.
2. **Both false docstrings corrected in place.** `discover_guards`'s *"the population is the
   FILESYSTEM"* becomes true for the first time; the two-source paragraph goes with the function
   below. The corrections keep what made the claims false, per this repo's practice of correcting
   rather than deleting.
3. **`discover_ratchets` and `RATCHET_DOCSTRING_RE` deleted**, with their self-test cases. See §7.
4. **The stale sanity comment** at `:404` — `"This project has 24"` — is already wrong (26 today) and
   becomes 28. The `if not ratchets` check it annotates is unchanged.
5. **17 one-line docstring additions** across the OUT set.

`evaluate`, `check_contract`, `check_caller`, `fail_open_handlers`, `invocation_re`, `NO_CALLER_RE` and
`BASELINE` are untouched.

---

## §6 — What this does NOT do

**Stated rather than hidden, because an overclaimed guard is the defect this spec exists to fix.**

- **It does not make lying impossible.** Nothing mechanically stops `NOT-A-GUARD:` being written on a
  real guard. It is a written, reviewable claim — the same trade this file already accepts for
  `NO-CALLER:`. What changes is that **silence is no longer an option**: the previous mechanism let a
  guard escape by being named unconventionally, with nobody stating anything at all.
- **It does not verify that an IN file is a good guard**, only that it has a self-test, no fail-open
  handler, and a caller. R1–R3 are unchanged.
- **It does not reach outside `scripts/`.** Guards under `.claude/hooks/` are still discovered only as
  *callers*, never as subjects. That gap is unchanged by this spec and is not claimed to be closed.
- **It does not police `scripts/*.sh`.** The population is `*.py`, as before.

---

## §7 — Backlog #73 is settled as DELETE, and closes here

Backlog #73 (*"`discover_ratchets` is dead production code, kept alive only by its own self-test"*) was
filed deliberately blocked on this decision: *"if #72 is resolved by widening the population,
`discover_ratchets` may be the right implementation to restore rather than delete."*

**It is not the right implementation.** The chosen mechanism is declare-*out*; `discover_ratchets`
implements declare-*in* via a bare-word docstring match, which §1.1 measured as unable to tell a
declaration from a denial. Restoring it would ship the defect. It is deleted, along with the share of
the 21 self-test cases that exercised it.

Both rows close in this PR. Per the convention learned in PR #213, each closed row must **lead**
`✅ (was 🟠)`, and its `GROUPS` tuple in `scripts/gen-backlog-page.py` must be deleted — the coverage
check is bidirectional and will refuse prose describing a now-closed item.

---

## §8 — Falsifiers

Each states the observation that would make it FAIL, per `docs/dev-process.md`.

| # | Falsifier | Fails if |
|---|---|---|
| F1 | `gen-m4-manifest.py` appears in the `guards discovered (…)` line | it does not — widening bought nothing |
| F2 | Count is exactly 28 | any other number: the OUT list is wrong, or a file was missed |
| F3 | Create `scripts/zz-probe.py` with no `--self-test` and no declaration → contract exits **1** | it exits 0 — omission still escapes, which is the whole point |
| F4 | Add `NOT-A-GUARD: a probe` to that file → contract exits **0** | it stays red — the opt-out does not work |
| F5 | Write `NOT-A-GUARD:` with the reason on the *next* line → the file is still IN | it is excluded — `\s` regression, the rubber-stamp bug |
| F6 | `grep -rn discover_ratchets scripts/ .github/ .claude/` returns nothing | any hit — #73 not actually closed |
| F7 | `BASELINE` is still `0` and the run is green | a raised baseline would launder the 10 failures instead of resolving them |

F3–F5 run against a temp copy of the repo, never the live tree — an instrument that edits the repo
corrupts its peers.

---

## §9 — Test and mutation coverage

- **Self-test cases** for `discover_guards`'s new behaviour: a `check-*` file (IN), a non-`check-*`
  file with no declaration (IN — the payload case), a file with `NOT-A-GUARD:` (OUT), a file with a
  bare `NOT-A-GUARD:` and prose on the next line (**IN** — the near-miss F5 asserts), and a file whose
  docstring merely *mentions* the phrase in prose without the colon form (IN).
- **Cases deleted** with `discover_ratchets`. `scripts/check-selftest-counts.py` ratchets the total, so
  its pinned count moves in the same commit — up or down, whichever the arithmetic gives. ⚠ It must
  **not** be "corrected" toward a remembered number.
- **Mutation manifest** (`scripts/mutations/*.json`), each entry naming exactly ONE case that goes red:
  - `GUARD_PATH_RE` narrowed back to `scripts/check-[\w.-]+\.py` → must go red **via the
    `gen-m4-manifest` discovery case**, not via a count assertion.
  - `NOT_A_GUARD_RE`'s `[ \t]` widened to `\s` → must go red via the F5 near-miss case.
  - `EXPECTED_MUTATIONS` rises by the number added. It cannot fall.
- ⚠ **Anchors bind by TEXT.** This change edits `discover_guards`, which existing mutation anchors may
  target. Every anchor touching that function is re-checked and retargeted if the surrounding text
  moved — a refactor orphans the mutations guarding it, and the suite stays green while it happens.

---

## §10 — Delivery

One branch, `fix/guard-inventory-population`, one PR, closing backlog **#72** and **#73**. The merge
tick is written before the PR is opened. A dashboard entry is required — the branch changes tracked
files — and the row status ticks ride in the same PR as the work.
