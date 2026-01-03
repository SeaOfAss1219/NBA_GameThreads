import os
import asyncio
import aiohttp
import discord
from discord.ext import commands
from datetime import datetime, timezone, timedelta

# Configuration from environment variables
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.environ.get("DISCORD_CHANNEL_ID", 0))

# ESPN NBA Scoreboard API endpoint
ESPN_API_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"

# Bot setup with necessary intents
intents = discord.Intents.default()
intents.guilds = True
intents.guild_messages = True
bot = commands.Bot(command_prefix="!", intents=intents)


async def fetch_todays_games():
    """Fetch today's NBA games from ESPN API."""
    async with aiohttp.ClientSession() as session:
        async with session.get(ESPN_API_URL) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("events", [])
            else:
                print(f"Failed to fetch games: {response.status}")
                return []


def parse_game_info(event):
    """Extract away and home team names and game time from an ESPN event."""
    competitions = event.get("competitions", [])
    if not competitions:
        return None, None, None
    
    competition = competitions[0]
    competitors = competition.get("competitors", [])
    
    away_team = None
    home_team = None
    
    for competitor in competitors:
        team_name = competitor.get("team", {}).get("shortDisplayName", "Unknown")
        if competitor.get("homeAway") == "away":
            away_team = team_name
        elif competitor.get("homeAway") == "home":
            home_team = team_name
    
    # Get game time and convert to EST
    game_time_str = event.get("date", "")
    tipoff_time = None
    
    if game_time_str:
        try:
            # ESPN returns time in UTC (ISO format)
            utc_time = datetime.fromisoformat(game_time_str.replace("Z", "+00:00"))
            # Convert to EST (UTC-5)
            est = timezone(timedelta(hours=-5))
            est_time = utc_time.astimezone(est)
            tipoff_time = est_time.strftime("%I:%M %p").lstrip("0")  # e.g., "7:30 PM"
        except Exception as e:
            print(f"Error parsing game time: {e}")
            tipoff_time = "TBD"
    
    return away_team, home_team, tipoff_time


async def delete_existing_threads(channel):
    """Delete all existing threads in the channel."""
    deleted_count = 0
    
    # Get all active threads in the guild
    threads = channel.guild.threads
    for thread in threads:
        if thread.parent_id == channel.id:
            try:
                await thread.delete()
                print(f"Deleted thread: {thread.name}")
                deleted_count += 1
            except discord.errors.Forbidden:
                print(f"No permission to delete thread: {thread.name}")
            except discord.errors.NotFound:
                print(f"Thread already deleted: {thread.name}")
    
    # Also check archived threads
    async for thread in channel.archived_threads(limit=100):
        try:
            await thread.delete()
            print(f"Deleted archived thread: {thread.name}")
            deleted_count += 1
        except discord.errors.Forbidden:
            print(f"No permission to delete archived thread: {thread.name}")
        except discord.errors.NotFound:
            print(f"Archived thread already deleted: {thread.name}")
    
    return deleted_count


async def create_game_thread(channel, away_team, home_team, tipoff_time):
    """Create a thread for a game."""
    thread_name = f"{away_team} vs {home_team}"
    opening_message = f"This is the game day chat room for the {away_team} vs {home_team} game!\n\nTip-off time: {tipoff_time} EST"
    
    try:
        # Create a public thread
        thread = await channel.create_thread(
            name=thread_name,
            type=discord.ChannelType.public_thread,
            reason="NBA Game Day Thread"
        )
        
        # Send the opening message
        await thread.send(opening_message)
        print(f"Created thread: {thread_name}")
        return thread
    except discord.errors.Forbidden:
        print(f"No permission to create thread: {thread_name}")
        return None
    except Exception as e:
        print(f"Error creating thread {thread_name}: {e}")
        return None


@bot.event
async def on_ready():
    """Run when the bot is ready."""
    print(f"Logged in as {bot.user}")
    
    # Get the target channel
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print(f"Could not find channel with ID: {CHANNEL_ID}")
        await bot.close()
        return
    
    print(f"Found channel: {channel.name}")
    
    # Delete existing threads
    print("Deleting existing threads...")
    deleted = await delete_existing_threads(channel)
    print(f"Deleted {deleted} existing threads")
    
    # Fetch today's games
    print("Fetching today's NBA games...")
    games = await fetch_todays_games()
    
    if not games:
        print("No games scheduled for today")
    else:
        print(f"Found {len(games)} games")
        
        # Create a thread for each game
        for game in games:
            away_team, home_team, tipoff_time = parse_game_info(game)
            if away_team and home_team:
                await create_game_thread(channel, away_team, home_team, tipoff_time or "TBD")
                # Small delay to avoid rate limiting
                await asyncio.sleep(1)
    
    print("Done! Shutting down...")
    await bot.close()


def main():
    """Main entry point."""
    if not DISCORD_BOT_TOKEN:
        print("Error: DISCORD_BOT_TOKEN environment variable not set")
        return
    
    if not CHANNEL_ID:
        print("Error: DISCORD_CHANNEL_ID environment variable not set")
        return
    
    print("Starting NBA Game Threads Bot...")
    bot.run(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    main()
