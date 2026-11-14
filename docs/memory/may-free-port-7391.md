---
name: may-free-port-7391
description: "FIRES-WHEN: something needs port 7391 (the owner's explainer server), e.g. plan step H7. Standing permission (owner 11-13 03:09): stop it, use the port, then RESTART it."
metadata:
  type: feedback
---

**I may free port 7391 myself whenever work needs it.** Owner, 2026-11-13 03:09, about marketplace plan step H7: "whenever you need to use the port, feel free to free up the port".

**Why:** the port is a constant in `scripts/explainer-serve.py`, so the marketplace experiment's "stranger" server can only run there. Waiting on the owner to stop their own server blocked the experiment for no gain.

**How to apply:**
- Stop it with `python3 scripts/explainer-serve.py --stop`, run from the owner's checkout, and note the time.
- **RESTART it afterwards from the same checkout.** Their pages and the Ask tray depend on it. Check that it answers on 7391 before saying it is back.
- No announcement needed (owner 11-13 03:12: chat moves too fast to notice, and a page cannot report its own server being down). Keep the outage short; if it interferes with their reading they will say so.
- This replaces the earlier "never stop or restart the owner's 7391 server" constraint ONLY for freeing the port; it does not permit editing their checkout's files. Plan step H7 is therefore no longer owed to the owner.
