"""
Run once to get YouTube OAuth refresh token.
Usage:
    source yag-env/bin/activate
    python scripts/get_yt_token.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import os
from google_auth_oauthlib.flow import InstalledAppFlow

CLIENT_ID = os.environ.get("YT_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("YT_CLIENT_SECRET", "")

if not CLIENT_ID or not CLIENT_SECRET:
    print("❌ YT_CLIENT_ID и YT_CLIENT_SECRET не заполнены в .env")
    sys.exit(1)

flow = InstalledAppFlow.from_client_config(
    {
        "installed": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uris": ["http://localhost:8080/"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    },
    scopes=["https://www.googleapis.com/auth/youtube.upload"],
)

print("Открываю браузер для авторизации...")
creds = flow.run_local_server(port=8080, open_browser=True)

print("\n✅ Успешно!\n")
print(f"YT_REFRESH_TOKEN={creds.refresh_token}")
print("\nВставь эту строку в .env")
