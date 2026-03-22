"""LLM-assisted transform for generating native SOUL.md content."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

_SOUL_SYSTEM = """\
You are a harness engineer seeding a new AI agent's identity file.

You will be given:
1. A canonical SOUL.md from the source agent (Norm).
2. A set of voice_notes describing the target agent's character.
3. The target agent's name and deployment context.

Your job: Write a new SOUL.md for the target agent.

Rules:
- First-person, experiential language throughout. "I do X" not "The agent does X."
- The voice must match voice_notes — don't copy Norm's voice verbatim.
- Keep the structure: Core Truths, The Ethic, Hard-Won Beliefs, Anti-Patterns, Agency.
- Each section should feel earned, not templated. Adapt principles to this agent's context.
- No hollow affirmations. No corporate speak. No "I am always happy to help."
- Length: similar to the canonical (~600–800 words). Don't pad.
- Output the raw Markdown file only — no preamble, no commentary.
"""

_SOUL_PROMPT = """\
## Canonical SOUL.md (source agent: Norm)

{canonical_soul}

---

## Target agent profile

Name: {name}
OS: {os}
Harness: {harness}
Model: {model}
Voice notes: {voice_notes}
Platform notes: {platform_notes}

---

Write SOUL.md for {name}.
"""


@dataclass
class LLMTransform:
    """Generate SOUL.md via LLM from voice_notes + canonical source."""

    agent_name: str
    agent_os: str
    agent_harness: str
    agent_model: str
    voice_notes: str
    platform_notes: str
    api_base: str = "https://openrouter.ai/api/v1"
    generation_model: str = "openrouter/minimax/minimax-m2.7"
    name: str = field(default="llm", init=False)

    def apply(self, text: str) -> str:
        """Generate a native SOUL.md. `text` is the canonical SOUL.md content."""
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "openai package is required for LLM transforms: uv add openai"
            ) from exc

        api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY or OPENAI_API_KEY env var must be set for LLM transforms"
            )

        client = OpenAI(api_key=api_key, base_url=self.api_base)
        prompt = _SOUL_PROMPT.format(
            canonical_soul=text,
            name=self.agent_name,
            os=self.agent_os,
            harness=self.agent_harness,
            model=self.agent_model,
            voice_notes=self.voice_notes,
            platform_notes=self.platform_notes,
        )
        response = client.chat.completions.create(
            model=self.generation_model,
            messages=[
                {"role": "system", "content": _SOUL_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("LLM returned empty content for SOUL.md generation")
        return content.strip() + "\n"
