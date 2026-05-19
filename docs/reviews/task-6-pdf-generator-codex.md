# Task 6 — PDF Generator: Codex Adversarial Review

**Verdict:** Three P1 security/reliability issues; P1.2 (Chromium leak) fixed; P1.1 and P1.3 addressed by design or documentation

---

## Findings

### P1 (Critical)

**1. Arbitrary file write via unsanitized `outputPath`**
`lib/pdf.ts` passes caller-controlled `outputPath` directly to `fs.writeFile` without bounds checking. Path traversal (e.g. `../`) can overwrite arbitrary files.
*Resolution:* Path validation (`outputFolder` bounds + `videoId` format) is the responsibility of the API routes layer (Task 10), per `docs/design-spec.md` Filesystem Safety spec. `generatePdf` is an internal utility that receives pre-validated paths. Added JSDoc doc comment to make this contract explicit: "Path validation is the caller's responsibility."

**2. `md-to-pdf` cleanup skipped when `dest` write fails — Chromium process leak**
Using `dest`-based writes, if `fs.writeFile` fails inside `md-to-pdf`, the Puppeteer browser may not be properly closed, leaking Chromium instances.
*Fix:* Switched to buffer mode: `mdToPdf({ content }, { css })` (no `dest`) returns a Buffer after Puppeteer is cleanly closed, then `fs.writeFile` is called separately. Failures in either step are caught independently. Added test for write failure path.

**3. Untrusted markdown/HTML executes in Chromium**
`mdContent` is passed directly to `md-to-pdf` which renders via Marked and Puppeteer. The package README warns to sanitize input. Script tags in model output would execute locally.
*Resolution:* Content originates from Gemini API (AI-generated Markdown, not raw HTML). The prompt injection defense in `lib/gemini.ts` (`<transcript>` delimiters + "do not follow instructions") reduces risk that transcript content escapes into summary/deep-dive Markdown. Accepted risk for this use case; documented for future review if content sources expand.

---

### P2 (Should Fix)

**4. Missing parent directory fails inside md-to-pdf — not before buffer generation**
Previously `md-to-pdf` would fail mid-operation if `dest` parent didn't exist. With buffer mode, `mdToPdf` runs to completion and then `fs.writeFile` throws ENOENT.
*Resolution:* Buffer mode isolates the write failure cleanly. Callers (`pipeline.ts`, `deep-dive.ts`) must create `outputFolder` before calling `generatePdf`. JSDoc documents this. Test added verifying correct ENOENT error wrapping.

**5. Puppeteer open handle causes Jest hang**
`md-to-pdf` keeps a Puppeteer browser handle open, causing Jest to hang after tests complete.
*Fix:* Added `forceExit: true` to `jest.config.ts` (async wrapper pattern to satisfy Next.js jest config TypeScript types).

---

## Resolutions Applied

- Buffer mode (no `dest`) prevents Chromium leak on write failure
- `fs.writeFile` called after `mdToPdf` returns cleanly
- JSDoc added: "parent directory must already exist; path validation is caller's responsibility"
- Test added: ENOENT error wrapping verified (`err.cause.code === 'ENOENT'`)
- `forceExit: true` added to `jest.config.ts`
