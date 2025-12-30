from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pandas as pd
import isodate
from datetime import datetime

def get_youtube_client(api_key):
    """Initializes the YouTube Data API client."""
    try:
        if not api_key:
            return None
        return build('youtube', 'v3', developerKey=api_key)
    except Exception as e:
        print(f"Error initializing YouTube API: {e}")
        return None

def search_videos(youtube, query, start_date=None, end_date=None, max_results=50, category_id=None):
    """
    Searches for videos on YouTube.
    
    Args:
        youtube: The initialized YouTube client.
        query (str): The search query.
        start_date (date): Filter after this date.
        end_date (date): Filter before this date.
        max_results (int): Max number of videos to retrieve.
        category_id (str): Optional YouTube Video Category ID to filter by.
    
    Returns:
        list: A list of video dictionaries (id, title, channelId, publishedAt).
    """
    if not youtube:
        return []

    # Convert dates to RFC 3339 format (e.g., 2023-01-01T00:00:00Z)
    published_after = f"{start_date.isoformat()}T00:00:00Z" if start_date else None
    published_before = f"{end_date.isoformat()}T23:59:59Z" if end_date else None

    videos = []
    next_page_token = None
    
    while len(videos) < max_results:
        # Calculate how many to fetch in this batch (max 50 per request)
        remaining = max_results - len(videos)
        batch_size = min(remaining, 50)
        
        try:
            search_request = youtube.search().list(
                q=query,
                type='video',
                part='id,snippet',
                order='viewCount', # Sort by popularity initially
                maxResults=batch_size,
                publishedAfter=published_after,
                publishedBefore=published_before,
                videoCategoryId=category_id,
                pageToken=next_page_token
            )
            search_response = search_request.execute()

            for item in search_response.get('items', []):
                videos.append({
                    'video_id': item['id']['videoId'],
                    'title': item['snippet']['title'],
                    'channel_id': item['snippet']['channelId'],
                    'channel_title': item['snippet']['channelTitle'],
                    'published_at': item['snippet']['publishedAt'],
                    'thumbnail': item['snippet']['thumbnails']['high']['url'],
                    'video_url': f"https://www.youtube.com/watch?v={item['id']['videoId']}"
                })
            
            next_page_token = search_response.get('nextPageToken')
            if not next_page_token:
                break
        except HttpError as e:
            print(f"Error during search: {e}")
            break
            
    return videos

def get_video_details(youtube, video_data):
    """
    Fetches detailed statistics for a list of videos and merges with subscriber count.
    
    Args:
        youtube: The YouTube client.
        video_data (list): List of video dictionaries from search_videos.
        
    Returns:
        pd.DataFrame: DataFrame containing full analysis data.
    """
    if not video_data:
        return pd.DataFrame()

    video_ids = [v['video_id'] for v in video_data]
    channel_ids = list(set([v['channel_id'] for v in video_data]))

    # 1. Get Video Stats
    try:
        video_stats = {}
        for i in range(0, len(video_ids), 50):
            chunk = video_ids[i:i+50]
            video_response = youtube.videos().list(
                part='statistics,contentDetails',
                id=','.join(chunk)
            ).execute()
            
            for item in video_response.get('items', []):
                stats = item['statistics']
                content_details = item['contentDetails']
                duration_iso = content_details.get('duration', 'PT0S')
                try:
                    duration_td = isodate.parse_duration(duration_iso)
                    # Format duration as HH:MM:SS or MM:SS
                    total_seconds = int(duration_td.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    if hours > 0:
                        duration_str = f"{hours}:{minutes:02}:{seconds:02}"
                    else:
                        duration_str = f"{minutes}:{seconds:02}"
                except:
                    duration_str = "0:00"
                    total_seconds = 0

                video_stats[item['id']] = {
                    'view_count': int(stats.get('viewCount', 0)),
                    'like_count': int(stats.get('likeCount', 0)),
                    'comment_count': int(stats.get('commentCount', 0)),
                    'duration': duration_str,
                    'duration_sec': total_seconds
                }

    except HttpError as e:
        print(f"Error fetching video stats: {e}")
        return pd.DataFrame()

    # 2. Get Channel Stats (for Subscriber Count)
    try:
        # Check if we have too many channels (chunks of 50)
        channel_stats = {}
        for i in range(0, len(channel_ids), 50):
            chunk = channel_ids[i:i+50]
            # Remove duplicated channel IDs within chunk if any
            chunk = list(set(chunk))
            
            channel_response = youtube.channels().list(
                part='statistics',
                id=','.join(chunk)
            ).execute()
            
            for item in channel_response.get('items', []):
                sub_count = item['statistics'].get('subscriberCount', 0)
                channel_stats[item['id']] = int(sub_count) if not item['statistics'].get('hiddenSubscriberCount') else 0

    except HttpError as e:
        print(f"Error fetching channel stats: {e}")
        # Continue without crashing, just sub count will be 0

    # 3. Merge Data
    final_data = []
    for video in video_data:
        vid = video['video_id']
        cid = video['channel_id']
        
        stats = video_stats.get(vid, {'view_count': 0, 'like_count': 0, 'comment_count': 0, 'duration': "0:00", 'duration_sec': 0})
        sub_count = channel_stats.get(cid, 0)
        
        # Calculate Ratio (Views / Subscribers)
        ratio = 0.0
        if sub_count > 0:
            ratio = round(stats['view_count'] / sub_count, 2)

        # Format Published At
        pub_date = datetime.strptime(video['published_at'], "%Y-%m-%dT%H:%M:%SZ")

        final_data.append({
            'Thumbnail': video['thumbnail'],
            'Title': video['title'],
            'Duration': stats['duration'],
            'DurationSec': stats['duration_sec'],
            'Channel': video['channel_title'],
            'Published': pub_date.strftime("%Y-%m-%d"),
            'Views': stats['view_count'],
            'Likes': stats['like_count'],
            'Comments': stats['comment_count'],
            'Subscribers': sub_count,
            'Performance (Views/Subs)': f"{ratio}x",
            'Link': video['video_url']
        })

    return pd.DataFrame(final_data)

def search_and_filter_videos(youtube, query, start_date=None, end_date=None, target_count=50, category_id=None, min_duration_sec=None, max_duration_sec=None, region_code=None, relevance_language=None):
    """
    Searches, fetches details, and filters videos until the target_count is met.
    Guarantees 'target_count' filtered results if available within safety limits.
    """
    valid_videos_df = pd.DataFrame()
    next_page_token = None
    processed_count = 0
    safety_limit = 1000  # Increased to 1000 to ensure we find 30 videos even with strict filters
    
    # Optimization: Use API's videoDuration if possible
    api_duration_param = None
    if max_duration_sec and max_duration_sec <= 240:
        api_duration_param = 'short' # < 4 mins
    # We can't easily use 'medium' or 'long' for our specific >3m split without missing data

    # RFC 3339 Dates
    published_after = f"{start_date.isoformat()}T00:00:00Z" if start_date else None
    published_before = f"{end_date.isoformat()}T23:59:59Z" if end_date else None

    # print(f"DEBUG: Starting strict search. Target: {target_count}, Query: {query}, Region: {region_code}")
    print(f"DEBUG: Search params - Query: {query}, DurationParam: {api_duration_param}, Region: {region_code}, MinDur: {min_duration_sec}, MaxDur: {max_duration_sec}")

    while len(valid_videos_df) < target_count and processed_count < safety_limit:
        try:
            # 1. Search Batch (50 items)
            search_request = youtube.search().list(
                q=query,
                type='video',
                part='id,snippet',
                order='viewCount',
                maxResults=50,
                publishedAfter=published_after,
                publishedBefore=published_before,
                videoCategoryId=category_id,
                regionCode=region_code,
                relevanceLanguage=relevance_language,
                videoDuration=api_duration_param,
                pageToken=next_page_token
            )
            search_response = search_request.execute()
            
            items = search_response.get('items', [])
            print(f"DEBUG: API returned {len(items)} items. PageToken: {next_page_token}")
            
            if not items:
                print("DEBUG: No more items from search API.")
                break
                
            # Parse raw items
            raw_videos = []
            for item in items:
                raw_videos.append({
                    'video_id': item['id']['videoId'],
                    'title': item['snippet']['title'],
                    'channel_id': item['snippet']['channelId'],
                    'channel_title': item['snippet']['channelTitle'],
                    'published_at': item['snippet']['publishedAt'],
                    'thumbnail': item['snippet']['thumbnails']['high']['url'],
                    'video_url': f"https://www.youtube.com/watch?v={item['id']['videoId']}"
                })
            
            processed_count += len(raw_videos)
            
            # 2. Get Details (Duration, Views, etc.)
            batch_df = get_video_details(youtube, raw_videos)
            
            if not batch_df.empty and 'DurationSec' in batch_df.columns:
                # 3. Filter by Duration
                filtered_df = batch_df.copy()
                
                if min_duration_sec is not None:
                    filtered_df = filtered_df[filtered_df['DurationSec'] >= min_duration_sec]
                
                if max_duration_sec is not None:
                    filtered_df = filtered_df[filtered_df['DurationSec'] <= max_duration_sec]
                
                print(f"DEBUG: Batch size {len(batch_df)} -> Filtered down to {len(filtered_df)}")

                if not filtered_df.empty:
                    valid_videos_df = pd.concat([valid_videos_df, filtered_df], ignore_index=True)
            
            # 4. Check if we need more
            if len(valid_videos_df) >= target_count:
                print("DEBUG: Target count met.")
                break
                
            next_page_token = search_response.get('nextPageToken')
            if not next_page_token:
                print("DEBUG: End of results (no next page).")
                break
                
        except HttpError as e:
            if "quotaExceeded" in str(e):
                print("DEBUG: Quota exceeded, raising error.")
                raise e
            print(f"API Error in loop: {e}")
            break
            
    # Final Slice and Sort
    if not valid_videos_df.empty:
        valid_videos_df = valid_videos_df.sort_values(by='Views', ascending=False)
        return valid_videos_df.head(target_count)

    return pd.DataFrame()