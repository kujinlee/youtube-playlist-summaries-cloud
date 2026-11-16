# Round 1 — `canonical-file-entry` (PR #595, backlog #658) — coordinator — NOT CONVERGED (both halves)

```yaml
round: 1
fixes_nontrivial: true
subject: canonical-file-entry
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: true, component: prose, disposition: fixed}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: false, component: identity-case, disposition: fixed}
  - {id: C1, severity: Low, aim: deliverable, fix_induced: true, component: prose, disposition: fixed}
  - {id: C2, severity: Low, aim: deliverable, fix_induced: true, component: prose, disposition: fixed}
  - {id: C3, severity: Low, aim: deliverable, fix_induced: true, component: prose, disposition: fixed}
  - {id: C4, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

Both halves on `d3430eb1`. **Held:** self-test 33/33; all 15 manifest mutations killed by their named case (both halves
applied them independently); `./` and case spellings refused by both copies.

- **X1 = C1 (Codex MAJOR, Claude MINOR — taken as Medium):** the claim that `check-plan-code.py`'s `_staged_root` matches a
  file entry exactly is FALSE — its `startswith(r + "/")` arm runs for the file root, so `.claude/settings.json/foo` is
  staged there and refused here. Verified by reading `check-plan-code.py:624-628`. Harmless (nothing exists under a
  file; this copy is the stricter one), so fixed as WORDING in the code comment, the backlog row and the dashboard note
  — changing `_staged_root` would select the whole mutation manifest for no behaviour a real path can reach. Codex's
  `docs` / `docs/../X` differences are the two rules' different purposes (a lexical cite check vs a root lookup), not drift.
- **X2 (Codex MAJOR):** the identity case compared the UNION, so `supabase/` moved into `STAGEABLE_FILES` stayed equal
  while every migration became unstageable (33/33). **Fixed:** prefixes and files compared SEPARATELY, each against
  `HARNESS_TREE`'s entries classified by what is on disk; that move is now a mutation the case kills.
- **C2–C4 (NITs/INFO):** the pin comment's re-bound count (two, not one), the case name (now names both sets), and the
  prose list of what `HARNESS_TREE` stages (now includes `.githooks` and the file) — all fixed.

Mutations 15 → 16: the union mutation lost its anchor and became "the file entry dropped"; `supabase/` moved between the
sets is new; the #651 slash-on-a-file mutation is re-bound to the new `_ht_files` line. Sweep:
`OK — 16 mutation(s), 16 killed, 16 attributed to the case each names, 0 survivor(s)`.

Round 2 alternates: Codex's turn (it found X2).
