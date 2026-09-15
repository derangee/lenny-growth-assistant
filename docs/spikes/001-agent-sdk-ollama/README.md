# Spike 001 — Can the Claude Agent SDK drive a small local Ollama model?

Date: 2026-09-15 · Phase 1 (architecture) · Throwaway code, not product code.

## Question

The assessment requires the Claude Agent SDK (or Pi) **and** Ollama. The development machine has
8 GB RAM and a 4 GB GPU, so the local model has to be ~4B parameters. Two things to find out:

1. Can the SDK talk to Ollama at all? (Ollama 0.32.5 exposes an Anthropic-compatible `/v1/messages`.)
2. Can grounding safely rely on the model deciding to call a `search_transcripts` tool?

## Setup

- `claude-agent-sdk` 0.2.152 (Python), `qwen3:4b-instruct` via Ollama 0.32.5, Windows 11, GTX 1650 Ti.
- One **synthetic** evidence chunk (`SYNTH-001`), not transcript data.
- SDK options: custom `system_prompt`, `tools=[]` (no built-in Claude Code tools), `setting_sources=[]`,
  env `ANTHROPIC_BASE_URL=http://localhost:11434`.
- Script: [`spike.py`](spike.py). Raw output: [`run1-cold.log`](run1-cold.log), [`run2-warm.log`](run2-warm.log).

## Results (verbatim numbers from the logs)

| Variant | Cold | Warm | Outcome |
| --- | --- | --- | --- |
| A. Direct `POST /v1/messages`, evidence in prompt | 22.7 s (includes model load) | 4.8 s | Correct answer with correct citation |
| B. Agent SDK + in-process MCP `search_transcripts` tool, model decides to search | 50.9 s (42.3 s CLI init) | 10.7 s | **Tool never called** in either run. Model declined. Run 1 still attached `[SYNTH-001]`, a citation to evidence it never saw. |
| C. Agent SDK, no tools, evidence pre-retrieved in code and placed in prompt | — | 5.0 s (1.1 s init) | Correct answer with correct citation |

Harmless stderr noise from the CLI: `unrecognized_model` (it doesn't know Ollama model names) and a
note that claude.ai connectors are disabled.

## Decision

1. **Use the Claude Agent SDK as the generation runtime for both providers.** Anthropic works
   natively. Ollama works through its Anthropic-compatible API. Switching providers is a
   configuration change (base URL, auth, model), with no code change.
2. **Never make grounding depend on model-initiated tool use.** Skills run retrieval
   deterministically in code and pass numbered evidence to the model (variant C).
3. **Validate citations in code.** Variant B showed a small model will cite evidence it never
   received. Only citation labels that map to chunks retrieved for that turn survive.
4. **Keep a fallback runtime** that calls `/v1/messages` directly (variant A, same wire format for
   both providers). It covers environments where the SDK's bundled CLI can't run. It gets selected by
   configuration and is documented as a fallback, not the default.
5. SDK start-up overhead (~1 s warm, much longer cold on Windows) is acceptable next to model
   latency. It gets re-measured inside the Linux container in Phase 5.
