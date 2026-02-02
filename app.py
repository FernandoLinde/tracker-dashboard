import streamlit as st
import yt_dlp
import datetime
from itertools import groupby
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable

# --- HELPER FUNCTIONS ---

def get_transcript(video_url):
    """Fetches transcript using the official youtube-transcript-api."""
    try:
        # Extract video ID from URL
        if 'v=' in video_url:
            video_id = video_url.split('v=')[-1].split('&')[0]
        elif 'youtu.be/' in video_url:
            video_id = video_url.split('youtu.be/')[-1].split('?')[0]
        else:
            video_id = video_url
        
        # Use the correct API method - get_transcript is a CLASS METHOD
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['pt', 'pt-BR', 'en', 'en-US'])
        
        # Convert to text format
        full_text = "\n".join([entry['text'] for entry in transcript])
        return full_text
        
    except TranscriptsDisabled:
        print(f"Transcripts are disabled for video: {video_id}")
        return None
    except NoTranscriptFound:
        print(f"No transcript found for video: {video_id}")
        return None
    except VideoUnavailable:
        print(f"Video is unavailable: {video_id}")
        return None
    except Exception as e:
        print(f"Error fetching transcript: {type(e).__name__} - {str(e)}")
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

def format_upload_date(upload_date_str):
    """Format upload date as 'X days ago' from YYYYMMDD string"""
    if not upload_date_str or upload_date_str == "NA":
        return "-"
    try:
        # Parse the YYYYMMDD format
        upload_date = datetime.datetime.strptime(str(upload_date_str), '%Y%m%d')
        now = datetime.datetime.now()
        delta = now - upload_date
        days = delta.days
        
        if days == 0:
            return "Today"
        elif days == 1:
            return "1 day ago"
        elif days < 7:
            return f"{days} days ago"
        elif days < 30:
            weeks = days // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        elif days < 365:
            months = days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        else:
            years = days // 365
            return f"{years} year{'s' if years > 1 else ''} ago"
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
        'extract_flat': 'in_playlist',
        'playlist_items': '1-7',      
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'extractor_args': {
            'youtubetab': {
                'approximate_date': True  # This enables approximate upload dates in flat mode
            }
        }
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
                            'upload_date': v.get('upload_date'),
                            'id': vid_id
                        })
            except Exception as e:
                print(f"Error fetching {channel_url}: {e}")
                continue
                
    return all_videos

# Initialize session state for transcripts
if 'transcripts' not in st.session_state:
    st.session_state.transcripts = {}

# --- SIDEBAR ---
with st.sidebar:
    st.title("📊 Menu")
    selected_category = st.radio("Select Category:", list(CATEGORIES.keys()))
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.session_state.transcripts = {}
        st.rerun()
    
    st.divider()
    st.caption("💡 Using official YouTube Transcript API")

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
            h1, h2, h3, h4, h5, h6 = st.columns([4, 1, 1, 1, 1, 1])
            h1.markdown("<small style='color:grey'>VIDEO TITLE</small>", unsafe_allow_html=True)
            h2.markdown("<small style='color:grey'>UPLOADED</small>", unsafe_allow_html=True)
            h3.markdown("<small style='color:grey'>VIEWS</small>", unsafe_allow_html=True)
            h4.markdown("<small style='color:grey'>LENGTH</small>", unsafe_allow_html=True)
            h5.markdown("<small style='color:grey'>EXTRA</small>", unsafe_allow_html=True)
            h6.markdown("<small style='color:grey'>TRANS</small>", unsafe_allow_html=True)
            
            st.divider()

            for i, v in enumerate(channel_videos):
                c1, c2, c3, c4, c5, c6 = st.columns([4, 1, 1, 1, 1, 1])
                
                # Column 1: Title
                c1.markdown(f"[{v['title']}]({v['url']})", unsafe_allow_html=True)
                
                # Column 2: Upload Date
                c2.write(format_upload_date(v['upload_date']))
                
                # Column 3 & 4: Metrics
                c3.write(format_views(v['views']))
                c4.write(format_duration(v['duration']))
                
                # Column 5: Popover
                with c5:
                    with st.popover("✨"):
                        st.caption("Copy Link:")
                        st.code(v['url'], language="text")
                        st.caption("Summarize:")
                        st.link_button("Go to Gemini 💎", GEM_URL)
                
                # Column 6: Transcript (On-Demand)
                with c6:
                    # Create unique key for this video
                    transcript_key = f"transcript_{v['id']}"
                    
                    # Fetch button
                    if st.button("📄", key=f"btn_{v['id']}_{i}", help="Fetch Transcript"):
                        with st.spinner("Fetching..."):
                            content = get_transcript(v['url'])
                            if content and len(content.strip()) > 0:
                                st.session_state.transcripts[transcript_key] = content
                            else:
                                st.session_state.transcripts[transcript_key] = "ERROR"
                    
                    # Show download button if transcript is available
                    if transcript_key in st.session_state.transcripts:
                        if st.session_state.transcripts[transcript_key] == "ERROR":
                            st.error("N/A")
                        else:
                            st.download_button(
                                label="💾",
                                data=f"# {v['title']}\n\n{st.session_state.transcripts[transcript_key]}",
                                file_name=f"transcript_{v['id']}.md",
                                mime="text/markdown",
                                key=f"dl_{v['id']}_{i}"
                            )

                if i < len(channel_videos) - 1:
                     st.markdown("<hr style='margin: 5px 0; opacity: 0.1;'>", unsafe_allow_html=True)import streamlit as st
import yt_dlp
import datetime
from itertools import groupby
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable

# --- HELPER FUNCTIONS ---

def get_transcript(video_url):
    """Fetches transcript using the official youtube-transcript-api."""
    try:
        # Extract video ID from URL
        if 'v=' in video_url:
            video_id = video_url.split('v=')[-1].split('&')[0]
        elif 'youtu.be/' in video_url:
            video_id = video_url.split('youtu.be/')[-1].split('?')[0]
        else:
            video_id = video_url
        
        # Use the correct API method - get_transcript is a CLASS METHOD
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['pt', 'pt-BR', 'en', 'en-US'])
        
        # Convert to text format
        full_text = "\n".join([entry['text'] for entry in transcript])
        return full_text
        
    except TranscriptsDisabled:
        print(f"Transcripts are disabled for video: {video_id}")
        return None
    except NoTranscriptFound:
        print(f"No transcript found for video: {video_id}")
        return None
    except VideoUnavailable:
        print(f"Video is unavailable: {video_id}")
        return None
    except Exception as e:
        print(f"Error fetching transcript: {type(e).__name__} - {str(e)}")
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

def format_upload_date(upload_date_str):
    """Format upload date as 'X days ago' from YYYYMMDD string"""
    if not upload_date_str or upload_date_str == "NA":
        return "-"
    try:
        # Parse the YYYYMMDD format
        upload_date = datetime.datetime.strptime(str(upload_date_str), '%Y%m%d')
        now = datetime.datetime.now()
        delta = now - upload_date
        days = delta.days
        
        if days == 0:
            return "Today"
        elif days == 1:
            return "1 day ago"
        elif days < 7:
            return f"{days} days ago"
        elif days < 30:
            weeks = days // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        elif days < 365:
            months = days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        else:
            years = days // 365
            return f"{years} year{'s' if years > 1 else ''} ago"
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
        'extract_flat': 'in_playlist',
        'playlist_items': '1-7',      
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'extractor_args': {
            'youtubetab': {
                'approximate_date': True  # This enables approximate upload dates in flat mode
            }
        }
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
                            'upload_date': v.get('upload_date'),
                            'id': vid_id
                        })
            except Exception as e:
                print(f"Error fetching {channel_url}: {e}")
                continue
                
    return all_videos

# Initialize session state for transcripts
if 'transcripts' not in st.session_state:
    st.session_state.transcripts = {}

# --- SIDEBAR ---
with st.sidebar:
    st.title("📊 Menu")
    selected_category = st.radio("Select Category:", list(CATEGORIES.keys()))
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.session_state.transcripts = {}
        st.rerun()
    
    st.divider()
    st.caption("💡 Using official YouTube Transcript API")

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
            h1, h2, h3, h4, h5, h6 = st.columns([4, 1, 1, 1, 1, 1])
            h1.markdown("<small style='color:grey'>VIDEO TITLE</small>", unsafe_allow_html=True)
            h2.markdown("<small style='color:grey'>UPLOADED</small>", unsafe_allow_html=True)
            h3.markdown("<small style='color:grey'>VIEWS</small>", unsafe_allow_html=True)
            h4.markdown("<small style='color:grey'>LENGTH</small>", unsafe_allow_html=True)
            h5.markdown("<small style='color:grey'>EXTRA</small>", unsafe_allow_html=True)
            h6.markdown("<small style='color:grey'>TRANS</small>", unsafe_allow_html=True)
            
            st.divider()

            for i, v in enumerate(channel_videos):
                c1, c2, c3, c4, c5, c6 = st.columns([4, 1, 1, 1, 1, 1])
                
                # Column 1: Title
                c1.markdown(f"[{v['title']}]({v['url']})", unsafe_allow_html=True)
                
                # Column 2: Upload Date
                c2.write(format_upload_date(v['upload_date']))
                
                # Column 3 & 4: Metrics
                c3.write(format_views(v['views']))
                c4.write(format_duration(v['duration']))
                
                # Column 5: Popover
                with c5:
                    with st.popover("✨"):
                        st.caption("Copy Link:")
                        st.code(v['url'], language="text")
                        st.caption("Summarize:")
                        st.link_button("Go to Gemini 💎", GEM_URL)
                
                # Column 6: Transcript (On-Demand)
                with c6:
                    # Create unique key for this video
                    transcript_key = f"transcript_{v['id']}"
                    
                    # Fetch button
                    if st.button("📄", key=f"btn_{v['id']}_{i}", help="Fetch Transcript"):
                        with st.spinner("Fetching..."):
                            content = get_transcript(v['url'])
                            if content and len(content.strip()) > 0:
                                st.session_state.transcripts[transcript_key] = content
                            else:
                                st.session_state.transcripts[transcript_key] = "ERROR"
                    
                    # Show download button if transcript is available
                    if transcript_key in st.session_state.transcripts:
                        if st.session_state.transcripts[transcript_key] == "ERROR":
                            st.error("N/A")
                        else:
                            st.download_button(
                                label="💾",
                                data=f"# {v['title']}\n\n{st.session_state.transcripts[transcript_key]}",
                                file_name=f"transcript_{v['id']}.md",
                                mime="text/markdown",
                                key=f"dl_{v['id']}_{i}"
                            )

                if i < len(channel_videos) - 1:
                     st.markdown("<hr style='margin: 5px 0; opacity: 0.1;'>", unsafe_allow_html=True)
