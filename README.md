# Broletter

An adaptive, AI-generated daily science newsletter delivered to your phone via Telegram.
Around 7 minutes of reading each morning — real arXiv papers explained clearly,
a deep curiosity topic, quick fascinating bites across fields, and a section
tied to your research focus. All for $0/day.

Built for researchers and students who want to stay broadly curious while keeping
a sharp eye on their own field.


## What it does

Every night at 11 PM, the system fetches fresh papers from arXiv, generates a
personalized newsletter using Gemini (free tier), and delivers it to your
Telegram chat. In the morning, a short reminder pings your phone so you
can read it on the commute.

You react to each section with inline buttons (love / meh / skip / more of this).
The system learns gently from your feedback — shifting weights just enough to
surface more of what you care about, without collapsing into a filter bubble.
Exploration always wins long-term.

| Section | Description |
|---------|-------------|
| **Deep Curiosity** | One fascinating topic in depth — physics, aerospace, bio, history of computing |
| **Research Spotlight** | A real arXiv paper explained, with researcher backstories |
| **Quick Bites** | Three mind-blowing facts from different fields |
| **Your Research Corner** | Tied to your thesis area, referencing real labs and ongoing debates |
| **Sunday Recap** | Weekly connections and emerging themes across everything you read |


## How it runs (battery and resources)

The newsletter uses **zero background processes**. It works like an alarm clock:

- Your computer's built-in scheduler (LaunchAgent on Mac, Task Scheduler on Windows)
  wakes up Python for a few seconds at scheduled times
- Python generates the newsletter, sends it to Telegram, then exits completely
- Between runs, nothing is running — zero CPU, zero RAM, zero battery drain

If your computer is asleep or off at the scheduled time, the task runs
automatically the next time it wakes up. Nothing is lost.

The whole process takes about 30-60 seconds and uses:
- ~5 free API calls to Google Gemini
- ~1 HTTP request to arXiv (free, no account needed)
- ~3 HTTP requests to Telegram (free)


---


## Setup guide — macOS

If you're on Windows, skip to the [Windows setup guide](#setup-guide--windows) below.


### Step 1: Install Python (if you don't have it)

Open **Terminal** (press `Cmd + Space`, type "Terminal", press Enter).

Check if Python is installed:

```bash
python3 --version
```

If you see something like `Python 3.11.x` or higher, you're good — skip to Step 2.

If not, install it with Homebrew:

```bash
# Install Homebrew (if you don't have it)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python
```


### Step 2: Download the project

In Terminal, run:

```bash
git clone https://github.com/landigf/Broletter.git
cd Broletter
```


### Step 3: Create a virtual environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

You should see packages installing. When it finishes, you're ready.


### Step 4: Get your API keys (both free)

You need two keys. Both are completely free.

#### 4a. Gemini API key (for generating the newsletter)

1. Go to https://aistudio.google.com/apikey
2. Sign in with your Google account (any Gmail works)
3. Click **"Create API Key"**
4. Select any project (or create one — the name doesn't matter)
5. Copy the key — it looks like `AIzaSy...` (about 40 characters)

The free tier gives you 1500 requests per day. The newsletter uses about 5.

#### 4b. Telegram bot token (for delivering the newsletter to your phone)

1. Open Telegram on your phone
2. Search for **@BotFather** (it has a blue checkmark)
3. Tap **Start**, then send the message: `/newbot`
4. BotFather will ask for a **name** — type anything you like (e.g., "My Science Newsletter")
5. BotFather will ask for a **username** — this must end in `bot` (e.g., `my_science_bot`)
6. BotFather will reply with your token — it looks like `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`
7. Copy that token


### Step 5: Save your keys

Paste these two lines into Terminal, replacing the placeholder text with your actual keys:

```bash
echo 'export GEMINI_API_KEY="paste-your-gemini-key-here"' >> ~/.zshrc
echo 'export TELEGRAM_BOT_TOKEN="paste-your-telegram-token-here"' >> ~/.zshrc
source ~/.zshrc
```

This saves the keys permanently so they survive restarts.

To verify they're set:

```bash
echo $GEMINI_API_KEY
echo $TELEGRAM_BOT_TOKEN
```

Both should print your keys (not empty lines).


### Step 6: Configure your interests

Open `config.yaml` in any text editor (TextEdit works, or VS Code if you have it).

You can also copy the example config as a starting point:

```bash
cp config.example.yaml config.yaml
```

Edit these sections to match **your** interests:

```yaml
reader:
  name: "Your Name"
  background: "PhD Physics @ MIT (condensed matter)"
  thesis_area: "topological insulators and quantum transport"
  target_groups:
    - "Charlie Kane @ UPenn"
    - "Claudia Felser @ MPI Dresden"

curiosity_themes:
  - "how superconductors work at the atomic level"
  - "history of computing and technology"
  - "aerospace and space exploration"
  - "marine biology and deep ocean ecosystems"

arxiv:
  primary_categories:
    - "cond-mat.mes-hall"
    - "quant-ph"
  secondary_categories:
    - "physics.app-ph"
    - "cs.AI"

thesis_keywords:
  - "topological insulator"
  - "quantum Hall effect"
  - "spin-orbit coupling"
```

**Tip**: Keep your curiosity_themes list wide. Half the value of a daily newsletter
is stumbling into something you'd never search for. If you only track your own
subfield, you lose the serendipity that makes science fun.

For arXiv category codes, see: https://arxiv.org/category_taxonomy


### Step 7: Register your Telegram chat

```bash
source .venv/bin/activate
python main.py listen
```

Now open Telegram on your phone, find your bot by the name you gave it, and send
`/start`. You should see a confirmation message both in Telegram and in Terminal.

Press **Ctrl+C** in Terminal to stop the listener.


### Step 8: Generate your first newsletter

```bash
python main.py generate
```

Wait about 30-60 seconds. Check Telegram — your newsletter should arrive in
sections, each with reaction buttons (love / meh / skip / more of this).


### Step 9: Automate it (so it runs every night by itself)

```bash
python scripts/install_schedule.py
```

This installs three lightweight scheduled tasks:

| Task | When | What it does |
|------|------|--------------|
| **Generate** | 11 PM daily + on wake | Fetches feedback, generates newsletter, sends it |
| **Sync** | Every 5 minutes | Processes Telegram commands (`/add_interest`, etc.) and button presses |
| **Reminder** | Every 30 min (mornings only) | Pings Telegram so you see the newsletter on your phone |

All tasks are **idempotent** — if your Mac was asleep at 11 PM, it generates
the newsletter when it wakes up. If it already sent today's newsletter, it
skips. You never get duplicates.

**That's it! You're done.** Your newsletter will arrive every morning automatically.

To check the logs if something goes wrong:

```bash
cat /tmp/com.botletter.generate.log
cat /tmp/com.botletter.generate.err
```


---


## Setup guide — Windows

Complete beginner guide. No prior terminal experience needed.


### Step 1: Install Python

1. Go to https://www.python.org/downloads/
2. Click the big yellow **"Download Python 3.x.x"** button
3. Run the installer
4. **IMPORTANT**: On the first screen, check the box that says **"Add Python to PATH"** (at the bottom). This is critical — don't skip it!
5. Click **"Install Now"**
6. When it finishes, click **"Close"**

To verify it worked, open **PowerShell**:
- Press `Win + X`, then click **"Windows PowerShell"** (or **"Terminal"**)
- Type:

```powershell
python --version
```

You should see something like `Python 3.12.x`. If you see an error, restart
your computer and try again (the PATH change needs a restart sometimes).


### Step 2: Install Git

1. Go to https://git-scm.com/download/win
2. Download and run the installer
3. Click **Next** through all the screens — the default settings are fine
4. Click **Install**, then **Finish**


### Step 3: Download the project

Open PowerShell and run:

```powershell
cd Desktop
git clone https://github.com/landigf/Broletter.git
cd Broletter
```

This creates a `Broletter` folder on your Desktop.


### Step 4: Create a virtual environment and install dependencies

Still in PowerShell, run:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

If you see a red error about "execution policy", run this first and then try again:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```


### Step 5: Get your API keys (both free)

#### 5a. Gemini API key (for generating the newsletter)

1. Go to https://aistudio.google.com/apikey
2. Sign in with your Google account (any Gmail works)
3. Click **"Create API Key"**
4. Select any project (or create one — the name doesn't matter)
5. Copy the key — it looks like `AIzaSy...` (about 40 characters)

#### 5b. Telegram bot token (for delivering the newsletter to your phone)

1. Open Telegram on your phone
2. Search for **@BotFather** (it has a blue checkmark)
3. Tap **Start**, then send the message: `/newbot`
4. BotFather asks for a **name** — type anything (e.g., "My Science Newsletter")
5. BotFather asks for a **username** — must end in `bot` (e.g., `my_science_bot`)
6. BotFather replies with your token — looks like `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`
7. Copy that token


### Step 6: Save your keys permanently

In PowerShell, paste these two lines, replacing the placeholders with your actual keys:

```powershell
[System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "paste-your-gemini-key-here", "User")
[System.Environment]::SetEnvironmentVariable("TELEGRAM_BOT_TOKEN", "paste-your-telegram-token-here", "User")
```

**Close PowerShell and open a new one** for the changes to take effect.

To verify they're saved:

```powershell
echo $env:GEMINI_API_KEY
echo $env:TELEGRAM_BOT_TOKEN
```

Both should print your keys.


### Step 7: Configure your interests

Open the file `config.yaml` inside the Broletter folder with **Notepad** (right-click
the file → Open with → Notepad).

You can also copy the example config first:

```powershell
copy config.example.yaml config.yaml
```

Edit the file to match your interests (see the [Configure your interests](#step-6-configure-your-interests)
section in the macOS guide above for what each field means).

**Important**: YAML files are sensitive to spacing. Use spaces (not tabs), and keep
the indentation exactly as shown in the example.


### Step 8: Register your Telegram chat

In PowerShell:

```powershell
cd Desktop\Broletter
.venv\Scripts\activate
python main.py listen
```

Open Telegram on your phone, find your bot, and send `/start`.
You should see a confirmation. Press **Ctrl+C** in PowerShell to stop.


### Step 9: Generate your first newsletter

```powershell
python main.py generate
```

Wait about 30-60 seconds. Check Telegram — your newsletter should appear!


### Step 10: Automate it (so it runs every night by itself)

Open PowerShell **as Administrator** (right-click → "Run as Administrator"):

```powershell
cd Desktop\Broletter
.venv\Scripts\activate
python scripts\install_schedule_windows.py
```

This creates three scheduled tasks in Windows Task Scheduler:

| Task | When | What it does |
|------|------|--------------|
| **Broletter_Generate** | 11 PM daily | Fetches feedback, generates newsletter, sends it |
| **Broletter_Sync** | Every 5 minutes | Processes Telegram commands and button presses |
| **Broletter_Reminder** | 7 AM daily | Pings Telegram so you see the newsletter |

Your PC needs to be **on (not asleep)** at 11 PM for generation. If it's off,
the newsletter generates the next time you log in.

**That's it! You're done.**

To check if the tasks are working:

```powershell
schtasks /Query /TN Broletter_Generate
```


---


## Usage

```bash
python main.py generate              # Generate + send today's newsletter
python main.py generate --no-fetch   # LLM-only, skip arXiv
python main.py generate --no-send    # Generate markdown only, don't send
python main.py generate --no-publish # Don't rebuild/push the website
python main.py remind                # Send morning Telegram reminder
python main.py sync                  # Fetch and process pending Telegram commands
python main.py listen                # Start Telegram bot for /start registration
python main.py setup                 # Check what's configured
```


## Telegram commands

You can manage your interests directly from Telegram, without editing config
files. Casual input works — the system uses Gemini to rephrase your message
into a clean config entry.

| Command | Example | What it does |
|---------|---------|--------------|
| `/add_interest` | `/add_interest that crazy quantum bio stuff` | Adds a curiosity theme |
| `/add_topic` | `/add_topic how GPUs talk to each other` | Adds a research keyword for arXiv filtering |
| `/add_researcher` | `/add_researcher that Italian prof at Stanford who made Spark` | Follows a researcher (LLM resolves the name) |
| `/remove_interest` | `/remove_interest materials science` | Removes a theme (fuzzy matching) |
| `/remove_topic` | `/remove_topic serverless` | Removes a keyword |
| `/remove_researcher` | `/remove_researcher Zaharia` | Removes a researcher |
| `/config` | `/config` | Shows all current settings |
| `/history` | `/history` | Lists past newsletter dates |
| `/help` | `/help` | Shows all available commands |

**Note**: Telegram commands are processed every 5 minutes by the sync task.
When you send a command, you'll get a reply within a few minutes (not instantly).


## Feedback buttons

Each section is delivered with inline reaction buttons:

- **Love it** — gentle boost to this section type (+0.05 weight, max 1.15x)
- **Meh** — slight decrease (-0.03, min 0.85x)
- **Skip** — a bit more decrease (-0.05, min 0.85x)
- **More of this tomorrow** — one-shot deep dive on the same topic next day

After the last section, a length feedback row: **Shorter / Perfect / Longer**.
Each vote shifts reading time by 0.3 minutes, clamped to +/-1.5 from your base.

The adaptation is intentionally gentle. A single "meh" does not kill a section.
The system is biased toward exploration — weights always drift back toward 1.0
over time, so your newsletter never narrows down to a single topic.


## Website

Every newsletter is automatically published to a static website hosted on
GitHub Pages. After each generation, the site is rebuilt and pushed — no
manual steps needed.

The site lives at the URL GitHub Pages gives your repo (for the original:
https://landigf.github.io/Broletter/). Each issue gets its own page with
clean typography and dark mode support.

### Public Telegram channel

To let others subscribe to your newsletter via a public Telegram channel:

1. Create a public channel in Telegram (Settings → New Channel → Public)
2. Add your bot as an admin with permission to post messages
3. Set `telegram.channel_username` in `config.yaml` to your channel's username

The bot automatically cross-posts each issue there (without reaction buttons —
those are personal).


## Architecture

```
config.yaml              Your interests, arXiv categories, thesis keywords
main.py                  CLI orchestrator: generate / remind / sync / listen / setup
fetcher.py               arXiv paper fetching (free, no auth)
generator.py             Newsletter generation via Gemini (google-genai SDK)
templates.py             LLM prompt templates with tone rotation
bot.py                   Telegram delivery, feedback collection, config commands
store.py                 Persistence: history, feedback, knowledge map, config editing
site_builder.py          Static site generator (output/*.md → docs/ HTML)
scripts/
  install_schedule.py    macOS LaunchAgent installer (3 agents)
  install_schedule_windows.py  Windows Task Scheduler installer (3 tasks)
  launch_main.py         macOS bootstrap (runs main.py from base Python + venv packages)
data/
  history.json           Papers seen, themes used, quick bite topics
  feedback.json          Reactions, length preferences, adaptation weights
  knowledge-map.md       Growing log of every topic explored
  telegram.json          Bot state (chat ID, last topics)
  last_sent.txt          Idempotency guard for send retries
output/
  YYYY-MM-DD.md          Archived newsletters (one per day, searchable)
docs/
  index.html             Website index (auto-generated, committed to git)
  issues/*.html          Individual newsletter pages
  style.css              Site stylesheet
```


## Troubleshooting

### Newsletter not generating

Check the error log:

```bash
# macOS
cat /tmp/com.botletter.generate.err

# Windows (PowerShell)
schtasks /Query /TN Broletter_Generate /V
```

Common causes:
- **Python path changed** (e.g., Homebrew upgrade): re-run `python scripts/install_schedule.py`
- **API key expired or missing**: check with `echo $GEMINI_API_KEY` (Mac) or `echo $env:GEMINI_API_KEY` (Windows)
- **No internet at 11 PM**: the newsletter will retry on next wake/login automatically

### Telegram commands not responding

Commands are processed every 5 minutes by the sync task. If nothing happens
after 10 minutes, check if the sync task is running:

```bash
# macOS
launchctl list | grep botletter

# Windows
schtasks /Query /TN Broletter_Sync
```

### Manual test

To test everything works right now:

```bash
# macOS
source .venv/bin/activate
python main.py generate --no-publish

# Windows
.venv\Scripts\activate
python main.py generate --no-publish
```


## Cost

| Component | Cost |
|-----------|------|
| Gemini 2.5 Flash | Free tier (1500 req/day, newsletter uses ~5) |
| arXiv API | Free, no authentication |
| Telegram Bot API | Free |
| macOS LaunchAgent / Windows Task Scheduler | Built-in |

Total: **$0/day**.


## Requirements

- Python 3.11+
- macOS or Windows 10/11
- A Google account (for Gemini API key)
- A Telegram account (for the bot)


## License

MIT
