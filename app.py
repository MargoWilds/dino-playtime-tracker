import os
import re
import sqlite3
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

GUILD_ID = os.environ.get("DISCORD_GUILD_ID")
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
CASINO_CHANNEL_ID = os.environ.get("CASINO_CHANNEL_ID")

DB_FILE = "player_links.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS links (
            steam_id TEXT PRIMARY KEY,
            discord_id TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# 1. PAYOUT PIPELINE: Processes your Beasts of Bermuda logout webhooks
@app.route('/webhook', methods=['POST'])
def handle_webhook():
    data = request.get_json(silent=True) or {}
    content = data.get("content", "")
    if not content:
        return jsonify({"status": "ignored"}), 200

    # Handles user link submissions via the public log channel
    if content.startswith("!link "):
        try:
            parts = content.split()
            steam_id = parts[1]
            author_id = data.get("author", {}).get("id") or data.get("member", {}).get("user", {}).get("id")
            
            if author_id and len(steam_id) == 17 and steam_id.isdigit():
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("INSERT OR REPLACE INTO links (steam_id, discord_id) VALUES (?, ?)", (steam_id, author_id))
                conn.commit()
                conn.close()
                
                # Public registration success reply tag
                discord_url = f"https://discord.com{CASINO_CHANNEL_ID}/messages"
                dc_headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}", "Content-Type": "application/json"}
                dc_data = {"content": f"✅ <@{author_id}>, your SteamID `{steam_id}` is now securely linked to your wallet!"}
                requests.post(discord_url, json=dc_data, headers=dc_headers)
                return jsonify({"status": "linked"}), 200
        except Exception:
            pass

    # Standard log parser for calculating dynamic playtime rewards
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
            discord_url = f"https://discord.com{CASINO_CHANNEL_ID}/messages"
            dc_headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}", "Content-Type": "application/json"}
            dc_data = {"content": f"!add-money <@{discord_id}> {dna_to_give}"}
            requests.post(discord_url, json=dc_data, headers=dc_headers)
            return jsonify({"status": "paid", "amount": dna_to_give}), 200

    return jsonify({"status": "ignored"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
