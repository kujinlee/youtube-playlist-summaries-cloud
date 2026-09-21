# pin-python-interpreter — round 3 — Codex half

Subject: PR #317, HEAD `cfefc377` (the merge of master + the `_steps()` redesign). Run via `scripts/codex-review.py` (`gpt-5.5`); `docs/reviews/verdicts/pin-r3-codex.verdict.json` records `gate_ran=true`.

⚠ **It reviewed `cfefc377`, and the tree moved under it** — it says so itself, which is the right behaviour: *"the worktree changed while I was reviewing… the findings above are explicitly against requested HEAD `cfefc377`."*

<!-- codex-review: model=gpt-5.5 -->

**High / Phase 6 Trigger** — `cfefc377:scripts/check-python-pin.py:127` and `:166`: `_steps()` treats block-scalar content as workflow structure. A job with no real `actions/setup-python` step can pass if its `run: |` body contains a fake step-shaped snippet:

```yaml
jobs:
  verify:
    steps:
      - name: write fake workflow
        run: |
          - uses: actions/setup-python@v5
            with:
              python-version: '9.9'
```

Measured against `cfefc377`: `declared_pins(...) -> ['9.9']`, `unpinned_jobs(...) -> []`, and `verdict(...) -> rc 0 / python pin OK`. This is the widened-net false-green family the prompt called out, and it is a fourth `declared_pins` finding. By the coordinator’s pre-committed falsifier, the redesign did not dissolve the class; Phase 6 fires.

**Medium** — [scripts/mutations/check-python-pin.json](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/mutations/check-python-pin.json:124): one manifest entry still targets the deleted pre-redesign opener-match code:

```text
m = re.match(r"^(\s*)-\s+uses:\s*actions/setup-python", line)
```

I derived this directly: `scripts/mutations/check-python-pin.json` has 27 entries, but entry 12’s old text is absent from `cfefc377:scripts/check-python-pin.py`. So the mutation claim is stale: this entry was not retargeted to the new `any(... step.body ...)` predicate, and a targeted anchor check reports it missing.

Verified:
`check-python-pin.py --self-test` passed `62/62`; `check-plan-code.py --self-test` passed `128/128`; `EXPECTED_MUTATIONS` has 52 entries summing to `856`; there are 52 manifest files summing to `856`; dashboard dates are nondecreasing and the count deletion is reasonable because the gate-owned sources are named.

Not run:
I did not run full `python3 scripts/check-plan-code.py --mutate .` because the prompt says it takes about 50 minutes. I ran targeted derivations instead. Also note the worktree changed while I was reviewing (`scripts/check-python-pin.py` modified and an untracked Claude r3 review appeared), so the findings above are explicitly against requested HEAD `cfefc377`.

---

## Coordinator disposition

### High / Phase 6 trigger — CONFIRMED, INDEPENDENTLY, AND THE FIRST FIX WAS AT THE WRONG LAYER

Two parties found the same fourth `declared_pins` defect within the hour, with **different fixtures**: the coordinator probing its own redesign (a bare `uses:` line inside a heredoc), and Codex here (a **dash line** inside a heredoc). Both are the widened-net false-green family.

⛔ **And the difference between the two fixtures is the whole finding.** The coordinator's first repair (`dc4efd1b`) applied `_structural()` to each step's body **after** `_steps()` had split. That closed its own fixture and left Codex's wide open: a dash line inside a block scalar is consumed by the SPLITTER, which manufactures a phantom step owning the fake `with:` beneath it. Measured against `dc4efd1b`: `declared_pins -> ['9.9']` — still a false green for a job with no `setup-python` at all.

**The mask now lives in `_steps()`.** *Which lines are structure* is logically prior to *which step owns a line*; filtering after the split asks the second question before the first. That is the same ordering error as the previous four, in a new costume — every one of them asked *where do I look?* before *what am I looking at?*

Codex's exact fixture is pinned as two cases (the pin, and the job reading as UNPINNED, which is the consequence that matters), plus a mutation that removes the mask from the splitter and dies via the case naming it.

### Medium — CONFIRMED AND FIXED. A stale manifest anchor the coordinator did not check for.

Entry 11 still targeted the pre-redesign opener-match, deleted by `cfefc377`. The coordinator ran an all-manifest orphan audit **before** the redesign and only a distinctness check after it — so an anchor orphaned BY the redesign was structurally invisible. Re-anchored to widen the action pattern instead. ⚠ Re-anchoring it collided with a newer entry, and a second pass caught that: **29 entries, 29 distinct anchor sets, 0 orphaned, 0 ambiguous**, verified under the gate's own expression.

### Verified by Codex and re-derived here

`EXPECTED_MUTATIONS` 52 entries summing to the declared value; 52 manifest files agreeing; dashboard dates non-decreasing; the count deletion sound because the gate-owned sources are named. Current tree: **68 cases, 29 pin mutations, derived sum 858 == declared 858**.

⚠ **Codex did NOT run `check-plan-code.py --mutate .` in full** — targeted derivations only, and it says so. The coordinator's full run is the authority and is in flight.

REVIEW GAP: claude — round 3's Claude half was dispatched concurrently and had not returned when this half was filed; it is being written to `docs/reviews/claude/pin-python-interpreter-r3-claude.md` and will be committed when complete. This is a timing note, not an absent half.
