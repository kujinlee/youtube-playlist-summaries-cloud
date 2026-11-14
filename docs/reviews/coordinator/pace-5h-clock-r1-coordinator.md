# Round 1 — `pace-5h-clock` (backlog #645) — coordinator — ⟳ NOT CONVERGED; all folded

```yaml
round: 1
fixes_nontrivial: true
subject: pace-5h-clock
halves:
  codex: ran
  claude: ran
findings:
  - {id: XM1, severity: Major, aim: deliverable, fix_induced: false, component: five-hour-read, disposition: fixed}
  - {id: XM2, severity: Major, aim: deliverable, fix_induced: false, component: block-note, disposition: fixed}
  - {id: Xm1, severity: Minor, aim: deliverable, fix_induced: false, component: block-note, disposition: fixed}
  - {id: CM1, severity: Major, aim: deliverable, fix_induced: false, component: block-note, disposition: fixed}
  - {id: CM2, severity: Major, aim: deliverable, fix_induced: false, component: gate-delivery, disposition: fixed}
  - {id: Cm1, severity: Minor, aim: deliverable, fix_induced: false, component: five-hour-read, disposition: fixed}
  - {id: Cm2, severity: Minor, aim: prose, fix_induced: false, component: block-zone, disposition: fixed}
```

Codex reviewed `ed587026`, Claude `ed587026` (filed at `83584981`). Both ran the self-test (428/428). Folded in `d2433be9`.
Every new case was written first and seen RED against the unfixed code (13 failing, then the gate cases crashed the
suite with `gate_output()` taking 3 arguments) before the fix; 442/442 after.

- **XM2 / CM1** (same defect) the AT MOST 2 AGENTS and NO NEW AGENTS sentences carried `used {pct(used)}`, so #628's
  whole-text dedup said every 1-point move again. Fixed in `block_note`: no moving figure is named (STOP says
  "at the 100% limit", a constant); the docstrings say so. The old case "a moved 5h reading speaks again" is replaced by
  ONE case driving the prompt hook through 70 → 75 → 80 → 80.1 → 85 → 90 → 95 → 100 at 50% elapsed in one session:
  `[T, F, F, T, F, T, F, T]` — silent inside a zone, speaks on a zone change; NO NEW AGENTS' reason changing from the
  clock to the 90% line speaks once (documented). Two mutations re-add `used%` to each sentence and name THIS case
  (the repeat check), not a fixed string.
- **XM1 / Cm1** an absent or `null` `five_hour` read as FREE. Fixed in `_evaluate`: a fresh cache with no five-hour
  window adds ` 5h block: UNKNOWN — … treat it as NOT RUN, never as fine.`, its own sentence, a WARN at any weekly
  level, never deduplicated (it carries `NOT_RUN_MARK`), and it never touches the weekly verdict. Cases: absent and
  null × weekly 10 (WARN + UNKNOWN), 85 (weekly WARN text intact + UNKNOWN), 98.5 (REFUSE + UNKNOWN), and a fixed
  string. The test `cache()` helper now carries a FREE five-hour window by default; `five=None` omits it.
- **Xm1** the STOP wake floored to the minute, so a reset at :30 printed a wake 30 s early. Fixed:
  `local_time(resets + BLOCK_WAKE_AFTER_S, exact=True)`. Case: a reset 30 s past the minute wakes at `02:01:30`.
- **CM2** the zones are spawn rules, but the spawn and wake gates spoke only on REFUSE, so an AFK run never heard them.
  Fixed: `evaluate` fills an optional `parts["five"]` with the five-hour sentence; `main` hands it to `gate_output`,
  which, on any call it ALLOWS, returns `hookSpecificOutput.additionalContext` with that sentence and NO
  `permissionDecision` (the permission flow is untouched; a REFUSE still denies). Cases: `gate_output` unit (WARN, OK,
  CANNOT RUN, overridden REFUSE → the note; REFUSE → deny), and through the shipped hooks (`run-hook.sh`, the same
  seam as the existing hook cases): spawn and wake at weekly 50% / 5h 100% allow with `5h block: STOP` + `WAKE at`,
  spawn at 5h 75.1% attaches AT MOST 2 AGENTS, spawn at 98.5% / 5h 100% still denies. ⚠ BOUND: that PreToolUse honours
  `additionalContext` is from the Claude Code hooks docs, NOT measured on this machine. Not deduplicated: each spawn is
  the moment the rule applies.
- **Cm2** `block_zone`'s `min(..., 100.0)` was unreachable. Removed; the docstring says why. The lower-clamp case
  ("a reset 30 min BEYOND 5 h …") and its mutation stay (re-bound).

**Mutations.** 6 added (both `used%` re-adds, the wake floor, absent-reads-FREE, the gate's silent allow, the
`main()` call site, `parts` never filled — the call-site pair because unit coverage does not compose); 2 #645 entries
re-bound (the lower clamp; the "moving figure" entry now re-adds `used%` and names the repeat case); 6 older entries
re-bound because their anchors sat on lines this fold changed (`gate_output`'s REFUSE test, `evaluate`'s try, the
wake-never-denies call, and three `evaluate(…)` call-site entries). Pin 213 → 219. All 14 applied one at a time to a
temp copy of `scripts/` + `.claude/hooks/` (control 442/442): **14/14 KILLED, each by every case its `expect`
names**; the other 205 entries were not run here
(CI's selected sweep answers them). Every anchor in the manifest resolves exactly once; every `expect` name is a case
the suite prints (442 names checked).

**Decision log.** No row added at this fold. The scheme reads `outcome: continued` as a LOST bet (the failure
observation seen) and FAILs trigger 3 until a next route is logged — measured: a prospective `continued` row made
`check-decision-scheme.py` exit 1 — and `stopped` would be false with r2 still to run. The recent subjects with ≥2
rounds (`627-serve-master`, `625`, `619r1`, `628-pace-once`) each logged their row at termination; this subject
follows them. The r1 bet, for that row: r2 (Codex) finds nothing caused by this fold in `block-note`,
`five-hour-read` or `gate-delivery`.
