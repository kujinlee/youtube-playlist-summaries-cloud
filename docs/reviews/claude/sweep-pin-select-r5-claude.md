Reviewed head: 74492404ab420cf889d5d609cc0e51da8e5970cc

# sweep-pin-select — review round 5, Claude half (adversarial)

PR #526, backlog #533 and backlog #536. Mandate: refute.

## Scope

`git diff origin/master...HEAD` at the reviewed head, with two focus areas:

1. The master merge in e1007ef5 (origin/master 1a053fd1, PR #523, merged into 87ed49c0): pins, the
   `check-plan-code.json` union, every anchor, and `check-plan-code.py`'s merged logic.
2. The survivor fixes b8480871 and 74492404 (`check-merge-ready.py` self-test only), and whether any other
   case in that self-test can be answered by the held-versus-displayed clause instead of its own.

## What I ran, and the results

| Check | Result |
|---|---|
| `python3 scripts/check-merge-ready.py --self-test` | 263/263 |
| `python3 scripts/check-plan-code.py --self-test` | 373/373 (matches the docstring's `# 373 cases`) |
| `python3 scripts/check-selftest-counts.py --self-test` | 60/60 |
| The harness's OWN rules, imported from `check-plan-code.py`: `load_manifests`, `anchor_problems` (sequential, exactly-once), `manifest_counts`, `pin_drift`, `own_pin_problems` | 3,849 mutations, 3,873 edits, **0 anchor problems**, **0 pin drift**, 0 own-pin problems, 88 pins, `declared_total` 3,849 = the manifests' sum |
| Pins at HEAD against merge base 319bd152, branch 87ed49c0 and merged master 1a053fd1 | check-plan-code 178 / 182 / 224 → **228** (= 178 + 4 + 46); check-merge-ready 97 / 102 / 97 → **102**; check-selftest-counts 36 / 36 / 34 → **34** (master's own documented lowering in PR #523, "36 -> 34", carried); no key dropped; every other pin equal on all sides |
| Per-entry 3-way of `check-plan-code.json` and `check-merge-ready.json` (base 319bd152, ours 87ed49c0, theirs 1a053fd1, result HEAD) | 0 missing, 0 extra, 0 duplicate entries, 0 duplicate names, on both manifests |
| `check-plan-code.py`: each side's `-U0` change compared with the merge result's | Master's 662 changed lines appear verbatim except the two pin lines, which moved to `expected_mutations.py` with their history comments; the branch's change appears verbatim except the self-test count line (323 -> 373) and the two pins. The seed logic (`parse_seeds`, `seed_outcome`, `seed_trees`, NONDETERMINISTIC reporting) and the branch's pins-file move are both present |
| Replayed manifest mutations 85, 86, 92, 93 in a git copy of HEAD (`git archive HEAD`) | each reds its named case: 86 → `[True, False, True]`; 92 and 93 → the bool case `(2, True, True, False)` (the held clause answers CANNOT RUN, and the new `TypeError: pin_display` term is what reds it); 85 → 16 cases red, including its named one |
| `check-plan-code.py --mutate . --only scripts/check-merge-ready.py --allow-long-local` | see *Sweep* at the end |

## Findings

### R5-F1 — High — fix_induced: yes (backlog #536) — component: merge-ready-pins

**`pin_pair`'s held-versus-displayed comparison reads the WORKING TREE, not HEAD, and a dirty working tree
makes a redirected, pin-lowering head READY.** The comment at `scripts/check-merge-ready.py:1077-1079` says
"the working tree is the PR head: `main()` refuses any other HEAD". `main()` refuses a different `HEAD`
commit (`scripts/check-merge-ready.py:412`), but nothing checks the working tree is clean: no `git status`
anywhere in the script. `held_pins` imports `PINS_READER`, the working-tree `check-plan-code.py`, which reads
the working-tree pins file. The display is read from `git show HEAD:...`. So the comparison compares the
committed display against whatever is on disk.

Reproduced in a git copy of the reviewed head:

1. Commit a head whose `check-plan-code.py` has the R1 redirect (`PINS_FILE = 'scripts/mutations/pins_v2.py'`
   above the `EXPECTED_MUTATIONS` line) and a `pins_v2.py` lowering `scripts/check-anchors.py` 5 -> 4.
   `expected_mutations.py` is untouched.
2. Control, clean tree: `pin_pair(run, "HEAD~1")` → `CANNOT RUN: HEAD: scripts/check-plan-code.py holds pins
   that differ from the display this script reads, for scripts/check-anchors.py (held 4, displayed 5)`.
3. `git checkout HEAD~1 -- scripts/check-plan-code.py` (uncommitted; HEAD unchanged):
   `pin_pair` answers, and `pin_falls` → `[]`.
4. The COMMITTED head harness, imported from a checkout of HEAD, holds `check-anchors.py` = **4**.

The committed head is what merges, and its harness enforces the lowered pin. Not Blocking: master has no
held comparison at all and would also be READY on the clean redirect, so this branch loses nothing master
had; it needs uncommitted changes in the PR's worktree, which the gate never checks. But it is the exact
route backlog #536 exists to close, and the comment states as true a precondition that nothing enforces.

**Fix:** either refuse CANNOT RUN when `git status --porcelain -- scripts/` is not empty, or (better) import
the reader for `held_pins` from a materialised HEAD tree (`git archive HEAD scripts/` into a temp dir), so
held and displayed are both HEAD's. Add a case that reproduces steps 1-3 and expects CANNOT RUN.

### R5-F2 — Medium — fix_induced: yes (backlog #536) — component: merge-ready-pins

**The same masking class the two survivor commits fixed is still present in three other cases: their
assertions are also answered by `held_pins`'s own refusal.** When HEAD's pins file is unreadable, the head
harness imported in the case's working tree holds `{}` (`read_pins` never raises), and `held_pins` refuses
it with `HEAD: scripts/check-plan-code.py's EXPECTED_MUTATIONS: ValueError: a present check-plan-code.py
with no pins is unreadable`. That text satisfies:

- `⛔ r1 (Claude S1, Codex X1): a DUPLICATE key that lowers a pin is CANNOT RUN, never a pass`
  (`scripts/check-merge-ready.py:2132`, asserts only the prefix `CANNOT RUN: HEAD:`);
- `⛔ a head with no single literal display is CANNOT RUN, never a pass` (`:2142`, three inputs, same prefix);
- `⭐ main() is CANNOT RUN, rc=2, when the head's pins cannot be read` (`:2407`, asserts only rc 2 and
  `mutation pins`).

Constructed mutation, not in the manifest: in `pin_pair`, a fail-open "an unreadable head is unchanged":

```python
    try:
        new = pins_at(run, "HEAD")
    except PinsUnreadable:
        new = dict(old)
```

Result in a git copy of HEAD: 262/263. All three cases above stay GREEN; the only red is
`⛔ backlog #533: a head that DELETES the pins file ...`, whose assertion names `{PINS_SCRIPT}:`. No current
manifest mutation survives because of this (mutation 85 returns `{}`, which skips the comparison), so it is
latent, and the property itself still holds end to end through the second clause. It matters for the same
reason b8480871 did: these cases cannot tell their own clause from the held clause, so a later change that
removes the display refusal on HEAD is attributed to nothing.

**Fix:** make each case require its OWN refusal's text, as b8480871 did: for `:2132` and `:2142`, the
display path (`HEAD: scripts/mutations/expected_mutations.py:`) and the reader's reason (`DUPLICATE key`,
`not exactly one`, `not a dict display`, `not an int literal`); for `:2407`, the same display-path term.
Add the mutation above to `check-merge-ready.json` with those cases as its `expect`, and bump the pin.

### R5-F3 — Low — fix_induced: yes (backlog #536) — component: merge-ready-pins

**`_exact_pins`'s refusal says `pin_display` even when it is reducing `EXPECTED_MUTATIONS` for
`held_pins`, so the new discriminator in 74492404 (`"TypeError: pin_display" in _o`) can be answered by the
held clause.** Reproduced: a copy of the real harness with `class _D(dict): pass` and
`EXPECTED_MUTATIONS = _D(EXPECTED_MUTATIONS)` appended to the module body → `held_pins()` raises `HEAD:
scripts/check-plan-code.py's EXPECTED_MUTATIONS: TypeError: pin_display did not return an exact dict`. No
current case or mutation is masked by this, because the seven reader-variant cases hold an exact
`EXPECTED_MUTATIONS`, so the 74492404 fix is sound today. But the text misnames its subject in operator
output, and the discriminator is weaker than it reads.

**Fix:** give `_exact_pins` a `what` parameter (`"pin_display"` / `"EXPECTED_MUTATIONS"`) used in its
messages, and have the reader-variant cases require `HEAD: scripts/mutations/expected_mutations.py` or
`base:` rather than the bare function name.

## On the two survivor commits (focus 2), directly

- b8480871 is sound and not over-fitted: each third now requires `` `git <cmd> `` and `exited 128`, which only
  that command's own refusal prints. The mutated copy reds `[True, False, True]` as the commit says. It couples
  to message wording, the accepted cost of attribution.
- 74492404 is sound for today's inputs (see R5-F3 for the bound). Mutations 92 and 93 now red the bool case.
- The `show` and `merge-base` returncode checks have no manifest mutation at all; the tightened case would
  attribute one correctly if added. Not a finding at the cap.

## Observations (not findings)

- **origin/master has moved past the merged master.** At review time origin/master is fca33440 (PR #525),
  which adds 16 `goal-tree.json` mutations and raises `goal-tree.py`'s pin 300 -> 316 in
  `check-plan-code.py`'s display. This branch moved the display to `expected_mutations.py`, so the next
  merge of master must carry 316 there. If it is missed, `pin_drift` reports it (300 pinned, 316 entries),
  so this fails loudly.

## Sweep

`python3 scripts/check-plan-code.py --mutate . --only scripts/check-merge-ready.py --allow-long-local`,
run in the sps worktree at the reviewed head (the harness stages its own copy). Its final line:

`OK — delivered scripts mutated: 1 file(s), 102 mutation(s), 102 killed, 102 attributed to the case each
names, 0 survivor(s) — measured over ONLY scripts/check-merge-ready.py — a DIAGNOSTIC slice, not the gate`

So the ls-tree survivor (mutation 86) and the two misattributed `_exact_pins` mutations (92, 93) are fixed.
R5-F2's constructed mutation is not in the manifest, so this sweep cannot see it.

## Verdict

CONVERGED (no Blocking findings). R5-F1 is High: it lets a pin-lowering redirect through as READY when the
PR worktree has uncommitted changes. It does not regress anything master had, so under the round cap it
is filed, not fixed now. The coordinator may judge it a BLOCKER under "a defect that would let a loosening
merge as READY".

VERDICT: CONVERGED
