import streamlit as st
import pandas as pd
from datetime import date, timedelta
from youtube_api import get_youtube_client, search_videos, get_video_details, search_and_filter_videos
from deep_translator import GoogleTranslator
import io
from datetime import date, timedelta
from youtube_api import get_youtube_client, search_videos, get_video_details, search_and_filter_videos
import io

# Page Config
st.set_page_config(page_title="유튜브 트렌드 분석기", page_icon="📈", layout="wide")

st.title("📈 유튜브 트렌드 분석기")

# Sidebar - Settings
with st.sidebar:
    st.header("설정")
    
    # API Key Input
    default_api_key = st.secrets.get("general", {}).get("YOUTUBE_API_KEY", "")
    
    if "api_key" not in st.session_state:
        st.session_state["api_key"] = default_api_key
    
    api_key_input = st.text_input("유튜브 데이터 API 키 (YouTube Data API Key)", value=st.session_state["api_key"], type="password")
    
    if api_key_input:
        st.session_state["api_key"] = api_key_input
        
    st.markdown("---")
    st.subheader("검색 필터")
    
    # Search Query
    # Keyword search is generally better for content discovery than tag search
    query = st.text_input("검색어 (예: 우주 미스터리, 심해 공포)", "")



    # Date Range Variables

    # Date Range Variables
    if "search_start_date" not in st.session_state:
        st.session_state["search_start_date"] = date.today() - timedelta(days=30)
    if "search_end_date" not in st.session_state:
        st.session_state["search_end_date"] = date.today()

    st.write("검색 기간")
    # Preset Buttons
    b_col1, b_col2, b_col3, b_col4 = st.columns(4)
    with b_col1:
        if st.button("1주일", use_container_width=True):
            st.session_state["search_start_date"] = date.today() - timedelta(weeks=1)
            st.session_state["search_end_date"] = date.today()
    with b_col2:
        if st.button("1개월", use_container_width=True):
            st.session_state["search_start_date"] = date.today() - timedelta(days=30)
            st.session_state["search_end_date"] = date.today()
    with b_col3:
        if st.button("6개월", use_container_width=True):
            st.session_state["search_start_date"] = date.today() - timedelta(days=180)
            st.session_state["search_end_date"] = date.today()
    with b_col4:
        if st.button("1년", use_container_width=True):
            st.session_state["search_start_date"] = date.today() - timedelta(days=365)
            st.session_state["search_end_date"] = date.today()

    # Date Inputs (Connected to Session State)
    d_col1, d_col2 = st.columns(2)
    with d_col1:
        start_date = st.date_input("시작 날짜", value=st.session_state["search_start_date"])
    with d_col2:
        end_date = st.date_input("종료 날짜", value=st.session_state["search_end_date"])

    # Update state if user manually changes picker
    st.session_state["search_start_date"] = start_date
    st.session_state["search_end_date"] = end_date
        
    # Updated per user request: Max 30 results
    max_results = st.slider("최대 검색 결과 수", 10, 30, 30)
    
    # Duration Filter
    # User requested: Merge Medium into Shorts (Shorts = < 3 min), Long = (> 3 min)
    duration_option = st.selectbox(
        "영상 길이 필터",
        ["모든 영상", "쇼츠 (3분 미만)", "장편 (3분 이상)"],
        index=0
    )
    
    # Region Filter
    country_option = st.selectbox(
        "검색 국가 (지역 필터)",
        ["전세계 (All)", "한국 (KR)", "일본 (JP)"],
        index=1
    )
    
    # Custom CSS to force pointer cursor on selectboxes (Attempt to target streamlit widgets)
    st.markdown("""
        <style>
        div[data-baseweb="select"] {
            cursor: pointer !important;
        }
        div[role="listbox"] ul {
            cursor: pointer !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    start_search = st.button("동영상 검색", type="primary", use_container_width=True)


# Helper function for Korean number formatting
def format_kr_number(num):
    if not isinstance(num, (int, float)):
        return num
    if num >= 10000:
        return f"{num/10000:.1f}만"
    return f"{num:,}"

if not st.session_state["api_key"]:
    st.warning("⚠️ 왼쪽 사이드바에 'YouTube Data API Key'를 입력해주세요.")
    st.info("키는 [구글 클라우드 콘솔](https://console.cloud.google.com/)에서 발급받을 수 있습니다.")
else:
    if start_search:
        with st.spinner("유튜브 검색 중..."):
            try:
                youtube = get_youtube_client(st.session_state["api_key"])
                
                # Map duration option to seconds (min, max)
                min_sec, max_sec = None, None
                
                # Logic: Shorts < 3min (180s), Long >= 3min (180s)
                if "쇼츠" in duration_option:
                    max_sec = 180
                elif "장편" in duration_option:
                    min_sec = 180
                    
                # Map Country Option
                region_code = None
                relevance_lang = None
                
                if "한국" in country_option:
                    region_code = 'KR'
                    relevance_lang = 'ko'
                elif "일본" in country_option:
                    region_code = 'JP'
                    relevance_lang = 'ja'
                    
                    # Auto-translate query to Japanese for better results
                    # Only translate if query contains Hangul (Korean characters)
                    if any(ord('가') <= ord(char) <= ord('힣') for char in query):
                         try:
                             translated_query = GoogleTranslator(source='auto', target='ja').translate(query)
                             st.info(f"🇯🇵 정확한 일본 검색을 위해 '{query}' -> '{translated_query}'(으)로 번역하여 검색합니다.")
                             query = translated_query
                         except Exception as e:
                             st.warning(f"번역 중 오류가 발생했습니다: {e}")

                
                # 1. Robust Search (Fetch until target count is met)
                # Note: 'region_code' argument requires youtube_api.py to be updated.
                # If cached, it might fail. Restarting the server is best.
                try:
                    df = search_and_filter_videos(
                        youtube=youtube,
                        query=query,
                        start_date=start_date,
                        end_date=end_date,
                        target_count=max_results,
                        min_duration_sec=min_sec,
                        max_duration_sec=max_sec,
                        region_code=region_code,
                        relevance_language=relevance_lang
                    )
                    
                    if not df.empty:
                        st.session_state["last_result"] = df
                        st.session_state["last_query"] = query
                        st.success(f"동영상 {len(df)}개를 찾았습니다!")
                    else:
                        st.warning("조건에 맞는 동영상을 찾지 못했습니다.")
                        st.info("팁: 검색 기간을 늘리거나 검색어를 변경해보세요.")

                except Exception as e:
                    error_msg = str(e)
                    if "quotaExceeded" in error_msg:
                        st.error("🚨 유튜브 API 일일 할당량을 초과했습니다. (Quota Exceeded)")
                        st.warning("내일(오후 5시 이후) 다시 시도하거나, 새로운 API 키를 발급받아 교체해주세요.")
                        st.info("ℹ️ 유튜브 데이터 API는 하루 할당량이 제한되어 있습니다. 많은 검색이나 개발 테스트 시 금방 소진될 수 있습니다.")
                    else:
                        st.error(f"오류가 발생했습니다: {e}")
                        st.write(f"상세 에러 내용: {str(e)}")

            except Exception as e:
                st.error(f"오류가 발생했습니다: {str(e)}")

    # Display Results (always show if available in session state)
    if "last_result" in st.session_state:
        df = st.session_state["last_result"]
        
        # Display Metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("총 조회수", format_kr_number(int(df['Views'].sum())))
        col2.metric("평균 조회수", format_kr_number(int(df['Views'].mean())))
        col3.metric("최고 성과도 (조회수/구독자)", df['Performance (Views/Subs)'].max())
        
        # Sort by Views (Descending) to ensure Ranking is correct
        df = df.sort_values(by="Views", ascending=False)

        # Prepare Display Dataframe
        display_df = df.copy()

        if display_df.empty:
            st.warning(f"조건에 맞는 동영상이 없습니다.")
        else:
            # Add 'Type' Column
            display_df['유형'] = display_df['DurationSec'].apply(lambda x: "📱 쇼츠" if x <= 60 else "📺 영상")

            # 1. Add Rank (순위)
            display_df.insert(0, "순위", range(1, len(display_df) + 1))
            
            # 2. Format Numbers (Views, Likes, Subscribers)
        # Note: We convert to string, so they won't be sortable numerically in the UI column sorting if user clicks header.
        # But user priority is "display format".
        display_df['Views'] = display_df['Views'].apply(format_kr_number)
        display_df['Likes'] = display_df['Likes'].apply(format_kr_number)
        display_df['Subscribers'] = display_df['Subscribers'].apply(format_kr_number)
        # Comments was not explicitly asked but good to consist, but user specified 3. Let's keep comments as is or format? User said "Likes, Views, Subs".
        
        # Dataframe with Image Column
        st.dataframe(
            display_df,
            column_config={
                "순위": st.column_config.NumberColumn("순위", format="%d"),
                "유형": st.column_config.TextColumn("유형"),
                "Thumbnail": st.column_config.ImageColumn("썸네일", width="small"),
                "Link": st.column_config.LinkColumn("링크"),
                "Views": st.column_config.TextColumn("조회수"), # Changed to TextColumn for string format
                "Title": st.column_config.TextColumn("제목"),
                "Duration": st.column_config.TextColumn("길이"),
                "Channel": st.column_config.TextColumn("채널명"),
                "Published": st.column_config.TextColumn("게시일"),
                "Likes": st.column_config.TextColumn("좋아요"), # Changed to TextColumn
                "Comments": st.column_config.NumberColumn("댓글수", format="%d"),
                "Subscribers": st.column_config.TextColumn("구독자수"), # Changed to TextColumn
                "Performance (Views/Subs)": st.column_config.TextColumn("성과도"),
                "DurationSec": None # Hide internal column
            },
            use_container_width=True,
            height=600,
            hide_index=True
        )
        

