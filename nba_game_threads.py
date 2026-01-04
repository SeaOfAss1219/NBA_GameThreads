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


def get_today_est():
    """Get today's date in EST timezone."""
    est = timezone(timedelta(hours=-5))
    now_est = datetime.now(est)
    return now_est.strftime("%Y%m%d")


async def fetch_todays_games():
    """Fetch today's NBA games from ESPN API using explicit EST date."""
    today = get_today_est()
    url = f"{ESPN_API_URL}?dates={today}"
    
    print(f"Fetching games for date: {today}")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
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
        return None, None, None, None
    
    competition = competitions[0]
    competitors = competition.get("competitors", [])
    
    # Get game status
    status = event.get("status", {}).get("type", {}).get("name", "")
    
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
    game_datetime = None
    
    if game_time_str:
        try:
            # ESPN returns time in UTC (ISO format)
            utc_time = datetime.fromisoformat(game_time_str.replace("Z", "+00:00"))
            # Convert to EST (UTC-5)
            est = timezone(timedelta(hours=-5))
            est_time = utc_time.astimezone(est)
            tipoff_time = est_time.strftime("%I:%M %p").lstrip("0")  # e.g., "7:30 PM"
            game_datetime = est_time
        except Exception as e:
            print(f"Error parsing game time: {e}")
            tipoff_time = "TBD"
    
    return away_team, home_team, tipoff_time, status


def is_upcoming_game(status, game_datetime=None):
    """Check if a game is upcoming (not started or finished)."""
    # Filter out completed games
    completed_statuses = ["STATUS_FINAL", "STATUS_POSTPONED", "STATUS_CANCELED"]
    
    if status in completed_statuses:
        return False
    
    # If we have a game time, also check if it's in the future
    if game_datetime:
        est = timezone(timedelta(hours=-5))
        now_est = datetime.now(est)
        # Allow games that started up to 3 hours ago (in case game is in progress)
        # but filter out games that ended (handled by status check above)
        if game_datetime < now_est - timedelta(hours=6):
            return False
    
    return True


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
    
    # Print current time in EST for debugging
    est = timezone(timedelta(hours=-5))
    now_est = datetime.now(est)
    print(f"Current time (EST): {now_est.strftime('%Y-%m-%d %I:%M %p')}")
    
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
        print(f"Found {len(games)} total games")
        
        # Create a thread for each upcoming game
        created_count = 0
        for game in games:
            away_team, home_team, tipoff_time, status = parse_game_info(game)
            
            if away_team and home_team:
                if is_upcoming_game(status):
                    await create_game_thread(channel, away_team, home_team, tipoff_time or "TBD")
                    created_count += 1
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(1)
                else:
                    print(f"Skipping completed/old game: {away_team} vs {home_team} (status: {status})")
        
        print(f"Created {created_count} game threads")
    
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

