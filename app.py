import os
import re
import sqlite3
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

GUILD_ID = os.environ.get("DISCORD_GUILD_ID")
API_TOKEN = os.environ.get("UNBELIEVABOAT_TOKEN")
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

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    data = request.get_json(silent=True) or {}
    content = data.get("content", "")
    if not content:
        return jsonify({"status": "ignored"}), 200

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
            
            ub_url = f"https://unbelievaboat.com{GUILD_ID}/users/{discord_id}"
            ub_headers = {"Authorization": API_TOKEN, "Content-Type": "application/json"}
            requests.patch(ub_url, json={"cash": dna_to_give}, headers=ub_headers)
            
            discord_url = f"https://discord.com{CASINO_CHANNEL_ID}/messages"
            dc_headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}", "Content-Type": "application/json"}
            dc_data = {"content": f"<@{discord_id}> {dna_to_give}"}
            requests.post(discord_url, json=dc_data, headers=dc_headers)
            
            return jsonify({"status": "paid", "discord_id": discord_id, "amount": dna_to_give}), 200
            
        return jsonify({"status": "ignored", "reason": "Player not linked to a Discord ID"}), 200

    return jsonify({"status": "ignored"}), 200

@app.route('/interactions', methods=['POST'])
def handle_interactions():
    data = request.get_json(silent=True) or {}
    if data.get("type") == 1:
        return jsonify({"type": 1}), 200
        
    if data.get("type") == 2:
        options = data["data"].get("options", [])
        steam_id = options[0]["value"] if options else ""
        discord_id = data["member"]["user"]["id"]
        
        if len(steam_id) == 17 and steam_id.isdigit():
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO links (steam_id, discord_id) VALUES (?, ?)", (steam_id, discord_id))
            conn.commit()
            conn.close()
            
            return jsonify({
                "type": 4,
                "data": {"content": f"✅ Your SteamID `{steam_id}` has been successfully linked to your wallet!"}
            }), 200
            
    return jsonify({"type": 4, "data": {"content": "❌ Invalid command format."}}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

