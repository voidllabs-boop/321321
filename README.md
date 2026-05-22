# AI Roleplay Discord Bot

A Discord bot that runs private, Groq-powered AI roleplay sessions with Umamusume Pretty Derby characters. Built on **disnake** using the modern **Components V2** layout system — **no embeds** anywhere.

Made by United Servers of Sovereign Republics.

## Features

- **`/setup_rp`** posts a plain-text hub panel with a button to spawn a private roleplay channel.
- Each room is **locked to the requesting user and the bot** via channel overwrites.
- Inside the room, a Components V2 setup panel lets the user pick:
  - **Role** — `Trainer` or `Fan` (drastically rewires the system prompt and opening beat).
  - **Character** — one of 28 Umamusume Pretty Derby characters. The selector paginates 25-at-a-time using **◀ Page / Page ▶** buttons so it stays within Discord's 25-option select cap.
- AI is generated via the official **`groq`** Python SDK. The user's **server display name (nick)** is injected into the system prompt so the AI addresses them in-character.
- **Memory window** is a rolling FIFO:
  - **50 messages** for regular users.
  - **200 messages** for **server boosters** (detected via `member.premium_since`).
- Every AI reply ships with two buttons:
  - **Reroll** — drops the last AI reply from history, deletes the message, and asks Groq for a brand-new response with identical context.
  - **Continue** — keeps the prior reply, asks Groq to push the scene forward, and posts the next beat as a **new message** with the buttons re-attached to the newest reply.
- Plain-text footer `Made by United Servers of Sovereign Republics` on every panel/system message.

## Project layout

```
.
├── bot.py                 # Entrypoint
├── config.py              # Env-driven settings
├── requirements.txt
├── .env.example
├── core/
│   ├── characters.py      # Umamusume catalogue + paging helper
│   ├── prompts.py         # System-prompt templates (per role)
│   ├── history.py         # Rolling FIFO history
│   ├── groq_client.py     # Async Groq wrapper with error mapping
│   └── sessions.py        # In-memory session store keyed by channel
├── ui/
│   ├── footer.py
│   ├── hub.py             # /setup_rp hub LayoutView
│   ├── setup_view.py      # Role + character setup LayoutView (paginated)
│   └── rp_message.py      # Reroll / Continue layout per AI reply
└── cogs/
    ├── setup_rp.py        # Slash command + channel creation + setup flow
    └── roleplay.py        # In-room chat, Reroll, Continue
```

## Setup

1. **Python 3.10+** required.
2. Create a virtual environment and install deps:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and fill in:
   - `DISCORD_TOKEN` — from your Discord application's bot page.
   - `GROQ_API_KEY` — from <https://console.groq.com/keys>.
   - (Optional) `GROQ_MODEL` — defaults to `llama-3.3-70b-versatile`.
   - (Optional) `DEV_GUILD_IDS` — comma-separated guild IDs to scope slash commands while developing.
   - (Optional) `RP_CATEGORY_ID` — category to create private rooms under.

4. In the Discord Developer Portal, enable the **Message Content** and **Server Members** privileged intents for your bot.

5. Invite the bot to your server with the following permissions:
   - `View Channels`
   - `Send Messages`
   - `Read Message History`
   - `Manage Channels` (needed to create the private rooms)
   - `Manage Messages` (needed for Reroll to delete old replies)

6. Run:

   ```bash
   python bot.py
   ```

7. In Discord, run **`/setup_rp`** in any channel where the bot can post. Anyone with **Manage Channels** can post the hub. Users click **Create Roleplay Room** to spin up their private session.

## Tweaking system prompts

All prompt scaffolding lives in [`core/prompts.py`](core/prompts.py) as `str.format`-friendly templates:

- `CORE_DIRECTIVE` — the creative-writing contract (in-character, free action, no AI breaks).
- `ROLE_TRAINER_BRIEF` / `ROLE_FAN_BRIEF` — per-role scene scaffolding.
- `CHARACTER_BLOCK_TEMPLATE` — wraps the selected character's profile.
- `CONTINUE_NUDGE` — what the **Continue** button injects into history.

Add new Umamusume characters by appending to the `CHARACTERS` tuple in [`core/characters.py`](core/characters.py). The pagination handles any count automatically.

## Error handling

- **Groq timeouts / connection errors** are caught in `core/groq_client.py` and surfaced to the channel as an in-scene "scene stalled" message with a working **Reroll** button.
- **Missing channel permissions** are detected when creating the private room and reported to the user ephemerally.
- **Missing privileged intents** raise a clear error on startup explaining which toggles to flip in the developer portal.
