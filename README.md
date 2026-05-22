# InterServer Bot

A bot for cross-server chat using Discord Webhooks.
Messages from linked channels automatically appear on all other servers in the network,
as if the user wrote them directly, with the origin server noted in their username.


## Project structure

```
interserver-bot/
|-- bot.py                   # Entry point
|-- requirements.txt
|-- interserver.db           # SQLite database (created automatically)
|-- cogs/
|   `-- interserver.py       # Core logic and slash commands
`-- utils/
    |-- database.py          # SQLite access via aiosqlite
    `-- webhook_manager.py   # Webhook creation and sending
```


## Setup

```bash
# 1. Copy the project files
# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your bot token
export DISCORD_TOKEN="your_token_here"
# Or paste it directly into bot.py: TOKEN = "your_token_here"

# 4. Run
python bot.py
```


## Required bot permissions

### Privileged Gateway Intents (Discord Developer Portal)
- Message Content Intent - needed to read message text

### Bot Permissions (when adding to a server)
- Read Messages / View Channels
- Send Messages
- Manage Webhooks  (required)
- Attach Files
- Read Message History


## Slash commands

| Command     | Description                              | Access        |
|-------------|------------------------------------------|---------------|
| `/link`     | Link this channel to the network         | Administrator |
| `/unlink`   | Unlink this channel                      | Administrator |
| `/network`  | List all channels and servers in network | Anyone        |


## How it works

```
[User sends a message in #global on Server A]
         |
  on_message fires
         |
  Builds: username = "John (Server A)", avatar from user profile
         |
  Downloads all attachments (<= 8 MB)
         |
  For each other channel in the network:
    `- Verifies webhook (recreates if deleted)
    `- Sends via webhook with username + jump link
```


## Features

- Webhook auto-recovery - if a webhook is deleted manually, the bot recreates it on the next message
- File forwarding - images, documents, video (up to 8 MB)
- Jump link - each relayed message includes a link back to the original
- SQLite storage - no external database required
- Ephemeral replies - /link and /unlink responses are only visible to the administrator
