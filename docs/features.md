# Feature map

**What this system does, what it deliberately does not, and where each is defined.** Rendered at
http://127.0.0.1:7391/features by `scripts/gen-features-page.py`; validated by
`scripts/check-features.py`.

**This file holds NAMES and PURPOSE, never STATE.** A node says what it is *for*; where it stands is
derived from the fragments beneath it. Do not add status, progress or "what's next" — a central file
that holds state drifts, and this project has measured that twice (see `docs/anchors.md`).

## PLATFORM

### job-queue-and-worker-lifecycle
state: built
for: Runs summarisation work reliably in the background, one job at a time, without losing or double-charging any of it.
anchors: cloud-publishing

### wake-on-visit
state: built
for: Lets the worker sleep when there is nothing to do and wake when a visitor causes work.
anchors: cloud-publishing
