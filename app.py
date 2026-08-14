import os
import re
import sqlite3
import discord
from discord.ext import commands
from aiohttp import web
import asyncio

BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
CASINO_CHANNEL_ID = os.environ.get("CASINO_CHANNEL_ID")

DB_FILE = "player_links.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS links (steam_id TEXT PRIMARY KEY, discord_id TEXT)")
    conn.commit()
    conn.close()

init_db()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")

@bot.command(name="link")
async def link_steam(ctx, steam_id: str):
    # Match by text name of the channel instead of a buggy number key
    if ctx.channel.name != "steam-link":
        try:
            await ctx.message.delete()
        except:
            pass
        warning = await ctx.send(f"❌ {ctx.author.mention}, you can only link your account inside the `#steam-link` channel!")
        await asyncio.sleep(5)
        await warning.delete()
        return

    if len(steam_id) == 17 and steam_id.isdigit():
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO links (steam_id, discord_id) VALUES (?, ?)", (steam_id, str(ctx.author.id)))
        conn.commit()
        conn.close()
        
        try:
            await ctx.message.delete()
        except:
            pass
            
        casino_channel = bot.get_channel(int(CASINO_CHANNEL_ID))
        if casino_channel:
            await casino_channel.send(f"✅ {ctx.author.mention}, your account has been successfully linked!")
    else:
        casino_channel = bot.get_channel(int(CASINO_CHANNEL_ID))
        if casino_channel:
            await casino_channel.send(f"❌ {ctx.author.mention}, that SteamID format is invalid. It must be exactly 17 digits.")
        try:
            await ctx.message.delete()
        except:
            pass

async def handle_game_webhook(request):
    try:
        data = await request.json()
    except Exception:
        return web.Response(text="Invalid JSON", status=400)
        
    content = data.get("content", "")
    match = re.search(r"Player\s+\S+\s+<(\d+):.*?Hours:\s+(\d+)\s+and\s+Minutes:\s+(\d+)", content)
    
    if match:
        steam_id = match.group(1)
        hours = int(match.group(2))
        minutes = int(match.group(3))
        
        total_minutes = (hours * 60) + minutes
        dna_to_give = total_minutes * 10
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT discord_id FROM links WHERE steam_id = ?", (steam_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            discord_id = row[0]
            casino_channel = bot.get_channel(int(CASINO_CHANNEL_ID))
            if casino_channel:
                await casino_channel.send(f"!add-money <@{discord_id}> {dna_to_give}")
                return web.Response(text="Paid", status=200)
                
    return web.Response(text="Ignored", status=200)

async def main():
    app = web.Application()
    app.router.add_post('/webhook', handle_game_webhook)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 5000)))
    await site.start()
    
    async with bot:
        await bot.start(BOT_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
