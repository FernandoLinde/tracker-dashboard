import streamlit as st
import yt_dlp
import datetime
from itertools import groupby

# --- PAGE CONFIG (Must be first) ---
st.set_page_config(page_title="Executive Tracker", page_icon="📊", layout="wide")

# --- CONFIGURATION ---
GEM_URL = "https://gemini.google.com/app" 

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

# --- CSS STYLING ---
st.markdown("""
<style>
    div[data-testid="stVerticalBlock"] > div { margin-bottom: -15px; }
    hr { margin-top: 5px; margin-bottom: 5px; }
    div[data-testid="column"] { display: flex; align-items: center; }
    .stExpander { border: 1px solid #ddd; border-radius: 5px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- DATA FUNCTIONS ---
@st.cache_data(ttl=3600)
def get_channel_data(category_name):
    channels = CATEGORIES[category_name]
    all_videos = []
    
    # FAST SCAN SETTINGS
    ydl_opts = {
        'extract_flat': True,         
        'playlist_items': '1-7',      # <--- UPDATED TO 7 VIDEOS
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
                # Use Channel Name if found, otherwise use URL name
                channel_title = info.get('channel', clean_url.split('@')[-1])

                for v in entries:
                    if v:
                        vid_id = v.get('id')
                        all_videos.append({
                            'channel': channel_title,
                            'title': v.get('title'),
                            'url': f"https://www.youtube.com/watch?v={vid_id}",
                            'views': v.get('view_count'),
                            'duration': v.get('duration'),
                            'date': v.get('upload_date'),
                            'timestamp': v.get('timestamp')
                        })
            except:
                continue
    
    return all_videos

def format_relative_time(date_str):
    if not date_str: return "-"
    try:
        date_obj = datetime.datetime.strptime(date_str, '%Y%m%d').date()
        today = datetime.date.today()
        delta = (today - date_obj).days
        
        if delta == 0: return "Today"
        if delta == 1: return "Yesterday"
        if delta < 30: return f"{delta} days ago"
        if delta < 365: return f"{delta // 30} months ago"
        return f"{delta // 365} years ago"
    except:
        return "-"

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

# --- SIDEBAR ---
with st.sidebar:
    st.title("📊 Menu")
    selected_category = st.radio("Category:", list(CATEGORIES.keys()))
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

# --- MAIN CONTENT ---
st.title(f"📺 {selected_category}")

with st.spinner(f"Fetching last 7 videos for all channels..."):
    videos = get_channel_data(selected_category)

if not videos:
    st.error("No videos found.")
else:
    # 1. Sort by Channel Name so we can group them
    videos.sort(key=lambda x: x['channel'])

    # 2. Group videos by Channel
    for channel_name, channel_videos in groupby(videos, key=lambda x: x['channel']):
        
        # Create a Dropdown (Expander) for each Channel
        with st.expander(f"**{channel_name}**", expanded=False):
            
            # Header for the table inside the expander
            h1, h2, h3, h4, h5 = st.columns([5, 1.5, 0.8, 1, 0.5])
            h1.caption("Video Title")
            h2.caption("Uploaded")
            h3.caption("Views")
            h4.caption("Length")
            h5.caption("AI")
            
            # List the 7 videos
            for v in channel_videos:
                c1, c2, c3, c4, c5 = st.columns([5, 1.5, 0.8, 1, 0.5])
                
                c1.markdown(f"[{v['title']}]({v['url']})", unsafe_allow_html=True)
                c2.write(format_relative_time(v['date']))
                c3.write(format_views(v['views']))
                c4.write(format_duration(v['duration']))
                
                with c5:
                    with st.popover("✨"):
                        st.code(f"Resuma este vídeo em português: {v['url']}", language="text")
                        st.link_button("Gemini", GEM_URL)
                
                st.divider()
