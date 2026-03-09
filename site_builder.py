"""
site_builder.py — Generate a static website from newsletter markdown files.

Reads output/*.md and produces docs/ with HTML pages + an index.
Designed for GitHub Pages (served from docs/ on main branch).
"""

import html
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
OUTPUT_DIR = ROOT / "output"
DOCS_DIR = ROOT / "docs"


def _md_to_html(md: str) -> str:
    """Convert newsletter markdown to HTML content."""
    text = html.escape(md)

    # Bold: **text**
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Italic: *text*
    text = re.sub(r'(?<!\w)\*(.+?)\*(?!\w)', r'<em>\1</em>', text)
    # Inline code: `text`
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)

    # Links: [text](url)
    def fix_link(m):
        label = m.group(1)
        url = html.unescape(m.group(2))
        return f'<a href="{url}" target="_blank" rel="noopener">{label}</a>'
    text = re.sub(r'\[(.+?)\]\((.+?)\)', fix_link, text)

    # Headings
    text = re.sub(r'^# (.+)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)

    # Blockquotes: > text
    text = re.sub(r'^&gt; (.+)$', r'<blockquote>\1</blockquote>', text, flags=re.MULTILINE)

    # Horizontal rules
    text = re.sub(r'^---+$', '<hr>', text, flags=re.MULTILINE)

    # Paragraphs: wrap non-tag lines separated by blank lines
    lines = text.split('\n')
    result = []
    paragraph = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if paragraph:
                content = '\n'.join(paragraph)
                if not any(content.strip().startswith(f'<{t}') for t in ('h1', 'h2', 'h3', 'hr', 'blockquote')):
                    content = f'<p>{content}</p>'
                result.append(content)
                paragraph = []
            continue
        paragraph.append(line)
    if paragraph:
        content = '\n'.join(paragraph)
        if not any(content.strip().startswith(f'<{t}') for t in ('h1', 'h2', 'h3', 'hr', 'blockquote')):
            content = f'<p>{content}</p>'
        result.append(content)

    return '\n'.join(result)


SITE_CSS = """\
:root {
    --bg: #fafaf9;
    --fg: #1c1917;
    --muted: #78716c;
    --accent: #2563eb;
    --border: #e7e5e4;
    --card-bg: #ffffff;
    --section-bg: #f5f5f4;
}
@media (prefers-color-scheme: dark) {
    :root {
        --bg: #0c0a09;
        --fg: #e7e5e4;
        --muted: #a8a29e;
        --accent: #60a5fa;
        --border: #292524;
        --card-bg: #1c1917;
        --section-bg: #1c1917;
    }
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--fg);
    line-height: 1.7;
    max-width: 720px;
    margin: 0 auto;
    padding: 2rem 1.5rem;
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
h1 { font-size: 1.8rem; margin-bottom: 0.5rem; letter-spacing: -0.02em; }
h2 { font-size: 1.3rem; margin: 2rem 0 0.8rem; letter-spacing: -0.01em; }
h3 { font-size: 1.1rem; margin: 1.5rem 0 0.5rem; }
p { margin-bottom: 1rem; }
hr { border: none; border-top: 1px solid var(--border); margin: 2rem 0; }
blockquote {
    border-left: 3px solid var(--accent);
    padding: 0.5rem 1rem;
    margin: 1rem 0;
    color: var(--muted);
    font-style: italic;
}
code {
    background: var(--section-bg);
    padding: 0.15rem 0.4rem;
    border-radius: 3px;
    font-size: 0.9em;
}
strong { font-weight: 600; }
.header { margin-bottom: 2rem; }
.header .subtitle {
    color: var(--muted);
    font-size: 0.95rem;
    margin-top: 0.25rem;
}
.nav { margin-bottom: 2rem; }
.nav a { margin-right: 1.5rem; font-size: 0.9rem; }
.issue-list { list-style: none; }
.issue-list li {
    padding: 1rem 0;
    border-bottom: 1px solid var(--border);
}
.issue-list li:last-child { border-bottom: none; }
.issue-list .date {
    font-weight: 600;
    font-size: 1.05rem;
}
.issue-list .weekday {
    color: var(--muted);
    font-size: 0.85rem;
    margin-left: 0.5rem;
}
.subscribe-box {
    background: var(--section-bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.2rem 1.5rem;
    margin: 2rem 0;
}
.subscribe-box p { margin-bottom: 0.5rem; }
.subscribe-box a { font-weight: 500; }
.footer {
    margin-top: 3rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--border);
    color: var(--muted);
    font-size: 0.85rem;
}
"""


def _page_template(title: str, body: str, nav_back: bool = False) -> str:
    """Wrap content in a full HTML page."""
    nav = ''
    if nav_back:
        nav = '<div class="nav"><a href="../">&larr; All issues</a></div>'

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="{'../' if nav_back else ''}style.css">
</head>
<body>
{nav}
{body}
<div class="footer">
    Botletter — an adaptive daily science newsletter by Gennaro Francesco Landi.<br>
    Generated with <a href="https://github.com/landigf/botletter">Botletter</a>.
    Powered by arXiv and Gemini.
</div>
</body>
</html>
"""


def build_site(channel_username: str | None = None):
    """Build the full static site from output/*.md into docs/."""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    issues_dir = DOCS_DIR / "issues"
    issues_dir.mkdir(exist_ok=True)

    # Write CSS + .nojekyll marker
    (DOCS_DIR / "style.css").write_text(SITE_CSS)
    (DOCS_DIR / ".nojekyll").touch()

    # Find all newsletters
    md_files = sorted(OUTPUT_DIR.glob("*.md"), reverse=True)
    if not md_files:
        print("No newsletters found in output/")
        return

    # Build individual issue pages
    issue_entries = []
    for md_path in md_files:
        date_str = md_path.stem  # "2026-03-09"
        md_content = md_path.read_text()

        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            weekday = dt.strftime("%A")
            display_date = dt.strftime("%B %d, %Y")
        except ValueError:
            weekday = ""
            display_date = date_str

        body_html = _md_to_html(md_content)
        page = _page_template(
            f"Botletter — {display_date}",
            body_html,
            nav_back=True,
        )
        (issues_dir / f"{date_str}.html").write_text(page)
        issue_entries.append((date_str, weekday, display_date))

    # Build index page
    subscribe_html = ""
    if channel_username:
        clean_username = channel_username.lstrip("@")
        subscribe_html = f"""
<div class="subscribe-box">
<p><strong>Subscribe</strong></p>
<p>Get this newsletter on your phone — join the
<a href="https://t.me/{clean_username}" target="_blank" rel="noopener">
Telegram channel</a> to receive each issue as it comes out.</p>
</div>
"""

    issues_html = ""
    for date_str, weekday, display_date in issue_entries:
        issues_html += (
            f'<li><a class="date" href="issues/{date_str}.html">{display_date}</a>'
            f'<span class="weekday">{weekday}</span></li>\n'
        )

    index_body = f"""
<div class="header">
<h1>Botletter</h1>
<p class="subtitle">A daily science newsletter by Gennaro Francesco Landi</p>
<p class="subtitle">MSc Computer Science @ ETH Zurich</p>
</div>
<p>An adaptive AI-generated newsletter mixing scientific curiosity with real
arXiv research. Each issue covers a deep curiosity topic, a research paper
spotlight, quick bites from across science, and a section tied to my research
area — infrastructure under AI/agentic workloads.</p>
<p>Built with <a href="https://github.com/landigf/botletter">Botletter</a>,
an open-source pipeline anyone can fork and personalize.</p>
{subscribe_html}
<h2>Issues</h2>
<ul class="issue-list">
{issues_html}
</ul>
"""

    index_page = _page_template("Botletter — Gennaro Francesco Landi", index_body)
    (DOCS_DIR / "index.html").write_text(index_page)

    print(f"🌐 Site built: {len(issue_entries)} issue(s) → docs/")


if __name__ == "__main__":
    import yaml
    config_path = ROOT / "config.yaml"
    channel = None
    if config_path.exists():
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
        channel = cfg.get("telegram", {}).get("channel_username")
    build_site(channel)
