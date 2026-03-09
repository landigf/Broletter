"""
fetcher.py — Fetch recent papers from arXiv (free, no auth needed).
"""

import random
from datetime import datetime, timedelta

import arxiv


def fetch_papers(config: dict, already_seen: list[str]) -> dict:
    """Fetch recent arXiv papers. Returns research_papers and thesis_papers lists."""
    arxiv_cfg = config["arxiv"]
    days_back = arxiv_cfg.get("days_lookback", 7)
    max_per_query = arxiv_cfg.get("max_papers_per_query", 10)
    thesis_keywords = [kw.lower() for kw in config.get("thesis_keywords", [])]

    categories = list(arxiv_cfg["primary_categories"])
    secondary = list(arxiv_cfg.get("secondary_categories", []))
    random.shuffle(secondary)
    categories += secondary[:2]

    cat_query = " OR ".join(f"cat:{cat}" for cat in categories)
    client = arxiv.Client()
    search = arxiv.Search(
        query=cat_query,
        max_results=max_per_query * len(categories),
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    cutoff = datetime.now().astimezone() - timedelta(days=days_back)
    research_papers = []
    thesis_papers = []

    for result in client.results(search):
        if result.entry_id in already_seen:
            continue
        if result.published.astimezone() < cutoff:
            continue

        paper = _parse_paper(result)
        text = (paper["title"] + " " + paper["summary"]).lower()
        if any(kw in text for kw in thesis_keywords):
            thesis_papers.append(paper)
        else:
            research_papers.append(paper)

    random.shuffle(research_papers)
    random.shuffle(thesis_papers)

    return {
        "research_papers": research_papers[:5],
        "thesis_papers": thesis_papers[:5],
    }


def _parse_paper(result) -> dict:
    return {
        "id": result.entry_id,
        "title": result.title,
        "authors": [a.name for a in result.authors],
        "summary": result.summary,
        "categories": result.categories,
        "published": result.published.strftime("%Y-%m-%d"),
        "pdf_url": result.pdf_url,
        "primary_category": result.primary_category,
    }


def format_paper_for_prompt(paper: dict) -> str:
    authors = ", ".join(paper["authors"][:5])
    if len(paper["authors"]) > 5:
        authors += f" et al. ({len(paper['authors'])} authors)"
    return (
        f"Title: {paper['title']}\n"
        f"Authors: {authors}\n"
        f"Categories: {', '.join(paper['categories'])}\n"
        f"Published: {paper['published']}\n"
        f"Abstract: {paper['summary']}\n"
        f"PDF: {paper['pdf_url']}"
    )
