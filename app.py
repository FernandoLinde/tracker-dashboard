import streamlit as st
import yt_dlp
import datetime
import re
import time
from itertools import groupby
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable

# --- HELPER FUNCTIONS ---

def extract_video_id(url):
    """Extract video ID from various YouTube URL formats."""
    # First try simple split method
    if 'v=' in url:
        video_id = url.split('v=')[-1].split('&')[0]
        if len(video_id) == 11:
            return video_id
    
    # Then try regex patterns
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([0-9A-Za-z_-]{11})',
        r'(?:youtube\.com\/embed\/)([0-9A-Za-z_-]{11})',
        r'(?:youtube\.com\/v\/)([0-9A-Za-z_-]{11})',
        r'^([0-9A-Za-z_-]{11})$'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def get_transcript(video_url, max_retries=2):
    """Fetches transcript with multiple retry strategies."""
    
    for attempt in range(max_retries):
        try:
            # Extract video ID
            video_id = extract_video_id(video_url)
            
            if not video_id:
                st.error(f"❌ Invalid video ID from URL")
                return None
            
            # Add small delay between retries
            if attempt > 0:
                time.sleep(1)
            
            # List all available transcripts
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Strategy 1: Try to get any manually created transcript first
            try:
                for transcript in transcript_list:
                    if not transcript.is_generated:
                        return "\n".join([item['text'] for item in transcript.fetch()])
            except:
                pass
            
            # Strategy 2: Try Portuguese (manual or auto)
            try:
                transcript = transcript_list.find_transcript(['pt', 'pt-BR'])
                return "\n".join([item['text'] for item in transcript.fetch()])
            except:
                pass
            
            # Strategy 3: Try English (manual or auto)
            try:
                transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
                return "\n".join([item['text'] for item in transcript.fetch()])
            except:
                pass
            
            # Strategy 4: Try ANY available transcript and translate if needed
            try:
                available_transcripts = list(transcript_list)
                if available_transcripts:
                    # Get the first available transcript
                    first_transcript = available_transcripts[0]
                    
                    # Try to translate to Portuguese if it's not PT or EN
                    try:
                        translated = first_transcript.translate('pt')
                        return "\n".join([item['text'] for item in translated.fetch()])
                    except:
                        # If translation fails, just return the original
                        return "\n".join([item['text'] for item in first_transcript.fetch()])
            except:
                pass
            
            # Strategy 5: Direct fetch without language preference
            try:
                transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
                return "\n".join([item['text'] for item in transcript_data])
            except:
                pass
                
        except TranscriptsDisabled:
            st.warning(f"⚠️ Transcripts disabled for this video")
            return None
        except NoTranscriptFound:
            st.warning(f"⚠️ No transcript found")
            return None
        except VideoUnavailable:
            st.error(f"❌ Video unavailable")
            return None
        except Exception as e:
            if attempt == max_retries - 1:
                st.error(f"❌ Error: {type(e).__name__}")
                print(f"Full error for {video_id}: {str(e)}")
            continue
    
    return None

def format_views(views):
    if not views: return "-"
    if views >= 1_000_000: return f"{views/1_000_000:.1f}M"
    if views >= 1_000: return f"{views/1_000:.0f}K"
    return str(views)

def format_duration(seconds):
    if not seconds: return "-"
    try:
        return str(datetime.timedelta(seconds=int(seconds)))
    except:
        return "-"

# --- PAGE CONFIG ---
st.set_page_config(page_title="Executive Tracker", page_icon="📊", layout="wide")

# --- CSS STYLING ---
st.markdown("""
<style>
    .stExpander {
        background-color: #0E1117 !important;
        border: 1px solid #303030 !important;
        color: white !important;
    }
    .streamlit-expanderHeader {
        color: white !important;
        background-color: #0E1117 !important;
    }
    .block-container {
        padding-top: 3rem; 
        padding-bottom: 5rem;
    }
    div[data-testid="column"] {
        display: flex;
        align-items: center; 
    }
    div[data-testid="stVerticalBlock"] > div {
        margin-bottom: -5px;
    }
    .stAlert {
        padding: 0.5rem;
        margin: 0.25rem 0;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# --- CONFIGURATION ---
GEM_URL = "https://gemini.google.com/gem/1HTDzIGbVXIA7dJodfgK3jahP3sayuWWl?usp=sharing" 

CATEGORIES = {
    "Tech": [
        "https://www.youtube.com/@JordiVisserLabs/videos",
        "https://www.youtube.com/@peterdiamandis/videos",
        "https://www.youtube.com/@AcquiredFM/videos",
        "https://www.youtube.com/@ycombinator/videos",
        "https://www.youtube.com/@BitBiasedAI/videos",
        "https://www.youtube.com/@IBMTechnology/videos",
        "https://www.youtube.com/@ILTB_Podcast/videos",
        "https://www.youtube.com/@Stratechery/videos",
        "https://www.youtube.com/@GiantVentures/videos",
        "https://www.youtube.com/@PioneersofAI/videos",
        "https://www.youtube.com/@AIUpload/videos",
        "https://www.youtube.com/@NoPriorsPodcast/videos",
        "https://www.youtube.com/@MarinaWyssAI/videos",
        "https://www.youtube.com/@EverydayAI_/videos",
        "https://www.youtube.com/@CanalTech/videos"
    ],
    "Macro": [
        "https://www.youtube.com/@BobEUnlimited/videos",
        "https://www.youtube.com/@macrovoices7508/videos",
        "https://www.youtube.com/@EconomistaSincero/videos",
        "https://www.youtube.com/@RichRP/videos"
    ],
    "Geral": [
        "https://www.youtube.com/@StockPickers/videos",
        "https://www.youtube.com/@mmakers/videos",
        "https://www.youtube.com/@business/videos",
        "https://www.youtube.com/@wealthhighgovernance/videos",
        "https://www.youtube.com/@MastersofScale_/videos",
        "https://www.youtube.com/@allin/videos",
        "https://www.youtube.com/@PodcastFlow/videos",
        "https://www.youtube.com/@Podpah/videos"
    ]
}

# --- DATA ENGINE ---
@st.cache_data(ttl=3600)
def get_channel_data(category_name):
    channels = CATEGORIES[category_name]
    all_videos = []
    
    ydl_opts = {
        'extract_flat': True,          
        'playlist_items': '1-7',      
        'lazy_playlist': True,
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for channel_url in channels:
            clean_url = channel_url.rstrip('/')
            if not clean_url.endswith('/videos'):
                clean_url += '/videos'
            
            try:
                info = ydl.extract_info(clean_url, download=False)
                entries = info.get('entries', [])
                channel_title = info.get('channel', clean_url.split('@')[-1])

                for v in entries:
                    if v:
                        vid_id = v.get('id')
                        all_videos.append({
                            'channel': channel_title,
                            'channel_url': channel_url,
                            'title': v.get('title'),
                            'url': f"https://www.youtube.com/watch?v={vid_id}",
                            'views': v.get('view_count'),
                            'duration': v.get('duration'),
                            'id': vid_id
                        })
            except:
                continue
    return all_videos

# --- SIDEBAR ---
with st.sidebar:
    st.title("📊 Menu")
    selected_category = st.radio("Select Category:", list(CATEGORIES.keys()))
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    st.caption("💡 Tip: If transcript fails, the video may not have captions enabled by the creator.")

# --- MAIN CONTENT ---
st.title(f"📺 {selected_category}")

with st.spinner(f"Updating Intelligence..."):
    videos = get_channel_data(selected_category)

if not videos:
    st.error("No videos found. Check connection.")
else:
    videos.sort(key=lambda x: x['channel'])

    for channel_name, channel_videos_iter in groupby(videos, key=lambda x: x['channel']):
        channel_videos = list(channel_videos_iter)
        c_url = channel_videos[0]['channel_url'] if channel_videos else "#"

        with st.expander(f"**{channel_name}**", expanded=False):
            st.markdown(f"🔗 [**Open Channel**]({c_url})")
            
            # Layout Columns
            h1, h3, h4, h5, h6 = st.columns([5, 1, 1, 1, 1])
            h1.markdown("<small style='color:grey'>VIDEO TITLE</small>", unsafe_allow_html=True)
            h3.markdown("<small style='color:grey'>VIEWS</small>", unsafe_allow_html=True)
            h4.markdown("<small style='color:grey'>LENGTH</small>", unsafe_allow_html=True)
            h5.markdown("<small style='color:grey'>EXTRA</small>", unsafe_allow_html=True)
            h6.markdown("<small style='color:grey'>TRANS</small>", unsafe_allow_html=True)
            
            st.divider()

            for i, v in enumerate(channel_videos):
                c1, c3, c4, c5, c6 = st.columns([5, 1, 1, 1, 1])
                
                # Column 1: Title
                c1.markdown(f"[{v['title']}]({v['url']})", unsafe_allow_html=True)
                
                # Column 2 & 3: Metrics
                c3.write(format_views(v['views']))
                c4.write(format_duration(v['duration']))
                
                # Column 4: Popover
                with c5:
                    with st.popover("✨"):
                        st.caption("Copy Link:")
                        st.code(v['url'], language="text")
                        st.caption("Video ID:")
                        st.code(v['id'], language="text")
                        st.caption("Summarize:")
                        st.link_button("Go to Gemini 💎", GEM_URL)
                
                # Column 5: Transcript (On-Demand)
                with c6:
                    if st.button("📄", key=f"btn_{v['id']}_{i}", help="Fetch Transcript"):
                        with st.spinner("Fetching..."):
                            content = get_transcript(v['url'])
                        
                        if content:
                            st.success("✓")
                            st.download_button(
                                label="💾 Download",
                                data=f"# {v['title']}\n\n{content}",
                                file_name=f"transcript_{v['id']}.md",
                                mime="text/markdown",
                                key=f"dl_{v['id']}_{i}"
                            )

                if i < len(channel_videos) - 1:
                     st.markdown("<hr style='margin: 5px 0; opacity: 0.1;'>", unsafe_allow_html=True)
