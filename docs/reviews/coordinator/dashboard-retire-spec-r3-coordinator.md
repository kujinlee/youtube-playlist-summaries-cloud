# Round 3 — `dashboard-retire-spec` — coordinator — ⟳ NOT CONVERGED (Claude); THRASHING → redesign; 5 fixed, 0 rejected

REVIEW GAP: codex — alternation (rounds 2+ run one half; Codex ran round 2 and runs round 4).

```yaml
round: 3
fixes_nontrivial: true
subject: dashboard-retire-spec
halves:
  codex: gap
  claude: ran
findings:
  - {id: B1, severity: Blocking, aim: deliverable, fix_induced: true, component: store-gate, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: store-gate, disposition: fixed}
  - {id: m1, severity: Low, aim: deliverable, fix_induced: true, component: store-gate, disposition: fixed}
  - {id: m2, severity: Low, aim: deliverable, fix_induced: false, component: retired-reference-gate, disposition: fixed}
  - {id: m3, severity: Low, aim: deliverable, fix_induced: false, component: store-gate, disposition: fixed}
```

Subject: `docs/superpowers/specs/2026-11-24-dashboard-retire-design.md` at `8cb1bf6e` (reviewed); fold at the
commit after it.

- Claude half: `docs/reviews/claude/dashboard-retire-spec-r3-claude.md` — 1 BLOCKER, 1 MAJOR, 3 MINOR. NOT CONVERGED.
- Codex half: not run (alternation).

## THRASHING — the arming condition, answered

`docs/review-method.md` → *The arming condition — full account*: two consecutive rounds whose findings came from
the previous round's fix, in one component.

| Round | Finding | Caused by | Evidence |
|---|---|---|---|
| r2 | XM1 — a merge of master shifts the branch's same-day ids; its answer closes master's ask | r1's K9, which compares HEAD with the CURRENT merge base (the r2 finding is written against K9's text) | r2 coordinator: four-entry fixture, `added_reference_errors` = `[]`, K9's prefix holds. ⚠ The r2 doc recorded `fix_induced: false`, because the shift exists TODAY too; the coordinator's reading (this round's brief) is that XM1 was found AGAINST r1's K9 mechanism. Both facts are stated so the record is not rewritten |
| r3 | B1 — K10 passes vacuously on CI's synthesised merge ref | r2's K10 | Claude r3 measured: walk of 1 commit on the merge ref, K10 `[]`, B open, A closed |
| r3 | M1 — an edit to the answer after the merge launders the shift | r2's K10 ("C = first commit holding the entry") | Claude r3 measured: 3 commits walked, K10 `[]`, misresolution stands |
| r3 | m1 — K10's failure paths unstated | r2's K10 | spec text |

One component (`store-gate`, specifically *how an answer identifies its ask*), two rounds, each finding produced by
the previous fold. **Can a redesign remove it? Yes.** Every finding in the chain exists because an entry's identity
is POSITIONAL (`parse_entries` sets `entry["id"] = f"{date}/{seen[date]}"`, `scripts/check-dashboard-entry.py:671`)
and therefore moves; each check (K9's base, K10's history) tried to detect the move after the fact. Patching K10
again (`--head`, `--merges` walk — the r3 half's own hypotheses) would add a third history-reading mechanism to the
same component.

**The redesign (coordinator decision, recorded in spec §7 as a mechanism choice within the owner's decisions):**
every ask written after S2 carries an explicit, unique, stable key — `[needs-you: <key>]`, answered by
`[resolved: <key>]` (spec §2.3a). Positional ids stay readable only for the pre-S2 asks, which K9 freezes and whose
ordinals cannot move. K10 and its history walk are DELETED; K11 is a shape check on HEAD's store alone. This adds to
the grammar for NEW entries only and touches none of the 591 existing entries, so it is consistent with the owner's
§7 Q1 A. It supersedes the r2 doc's "a stable key would be a grammar change, out of scope".

## Method — what was run in the fold, not taken from the half

A scratch copy of `scripts/` with the extension applied to `check-dashboard-entry.py` (`FLAG` payload, `KEY`,
`key` / `ref`, pass-2 refs and the duplicate-key error) and `gen-dashboard.py` (`resolvers` / `unresolved` keyed on
`ref`), run beside the unmodified copy, real `parse_entries` / `unresolved` throughout:

| Case | Result |
|---|---|
| live store, 591 entries, extended vs unmodified parser | identical in every field but `key` / `ref`; `ref == id` for all; 0 open asks both; heads-ups `2026-08-31/5`, `2026-09-15/10` |
| CONTROL, unmodified, bare ids, merged master-first | open: `Branch B ask.`, master's silently closed — r2's hazard reproduced |
| keyed, authored / merged master-first / merged branch-first | open: none / `Master A ask.` / `Master A ask.`; no errors — cannot misresolve in either order |
| keyed, `[resolved: 2026-11-25/2]` naming a keyed ask | parse error (generic "could not be parsed" text; K11 owes the *use its key* wording) and both asks stay open |
| two asks with one key | both entries errors — loud; the answer "names no entry" |
| legacy positional resolve of a keyless ask with keyed same-day asks after it | clears the legacy ask; the keyed one stays open |
| `header_error` | refuses a key of id shape, `Bad_Key`, and key + `[heads-up]`; today's unmodified one refuses `[needs-you: ok-key]` as "unrecognised text" |

Found in the fold, not a review finding: a duplicate key on master could not be repaired under K9 as written
(every edit to an old entry refused, and an appended entry cannot un-duplicate). K9 gains one narrow exception —
a base entry that is a parse error at the base may change if its date is unchanged and it parses at HEAD; ordinals
are claimed from the date (`:669`), so no id moves. INFERRED, not run; round 4 reviews it.

Consumers of an entry's identity checked and each given a row in spec §2.3a: `resolvers` / `cleared_ids` /
`unresolved` (`scripts/gen-dashboard.py:442`, `:454`), parse pass 2, `needs_from_dashboard`
(`scripts/goal-tree.py:1314`, whose NEEDS YOU diff compares `(source, ref)` at `:1165`), `pending_asks`
(`scripts/compaction-state.py:486`), the skill's grammar line (`.agents/skills/dashboard/SKILL.md:40`), K2, K3.

## Dispositions

| Finding | Severity | Disposition | Spec section changed |
|---|---|---|---|
| **B1** K10 vacuous on CI's synthesised merge ref | Blocking | FIXED BY REDESIGN — moot: K10 is withdrawn; K11 reads only HEAD's store, for which the merge ref is the right subject (it is what master will hold) | §2.1, §2.2, new §2.3a, §3 K10 struck / K11 added, CI paragraph |
| **M1** an edit after the merge defeats K10 | Medium | FIXED BY REDESIGN — moot: no check depends on when an entry first appeared; a key does not move when its entry is edited | §2.3a, §3 K11 |
| **m1** K10's failure paths unstated | Low | FIXED BY REDESIGN — moot: K10 is gone and no kept check reads history (no `rev-list`, no "first holder"); K2 / K9's merge-base read is unchanged from r1 | §3 CI paragraph |
| **m2** K8 omits subprocess argv; href category unbounded | Low | FIXED: an argv category (a `"scripts/<retired>.py"` literal in an argv list/tuple or a command table), seeded from `check-merge-ready.py:2198`; the href bound stated (a literal is seen, a run-time `f"/{name}"` is not; `key_link` has its own category; a missed link lands on the archive record) | §3 K8 |
| **m3** K9 misattributes an unclosed base fence | Low | FIXED: K9 names the open fence when the only difference is the base's last entry and the base parse ends fenced; one fixture | §3 K9 |

**Non-trivial fixes (why `fixes_nontrivial: true`):** a grammar extension for new asks, a new check (K11), the
withdrawal of K10, a K9 exception. Round 4 (Codex half, by alternation) owes a review of §2.3a, K11 and the K9
exception — and under the round cap (§0 Q4c) files anything below a BLOCKER.
