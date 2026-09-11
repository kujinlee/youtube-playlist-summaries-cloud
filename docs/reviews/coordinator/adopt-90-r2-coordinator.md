<!-- codex-review: model=gpt-5.5 -->

High: Rule 4 still does not prevent the retired bin from returning through generator context. [scripts/check-group-claims.py](/tmp/rev90b/scripts/check-group-claims.py:109) only compares `(INDEX_TITLE, INDEX_DEK)`, while [scripts/gen-backlog-page.py](/tmp/rev90b/scripts/gen-backlog-page.py:1485) renders those words inside generic group HTML, and the surrounding page prose before `{groups_html}` is independent at [scripts/gen-backlog-page.py](/tmp/rev90b/scripts/gen-backlog-page.py:1894). A change could leave both pinned strings untouched and still characterize the index by adding conditional prose around the index section, changing the preface, or otherwise emitting a claim adjacent to the index. The failing observation: “Instruments and habits, cheap individually” can be emitted around the index without changing `INDEX_TITLE` or `INDEX_DEK`, and Rule 4 would not see it.

Proof of subject:
`check-group-claims.py` declares `--self-test  # 30 cases`; `scripts/mutations/check-group-claims.json` has 11 entries; `EXPECTED_MUTATIONS` has 40 files and sums to 524.

Checked:
The manifest remediation is mechanically sound: 11 distinct names, 11 distinct effective edit anchors, each anchor exists exactly once in `scripts/check-group-claims.py`. `python3 scripts/check-plan-code.py --mutate .` passed after supplying the `node_modules/typescript` dependency that the exact archive lacks: `40 file(s), 524 mutation(s), 524 killed, 524 attributed, 0 survivor(s)`. Exact archive alone exits NOT MEASURED because `node_modules/typescript` is absent.

No finding on Rule 4 whitespace normalization: it catches punctuation, casing, added sentences, and rewording; it only collapses whitespace, matching browser/rendered prose behavior for this literal.

No finding on the two-line splits: `stated` and `same_words` preserve behavior and are live.

No finding on the new cases’ falsifiability: the Rule 4 manifest entries kill the retitle, reword, and raw-compare mutants; the re-wrap absence assertion is backed by the reword/retitle positive failures.

Regression checks passed:
`gen-backlog-page --self-test` 164/164, `check-group-claims --self-test` 30/30, `check-plan-code --self-test` 128/128, plus `check-docs`, `check-selftest-counts`, `check-fixture-variation`, and `check-ratchet-contract`.

VERDICT: NOT CONVERGED

---

## Round 2 remediation, recorded by the coordinator

**The Blocking from r1 is independently CLOSED.** This reviewer re-ran the real gate rather than
taking the coordinator's number: 11 distinct names, 11 distinct effective anchors, each existing
exactly once, and `--mutate .` → *40 files, 524 mutations, 524 killed, 524 attributed, 0
survivors*. ⚠ It also recorded that the exact `git archive` of tracked files alone exits NOT
MEASURED because `node_modules/typescript` is absent — a red CONTROL, and worth keeping: the
harness has a dependency outside the tracked tree.

**The High is ACCEPTED, and the fix is a RETRACTION rather than a fourth mechanism.**

r2 is right. Rule 4 compares `(INDEX_TITLE, INDEX_DEK)` only. Prose emitted elsewhere — the preface
above the groups, which already names the index by title, or new conditional markup around the
section — could characterise the index without touching either pinned string.

⛔ **NO FOURTH MECHANISM WAS ADDED, DELIBERATELY, AND THAT IS THE FINDING'S REAL RESOLUTION.**
Pinning the preface would close exactly the vector named here and leave the vocabulary paragraph,
the callout, and every paragraph written next year. The next reviewer would be equally right, and
this would be round 4 of the same shape. **Nothing can stop prose from characterising something.**

⚠ **THREE ROUNDS HAVE NOW FOUND THE SAME ERROR IN THREE PLACES, and it is one error:** I claimed a
thing was *mechanically* prevented when it was prevented only in the slot I happened to guard.
r1 found it on "the index is outside GROUPS"; r2 found it on "rule 4 pins the words". The fix that
finally holds is to state the scope exactly:

  * GUARDED — the index's framing FIELD, the slot that structurally played the retired bin's role.
  * NOT GUARDED — prose anywhere else. Named, with r2's example, in the guard's docstring and at
    the generator's own site.

The claim is now narrower than the finding, which is the only way a claim survives this class of
review. No code changed; two docstrings and one comment did.

REVIEW GAP: claude — not invoked. Only the adversarial half ran.
