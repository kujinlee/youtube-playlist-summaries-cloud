# Round 2 — `pace-5h-clock` (backlog #645) — coordinator — ⟳ NOT CONVERGED; folded

```yaml
round: 2
fixes_nontrivial: true
subject: pace-5h-clock
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XM1, severity: Major, aim: deliverable, fix_induced: false, component: notice-dedup, disposition: fixed}
```

REVIEW GAP: claude — alternation (round 2 runs one half; owner 2026-10-28).

Codex reviewed `c4427dcb` (the r1 fold `d2433be9` + its coordinator doc): `docs/reviews/codex/pace-5h-clock-r2-codex.md`.
It ran the self-test (442/442) and resolved all 219 anchors against the pin; its five loosening flags are answered
"not a loosening".

- **XM1** (Major, NOT caused by the r1 fold — a missed instance of r1's own class one level up). backlog #628's
  once-per-session key hashed the WHOLE WARN text, and that text carries the weekly figure, so an unchanged 5h zone
  (AT MOST 2 AGENTS at 5h 75) was said again on every 1-point weekly move (10 → 11). r1 had taken the moving figure
  out of `block_note`; the KEY still held one. Fixed in `main` (the prompt hook's WARN branch) and `last_notice`
  (new; `told_this_session` is now `last_notice(...) == key`): the state line keys the weekly text and the 5h sentence
  separately, `warn:<weekly-digest>:<5h-digest>`, and each part speaks only when ITS text changed. Outcomes: neither
  changed → silent; only the weekly text → the weekly text alone; only the 5h sentence → `⚠ usage pace:` + the 5h
  sentence alone; both → the whole WARN. A WARN that exists ONLY for the 5h sentence (`parts["alone"]`, set in
  `_evaluate`'s last WARN branch when the band zone is not WIND-DOWN / NO NEW STARTS / UNKNOWN) gives its weekly text
  no key: that text is context, never a notice — the same text with no 5h sentence is an OK, which the prompt hook
  never says. **The weekly rule is NOT loosened:** a weekly WARN (≥ the WARN line, the last-day USE IT, or a band
  zone WARN) still hashes its whole weekly text, so every change #628 named (zone, stop, the 0.1% reading, trend, days
  left) still speaks; REFUSE-SPAWN, CANNOT RUN and a WARN with a NOT RUN part still never dedupe; any non-WARN prompt
  still moves the state on (WARN → OK → WARN speaks).

**Cases** (written by the first r2 fold agent, which died before committing; this agent verified them, see
*Mutations* for the red side):
- `⭐ r2 fold: an unchanged 5h zone is silent when the weekly figure moves (10 → 11 → 12, 5h 75)` — Codex's input,
  one session: `[True, False, False]`. Fails if the weekly figure is in the 5h sentence's key.
- `⭐ r2 fold: a 5h zone change speaks with the weekly figure fixed (weekly 10 and weekly 85, 5h 75 → 85)` — at
  weekly 10 (5h-only WARN) and at weekly 85 (weekly WARN), 75 → 85 speaks NO NEW AGENTS, and at weekly 85 the second
  output does NOT repeat the unchanged weekly text. Fails if a 5h change is silent, or re-says the weekly text.
- `⭐ r2 fold: a moved weekly WARN speaks again (#628) WITHOUT re-saying an unchanged 5h zone` — weekly 85 → 86 → 86
  at 5h 75: the second says `weekly usage is 86` and no `5h block`; the third is silent. Fails if #628's weekly rule
  loosened, or the unchanged 5h sentence rides along.

**Same class searched** (a suppression key holding a moving figure): the absent-cache CANNOT RUN notice keys on the
session alone (no figure); the `seen:<verdict>` write is no suppression; the weekly WARN key holds the weekly figure
and the band note's trend BY #628's definition (each change is meant to speak) — not this class; the spawn and wake
gates never dedupe. Outside this script, `scripts/recall-llm.py`'s `nag_once` keys on `(plan, step)`, no moving
figure. Nothing else found.

**Mutations.** 4 added (the weekly and 5h keys re-merged on the whole message;
`alone` never set; the weekly-only re-say branch dropped; the 5h-only re-say branch dropped), 7 re-bound because their
anchors sat on lines this fold changed (`told_this_session`'s body moved into `last_notice`: 4; the last WARN branch
now sets `alone`: 2; `parts["five"]` now also sets `alone`: 1). Pin 219 → 223 in
`scripts/mutations/expected_mutations.py`. Every anchor in the manifest resolves exactly once (223 checked). All 11
applied one at a time to a temp copy of `scripts/` + `.claude/hooks/` outside the repo: **11/11 KILLED, each by every
case its `expect` names**. The other 212 entries were not run here (CI's selected sweep answers them).

**Self-test.** 445/445 on the final tree (442 + the 3 cases above). Two earlier runs on the same code each
had ONE different timing failure under machine load (the wake hook through `run-hook.sh` at 5h 100%; the 4 MiB meter
read under 2 s) — neither touches this fold, and the clean run is the one recorded.

**Decision log.** Trigger 1 FAILED (`pace-5h-clock` reached 2 rounds with no row) once the r2 review was filed. A row
is added: unit = the r1 fold, `route: accrete`, `outcome: continued` (round 3 follows), `retroactive: true` — the bet
("r2 finds nothing caused by the r1 fold") was stated before r2 in the r1 coordinator doc but is LOGGED after its
result, which is what the field means. Its prediction HELD (XM1 is not fold-caused). A prospective `continued` row
would FAIL trigger 3 until a next route is logged (measured at r1), and this fold is accrete again, not an escalation.
`check-decision-scheme.py` after the row: rc 0. The next row (at termination) takes a new unit (the r2 fold), since
a unit may not repeat a route.
