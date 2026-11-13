<!-- codex-review: model=gpt-6.1-sol -->

1. **MAJOR — Returning to a warning zone can be silent.** [check-usage-pace.py:1057](scripts/check-usage-pace.py#L1057) updates state only for WARN or absent-cache notices. OK, REFUSE and stale-cache notices leave the previous WARN key intact.

   Reproduced with session `zone-test`, TZ `PST8PDT,M3.2.0,M11.1.0`, `now=1800000000`, weekly usage `22`, reset `1800604800`. Meter snapshots containing a row at `1799996400` with starting percentages `10 → 11 → 10` produce:

   | Zone | Verdict | Notice |
   |---|---|---|
   | WIND-DOWN | WARN | Shown |
   | NORMAL | OK | Silent |
   | WIND-DOWN | WARN | **Silenced** |

   This violates the requirement to announce zone changes. Also reproduced `WARN(85) → REFUSE(99) → WARN(85)` and `fresh WARN → stale cache → fresh WARN`: both silence the final WARN. The four new tests miss intervening-verdict transitions.

2. **MINOR — Session/key concatenation can suppress another session’s absent-cache notice.** [check-usage-pace.py:858](scripts/check-usage-pace.py#L858) stores an ambiguous string.

   Concrete input: emit warning output `O` for session `"a"`. Then submit an absent-cache prompt with session ID `"a warn:" + sha256(O.encode()).hexdigest()[:16]`. That ID passes `session_of`; its **first absent-cache notice is silenced**, because it matches the first session’s stored WARN record. This requires an unusual session ID, rather than a normal UUID.

Validation: **413/413 self-tests passed**. Each of the three shipped mutations failed its intended test. Two additional temporary-copy mutations—constant WARN key and deduplication without a session ID—also failed the corresponding new tests, confirming sensitivity across all four new cases.

Repeated REFUSE, stale and malformed notices stayed loud. Ordinary absent/WARN alternation and session interleaving produced extra notices, without suppression. An unreadable state emitted the next warning before replacing the state. Override output remains outside WARN deduplication.

No repository edits or GitHub actions performed.

VERDICT: NOT CONVERGED
