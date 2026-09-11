<!-- codex-review: model=gpt-5.5 -->

High: [scripts/gen-backlog-page.py](/tmp/rev90c/scripts/gen-backlog-page.py:1407) still contains the old mechanism claim at the build site. Lines 1407-1413 say the index is not the bin because it has an empty falsifier and “cannot masquerade as a claim without failing the guard that polices claims.” That is still broader than the retraction. Observation that makes it fail: I changed both pinned `INDEX_DEK` copies to “Instruments and habits, cheap individually…” and `python3 scripts/check-group-claims.py` still exited 0: `group claims OK — 6 group(s)...`. The empty falsifier is not policed because the index is appended after `sanitise_groups(GROUPS, ...)` and is not in `GROUPS`; only rule 4’s two-copy agreement protects that field.

No Blocking findings.

Proof of subject: HEAD is `ea3c6554700e09b9b760cd883246fc4e0d6a9360`. `scripts/check-group-claims.py` declares `--self-test  # 30 cases`, and the suite has 30 `case(` calls. `scripts/mutations/check-group-claims.json` has 11 manifest entries.

Narrow claim itself: true as stated. [check-group-claims.py](/tmp/rev90c/scripts/check-group-claims.py:148) imports `INDEX_TITLE, INDEX_DEK` from the generator and [index_errors](/tmp/rev90c/scripts/check-group-claims.py:125) compares them to its pinned copies. [build](/tmp/rev90c/scripts/gen-backlog-page.py:1417) appends the index using `INDEX_TITLE, INDEX_DEK`; `sanitise_groups` only rebuilds `GROUPS` before that, so it does not silently rewrite the index framing field. Generator-only rewording did fail rule 4 with the expected “index dek has been reworded” message.

Declining the fourth mechanism is defensible. A cheap preface/HTML phrase pin would catch one named vector and then move the boundary to synonyms, the vocabulary paragraph, the callout, or future prose. It would not close the class; it would just create the next partial mechanism.

Regression run in `/tmp/rev90c`: `gen-backlog-page --self-test` 164/164, `check-group-claims --self-test` 30/30, `check-plan-code --self-test` 128/128, plus `check-docs`, `check-selftest-counts`, `check-fixture-variation`, `check-ratchet-contract`, and `check-review-rounds` all green after copying the symlink target `.agents` and `supabase` into the isolated tree.

VERDICT: NOT CONVERGED

---

## Round 3 remediation, recorded by the coordinator

⚠ **THIS ROUND REVIEWED `ea3c6554`, ONE COMMIT BEHIND.** Its own proof of subject says so. The
sweep commit `8e4bff1f` — which fixes the exact site this High names — landed after r3 was
dispatched. **That does not dismiss the finding**, for two reasons worth separating:

1. The finding was CORRECT about the commit it read. I had retracted the claim in the guard's
   docstring and the generator's constant block and left it standing at the `build()` site. I found
   that myself by grepping, but only after dispatching this round — the reviewer and I reached the
   same place independently, which is the reviewer working, not a stale artifact.
2. **Its MEASUREMENT is a separate finding and it survives the sweep.** *"I changed both pinned
   `INDEX_DEK` copies and `check-group-claims.py` still exited 0."* That is true of HEAD too.

**RE-MEASURED against the fixed text, both directions:**

    both copies rewritten to the retired bin's framing  → guard rc=0   (by design)
    one copy only                                        → guard rc=1

So even the corrected wording — *"rule 4 pins the two strings so they cannot change silently"* —
was still slightly loose: a coordinated two-file edit keeps CI green, which many readers would call
silent. **Tightened at both sites to the measured property:**

> Rule 4 makes rewording the index a **two-file edit**. It does **not** prevent the rewording. What
> it buys is that the change appears in a diff as two files rather than one line, and that an
> asymmetric change fails CI. That is the whole of it.

⚠ **THAT IS THE THIRD TIGHTENING OF ONE SENTENCE, AND THE PATTERN IS THE FINDING.** r1 refuted
"outside GROUPS means the bin cannot return". r2 refuted "rule 4 pins the words, so the bin cannot
return". r3's measurement refutes "cannot change silently". Each version was narrower than the last
and each was still a promise where only a property was true. The version now committed states a
property and names what it does not do.

**The reviewer also explicitly endorsed declining the fourth mechanism** — *"a cheap preface/HTML
phrase pin would catch one named vector and then move the boundary to synonyms, the vocabulary
paragraph, the callout, or future prose. It would not close the class."* That is the reasoning the
retraction rests on, reached independently.

**Also recorded, because it is reusable:** r3 needed `.agents` and `supabase` copied into its
isolated tree, and r2 needed `node_modules/typescript`, before the control was green. A reviewer
given only the tracked tree gets a RED control and nothing it measures is attributable.

REVIEW GAP: claude — not invoked. Only the adversarial half ran.
