import streamlit as st
import yt_dlp
import datetime
from itertools import groupby

# --- HELPER FUNCTIONS ---

def get_transcript_with_ytdlp(video_url):
    """Use yt-dlp to fetch subtitles - more reliable alternative."""
    try:
        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['pt', 'pt-BR', 'en', 'en-US'],
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            # Try to get subtitles in order of preference
            subtitles = info.get('subtitles', {})
            automatic_captions = info.get('automatic_captions', {})
            
            # Priority order: pt manual > en manual > pt auto > en auto
            for lang in ['pt', 'pt-BR', 'en', 'en-US', 'en-GB']:
                if lang in subtitles:
                    return extract_text_from_subtitle_data(subtitles[lang])
            
            for lang in ['pt', 'pt-BR', 'en', 'en-US', 'en-GB']:
                if lang in automatic_captions:
                    return extract_text_from_subtitle_data(automatic_captions[lang])
            
            # If no preferred language, get first available
            if subtitles:
                first_lang = list(subtitles.keys())[0]
                return extract_text_from_subtitle_data(subtitles[first_lang])
            
            if automatic_captions:
                first_lang = list(automatic_captions.keys())[0]
                return extract_text_from_subtitle_data(automatic_captions[first_lang])
            
            return None
            
    except Exception as e:
        print(f"yt-dlp error: {str(e)}")
        return None

def extract_text_from_subtitle_data(subtitle_list):
    """Extract text from subtitle format data."""
    import requests
    
    # subtitle_list contains different formats (vtt, srv3, etc)
    # Try to find a text-based format
    for sub_format in subtitle_list:
        if 'url' in sub_format:
            try:
                response = requests.get(sub_format['url'], timeout=10)
                content = response.text
                
                # Parse VTT or SRT format
                lines = content.split('\n')
                text_lines = []
                
                for line in lines:
                    line = line.strip()
                    # Skip timestamp lines and metadata
                    if '-->' in line or line.isdigit() or line.startswith('WEBVTT') or line.startswith('Kind:') or not line:
                        continue
                    # Skip lines with only tags
                    if line.startswith('<') and line.endswith('>'):
                        continue
                    text_lines.append(line)
                
                return '\n'.join(text_lines)
            except:
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
    st.caption("📝 Using yt-dlp for transcript extraction")

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
                        st.caption("Summarize:")
                        st.link_button("Go to Gemini 💎", GEM_URL)
                
                # Column 5: Transcript (On-Demand)
                with c6:
                    if st.button("📄", key=f"btn_{v['id']}_{i}", help="Fetch Transcript"):
                        with st.spinner("Fetching..."):
                            content = get_transcript_with_ytdlp(v['url'])
                        
                        if content and len(content.strip()) > 0:
                            st.success("✓")
                            st.download_button(
                                label="💾",
                                data=f"# {v['title']}\n\n{content}",
                                file_name=f"transcript_{v['id']}.md",
                                mime="text/markdown",
                                key=f"dl_{v['id']}_{i}"
                            )
                        else:
                            st.error("No captions available")

                if i < len(channel_videos) - 1:
                     st.markdown("<hr style='margin: 5px 0; opacity: 0.1;'>", unsafe_allow_html=True)
