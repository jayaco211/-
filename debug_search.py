import sys
import os
# Force UTF-8 explicitly for Windows
sys.stdout.reconfigure(encoding='utf-8')

import streamlit as st
import toml
from youtube_api import get_youtube_client, search_and_filter_videos
from datetime import date, timedelta

# Load API Key
try:
    secrets = toml.load(".streamlit/secrets.toml")
    API_KEY = secrets["general"]["YOUTUBE_API_KEY"]
except Exception as e:
    print(f"Could not load API Key: {e}")
    exit()

youtube = get_youtube_client(API_KEY)

def test_search(query, duration_option, region="KR"):
    print(f"\n==================================================")
    print(f"TEST: Query='{query}', Duration='{duration_option}', Region='{region}'")
    
    min_sec, max_sec = None, None
    if duration_option == "Shorts":
        max_sec = 180
    elif duration_option == "Long":
        min_sec = 180
    
    # Translate if JP
    if region == "JP" and query == "경제":
        query = "経済" # Simulate translation

    results = search_and_filter_videos(
        youtube=youtube,
        query=query,
        start_date=date.today() - timedelta(days=30),
        end_date=date.today(),
        target_count=30,
        min_duration_sec=min_sec,
        max_duration_sec=max_sec,
        region_code=region
    )
    
    print(f"RESULT: Found {len(results)} videos.")
    if not results.empty:
        print(results[['Title', 'Duration', 'Views']].head(3))

# Test 1: Shorts Search (Should use API videoDuration='short')
test_search("news", "Shorts", "KR")

# Test 2: Long Search (API videoDuration=None, manual filter)
test_search("news", "Long", "KR")
