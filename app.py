import os
import re
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

GUILD_ID = os.environ.get("DISCORD_GUILD_ID")
API_TOKEN = os.environ.get("UNBELIEVABOAT_TOKEN")

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    data = request.get_json(silent=True) or {}
    content = data.get("content", "")
    if not content:
        return jsonify({"status": "ignored", "reason": "empty content"}), 200

    match = re.search(r"Player\s+(\S+).*?Hours:\s+(\d+)\s+and\s+Minutes:\s+(\d+)", content)
    
    if match:
        player_name = match.group(1)
        hours = int(match.group(2))
        minutes = int(match.group(3))
        
        total_minutes = (hours * 60) + minutes
        dna_to_give = total_minutes * 10
        
        print(f"Parsed {player_name}: Calculated {dna_to_give} DNA.")
        return jsonify({"status": "success", "player": player_name, "dna": dna_to_give}), 200

    return jsonify({"status": "ignored", "reason": "no match"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
