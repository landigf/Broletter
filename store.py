"""
store.py — Persistent storage for history, feedback, and knowledge map.

All data lives in the data/ directory as JSON files.
"""

import json
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


def _ensure_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


# ── History (papers seen, themes used) ──────────────────────

def load_history() -> dict:
    path = DATA_DIR / "history.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"papers_seen": [], "themes_used": [], "quick_bite_topics": []}


def save_history(history: dict):
    _ensure_dir()
    with open(DATA_DIR / "history.json", "w") as f:
        json.dump(history, f, indent=2)


# ── Feedback ────────────────────────────────────────────────

def load_feedback() -> dict:
    """Load all feedback. Structure:
    {
      "reactions": [
        {"date": "2026-03-09", "section": "curiosity", "reaction": "love", "ts": ...},
        ...
      ],
      "length_feedback": [
        {"date": "2026-03-09", "preference": "shorter", "ts": ...},
        ...
      ],
      "more_requests": [
        {"date": "2026-03-09", "section": "curiosity", "topic": "...", "ts": ...},
        ...
      ],
      "preferences": {
        "length_adjustment": 0,  # -2 to +2 scale (shorter to longer)
        "theme_weights": {},     # theme -> weight multiplier
        "section_weights": {}    # section -> weight multiplier
      }
    }
    """
    path = DATA_DIR / "feedback.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {
        "reactions": [],
        "length_feedback": [],
        "more_requests": [],
        "preferences": {
            "length_adjustment": 0,
            "theme_weights": {},
            "section_weights": {},
        },
    }


def save_feedback(feedback: dict):
    _ensure_dir()
    with open(DATA_DIR / "feedback.json", "w") as f:
        json.dump(feedback, f, indent=2)


def record_reaction(date: str, section: str, reaction: str):
    """Record a reaction (love/meh/skip) for a section."""
    fb = load_feedback()
    fb["reactions"].append({
        "date": date,
        "section": section,
        "reaction": reaction,
        "ts": datetime.now().isoformat(),
    })
    _update_preferences(fb)
    save_feedback(fb)


def record_length_feedback(date: str, preference: str):
    """Record length preference (shorter/perfect/longer)."""
    fb = load_feedback()
    fb["length_feedback"].append({
        "date": date,
        "preference": preference,
        "ts": datetime.now().isoformat(),
    })
    _update_preferences(fb)
    save_feedback(fb)


def record_more_request(date: str, section: str, topic: str):
    """Record 'tell me more about this tomorrow' request."""
    fb = load_feedback()
    fb["more_requests"].append({
        "date": date,
        "section": section,
        "topic": topic,
        "ts": datetime.now().isoformat(),
    })
    save_feedback(fb)


def _update_preferences(fb: dict):
    """Recompute preferences from recent feedback.

    Philosophy: exploration first. Feedback is a gentle nudge, never a takeover.
    - "love" = slight boost (+0.05 per reaction, max 1.15x)
    - "meh" = tiny decrease (-0.03, min 0.85x)
    - "skip" = small decrease (-0.05, min 0.85x)
    - Length adjusts slowly: each vote shifts by 0.3 minutes, not full minutes
    - Everything decays toward 1.0 over time (exploration wins long-term)
    """
    prefs = fb["preferences"]

    # Length: slow-moving average — each vote shifts by 0.3 min, clamped to ±1.5
    recent_length = fb["length_feedback"][-15:]
    if recent_length:
        score = 0.0
        for entry in recent_length:
            if entry["preference"] == "shorter":
                score -= 0.3
            elif entry["preference"] == "longer":
                score += 0.3
            # "perfect" = 0, acts as anchor toward current length
        prefs["length_adjustment"] = max(-1.5, min(1.5, score))

    # Section weights: gentle nudges, always pulled back toward 1.0
    # Only look at last 20 reactions, recent ones matter slightly more
    recent_reactions = fb["reactions"][-20:]
    section_scores: dict[str, float] = {}
    section_counts: dict[str, int] = {}
    for entry in recent_reactions:
        sec = entry["section"]
        # Small deltas: love +0.05, meh -0.03, skip -0.05
        delta = {"love": 0.05, "meh": -0.03, "skip": -0.05}.get(entry["reaction"], 0.0)
        section_scores[sec] = section_scores.get(sec, 0.0) + delta
        section_counts[sec] = section_counts.get(sec, 0) + 1

    for sec, total_delta in section_scores.items():
        # Clamp weight to [0.85, 1.15] — never let feedback dominate
        weight = 1.0 + total_delta
        prefs["section_weights"][sec] = max(0.85, min(1.15, weight))


def get_pending_more_requests() -> list[dict]:
    """Get undelivered 'more' requests — only from the most recent day.

    "More tomorrow" means exactly that: ONE follow-up, then it expires.
    If the user wants to go deeper again, they click again.
    """
    fb = load_feedback()
    requests = fb.get("more_requests", [])
    if not requests:
        return []
    # Only return requests that haven't been delivered yet
    return [r for r in requests if not r.get("delivered", False)]


def clear_more_requests():
    """Mark requests as delivered (not deleted — kept for history).
    They won't be returned by get_pending_more_requests again."""
    fb = load_feedback()
    for r in fb.get("more_requests", []):
        r["delivered"] = True
    save_feedback(fb)


def get_target_word_count(config: dict) -> int:
    """Calculate target words based on base config + length feedback."""
    base_minutes = config["format"]["base_reading_time_minutes"]
    fb = load_feedback()
    adjustment = fb.get("preferences", {}).get("length_adjustment", 0)
    # ~215 words per minute reading speed
    adjusted_minutes = base_minutes + adjustment
    adjusted_minutes = max(4, min(12, adjusted_minutes))  # clamp 4-12 min
    return int(adjusted_minutes * 215)


# ── Knowledge Map ───────────────────────────────────────────

def load_knowledge_map() -> str:
    path = DATA_DIR / "knowledge-map.md"
    if path.exists():
        return path.read_text()
    return ""


def append_to_knowledge_map(date: str, entries: list[str]):
    """Add today's topics to the knowledge map."""
    _ensure_dir()
    path = DATA_DIR / "knowledge-map.md"
    if not path.exists():
        path.write_text("# Knowledge Map\n\nTopics explored, connections found.\n\n")

    with open(path, "a") as f:
        f.write(f"\n## {date}\n\n")
        for entry in entries:
            f.write(f"- {entry}\n")


# ── Telegram State ──────────────────────────────────────────

def load_telegram_state() -> dict:
    path = DATA_DIR / "telegram.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def save_telegram_state(state: dict):
    _ensure_dir()
    with open(DATA_DIR / "telegram.json", "w") as f:
        json.dump(state, f, indent=2)


# ── Send status tracking ────────────────────────────────────

def mark_sent(date: str):
    """Mark a newsletter as successfully sent to Telegram."""
    _ensure_dir()
    (DATA_DIR / "last_sent.txt").write_text(date)


def was_sent(date: str) -> bool:
    """Check if a newsletter for this date was already sent."""
    path = DATA_DIR / "last_sent.txt"
    return path.exists() and path.read_text().strip() == date


# ── Config editing (from Telegram) ──────────────────────────

_CONFIG_PATH = Path(__file__).parent / "config.yaml"


def _load_config_yaml() -> dict:
    import yaml
    with open(_CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _save_config_yaml(config: dict):
    import yaml
    with open(_CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def _rephrase(raw_input: str, category: str) -> str:
    """Use Gemini to turn casual vibes into clean config terms.

    Examples:
      "like that crazy quantum biology stuff" → "quantum biology"
      "how GPUs talk to each other in clusters" → "GPU interconnects and cluster communication"
      "that italian prof at stanford who does spark" → "Matei Zaharia @ Stanford University"
    """
    import os
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return raw_input  # fallback: store as-is

    from google import genai
    client = genai.Client(api_key=api_key)

    prompts = {
        "interest": (
            "The user wants to add a curiosity theme to their daily science newsletter. "
            "Rephrase their casual input into a clean, concise theme label (3-8 words). "
            "Examples of good labels: 'quantum biology', 'history of computing and technology', "
            "'aerospace and space exploration', 'biomedical engineering and neuroscience'.\n\n"
            f"User said: \"{raw_input}\"\n\nClean label:"
        ),
        "topic": (
            "The user wants to add a research keyword/topic to track on arXiv. "
            "Rephrase their casual input into 1-3 clean, specific technical keywords "
            "(like you'd search on arXiv). Separate multiple keywords with commas only if "
            "the input clearly describes multiple distinct topics.\n"
            "Examples: 'KV cache', 'GPU scheduling', 'LLM serving', 'tail latency'.\n\n"
            f"User said: \"{raw_input}\"\n\nClean keyword(s):"
        ),
        "researcher": (
            "The user wants to follow a researcher. Clean up their input into the format "
            "'Full Name @ University/Lab'. If they give enough info to identify the person, "
            "use the correct full name and affiliation. If not enough info, just clean up "
            "what they gave.\n"
            "Examples: 'Ion Stoica @ UC Berkeley', 'Jeff Dean @ Google DeepMind'.\n\n"
            f"User said: \"{raw_input}\"\n\nClean researcher:"
        ),
    }

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompts[category],
        )
        cleaned = response.text.strip().strip('"').strip("'").strip("*").strip()
        # Strip any markdown formatting the LLM might add
        cleaned = cleaned.replace("**", "").replace("__", "").strip()
        # Sanity: if LLM returned something absurdly long, use original
        if len(cleaned) > 100 or not cleaned:
            return raw_input
        return cleaned
    except Exception:
        return raw_input  # fallback: store as-is


def add_interest(theme: str) -> str:
    """Add a curiosity theme. Returns confirmation message."""
    original = theme
    theme = _rephrase(theme, "interest")
    config = _load_config_yaml()
    themes = config.setdefault("curiosity_themes", [])
    if theme.lower() in [t.lower() for t in themes]:
        return f"Already tracking: {theme}"
    themes.append(theme)
    _save_config_yaml(config)
    if original.lower() != theme.lower():
        return f"✅ Added curiosity theme: {theme}\n(interpreted from: \"{original}\")"
    return f"✅ Added curiosity theme: {theme}"


def add_topic(keyword: str) -> str:
    """Add a thesis/research keyword. Returns confirmation message."""
    original = keyword
    keyword = _rephrase(keyword, "topic")
    config = _load_config_yaml()
    keywords = config.setdefault("thesis_keywords", [])
    # Handle comma-separated keywords from LLM
    new_keywords = [k.strip() for k in keyword.split(",") if k.strip()]
    added = []
    for kw in new_keywords:
        if kw.lower() not in [k.lower() for k in keywords]:
            keywords.append(kw)
            added.append(kw)
    if not added:
        return f"Already tracking: {keyword}"
    _save_config_yaml(config)
    result = "✅ Added research topic(s): " + ", ".join(added)
    if original.lower() != keyword.lower():
        result += f"\n(interpreted from: \"{original}\")"
    return result


def add_researcher(researcher: str) -> str:
    """Add a researcher to follow. Returns confirmation message."""
    original = researcher
    researcher = _rephrase(researcher, "researcher")
    config = _load_config_yaml()
    groups = config.setdefault("reader", {}).setdefault("target_groups", [])
    if researcher.lower() in [g.lower() for g in groups]:
        return f"Already following: {researcher}"
    groups.append(researcher)
    _save_config_yaml(config)
    if original.lower() != researcher.lower():
        return f"✅ Now following: {researcher}\n(interpreted from: \"{original}\")"
    return f"✅ Now following: {researcher}"


def remove_interest(theme: str) -> str:
    """Remove a curiosity theme. Uses fuzzy matching via LLM if no exact match."""
    config = _load_config_yaml()
    themes = config.get("curiosity_themes", [])
    # Try exact match first
    matches = [t for t in themes if t.lower() == theme.lower()]
    if not matches:
        # Fuzzy: ask LLM which existing theme they meant
        matches = _fuzzy_match(theme, themes)
    if not matches:
        return f"Not found: {theme}\nCurrent themes: " + ", ".join(themes[:5])
    themes.remove(matches[0])
    _save_config_yaml(config)
    return f"🗑 Removed curiosity theme: {matches[0]}"


def remove_topic(keyword: str) -> str:
    """Remove a thesis keyword. Uses fuzzy matching via LLM if no exact match."""
    config = _load_config_yaml()
    keywords = config.get("thesis_keywords", [])
    matches = [k for k in keywords if k.lower() == keyword.lower()]
    if not matches:
        matches = _fuzzy_match(keyword, keywords)
    if not matches:
        return f"Not found: {keyword}\nCurrent topics: " + ", ".join(keywords[:5])
    keywords.remove(matches[0])
    _save_config_yaml(config)
    return f"🗑 Removed research topic: {matches[0]}"


def remove_researcher(researcher: str) -> str:
    """Remove a researcher. Uses fuzzy matching via LLM if no exact match."""
    config = _load_config_yaml()
    groups = config.get("reader", {}).get("target_groups", [])
    matches = [g for g in groups if g.lower() == researcher.lower()]
    if not matches:
        matches = _fuzzy_match(researcher, groups)
    if not matches:
        return f"Not found: {researcher}"
    groups.remove(matches[0])
    _save_config_yaml(config)
    return f"🗑 Removed researcher: {matches[0]}"


def _fuzzy_match(query: str, options: list[str]) -> list[str]:
    """Use Gemini to find which option the user meant."""
    import os
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key or not options:
        return []

    from google import genai
    client = genai.Client(api_key=api_key)

    options_str = "\n".join(f"- {o}" for o in options)
    prompt = (
        f"The user wants to remove an item. Which of these existing items did they mean?\n\n"
        f"Existing items:\n{options_str}\n\n"
        f"User said: \"{query}\"\n\n"
        f"Reply with ONLY the exact matching item from the list, or 'NONE' if no match."
    )

    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        result = response.text.strip().strip('"').strip("'")
        if result == "NONE" or result not in options:
            return []
        return [result]
    except Exception:
        return []


def list_config_summary() -> str:
    """Return a formatted summary of current interests."""
    config = _load_config_yaml()
    lines = ["<b>🔬 Your current config</b>\n"]

    lines.append("<b>👥 Researchers:</b>")
    for r in config.get("reader", {}).get("target_groups", []):
        lines.append(f"  • {r}")

    lines.append("\n<b>💡 Curiosity themes:</b>")
    for t in config.get("curiosity_themes", []):
        lines.append(f"  • {t}")

    lines.append("\n<b>🎯 Research topics:</b>")
    for k in config.get("thesis_keywords", []):
        lines.append(f"  • {k}")

    return "\n".join(lines)
