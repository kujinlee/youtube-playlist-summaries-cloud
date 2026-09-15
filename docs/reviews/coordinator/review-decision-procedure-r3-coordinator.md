# review-decision-procedure — round 3 — **ARCHITECTURE REVIEW, armed and answered**

```yaml
round: 3
subject: review-decision-procedure
halves:
  codex: ran
  claude: "GAP: this session spawns no subagents"
findings:
  - {id: B1, severity: Blocking, aim: deliverable, fix_induced: true, component: scope-for, disposition: fixed}
  - {id: B2, severity: Blocking, aim: deliverable, fix_induced: false, component: parse-header, disposition: fixed}
```

* Codex: `docs/reviews/codex/review-decision-procedure-r3-codex.md` (`gpt-5.5`) —
  **2 Blocking. NOT CONVERGED. Verdict: ARCHITECTURE REVIEW.**
* **REVIEW GAP: claude** — as rounds 1 and 2.

⭐ **TWO JUDGES, INDEPENDENTLY, REACHED THE SAME VERDICT ON THE SAME TEST.** The coordinator
found the `docs/` instance while r3 was running and wrote REDESIGN into its scratch notes;
Codex found it unprompted by the notes and graded it REDESIGN. The brief demanded a
per-finding answer to *did the previous fix cause this?* and got one.

## The arming condition, with its evidence

| round | the list that was wrong | measured |
|---|---|---|
| r1 B2 | the **risky** allowlist missed `app/api/` | the route's own docstring says *"money is charged there"* → `one-round` |
| r2 H1 | the **inverted** default still listed `scripts/` | `check-paid-caller-arrival.py` protects paid attempts → `one-round` |
| r3 B1 | …and still listed `docs/` | two mode-`755` schema gates, run as gates 1 and 2 of `check-schema-gates.sh` → `one-round` |

**Inverting the default MOVED the list; it did not remove it.** Codex: *"The repair needed
is not another prefix carve-out."*

**The test** (`:156`) — *can a redesign remove it?* — **yes, for both Blockings.** Mechanism
defect. Patching was the wrong prescription and had been for two rounds.

## The redesign

⭐ **THE CLASSIFIER ALREADY EXISTED, HARDENED, IN THIS REPOSITORY, AND I WROTE A SECOND
ONE.** `check-review-recorded.py:187`'s `is_prose()` answers exactly this question. It
carries `CODE_UNDER_PROSE` for the executable gates under `docs/` (`:181`), was hardened
over four rounds of PR #299, is mutation-covered, and ships `prose_exceptions_cover()` as an
anti-drift falsifier against the CI workflow globs. Its own comment states the rule my three
lists kept getting wrong:

> a gate script does not stop being code by living in a documentation directory

`scope_for` no longer owns a path taxonomy. It asks the one that exists: **contained ⟺
`is_prose`**, both being the same axis — blast radius. The classifier is **injected**, so
the rule stays pure and cheap to case; `main()` passes the real one, and a loader that
cannot find it **raises** rather than guessing at blast radius.

**Measured after the redesign** — all three instances dissolve at once, and prose is
unharmed:

```
full-loop  app/api/pdf/[id]/route.ts                     (r1 B2)
full-loop  scripts/check-paid-caller-arrival.py          (r2 H1)
full-loop  docs/…/mutate-schema.py                       (r3 B1)
one-round  docs/review-method.md                         (must not regress)
```

⚠ This is the failure recorded thirteen times in this project's memory — *a second
implementation of one rule drifts* — committed while building the tool meant to stop
exactly this kind of repetition.

## B2 — an ABSENT `findings:` key read as a clean round

**ACCEPTED AND FIXED.** `_findings_span` returns `""` when the key is missing, so
`declared == 0 == len(findings)` and **nothing was validated**. `parse_header` returned
`{'round': 1, 'findings': []}` for a header with no findings key at all.

⛔ **r1's B1 for the THIRD time, through a third shape** — first block-style items, then a
missing colon, now a missing key. Each repair closed the shape in front of it.
**An explicit empty list is a claim; a missing key is a silence**, and the two must not read
alike. Now raises.

Codex graded this *not* fix-induced — correct, it predates r2's repair — but noted the
redesign dissolves it too.

## ⚠ A broken harness reported a PASS, and the control caught it

The first mutation run of the redesign reported **0 cases red** for both new mutations.
Not a missing falsifier: the ad-hoc harness copied the file to `/tmp`, and after the
redesign `_repo_is_prose()` resolves `REPO` from `__file__`, so the run died with a
traceback and there were no `[FAIL]` lines to count. **A traceback and a clean suite are
indistinguishable to a grep.** Re-run with the tree staged, over a proved-green control:

```
CONTROL (unmutated, staged)                      47/47
scope_for ignores the classifier                 11 case(s) red
an absent findings key is accepted                1 case red
thrashing unions instead of intersecting          3 cases red
convergence ignores aim                           1 case red
```

⚠ **And the redesign caused this**: delegating to a repo-resident classifier means the
suite is no longer location-independent. Stated rather than discovered later — `--mutate .`
stages `HARNESS_TREE`, so CI is unaffected, but any ad-hoc harness must stage the tree too.

## Verified on this tree

```
check-review-decision --self-test  47/47   (43 before; 4 added for the redesign and B2)
mutations 4 -> 6, EXPECTED_MUTATIONS 633 -> 635
check-plan-code · check-fixture-variation · check-selftest-counts ·
check-ratchet-contract · check-docs                                  all rc=0
```

**NOT CONVERGED — round 4 owed**, and it reviews **a redesign**, not a patch. The branch is
full-loop, so convergence needs two consecutive clean rounds.
