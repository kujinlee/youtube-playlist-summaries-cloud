Reviewed head: 380689fb486b3497128746c53479acbbbf1bf082

# explainer-port-631 — round 1, Claude half

Branch `explainer-port-631` (draft PR #651), against `origin/master`. The claim under attack: *"a foreign
listener or pid is never treated as ours or signalled, and our own server still works"* (backlog row 631,
whose FAILS-IF is "a foreign listener on the port makes `start()` exit 0, or `stop()` signals a pid that is
not our server").

`python3 scripts/explainer-serve.py --self-test` → **314/314 passed** (35 s). Every probe below ran on
ephemeral ports with `EXPLAINER_SERVE_ROOT` set to a temp dir. Nothing touched 7391. Probe script:
`/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/b8b70ddb-ac10-4d26-bd53-6419325840da/scratchpad/p631/probe.py`
(it loads the origin/master copy as `scripts/_old_explainer-serve.py`, which has since been deleted).

**Holds:** `start` on a silent listener, a non-JSON listener or an imposter with another root exits 3 and
leaves the listener alive. `--status` exits 3 on a foreign listener. Our own server's cycle works
(start 0 → "already serving" 0 → status 0 → stop kills it). `/__whoami` refuses a rebound Host and a
foreign Origin with 403, and it sends no CORS header. The exit-code table in the docstring matches `main`,
`start`, `stop` and `status`. The delivery-doc text matches the code.

## Findings

### F1 — MAJOR — `stop()` still SIGTERMs a pid that is not this server: the `ps` fallback is a substring match on the whole command line — REPRODUCED

`scripts/explainer-serve.py:2410`: `return "explainer-serve.py" in pid_command(pid)`. When the port gives no
`/__whoami` answer (the usual case for a stale pidfile, since our server is then down), any live process
whose argv *mentions* the filename counts as ours. This is the row's own FAILS-IF, conditioned on pid
reuse:

- **Reused pid onto an unrelated process that mentions the file.** Pidfile names
  `python3 -c 'sleep 60' /tmp/notes-about-explainer-serve.py`, and our port is free.
  `--stop` → `stopped pid 23069`, rc 0, and the **victim died**. An editor (`vim scripts/explainer-serve.py`),
  a `tail -f`, or a `--self-test` run are the realistic shapes.
- **Reused pid onto a sibling explainer-serve** (another root, another port). `--stop` → `stopped pid 18348`,
  and the sibling died (probe B). The same happens when our port is held by a foreign, silent listener
  (probe B2). The function's own comment says *"A sibling server elsewhere whose command also names the
  script is not what this pidfile's stop is about"*, but the fallback does exactly that.

This is better than before (master signalled any pid), but the claim "never signals a pid that is not this
server" is false. **Fix:** take the fallback only when the port IS busy and its holder (`lsof -t`) is the
pidfile's pid. That still lets `--stop` remove an old server that has no `/__whoami` (F3), and it refuses
both shapes above. A reused pid cannot be listening on our port by accident.

### F2 — MAJOR — `stop()` deletes a VALID pidfile of our own live server, then reports "not running" while two servers run — REPRODUCED

`scripts/explainer-serve.py:2391` (`if cmd: PIDFILE.unlink(...)`). The pidfile is keyed by ROOT, not by
port. The exit-3 message itself recommends `EXPLAINER_SERVE_PORT=<other>`, so one root served on two ports
is a state this change makes likely. Probe E: one root, server A on port a, then server B on port b, so the
pidfile now names B. Then:

- `start` on a → exit 3, *"held by another explainer-serve (pid A, serving <ROOT>) … NOT this server
  (root <ROOT>)"*. The two roots in that message are identical.
- `--stop` on a → exit 3, *"pid B is not our server (…/explainer-serve.py) … **Removed the stale pidfile**"*.
  B is our live server, and the pidfile was not stale. `cmd` being non-empty proves only that the pid is
  alive, not that it is foreign.
- `--stop` again → **rc 0 "not running"**, while A and B are both alive. Neither can now be stopped by the
  script, and `start` on either port exits 3 for good (classify needs pid == pidfile pid).

**Fix:** remove the pidfile only when `ps` shows the pid is NOT an explainer-serve. Better, key the pidfile
by port (or store `pid port` in it), so the pid comparison in `classify_listener` (`:1339`) asks the right
question. Also consider whether `start` should need pid equality at all, when marker + root already
identify the server and `start` is a no-op.

### F3 — MINOR — the owner's long-running OLD server (no `/__whoami`) now makes `start`/`--status` exit 3, with a self-contradicting message — REPRODUCED

Probe A: an origin/master server, then the new code gives:

- `start` → rc 3, *"held by a program that is NOT explainer-serve — pid 18335 (…/Python …/explainer-serve.py)"*.
- `--status` → rc 3, with the same text.
- `--stop` → rc 0, `stopped pid 18335`. The old server is gone, through the `ps` fallback.

So `--stop` does NOT regress, and nothing is signalled without being asked. The behaviour is **acceptable**:
it is a one-time state that `--stop` then `start` clears. But the message names explainer-serve while
saying it is not explainer-serve. Its choices omit the one that works (`--stop`, then re-run). And the
delivery doc tells the agent never to stop it, so the owner is asked to free a port held by their own old
server. **Fix:** when the holder's pid equals the pidfile pid and `ps` names the script, say "an older
explainer-serve without /__whoami — run `--stop`, then start again" (and give it its own exit code, or rc 3
with that text). Add one line in the delivery doc.

### F4 — MINOR — `start`/`--status`/`--stop` hang without bound on a listener that drip-feeds bytes — REPRODUCED

`listener_identity` (`:1310`) relies on the socket `timeout=1.0`, which applies per recv, not to the whole
exchange. A listener that sends one byte every 0.5 s kept `start` running past a 20 s harness timeout
(`TIMEOUT 20.01`). A silent listener (accepts, never answers) is bounded: start took 1.28 s, as did status.
The drip shape is pathological, but "every failure is None" is the stated contract. **Fix:** an overall
deadline, for example a monotonic check per read with a short cap.

### F5 — MINOR — two safety branches survive mutation (no case goes red) — REPRODUCED on temp copies, now deleted

- `:2409` `return answer.get("pid") == pid` → `return True`: **314/314 still pass**. This is the branch that
  keeps `stop` from signalling a reused pid while OUR server answers on the port with another pid. No case
  puts a listener on the port during `--stop`: `_stop_spares` uses `_free_port()`.
- `:2391` `if cmd:` → `if True:` ("unknown keeps the pidfile"): **314/314 still pass**.

I also checked one listed mutation: *"#631 start returns 0 on a listener that is NOT this server"* turns
exactly its `expect` case red (313/314). The other three listed mutations target `classify_listener` lines
that their named pure cases plainly assert. **Fix:** add a `--stop` case with an explainer-serve stand-in
answering on the port with pid ≠ the pidfile's pid, and a case where `ps` cannot say. Add both as mutations.

### F6 — NIT — `/__whoami` is trivially spoofable, and the bound is unstated

A local process that answers `{"server":"explainer-serve","pid":<pidfile pid>,"root":<ROOT>}` is "ours".
`start` then says "already serving", and `--stop` SIGTERMs the pidfile's pid. Any local process can already
do worse, so this is outside the threat model. Name it in the `#631` block comment as a BOUND, the way
`cross_site` states its own.

## DNS rebinding / cross-site

`/__whoami` goes through `cross_site` (`:1224`): `Host: rebound.evil.example` → 403, and a foreign `Origin`
→ 403 (self-test case, and it would go red without the check). With no CORS header, a cross-origin page cannot
read the body anyway. A request with neither header (curl) is let through, which is the stated bound. No
finding.

VERDICT: NOT CONVERGED
