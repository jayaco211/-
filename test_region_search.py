import sys
import os
# Force UTF-8 explicitly for Windows
sys.stdout.reconfigure(encoding='utf-8')

import streamlit as st

from youtube_api import get_youtube_client, search_videos, search_and_filter_videos
from datetime import date, timedelta

# Mock API Key from secrets (assuming running in same environment or just hardcode for test if needed but let's try to load)
# Since this is a script, st.secrets might not work if not run via streamlit.
# I will try to read the secrets file directly or rely on the user having it in env, 
# but for this environment, I'll try to read the toml.
import toml

try:
    secrets = toml.load(".streamlit/secrets.toml")
    API_KEY = secrets["general"]["YOUTUBE_API_KEY"]
except Exception as e:
    print(f"Could not load API Key: {e}")
    exit()

youtube = get_youtube_client(API_KEY)

def test_query(query, region, lang, description):
    print(f"\n--- Test: {description} (Query='{query}', Region='{region}', Lang='{lang}') ---")
    results = search_and_filter_videos(
        youtube=youtube,
        query=query,
        start_date=date.today() - timedelta(days=7),
        end_date=date.today(),
        target_count=5,
        region_code=region,
        relevance_language=lang
    )
    if not results.empty:
        for idx, row in results.iterrows():
            title = row['Title']
            try:
                print(f"{idx+1}. [{row['Channel']}] {title} (Views: {row['Views']})")
            except UnicodeEncodeError:
                print(f"{idx+1}. [{row['Channel']}] (Title has emojis/unicode) (Views: {row['Views']})")
    else:
        print("No results found.")

# 1. Neutral Keywork (News) - Region KR
test_query("News", "KR", "ko", "Global Keyword in KR")

# 2. Neutral Keyword (News) - Region JP
test_query("News", "JP", "ja", "Global Keyword in JP")

# 3. Korean Keyword (경제) - Region JP
test_query("경제", "JP", "ja", "Korean Keyword in JP (Expecting Korean results mostly)")

# 4. Japanese Keyword (経済) - Region JP
test_query("経済", "JP", "ja", "Japanese Keyword in JP (Expecting Japanese results)")
