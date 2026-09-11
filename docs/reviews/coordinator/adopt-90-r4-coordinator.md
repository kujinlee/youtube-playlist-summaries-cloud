<!-- codex-review: model=gpt-5.5 -->

Blocking: [scripts/gen-backlog-page.py](/tmp/rev90e/scripts/gen-backlog-page.py:2809) — the requested isolated regression command does not reach `164/164`. In the exact `/tmp/rev90e` tree copied from `{scripts,docs}`, `python3 scripts/gen-backlog-page.py --self-test` fails `160/164`, because four hook-filter tests read missing `.claude/hooks/regen-backlog-page.sh`. Observation: exact isolate command, then `python3 scripts/gen-backlog-page.py --self-test` ⇒ `FileNotFoundError`, `rc=1`.

Proof of subject: [scripts/check-group-claims.py](/tmp/rev90e/scripts/check-group-claims.py:48): “It makes rewording the index a TWO-FILE EDIT. It does not prevent rewording: change both copies together and this guard exits 0 — measured, and by design.”

A. Claim check: true as stated. Generator-only `INDEX_DEK` reword ⇒ `check-group-claims.py` fails `rc=1`. Guard-only reword ⇒ fails `rc=1`. Both copies reworded together ⇒ passes `rc=0`. I found no asymmetric path that stays green, and confirmed the coordinated reword is not prevented.

B. Consistency: no fourth stale live claim found in `scripts/`, row #90, dashboard entry, or current review notes. Older broad wording appears only as historical/refuted review text or explicit correction history.

C. Hedging: not too far. The docs still state the useful guard: asymmetric change fails CI / the governed field cannot change as a one-line silent edit. They also correctly say the guard does not police all prose.

Regressions run: `check-group-claims.py --self-test` `30/30 rc=0`; `check-group-claims.py` `rc=0`; `gen-backlog-page.py --self-test` `160/164 rc=1`, not the requested `164/164`.

VERDICT: NOT CONVERGED

---

## Round 4 remediation, recorded by the coordinator

⚠ **THE FIRST ATTEMPT AT THIS ROUND TIMED OUT.** The wrapper refused to write a review rather than
writing an empty one (`gate_ran: false`, reason *"timed out"*) — the fail-loud behaviour
`docs/plugins.md` describes, working. One narrowed re-run was the sanctioned single retry; the
first prompt had asked for the whole branch on top of the convergence questions.

### The Blocking is MY BRIEFING, not the code — and that is the third time

`gen-backlog-page.py --self-test` reaches **164/164 in the repo** and **160/164 in the tree the
reviewer was told to build**, because my isolate command said `cp -R {scripts,docs}` and four cases
read `.claude/hooks/regen-backlog-page.sh`.

⛔ **I HAD ALREADY RECORDED THIS TWICE.** r2 needed `node_modules/typescript`; r3 needed `.agents`
and `supabase`; both are written into this branch's own commit messages as *"a reviewer handed only
the tracked tree gets a RED control"*. I then wrote a NARROWER isolate command for the retry —
dropping `.claude` — while trying to make the round cheaper. Knowing a hazard and writing it down
did not stop me walking into it a third time.

### But there IS a real defect underneath, and it is why the reviewer was misled

`_hook_awk` called `.read_text()` on the hook with no guard, so a tree without `.claude` raised
`FileNotFoundError` and **killed the whole suite**. A suite that dies reports nothing, so what the
reviewer saw was indistinguishable from a code failure — and it read it as Blocking, reasonably.

Two of this repo's own rules were being broken at once: *"cannot run is a FAILURE, never a pass"*
wants a NAMED failure, and *"a case that dies from its defect is weaker than one that reports it"*
wants the run to survive.

**FIXED, and verified by running the reviewer's exact command:**

    before  FileNotFoundError, traceback, nothing attributable
    after   162/165, first named failure: "the hook this suite reads is present —
            a missing one is CANNOT RUN, not a pass", and `_hook_awk` returns a
            sentence saying to stage scripts, docs AND .claude

Cases 164 → 165. The population is now asserted before it is read.

### Everything the round was actually asked to check came back clean

- **A — is the two-file-edit claim true?** *"true as stated… I found no asymmetric path that stays
  green, and confirmed the coordinated reword is not prevented."* Generator-only reword → rc=1;
  guard-only reword → rc=1; both together → rc=0.
- **B — is it stated consistently everywhere?** *"no fourth stale live claim found."* ⚠ There HAD
  been one — row #90 said *"cannot be **changed** silently"* while my sweep grepped for *"cannot
  change silently"*. I found and fixed it while this round was running. **A literal grep finds the
  phrasings you remember.**
- **C — has the hedging gone too far?** *"not too far."*

⭐ **SO THE SUBSTANTIVE REVIEW CONVERGED.** The verdict line reads NOT CONVERGED on the strength of
a red control I caused. Rounds 2, 3 and 4 changed **no code between them** except this one
robustness fix; `review-method.md`'s guidance is that prose rounds can be right forever and that
this is a signal to ship rather than to convene Phase 6. This is where the rounds stop.

REVIEW GAP: claude — not invoked. Only the adversarial half ran, in all four rounds.
