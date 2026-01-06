import streamlit as st
import yt_dlp
import datetime
from itertools import groupby

# --- PAGE CONFIG ---
st.set_page_config(page_title="Executive Tracker", page_icon="📊", layout="wide")

# --- CSS STYLING (Visual Fixes) ---
st.markdown("""
<style>
    /* 1. Fix Title Cutoff: Push the main content down */
    .block-container {
        padding-top: 3rem; 
        padding-bottom: 5rem;
    }
    
    /* 2. Styling the Expanders (Channels) */
    .stExpander {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        background-color: #ffffff;
        margin-bottom: 15px; /* Space between channels */
    }
    
    /* 3. Text Alignment */
    div[data-testid="column"] {
        display: flex;
        align-items: center; /* Vertically center all text */
    }
    
    /* 4. Remove default Streamlit whitespace between elements */
    div[data-testid="stVerticalBlock"] > div {
        margin-bottom: -5px;
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
    
    # ACCURATE MODE (Fixes the missing dates)
    ydl_opts = {
        'playlist_items': '1-7',      
        'lazy_playlist': True,
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'skip_download': True,        # Don't download video file
        'ignore_no_formats': True,    # Speed up metadata check
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
                            'date': v.get('upload_date'), # This will now work!
                            'timestamp': v.get('timestamp')
                        })
            except:
                continue
    
    return all_videos

# --- FORMATTING ---
def format_relative_time(date_str):
    if not date_str: return "Unknown"
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
        return "Unknown"

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
    selected_category = st.radio("Select Category:", list(CATEGORIES.keys()))
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# --- MAIN CONTENT ---
st.title(f"📺 {selected_category}")

with st.spinner(f"Updating Intelligence for {selected_category}..."):
    videos = get_channel_data(selected_category)

if not videos:
    st.error("No videos found. Please check internet connection.")
else:
    videos.sort(key=lambda x: x['channel'])

    for channel_name, channel_videos_iter in groupby(videos, key=lambda x: x['channel']):
        channel_videos = list(channel_videos_iter)
        c_url = channel_videos[0]['channel_url'] if channel_videos else "#"

        with st.expander(f"**{channel_name}**", expanded=False):
            
            # Link to Channel
            st.markdown(f"🔗 [**Open {channel_name} Channel**]({c_url})")
            
            # Column Headers
            h1, h2, h3, h4, h5 = st.columns([5, 1.5, 0.8, 1, 0.5])
            h1.markdown("<small style='color:grey'>VIDEO TITLE</small>", unsafe_allow_html=True)
            h2.markdown("<small style='color:grey'>UPLOADED</small>", unsafe_allow_html=True)
            h3.markdown("<small style='color:grey'>VIEWS</small>", unsafe_allow_html=True)
            h4.markdown("<small style='color:grey'>LENGTH</small>", unsafe_allow_html=True)
            h5.markdown("<small style='color:grey'>AI</small>", unsafe_allow_html=True)
            
            st.divider()

            # Video Rows
            for i, v in enumerate(channel_videos):
                c1, c2, c3, c4, c5 = st.columns([5, 1.5, 0.8, 1, 0.5])
                
                # Title
                c1.markdown(f"[{v['title']}]({v['url']})", unsafe_allow_html=True)
                
                # Metadata
                c2.write(format_relative_time(v['date']))
                c3.write(format_views(v['views']))
                c4.write(format_duration(v['duration']))
                
                # Button
                with c5:
                    with st.popover("✨"):
                        st.code(f"Resuma este vídeo em português: {v['url']}", language="text")
                        st.link_button("Gemini", GEM_URL)
                
                # SPACER: Use a Divider if it's not the last video, otherwise just space
                if i < len(channel_videos) - 1:
                     st.markdown("<hr style='margin: 5px 0; opacity: 0.3;'>", unsafe_allow_html=True)
                else:
                     st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

