#!/usr/bin/env node
// Print, as JSON, the UTF-16 CODE-UNIT spans of every COMMENT in each TypeScript/TSX file on argv.
//
// ⟳ r12 LOW (codex). This line said "byte spans" and the tool has never emitted bytes — TypeScript's
// scanner counts UTF-16 code units, so for `const x = '🖼'; // record_artifact` the `//` starts at
// byte 18 and this prints 16. The CODE is right and the SENTENCE was wrong: the only consumer,
// `scripts/check-paid-caller-arrival.py`, converts its own offsets with
// `len(t.encode("utf-16-le")) // 2` precisely because these are UTF-16 units. Changing the tool to
// emit bytes would have broken the caller to satisfy a comment. Naming the unit is the fix —
// a wrong contract is worse than none, because the next caller trusts it without measuring.
//
//     node scripts/ts-comment-spans.mjs a.ts b.tsx      ->  {"a.ts":[[12,40],[88,101]], ...}
//     node scripts/ts-comment-spans.mjs --self-test
//
// ⭐⭐ WHY THIS EXISTS: FOUR HAND-WRITTEN ANSWERS TO "IS THIS INSIDE A COMMENT?", EACH WRONG.
//
//   r10 H4  two regexes  -> a `//` INSIDE A STRING blanked a real `.rpc('record_artifact', …)` call
//   r11 H1  a scanner    -> a REGEX LITERAL containing a quote opened a phantom string, and from
//                           there inside/outside was inverted. MEASURED on the real tree: 14 files
//                           ended the scan inside a string and 240 real comment lines across 12
//                           production files were being classified as CODE. Both directions
//                           reproduced: a comment reported as a money caller, and a live
//                           `.rpc('record_artifact')` reported DORMANT.
//
// Each fix asked "what did the last counter-example have that ordinary code does not?" — a question
// about characters, with an unbounded supply of answers. `run-schema-assertions.sh` documents the
// same sequence costing four rounds in this repo, and the way out was to stop proxying and ask the
// thing itself. This is that: the TypeScript compiler already answers this question exactly, it is
// already a dependency of this repo (Next.js app, `tsc --noEmit` in CI), and it knows about regex
// literals, JSX, template interpolation, escapes and CRLF because it has to.
//
// ⛔ NO FALLBACK. If this cannot run, the caller must report CANNOT RUN. A degraded hand-rolled
//    answer is what the two rounds above were.
import ts from 'typescript';
import { readFileSync } from 'node:fs';

/** All comment spans in `text`, as [start, end) offsets. */
export function commentSpans(text, fileName = 'x.tsx') {
  const sf = ts.createSourceFile(fileName, text, ts.ScriptTarget.Latest, /*setParentNodes*/ true,
    fileName.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
  const spans = [];
  const seen = new Set();
  const add = (r) => {
    if (!r) return;
    for (const c of r) {
      const k = `${c.pos}:${c.end}`;
      if (!seen.has(k)) { seen.add(k); spans.push([c.pos, c.end]); }
    }
  };
  // Every token's leading trivia holds the comments that precede it; the last token (EndOfFile)
  // carries any trailing comments at the end of the file. Walking tokens therefore covers all of
  // them, and `getTrailingCommentRanges` catches same-line comments the next token would not lead.
  const walk = (node) => {
    if (node.getChildCount(sf) === 0) {
      const full = node.getFullStart();
      add(ts.getLeadingCommentRanges(text, full));
      add(ts.getTrailingCommentRanges(text, node.getEnd()));
    }
    node.getChildren(sf).forEach(walk);
  };
  walk(sf);
  return spans.sort((a, b) => a[0] - b[0]);
}

if (process.argv.includes('--self-test')) {
  let bad = 0, n = 0;
  const ck = (name, got, want) => {
    n++;
    if (got === want) console.log(`  ✓ ${name}`);
    else { console.log(`  ✗ ${name} — got ${got}, wanted ${want}`); bad++; }
  };
  // `inComment(text, needle)` — is the FIRST occurrence of `needle` inside a comment?
  const inComment = (text, needle) => {
    const at = text.indexOf(needle);
    return commentSpans(text).some(([s, e]) => at >= s && at < e);
  };
  ck('a plain line comment', inComment('// TODO record_artifact\n', 'record_artifact'), true);
  ck('a block comment', inComment('/* record_artifact */\nx;\n', 'record_artifact'), true);
  ck('a // inside a string is NOT a comment',
     inComment("const u='https://x/a'; sb.rpc('record_artifact');\n", 'record_artifact'), false);
  ck('r11 H1 — a REGEX LITERAL containing a quote does not desync',
     inComment(`s.replace(/["\\\\/;]/g,'_'); sb.rpc('record_artifact');\n`, 'record_artifact'), false);
  ck('r11 H1 — regex then a real comment is still a comment',
     inComment(`s.replace(/["\\\\/;]/g,'_'); // record_artifact soon\n`, 'record_artifact'), true);
  ck('a JSX apostrophe does not open a string',
     inComment(`const l=<p>Don't</p>; sb.rpc('record_artifact');\n`, 'record_artifact'), false);
  ck('a glob string containing /* does not open a block comment',
     inComment(`const G='src/*'; sb.rpc('record_artifact');\n`, 'record_artifact'), false);
  ck('template interpolation is CODE, not string',
     inComment('const s=`${sb.rpc("record_artifact")}`;\n', 'record_artifact'), false);
  ck('a comment inside template interpolation IS a comment',
     inComment('const s=`${/* record_artifact */ v}`;\n', 'record_artifact'), true);
  ck('CRLF line comment', inComment('// record_artifact\r\nx;\r\n', 'record_artifact'), true);
  console.log(`\n${n - bad} of ${n} self-test cases passed`);
  process.exit(bad);
}

const files = process.argv.slice(2).filter((a) => !a.startsWith('--'));
const out = {};
for (const f of files) out[f] = commentSpans(readFileSync(f, 'utf8'), f);
process.stdout.write(JSON.stringify(out));
