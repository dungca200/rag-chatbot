#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = ["requests", "python-dotenv"]
# ///

import os, sys, json, subprocess
from pathlib import Path
from dotenv import load_dotenv
import requests

# Load .env from project root
load_dotenv(Path(__file__).parent.parent.parent / ".env")

# Read stdin (required by hook)
try:
    json.load(sys.stdin)
except:
    pass

api_key = os.getenv('ELEVENLABS_API_KEY')
if not api_key:
    sys.exit(0)

try:
    response = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{os.getenv('ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM')}",
        headers={'Accept': 'audio/mpeg', 'Content-Type': 'application/json', 'xi-api-key': api_key},
        json={'text': 'Task completed.', 'model_id': 'eleven_turbo_v2_5'},
        timeout=10
    )

    if response.status_code == 200:
        with open('/tmp/claude_tts.mp3', 'wb') as f:
            f.write(response.content)
        subprocess.run(['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', '/tmp/claude_tts.mp3'], timeout=15)
        os.unlink('/tmp/claude_tts.mp3')
except:
    pass
