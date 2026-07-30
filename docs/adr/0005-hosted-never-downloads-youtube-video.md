---
status: accepted
---

# The hosted product never downloads YouTube video (no `yt-dlp`/`ffmpeg` server-side)

The **hosted** product obtains all YouTube content through **Gemini's native YouTube-URL
ingestion** — Google's API consuming Google's own video — and **never downloads video bytes
to our server**. The server image therefore ships **no `yt-dlp` and no `ffmpeg`/`ffprobe`**
(`Dockerfile` installs only Chromium, for PDF export). The **local** single-user tool keeps
the full `yt-dlp`/`ffmpeg` slide-capture path.

**This is a Terms-of-Service decision, not a packaging or performance one.** That distinction
is the whole reason this ADR exists: from the code, the absence of `ffmpeg` in the Dockerfile
is indistinguishable from an oversight, and reads as a gap someone should close.

Source: `docs/superpowers/specs/2026-07-01-cloud-publishing-architecture-design.md` §2.1
("Legal/ToS gate (Codex H9) — RESOLVED 2026-07-02").

## Why this is recorded as an ADR

The decision previously lived **only** in that spec — which is marked **Draft v3**, so a
reader cannot tell that §2.1 is binding while the surrounding document is provisional — plus
a single clause in `docs/deploy.md`.

It was misread on 2026-07-30. The first architecture review (`docs/reviews/architecture-review-2026-07-30.md`)
read exactly what Phase 6 requires — `CONTEXT.md` and `docs/adr/` — found no mention, and
described cloud slide capture as an incidental packaging limitation. `improve-codebase-architecture`
treats ADRs as the decisions a review must not re-litigate; a decision absent from `docs/adr/`
is, in practice, a decision a future review will propose reversing.

## Considered options

- **`yt-dlp` on the server (rejected — the ToS gate itself).** Reuse the existing local
  capture code in the worker. This is a server-side download of YouTube video, which the ToS
  gate exists to forbid. Datacenter IPs are also blocked in practice, so it fails
  operationally as well as legally.
- **Headless Chromium screenshotting the player (rejected — the same violation).** Tempting
  because **Chromium is already in the image** for PDF export, so it looks free. It is not:
  per §2.1, *any* server capture — `yt-dlp` **or** Chromium screenshotting the player — is
  the same ToS violation. **Swapping the tool does not change the posture.** Anyone proposing
  "we already have Chromium, just screenshot the frame" is re-opening this ADR, not finding a
  loophole.
- **Browser extension (rejected for now).** Cleaner frames and low per-use friction, but
  frame extraction is more aggressive, and it carries Chrome-Web-Store takedown risk under
  YouTube-downloader policy, plus a per-browser build.
- **Gemini YouTube-URL ingestion (chosen).** The Gemini API accepts a YouTube URL directly;
  Google's infrastructure watches the video and returns transcript/summary/analysis. No bytes
  touch our server. Already present in the codebase as `transcribeViaGemini`, promoted from
  caption-gated fallback to the primary hosted path. Constraints to design around: **public
  videos only**, a per-day YouTube quota, and the URL feature being in preview.

## Consequences

- **ToS-clean hosted deliverables** are summaries, dig-deeper *text*, section timestamps, and
  visual *descriptions* ("at 4:32 a diagram shows…"). Gemini returns understanding, not frames.
- **No pixel slides in the cloud, by construction.** Real YouTube pixels can only be obtained
  on the **user's own device** — via the official player or a file the user already holds.
  Slide capture is therefore a capability with two implementations: a cloud one (descriptions
  / no image) and an on-device one (the current `yt-dlp`/`ffmpeg` code).
- **When hosted slides are added, `getDisplayMedia` is the default mechanism** — the user
  screenshots their own screen, needs no install, and keeps the cleanest posture. It is a
  deferred, self-contained feature, not part of the spine.
- **The absent binaries are load-bearing, not an oversight.** Do not add `yt-dlp` or `ffmpeg`
  to the `Dockerfile` to "fix" cloud slide capture. A lighter worker image is a side effect of
  this decision, never its justification.
- **CI installing `ffmpeg` does not contradict this** (`.github/workflows/ci.yml`). The test
  runner is not the product: `tests/lib/dig/slide-crop.integration.test.ts` exercises the
  **local** capture path, which legitimately uses `ffmpeg`. The constraint is on what the
  hosted product does to YouTube, not on what a test machine has installed.
- **The CSP is consistent with this, not accidentally inert.** `buildDigCsp` sets
  `img-src 'none'` while the dig renderer can emit `data:` images; that combination never
  fires in the cloud because the cloud dig path carries no assets. Exploration during the
  2026-07-30 review raised this as latent risk "if cloud slide capture ships" (it was not
  carried into that document's findings). Under this ADR server-side capture does not ship,
  so it stays inert by design. Revisit the CSP only if on-device capture starts delivering
  pixels into a cloud-served document.
- **Reversing this decision is a legal question first.** Any change that makes the server
  acquire YouTube frames — regardless of tool — requires re-opening the ToS gate, not merely
  an engineering plan.
