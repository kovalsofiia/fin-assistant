import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import createDOMPurify from 'dompurify';
import { JSDOM } from 'jsdom';
import { renderMarkdown, __setPurifyForTests } from './renderMarkdown.js';

const { window } = new JSDOM('');
__setPurifyForTests(createDOMPurify(window));

describe('renderMarkdown', () => {
  it('renders headings, bold, and tables as HTML', () => {
    const html = renderMarkdown(
      '## Title\n\n**bold**\n\n| A | B |\n|---|---|\n| 1 | 2 |'
    );
    assert.match(html, /<h2[\s>]/i);
    assert.match(html, /<strong>bold<\/strong>/);
    assert.match(html, /<table[\s>]/i);
    assert.doesNotMatch(html, /\*\*bold\*\*/);
  });

  it('strips script tags from malicious input', () => {
    const html = renderMarkdown('<script>alert(1)</script>Hello');
    assert.doesNotMatch(html, /<script/i);
    assert.match(html, /Hello/);
  });

  it('returns empty string for empty-ish content', () => {
    assert.equal(renderMarkdown(''), '');
    assert.equal(renderMarkdown(null), '');
  });
});
