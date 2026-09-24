# Round 5 — `velocity-177` — coordinator

```yaml
round: 5
fixes_nontrivial: true
subject: velocity-177
halves:
  claude: ran
  codex: "GAP: alternation — Codex took r4, so r5 is the Claude half"
findings:
  - {id: B1, severity: Blocking, aim: instrument, fix_induced: true, component: review-gap-grammar, disposition: fixed}
  - {id: H1, severity: High, aim: deliverable, fix_induced: true, component: invariant-scope, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: number-populations, disposition: fixed}
  - {id: M2, severity: Medium, aim: deliverable, fix_induced: true, component: invariant-scope, disposition: fixed}
```

REVIEW GAP: codex — alternation, per `review-method.md` -> Round topology step 4: Codex took r4, so r5 is the Claude half. Not a failure to run.

## ⭐ THE THRASHING IS BROKEN. The shape invariant holds; there is no link four.

r5 swept the section for every digit, number-word and positional token — **35 lines flagged, all
read** — and reports that inside the numbered rule bodies the count of surviving live repository
assertions in the invariant's enumerated forms is **zero**. The fix that differed in KIND from the
four patterns before it **worked**, and this is the first round to test it.

⚠ **It did not converge, and the reason is not prose.** r5 explicitly declined de-escalation and
said why: B1 is a red required CI gate, H1 a contradiction between two sentences of one rule, M1 a
measured rot. None is a wording preference.

## B1 (Blocking) — a required CI gate was RED on the merge tree, and had been for four rounds

`scripts/check-review-rounds.py` exits **1** on this branch, and `.github/workflows/ci.yml` runs it
unconditionally in the required `verify` job. **Reproduced:** `gh pr checks 345` showed
`verify fail 1m33s` while `schema-gates` passed.

⛔ **TWO GRAMMARS FOR ONE CONCERN.** `docs/round-header-template.md` sanctions recording a gap in the
YAML header — *"`halves.<name>`: `ran`, or a string starting `GAP:`"* — and every coordinator
document on this branch did exactly that. The gate's grammar requires a **line-initial**
`REVIEW GAP: <half> — <reason>`. Following the template put the branch in violation of the gate.

⚠ **AND THE COORDINATOR DID NOT CATCH IT, TWICE OVER.** `check-review-rounds.py` was run at r1 and
returned rc=0 — before any coordinator document with a gap existed. It was never re-run as the
rounds accumulated, and the CI result was reported to the user as green from an earlier commit. **A
green is a claim about the tree it ran on**, which is this repo's most-recorded lesson and was not
applied to its own branch.

Fixed mechanically: the prose form added to rounds 2, 3, 4 and this one. ⚠ **The template/gate
divergence is a repo defect, not a branch defect**, and is proposed as its own backlog row — one
mechanism per concern, and here there are two.

## H1 (High) — the invariant's scope was undecidable, and the two readings contradicted

Its heading said *"the shape **these rules** keep"*; its body said *"**a governing rule's** body"*.
Measured by r5: the wide reading condemns `docs/review-method.md`, which carries many bare `:NNN`
locators inside governing rule bodies and, at *"must paste the relevant lines, with a `file:line`"*,
**mandates the forbidden form**. The narrow reading leaves the invariant no reach at all.

**Fixed by stating the scope outright — this section, its preamble and its five rule bodies — and by
recording that widening it is a real question requiring an audit of what it would condemn.** That
audit is backlog #181's work. Claiming repo-wide reach without it would be this section's own defect.

## M1 (Medium) — the one expression that had already rotted, re-pinned by the fix for it

The preamble said *"They are numbered 1, 1b, 2, 3, 4 — **five of them**"*: a count of this section's
own contents, sitting **before** the first rule and therefore outside the invariant under either
reading. Its predecessor *"all four"* went stale when 1b was added and was caught at r3 — **and the
r4 fold's repair was to re-pin the count rather than remove it.**

Now a list, not a count: *"numbered 1, 1b, 2, 3 and 4"*. **A list cannot disagree with its own
contents.** The invariant's scope was extended to the preamble in the same fix, because that is
where the only measured rot occurred.

## M2 (Medium) — the general clause over-reached its own enumeration

*"Makes no claim about the repository's contents"*, read as the test, forbids three expressions
these rules need — all verified true by r5: rule 4's verbatim quotation of `check-merge-ready.py`'s
`WORKFLOW` comment, its observation that `ci.yml` mentions `check-schema-gates.sh` only inside
comments, and rule 3's cross-reference to `review-method.md` §0 Q2 step 5.

**Fixed by inverting which sentence governs: the three-form ENUMERATION is the test, and the general
sentence is its reason.** A criterion that condemns the repo's own standing rule about quoting code
is the wrong criterion.

## ⚠ Out of scope, reported anyway — and it is evidence for #179

`docs/dev-process.md` says **thirteen** schema gates in one row and **fifteen** in another.
Pre-existing on master, untouched here. ⭐ It is a live instance of the principle this branch spent
five rounds rediscovering, in the spine document itself — and **backlog #180's pointer would not
reach it**, because nobody writing that row was reading the numbers section. Only an ADR (**#179**)
is read by the process that would.
