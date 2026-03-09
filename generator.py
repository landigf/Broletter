"""
generator.py — Generate newsletter sections using Gemini (free tier).
"""

import os

from google import genai

from fetcher import format_paper_for_prompt
from store import get_pending_more_requests, get_target_word_count, load_feedback
from templates import (
    CURIOSITY_PROMPT,
    QUICK_BITES_PROMPT,
    RECAP_PROMPT,
    RESEARCH_PROMPT,
    SYSTEM_PROMPT,
    THESIS_CORNER_PROMPT,
    get_section_word_counts,
    get_tone_instruction,
)


def _get_client() -> genai.Client:
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def _build_system_prompt(config: dict) -> str:
    prefs = load_feedback().get("preferences", {})
    total_words = get_target_word_count(config)
    tone = get_tone_instruction(prefs)
    reader = config.get("reader", {})
    return SYSTEM_PROMPT.format(
        tone_instruction=tone,
        target_words=total_words,
        reader_name=reader.get("name", "Reader"),
        reader_background=reader.get("background", "a researcher"),
        thesis_area=reader.get("thesis_area", "general science"),
        target_groups=", ".join(reader.get("target_groups", [])) or "none specified",
    )


def _generate(client: genai.Client, model: str, system: str, prompt: str) -> str:
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=genai.types.GenerateContentConfig(system_instruction=system),
    )
    return response.text


class NewsletterGenerator:
    def __init__(self, config: dict):
        self.client = _get_client()
        self.model = config["llm"].get("model", "gemini-2.5-flash")
        self.system = _build_system_prompt(config)

    def _gen(self, prompt: str) -> str:
        return _generate(self.client, self.model, self.system, prompt)

    def curiosity(self, theme: str, word_count: int) -> str:
        return self._gen(CURIOSITY_PROMPT.format(theme=theme, word_count=word_count))

    def research_spotlight(self, paper: dict, word_count: int) -> str:
        paper_text = format_paper_for_prompt(paper)
        return self._gen(RESEARCH_PROMPT.format(paper=paper_text, word_count=word_count))

    def quick_bites(self, previous_topics: list[str], word_count: int) -> str:
        if previous_topics:
            instruction = "Avoid these recently covered topics: " + ", ".join(previous_topics[-15:])
        else:
            instruction = "This is the first edition — pick whatever excites you!"
        return self._gen(QUICK_BITES_PROMPT.format(
            previous_topics_instruction=instruction, word_count=word_count,
        ))

    def thesis_corner(self, paper: dict | None, word_count: int) -> str:
        if paper:
            paper_section = (
                "Here's a recent arXiv paper in the reader's thesis area:\n\n"
                f"{format_paper_for_prompt(paper)}\n\n"
                "Use it as a jumping-off point, but also bring your own knowledge."
            )
        else:
            paper_section = (
                "No specific paper today — draw from your knowledge of recent trends "
                "in AI infrastructure, caching, GPU scheduling, model serving, "
                "serverless for ML. Reference real work from real groups."
            )

        more_requests = get_pending_more_requests()
        if more_requests:
            topics = [r.get("topic", "") for r in more_requests]
            more_instruction = (
                "The reader asked to go deeper on these topics from yesterday: "
                + ", ".join(topics)
                + ". Incorporate this into your response if relevant."
            )
        else:
            more_instruction = ""

        return self._gen(THESIS_CORNER_PROMPT.format(
            paper_section=paper_section, word_count=word_count,
            more_request_instruction=more_instruction,
        ))

    def recap(self, weekly_topics: list[str], word_count: int) -> str:
        topics_list = "\n".join(f"- {t}" for t in weekly_topics)
        return self._gen(RECAP_PROMPT.format(topics_list=topics_list, word_count=word_count))
