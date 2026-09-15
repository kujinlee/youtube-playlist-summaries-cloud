# review-decision-procedure — round 2, coordinator adjudication

```yaml
round: 2
fixes_nontrivial: true
subject: review-decision-procedure
halves:
  codex: ran
  claude: "GAP: this session spawns no subagents"
findings:
  - {id: B1, severity: Blocking, aim: deliverable, fix_induced: true, component: parse-header, disposition: fixed}
  - {id: H1, severity: High, aim: deliverable, fix_induced: true, component: scope-for, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: parse-header, disposition: fixed}
```

**REVIEW GAP: claude** — as round 1; this session does not spawn subagents.

* Codex: `docs/reviews/codex/review-decision-procedure-r2-codex.md` (`gpt-5.5`) —
  **1 Blocking, 1 High, 1 Medium. NOT CONVERGED.**

⛔ **ALL THREE ARE FIX-INDUCED — every one sits inside round 1's repair.** That is the
thrashing signature by this branch's own arming condition, and it is recorded here so the
next round must answer it rather than discover it. The counter now stands at **one**
consecutive fix-induced round; a second in `parse-header` or `scope-for` arms the
architecture review.

## B1 — parity proved a dict appeared, not that it SAID anything

**ACCEPTED AND FIXED.** r1's repair counted list-item markers and refused a mismatch. Codex
went one layer deeper with a missing colon:

```yaml
  - id: H1
    severity High        # ← no colon
    aim: instrument
```

The field is simply absent. `.get("severity")` returns `None`, which is neither `Blocking`
nor `High`; `aim` is `instrument`. The finding reads as **clean**, the round reads as
converged, and `decide()` returned `STOP`. Codex executed it.

⭐ **The same fail-open as r1's B1, one layer in — and r1's fix is what created the
opportunity to be wrong at this layer.** Parity is a claim about *shape*. A safety record
needs a claim about *content*.

⛔ **And `docs/round-header-template.md` already PROMISED this check** — *"the machine checks
that the fields are present and well-formed"*. It did not. **The sentence preceded the
behaviour by two rounds**, which is this repository's oldest failure: a written assurance
that nothing implements.

**Fixed:** every decision-bearing field is validated against its allowed set — `severity`,
`aim`, `fix_induced`, `disposition` — and `component` must be non-empty, because thrashing
is judged per component and an unnamed one cannot arm it. Anything else raises. The template
now says what the code does.

## H1 — `scripts/` was contained, and that repeated the allowlist mistake inside the inverted default

**ACCEPTED AND FIXED.** r1's B2 killed an allowlist of *risky* prefixes by inverting the
default. The inverted version then shipped an allowlist of *contained* prefixes — and
`scripts/` is where this repository's guards live.

Codex verified against the files rather than arguing: `check-paid-caller-arrival.py`'s own
contract says shipping a caller before the backlog decision *"silently promotes a summary
from 1 paid attempt to 5"*; `check-live-schema.py` exists because no other gate reads the
live database. **Both scored `one-round`.**

⭐ **The class is "a hand-kept list of what is safe", and inverting it moved the list rather
than removing it.** Carving out risky `scripts/` entries would have been the allowlist a
third time, one level down. `scripts/` is removed from `CONTAINED_PREFIXES` entirely.

⚠ **The cost is stated, not hidden.** A single-file guard change is now **full-loop**, which
sits in tension with `:398`'s *"one round is fine"* for contained work. It buys one extra
clean round, and the asymmetry that settled r1's B2 settles this: a wrong `full-loop` costs a
round; a wrong `one-round` merges unreviewed money code.

⚠ **AND IT RECLASSIFIES THIS BRANCH.** `scripts/` is in its own diff, so
`review-decision-procedure` is now full-loop and needs **two consecutive clean rounds** to
converge. The rule was not weakened to spare its author.

## M1 — the parity check refused a legitimate header

**ACCEPTED AND FIXED.** `declared` counted `- ` anywhere in the block, so a `halves.claude`
value written as a YAML block scalar containing a bullet raised
`header declares 2 finding item(s) but 1 parsed`. A **false CANNOT RUN**, correctly graded
below Blocking — but a guard that refuses valid input is a guard that gets switched off.
Markers are now counted only within the `findings:` span.

⚠ The coordinator had found this independently while r2 was running, with a weaker
reproduction (`halves:` as a list), and **held the fix uncommitted** rather than landing it
mid-round — `:355`'s rule, applied correctly this time. Codex's block-scalar case is the
better repro and is the one cased.

## What Codex re-derived rather than inherited

All 13 card citations resolve, including the one that drifted to `:441` in r1's repair, and
the `SUPERSEDED` markers did not shift it further. Mixed flow/block headers parse; a
dedented key after `findings:` parses; `round: 9` with an empty list still yields zero
findings. `middleware`'s missing slash is loose but conservative. A **deleted** `app/api/`
path still forces the full loop.

## Verified on this tree

```
check-review-decision --self-test  43/43   (38 before; 5 added for B1, H1 and M1)
check-docs                          rc=0
all four r1/r2 round documents parse under the STRICTER validation
```

**NOT CONVERGED — round 3 owed**, and the branch is now full-loop, so convergence needs two
consecutive clean rounds. ⚠ **Round 3 must answer the thrashing question explicitly**: all
three of this round's findings were fix-induced, and a second consecutive fix-induced round
in `parse-header` or `scope-for` arms the architecture review.
