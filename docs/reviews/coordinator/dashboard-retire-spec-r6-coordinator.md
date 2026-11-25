# Round 6 — `dashboard-retire-spec` — coordinator — NOT CONVERGED (both halves); ROUND CAP → 2 BLOCKERs fixed (K7/K8 restored, conflict markers a PROBLEM), 4 carried into the plan, 1 wording fix

```yaml
round: 6
fixes_nontrivial: true
subject: dashboard-retire-spec
halves:
  codex: ran
  claude: ran
findings:
  - {id: B1, severity: Blocking, aim: deliverable, fix_induced: true, component: kept-gates-table, disposition: fixed}
  - {id: CX-B1, severity: Blocking, aim: deliverable, fix_induced: true, component: ask-file-reader, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: false, component: cutover-l1, disposition: filed}
  - {id: m1, severity: Low, aim: deliverable, fix_induced: true, component: ask-file-reader, disposition: filed}
  - {id: m2, severity: Low, aim: deliverable, fix_induced: true, component: ask-file-reader, disposition: filed}
  - {id: m3, severity: Low, aim: deliverable, fix_induced: true, component: ask-file-reader, disposition: filed}
  - {id: CX-m1, severity: Low, aim: deliverable, fix_induced: true, component: ask-identity-prose, disposition: fixed}
```

Subject: `docs/superpowers/specs/2026-11-24-dashboard-retire-design.md` at `8ccc6068` (reviewed, the Phase 6 fold);
fold at the commit after `45286f4e`.

- Codex half: `docs/reviews/codex/dashboard-retire-spec-r6-codex.md` (model `gpt-6.1-terra`) — 1 BLOCKER, 1 MINOR. NOT CONVERGED.
- Claude half: `docs/reviews/claude/dashboard-retire-spec-r6-claude.md` — 1 BLOCKER, 1 MAJOR, 3 MINOR. NOT CONVERGED.

## ROUND CAP

`docs/review-method.md` §0 Q4c: from round 4 only a BLOCKER changes the spec's mechanism. Both BLOCKERs are folded;
the MAJOR and MINORs are FILED into a new spec section, §3 *Carried into the plan (round cap, r6)*, each with its
proposed fix, which the plan must address. The Codex MINOR is a wrong sentence, not mechanism, and is corrected.

`fix_induced: true` marks findings whose subject the Phase 6 fold introduced (the dropped rows, the ask-file reader,
`.gitkeep`, the `## Answer` rule, the identity prose). M1 is `false`: the cutover race existed in the pre-fold L1/K9 design too.

## Dispositions

| Finding | Disposition | What changed |
|---|---|---|
| Claude B1 — the Phase 6 fold deleted K7 and K8 | **fixed** | both rows restored verbatim from `f63709f3` after K6. K8's retired-path list only adjusted: `check-dashboard-entry.py` is "retired by S2's rename to `check-ask-store.py`", the `dashboard` skill "renamed `needs-you` in S2" (was "if renamed"). Neither row cites a deleted check. S2's "K4–K7", S3's "K8" and §4.3's "K8 inspects …" now resolve again |
| Codex BLOCKER — conflict markers after a valid first line close an ask | **fixed** | §2.3's PROBLEM list: a line beginning `<<<<<<<` or `>>>>>>>` ANYWHERE in the file, fenced or not. A1's row says so and gains the case Codex names: a valid `# ` first line plus two conflicting `## Answer` sides → PROBLEM, A1 red, goal tree NOT READ (K5). §8 records Codex's scratch measurement |
| Claude M1 — L1 cutover window | **filed** (carried) | §3 *Carried*: blob pin + `git cat-file` restore, master-store-unchanged check before S2 merges, merge master into open PRs after S2. §2.3b's race row points there |
| Claude m1 — `.gitkeep` / F1 scope | **filed** (carried) | F1 over name-rule files only; A1 requires `.gitkeep` empty |
| Claude m2 — exact `## Answer` | **filed** (carried) | `line.rstrip() == "## Answer"` at column 0, outside a fence; two cases |
| Claude m3 — A1 HEAD tree vs filesystem | **filed** (carried) | the plan picks working tree or `git ls-tree HEAD` and states it |
| Codex MINOR — git identical-add coalescing | **fixed** (wording) | §2.1's identity row and §3's K11 *Deleted* row: git cannot hold two distinct files at one path; differing additions conflict (`AA`), identical ones coalesce into one ask. "no duplicate can be merged" → "no two distinct asks can share a path" |

## Correction to the r4-phase6 record

`dashboard-retire-spec-r4-phase6-coordinator.md` says "Kept with a falsifier each: K4–K8 (… K7, K8 unchanged)". That
was the intent, and the spec at `8ccc6068` did not hold it: the two rows were missing. The record is left as written
(a coordinator document records its round); this section is the correction, and the spec now matches it.

## Kept-row audit — every gate id, `f63709f3` → this fold

| Section | At `f63709f3` | Now |
|---|---|---|
| §3 Kept | K9, K10 (withdrawn), K11, K1, K2, K3, K4, K5, K6, K7, K8 | A1, F1, L1, C1, K4, K5, K6, K7, K8 |
| §3 Deleted by Phase 6 | — | K1, K2, K3, K9, K10, K11, key grammar |

Every id absent from *Kept* is in *Deleted* with its reason; no other kept row was dropped (`git diff f63709f3` on the spec, ids listed by `grep '^| [KAFLC][0-9]'`).

## Spec sections changed

Status line; §2.1 identity row; §2.3 PROBLEM list; §2.3b race row (pointer); §3 Kept (K7, K8 restored; A1's text
and cases); §3 *Deleted* (K11 and key-grammar rows' wording); §3 *Carried into the plan (round cap, r6)* (new); §8
one row.
