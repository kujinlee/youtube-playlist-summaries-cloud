---
name: restart-docker-dont-record-cannot-run
description: "FIRES-WHEN: a gate needs Docker and it is unresponsive — ⭐ User instruction 2026-09-22 — when a gate needs Docker and it is unresponsive, RESTART IT. Do not record CANNOT RUN and defer to CI. A visible Docker Desktop window is not a responsive daemon"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e8d4fa1c-667d-4d08-bd64-55931cd5a12f
  modified: 2026-09-23T03:07:57.142Z
---

**User, 2026-09-22, twice:** *"restart docker when you need it"* and then *"when you need docker and
it is not responsive, do not give up. restart it."*

I had run the catalog-reading gates, watched them hang, recorded **CANNOT RUN**, and deferred them
to CI. That is the correct handling of a gate that *cannot* be made to run — and the wrong handling
of one that can, because restarting Docker is a local, reversible, thirty-second operation.

**Why:** `docker` is not an external dependency that is simply down; it is a local app I am allowed
to restart. Recording CANNOT RUN when the fix is in reach converts a solvable problem into a
permanent gap in the evidence, and this project's whole standard is that *"CI covered it"* and
*"I checked it here"* are different claims.

**How to restart it — `open -a Docker` IS NOT ENOUGH, measured:**

| Symptom | What it means |
|---|---|
| Docker Desktop window visible, `com.docker.backend` running | the APP launched — proves nothing about the engine |
| `docker context ls` answers instantly | the CLI binary is fine (no daemon needed) |
| `docker version` / `docker ps` hang | the Linux VM behind the socket is wedged |
| `~/.docker/run/docker.sock` exists but dates from days ago | a stale socket, not a live one |

```bash
open -a Docker                       # NO-OP if macOS thinks the app is already running
osascript -e 'quit app "Docker Desktop"'   # quits the UI; the backend IGNORED it
pkill -f com.docker.backend          # needed SIGTERM *and then* SIGKILL
pkill -9 -f com.docker.backend
open -a Docker                       # daemon answered immediately after a clean start
```

⚠ `com.docker.vmnetd` is a privileged LaunchDaemon and is MEANT to survive — do not chase it.

**Probe it BOUNDED, or the probe becomes the hang.** `docker ps` in a plain Bash call blocks until
the tool's timeout; use `subprocess.run(..., timeout=10)` and treat a `TimeoutExpired` as "wedged".
Same shape as [[a-hang-is-not-a-diagnosis]]: a socket file existing proves a path, not an answer.

See also [[separate-the-rule-from-the-fetch]] — three ratchets sat untestable for 8 days because
their ENTRY POINT needed Docker while their rules were pure.
