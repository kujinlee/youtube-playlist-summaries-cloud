# closing-table — round 4, Claude half

**REVIEW GAP: the independent Claude half could not be dispatched (fourth round running).** Same
constraint throughout: this session cannot spawn subagents. Coordinator self-review only.

## r4's verdict: NOT CONVERGED — and it falsified the property the redesign rests on

| # | Grade | Finding | Status |
|---|---|---|---|
| r4-H1 | High | **`tool_outputs_of` read the WHOLE WINDOW**, so a failed `git push` in one call cancelled a successful `git push` in a later call. The veto INTRODUCED a miss | fixed — the veto is evaluated per call against **its own paired result** |
| r4-M1 | Medium | arbitrary stdout could impersonate veto evidence: any command printing `Everything up-to-date` cancelled a real push | fixed by the same change — evidence must come from the act's own invocation |
| r4-M2 | Medium | `mask_heredocs` tracked ONE terminator and matched with `strip()`; two heredocs in one command, and a space-indented terminator, both leaked `git push` as an act | fixed — a QUEUE of terminators, POSIX-strict matching (`<<-` strips TABS only) |
| r4-G1 | gap | the new mutations covered "veto disabled" and "wrong act label" but not paired scoping, multiple heredocs, or whitespace terminators | fixed — three new mutations, one per repro |

## ⭐ r4-H1 is the most valuable finding of the whole branch, because it refuted a claim I wrote down

The veto design rests on one property, stated in a comment and in the commit message:

> a veto can never introduce a MISS, because no output means no veto

**That is false as I implemented it**, and r4 produced the counter-example in two lines:

    git push   -> error: failed to push some refs     (rejected, then rebased)
    git push   -> To github.com ...                   (succeeds)

Whole-window scoping let the first call's failure cancel the second call's real push. The property
is true of a *paired* veto and false of a *window* veto — and I chose window scoping deliberately,
writing a comment justifying it ("a turn that pushes in one call and reports the failure in the next
should still be vetoed"). The justification was the bug.

**The lesson is not "scope it to the pair".** It is that I stated a safety property as a comment and
did not write a case that could falsify it. Every one of the veto's cases tested that it removes the
right things; none tested that it removes only those. There is now a case and a mutation for exactly
that direction.

## On the heredoc bound, which I overclaimed one round ago

r3's fix made me write *"the heredoc half of this bound is CLOSED"*. r4 found two leaks. The bound
now reads NARROWED, with the specific things it still does not understand named (`$(...)`,
backslash-continued `<<`, a delimiter built by expansion). A bound that has quietly become false is
worse than one never claimed.

## Verification

| check | result |
|---|---|
| Self-test | ✅ **116/116** |
| Mutations kill via the case each NAMES | ✅ **32/32** — 0 survivors, 0 unattributable, 0 orphaned |
| r4-H1 repro (failed push then successful push) | ✅ `['a push']` — was `[]` |
| r4-M1 repro (unrelated `Everything up-to-date`) | ✅ `['a push']` — was `[]` |
| r4-M2 repro (two heredocs; indented terminator) | ✅ `[]` both — was `['a push']` |
| `<<-` still strips TABS (the fix must not over-correct) | ✅ `['a push']` |
| **Corpus, 229 real Bash calls** | ✅ fires 11, **false positives 0, MISSES 0** |
| CI `--mutate .` on the previous head | ✅ Codex independently ran it: `811 mutations, 811 killed, 0 survivors` |
| `check-fixture-variation` / `check-selftest-counts` / `check-ratchet-contract` / `check-docs` | ✅ all rc=0 |
| An independent Claude reviewer ran | ❌ **NO** — see REVIEW GAP |

⚠ **One correction to my own numbers:** I reported the corpus as 211 Bash calls; Codex counted 219,
and it is now 229. All three are right about different moments — the transcript grows while the
session runs, which is the *a document inside the corpus it measures* shape. The ratios, not the
absolute count, are what the comparison rested on.
