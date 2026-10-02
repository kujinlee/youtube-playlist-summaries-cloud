---
name: a-hang-is-not-a-diagnosis
description: "FIRES-WHEN: about to report why something hung or did not respond — A non-answer got reported as an answer, then the correction repeated the error with a different instrument — plus three false greens from pipeline exit codes, all in one day"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: dca6fb13-6aee-4a29-9254-0fa87e826497
  modified: 2026-08-24T18:28:15.568Z
---

**2026-08-24. Told the user "Docker is down, so the migration never ran" on the evidence of ONE
`docker info` that hung.** Never checked the socket, never checked whether Docker Desktop was
running, never tried to start it, and never checked whether Postgres was reachable at all. The user
asked *"you could not run the docker?"* — and the honest answer was that I had turned **"I got no
answer" into "the answer is no."** A hang is a missing measurement, not a negative one.

**Then the correction made the same error with a different instrument.** `nc -z 127.0.0.1 54322`
succeeded, so I said the database had been reachable all along. Also false: Docker Desktop's
port-forwarder keeps LISTENING after the container behind it stops answering, so the handshake
succeeds against nothing. `supabase migration up` timed out on
`host=127.0.0.1 user=postgres`. **A port that accepts a handshake is not a database** — `nc -z`
measures the layer *beside* the claim, which is [[true-about-the-name-silent-about-the-layer]] aimed
at my own tooling. Measured end state: CLI installed, Desktop process running, socket present,
`docker info`/`docker ps` both hang, port open, no Postgres. The daemon API was wedged.

**Why:** the original conclusion happened to be right, which is the trap — a correct outcome from an
unchecked premise reads as verification and gets written into a commit message, the roadmap and a PR
body. Being right by accident is not evidence of having checked.

**How to apply:** when a probe hangs, say *"could not determine"* and pick a different probe — never
promote the silence to a finding. Before believing any liveness check, ask what it actually opens:
`nc -z` opens a socket, `docker info` opens the daemon API, only a real query opens the database.
Same rule as [[separate-the-rule-from-the-fetch]]: do not let one tool's failure stand for a whole
capability.

---

**THE SAME DAY, THREE FALSE GREENS FROM ONE MECHANICAL CAUSE — treat as one class:**

1. `cmd | tail` reports **tail's** exit code. A ratchet read as passing for exactly this reason.
2. `timeout` **does not exist on macOS**. A dispatch died instantly and the pipeline reported `EXIT=0`.
3. A backgrounded `npx jest … | tail -60` produced a completion notification saying **"exit code 0"**
   while jest had FAILED at globalSetup. The harness's own success summary was wrong; only reading
   the output file caught it.

**Rule: never read `$?` after a pipe when the exit code is the thing being asserted.** Use
`${PIPESTATUS[0]}`, or redirect to a file and check the command's own status. Recorded on task #144
as a candidate for `docs/portable-practices.md` — measured, project-independent, three occurrences
in a day. Related: [[a-test-that-cannot-fail]],
[[a-convention-catches-what-you-read]].
