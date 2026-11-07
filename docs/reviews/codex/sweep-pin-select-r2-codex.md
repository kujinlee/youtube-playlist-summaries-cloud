<!-- codex-review: model=gpt-6.1-sol -->

- **R2-F1 — Medium — `scripts/check-merge-ready.py:1075`**: The binding check still permits the round-one bypass. Insert `globals()['PINS_FILE'] = 'scripts/mutations/pins_v2.py'` before the accepted `EXPECTED_MUTATIONS` assignment, or import the replacement `PINS_FILE`: neither creates an `ast.Name(Store)` node. Changing `own_pins_path()` to return that alternate file also passes. Reproduced all three with `check-anchors.py` lowered 5 → 4: binding problems, effective pin drift, own-pin problems, and merge holds were all empty while merge-ready read the unchanged original pins. Otherwise-green gates therefore yield READY. Trusting the loader bodies leaves the same source-divergence defect open; the new cases do not cover these routes.

- **R2-F2 — Low — `scripts/check-merge-ready.py:1075`**: The scan counts unrelated local variables as module bindings. Adding a harmless helper containing local `PINS_FILE = "fixture.py"` makes the real harness fail with `PINS_FILE is written 2 times, not once`, causing CANNOT RUN despite unchanged effective pins. Reproduced directly.

Validation: both self-tests passed (**323/323**, **264/264**). All **five added or modified mutations** failed every named case. Direct augmented assignment and deletion were refused.

VERDICT: NOT CONVERGED
