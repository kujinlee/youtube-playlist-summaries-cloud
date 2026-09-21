# pin-python-interpreter — round 4 — Codex half (scoped to the r3-fix delta)

Subject: `git diff cfefc377..5206e020 -- scripts/` — the repairs for round 3's six findings. Run via `scripts/codex-review.py` (`gpt-5.5`); `docs/reviews/verdicts/pin-r4-codex.verdict.json` records `gate_ran=true`.

⚠ **Claude half absent BY PROTOCOL, not by failure** — `docs/review-method.md` step 4: rounds 2+ go to the half that did NOT author the fix. The Claude half found F3/F4/F5 *and proposed their repairs*. See the REVIEW GAP line.

<!-- codex-review: model=gpt-5.5 -->

**Findings**

**High: `_steps` still accepts non-`steps:` lists as workflow steps, so a matrix entry can falsely pin an unpinned job.**  
At [scripts/check-python-pin.py:173](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-python-pin.py:173), `_steps` scans every structural dash in the whole job block. It does not first enter a `steps:` sequence, so a valid `strategy.matrix.include` item can be parsed as a step:

```yaml
jobs:
  verify:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        include:
          - uses: actions/setup-python@v5
            with:
              python-version: '9.9'
    steps:
      - run: python3 --version
```

Measured at HEAD: `declared_pins` returns `['9.9']`, `unpinned_jobs` returns `[]`, and `verdict(..., running='9.9')` returns rc `0` with `python pin OK`, even though the job has no setup-python step. I also checked `cfefc377`; this shape already failed there too, so it is not newly introduced by the latest commit. But it directly falsifies the rewritten splitter’s repaired contract: the new sibling/dedent rule still partitions “all YAML list items that look step-like,” not actual workflow steps. I searched the requested sibling shapes: nested lists before `uses:`, a list as the first key, and a list inside `with:` all stayed correctly attached to the current step; the remaining wrong level I found is `strategy.matrix.include`.

**Medium: the new mutation manifest entry is not attributable to its declared case.**  
The entry at [scripts/mutations/check-python-pin.json:300](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/mutations/check-python-pin.json:300) says removing the splitter-level structural mask should be caught by `"a DASH LINE inside a block scalar does not manufacture a step"`. Targeted `run_mutations` shows that exact `expect` matches zero red cases:

```text
ok False mutations 1 survivors 0
expect 'a DASH LINE inside a block scalar does not manufacture a step' matched 0 red case(s)
caught by: setup-python INSIDE a run-block heredoc..., folded scalar, chomping indicator,
a named step whose heredoc CONTAINS..., a COMMENT at the dash indent...
```

The reason is subtle but important: after the sibling-indent rewrite, the dash-in-block-scalar fixture at [scripts/check-python-pin.py:630](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-python-pin.py:630) no longer fails when `_structural` is bypassed; the deeper dash is treated as body, not as a phantom step. The strengthened heredoc fixture does redden, so the behavior is covered, but the manifest’s named anchor is now stale and `--mutate` treats that as not measured.

**Checks Run**

`python3 scripts/check-python-pin.py --self-test`: `72/72 passed`  
`python3 scripts/check-plan-code.py --self-test`: `128/128 passed`  
Targeted `check-python-pin` mutations via `check-plan-code.run_mutations`: `32` mutations, `0` survivors, but `ok False` due the attribution issue above. I did not run full `python3 scripts/check-plan-code.py --mutate .` because the prompt called out the ~50 minute cost.

I confirmed the declared mutation sum is `861`, `check-python-pin.py` declares `32`, the manifest has `32` entries, and every edit anchor appears exactly once. Real workflows read as requested: `ci.yml` has one pin, `schema-gates.yml` has two, and both have no unpinned jobs reported.

---

## Coordinator disposition

### High — CONFIRMED and FIXED. The SEVENTH defect, and it was never about the rewrite.

Reproduced exactly: `declared_pins -> ['9.9']`, `unpinned_jobs -> []` for a job whose only real step is `run: python3 --version`. A **false green** — the direction this guard must never fail in.

⭐ **Codex is right that it predates the sibling rewrite, and that is the important half of the finding.** My own r4-prep probe tested `strategy.matrix` and passed it — because my fixture's matrix held `py: ['3.11','3.12']`, a list of SCALARS. Codex's holds `include:`, a list of **mappings**, which is what a step looks like. The defect was never about nesting depth; it was that `_steps` did not know which LIST it was in.

`_steps` now enters a `steps:` sequence before yielding anything. ⚠ **That change red-ed 12 existing cases**, and the fixtures were at fault, not the rule: they were bare step fragments with no `steps:` key, which is not what `declared_pins` ever receives. **All 22 fragment fixtures are now wrapped in a real `steps:` sequence** — r3 F5's lesson applied to the whole suite rather than to the one case that failed.

### Medium — CONFIRMED and FIXED. It would have red-ed CI as NOT MEASURED.

Verified independently: the `expect` matched **0** red cases, so `--mutate` scores the entry unmeasured and the whole run `ok False`. Cause is exactly as Codex diagnosed — after the sibling rewrite, a dash inside a block scalar is treated as *body*, so the dashed fixture no longer discriminates when the mask is bypassed. Re-pointed to the strengthened heredoc case, which does.

⚠ **AND MY REPLACEMENT MUTATION FOR THE HIGH FAILED ATTRIBUTION FIRST**, caught by running the check rather than assuming: `opens_steps = None` made EVERY case return `[]`, so the matrix case — which asserts `[]` — still passed. A mutation must reproduce the OLD BEHAVIOUR, not destroy the function. Re-targeted to `steps_indent = -1` (every list is a steps list), which is precisely the pre-fix state.

### Verified after

**75 cases, 33 mutations, every one killing AND attributing to the case it names over a green control** (`scratchpad/attrib.py`, the same check `--mutate` performs). Derived sum 862 == declared. Real workflows unchanged: `ci.yml` one pin, `schema-gates.yml` two.

### ⛔ SEVEN DEFECTS, ONE ROOT CAUSE — and this round is why the ordering question goes back to the human

Each repair has taught this function one more thing that SHAPE alone cannot tell it: where a step ends, which lines are content, which dashes are siblings, which are comments, and now which list it is in. Backlog **#153** (the architecture review) is filed and asks whether this should parse or refuse rather than keep learning YAML one defect at a time. The coordinator pre-committed to re-raising the ORDER — finish #317 first, or do #153 first — if a seventh arrived. It has.

⚠ Codex did NOT run `--mutate .` in full; targeted runs only, and it says so.

REVIEW GAP: claude — not run for round 4, by protocol. `review-method.md` step 4 sends an alternating round to the half that did not author the fix; the Claude half authored these repairs' findings in round 3. It reviewed this component in rounds 1, 2 and 3.
