# Discovery Brief

Phase 0 audit for **The Lenny Growth Assistant** (Oogway Labs, Forward Deployed Engineer take-home).
Audited on 2026-09-15. This document records what existed, what the environment can do, and the
decisions that follow from it. Product requirements live in [`PRD.md`](../PRD.md).

## 1. Repository state at audit

| Item | Finding |
| --- | --- |
| Commits | One: `39cc298 Initial commit` |
| Branches | `main` only, tracking `origin/main` |
| Remote | `https://github.com/derangee/lenny-growth-assistant.git` |
| Files | `README.md` (2 lines: project name, "for oogway labs") |
| Framework / package manager / deps / config | None |
| Working tree | Clean |

**What must be preserved:** the git history and remote. No application code exists, so there is
nothing to migrate. The placeholder README gets replaced in the documentation phase.

## 2. Environment at audit (developer machine)

| Capability | Finding | Consequence |
| --- | --- | --- |
| OS | Windows 11 | Scripts can't assume `make`/bash. I'll provide Docker Compose commands that work everywhere, plus a `Makefile` for macOS/Linux evaluators. |
| RAM / CPU | 8 GB / 8 logical cores | Postgres, API, web, and a local model must all fit in 8 GB. Local chat models have to be small (3–4B parameters, quantized). |
| GPU | NVIDIA GTX 1650 Ti, 4 GB VRAM | Enough for a quantized ~3B model plus a small embedding model. Nothing bigger. |
| Python | 3.13.0 (no `uv`) | Backend targets Python 3.12 inside Docker. Local dev uses `pip` + venv. |
| Node | 24.17.0, npm 11.13 (no pnpm) | Frontend uses npm. |
| Docker | Desktop 28.5.1, Compose v2.40. Daemon was **not running** at audit time. | Compose is the one-command path. The docs have to tell evaluators to start the daemon. |
| Ollama | 0.32.5 installed, **no models pulled** | Setup has to include explicit `ollama pull` steps. Nothing is pre-provisioned. |
| Ollama Anthropic API | `POST /v1/messages` answers in Anthropic's error format | The Claude Agent SDK could target Ollama via base-URL override. I'll prove this with a spike before relying on it (Phase 5). |
| Cloud keys | No `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` in the environment | The cloud provider path is built and tested with mocked transports. A live cloud run needs an evaluator-supplied key. I won't claim a live cloud run without one. |
| `claude-agent-sdk` | 0.2.152 available on PyPI | Viable agent-layer dependency. |

## 3. Knowledge source

No transcripts or Ship 30 material were supplied with the repository.

### Transcripts — selected source

[`ChatPRD/lennys-podcast-transcripts`](https://github.com/ChatPRD/lennys-podcast-transcripts),
pinned at commit `be8ab89a890a833cbba2c892178f823fff178c65`.

- 269 episodes, one `episodes/<guest-slug>/transcript.md` each.
- YAML frontmatter: `guest`, `title`, `youtube_url`, `video_id`, `publish_date`, `description`,
  `duration_seconds`, `duration`, `view_count`, `channel`, `keywords`.
- Body: speaker turns formatted as `Speaker Name (HH:MM:SS):` followed by the utterance. Every
  turn has a timestamp.

Why this source:

1. **Verifiable citations.** Speaker + timestamp + `video_id` means each citation can deep-link to
   the exact second on YouTube. An evaluator can check any claim in one click.
2. **Coverage.** 269 episodes, versus 50 in the official free starter pack
   ([`LennysNewsletter/lennys-newsletterpodcastdata`](https://github.com/LennysNewsletter/lennys-newsletterpodcastdata)).
3. **Structured metadata** needs no scraping and no guesswork.

Rights and handling: the source states the content "belongs to Lenny's Podcast and the respective
guests" and is provided for personal and educational use. Because this repository will be public,
**transcripts are not committed**. Ingestion downloads them at a pinned commit. Test fixtures are
short, synthetic, and clearly labelled as synthetic.

The ingestion design should keep the source pluggable. Adapting the parser to the official starter
pack should be a small change, but that isn't built unless there's time.

### Ship 30 for 30 guidance — public sources used

No guidance was supplied, so the skill encodes principles from Ship 30 for 30's own public guides:

- [How to Write an Atomic Essay: A Beginner's Guide](https://www.ship30for30.com/post/how-to-write-an-atomic-essay-a-beginners-guide)
- [How To Start Writing Online: The Ship 30 for 30 Ultimate Guide](https://www.ship30for30.com/post/how-to-start-writing-online-the-ship-30-for-30-ultimate-guide)

Principles extracted, to be encoded in Phase 7:

- **Headline:** answers *how many / what / who / feel / promise*. Clear beats clever. Uses a
  curiosity gap (show the start and the end, hold back the middle).
- **Intro:** 1/3/1 rhythm. One hook sentence, three sentences on relevance, credibility, and
  promise, then one sentence transitioning into the body.
- **Credibility type:** "curating experts". The essay's authority comes from the guests quoted,
  not from the model.
- **Proven approach:** pick one container (Steps, Lessons, Mistakes, Tips, Reasons) and keep it
  consistent. The headline's number must match the number of sections.
- **Skimmability:** wheels and spokes (headings and subheadings), bolded key sentences, lists for
  3+ items. Alternate short and long blocks. Avoid the monotone 1/1/1 and 5/5/5 rhythms.
- **Rate of revelation:** every sentence adds something new.
- **Differentiation ("Tequila test"):** avoid the clichéd answers.
- **Conclusion:** restate the takeaway and tell the reader what to do next.

**Length tension:** a Ship 30 *atomic essay* is ~250 words, but the assessment asks for ~1,250.
I read this as a long-form Ship 30-style essay: the same principles applied as a stack of
atomic-sized sections under a single headline promise. That assumption is recorded in the PRD.

## 4. Other public submissions

Search results show other candidates' public repositories for this same assessment. I haven't
read them, and this implementation doesn't borrow from them.

## 5. Implementation plan (summary)

Phases 1–14 follow the assessment brief in order. The plan's reasoning:

1. **Design before code** (Phase 1): architecture and UX system, including the decision on how
   the Claude Agent SDK fits with a 3B local model.
2. **Foundation → persistence → knowledge → models → agent → skills → artifacts → UI.** Each layer
   gets tested before the next one depends on it.
3. **Retrieval runs deterministically in code, before generation.** Grounding shouldn't depend on
   a small local model choosing to call a search tool.
4. **Citations are validated in code.** The model can only cite chunk IDs that retrieval actually
   returned. Anything else gets stripped and flagged.
5. **Hardening, docs, self-review, clean-clone verification** at the end, with every claim backed
   by a command that was actually run.

The riskiest unknowns get spiked early, in the phase that first needs them:

| Unknown | Spike in | Fallback if it fails |
| --- | --- | --- |
| Claude Agent SDK driving Ollama through `/v1/messages` | Phase 5 | Agent SDK for the cloud path. A direct Ollama adapter behind the same provider interface for local. Documented honestly. |
| A 3–4B local model following citation format | Phase 6 | Constrained output format plus code-side citation repair and validation. Stronger model recommended in docs. |
| Embedding all 269 episodes on 8 GB RAM in reasonable time | Phase 4 | Episode-subset ingestion flag for quick demos, plus Postgres full-text search as the lexical leg. |
