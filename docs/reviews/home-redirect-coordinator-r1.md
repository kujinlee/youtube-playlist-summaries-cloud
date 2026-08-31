# HOME-redirect slice — round 1, coordinator half

**Subject:** branch `fix/mutation-harness-home-redirect` (Phase 6 candidate 3).
**Codex half:** [`home-redirect-codex-r1.md`](home-redirect-codex-r1.md) — ran on `gpt-5.5`
(`gpt-5.6-terra` and `-luna` both returned HTTP 400 and the wrapper fell through).

**REVIEW GAP: claude — an independent subagent reviewer could not be dispatched under this
session's tool constraints, so the coordinator ran the adversarial pass in its place.**

⚠ **This half was run by the COORDINATOR, not an independently dispatched subagent.** That is a
real weakening — an author reviewing their own diff shares its blind spots — and it is recorded
rather than glossed. It is not the Codex-unavailable fallback; Codex ran fine. `check-review-rounds.py`
refused the round when this file was named `-coordinator-`, which is the check drawing exactly the
distinction this paragraph makes; the gap line above is the honest resolution, not a rename to
`-claude-`.

---

## Codex findings, adjudicated by reading the code

Every one was reproduced by hand before acting. All three stand.

| # | Sev | Claim | Verdict |
|---|---|---|---|
| 1 | Medium | The redirect covers `$HOME` only; `pwd.getpwuid()` and `~user` still reach the real home | **CONFIRMED.** Measured under a redirected home: `Path.home()` and `expanduser('~')` → fake; `getpwuid(...).pw_dir` and `expanduser('~kujinlee')` → `/Users/kujinlee` |
| 2 | Medium | `check()` (plan mode) spawns suites with a redirected but NONEXISTENT home, unlike `mutate_delivered` | **CONFIRMED.** `check()` builds a temp tree and never creates `.home`. Codex's repro reproduced |
| 3 | Low | The canary cleanup could delete a real-home file that merely shares the basename | **CONFIRMED as a class**, though only reachable once the redirect is already broken |

### What was done

1. **Scope stated, then enforced.** The docstring overclaimed ("cannot reach the reader's pages");
   it now says what `$HOME` actually governs. A claim narrowed by prose alone would rot, so
   `home_escapes()` refuses a mutation target using `getpwuid`/`getpwnam`, `expanduser('~user')`,
   or a hardcoded absolute home. Four cases, plus one for the WIRING — this file already records
   *"extracting the function bought coverage of the function; the wiring inherited the same blind
   spot."*
2. **`check()` creates `.home` too.** Verified with Codex's own repro: the plan suite now passes
   `1/1` **and** writes nothing to the real home. Both halves of the property, not one.
3. **The canary's identity is its CONTENT, not its name.** Cleanup reads the file back and unlinks
   only on a match. Verified: a foreign `~/explainers/harness-canary-tmpFOREIGN.html` survives a
   full self-test unmodified.

---

## Coordinator finding — against the fix written for Codex #1

**FIXING A PREMISE IS NOT COVERING THE BRANCH.** `home_escapes` was wired to scan
`root / target` — the delivered source **as it is before the mutation**. But a mutation is the one
thing that rewrites that source, so a clean target says nothing about what the manifest is about to
put there. A manifest entry whose *replacement text* introduced `pwd.getpwuid(...)` would have
passed the new check completely.

Measured: `home_escapes('OUT = pwd.getpwuid(os.getuid()).pw_dir')` flags it, and nothing was
passing that string in. Fixed by scanning every `edits` replacement as well as the target, with a
case whose target is clean and whose *mutation* carries the route.

This is the point of two halves. Codex found the layer I could not see; this half found the hole in
the fix I wrote for it, an hour later, of exactly the class my own notes describe.

---

## Measurements

```
scripts/check-plan-code.py --self-test   145/145   (136 -> 145 over the round)
scripts/check-plan-code.py --mutate .    3 files, 73 mutations, 0 survivors
scripts/check-ratchet-contract.py        OK
scripts/page_markup.py --self-test       78/78
scripts/check-docs.py / check-anchors.py / check-dashboard-entry.py   OK
```

Falsifier for the new guard, run with the PARENT's `HOME` redirected so proving it could not itself
write into the reader's tree: dropping `env=child_env(d)` reddens exactly the three canary cases and
leaves no debris.

**Not converged into a second round.** All three Codex findings and the coordinator finding are
fixed in-branch and re-measured. A round 2 would be reviewing four small fixes each of which already
carries its own case; the standing gap is the *coordinator-half* caveat above, not an unaddressed
finding.

## Out of scope, recorded not fixed

`home_escapes` is static, so a home path assembled at runtime slips past it. Said plainly in its
docstring rather than left for someone to discover. It is a ratchet against the cheap accidents,
not a proof.
