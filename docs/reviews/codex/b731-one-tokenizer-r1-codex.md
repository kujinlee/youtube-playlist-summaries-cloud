<!-- codex-review: model=gpt-6.1-terra -->

1. **MEDIUM — ADRs with invalid anchors no longer fail the status gate.** [check-goal-status.py:325](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/b731-one-tokenizer/scripts/check-goal-status.py:325) now builds `named` only from living specs and plans: `for d in docs: ... named.setdefault(d["anchor"], []).append(d["rel"])`. Master also included ADR headers through `ca.anchored_slugs(root)`. In a temporary tree with current nodes `alpha`, `beta`, `dev-speed`, and `harness-ships-elsewhere`, a valid shipped spec anchored to `alpha`, and this ADR header:

   ```text
   # ADR
   > **Anchor:** `nonexistent` — **ADR:** none
   ```

   Master exited **1** with “a document names no current node”; the branch exited **0**. This is a real loosening of `check-goal-status`’s misnamed-slug check. The separate anchor gate may still reject the ADR, but that does not preserve this gate’s former behavior.

2. **MEDIUM — Prose mentioning an armed anchor makes an exempt document fail.** [check-goal-status.py:260](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/b731-one-tokenizer/scripts/check-goal-status.py:260) enforces `next((c for c in d["claims"] if c in armed), None)` for every claim, including examples in prose. With the same temporary node tree and this spec:

   ```text
   # X
   Example: **Anchor:** `alpha`
   > **Anchor:** `dev-speed` — **ADR:** none
   ```

   Master exited **0**; the branch exited **1**, demanding a status because `alpha` is armed. The real header names exempt `dev-speed`. This follows the proposed “any claim” rule, but refutes the design review’s claim that the redesign does not newly refuse the prose-example case.

The property oracle is independent: [check-goal-status.py:491](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/b731-one-tokenizer/scripts/check-goal-status.py:491) compiles a separate literal and uses its own 18-line window. Its identity assertion can fail if the tokenizer’s pattern or window changes independently. It checks equality of those two constants, however, not equivalence of the complete readers: the oracle uses `splitlines()`, while the tokenizer uses `split("\n")`.

The removal of ADRs from the **armed set** has no demonstrated status-enforcement loosening: any spec or plan claiming a current non-exempt slug itself adds that slug to the branch’s armed set. The demonstrated ADR loosening is the separate misnamed-slug failure above. A two-claim probe with bare `alpha` followed by a well-formed `dev-speed` header and no status exited **0 on master and 1 on the branch**; it did not expose a master-refusal/branch-pass regression.

All requested self-tests ran and passed:

- `check-anchors.py`: **27/27**, exit 0
- `check-goal-status.py`: **45/45**, exit 0
- `check-features.py`: **101/101**, exit 0
- `gen-goals-page.py`: **85/85**, exit 0
- `gen-features-page.py`: **54/54**, exit 0

## Loosening answers
LOOSENING-CHECK 01153378395f: not a loosening
LOOSENING-CHECK 6f2ded099e1e: not a loosening
LOOSENING-CHECK 02952a74b7d3: not a loosening
LOOSENING-CHECK d70bc5d51f9c: not a loosening
LOOSENING-CHECK f37e4a4ee06c: not a loosening
LOOSENING-CHECK a5c621529bbb: not a loosening
LOOSENING-CHECK 8f367ef6ac65: not a loosening
LOOSENING-CHECK 3abaeafd1122: not a loosening
LOOSENING-CHECK c0a5723843c4: finding: an ADR with a well-formed nonexistent anchor passes the status gate
LOOSENING-CHECK dd509572087b: finding: an ADR with a well-formed nonexistent anchor passes the misnamed-slug check
LOOSENING-CHECK e8b77d8d5661: not a loosening
LOOSENING-CHECK 5c9687cdbaf0: not a loosening
LOOSENING-CHECK 17f22b33bac5: not a loosening
VERDICT: HOLD
