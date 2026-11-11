# Round 4 — `banner-thread-armed` — coordinator — ❌ NOT CONVERGED (1 Major) — THRASHING, resolved by REMOVAL

```yaml
round: 4
fixes_nontrivial: true
subject: banner-thread-armed
halves:
  codex: ran
  claude: "GAP: alternation — the r3 fold was written by a Claude implementer subagent, so r4 is the Codex half"
findings: [identical-copy-collapse-merges-different-ancestry]
```

REVIEW GAP: claude — alternation, per `review-method.md` -> Round topology step 4: the round-3 fold was written by a Claude implementer subagent, so round 4 goes to Codex. Not a failure to run.

## Thrashing or prose floor? — THRASHING

The arming condition holds: round 3's findings came from the round-2 fold, and round 4's one Major
came from the round-3 fold, both in ONE component — the every-checkout reader's handling of a slug
held in more than one checkout. Asked *can a redesign remove it?*: yes, by REMOVING the feature. The
byte-identical collapse assumed equal content means the same plan, which Codex disproved (two children
of different parents, identical bytes). Identity becomes (checkout, slug), always: duplicates are
separate labelled rows; an identical copy is counted twice, a stated limit. That deletes the class
rather than patching it a third time, so no architecture review is convened — the redesign IS the
response the rule asks for, and it is a reduction.

FOLD: subagent — the implementer retires the collapse it added.
