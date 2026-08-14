// tests/integration/storage-key-contract.test.ts
//
// Pins the four facts about SUPABASE STORAGE ITSELF that the backlog #36 design
// rests on. Run via: npm run test:integration -- storage-key-contract
//
// WHY THIS FILE EXISTS
// --------------------
// The #36 spec's premises table (§1.1) labels P1 and P2 MEASURED. They were —
// by a throwaway probe script, whose output was then retyped into prose. The
// first version of that prose said Storage's limit was "267 characters, whole
// path". It is 255 per path SEGMENT. The probe varied one segment under a fixed
// 12-character prefix, so NO OUTCOME OF IT could distinguish the two
// hypotheses, and the wrong one was written down and believed for three review
// rounds.
//
// A measurement that lives in prose cannot go red. These assertions can. They
// deliberately test Storage the SERVICE, through the raw client, NOT through
// SupabaseBlobStore — once #36's encoder lands at that seam, the adapter will
// never send Storage a key that violates any of these, so testing through it
// would silently stop measuring the subject.
//
// If Storage's behaviour ever changes, this file goes red and the spec's
// premises are wrong. That is the entire point.

import { newUser, signInAs } from './helpers/clients';
import type { SupabaseClient } from '@supabase/supabase-js';

jest.setTimeout(30_000);

const BUCKET = 'artifacts';

/** A fresh authenticated client plus this user's owner prefix. Storage RLS keys
 *  writes off the first path segment, so every key below is built under it. */
async function ownerClient(): Promise<{ client: SupabaseClient; prefix: string }> {
  const u = await newUser();
  const { client, userId } = await signInAs(u.email, u.password);
  return { client, prefix: `${userId}/keycontract` };
}

/** Upload one byte at `path` and report what Storage said.
 *
 *  Returns the HTTP status rather than a boolean, because two of the four facts
 *  below are ABOUT the status: an over-long key is a 500 and a bad character is
 *  a 400, which is why an over-long key is indistinguishable from a transient
 *  fault at the call site. Collapsing that to ok/not-ok would erase the finding.
 *
 *  Throws if the call produced neither a success nor a readable status — "could
 *  not reach Storage" must never be scored as a pass. */
async function tryUpload(
  client: SupabaseClient,
  path: string,
): Promise<{ ok: boolean; status: number | null; message: string }> {
  const { error } = await client.storage
    .from(BUCKET)
    .upload(path, Buffer.from('x'), { contentType: 'text/plain', upsert: true });

  if (!error) return { ok: true, status: 200, message: '' };

  const status = (error as { statusCode?: string | number }).statusCode;
  const parsed = status === undefined ? null : Number(status);

  if (parsed === null || Number.isNaN(parsed)) {
    throw new Error(
      `Storage rejected ${JSON.stringify(path)} with no readable status — TREAT THIS AS NOT RUN, ` +
        `not as a passing rejection. Raw error: ${JSON.stringify(error)}`,
    );
  }
  return { ok: false, status: parsed, message: error.message };
}

/** Remove everything this file created, so a rerun measures the same world. */
async function cleanup(client: SupabaseClient, paths: string[]) {
  if (paths.length) await client.storage.from(BUCKET).remove(paths);
}

// ---------------------------------------------------------------------------
// Precondition: the suite can actually write to Storage.
//
// Every assertion below is of the form "Storage REFUSES x". A run with no
// credentials, no bucket, or no RLS grant would refuse everything and every
// test would pass — the exact shape of a green check over an unreachable
// subject. This runs first and fails loudly instead.
// ---------------------------------------------------------------------------
test('precondition — a plainly legal key uploads, so a refusal below means something', async () => {
  const { client, prefix } = await ownerClient();
  const path = `${prefix}/0001_plain-ascii.md`;

  const r = await tryUpload(client, path);
  expect({ ...r, note: 'if this fails, EVERY assertion in this file is vacuous' }).toMatchObject({
    ok: true,
  });

  await cleanup(client, [path]);
});

// ---------------------------------------------------------------------------
// P1 — Storage rejects every non-ASCII object key. (#36 spec §2.1)
//
// This is the whole reason #36 exists: a Korean title reached the key and the
// upload 400'd AFTER Gemini had been paid.
// ---------------------------------------------------------------------------
describe('P1 — non-ASCII keys are rejected', () => {
  const NON_ASCII: Array<[string, string]> = [
    ['Hangul', '0001_한국어.md'],
    ['Japanese', '0001_日本語.md'],
    ['Cyrillic', '0001_русский.md'],
    ['accented Latin NFC', '0001_café.md'],
    ['accented Latin NFD', '0001_café.md'],
    ['emoji', '0001_a\u{1F600}b.md'],
  ];

  test.each(NON_ASCII)('rejects %s', async (_label, key) => {
    const { client, prefix } = await ownerClient();
    const r = await tryUpload(client, `${prefix}/${key}`);
    expect(r.ok).toBe(false);
    expect(r.status).toBe(400);
  });

  // NFC and NFD both being rejected is load-bearing: it is why the design can
  // decline to introduce ANY Unicode equivalence. If Storage ever started
  // accepting one form, "two byte strings are two keys" would stop being free.
  test('both NFC and NFD accented forms are rejected — no form sneaks through', async () => {
    const { client, prefix } = await ownerClient();
    expect((await tryUpload(client, `${prefix}/café.md`)).ok).toBe(false);
    expect((await tryUpload(client, `${prefix}/café.md`)).ok).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// P2 — the length limit is 255 per path SEGMENT, with no whole-path bound in
// the range that matters. (#36 spec §2.2)
//
// THIS IS THE ONE THAT WAS MEASURED WRONG. The assertions are written as the
// discriminating experiment the original probe was not: a long TOTAL path built
// from short segments must be ACCEPTED, and only the segment itself is bounded.
// ---------------------------------------------------------------------------
describe('P2 — 255 per segment, not per path', () => {
  test('a 255-character segment is accepted', async () => {
    const { client, prefix } = await ownerClient();
    const seg = `${'a'.repeat(252)}.md`; // 255 exactly
    expect(seg.length).toBe(255);

    const path = `${prefix}/${seg}`;
    const r = await tryUpload(client, path);
    expect(r.ok).toBe(true);

    await cleanup(client, [path]);
  });

  test('a 256-character segment is rejected — and with 500, NOT 400', async () => {
    const { client, prefix } = await ownerClient();
    const seg = `${'a'.repeat(253)}.md`; // 256 exactly
    expect(seg.length).toBe(256);

    const r = await tryUpload(client, `${prefix}/${seg}`);
    expect(r.ok).toBe(false);
    // Deliberately asserting the exact status. An over-length key is reported
    // the same way a transient backend fault is, so a caller that retries on
    // 5xx will retry this forever. Anything that changes this is worth knowing.
    expect(r.status).toBe(500);
  });

  test('a >1000-character total path made of short segments is ACCEPTED', async () => {
    const { client, prefix } = await ownerClient();
    // 60 segments of 18 chars + separators, every segment far under 255.
    const deep = Array.from({ length: 60 }, (_, i) => `seg${String(i).padStart(2, '0')}_padpadpadpad`);
    const path = `${prefix}/${deep.join('/')}/leaf.md`;
    // Asserted, not assumed: the first draft of this line claimed >1000 for a
    // path that was 816, and the test caught it. Prose arithmetic about lengths
    // is precisely what got the 255-vs-267 measurement wrong in the first place.
    expect(path.length).toBeGreaterThan(1000);

    const r = await tryUpload(client, path);
    // If this ever fails, a whole-path bound exists after all and the encoder's
    // per-segment reasoning (spec §3.2) is unsound.
    expect(r.ok).toBe(true);

    await cleanup(client, [path]);
  });
});

// ---------------------------------------------------------------------------
// P-charset — the five characters Storage ACCEPTS that the encoder's SAFE class
// excludes. (#36 spec §4)
//
// These are the entire content of the "do we need a migration?" question: SAFE
// is `[A-Za-z0-9._-]`, so any pre-existing object using one of these would be
// renamed by the encoder and its blob orphaned. If this list ever grows, §4's
// gate is checking for the wrong set.
// ---------------------------------------------------------------------------
describe('P-charset — accepted by Storage but outside the encoder SAFE class', () => {
  const ACCEPTED_OUTSIDE_SAFE: Array<[string, string]> = [
    ['space', '0001_a b.md'],
    ['open paren', '0001_a(b.md'],
    ['close paren', '0001_a)b.md'],
    ['plus', '0001_a+b.md'],
    ['equals', '0001_a=b.md'],
    ['leading equals', '=0001_ab.md'],
  ];

  test.each(ACCEPTED_OUTSIDE_SAFE)('Storage accepts %s', async (_label, key) => {
    const { client, prefix } = await ownerClient();
    const path = `${prefix}/${key}`;

    const r = await tryUpload(client, path);
    expect(r.ok).toBe(true);

    await cleanup(client, [path]);
  });

  // `=` is the encoder's marker character. The design argues it is safe to use
  // because Storage accepts it and `slugify` cannot emit it. The first half of
  // that argument is asserted above; this pins the second half so the two
  // cannot drift apart silently.
  test('slugify cannot emit the marker character `=`', async () => {
    const { slugify } = await import('@/lib/slugify');
    const hostile = 'a=b === c =';
    expect(slugify(hostile)).not.toContain('=');
  });
});
