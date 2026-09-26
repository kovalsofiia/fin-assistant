# Design: Chat Markdown rendering + loading spinner

Date: 2026-09-27  
Status: approved (pending implementation plan)

## Goal

Improve the financial assistant chat widget so assistant replies render as proper Markdown (headers, bold/italic, lists, tables, code), show a clear loading spinner while waiting for a reply, and separate the message list from the input area visually.

## Requirements

- Assistant messages (and the static greeting) render **full Markdown**: headings, emphasis, lists, tables, fenced/inline code.
- User messages stay plain text (no Markdown parsing).
- HTML from Markdown is sanitized before `v-html` (XSS-safe).
- While `isLoading` is true, show a typing/loading bubble with a spinner (not only italic “Друкує…”).
- Message area background differs from the input bar (`bg-gray-50` vs white + clearer top border).
- Assistant bubbles may be wider (`max-w-[92%]`) so tables remain readable.
- Send/reset remain disabled while loading (existing behavior).

## Non-goals

- Code syntax highlighting (e.g. highlight.js).
- Streaming / token-by-token replies.
- Backend or API contract changes.
- Changing chat FAB position or dashboard FAB stacking.
- Markdown in user messages.

## Approach

**`marked` + `DOMPurify` + Tailwind utility styles** inside a small presentational component.

Alternatives considered:

| Option | Verdict |
|--------|---------|
| `marked` + `DOMPurify` | Chosen — small, secure, enough for full MD |
| `markdown-it` + plugins | Heavier config for same outcome |
| Vue markdown component wrappers | Less control over sanitization/styles |

## Architecture

```
frontend/
  package.json                          # + marked, dompurify
  src/components/chat/
    ChatWidget.vue                      # layout, loading bubble, wires ChatMarkdown
    ChatMarkdown.vue                    # marked → DOMPurify → v-html + prose-like classes
```

### ChatMarkdown.vue

- Props: `content: string`
- Pipeline: `marked.parse(content)` → `DOMPurify.sanitize(html)` → `v-html`
- Scoped/parent Tailwind targets for `h2`/`h3`, `p`, `ul`/`ol`, `table`/`th`/`td`, `code`/`pre`, `strong`/`em`, `a` (if links allowed — open in new tab or strip `href` per sanitizer config; prefer allow safe http(s) links with `rel="noopener noreferrer"`).
- No business logic; pure presentational.

### ChatWidget.vue changes

- Replace plain `{{ message.content }}` for `role === 'assistant'` with `<ChatMarkdown :content="message.content" />`.
- Greeting uses `<ChatMarkdown :content="GREETING" />` (plain text still fine through the same path).
- User bubbles unchanged (`{{ message.content }}`).
- Loading row: left-aligned gray bubble containing Lucide `Loader2` with `animate-spin` + short label (e.g. «Думаю…» or keep «Друкує…»).
- List container: add `bg-gray-50`; form/footer stay white with stronger `border-t border-gray-200`.

## Data flow

Unchanged API flow. Only the render path for assistant content changes:

1. User sends → `isLoading = true` → spinner bubble.
2. `POST /chat/` returns `reply`.
3. Push `{ role: 'assistant', content: reply }` → `ChatMarkdown` renders sanitized HTML.
4. `isLoading = false`.

## Error handling

- Existing error path unchanged (pop user message, restore draft, show red error text).
- If Markdown parse/sanitize throws (unlikely), fall back to plain escaped text in `ChatMarkdown` so the widget never blanks.

## Dependencies

- `marked`
- `dompurify`
- Types: use package built-in types or `@types/dompurify` if needed for the toolchain (Vite/Vue; no strict TS project today — add types only if install/docs recommend).

## Testing / verification

Manual:

1. Ask a question that returns headers + table (tax summary) → rendered, not raw `##` / `|`.
2. Bold/lists/code look styled inside the gray bubble.
3. Send message → spinner bubble appears until reply; send button disabled.
4. Message list vs input visually separated.
5. User message with `**text**` still shows literal asterisks (no MD).

## Out of scope follow-ups

- Syntax highlighting.
- Streaming UI.
- Shared design tokens / `@tailwindcss/typography` plugin (optional later if prose classes grow).
