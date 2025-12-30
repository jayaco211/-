import sys
try:
    from youtube_api import search_and_filter_videos
    print("Import successful!")
except ImportError as e:
    print(f"Import failed: {e}")
except Exception as e:
    print(f"Other error: {e}")
