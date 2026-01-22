"""Pitch drafting agent that composes personalized outreach drafts.

This agent crafts a draft pitch in Markdown format using research notes,
the Life Legally Single brand context, and a friendly, journalistic tone.
It does not send any communications; it merely returns the draft text
alongside metadata for downstream saving. When no LLM provider is
configured, the agent falls back to a deterministic template.
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional

from ..schemas.models import Citation, PitchDraft, Prospect, ResearchNotes
from ..utils.slugify import slugify

try:
    import openai  # type: ignore
except ImportError:
    openai = None  # type: ignore


class PitchDraftingAgent:
    """Agent responsible for generating a draft pitch for a journalist."""

    def __init__(self, brand_config: dict, logger: Optional[logging.Logger] = None):
        self.brand_config = brand_config
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        # Extract brand fields
        self.brand_name = brand_config.get("name", "Life Legally Single")
        self.tone = brand_config.get("tone", "")
        self.pillars: List[str] = brand_config.get("pillars", [])
        self.context = brand_config.get("context", "")
        self.mission = brand_config.get("mission", "")
        self.vision = brand_config.get("vision", "")
        # Determine if an OpenAI API key is available
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

    async def run(self, prospect: Prospect, profile: ResearchNotes) -> PitchDraft:
        """Generate a pitch draft tailored to the prospect.

        Parameters
        ----------
        prospect: Prospect
            Prospect record with basic info.
        profile: ResearchNotes
            Research notes containing topics and suggested angles.

        Returns
        -------
        PitchDraft
            Structured pitch draft with subject, greeting, body, and closing.
        """
        self.logger.debug(f"Drafting pitch for {prospect.name}")
        # Pick the first suggested angle or a default
        angle = profile.angles[0] if profile.angles else "the empowerment of singlehood"

        first_name = prospect.name.split()[0] if prospect.name.strip() else "there"
        subject_line = f"Story idea: {angle.capitalize()}"
        greeting = f"Hi {first_name},"

        # Compose the body using either an LLM or a deterministic template
        if openai and self.openai_api_key:
            self.logger.debug("Using OpenAI to generate pitch draft")
            try:
                openai.api_key = self.openai_api_key
                prompt = self._build_prompt(prospect, profile, angle)
                response = await openai.ChatCompletion.acreate(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                )
                content = response.choices[0].message.content.strip()
                # We assume the model returns complete pitch text; split into body and closing heuristically
                body, closing = self._split_body_closing(content)
            except Exception as e:
                self.logger.exception("LLM failed, falling back to template")
                body, closing = self._template_body_closing(profile, angle)
        else:
            # Template fallback
            body, closing = self._template_body_closing(profile, angle)

        slug = slugify(prospect.name)
        pitch = PitchDraft(
            prospect_name=prospect.name,
            slug=slug,
            subject_line=subject_line,
            greeting=greeting,
            body=body,
            closing=closing,
            citations=profile.citations,
        )
        self.logger.debug(f"Pitch drafted for {prospect.name}")
        return pitch

    def _build_prompt(self, prospect: Prospect, profile: ResearchNotes, angle: str) -> str:
        """Build a prompt for the language model based on brand context."""
        topics = ", ".join(profile.topics) if profile.topics else "recent trends"
        return (
            f"You are an outreach assistant for {self.brand_name}. "
            f"Our brand is {self.tone}. "
            f"We want to pitch a story idea to a journalist who covers {topics}. "
            f"The angle for this pitch is: {angle}. "
            f"Please write a concise yet thoughtful pitch (subject, greeting, body, closing) "
            f"that introduces the Life Legally Single platform, its mission and vision, "
            f"and explains why this story would resonate with their audience. "
            f"Do not include any hard sell or hype; keep it journalist-first."
        )

    def _split_body_closing(self, content: str) -> tuple[str, str]:
        """Split the generated content into body and closing by detecting the last line break."""
        parts = content.rsplit("\n", maxsplit=2)
        if len(parts) >= 2:
            body = "\n".join(parts[:-1]).strip()
            closing = parts[-1].strip()
        else:
            body = content.strip()
            closing = f"Best,\n{self.brand_name}"
        return body, closing

    def _template_body_closing(self, profile: ResearchNotes, angle: str) -> tuple[str, str]:
        """Fallback template for body and closing when no LLM is available."""
        # Construct paragraphs
        topics_str = ", ".join(profile.topics) if profile.topics else "topics relevant to your audience"
        body_lines = [
            f"I’m reaching out on behalf of {self.brand_name}, an AI‑powered lifestyle platform built to help singles thrive.",
            f"We’ve been following your coverage of {topics_str} and thought you might be interested in a story idea about {angle}.",
            "Our mission is to equip singles with tools, community, and technology that elevate self‑love, finance, travel, and personal growth.",
            "We believe your readers would appreciate a fresh perspective on how singlehood can be a power move rather than a placeholder.",
        ]
        body = "\n\n".join(body_lines)
        closing = f"Best regards,\n{self.brand_name}"
        return body, closing