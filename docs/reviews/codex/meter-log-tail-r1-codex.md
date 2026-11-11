<!-- codex-review: model=gpt-6.1-sol -->

- **C1 — Medium — scripts/check-usage-pace.py:341:** A retained pre-midnight row does not prove the correct midnight start survived the cut when rows arrive out of order. Reproduced with the actual 4 MiB bound: an 85% row at midnight−1s lies outside the tail; a later-appended 10% row timestamped midnight−1h remains inside it. With reset three days after midnight, the complete log yields **92.5%**, but the tail yields **55%** with no refusal or NOT RUN warning. The documented ordering assumption is unenforced.

Validation: **361/361 self-tests passed**. All nine new mutations and seven repointed mutations triggered their expected failures. Boundary, UTF-8, CRLF, DST, deadline, growth, and truncation probes completed.

VERDICT: NOT CONVERGED
