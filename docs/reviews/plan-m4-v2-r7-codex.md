<!-- codex-review: model=gpt-5.5 -->

Wrote the Round 7 review to [docs/reviews/plan-m4-v2-r7-codex.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/reviews/plan-m4-v2-r7-codex.md).

Result: **NOT CONVERGED**.

Findings filed:
- **Blocking:** `TRUNCATE` is omitted from the live privilege digest, and `check-anon-exposure.py` does not cover M4 tables. Measured `anon` emptying `video_artifacts` while the live M4 gate stayed green.
- **High:** `proargdefaults` is excluded for a false reason. Measured a default-only function behavior change with identical `prosrc`, unchanged identity args, and `check-live-schema.py` still exit 0.
- **Medium:** `check-catalog-coverage.py` does not fail closed if `CATALOGS` omits a read catalog.
- **Medium:** `run-schema-assertions.sh` still cannot run against the real `05_assert.sql`, while the plan says it should exit 0 and be wired into the gate suite.

Cleanup verified:
- `remaining_dbs|<none>`
- `remaining_roles|<none>`

Only the new review file is changed/untracked.

---

# ⛔ REVIEW GAP — coordinator note, 2026-08-25

**This file is a SUMMARY of a review, not the review.** Line 3 says *"Wrote the Round 7 review to
`docs/reviews/plan-m4-v2-r7-codex.md`"* — pointing at itself. The four findings below it are stated
as conclusions with no premise, no quoted `file:line`, and **none of the executed evidence the
prompt required**. The commands, their output, and the reasoning are gone; the task output file
(189 bytes) and the wrapper log (513 bytes) do not hold them either.

**This is a NEW fail-open mode for `scripts/codex-review.py`.** Its documented success criterion is
that `-o/--output-last-message` wrote *a substantive final-message file* — deliberately not the exit
code, after HTTP-400 runs were recorded as completed gates. A summary satisfies "substantive". The
criterion checks that the file is not empty; it cannot check that the file **is the review**.

**Disposition: treat the Codex half of round 7 as HAVING RUN BUT NOT HAVING REPORTED.** Its four
claims are LEADS, not findings, and each is being re-derived from scratch by the coordinator. Under
`docs/plugins.md` the fallback rule ("a Claude adversarial review satisfies the gate") applies, and
the Claude half is the substantive half of this round.

## Lead 1 (claimed Blocking) — ✅ **CONFIRMED BY THE COORDINATOR, INDEPENDENTLY MEASURED**

The claim: `TRUNCATE` is omitted from the live privilege digest, and `check-anon-exposure.py` does
not cover the M4 tables.

Re-derived by execution on a scratch M4 database, `m4_v7_trunc`, since dropped:

```
control (clean M4): gate exit=0
--- anon TRUNCATE before: false
    grant truncate on video_artifacts to anon;
--- anon TRUNCATE after : true
--- gate after granting TRUNCATE to anon: exit=0
    live schema […]: M4 is PRESENT as expected — checked all 161 objects,
    BY DEFINITION not just by name

--- does check-anon-exposure notice?
    money tables TRUNCATE-able by a session role: 5/5 (baseline 5)
    Anon exposure OK — … the TRUNCATE debt has not grown.
```

And by reading, `scripts/check-anon-exposure.py:67-68`:

```python
MONEY_TABLES = ("spend_ledger", "ledger_audit", "serve_owner_budget",
                "serve_model_charge", "guardrail_config")
```

**Not one M4 table.**

⭐ **THE PART THAT IS MINE, AND IS WORSE THAN THE GAP ITSELF.** `scripts/m4_catalog.py`'s r6 note
justifies excluding TRUNCATE from `REL_PRIVS` like this:

> *"The privileges that diverge are exactly the ones the M4 spec never mentions, and they are
> already covered by `check-anon-exposure.py`, which ratchets them against a recorded
> per-environment baseline — the right home, because it is environment-aware and this manifest
> cannot be."*

**That sentence is false for the five M4 tables**, and I wrote it in the same round that added
`check-catalog-coverage.py`, whose own docstring says: *"It cannot prove an excluded column is
CORRECTLY excluded — that judgement is in the REASONS, and a wrong reason here is a real defect that
this script will happily report as green."* The script predicted the shape of my own next mistake
and I made it eight hours later, in the file the script was written to protect.

**Consequence, in observable units.** `truncate video_artifacts` deletes every paid artifact row,
and TRUNCATE does **not** fire the row-level append-only guards — so the mechanism M4 exists to
provide is bypassed rather than violated. Two independent instruments report green over it.

**⭐ The fix is now CHEAPER than the reason for the exclusion.** TRUNCATE/REFERENCES/TRIGGER/MAINTAIN
were excluded because they diverged between a `--no-privileges` clone and production — measured in
r6 as `anon=r` vs `anon=rDxtm`. **The r6 revoke-before-grant change strips exactly those**, so all
privileges should now agree in both environments and the exclusion has outlived its own premise.
To be verified against the three-shape test before the fix is claimed.

Leads 2-4 (`proargdefaults` excluded for a false reason; `check-catalog-coverage.py` not failing
closed when `CATALOGS` omits a catalog; `run-schema-assertions.sh` still unable to run against the
real `05_assert.sql`) are **NOT YET VERIFIED** and are recorded here so round 8 does not lose them.
