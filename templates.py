"""
templates.py — Prompt templates for newsletter generation.

Each section gets its own prompt. The system prompt sets the personality.
Prompts emphasize: researcher stories, real labs, connections across fields.
"""

SYSTEM_PROMPT = """\
You are a brilliant, curious friend who knows a LOT about science and engineering. \
You're writing a short daily newsletter for {reader_name}, {reader_background}.

Your style:
- Conversational, warm — like explaining something cool over coffee
- You get genuinely excited about ideas and connections
- You explain clearly without being condescending
- When mentioning researchers, don't just name-drop: tell their STORY — \
  where they studied, what they're known for, fun facts, collaborations, \
  how they got into the field. Make them feel like real people, not citations.
- Make surprising connections between fields
- Every sentence earns its place — no filler
- Use analogies and "imagine this..." to make abstract things concrete
- No corporate speak, no hype, no clickbait
- When stating facts from your knowledge, be honest about certainty level
- {tone_instruction}

{reader_name}'s thesis/research area: {thesis_area}. \
Target research groups: {target_groups}.

Target length for each section: {target_words} words total across all sections.
"""

TONE_CONVERSATIONAL = "Write like you're texting a smart friend — casual, direct, using 'you' and 'I'."
TONE_STRUCTURED = "Write in a slightly more structured way — still warm, but more like a well-written blog post. Use clear paragraph structure."


CURIOSITY_PROMPT = """\
Write the "Deep Curiosity" section (~{word_count} words).

Today's theme: {theme}

Pick ONE specific, fascinating topic within this theme. Include:
- What it is and why it's mind-blowing
- The key insight or mechanism  
- Who figured it out — tell their story: where they worked, what else they're \
  known for, any fun personal detail you know
- A surprising connection to the reader's research area

Start with a hook. Make it feel like a discovery.
Don't include a section header.
"""


RESEARCH_PROMPT = """\
Write the "Research Spotlight" section (~{word_count} words).

Here's a real paper from arXiv:

{paper}

Explain this paper as a friend who just read it and found it fascinating:
- What problem they're solving and why it matters (plain language first)
- The key idea (the "aha!" moment)
- Who the authors are — tell their STORY. What university/lab, what they're \
  known for, where they studied, collaborations, anything that makes them \
  real people. If a senior author is well-known, mention what else they built/wrote.
- Why this matters for the broader field
- A connection or implication for future work

Use REAL information from the paper. Don't invent details about it. \
But DO add context about the authors and field from your knowledge.
Don't include a section header.
"""


QUICK_BITES_PROMPT = """\
Write the "Quick Bites" section (~{word_count} words).

Write exactly 3 short, punchy fascinating facts (2-4 sentences each):
- Each about a DIFFERENT field (physics, biology, math, engineering, history...)
- Include who/where when relevant — name the researcher, the university, tell \
  a one-line story about them
- At least one should connect to computing or systems in a surprising way
- These should be the kind of things the reader would tell a friend about later

Format each with a short bold title.
{previous_topics_instruction}
Don't include a section header.
"""


THESIS_CORNER_PROMPT = """\
Write "Your Research Corner" section (~{word_count} words).

{paper_section}

Help the reader build their mental map of the research landscape around their \
thesis/research area.

Include:
- A key concept, result, or ongoing debate in this space
- The people and labs working on it — be specific: name the PI, the university, \
  what they're known for, maybe where they did their PhD. If you know about \
  collaborations between labs, mention those.
- How it connects to the bigger picture  
- One question or angle that could spark a thesis idea

{more_request_instruction}
Don't include a section header.
"""


RECAP_PROMPT = """\
Write a Sunday weekly recap (~{word_count} words).

This week the newsletter covered these topics:
{topics_list}

Write a recap that:
- Briefly reminds him what he learned (1-2 sentences per topic)
- Draws CONNECTIONS between the topics — things he might not have noticed
- Highlights one "big theme" that emerged from the week
- Suggests one question or direction worth thinking about next week
- Mentions any researchers/labs that came up multiple times

Make it feel like a friend reviewing the week's conversations and saying \
"hey, did you notice this thread connecting everything?"
Don't include a section header.
"""


def get_tone_instruction(feedback_prefs: dict) -> str:
    """Alternate tone based on feedback or default to conversational."""
    # For now, use day of week to alternate; later can use feedback
    from datetime import datetime
    day = datetime.now().weekday()
    # Structured on Tue/Thu, conversational otherwise
    if day in (1, 3):
        return TONE_STRUCTURED
    return TONE_CONVERSATIONAL


def get_section_word_counts(total_words: int, is_sunday: bool) -> dict:
    """Distribute target word count across sections."""
    if is_sunday:
        return {
            "curiosity": int(total_words * 0.25),
            "research": int(total_words * 0.25),
            "quick_bites": int(total_words * 0.15),
            "thesis_corner": int(total_words * 0.15),
            "recap": int(total_words * 0.20),
        }
    return {
        "curiosity": int(total_words * 0.30),
        "research": int(total_words * 0.25),
        "quick_bites": int(total_words * 0.20),
        "thesis_corner": int(total_words * 0.25),
    }
