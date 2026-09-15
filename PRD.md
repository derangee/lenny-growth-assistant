# PRD — The Lenny Growth Assistant

Status: Draft v1 (Phase 0) · Owner: FDE candidate · Last updated: 2026-09-15
Discovery findings: [`docs/assessment.md`](docs/assessment.md)

## 1. User and problem

### Primary user

A **product or growth practitioner**: a PM, growth lead, or founder-operator at a software company.
They know Lenny's Podcast is a strong body of practitioner knowledge. They need to use it while
doing real work, like preparing a strategy doc, settling an internal debate, onboarding into a
growth role, or writing for their team.

### Secondary user

A **content-oriented operator** who turns that knowledge into writing: an internal memo, a
newsletter-style essay, or a one-page brief.

### Job to be done

> "When I'm facing a product or growth decision, I want to quickly find what experienced
> operators have actually said about it, with the exact source, so I can act with confidence and
> defend my reasoning to others."

Supporting jobs:

- Go deeper with follow-up questions without restating context.
- Turn what I learned into a publishable essay or a shareable document.

### Pain removed

| Today | With the assistant |
| --- | --- |
| 269 episodes × ~1 hour each. Knowledge is locked in audio and long transcripts. | Ask a question in plain language and get a synthesized answer in seconds. |
| General chatbots blend podcast advice with generic web knowledge and invent quotes. Output can't be trusted or cited. | Every claim links to an episode, speaker, and timestamp. When the transcripts don't cover something, the assistant says so. |
| Turning research into writing is a separate, slow step. | Ship 30 for 30 essays and HTML/Markdown documents are generated from the same grounded evidence and rendered beside the chat. |

The core value is **trust**. A fluent answer without a verifiable source is worth less than
"the transcripts don't cover this".

## 2. Success metrics

These are **definitions and targets, not results**. No numbers are reported until measured. Results
will be recorded in `docs/evaluation.md` with the command that produced them.

### North-star

**Grounded task completion rate.** The share of user questions answered with a response that
(a) addresses the question and (b) is fully supported by valid citations, or correctly declines
when evidence is insufficient.
Measured on a fixed evaluation set of hand-written questions: in-corpus, out-of-corpus, and
follow-ups. Scored by a documented rubric.

### Supporting metrics

| Metric | Definition | How measured | Target |
| --- | --- | --- | --- |
| Citation validity | % of citations that resolve to a chunk actually retrieved for that turn | Automated validator on every response. Enforced in code. | **100%** (hard invariant; invalid citations are stripped and logged) |
| Citation coverage | % of substantive answer paragraphs carrying ≥1 valid citation | Automated check on eval set | ≥ 90% |
| Insufficient-evidence correctness | % of out-of-corpus questions where the assistant declines rather than answering from general knowledge | Eval set (out-of-corpus subset) | ≥ 90% |
| Retrieval hit rate @k | % of in-corpus questions where a chunk from the expected episode appears in the top-k | Labeled question → episode pairs built from real transcripts | Baseline measured in Phase 4; must not regress |
| Ship 30 skill conformance | % of essays passing structural checks (1,000–1,500 words, headline, intro, N sections matching headline promise, takeaway, citations) | Automated validator | ≥ 90% on cloud model; measured and reported for local model |
| Artifact render success | % of artifact requests that produce a stored artifact that renders in the viewer without error | Automated tests + manual test plan | ≥ 95% |
| Time to first useful answer | Wall-clock time from send to first visible answer text (p50/p95), per provider | Timing logs | Measured and reported per provider and hardware. No target invented before measuring. |
| Graceful failure coverage | % of listed failure modes (§7) that produce a clear, actionable user-facing message and a structured log | Automated failure-path tests + manual plan | 100% |

Deliberately **not** tracked: token counts shown to users, "confidence" scores, or vanity usage
counts. Nothing in this system measures them reliably, and they don't help the user.

## 3. Assumptions

These fill gaps in the assignment. Each is a decision I can revisit.

1. **Data source.** The transcript corpus is the public
   `ChatPRD/lennys-podcast-transcripts` dataset (269 episodes), pinned to a commit. The assessment
   didn't supply one. See `docs/assessment.md` §3.
2. **Transcripts aren't redistributed.** Content belongs to Lenny's Podcast and guests. The public
   repo contains the ingestion pipeline, not the transcripts.
3. **Single-tenant, no authentication.** It runs locally for one evaluator or a small trusted team.
   "User metadata" means an **anonymous client identifier** generated in the browser, plus
   per-message technical metadata (provider, model, route/skill, latency, retrieved sources). No
   names, emails, or IP addresses are stored.
4. **Sessions are independent.** No retrieval or memory crosses sessions. Context within a session
   is the recent message history.
5. **Ship 30 length.** "~1,250 words" means a long-form essay applying Ship 30 for 30 atomic-essay
   principles as stacked sections. Acceptable band: 1,000–1,500 words.
6. **Ship 30 guidance** comes from Ship 30 for 30's public guides, since none was supplied.
7. **Ollama is the default demo provider.** Local hardware is constrained (8 GB RAM, 4 GB VRAM), so
   the local model is a small quantized one. Answer quality on it will be lower than the cloud
   model. Grounding and citation guarantees must still hold, because they're enforced in code.
8. **Cloud provider is Anthropic** (natural fit with the Claude Agent SDK). No key was available
   during development, so that path is verified with mocked transports. A live run needs the
   evaluator's key.
9. **English only.** The corpus is English.
10. **Artifacts** are Markdown and self-contained HTML/CSS documents. Generated JavaScript isn't
    executed.
11. **The corpus is static between refreshes.** Refreshing means re-running ingestion against a
    newer pinned commit. There's no live sync.

## 4. Scope

### Included

| Capability | Why |
| --- | --- |
| Grounded Q&A with timestamped, deep-linked citations | Core job. Trust is the product. |
| Explicit insufficient-evidence responses | Required. It's the main defense against hallucination. |
| Follow-up questions with in-session context | Required. Real research is iterative. |
| Persistent, independent sessions (PostgreSQL) | Required. Lets users return to prior work. |
| Ship 30 for 30 essay skill (dedicated, validated) | Required. It's the secondary user's job. |
| Markdown + HTML/CSS artifacts in a sandboxed side viewer | Required. Turns answers into shareable output. |
| Ollama (local) + Anthropic (cloud), switchable by configuration | Required. Also covers privacy and cost trade-offs. |
| Reproducible ingestion (acquire → parse → chunk → index) with refresh | Required. Evaluators must be able to rebuild the knowledge base. |
| Health endpoints, structured logs, graceful degradation | Required. It has to be operable, not just demoable. |
| Docker Compose one-command startup | Required. Keeps setup easy for evaluators. |

### Excluded

| Capability | Why excluded |
| --- | --- |
| Authentication, multi-tenant accounts, RBAC | Not requested. Adds setup friction for evaluators. Documented as a production gap. |
| Newsletter posts and other non-transcript sources | Assessment scopes to podcast transcripts. Keeps grounding claims precise. |
| Live corpus sync / scheduled re-ingestion | Corpus changes rarely. A manual refresh command is enough. |
| Audio/video ingestion or our own transcription | The corpus is already transcribed. |
| Artifact JavaScript execution, external network in artifacts | Security. See §7. |
| Artifact editing, versioning, collaborative sharing | Viewing, copying source, and downloading cover the job. |
| Streaming tokens over WebSockets | SSE (or simple request/response if SSE proves brittle) is enough for one user. |
| Fine-tuning, re-ranking models, external vector databases | Postgres (full-text + pgvector) is enough at ~30k chunks. Fewer moving parts. |
| Usage analytics dashboards | No user need. Would invite fabricated numbers. |

## 5. Functional requirements

1. **Sessions.** Create a session. List sessions (most recent first). Load a session's full
   history. Start a new conversation at any time. Sessions don't share context.
2. **Messaging.** Send a message. Receive an assistant reply with: answer text, citations
   (episode title, guest, speaker, timestamp, deep link, excerpt), route/skill used, provider and
   model used, and any artifact produced.
3. **Grounding.** Every factual claim attributed to the podcast must cite retrieved evidence. If
   retrieval returns nothing relevant, or the evidence doesn't support an answer, the reply says so
   plainly. It may suggest related topics the corpus does cover.
4. **Routing.** Requests go to one of: grounded answer, Ship 30 essay, or artifact generation.
   Routing is explainable (the reply shows which skill ran). The user can also pick the skill
   explicitly.
5. **Ship 30 skill.** Given a topic, produce a ~1,250-word essay that follows the encoded
   principles, with citations. It's validated before it's returned, and stored as a Markdown
   artifact.
6. **Artifacts.** Generate Markdown or complete HTML/CSS documents. Store them per session. Render
   them in a side viewer with Preview and Source views. HTML renders in a sandboxed, script-disabled
   iframe after sanitization.
7. **Configuration.** Provider and model are set by environment variables. The UI shows the active
   provider/model subtly. Provider readiness is exposed by a health endpoint.
8. **Ingestion.** One command fetches the pinned corpus, parses, chunks, embeds, and indexes it.
   It's idempotent. A subset option exists for quick demos.

## 6. Non-functional requirements

- **Setup:** clone → copy `.env.example` → `docker compose up` → ingest → use. Every step
  documented.
- **Reliability:** the API stays up when the model or database is down, and reports the problem.
- **Security:** no secrets in the repo or logs. Generated HTML treated as hostile. Strict
  validation on API inputs.
- **Privacy:** full message content isn't logged by default. Only identifiers, sizes, routes,
  timings, and error classes are.
- **Accessibility:** keyboard-operable, visible focus, semantic landmarks, WCAG AA contrast.

## 7. Risks

| Risk | Impact | Likelihood | Mitigation |
| --- | --- | --- | --- |
| **Hallucination** (invented quotes, episodes, facts) | Destroys trust, the core value | High on small local models | Retrieval runs in code before generation. Citations can only reference retrieved chunk IDs and get validated after generation. Invalid ones are stripped and logged. The prompt forbids unsupported claims. There's an explicit insufficient-evidence path. Eval set includes out-of-corpus questions. |
| **Retrieval quality** (right episode missed, jargon mismatch) | Correct answers look unsupported, or wrong evidence gets cited | Medium | Hybrid retrieval (Postgres full-text + vector similarity with rank fusion). Speaker-turn-aware chunks with overlap. Labeled hit-rate@k baseline. Relevance threshold that triggers insufficient-evidence. |
| **Latency** (CPU/4 GB GPU local inference) | Slow responses; essays may take minutes locally | High on local | Honest progress states. Streamed output if feasible. Bounded context size. Per-request timeouts. Docs recommend the cloud provider for long essays. |
| **Model quality** (3B model ignores format and citation instructions) | Poor essays, malformed citations | High on local | Simple, constrained output formats. Code-side parsing, repair, and validation. One revision pass for Ship 30. Measured conformance published per provider. |
| **Cost** (cloud tokens, long essays) | Unexpected spend | Low–Medium | Bounded retrieved context and history window. Configurable `max_tokens`. Ollama is the default. |
| **Ollama availability** (not running, model not pulled) | Assistant unusable | Medium | Readiness check reports exactly which model is missing and the `ollama pull` command. Clear UI error. Optional configured fallback provider. |
| **Data leakage** (user prompts to cloud, secrets in logs) | Privacy/security incident | Medium | Local-first default. UI shows which provider handles requests. Logs exclude content and keys. `.env` is git-ignored. Secret scanning before each commit. |
| **HTML artifact security** (XSS, exfiltration, phishing forms, parent-frame access) | Compromise of the app origin or the user | High if unmitigated | Server-side sanitization (scripts, event handlers, `javascript:` URLs, forms, external resources removed). Iframe with `sandbox` (no `allow-scripts`, no `allow-same-origin`), `srcdoc`, and a restrictive CSP. Malicious-payload tests. Limits documented. |
| **Database failures** (Postgres down, migrations missing) | Lost sessions; API errors | Low–Medium | `/health/db`. Structured 503 errors with a clear message. Startup waits for DB health. Migrations run on start. Transactions per message exchange. |
| **Corpus rights** | Takedown/licensing issue for a public repo | Low | Transcripts aren't committed. Fetched at ingestion from source with attribution. |
| **Claude Agent SDK ↔ Ollama compatibility** | Agent layer can't serve the mandatory local demo | Medium | Spike in Phase 5. Fallback: direct Ollama adapter behind the same provider interface. Documented honestly. |

## 8. Implementation plan

Phased, with a test gate and a commit at the end of each phase:

| # | Phase | Exit criteria |
| --- | --- | --- |
| 0 | Discovery & PRD | This document + discovery brief |
| 1 | Architecture & UX system | `architecture.md`, `design.md` with boundaries, data model, security model, UI principles |
| 2 | Foundation | Monorepo, Compose (Postgres + API + web), `.env.example`, lint/format/test tooling, `/health`, `/health/db`, structured logs |
| 3 | Sessions & persistence | Session/message/artifact models, migrations, session APIs, persistence tests |
| 4 | Ingestion & retrieval | `ingest` command, chunking with provenance, hybrid retrieval, retrieval tests, hit-rate baseline |
| 5 | Providers | Ollama + Anthropic behind one interface, configuration-driven, readiness + failure tests, Agent SDK spike result documented |
| 6 | Grounded agent | Router + grounded-answer skill, citation validation, insufficient-evidence path, tests |
| 7 | Ship 30 skill | Skill spec + prompt + validator + revision pass, tests |
| 8 | Artifacts | Markdown/HTML generation, sanitization, sandboxed rendering, malicious-case tests |
| 9 | Frontend | Conversation-first UI, citations, artifact viewer, states; visually reviewed and iterated |
| 10 | Testing | Backend + frontend suites, lint, types, build; manual test plan |
| 11 | Resilience | Every failure mode in §7 verified with a message + structured log |
| 12 | Docs & transcripts | README, final PRD/design/architecture, agent transcripts |
| 13 | Self-review | Checklist-driven review, fixes, full verification |
| 14 | Clean clone | Fresh-clone walkthrough; fix anything undocumented |

## 9. Open questions

- If the evaluator has the original assessment brief or specific Ship 30 material, it should be
  compared against assumptions 1, 5, and 6.
- The local model choice (e.g., which 3–4B instruction model) is decided by measurement in Phase 5,
  not asserted here.
