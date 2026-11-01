<!-- codex-review: model=gpt-6.1-sol -->

1. **Medium — notice persistence can block indefinitely.** `scripts/check-usage-pace.py:467`  
   **Fix-induced: yes**, round-1 notice fold (`b37549ce`); predates DEFER.  
   Concrete input: absent cache; stdin `{"session_id":"fifo-notice"}`; a FIFO at `.claude/usage-pace-notice.<python-pid>.tmp`, created before sending and closing stdin. The **shipped prompt hook remained alive after 5 seconds**, producing nothing; I killed its process group. The synchronous `open(..., "w")` has no deadline.  
   **Fix:** create temporary files exclusively with unpredictable names and bound notice persistence within the hook’s overall deadline.

2. **Medium — checkout resolution exceeds the read-deadline guarantee.** `scripts/check-usage-pace.py:420–421`  
   **Fix-induced: yes**, round-1 override fold (`791c4791`); predates DEFER.  
   Concrete input: fresh weekly **95%** cache, no override, and `.git/config` replaced with a FIFO without a writer. The **shipped spawn hook took 5.20 seconds** before denying, exceeding the one-second deadline and existing 1.5-second test margin. Git has its own five-second timeout outside the bounded reads.  
   **Fix:** enforce an overall monotonic hook budget and pass its remaining time to git and subsequent I/O.

3. **Low — an override can authorize after expiry.** `scripts/check-usage-pace.py:507`, `:628–639`  
   **Fix-induced: yes**, round-1 expiring-override fold (`791c4791`); predates DEFER.  
   Concrete input: fresh **95%** cache; override expiry `t+0.8`; delay git’s config read for 1.5 seconds using a FIFO, then replace it with regular config and release the reader. The **shipped spawn hook silently allowed at 1.53 seconds**, about **0.73 seconds after expiry**. Expiry is compared with the timestamp captured before I/O. An already-expired override correctly denied.  
   **Fix:** check expiry against current wall time after lookup, immediately before allowing.

All findings take the **FILED** disposition under terminal DEFER; no fold performed.

Reviewed the DEFER diff first, then the branch against `origin/master`, including `91e4b490`. Its teammate bound remains explicitly qualified as inference. The DEFER protections held; #404 is excluded.

Both requested commands completed in the foreground:

- Self-test: **279/279 passed**.
- Mutation diagnostic: **102 killed, 102 attributed, 0 survivors**, exit 0.

Working tree unchanged; no review file written; `~/.claude` untouched; `.claude/plans/` neither read nor quoted.

**NOT CONVERGED.**
