# Design — The Lenny Growth Assistant

Status: v1 (Phase 1, pre-implementation) · Companion docs: [`PRD.md`](PRD.md), [`architecture.md`](architecture.md)

This is the UX system the frontend gets built and reviewed against. It covers principles,
layout, type, color, components, states, and accessibility. Every visual choice should trace
back to the user's job: **find what operators actually said, verify it, and turn it into
something usable.**

## 1. Design stance

The product is a **research desk**, not a chatbot toy. The references are editorial tools and
well-set long-form reading: a good newspaper's article page, a legal research tool, a writer's
editor. The chat metaphor is kept only where it helps, as a turn-by-turn record of questions and
answers.

### Principles

1. **The conversation is the product.** Everything else is secondary chrome and gets out of the
   way until needed.
2. **Hierarchy through type and space, not boxes.** No bubbles, no cards around messages. A
   question reads like a heading, an answer reads like an article paragraph, and sources read like
   footnotes.
3. **Evidence is first-class but quiet.** Citation markers are small, numbered, and always there.
   The source list sits under the answer like footnotes. Excerpts appear on demand.
4. **Honesty in every state.** Loading text names the real stage. Errors say what failed and
   what to do. An uncited answer is visibly marked. Nothing is shown that the system didn't
   actually measure.
5. **Working surfaces appear when there's work.** The artifact viewer doesn't exist on screen
   until there's an artifact.
6. **Restraint is the default.** Every icon, border, color, and badge has to justify itself. If it
   doesn't help the user decide or act, it goes.

### Explicitly not doing

Purple/blue gradients, glassmorphism, gradient blobs, sparkle/magic iconography, hero sections,
message bubbles, cards around every section, statistics or "insights" panels, token/confidence
meters, activity feeds, avatars for the assistant, pill clusters, decorative empty panels, and
"AI-powered" copy.

## 2. Layout

### Desktop (≥ 1100 px)

```
┌──────────┬──────────────────────────────────────┬───────────────────────────────┐
│ Sessions │  Conversation                         │  Artifact viewer (only when   │
│ (240px)  │  reading column max 68ch, centered    │  an artifact is open)         │
│          │                                       │  ~44% width, min 420px        │
│ New      │  Q: question as a heading line        │  Title          Preview|Source│
│ ──────   │  Answer paragraphs with ¹ ² markers   │  ─────────────────────────────│
│ Today    │  Sources                              │                               │
│  item    │   1  Guest — Episode · 00:41:12       │   rendered document           │
│  item    │   2  …                                │                               │
│ Earlier  │                                       │                               │
│  item    │  ─────────────────────────────────── │                               │
│          │  Composer                             │                               │
│          │  Ask · Essay · Document   local·model │                               │
└──────────┴──────────────────────────────────────┴───────────────────────────────┘
```

- The **sessions rail** is quiet: a text list with a hairline right rule. It can be collapsed
  (`Ctrl/⌘ + \`), and collapse state is remembered per browser.
- The **conversation column** stays at a comfortable measure (~68ch) whether or not the viewer is
  open. When the viewer opens, the column re-centers in the remaining space instead of stretching.
- The **artifact viewer** slides in from the right, separated by a hairline rule, not a shadow.
  Closing it (`Esc` or the Close control) returns the full width to the conversation.

### Tablet (700–1099 px)

The rail becomes an off-canvas drawer opened from a "Sessions" text button. The viewer, when open,
takes the full content width, and a "Back to conversation" control returns to chat.

### Mobile (< 700 px)

Single column. The viewer is a full-screen layer with its own header. The composer stays pinned to
the bottom and respects safe-area insets. Source excerpts expand inline.

## 3. Typography

Two families with distinct jobs, self-hosted through `@fontsource` packages. No third-party font
requests, and it works offline.

| Role | Family | Why |
| --- | --- | --- |
| Reading (assistant answers, artifact Markdown) | **Source Serif 4** | A reading face made for screens. Makes long answers read like articles. |
| Interface (questions, controls, rail, metadata) | **IBM Plex Sans** | Neutral, technical, legible at small sizes. Reads differently from the serif, so questions and answers never blur. |
| Data (timestamps, source code view, model names) | **IBM Plex Mono** | Tabular alignment for timestamps. Honest "this is data" signal. |

Fallback stacks: `"Source Serif 4", Georgia, "Times New Roman", serif` ·
`"IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif` ·
`"IBM Plex Mono", ui-monospace, "SFMono-Regular", Consolas, monospace`.

### Scale (rem, base 16px)

| Token | Size / line-height | Use |
| --- | --- | --- |
| `--text-xs` | 0.75 / 1.4 | Timestamps in lists, keyboard hints |
| `--text-sm` | 0.8125 / 1.45 | Metadata, source list, rail items, composer controls |
| `--text-base` | 0.9375 / 1.5 | UI text, question text |
| `--text-read` | 1.0625 / 1.65 | Answer body (serif) |
| `--text-lg` | 1.25 / 1.35 | Question as heading line, viewer title |
| `--text-xl` | 1.5 / 1.25 | Empty-state title only |

No heading larger than `--text-xl` anywhere in the app chrome. Weights: 400 and 600 (sans), 400
and 600 (serif). Italics only for quoted speech in answers.

## 4. Color

A warm paper ground, ink text, and **one** accent. The accent is reserved for things that are
interactive or evidentiary: citation markers, links, the focus ring, and the primary send action.

| Token | Light | Dark | Use |
| --- | --- | --- | --- |
| `--paper` | `#F8F6F1` | `#161513` | App background |
| `--paper-raised` | `#FFFFFF` | `#1E1C19` | Composer field, viewer document surface |
| `--ink` | `#1D1B18` | `#ECE8E1` | Primary text |
| `--ink-2` | `#55514A` | `#B3ADA3` | Secondary text, metadata |
| `--ink-3` | `#716C63` | `#948E84` | Tertiary: timestamps, hints |
| `--rule` | `#E4DFD5` | `#2E2B27` | Hairlines and separators |
| `--accent` | `#A8401E` | `#E0805C` | Citation markers, links, focus, send |
| `--accent-wash` | `#F3E4DC` | `#3A2419` | Highlighted source row, selected session |
| `--notice` | `#7A5A00` | `#D9B55A` | Uncited-answer and fallback notices (text only) |
| `--danger` | `#9B1C1C` | `#F08A8A` | Errors (text + a thin left rule, never a filled red block) |
| `--ok` | `#2F6B3A` | `#7FC08A` | Provider-ready dot only |

The accent is a burnt vermilion, warm and editorial. It avoids the usual AI-product blues and
purples. Dark mode follows `prefers-color-scheme`.

**Contrast (WCAG 2.2, computed in Phase 1).** All text tokens pass AA (≥ 4.5:1) on both `--paper`
and `--paper-raised` in both themes:

| Token | Light (paper / raised) | Dark (paper / raised) |
| --- | --- | --- |
| `--ink` | 15.91 / 17.18 | 14.94 / 13.92 |
| `--ink-2` | 7.30 / 7.89 | 8.19 / 7.63 |
| `--ink-3` | 4.83 / 5.21 | 5.61 / 5.23 |
| `--accent` | 5.69 / 6.15 (4.96 on `--accent-wash`) | 6.44 / 6.00 (5.12 on wash) |
| `--notice` | 5.91 / 6.38 | 9.30 / 8.67 |
| `--danger` | 7.55 / 8.15 | 7.57 / 7.05 |

The first draft had `--ink-3` at 3.4:1, which fails for small text. It was darkened before
implementation.

## 5. Spacing and rules

- Base unit 4px. Scale: 4, 8, 12, 16, 24, 32, 48, 64.
- Separation between turns: 48px of space plus a hairline `--rule`. Space carries most of the
  structure, and the rule marks the turn boundary.
- Radii: 6px on the composer field and buttons, 0 on everything else. Content is never inside a
  rounded container.
- Shadows: none. Layering (viewer, drawer, mobile sheet) uses hairline rules and `--paper-raised`.

## 6. Components

### 6.1 Turn

- **Question:** sans, `--text-lg`, 600 weight, `--ink`, no container. Above it on the left, a
  small metadata line in `--ink-3` shows the time only (e.g., `14:02`).
- **Answer:** serif `--text-read` paragraphs. Markdown supported (lists, bold, short tables).
  Headings inside answers are capped at `--text-base` 600 so they never compete with the question.
- **Answer footer line** (sans `--text-sm`, `--ink-3`): `Grounded answer · 5 sources · qwen3:4b-instruct (local)`.
  Skill name, real source count, and the model that actually answered. For a fallback:
  `· answered by claude-sonnet-5 after Ollama was unavailable` in `--notice`.
- **Actions** on hover/focus of the turn (text buttons, no icons): `Copy` · `Open document`
  (when there's an artifact).

### 6.2 Citations

- Inline markers render as superscript numerals in `--accent` (`¹`, as `<sup><a>`). Each links to
  its source row, and the target briefly gets `--accent-wash`.
- **Sources list** below the answer, labeled "Sources" in `--text-sm` 600 small caps:

  ```
  1  Brian Chesky — Brian Chesky's new playbook             00:41:12 ↗
     ▸ Excerpt
  ```

  Number (mono), guest (600), episode title (`--ink-2`), timestamp (mono, `--ink-3`), and an
  external-link glyph that opens YouTube at that second in a new tab (the glyph is there because it
  tells the user the link leaves the app). `Excerpt` is a disclosure. It reveals the exact retrieved
  text with its speaker label and timestamp, so the user can verify the claim without leaving.
- Only cited sources are listed. Retrieved-but-uncited chunks aren't padded in to look thorough.
- **Uncited answer:** a `--notice` line above the sources position: "This answer doesn't cite
  transcript evidence. Treat it as unverified." No sources list.
- **Insufficient evidence:** the answer states it plainly. Where retrieval found weakly related
  episodes, it offers "The closest material is in …" with those episodes as normal links. They're
  never presented as support.

### 6.3 Composer

- A textarea on `--paper-raised` with a 1px `--rule` border (the one place a bordered field is
  earned: it's the input). Auto-grows to 8 lines, then scrolls.
- `Enter` sends, `Shift+Enter` adds a newline, `Ctrl/⌘+K` focuses the composer from anywhere.
- **Mode control** under the field as a text segmented control: `Ask · Essay · Document`. The
  active mode is underlined in `--accent`. The placeholder changes with the mode ("Ask about product
  and growth…", "Topic for a Ship 30 for 30 essay…", "Describe the document to create…"). Mode maps
  directly to the API `mode`. `Ask` is `auto`, so natural requests still route correctly.
- **Model indicator** on the right, `--text-sm` mono: `● local · qwen3:4b-instruct`. The dot is
  `--ok` when ready and `--danger` when not, and it isn't the only signal: the text reads
  `unavailable` when not ready. With more than one provider configured, it's a menu listing each
  provider, its model, and readiness. Unavailable options are disabled and show the reason
  ("Ollama not reachable", "API key not set").
- **Send** is a text button, "Send", in `--accent`. While a turn runs, it becomes "Stop" (cancels
  the stream client-side) and the textarea stays editable.

### 6.4 Sessions rail

- "New conversation" text button at the top (`Ctrl/⌘+Shift+O`).
- Grouped by real dates: "Today", "Yesterday", "Previous 7 days", "Older". Item label is the
  session title (first question, truncated). The active item gets `--accent-wash` and 600 weight.
- Delete on hover/focus shows a confirm step inline ("Delete · Cancel"), not a modal.
- Empty rail: nothing but the New conversation button. No placeholder illustration.

### 6.5 Artifact viewer

- **Header:** title (sans `--text-lg` 600, truncates), kind in `--ink-3` ("Markdown" / "HTML
  document"), and on the right the text controls `Preview | Source`, `Copy`, `Download`, `Close`.
- **Preview:** Markdown renders in the reading styles on `--paper-raised` at a document measure.
  HTML renders in the sandboxed iframe (architecture §10) sized to the pane.
- **Source:** mono, line numbers, horizontal scroll, and read-only. For HTML this shows the
  *sanitized* document, with a one-line note when the sanitizer removed content:
  "Removed for safety: 2 scripts, 1 external stylesheet."
- **Provenance line** under the header: "Generated from 9 sources in this conversation" linking back
  to the originating turn. The count is real.
- **Generated-content label:** a persistent small `--ink-3` line at the top of the HTML preview,
  "Generated document · scripts and external resources are disabled". It signals the frame is
  untrusted and discourages trusting fake UI drawn inside it.
- **Multiple artifacts:** the header title is a menu listing this session's artifacts, newest first.
- **Render failure:** the preview area is replaced with the error text, and the viewer switches to
  Source automatically so the content is still reachable.

## 7. States

| State | What the user sees |
| --- | --- |
| **First visit, knowledge base ready** | Empty state in the conversation column: one line title "Research Lenny's Podcast", one sentence on what it does and that answers cite episodes and timestamps, the real corpus size ("269 episodes, indexed from the public transcript archive"), then 4 starter questions as plain text links. Starters must be verified in Phase 9 to return grounded answers. |
| **Knowledge base empty** | Same position: "The transcript index is empty." plus the exact command (`make ingest`, or the docker compose equivalent) in mono, and a link to README setup. Composer disabled with the reason stated. |
| **Provider unavailable** | Model indicator shows `unavailable`. Above the composer, one `--danger` line with the specific reason and fix ("Ollama isn't reachable. Start it with `ollama serve`."). Composer disabled only if *no* provider is ready. |
| **Turn in progress** | Directly under the question, a single `--ink-2` status line reflecting the real stage from SSE events: "Searching transcripts…" → "Found 8 passages across 5 episodes. Writing with qwen3:4b-instruct…" → streamed text. A subtle animated ellipsis is the only motion. No skeleton blocks and no fake progress bar. For essays: "Essays take longer on local models." (a fact, stated once). |
| **Turn failed** | The question stays. Under it, `--danger` text with a thin left rule: message + hint from the error envelope, plus a `Retry` text button. The failure persists in history. |
| **Insufficient evidence** | Normal answer styling (it's a legitimate answer), with footer line `No supporting evidence found`. |
| **Session not found** (stale link) | Conversation column: "This conversation doesn't exist or was deleted." plus "Start a new conversation". |
| **Database unavailable** | Full-width top line in `--danger`: "Can't reach the database. Conversations can't be loaded or saved." The rest of the UI stays visible but inert. |

Motion: 150ms ease-out for viewer open/close and disclosure. Everything honors
`prefers-reduced-motion` (no motion at all).

## 8. Content and voice

- Plain, specific, and short. Say what happened and what to do.
- No "AI", "magic", "powered by", "insights", "supercharge". The product is "the assistant" at most,
  and usually unnamed.
- Numbers only when true and measured (source counts, corpus size from the database).
- Timestamps as `HH:MM:SS` in mono. Dates as "12 Nov 2023".

## 9. Accessibility

- Landmarks: `nav` (sessions), `main` (conversation), `aside` (artifact viewer, labeled with the
  artifact title).
- The live conversation region is `aria-live="polite"` for stage lines and completion. Streamed
  tokens are **not** announced one by one: the full answer is announced when done.
- All controls reachable and operable by keyboard. Visible focus ring: 2px `--accent` outline with
  2px offset. Never removed.
- Citation markers have accessible names ("Source 1: Brian Chesky, Brian Chesky's new playbook,
  41 minutes 12 seconds").
- The sandboxed iframe gets a `title` ("Generated document preview: <title>").
- Status is never communicated by color alone (provider dot has text, errors have text).
- Hit targets ≥ 32px on desktop, ≥ 44px on touch layouts.
- Contrast checked against WCAG 2.2 AA in both themes (Phase 9 checklist).

## 10. Review checklist (used in Phases 9 and 13)

- [ ] Can a first-time user ask a question within 5 seconds of load without reading instructions?
- [ ] Does every number on screen come from real data?
- [ ] Is there any container, border, icon, or badge that can be removed without losing meaning?
- [ ] Do questions, answers, and sources read as three distinct levels at a glance?
- [ ] Is every citation one click from its verbatim excerpt and one more from the video moment?
- [ ] Does the viewer appear only when there's an artifact, and close cleanly?
- [ ] Does every error state say what failed and what to do?
- [ ] Keyboard-only walkthrough of the full workflow succeeds.
- [ ] Layout verified at 375px, 768px, 1280px, and 1600px wide, light and dark.
- [ ] Nothing on screen reads as an "AI demo".
