# Round 4 — `explainer-src-root-self-configures` (PR #295) — coordinator

```yaml
round: 4
fixes_nontrivial: true
subject: explainer-src-root-self-configures
halves:
  codex: ran
  claude: ran
findings:
  - {id: H1, severity: High, aim: instrument, fix_induced: true, component: class-falsifier, disposition: fixed}
  - {id: M1, severity: Medium, aim: instrument, fix_induced: true, component: class-falsifier, disposition: fixed}
  - {id: M2, severity: Medium, aim: instrument, fix_induced: false, component: suite-construction, disposition: fixed}
  - {id: M3, severity: Medium, aim: instrument, fix_induced: false, component: src-root-probe, disposition: fixed}
  - {id: L1, severity: Low, aim: deliverable, fix_induced: false, component: src-root-probe, disposition: filed}
```

## The round in one line

**The redesign worked — the class is gone from production — and every finding this round was in
the guards written to prove it.**

## The answer to the question this round existed to ask

Both halves were asked directly whether the class was removed or merely relocated.

**Codex:** removed, verified at the caller — `observed.root` decides, and `src_root_help(observed)`
is reached only on failure, with no second env read and no second probe.

⭐ **The Claude half earned a stronger answer by building a BETTER FALSIFIER THAN THE SHIPPED ONE**
— 13 `Path` methods, 9 `os` functions, `builtins.open`, a raising `os.environ`, and a third arm
fixture — and running the **unmutated** production code under it: **128/128 green.** Production
renders every arm with the filesystem and the environment fully denied. Nineteen mutations; every
re-derivation injected into production was caught.

That is the difference between *"I could not find a defect"* and *"I constructed the instrument that
would have found one, and it stayed green."*

## Findings — all in the instrument, and the same shape three more times

### H1 — the falsifier never rendered one of the three arms → **FIXED**

`_gone_checkout_help`'s `why` branches on `env_value`; the non-empty side is the arm r2's Medium
**added**, and neither fixture reached it. **MEASURED:** `observed.fallback.exists()` — *the second
entry of `_PROBES`* — inserted there passed **128/128**, while the identical probe in the sibling arm
died instantly.

⚠ **This is not a denylist gap.** The denylist names that probe and is powerless because the line
never executes. **A guard's coverage is the product of what it FORBIDS and what it RUNS**, and only
the first half was being thought about.

### M1 — the denylist covered `pathlib` only → **FIXED**

`os.path.isdir`, `os.path.exists` and `os.access` each survived at 128/128 while the comment claimed
*"every probing entry point a renderer could reach is named."* False — and a coverage claim in a
guard's own prose is **the least-tested sentence in a file, because nothing executes a docstring.**
The alternative was checked and rejected on evidence: audit hooks do not fire for `stat`/`access`/
`Path` methods, so a denylist is the right mechanism; it simply had half its surface.

### M2 — the eager-fixture hazard at two more sites → **FIXED**

⭐ **And `rev_before` taught why "make it lazy" is not the rule.** It is a SNAPSHOT taken before the
file changes; a lambda re-reads it afterwards and the later "revision changed" cases go vacuously
false — measured, 129/131, two red. The raise became a **value** instead, which keeps the snapshot
and still reports through the runner.

### M3 — the probe's `MISSING_FALLBACK` arm had no case → **FIXED**

Every `MISSING_FALLBACK` fixture was a hand-built `SrcRoot` that never went through `src_root`. **A
fixture that bypasses the function under test proves the fixture.** `fallback_ok = REPO.is_dir()` →
`= True` survived 128/128, and the consequence is not cosmetic: with the checkout gone the probe then
returns `OK` with a non-None root, the caller never renders the remedy, and the reader gets *"no such
source file"* instead of the recovery instructions this branch exists to give them.

### L1 — `expanduser()` raises on `~unknownuser` → **FILED**

`EXPLAINER_DOCS_ROOT=~unknownuser/x` raises `RuntimeError`; measured live, `GET /src/…` returns
`RemoteDisconnected`. **Pre-existing on `master` since #149** and the same symptom as backlog #87 —
not this branch's work, so it is filed rather than fixed here.

## Q5 — thrashing?

**No, and the classification is stated rather than assumed.** H1 and M1 are fix-induced, but in
`class-falsifier` — the instrument — not in `src-root-help`, which is the component the r3
architecture review was about and which took **no** finding this round.

⚠ **The alternative reading is worth naming:** if the falsifier is counted as part of
`src-root-help`, this would be two consecutive fix-induced rounds and would arm again. It is counted
separately because the r3 arming was about the **renderer's design** — a thing that shipped — while
these are about a **test's completeness**. The production shape took no finding at all this round,
which is the distinction doing the work.

## Q4 — another round owed?

**Yes, narrowly.** Convergence needs **two consecutive rounds** with no Blocking/High and every
finding aimed at the instrument. This round has a High, and L1 is aimed at the deliverable even
though it is filed as pre-existing. Round 5 is owed, and the fixes above are unreviewed code.
