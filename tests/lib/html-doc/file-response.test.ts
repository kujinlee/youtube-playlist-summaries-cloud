import { fileResponse } from '@/lib/html-doc/file-response';

const get = (r: Response, h: string) => r.headers.get(h);

describe('fileResponse', () => {
  it('inline md is text/plain (non-executable) with nosniff, no disposition', () => {
    const r = fileResponse('# hi', { kind: 'md', download: false, base: '00042_intro', cache: 'no-store' });
    expect(get(r, 'Content-Type')).toBe('text/plain; charset=utf-8');
    expect(get(r, 'X-Content-Type-Options')).toBe('nosniff');
    expect(get(r, 'Content-Disposition')).toBeNull();
  });
  it('download md is text/markdown, attachment, ascii base-key filename + unicode filename*', () => {
    const r = fileResponse('# hi', { kind: 'md', download: true, base: '00042_intro', title: 'Intro to AI', cache: 'no-store' });
    expect(get(r, 'Content-Type')).toBe('text/markdown; charset=utf-8');
    expect(get(r, 'Content-Disposition')).toBe(`attachment; filename="00042_intro.md"; filename*=UTF-8''Intro%20to%20AI.md`);
  });
  it('unicode title → ascii filename= is the base key, unicode rides in filename*', () => {
    const r = fileResponse('x', { kind: 'md', download: true, base: '00042_geon', title: '건강한 식습관', cache: 'no-store' });
    const cd = get(r, 'Content-Disposition')!;
    expect(cd).toContain('filename="00042_geon.md"');        // ascii half = base key
    expect(cd).toContain("filename*=UTF-8''");
    expect(cd).toMatch(/%ea%b1%b4/i);                        // 건 encoded, never literal in filename=
    expect(cd).not.toContain('건강');                         // never a non-Latin-1 filename= value
  });
  it('CR/LF/quote/semicolon in title cannot inject the header', () => {
    const r = fileResponse('x', { kind: 'md', download: true, base: '00001_v', title: 'a"\r\nb;c', cache: 'no-store' });
    const cd = get(r, 'Content-Disposition')!;
    expect(cd).not.toMatch(/[\r\n]/);
    expect(cd).toContain('filename="00001_v.md"');
    expect(cd).toContain('%0D%0A');                          // CR/LF percent-encoded in filename*
  });
  it('empty/all-non-ascii base → filename= falls back to summary', () => {
    const r = fileResponse('x', { kind: 'md', download: true, base: '   ', title: '', cache: 'no-store' });
    expect(get(r, 'Content-Disposition')).toContain('filename="summary.md"');
  });
  it('html carries csp + referrerPolicy when given; nosniff always', () => {
    const r = fileResponse('<html>', { kind: 'html', download: false, base: 'b', cache: 'no-store', csp: "default-src 'none'", referrerPolicy: 'no-referrer' });
    expect(get(r, 'Content-Type')).toBe('text/html; charset=utf-8');
    expect(get(r, 'Content-Security-Policy')).toBe("default-src 'none'");
    expect(get(r, 'Referrer-Policy')).toBe('no-referrer');
    expect(get(r, 'X-Content-Type-Options')).toBe('nosniff');
  });
  it('owner-style html (no referrerPolicy) emits no Referrer-Policy', () => {
    const r = fileResponse('<html>', { kind: 'html', download: false, base: 'b', cache: 'private, no-store', csp: 'x' });
    expect(get(r, 'Referrer-Policy')).toBeNull();
  });
  it('Buffer body round-trips byte-exactly (proves the as-BodyInit cast is safe)', async () => {
    const buf = Buffer.from('# héllo\n\nbody', 'utf-8');
    const r = fileResponse(buf, { kind: 'md', download: true, base: '00001_x', cache: 'no-store' });
    const rClone = r.clone();
    expect(await r.text()).toBe('# héllo\n\nbody');
    expect(Buffer.from(await rClone.arrayBuffer()).equals(buf)).toBe(true);
  });
});
