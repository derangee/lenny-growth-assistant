# Architecture — The Lenny Growth Assistant

Status: v1 (Phase 1, pre-implementation) · Companion docs: [`PRD.md`](PRD.md), [`design.md`](design.md),
[`docs/assessment.md`](docs/assessment.md), [`docs/spikes/001-agent-sdk-ollama`](docs/spikes/001-agent-sdk-ollama/README.md)

This document is the design the implementation phases build against. Where a phase learns something
that changes a decision here, the change and its reason get recorded in §14.

## 1. Guiding decisions

1. **Grounding is enforced by code, not requested from the model.** Retrieval runs
   deterministically before generation. Citations get validated against the evidence actually
   retrieved for that turn. Spike 001 showed a 4B model will skip tool calls and still cite evidence
   it never saw.
2. **One database.** PostgreSQL holds sessions, messages, artifacts, the transcript corpus,
   full-text indexes (`tsvector`), and vectors (`pgvector`). At ~10–30k chunks a separate vector
   store buys nothing and adds another service to break.
3. **Provider-agnostic generation through one wire format.** Anthropic and Ollama both speak the
   Anthropic Messages API, so switching providers means changing base URL, auth, and model name. The
   Claude Agent SDK is the runtime.
4. **Deterministic, explainable routing.** Skill selection is explicit (the user picks a mode) or
   rule-based. It isn't delegated to a small model's judgment. Every reply records which skill ran.
5. **Generated HTML is hostile.** It gets sanitized on the server and rendered in a script-less,
   origin-less sandboxed iframe under a restrictive CSP. Either layer alone should stop script
   execution.
6. **Fail loudly and specifically.** Every dependency failure maps to a typed error code, a
   human-readable message, a remediation hint, and a structured log line with a request ID.

## 2. System overview

```
 Browser (React SPA)
   │  same-origin HTTP  (/api/*, SSE for replies)
   ▼
 web ─ nginx ──────────────────────────────────────────────── container: web
   │  serves static build · proxies /api → api:8000 · buffering off for SSE
   ▼
 FastAPI application ─────────────────────────────────────── container: api
   │
   ├── API layer ........... routers, Pydantic request/response schemas, error envelope,
   │                         request-ID + access-log middleware, health endpoints
   │
   ├── Conversation service  session lifecycle, message persistence, history window,
   │                         turn orchestration, artifact persistence
   │
   ├── Agent layer
   │     ├── Router .......... explicit mode → rules → default (grounded answer)
   │     ├── Skills
   │     │     ├── grounded_answer   Q&A + follow-ups over retrieved evidence
   │     │     ├── ship30_essay      ~1,250-word Ship 30 for 30 essay (+ validator, revision pass)
   │     │     └── artifact          Markdown / HTML-CSS documents
   │     ├── Evidence ledger ..... numbered evidence per turn ([S1]..[Sn] → chunk IDs)
   │     └── Citation validator .. strips labels not in the ledger, computes coverage
   │
   ├── Knowledge layer
   │     ├── Retriever ....... hybrid: Postgres full-text + pgvector, reciprocal rank fusion,
   │     │                     per-episode diversity cap, relevance gate
   │     ├── Embedder ........ in-process ONNX model (fastembed, bge-small-en-v1.5, 384-d)
   │     └── Ingestion CLI ... acquire → parse → normalize → chunk → embed → index → record run
   │
   ├── Model layer
   │     ├── Provider registry  profiles from env: ollama, anthropic (+ readiness probes)
   │     ├── Runtime: ClaudeAgentSdkRuntime   (default)
   │     └── Runtime: MessagesApiRuntime      (fallback; direct /v1/messages over httpx)
   │
   └── Artifact security ... HTML sanitizer (nh3) + render envelope (CSP meta) + limits
         │
         ▼
 PostgreSQL 16 + pgvector ──────────────────────────────────── container: db
   sessions · messages · artifacts · episodes · chunks · ingestion_runs

 Model providers (outside the compose network)
   ├── Ollama   http://host.docker.internal:11434   (host install; optional compose profile)
   └── Anthropic API  https://api.anthropic.com      (requires ANTHROPIC_API_KEY)
```

Dependency direction points one way: `api → conversation → agent → (knowledge, model) → db/providers`.
Skills never touch HTTP or the ORM session directly. They get a retriever and a runtime through
their constructor. That's what lets them be unit-tested with fakes.

## 3. Technology choices

| Concern | Choice | Why | Rejected |
| --- | --- | --- | --- |
| API | FastAPI + Pydantic v2 | Required. Typed contracts, validation, OpenAPI. | — |
| Python | 3.12 (container) | Stable wheel availability for onnxruntime/pgvector/psycopg | 3.13 in container (wheel risk for no benefit) |
| ORM / migrations | SQLAlchemy 2.0 (async) + Alembic | Explicit schema, migrations evaluators can read | Raw SQL only (harder to evolve), SQLModel (thin benefit) |
| DB driver | psycopg 3 (async) | One driver for app, Alembic, and pgvector adapter | asyncpg (second driver for Alembic) |
| Database | PostgreSQL 16 + pgvector (`pgvector/pgvector:pg16` image) | Relational data, FTS, and vectors in one service | Chroma/Qdrant (extra service), SQLite (no pgvector, assessment wants Postgres) |
| Embeddings | fastembed (ONNX) `BAAI/bge-small-en-v1.5`, 384-d, in-process | CPU-fast, no GPU, and **independent of the chat provider**. The index doesn't depend on Ollama or Anthropic. | Ollama embeddings (index breaks if Ollama is down or the model is missing), Anthropic (no embeddings API), sentence-transformers (pulls in PyTorch, ~2 GB image) |
| Agent runtime | `claude-agent-sdk` (Python) | Required by assessment. Works with Anthropic and Ollama (spike 001). | Pi Coding Agent (Node-centric, less natural in a Python API) |
| Fallback runtime | httpx → `/v1/messages` | Same wire format, no subprocess. For environments where the bundled CLI can't run. | LangChain/LiteLLM (large abstraction for two endpoints) |
| HTML sanitizer | `nh3` (Rust ammonia bindings) | Allow-list sanitizer, fast, maintained | bleach (deprecated), regex (unsafe) |
| Logging | structlog → JSON to stdout | Structured, container-native, context-bound request IDs | stdlib text logs |
| Frontend | Vite + React 18 + TypeScript | Plain SPA. No SSR needed behind a local API. | Next.js (server features unused, heavier) |
| Styling | Hand-written CSS with design tokens (CSS custom properties) | Full control over an editorial look. Avoids the default component-kit aesthetic. | Tailwind + shadcn (tends toward the generic look `design.md` rejects) |
| Markdown | `react-markdown` + `remark-gfm`, no raw HTML | Safe by default. Raw HTML is never interpreted. | `dangerouslySetInnerHTML` with marked |
| Frontend tests | Vitest + React Testing Library | Vite-native | Jest (extra config) |
| Serving | nginx (static + reverse proxy) | Same-origin API (no CORS), SSE-friendly | Serving static files from FastAPI (mixes concerns) |

## 4. Repository layout

```
.
├── backend/
│   ├── app/
│   │   ├── main.py                 app factory, middleware, router registration
│   │   ├── config.py               pydantic-settings; single source of configuration
│   │   ├── logging.py              structlog setup, redaction
│   │   ├── errors.py               AppError hierarchy → error envelope
│   │   ├── api/                    routers: health, sessions, messages, artifacts, meta
│   │   ├── schemas/                Pydantic request/response models (API contracts)
│   │   ├── db/                     engine, session factory, ORM models
│   │   ├── services/               conversation service (turn orchestration)
│   │   ├── agent/                  router, evidence ledger, citations, skills/
│   │   │   └── skills/<name>/      SKILL.md (spec) + skill.py (implementation)
│   │   ├── knowledge/              source, parser, chunker, embedder, indexer, retriever
│   │   ├── llm/                    provider registry, runtimes, readiness probes
│   │   └── artifacts/              sanitizer, render envelope
│   ├── migrations/                 Alembic
│   ├── tests/                      unit/ (no services) · integration/ (Postgres)
│   ├── pyproject.toml              deps, ruff, mypy, pytest config
│   └── Dockerfile
├── frontend/
│   ├── src/                        app shell, conversation, sources, artifact viewer, api client
│   ├── index.html, vite.config.ts, package.json
│   ├── nginx.conf
│   └── Dockerfile                  multi-stage: build → nginx
├── docs/                           assessment, spikes, manual test plan, evaluation, agent transcripts
├── docker-compose.yml
├── Makefile                        convenience wrappers (macOS/Linux); docs also show raw commands
├── .env.example
├── README.md · PRD.md · design.md · architecture.md
```

## 5. Data model (PostgreSQL)

```
sessions
  id               uuid pk
  client_id        uuid  not null, indexed      -- anonymous browser identifier (no PII)
  title            text  null                   -- derived from the first user message (truncated)
  created_at       timestamptz not null default now()
  updated_at       timestamptz not null         -- bumped on every message

messages
  id               uuid pk
  session_id       uuid fk → sessions(id) on delete cascade
  role             text  check in ('user','assistant')
  content          text  not null
  status           text  check in ('complete','error')   -- assistant failures are persisted, visibly
  skill            text  null        -- grounded_answer | ship30_essay | artifact
  provider         text  null        -- ollama | anthropic
  model            text  null
  grounding        text  null        -- grounded | insufficient_evidence | uncited
  citations        jsonb not null default '[]'  -- snapshot: label, chunk_id, episode, speaker, ts, url, excerpt
  error            jsonb null        -- {code, message, hint}
  timings          jsonb null        -- {retrieval_ms, generation_ms, total_ms}
  created_at       timestamptz not null default now()
  index (session_id, created_at)

artifacts
  id               uuid pk
  session_id       uuid fk → sessions(id) on delete cascade
  message_id       uuid fk → messages(id) on delete cascade
  kind             text check in ('markdown','html')
  title            text not null
  content          text not null     -- render-safe content (sanitized for html)
  source           text not null     -- raw model output, kept for audit and "view source"
  sanitizer_report jsonb null        -- what was removed and why (counts by category)
  created_at       timestamptz not null default now()

episodes
  id               text pk           -- source folder slug, e.g. "brian-chesky"
  title, guest     text
  youtube_url      text null
  video_id         text null
  publish_date     date null
  duration_seconds int  null
  description      text null
  keywords         text[] not null default '{}'
  content_hash     text not null     -- sha256 of source file; drives incremental refresh
  source_ref       text not null     -- dataset commit SHA the row came from
  ingested_at      timestamptz not null

chunks
  id               text pk           -- "<episode_id>:<ordinal zero-padded>"
  episode_id       text fk → episodes(id) on delete cascade
  ordinal          int  not null
  start_seconds    int  not null
  end_seconds      int  null
  speakers         text[] not null
  text             text not null
  word_count       int  not null
  tsv              tsvector generated always as (to_tsvector('english', text)) stored   -- GIN index
  embedding        vector(384) not null                                                -- HNSW, cosine

ingestion_runs
  id               uuid pk
  source, source_ref, embedding_model   text
  status           text check in ('running','succeeded','failed')
  started_at, finished_at               timestamptz
  stats            jsonb             -- episodes seen/added/updated/unchanged/removed, chunks written
  error            text null
```

Notes:

- **Citations are snapshotted into the message.** History stays accurate after a corpus refresh
  changes or deletes chunks.
- **Assistant failures are stored** as `status='error'` messages with a typed error. Reloading a
  session shows what happened, instead of the message silently disappearing.
- **No user PII.** `client_id` is a random UUID the browser generates and keeps in `localStorage`.
  It scopes the session list. It isn't authentication (see §11).

## 6. API contracts

All routes are JSON and prefixed `/api`, except health. Requests are validated by Pydantic. Unknown
fields are rejected (`extra="forbid"`). The browser sends the client identifier as the
`X-Client-Id` header (UUID format validated).

| Method & path | Purpose | Success | Notable errors |
| --- | --- | --- | --- |
| `GET /health` | Liveness (process up) | 200 `{status:"ok"}` | — |
| `GET /health/db` | DB connectivity + migration state | 200 / 503 | `database_unavailable` |
| `GET /health/providers` | Per-provider readiness: reachable, model present, key configured | 200 (body reports each) | — |
| `GET /health/knowledge` | Episode/chunk counts, last ingestion run, embedding model match | 200 / 503 | `knowledge_base_empty`, `embedding_model_mismatch` |
| `GET /api/meta` | UI bootstrap: providers (name, model, ready), default provider, corpus stats | 200 | — |
| `POST /api/sessions` | Create session | 201 session | 422 validation |
| `GET /api/sessions` | List client's sessions, newest first | 200 | — |
| `GET /api/sessions/{id}` | Session + messages + artifact summaries | 200 | 404 `session_not_found` |
| `DELETE /api/sessions/{id}` | Delete session and its data | 204 | 404 |
| `POST /api/sessions/{id}/messages` | Send a message; reply streamed as SSE (or JSON with `Accept: application/json`) | 200 | 404, 422, 409 `turn_in_progress` |
| `GET /api/artifacts/{id}` | Full artifact (render-safe content + source) | 200 | 404 `artifact_not_found` |

**Send-message request:**

```json
{ "content": "How do the best teams think about activation?",
  "mode": "auto",            // auto | answer | essay | artifact
  "provider": "ollama" }     // optional; must be a configured provider, else default
```

**Reply SSE events** (all JSON). Every event is emitted for real, never simulated:

| Event | When | Payload |
| --- | --- | --- |
| `turn.started` | User message persisted | `{user_message_id, skill, provider, model}` |
| `retrieval.completed` | Retrieval finished | `{evidence_count, episodes: n}` |
| `answer.delta` | Model output chunk (if the runtime streams), otherwise one final chunk | `{text}` |
| `artifact.created` | Artifact stored | `{artifact_id, kind, title}` |
| `turn.completed` | Assistant message persisted | full assistant message (content, citations, grounding, timings) |
| `turn.failed` | Any failure after start | `{code, message, hint, assistant_message_id}` |

**Error envelope** (all non-2xx):

```json
{ "error": { "code": "provider_unavailable",
             "message": "Ollama is not reachable at http://host.docker.internal:11434.",
             "hint": "Start Ollama (`ollama serve`) or set LLM_PROVIDER=anthropic.",
             "request_id": "5f0c…" } }
```

Error codes (the stable set; extended only deliberately): `validation_error`, `session_not_found`,
`artifact_not_found`, `turn_in_progress`, `database_unavailable`, `knowledge_base_empty`,
`embedding_model_mismatch`, `provider_not_configured`, `provider_unavailable`, `model_not_found`,
`model_timeout`, `provider_error`, `malformed_model_output`, `artifact_generation_failed`,
`internal_error`.

## 7. Knowledge layer

### 7.1 Ingestion pipeline

```
acquire ──► parse ──► normalize ──► chunk ──► embed ──► index ──► record run
```

| Stage | Behaviour |
| --- | --- |
| **Acquire** | Download `codeload.github.com/ChatPRD/lennys-podcast-transcripts/tar.gz/<SHA>` into a cache volume. SHA comes from `TRANSCRIPTS_SOURCE_REF` (pinned default). `--source-dir` uses a local checkout instead (offline). |
| **Parse** | Split YAML frontmatter from body. Parse speaker turns with the pattern `^(?P<speaker>.+?) \((?P<ts>\d{1,2}:\d{2}:\d{2})\):$`, then the utterance lines. Files that fail parsing are reported per file and skipped, never guessed at. |
| **Normalize** | Unicode NFC, collapse whitespace, strip empty turns, convert timestamps to seconds, validate required metadata (title, at least one turn). |
| **Chunk** | Speaker-turn-aware packing (§7.2). |
| **Embed** | Embedding input = `"{title} — {guest}\n{speakers}: {text}"` (the header gives context to short chunks). Stored text excludes the header. Batched. |
| **Index** | Per episode in one transaction: skip if `content_hash` unchanged, else delete and reinsert the episode's chunks. Episodes missing from the source are deleted (`--no-prune` to keep). |
| **Record** | `ingestion_runs` row with stats, source ref, embedding model, and status. Failures mark the run `failed` with the error. |

Command: `docker compose run --rm api python -m app.knowledge.ingest [--limit N] [--episodes slug,…] [--source-dir PATH]`
(wrapped as `make ingest`). Idempotent. Re-running with no source changes writes nothing.

**Refresh:** bump `TRANSCRIPTS_SOURCE_REF` and re-run ingestion. Only changed episodes get
re-embedded. Changing `EMBEDDING_MODEL` needs `--rebuild`. The API refuses retrieval with
`embedding_model_mismatch` rather than silently comparing vectors from different models.

### 7.2 Chunking strategy

- **Unit:** consecutive speaker turns packed to a target of **~300 words** (hard max ~450). One
  chunk usually holds a question-and-answer exchange, which keeps the claim and its context together.
- **Long turns** (monologues over the max) get split on sentence boundaries. Each piece keeps the
  turn's speaker and start timestamp.
- **Overlap:** the last turn (or last ~60 words of a split turn) is repeated at the start of the next
  chunk. Answers that straddle a boundary stay retrievable.
- **Provenance per chunk:** episode ID, title, guest, speakers present, start/end seconds, ordinal,
  deep link `https://www.youtube.com/watch?v=<video_id>&t=<start_seconds>s`.
- **Why not fixed token windows:** they cut through speaker turns, so a citation could credit a claim
  to the wrong person. Speaker attribution is part of what makes a citation trustworthy.

Parameters are provisional. Phase 4 checks them against a labeled hit-rate set, and any change gets
recorded in §14.

### 7.3 Retrieval

1. **Query construction.** The current user message. For follow-ups (short messages, anaphora such
   as "that", "they", "what about"), the previous user message gets appended, so "what about for
   B2B?" retrieves in the context of the earlier question. Deterministic, no extra model call.
2. **Lexical leg.** `websearch_to_tsquery('english', q)` against `tsv`, ranked by `ts_rank_cd`, top 40.
3. **Semantic leg.** Cosine distance on `embedding` (HNSW), top 40.
4. **Fusion.** Reciprocal rank fusion (`k=60`). Handles both jargon matches ("NPS", "PLG") and
   paraphrases.
5. **Diversity.** At most 3 chunks per episode in the final set, so one long episode can't crowd
   out the rest.
6. **Relevance gate.** If the best semantic similarity is below `RETRIEVAL_MIN_SIMILARITY` *and* the
   lexical leg matched nothing, retrieval returns **empty**. The skill then answers with
   insufficient evidence **without calling the model**. The threshold gets calibrated in Phase 4
   against in-corpus and out-of-corpus questions.
7. **Budget.** Final k: 8 for answers, 14 for essays, 10 for artifacts. Each skill sets its own.

## 8. Model layer

### 8.1 Provider profiles (configuration only)

```
LLM_PROVIDER=ollama                 # default provider: ollama | anthropic
LLM_FALLBACK_PROVIDER=              # optional; used only when the default is unavailable
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen3:4b-instruct
ANTHROPIC_API_KEY=                  # secret; never logged, never sent to the browser
ANTHROPIC_MODEL=claude-sonnet-5
AGENT_RUNTIME=claude_agent_sdk      # claude_agent_sdk | messages_api
LLM_TIMEOUT_SECONDS=180
```

A **profile** is `{name, base_url, auth, model, max_output_tokens}`. The registry builds profiles
from env at startup and validates them. An invalid configuration fails fast at boot with a message
naming the variable. Model names exist only in configuration. `GET /api/meta` exposes profile
name, model, and readiness (never secrets), and the UI shows the active one. A per-message
`provider` field lets a user switch between *configured* providers without redeploying.

### 8.2 Runtimes

```python
class ModelRuntime(Protocol):
    async def generate(self, profile: ProviderProfile, request: GenerationRequest) -> AsyncIterator[GenerationEvent]: ...
```

- `ClaudeAgentSdkRuntime` (default): `query()` with the skill's system prompt, `tools=[]`,
  `setting_sources=[]`, `max_turns=1`, and env mapped from the profile
  (`ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`/`ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`). Partial
  messages stream as `answer.delta` where supported.
- `MessagesApiRuntime` (fallback): the same request shape posted to `{base_url}/v1/messages`.
- Both map failures to typed errors: connection refused → `provider_unavailable`; 404 model →
  `model_not_found`; timeout → `model_timeout`; 401/403 → `provider_not_configured`; other →
  `provider_error`.

### 8.3 Readiness and fallback

- Ollama readiness: `GET {base}/api/tags` reachable **and** the configured model is listed.
  Otherwise the hint includes `ollama pull <model>`.
- Anthropic readiness: key present (format check only, no billable call on health checks).
- Fallback: if the chosen provider fails *before any output was streamed* with
  `provider_unavailable`/`model_not_found`, and `LLM_FALLBACK_PROVIDER` is set and ready, the turn
  retries once on the fallback. The reply records the provider that actually answered, and the UI
  says a fallback was used. No silent switching, and never a switch after partial output.

## 9. Agent layer

### 9.1 Turn orchestration

```
POST message
  → validate + persist user message (turn lock per session)
  → Router.select(mode, content, history)            → skill
  → skill.plan_retrieval(content, history)           → queries, k
  → Retriever.search(...)                            → evidence (may be empty)
  → EvidenceLedger(evidence)                         → [S1]..[Sn]
  → if empty and skill requires evidence             → insufficient-evidence reply (no model call)
  → skill.build_prompt(ledger, history, content)     → system + messages
  → Runtime.generate(profile, prompt)                → streamed text
  → skill.postprocess(text, ledger)                  → citations validated, artifact extracted/validated
  → persist assistant message (+ artifact)           → turn.completed
```

### 9.2 Router

1. `mode` explicit (`answer` / `essay` / `artifact`) → that skill. The UI exposes these, so users
   control routing when it matters.
2. `mode=auto` → ordered rules on the message:
   - Ship 30 intent: "ship 30", "atomic essay", "essay", "write a post/article about" → `ship30_essay`
   - Artifact intent: create/make/generate/turn … into a "one-pager", "document", "doc", "brief",
     "report", "checklist", "playbook", "html", "page", "markdown" → `artifact`
   - Otherwise → `grounded_answer`
3. The decision (and which rule matched) goes into the reply and the logs. Rules are table-driven
   and unit-tested with positive and negative examples.

A model-based classifier was considered and rejected for v1. It adds a model call per turn, and on
a 4B model it's less predictable than rules. Explicit mode covers the ambiguous cases.

### 9.3 Skills

Each skill lives in `app/agent/skills/<name>/`:

- `SKILL.md`: the human-readable specification. Purpose, inputs, grounding rules, output format,
  validation criteria. The system prompt gets assembled from it, so behaviour and documentation
  can't drift apart.
- `skill.py`: `plan_retrieval`, `build_prompt`, `postprocess`, `validate`.

| Skill | Retrieval | Output | Validation |
| --- | --- | --- | --- |
| `grounded_answer` | k=8, follow-up-aware query | Prose answer with `[S#]` labels; or the insufficient-evidence form | Citation validity; coverage; decline detection |
| `ship30_essay` | k=14, topic query plus 2 sub-queries derived from the topic | Markdown essay → stored as Markdown artifact + short chat summary | Word count 1,000–1,500; H1 headline; intro; N sections matching the headline's number; takeaway section; ≥ 5 valid citations. One revision pass on failure, then returned with any unmet checks listed. |
| `artifact` | k=10 on the request (or reuses the previous turn's evidence for "turn this into…") | Markdown or complete HTML/CSS document → stored artifact + short chat summary | Kind detected; HTML parseable with `<body>` content; sanitized; size limit; citations validated |

### 9.4 Citations

- The prompt presents evidence as numbered blocks: `[S3] Brian Chesky — "Brian Chesky's new playbook" (00:41:12)`.
- The model is told to cite with `[S#]` only.
- `CitationValidator` parses labels, keeps those in the ledger, and removes the rest (logged as
  `citations_invalid`). It renumbers into reader order (`[1]`, `[2]`…) and snapshots provenance into
  `messages.citations`.
- `grounding` status: `grounded` (≥1 valid citation), `insufficient_evidence` (decline form), or
  `uncited` (substantive text with no valid citation). The UI shows `uncited` answers with a visible
  notice. They aren't hidden, and they aren't passed off as grounded.
- Quotes: text inside quotation marks attributed to a guest must appear verbatim (after whitespace
  normalization) in a cited chunk. Otherwise the quote marks are removed and the event is logged.
  Paraphrase is allowed. Fabricated verbatim quotes aren't.

### 9.5 Conversation context

- History window: the last 6 messages (3 exchanges), truncated to a character budget, go into the
  prompt. Older context gets dropped rather than summarized. That's predictable and cheap on local
  models.
- Sessions share nothing. All queries filter by `session_id`.
- One active turn per session (row-level lock). A concurrent send returns `409 turn_in_progress`.

## 10. Artifact generation and isolation

### 10.1 Pipeline

```
model output → extract (fenced block / document) → classify kind → validate
  → markdown: store as-is (rendered safely on the client, raw HTML disabled)
  → html:     sanitize (nh3) → wrap in render envelope → store content + source + report
```

### 10.2 HTML defense in depth

| Layer | Mechanism | Stops |
| --- | --- | --- |
| 1. Server sanitization | `nh3` allow-list: structural/text/table/list/semantic tags, `<style>`, `class`/`style`/`id` attributes. **Removed:** `<script>`, `<iframe>`, `<object>`, `<embed>`, `<form>`/inputs, `<link>`, `<meta>`, `<base>`, SVG/MathML, all `on*` handlers, and `href`/`src` with non-`https:` schemes (so `javascript:` and `data:` in links are gone). CSS `@import` and `url()` referencing non-`data:` resources are stripped. | Script injection, phishing forms, external loads, clickjacking containers |
| 2. Render envelope | Server-built document: `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; font-src data:; form-action 'none'; base-uri 'none'">` placed first in `<head>`, followed by the sanitized content | Anything the sanitizer misses gets no network and no script source |
| 3. Sandboxed iframe | `<iframe sandbox srcdoc=…>` with **no** `allow-scripts`, **no** `allow-same-origin`, no forms, no top navigation. Only `allow-popups allow-popups-to-escape-sandbox` so citation links can open in a new tab on user click. `referrerpolicy="no-referrer"`. | Script execution even if layers 1–2 fail. Opaque origin means no access to the app's cookies, storage, or DOM. |
| 4. App CSP (nginx) | `default-src 'self'; frame-src 'self' about:; object-src 'none'; base-uri 'self'` on the SPA | Limits the damage if anything escapes into the app itself |
| 5. Limits | HTML artifacts capped at 300 KB; reject documents with no renderable body | Resource abuse, blank renders |

**Markdown** is rendered with `react-markdown` **without** `rehype-raw`, so embedded HTML shows up as
text. Links are limited to `http(s):`/`mailto:` and open with `rel="noopener noreferrer"`. Remote
images aren't loaded (they'd be tracking beacons). Their alt text and URL show instead.

**Known limitations (documented, accepted):** CSS alone can still make visually deceptive content
(fake UI inside the frame), so the viewer frame is clearly labeled as generated content. Links
opened from the frame go to arbitrary `https:` URLs the model wrote. The sanitizer is only as good
as nh3's parser, which is why the iframe sandbox is the real boundary. Tests include an XSS payload
corpus (script tags, event handlers, `javascript:` URLs, SVG onload, CSS `url()` exfiltration,
`<base>` hijack, meta refresh, form phishing).

## 11. Session management and privacy

- The browser generates a random `client_id` UUID on first visit (`localStorage`). It scopes session
  listing so separate browsers don't see each other's lists. **It isn't an authorization boundary:**
  anyone with a session UUID can read it. That's fine for a local single-tenant tool, and it's
  documented as the first thing to change for multi-user deployment (add authentication and bind
  sessions to authenticated users).
- Stored: message text, timestamps, the skill/provider/model used, citations, timings, and error
  codes. Not stored: IP addresses, user agents, names, emails.
- With `LLM_PROVIDER=anthropic`, user messages and retrieved transcript excerpts are sent to
  Anthropic. The UI shows the active provider so this is never hidden.

## 12. Observability

- **Logs:** structlog JSON to stdout. Each request gets a `request_id` (from `X-Request-ID` or
  generated), returned in the response header and error envelope, and bound to every log line in
  that request.
- **Key events:** `http.request` (method, route, status, duration_ms), `turn.completed` (session_id,
  skill, route_rule, provider, model, evidence_count, citations_valid, citations_invalid, grounding,
  retrieval_ms, generation_ms, total_ms), `turn.failed` (code, provider, stage), `provider.fallback`,
  `retrieval.empty`, `artifact.sanitized` (removed counts), `ingestion.*`.
- **Redaction:** API keys never reach log calls. A structlog processor also masks values of
  `*key*`/`*token*`/`*secret*`/`authorization` fields as a backstop. Message content isn't logged
  unless `LOG_CONTENT=true` (off by default and documented as for local debugging only).
- **Health endpoints** (§6) back the compose healthchecks and the UI's provider indicator.

## 13. Deployment

```
docker compose up --build
  db   pgvector/pgvector:pg16  · healthcheck pg_isready · named volume pgdata
  api  backend image           · waits for db healthy · runs `alembic upgrade head` then uvicorn
                                · extra_hosts host.docker.internal:host-gateway (Linux)
                                · volumes: transcript cache, embedding model cache
                                · healthcheck GET /health
  web  frontend image (nginx)  · depends on api · publishes :8080
  ollama (profile "ollama")    · optional containerized Ollama for machines without a host install
```

- One `.env` file drives everything. `.env.example` documents every variable with safe defaults and
  no secrets.
- Startup doesn't require the knowledge base or a model to be ready. The app starts, and health
  endpoints and the UI say what's missing (`knowledge_base_empty` → "run `make ingest`";
  `model_not_found` → "`ollama pull qwen3:4b-instruct`").
- Host Ollama is recommended on macOS (a container can't use Metal) and on Windows/Linux with a GPU.
  The compose profile is a CPU convenience.

## 14. Decision log

| Date | Decision | Reason |
| --- | --- | --- |
| 2026-09-15 | Retrieval runs in code before generation. No model-initiated retrieval in v1. | Spike 001: 4B model never called the tool and cited evidence it never saw. |
| 2026-09-15 | Claude Agent SDK is the runtime for both providers via Anthropic-compatible endpoints | Spike 001: works against Ollama with ~1 s warm overhead |
| 2026-09-15 | Embeddings in-process (fastembed), not via the chat provider | The index stays valid when switching providers or when Ollama is down |
