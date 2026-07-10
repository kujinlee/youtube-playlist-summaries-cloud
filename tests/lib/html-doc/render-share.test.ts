import { renderMagazineHtml } from '@/lib/html-doc/render';

const parsed = {
  title: 'V', channel: 'C', url: 'https://youtu.be/x', videoId: 'abc123',
  sourceMd: '00042_my-secret-slug.md', tldr: 'td', takeaways: [],
  sections: [{ title: 'S1', prose: 'p', timestamp: null }], sourceSectionsRaw: [],
} as any;
// MagazineSection requires `lead: string` + `bullets: Bullet[]` (types.ts:39-43) — render.ts:92/98
// read m.bullets[].text and m.lead, so a {heading,body} fixture would throw before any assertion.
const model = { title: 'V', dek: 'd', sections: [
  { lead: 'S1', bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] },
] } as any;

describe('renderMagazineHtml share mode', () => {
  it('strips the MD key + video-id + generator metas when share:true', () => {
    const html = renderMagazineHtml(parsed, model, { nonce: 'n', dig: false, share: true });
    expect(html).not.toContain('00042_my-secret-slug.md'); // B22 — the owner-structure leak
    expect(html).not.toContain('name="source-md"');
    expect(html).not.toContain('name="video-id"');
    expect(html).not.toContain('name="generator"');
    expect(html).toContain('S1'); // body retained
  });
  it('non-share render still emits the metas (unchanged default)', () => {
    const html = renderMagazineHtml(parsed, model, { nonce: 'n', dig: false });
    expect(html).toContain('00042_my-secret-slug.md');
  });
});
