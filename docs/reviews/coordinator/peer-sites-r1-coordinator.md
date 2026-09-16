# Round 1 — `peer-sites` — coordinator

```yaml
round: 1
fixes_nontrivial: true
subject: peer-sites
halves:
  codex: ran
  claude: ran
findings:
  - {id: B1, severity: Blocking, aim: deliverable, fix_induced: false, component: containers, disposition: fixed}
  - {id: H1, severity: High, aim: deliverable, fix_induced: false, component: containers, disposition: filed}
  - {id: H2, severity: High, aim: deliverable, fix_induced: false, component: main-diff, disposition: fixed}
  - {id: H3, severity: High, aim: deliverable, fix_induced: false, component: branches-shape, disposition: filed}
  - {id: H4, severity: High, aim: instrument, fix_induced: false, component: fixture-exemptions, disposition: fixed}
  - {id: H5, severity: High, aim: instrument, fix_induced: false, component: peer-sites-manifest, disposition: fixed}
  - {id: P2, severity: High, aim: deliverable, fix_induced: false, component: activation, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: false, component: report, disposition: fixed}
  - {id: M2, severity: Medium, aim: deliverable, fix_induced: false, component: parse-hunks, disposition: fixed}
  - {id: M3, severity: Medium, aim: deliverable, fix_induced: false, component: main-diff, disposition: fixed}
  - {id: M4, severity: Medium, aim: deliverable, fix_induced: false, component: stated-bounds, disposition: fixed}
  - {id: L1, severity: Low, aim: deliverable, fix_induced: false, component: stated-bounds, disposition: fixed}
  - {id: L2, severity: Low, aim: deliverable, fix_induced: false, component: stated-bounds, disposition: fixed}
  - {id: L3, severity: Low, aim: deliverable, fix_induced: false, component: if-chain, disposition: fixed}
  - {id: L4, severity: Low, aim: deliverable, fix_induced: false, component: main-diff, disposition: fixed}
  - {id: L5, severity: Low, aim: instrument, fix_induced: false, component: peer-sites-manifest, disposition: fixed}
  - {id: C1, severity: High, aim: instrument, fix_induced: true, component: peer-sites-suite, disposition: fixed}
  - {id: C2, severity: Medium, aim: instrument, fix_induced: true, component: activation, disposition: fixed}
  - {id: P1, severity: High, aim: instrument, fix_induced: true, component: review-protocol, disposition: filed}
deliverable_findings: 12
stopping_rule: not_triggered
```

## The verdict, first

**NOT CONVERGED, and the branch is better for it.** Two independent halves ran. Codex found 4
findings; the Claude half found **14 plus 3 process findings**, and — the part that matters —
**refuted three of the design's central claims by replaying the tool over 200 master commits**
rather than by reasoning about it. 16 of 19 are fixed; 3 are filed with their measurements.

The branch ships a real mechanism. It does not ship the one that was claimed.

## What the replay refuted, and why the method is the finding

The docstring asserted three things. All three were assertions from the *design*, not from a run:

| claimed | measured over 138 python-touching commits |
|---|---|
| "no such thing as a false positive **by construction**" | one idiom — `if ok: … else: print("[FAIL]")` — produced **4 of the 12** `branches` containers, in four different guard files |
| "prints **2-4 lines**" | 96 of 138 commits print **nothing**; the tail runs to **32 lines**; 10 single containers print 9+ on their own |
| "catches **3 of 6** [of the replayed misses]" | a ceiling for a hand-picked sample. An edit inside an arm **body** is invisible — **79 silent vs 5 spoken** |

⭐ **The lesson is not that the numbers were wrong. It is that the branch's own headline virtue —
*the design came out of an experiment, not an intuition* — was applied to choosing the design and
then abandoned when describing it.** The experiment ran on six hand-picked misses; the claims were
written as if it had run on the corpus. The reviewer ran it on the corpus. Everything above came
back in one pass.

## H5 — the finding that indicts the mechanism with its own premise

The author found `len(rets) > 1 → > 0` was invisible through `report`, moved the claim to
`containers`, and shipped a manifest entry for it. **The identical expression appears twice more in
the same function, eight lines apart, and neither was ratcheted** — `len(node.handlers) > 1` and
`len(chain) > 1`, both of which survived the whole suite when widened to `> 0`.

Then the reviewer asked `peer-sites.py` about its own line 92, and it said **nothing**: three
sequential `if` statements are not one of its three shapes.

> The mechanism built to stop *fix the instance, miss the sibling* cannot see that failure in its
> own source, committed by its own author, in the commit that introduces it.

Six mutations survived the 32-case suite in total. All six are now closed — the manifest goes
**7 → 16 entries**, and every one was re-verified to go red **via the case it names**, over a
control proved green first.

## P2 — it had no caller, which makes the premise false as stated

`grep -rn peer-sites` returned the script, its manifest, three ratchet registrations and two prose
mentions. **No hook, no CI step, no skill.** The branch exists because *"having the rule did not
help, so this is the attempt at a mechanism"* — and a script a human must remember to run is that
same rule with an executable attached. It would have failed the same way.

Fixed: `.claude/hooks/peer-sites-advisory.sh` runs it before `git commit` — the machine-observable
instant the rule describes, while the fix is still in your hands. A reminder, never a gate,
modelled on `suggest-explainer.sh`. ⚠ Deliberately **not** PR-open time, where a sibling check
arrives after the moment it was for.

**C2 — and building that caller reproduced the class it guards against, twice, in fifteen minutes.**
Both were caught by *live-firing* the hook rather than reading it:

1. `timeout` is not on macOS. The hook exited 127 on every commit — the CANNOT-RUN branch reported
   it correctly, which is the design working, but loudly and forever.
2. Worse, and the reason this is recorded: the first version accepted `rc=1` as success for no
   reason. A bash error exited 1, the error text landed in `$out`, the `grep` found nothing, and
   **the hook exited silently** — a broken advisory indistinguishable from *"no siblings found"*,
   inside the very file whose header warns that nothing should read its silence that way.

## The three filed, with their measurements

| id | Why it is not being fixed here |
|---|---|
| **H1** (arm bodies) | **79 of 84** partially-touched containers are silent because a member is its HEAD. Making a member the whole arm tiles the statement, so every edit marks every member touched and the partially-touched filter can never fire. That is a redesign of what a member IS, and it needs the same replay treatment that produced this finding — not a wider span guessed at in a fix round |
| **H3** (systematic false positives) | narrowing the `branches` shape needs a *rule*, not a special case for one idiom. The reviewer's own sibling search found the `exits` shape — 61 of 73 containers — carries none of the noise, so the narrowing is cheap when someone designs it |
| **P1** (review protocol) | `review-method.md:54-55` forbids *committing* the first half's fixes before the second finishes. The fixes were **written into the working tree** instead, carrying `r1 BLOCKING` labels, and the second reviewer read them. The rule's falsifier should be the **tree**, not the commit. That is a change to the review method, not to this branch |

## P1 in practice, and the near-miss worth recording

The reviewer discovered the moving tree **itself** — `grep -n` returned line 473 of a file it had
read as 447 lines — and re-ran **every** measurement against `git show 52010914:scripts/peer-sites.py`
(md5 `e4d70ddbc9a1c55cf5a4c87f9905368b`, 447 lines, 32/32). Its findings therefore have one clean
subject. A reviewer that had not pinned the blob would have measured a mixture.

⚠ **And the coordinator nearly filed a `REVIEW GAP: claude` that was false.** The half was dispatched
in a previous session; a `/clear` intervened. The subagent transcript **in the old session
directory** stops at the moment of the clear and reads exactly like a dead agent. It was not dead —
it is an `in_process_teammate` that carried across, and its transcript **in the new session
directory** was still being appended. *The evidence checked first was a copy that had stopped being
written, not the agent.* The gap line was removed before it was committed, on the user's prompt —
not by any check.

## Why this does not converge

`fixes_nontrivial: true`, and not marginally: `containers()` changed its return shape, `parse_hunks`
became a body parser, `main --diff` gained a merge-base resolution and a non-zero CANNOT-RUN exit,
the dead `seen` dedupe was deleted, a hook was added, and the suite went **32 → 59** with the
manifest **7 → 16**. That is a large body of unreviewed code. **Round 2 is owed.**

`stopping_rule: not_triggered` — the two fix-induced findings (C1, C2) are in different components
and in one round, not two consecutive rounds in one component, so the architecture review is not
armed.

## What round 2 should attack

1. **The `else`-arm span**, which B1's fix left half-answered. `_if_chain` represents an `else` by
   `_span(cur.orelse[0])` — its first statement, whole — so on B1's own fixture the outer chain is
   `[3, 6-9]` and touching line 8 marks the outer `else` touched. Undecided, not decided, and it
   partially re-creates the tiling problem the docstring says it avoids.
2. **The new hook**, which is a PreToolUse hook on every `git commit` and has had exactly one
   author's attention. Its `_wants_check` rule is cased 9 ways; its live path is not in the manifest.
3. **The `main`-driving cases**, which are new machinery — a fake `subprocess.run`, a redirected
   `REPO`, a `SystemExit` catch. The `SystemExit` catch exists because driving `main` with the wrong
   argv form aborted the entire suite printing **nothing at all**, no tally and no `[FAIL]`.
4. **Whether `check-fixture-variation`'s new verdict on `main` is fully satisfied** — it refused a
   suite that passed `main` one constant argv, which is how the `--site` cases came to exist.
