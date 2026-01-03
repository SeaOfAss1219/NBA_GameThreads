# NBA Game Day Threads Discord Bot (Render Edition)

A Discord bot that automatically creates game day threads for NBA games. Runs daily via Render's cron job feature.

## What It Does

Every day at 12:00 PM EST, this bot:
1. Deletes all existing threads in your designated channel
2. Fetches today's NBA games from ESPN
3. Creates a thread for each game (e.g., "Celtics vs Lakers")
4. Posts an opening message with tip-off time in each thread

If there are no games that day, it simply does nothing.

---

## Setup Instructions

### Step 1: Create a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"** and give it a name (e.g., "NBA Game Threads")
3. Go to the **"Bot"** tab on the left sidebar
4. Click **"Add Bot"** and confirm
5. Under the bot's username, click **"Reset Token"** and copy the token
   - ⚠️ **Save this token somewhere safe—you'll need it later and can only view it once**
6. Scroll down and enable these **Privileged Gateway Intents**:
   - ✅ Server Members Intent
   - ✅ Message Content Intent

### Step 2: Invite the Bot to Your Server

1. In the Developer Portal, go to the **"OAuth2"** tab
2. Click **"URL Generator"**
3. Under **Scopes**, select:
   - ✅ `bot`
4. Under **Bot Permissions**, select:
   - ✅ `Manage Threads`
   - ✅ `Create Public Threads`
   - ✅ `Send Messages`
   - ✅ `Send Messages in Threads`
   - ✅ `Read Message History`
   - ✅ `View Channels`
5. Copy the generated URL at the bottom
6. Open the URL in your browser and select your server to invite the bot

### Step 3: Get Your Channel ID

1. In Discord, go to **User Settings** → **Advanced** → Enable **Developer Mode**
2. Right-click the channel where you want game threads created
3. Click **"Copy Channel ID"**
4. Save this ID—you'll need it in the next step

### Step 4: Push Code to GitHub

1. Create a new repository on GitHub
2. Upload these files to the repository:
   ```
   your-repo/
   ├── nba_game_threads.py
   ├── requirements.txt
   ├── render.yaml
   └── README.md
   ```

### Step 5: Set Up Render

1. Go to [render.com](https://render.com) and sign up (free)
2. Click **"New"** → **"Cron Job"**
3. Connect your GitHub account and select your repository
4. Configure the cron job:
   - **Name:** `nba-game-threads`
   - **Runtime:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python nba_game_threads.py`
   - **Schedule:** `0 17 * * *` (this is 12:00 PM EST / 17:00 UTC)
5. Add Environment Variables:
   - Click **"Add Environment Variable"**
   - Add `DISCORD_BOT_TOKEN` with your bot token
   - Add `DISCORD_CHANNEL_ID` with your channel ID
6. Click **"Create Cron Job"**

### Step 6: Test It

1. In your Render dashboard, go to your cron job
2. Click **"Trigger Run"** to manually run the bot
3. Check your Discord channel—threads should appear!

---

## Changing the Schedule

Edit the schedule in the Render dashboard or in `render.yaml`:

```yaml
schedule: "0 17 * * *"  # Currently 12:00 PM EST (17:00 UTC)
```

Cron format: `minute hour day month weekday`

Common examples:
- `"0 15 * * *"` = 10:00 AM EST
- `"0 18 * * *"` = 1:00 PM EST  
- `"0 20 * * *"` = 3:00 PM EST

> **Note:** Render uses UTC time. EST is UTC-5.

---

## Troubleshooting

**Bot doesn't create threads:**
- Check that the bot has the correct permissions in the channel
- Make sure the channel is a text channel (not a forum or voice channel)
- Check the Render logs for error messages

**Environment variables not working:**
- Make sure there are no extra spaces in the values
- Verify the channel ID is just the number (no quotes)

---

## How It Works

- **ESPN API:** Fetches live NBA schedule data (free, no API key needed)
- **discord.py:** Python library for interacting with Discord
- **Render Cron:** Runs the script on a schedule with reliable timing

The bot logs in, does its job, and immediately logs out. It only runs for a few seconds each day.

---

## License

MIT License - feel free to modify and use as you wish.
