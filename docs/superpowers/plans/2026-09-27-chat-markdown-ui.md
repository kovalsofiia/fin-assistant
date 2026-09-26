# Chat Markdown UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render assistant chat replies as sanitized Markdown, show a loading spinner while waiting, and visually separate the message list from the input bar.

**Architecture:** Extract a pure `renderMarkdown(content)` helper (`marked` → `DOMPurify`). Present it via `ChatMarkdown.vue`. Wire assistant bubbles + greeting in `ChatWidget.vue`; replace “Друкує…” with a `Loader2` spinner bubble; lightly restyle the panel chrome.

**Tech Stack:** Vue 3, Tailwind CSS 4, Lucide (`Loader2`), `marked`, `dompurify`, pnpm (frontend).

## Global Constraints

- Full Markdown for assistant/greeting only: headings, emphasis, lists, tables, fenced/inline code (no syntax highlighting).
- User messages stay plain text (no Markdown parsing).
- Sanitize all HTML before `v-html` (XSS-safe); allow safe `http`/`https` links with `target="_blank"` + `rel="noopener noreferrer"`.
- No backend/API changes; no streaming; no chat FAB / dashboard FAB layout changes in this plan.
- If render throws, fall back to escaped plain text so the bubble never blanks.
- Work in `frontend/` with pnpm; do not reintroduce `package-lock.json`.

## File map

| File | Responsibility |
|------|----------------|
| `frontend/package.json` (+ lockfile) | Add `marked`, `dompurify` |
| `frontend/src/components/chat/renderMarkdown.js` | Pure pipeline: parse + sanitize (+ fallback) |
| `frontend/src/components/chat/ChatMarkdown.vue` | Presentational `v-html` + element styles |
| `frontend/src/components/chat/ChatWidget.vue` | Wire markdown, spinner bubble, chrome styles |
| `frontend/src/components/chat/renderMarkdown.test.mjs` | Node built-in tests for the pure helper |

---

### Task 1: Add dependencies + `renderMarkdown` helper

**Files:**
- Modify: `frontend/package.json` (via pnpm)
- Create: `frontend/src/components/chat/renderMarkdown.js`
- Test: `frontend/src/components/chat/renderMarkdown.test.mjs`

**Interfaces:**
- Consumes: none
- Produces: `export function renderMarkdown(content: string): string` — returns safe HTML string

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/chat/renderMarkdown.test.mjs`:

```js
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { renderMarkdown } from './renderMarkdown.js';

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

  it('returns escaped plain text when content is empty-ish', () => {
    assert.equal(renderMarkdown(''), '');
    assert.equal(renderMarkdown(null), '');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run from `frontend/`:

```bash
node --test src/components/chat/renderMarkdown.test.mjs
```

Expected: FAIL (module not found / `renderMarkdown` missing).

- [ ] **Step 3: Install dependencies**

From `frontend/`:

```bash
pnpm add marked dompurify
```

Expected: `marked` and `dompurify` appear in `frontend/package.json` dependencies; lockfile updates.

- [ ] **Step 4: Implement `renderMarkdown.js`**

Create `frontend/src/components/chat/renderMarkdown.js`:

```js
import { marked } from 'marked';
import DOMPurify from 'dompurify';

marked.setOptions({
  gfm: true,
  breaks: false,
});

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
    return DOMPurify.sanitize(raw, {
      USE_PROFILES: { html: true },
      ADD_ATTR: ['target', 'rel'],
    });
  } catch {
    return escapeHtml(String(content)).replaceAll('\n', '<br>');
  }
}
```

Note: In Viteless Node tests, `dompurify` needs a `window`. If Step 5 fails with missing `window`, switch the helper to:

```js
import { marked } from 'marked';
import createDOMPurify from 'dompurify';
import { JSDOM } from 'jsdom';

const purify =
  typeof window !== 'undefined'
    ? createDOMPurify(window)
    : createDOMPurify(new JSDOM('').window);

// then use purify.sanitize(...)
```

and install `jsdom` as a **devDependency** only:

```bash
pnpm add -D jsdom
```

Prefer keeping production code on browser `window` when `typeof window !== 'undefined'`, and only construct `JSDOM` inside the Node test branch.

Minimal production-friendly pattern (recommended implementation):

```js
import { marked } from 'marked';
import createDOMPurify from 'dompurify';

marked.setOptions({ gfm: true, breaks: false });

function getPurify() {
  if (typeof window !== 'undefined') {
    return createDOMPurify(window);
  }
  // Lazy Node-only path for `node --test`
  const { JSDOM } = await import('jsdom'); // INVALID in sync fn — do not use
}
```

Use **sync** lazy init instead:

```js
import { marked } from 'marked';
import createDOMPurify from 'dompurify';

marked.setOptions({ gfm: true, breaks: false });

let purify;

function getPurify() {
  if (purify) return purify;
  if (typeof window !== 'undefined') {
    purify = createDOMPurify(window);
    return purify;
  }
  // eslint-disable-next-line no-undef
  const { JSDOM } = require('jsdom'); // avoid — project is ESM
}
```

**Final recommended helper** (ESM + optional jsdom for tests):

```js
import { marked } from 'marked';
import createDOMPurify from 'dompurify';

marked.setOptions({ gfm: true, breaks: false });

/** @type {import('dompurify').DOMPurify | null} */
let purify = null;

async function ensurePurify() {
  // Keep sync API for Vue: initialize synchronously in browser.
}

function createPurifySync() {
  if (purify) return purify;
  if (typeof window !== 'undefined') {
    purify = createDOMPurify(window);
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
      throw err; // surface misconfigured tests
    }
    return escapeHtml(String(content)).replaceAll('\n', '<br>');
  }
}

/** Test-only: inject a purify instance (e.g. from JSDOM). */
export function __setPurifyForTests(instance) {
  purify = instance;
}
```

Update the test file header to bootstrap JSDOM before importing the module under test — use dynamic import:

```js
import { describe, it, before } from 'node:test';
import assert from 'node:assert/strict';
import createDOMPurify from 'dompurify';
import { JSDOM } from 'jsdom';

const { window } = new JSDOM('');
const domPurify = createDOMPurify(window);

const { renderMarkdown, __setPurifyForTests } = await import('./renderMarkdown.js');
__setPurifyForTests(domPurify);

describe('renderMarkdown', () => {
  // ... same cases as Step 1
});
```

Install jsdom as devDependency:

```bash
pnpm add -D jsdom
```

Also post-process links after sanitize (optional but preferred) inside `renderMarkdown` after sanitize:

```js
// After sanitize, force safe link attrs via DOMPurify hook once at init:
createDOMPurify; // when creating purify:
// purify.addHook('afterSanitizeAttributes', (node) => {
//   if (node.tagName === 'A') {
//     node.setAttribute('target', '_blank');
//     node.setAttribute('rel', 'noopener noreferrer');
//   }
// });
```

Add the hook inside `createPurifySync` / test setter path once when the instance is first created.

- [ ] **Step 5: Run tests to verify they pass**

```bash
pnpm add -D jsdom
node --test src/components/chat/renderMarkdown.test.mjs
```

Expected: PASS (all 3 tests).

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/pnpm-lock.yaml \
  frontend/src/components/chat/renderMarkdown.js \
  frontend/src/components/chat/renderMarkdown.test.mjs
git commit -m "$(cat <<'EOF'
feat(chat): add sanitized Markdown render helper

EOF
)"
```

---

### Task 2: `ChatMarkdown.vue` presentational component

**Files:**
- Create: `frontend/src/components/chat/ChatMarkdown.vue`
- Test: manual (see Step 4); helper already covered in Task 1

**Interfaces:**
- Consumes: `renderMarkdown(content: string): string` from `./renderMarkdown.js`
- Produces: Vue SFC with prop `content: String` (required), renders sanitized HTML

- [ ] **Step 1: Create `ChatMarkdown.vue`**

```vue
<script setup>
import { computed } from 'vue';
import { renderMarkdown } from './renderMarkdown.js';

const props = defineProps({
  content: {
    type: String,
    required: true,
  },
});

const html = computed(() => renderMarkdown(props.content));
</script>

<template>
  <div
    class="chat-md text-sm text-gray-800 [&_h2]:mb-2 [&_h2]:mt-3 [&_h2]:text-base [&_h2]:font-bold [&_h3]:mb-1.5 [&_h3]:mt-2 [&_h3]:text-sm [&_h3]:font-semibold [&_p]:mb-2 [&_p:last-child]:mb-0 [&_ul]:mb-2 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:mb-2 [&_ol]:list-decimal [&_ol]:pl-5 [&_li]:my-0.5 [&_strong]:font-semibold [&_em]:italic [&_a]:text-blue-700 [&_a]:underline [&_code]:rounded [&_code]:bg-gray-200/80 [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-[0.8rem] [&_pre]:mb-2 [&_pre]:overflow-x-auto [&_pre]:rounded-lg [&_pre]:bg-gray-200/80 [&_pre]:p-2 [&_pre]:font-mono [&_pre]:text-[0.8rem] [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_table]:mb-2 [&_table]:w-full [&_table]:border-collapse [&_table]:text-left [&_th]:border [&_th]:border-gray-300 [&_th]:bg-gray-200/60 [&_th]:px-2 [&_th]:py-1 [&_th]:font-semibold [&_td]:border [&_td]:border-gray-300 [&_td]:px-2 [&_td]:py-1"
    v-html="html"
  />
</template>
```

- [ ] **Step 2: Smoke-check import in Node**

```bash
node -e "import('./src/components/chat/renderMarkdown.js').then(m => console.log(typeof m.renderMarkdown))"
```

Expected: prints `function` (may throw without purify init — if so, skip; rely on Task 1 tests).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/chat/ChatMarkdown.vue
git commit -m "$(cat <<'EOF'
feat(chat): add ChatMarkdown presentational component

EOF
)"
```

---

### Task 3: Wire Markdown + spinner + chrome in `ChatWidget.vue`

**Files:**
- Modify: `frontend/src/components/chat/ChatWidget.vue`

**Interfaces:**
- Consumes: `ChatMarkdown` (prop `content`), Lucide `Loader2`
- Produces: updated chat UX per spec

- [ ] **Step 1: Update imports**

In `<script setup>`, change the lucide import and add `ChatMarkdown`:

```js
import { MessageCircle, X, Send, RotateCcw, Loader2 } from 'lucide-vue-next';
import ChatMarkdown from './ChatMarkdown.vue';
import api from '@/services/api';
```

- [ ] **Step 2: Replace message list + loading + form chrome**

Replace the block from the messages `<div ref="listEl" …>` through the `<form …>` with:

```vue
      <div ref="listEl" class="flex-1 space-y-3 overflow-y-auto bg-gray-50 px-4 py-3">
        <div class="max-w-[92%] rounded-2xl bg-white px-3 py-2 shadow-sm ring-1 ring-gray-100">
          <ChatMarkdown :content="GREETING" />
        </div>
        <template v-for="(message, index) in messages" :key="index">
          <p
            v-if="message.role === 'user'"
            class="ml-auto max-w-[85%] whitespace-pre-line rounded-2xl bg-blue-600 px-3 py-2 text-sm text-white"
          >{{ message.content }}</p>
          <div
            v-else
            class="max-w-[92%] rounded-2xl bg-white px-3 py-2 text-gray-800 shadow-sm ring-1 ring-gray-100"
          >
            <ChatMarkdown :content="message.content" />
          </div>
        </template>
        <div
          v-if="isLoading"
          class="flex max-w-[92%] items-center gap-2 rounded-2xl bg-white px-3 py-2 text-sm text-gray-500 shadow-sm ring-1 ring-gray-100"
          role="status"
          aria-live="polite"
        >
          <Loader2 class="h-4 w-4 shrink-0 animate-spin text-blue-600" aria-hidden="true" />
          <span>Думаю…</span>
        </div>
      </div>

      <p v-if="error" class="bg-white px-4 pb-2 text-sm text-red-600">{{ error }}</p>

      <form class="flex items-end gap-2 border-t border-gray-200 bg-white p-3" @submit.prevent="send">
        <textarea
          v-model="draft"
          rows="1"
          :maxlength="MAX_MESSAGE_CHARS"
          placeholder="Напишіть запитання…"
          class="max-h-32 flex-1 resize-none rounded-xl border border-gray-200 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          @keydown.enter.exact.prevent="send"
        />
        <button
          type="submit"
          :disabled="isLoading || !draft.trim()"
          class="flex h-9 w-9 items-center justify-center rounded-full bg-blue-600 text-white disabled:opacity-40"
          aria-label="Надіслати"
        >
          <Send class="h-4 w-4" />
        </button>
      </form>
```

Keep the existing `<header>` and outer `<section>` unchanged.

- [ ] **Step 3: Manual verification**

Run (from repo root or `frontend/` as you normally do):

```bash
pnpm --dir frontend dev
```

Checklist (must all pass):

1. Ask for a tax summary that returns `##` / table → headers + table render (no raw `**` / `|`).
2. Bold / lists / inline code look styled inside the white assistant bubble.
3. Send a message → gray/white bubble with spinning `Loader2` + «Думаю…» until reply; Send disabled.
4. Message area is `gray-50`; input bar is white with a clear top border.
5. User message containing `**text**` still shows literal asterisks.

- [ ] **Step 4: Re-run unit tests**

```bash
cd frontend && node --test src/components/chat/renderMarkdown.test.mjs
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/chat/ChatWidget.vue
git commit -m "$(cat <<'EOF'
feat(chat): render Markdown replies and loading spinner

EOF
)"
```

---

## Spec coverage (self-review)

| Spec requirement | Task |
|------------------|------|
| Full MD (headings, bold, lists, tables, code) | Task 1 + 2 |
| User messages plain text | Task 3 |
| Sanitize before `v-html` | Task 1 |
| Spinner while loading | Task 3 |
| `bg-gray-50` list + clearer input border | Task 3 |
| Wider assistant bubbles (`max-w-[92%]`) | Task 3 |
| Send/reset disabled while loading | already in widget; Task 3 keeps it |
| Fallback on render failure | Task 1 `escapeHtml` catch |
| No highlighting / streaming / backend | Global constraints |
| Safe links | Task 1 DOMPurify hook |

No placeholders left after self-review; `renderMarkdown` / `__setPurifyForTests` / `ChatMarkdown` prop names are consistent across tasks.
