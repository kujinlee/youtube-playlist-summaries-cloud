# Round 2 — `seed-explainer-serve-manifest` — coordinator

```yaml
round: 2
fixes_nontrivial: true
subject: seed-explainer-serve-manifest
halves:
  claude: ran
  codex: standin-by-claude   # round 1's Codex half timed out; see that round's REVIEW GAP
findings:
  - {id: H1, severity: High, aim: deliverable, fix_induced: false, component: regenerate, disposition: fixed}
  - {id: H2, severity: High, aim: instrument, fix_induced: true, component: manifest-attribution, disposition: fixed}
  - {id: M3, severity: Medium, aim: instrument, fix_induced: true, component: regenerate, disposition: fixed}
  - {id: M4, severity: Medium, aim: deliverable, fix_induced: false, component: stale-endpoint, disposition: fixed}
  - {id: M5, severity: Medium, aim: deliverable, fix_induced: false, component: post-preamble, disposition: fixed}
  - {id: M6, severity: Medium, aim: deliverable, fix_induced: false, component: get-routing, disposition: fixed}
  - {id: M7, severity: Medium, aim: instrument, fix_induced: false, component: claimed-bound, disposition: fixed}
  - {id: L8, severity: Low, aim: instrument, fix_induced: true, component: bookkeeping, disposition: fixed}
  - {id: L9, severity: Low, aim: instrument, fix_induced: true, component: fixture-variation, disposition: fixed}
  - {id: L11, severity: Low, aim: instrument, fix_induced: false, component: send-headers, disposition: filed}
  - {id: L12, severity: Low, aim: instrument, fix_induced: false, component: explainers-ordering, disposition: fixed}
  - {id: L10, severity: Low, aim: instrument, fix_induced: false, component: process-layer, disposition: filed}
  - {id: S13, severity: Low, aim: instrument, fix_induced: true, component: reviewer-harness, disposition: fixed}
  - {id: S14, severity: Low, aim: instrument, fix_induced: true, component: stale-endpoint, disposition: fixed}
  - {id: S15, severity: Low, aim: instrument, fix_induced: true, component: manifest-attribution, disposition: fixed}
```

## REVIEW GAP: codex — still unavailable; a fresh Claude reviewer stood in, as round 1 said it would

Round 1's Codex half timed out (`gate_ran=false`, recorded in that round's coordinator document and
in `docs/reviews/verdicts/seed-explainer-serve-manifest-r1-codex.verdict.json`). `docs/plugins.md`'s
rule is **do not wait, do not retry** — run a rigorous Claude adversarial review in its place and
note the gap. This round's reviewer was a **fresh** agent with an explicit adversarial mandate and
was briefed to re-examine round 1's original entries and both of its headline findings, not merely
to follow up on the fixes. It did: H2 and M7 are both findings *against round 1's own work*.

⚠ **Stated plainly rather than implied: this branch has had no Codex pass.** The Codex-specific
review can be re-attempted before merge if access returns, and would be worth it — the two halves
have caught different classes all week.

## The headline: 73 mutations applied, 58 survived

The reviewer's own lead is fair and worth repeating — *the branch is correct and round 1's fixes
hold*. What it measured is that **the manifest's 25 entries and the suite's 167 cases both stopped at
the pure-helper boundary**, and eleven of the survivors sat inside `_regenerate` — **the function
round 1 declared fixed with five new cases**.

## H1 — HIGH — the allow-list its own docstring calls "THE WHOLE SECURITY ARGUMENT" could not be falsified

`scripts/explainer-serve.py:1173`. Four claims in that docstring, none with a case. Each mutation
alone, all at **167/167 SURVIVED**: `REGENERABLE.get(want)` → `want`; a defaulted
`.get(want, "gen-dashboard.py")`; a `shell=True` f-string; `str(SCRIPTS / script)` → `script`; and
the 400 body dropping the legal set.

**Proved by execution, not reading.** Under the first, a POST of
`{"page": "../../../../../../tmp/evil.py"}` put that string on the command line and answered
`ok: true`.

⭐ **Round 1 worked inside this function and cased the reply shape, not the argument.** Its five
cases asserted status codes; the only one touching `want` was about a `TypeError`.

**Fixed** with seven cases. ⚠ The key discriminator is a value that is a **legal script name but not
a key** — an allow-list that resolved the caller's string would accept it; a dict of literals refuses
it. A traversal fixture alone would also be refused by a `.get` with a default, so it cannot tell the
two apart. Three more assert the **recorded argv** rather than the reply: exactly
`[sys.executable, str(SCRIPTS / REGENERABLE[page])]`, a list with no shell, bounded by
`REGEN_TIMEOUT`.

**And the sibling of round 1's own headline, three lines below it:** round 1 cased the 504 timeout
arm; the **500 non-zero-exit arm says `NOT REBUILT` for the same reason** and could be deleted
silently. *After fixing, SEARCH for the class* — failing one `if` later, in the commit that cited the
rule. Second instance on this branch, per round 1's own H1.

## H2 — HIGH — my clause-3 case guarded a CONSTANT, so the entry certified a claim that could be false

The entry *"the listener stops being loopback"* pointed at `lambda: HOST == "127.0.0.1"`. The kill is
real; what it guards is the value of a constant. **Measured: leave `HOST` alone and change the bind
at `:1272` to a literal `"0.0.0.0"` — 167/167 SURVIVED.**

The reviewer rated this High where round 1 rated the structurally identical M3 a Medium, and said so
explicitly so the calibration could be disagreed with. **I accept the High**: it is the only finding
where the ratchet *actively certifies a claim that is false*, and the claim is one of four clauses
governing whether an entire checkout is reachable from the LAN.

**Fixed** with a second case: the bind must use the constant. Two facts, because either alone guards
nothing.

## M3–M7, L8, L9, L12 — fixed

- **M3** round 1's `_regenerate` stub stood in for `subprocess.run`'s *result*, so it could not see
  what the handler was about to execute. It now **records argv**, which is what made H1's three
  strongest cases possible.
- **M4** `/_stale` had no case; four guards each deletable. Now four cases. ⚠ See S14.
- **M5** `do_POST`'s whole preamble was uncased — route check, `Content-Length` parsing, the
  `MAX_BODY` bound, non-object bodies, undecodable bytes, and the **measured 2026-08-17 bug** (the
  right question under the wrong key, whose 400 must name the keys it got). Seven cases.
- **M6** an unknown path reaching the content-type map. One case.
- **M7** ⭐ **round 1's correction was itself incomplete.** It corrected the qualitative claim
  ("can never be named") in four places and left the **count** the conclusion rests on: the paragraph
  said *SIX* red cases, *"every one dies by AssertionError"*. Re-measured: **seven**, and the seventh
  is the RATCHETABLE case — a plain `False`, perfectly attributable — which the same paragraph
  describes as the fix. It was measuring a pre-fix world against a post-fix tree. *A correction that
  does not re-measure its own premise keeps the defect.*
- **L8** the debt-retirement comment still said "17 entries". Stale count removed rather than
  re-typed, since it drifts by construction.
- **L9** ⭐ **a gate was printing an instruction this branch created and did not follow:**
  `check-fixture-variation` said *"`safe_path.root` now varies — delete it from KNOWN_UNVARIED"*,
  because round 1's M3 repair added a case against a nested root. Debt paid, 127 → 126 ratcheted.
- **L12** `orders newest first` passed on a name-sort — `a.html` was both older *and* first
  alphabetically, so both orders agreed by accident. A third fixture (`z-oldest.html`) makes them
  disagree.

## L10, L11 — FILED, not fixed

- **L10** the process layer (`start`, `stop`, `detach_streams`, `main`'s routing) has no cases beyond
  `status()`'s exit code. Casing it means binding a port or a much larger fork harness — a new
  mechanism, which `review-method.md` Q3 says to **file**, not to smuggle into a manifest branch.
- **L11** `_send`'s `Content-Length` **value** is unasserted (only its presence). Small, but it sits
  in the same header-stub seam as L10's process work and belongs with it.

Both go to the backlog as one row rather than expanding this branch further.

## S13, S14, S15 — defects in this round's own instruments and fixes

- **S13** *the reviewer's own harness* parsed `^\[FAIL\] ` while the runner prints two leading
  spaces, so three batches reported `fails=0`. It changed no survivor verdict — survivors are decided
  by the `N/M passed` line — and the reviewer recorded it rather than quietly re-running. This is the
  **third** time on this project that a FAIL-parsing stand-in has been weaker than its subject.
- **S14** ⭐⭐ **my first `/_stale` cases passed locally and asserted nothing.** I drove them against
  the **real** `ROOT` on the theory that a page the repo genuinely configures is the honest fixture.
  Under `--mutate .` the child runs with `$HOME` redirected to a directory that does not exist, so
  `resolve_page` returned `None`, the handler answered `fresh` before reaching any line the mutations
  touch, and **two mutations SURVIVED behind green cases**. The world is now BUILT — a page in a
  sandbox `ROOT`, its source in a sandbox `REPO`, a `PAGE_SOURCES` entry, all restored in a
  `finally`. ⚠ **Same shape as the `~`-expansion defect two PRs ago, caught by the same mechanism:**
  a guard running children under a hostile `$HOME` disagreeing with a green local run. *A case whose
  premise depends on the ambient world asserts the world, not the code.*
- **S15** two entries died by exception and were unattributable (`AttributeError` on a list,
  `TypeError` on `None`), and one `expect` was orphaned by renaming the case it named. The first two
  are now wrapped to report the failure as a value; the third is repointed. ⚠ **A manifest binds
  `expect` → case name as TEXT**, so renaming a case silently orphans every entry pointing at it, and
  only a full sweep can see it.

## Evidence

`python3 scripts/check-plan-code.py --mutate .` — **679 mutations, 679 killed, 679 attributed to the
case each names, 0 survivors**, every control proved green first. Suite **167 → 188**, manifest
**25 → 36**, declared total **668 → 679**. Fourteen gates green, including under the non-existent
`$HOME` the harness spawns with.

⚠ **One entry was refused and DROPPED rather than forced:** `if r.returncode != 0:` → `> 0` and
→ `if False:` are different defects sharing one source line, so they share one edit anchor, and the
harness said *"repeats the edit anchors of an earlier entry — it measures nothing new"*. Splitting
the line to manufacture a second anchor is what `check-plan-code`'s own comment calls contorting
shipped code to suit the harness. **The case stays; only the entry is dropped** — coverage and
ratchet entries are different things and this is a place they legitimately differ.

## Q4 / Q5

**Convergence: not reached.** Two High, and `fixes_nontrivial: true` → **round 3 owed.**

**Thrashing: ARMED — and answered by the pre-commitment, not by a third attempt.** Round 1's S3 and
round 2's H2 are both fix-induced in **`manifest-attribution`**, two consecutive rounds, one
component. The round-1 coordinator document pre-committed, before this round ran:

> a third attempt at an entry's attribution should be answered by **deleting the entry** rather than
> re-pointing it again. An entry that cannot find an honest case to name is telling you the case does
> not exist yet.

⭐ **That was honoured, and the distinction it turns on is worth stating.** H2 was not re-pointed —
the case it names was **wrong about the property**, and the repair was to *add the missing fact* (the
bind uses the constant), which is writing the case that did not exist. The pre-commitment forbids
hunting for a red case that makes an entry look covered; it does not forbid making the case correct.
The two entries that genuinely could not find an honest case **were dropped**: the signal-kill entry
above, and round 1's platform-dependent `.resolve()` entry.

⚠ **PRE-COMMITTED FOR ROUND 3, before it runs:** `manifest-attribution` has now thrashed for two
rounds. If round 3 finds a **third** fix-induced attribution defect, the answer is **not** a fourth
repair — it is to stop adding entries to this manifest in this branch, ship what is proven, and file
the remainder. The manifest has grown 17 → 25 → 36 across two rounds while the reviewer's survivor
count fell; that is progress, and there is a point where continuing is worth less than shipping it.
