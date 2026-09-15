"""Throwaway spike: can the Claude Agent SDK drive a small Ollama model reliably enough?

Not product code. Data below is a SYNTHETIC placeholder chunk, not a real transcript.
"""

import asyncio
import json
import sys
import time

import httpx
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    query,
    tool,
)

MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen3:4b-instruct"
OLLAMA = "http://localhost:11434"
FAKE_CHUNK = {
    "id": "SYNTH-001",
    "episode": "Synthetic Test Episode",
    "speaker": "Test Guest",
    "text": "SYNTHETIC: Our activation metric was completing three projects in week one.",
}
SYSTEM = (
    "You answer questions using ONLY evidence returned by the search_transcripts tool. "
    "Always call search_transcripts first. Cite evidence as [SYNTH-001] style IDs. "
    "If evidence is insufficient, say so."
)
QUESTION = "What activation metric did the guest describe?"


def baseline() -> None:
    t = time.perf_counter()
    r = httpx.post(
        f"{OLLAMA}/v1/messages",
        json={
            "model": MODEL,
            "max_tokens": 200,
            "system": SYSTEM,
            "messages": [
                {
                    "role": "user",
                    "content": f"Evidence: {json.dumps(FAKE_CHUNK)}\n\nQuestion: {QUESTION}",
                }
            ],
        },
        timeout=300,
    )
    print(f"[A] direct /v1/messages status={r.status_code} secs={time.perf_counter() - t:.1f}")
    print("[A] text:", r.json()["content"][0]["text"][:400] if r.is_success else r.text[:400])


calls: list[dict] = []


@tool("search_transcripts", "Search Lenny's Podcast transcript chunks.", {"query": str})
async def search_transcripts(args: dict) -> dict:
    calls.append(args)
    return {"content": [{"type": "text", "text": json.dumps([FAKE_CHUNK])}]}


async def agent_sdk() -> None:
    server = create_sdk_mcp_server("kb", "1.0.0", tools=[search_transcripts])
    stderr_lines: list[str] = []
    options = ClaudeAgentOptions(
        model=MODEL,
        system_prompt=SYSTEM,
        tools=[],
        mcp_servers={"kb": server},
        allowed_tools=["mcp__kb__search_transcripts"],
        max_turns=4,
        setting_sources=[],
        permission_mode="bypassPermissions",
        stderr=stderr_lines.append,
        env={
            "ANTHROPIC_BASE_URL": OLLAMA,
            "ANTHROPIC_AUTH_TOKEN": "ollama",
            "ANTHROPIC_API_KEY": "",
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": MODEL,
            "ANTHROPIC_SMALL_FAST_MODEL": MODEL,
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        },
    )
    t = time.perf_counter()
    first_text_at = None
    try:
        async for msg in query(prompt=QUESTION, options=options):
            elapsed = time.perf_counter() - t
            if isinstance(msg, SystemMessage):
                print(f"[B] {elapsed:5.1f}s system subtype={msg.subtype}")
            elif isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, ToolUseBlock):
                        print(f"[B] {elapsed:5.1f}s tool_use {block.name} {block.input}")
                    elif isinstance(block, TextBlock):
                        first_text_at = first_text_at or elapsed
                        print(f"[B] {elapsed:5.1f}s text: {block.text[:400]!r}")
            elif isinstance(msg, ResultMessage):
                print(
                    f"[B] {elapsed:5.1f}s result subtype={msg.subtype} is_error={msg.is_error} "
                    f"turns={msg.num_turns}"
                )
    except Exception as exc:  # spike: report everything
        print(f"[B] EXCEPTION {type(exc).__name__}: {exc}")
    print(f"[B] total={time.perf_counter() - t:.1f}s tool_calls={calls}")
    if stderr_lines:
        print("[B] stderr tail:", "\n".join(stderr_lines[-15:]))


if __name__ == "__main__":
    baseline()
    asyncio.run(agent_sdk())


async def agent_sdk_preseeded() -> None:
    """Variant C: retrieval done in code, evidence in prompt, SDK used as the runtime."""
    options = ClaudeAgentOptions(
        model=MODEL,
        system_prompt="Answer ONLY from the evidence in the user message. Cite IDs like [SYNTH-001]. "
        "If evidence is insufficient, say so and cite nothing.",
        tools=[],
        max_turns=1,
        setting_sources=[],
        env={
            "ANTHROPIC_BASE_URL": OLLAMA,
            "ANTHROPIC_AUTH_TOKEN": "ollama",
            "ANTHROPIC_API_KEY": "",
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": MODEL,
            "ANTHROPIC_SMALL_FAST_MODEL": MODEL,
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        },
    )
    prompt = f"Evidence: {json.dumps(FAKE_CHUNK)}\n\nQuestion: {QUESTION}"
    t = time.perf_counter()
    async for msg in query(prompt=prompt, options=options):
        e = time.perf_counter() - t
        if isinstance(msg, SystemMessage):
            print(f"[C] {e:5.1f}s system init")
        elif isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, TextBlock):
                    print(f"[C] {e:5.1f}s text: {b.text[:300]!r}")
        elif isinstance(msg, ResultMessage):
            print(f"[C] {e:5.1f}s result {msg.subtype} error={msg.is_error}")
    print(f"[C] total={time.perf_counter() - t:.1f}s")


if __name__ == "__main__" and "C" in sys.argv:
    asyncio.run(agent_sdk_preseeded())
