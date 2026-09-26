import { marked } from 'marked';
import createDOMPurify from 'dompurify';

marked.setOptions({ gfm: true, breaks: false });

/** @type {ReturnType<typeof createDOMPurify> | null} */
let purify = null;

function attachLinkHook(instance) {
  instance.addHook('afterSanitizeAttributes', (node) => {
    if (node.tagName === 'A') {
      node.setAttribute('target', '_blank');
      node.setAttribute('rel', 'noopener noreferrer');
    }
  });
}

function createPurifySync() {
  if (purify) return purify;
  if (typeof window !== 'undefined') {
    purify = createDOMPurify(window);
    attachLinkHook(purify);
    return purify;
  }
  throw new Error('DOMPurify requires window; install jsdom for Node tests');
}

function escapeHtml(text) {
  return String(text)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

/**
 * Parse Markdown to sanitized HTML for assistant chat bubbles.
 * @param {unknown} content
 * @returns {string}
 */
export function renderMarkdown(content) {
  if (content == null || content === '') return '';
  try {
    const raw = marked.parse(String(content), { async: false });
    return createPurifySync().sanitize(raw, {
      USE_PROFILES: { html: true },
      ADD_ATTR: ['target', 'rel'],
    });
  } catch (err) {
    if (String(err?.message || err).includes('DOMPurify requires window')) {
      throw err;
    }
    return escapeHtml(String(content)).replaceAll('\n', '<br>');
  }
}

/** Test-only: inject a purify instance (e.g. from JSDOM). */
export function __setPurifyForTests(instance) {
  purify = instance;
  attachLinkHook(purify);
}
