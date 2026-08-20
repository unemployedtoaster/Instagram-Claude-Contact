# 🤖 Insta Claude Bot

An Instagram DM bot that:
- **Watches for reel links you send** → downloads them → gets Claude's reaction → DMs it back to you
- **Randomly sends you reels** throughout the day (funny, coding, AI content)

Runs entirely on **GitHub Actions** — no server needed, completely free.

---

## Setup

### 1. Fork / create this repo on GitHub

### 2. Add these GitHub Secrets
Go to `Settings → Secrets and variables → Actions → New repository secret`

| Secret | Value |
|--------|-------|
| `BOT_INSTA_USERNAME` | Username of your bot/burner IG account |
| `BOT_INSTA_PASSWORD` | Password of bot account |
| `MY_INSTA_USERNAME` | YOUR username (receives the DMs) |
| `ANTHROPIC_API_KEY` | Your Anthropic API key |

### 3. Enable Actions
Go to the `Actions` tab and enable workflows.

### 4. Test it
Hit `Run workflow` manually to test before waiting for the hourly cron.

---

## How it works

- Runs **every hour** via GitHub Actions cron
- Each run checks your DMs for new reel links → downloads → Claude reacts → replies
- Each run rolls a **20% dice** → if it lands, scrapes and sends you a random reel
- Statistically sends you **4-5 random reels per day** at unpredictable times
- Max **5 random reels per day** cap so it doesn't spam you

---

## Customise

Edit `SCRAPE_ACCOUNTS` in `main.py` to change which accounts it scrapes reels from.

Edit the `captions` list to change what message it sends with the reel.

Change `0.20` probability or `5` daily cap to adjust reel frequency.
