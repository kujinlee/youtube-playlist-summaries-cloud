describe('project setup', () => {
  it('Jest is configured and running', () => {
    expect(true).toBe(true);
  });

  it('TypeScript types are available', () => {
    const value: string = 'hello';
    expect(typeof value).toBe('string');
  });
});
