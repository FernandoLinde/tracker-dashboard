import datetime
import re
from itertools import groupby

import streamlit as st
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled, VideoUnavailable

# --- HELPER FUNCTIONS ---

def extract_video_id(video_url):
    if 'v=' in video_url:
        return video_url.split('v=')[-1].split('&')[0]
    if 'youtu.be/' in video_url:
        return video_url.split('youtu.be/')[-1].split('?')[0]
    return video_url


def _get_api_instance():
    try:
        return YouTubeTranscriptApi()
    except Exception:
        return None


def _fetch_transcript_list(video_id):
    """Support multiple youtube-transcript-api versions."""
    api = _get_api_instance()

    if api and hasattr(api, 'list'):
        return api.list(video_id)

    if hasattr(YouTubeTranscriptApi, 'list_transcripts'):
        return YouTubeTranscriptApi.list_transcripts(video_id)

    return None


def _direct_fetch_transcript(video_id, languages):
    """Direct transcript fetch that supports both API styles."""
    api = _get_api_instance()

    if api and hasattr(api, 'fetch'):
        return api.fetch(video_id, languages=languages)

    # Older versions
    if hasattr(YouTubeTranscriptApi, 'get_transcript'):
        return YouTubeTranscriptApi.get_transcript(video_id, languages=languages)

    return None


def _normalize_transcript_text(fetched_transcript):
    if not fetched_transcript:
        return None

    parts = []
    for snippet in fetched_transcript:
        if hasattr(snippet, 'text'):
            text = snippet.text
        elif isinstance(snippet, dict):
            text = snippet.get('text')
        else:
            text = None

        if text:
            parts.append(text)

    combined = "\n".join(parts).strip()
    return combined if combined else None


def get_transcript(video_url):
    """Fetch transcript text from manual, generated, or translated tracks."""
    video_id = extract_video_id(video_url)
    preferred_languages = ['pt', 'pt-BR', 'en', 'en-US', 'es', 'fr', 'de']

    try:
        fetched_transcript = None

        try:
            fetched_transcript = _direct_fetch_transcript(video_id, preferred_languages)
        except NoTranscriptFound:
            fetched_transcript = None

        if fetched_transcript is None:
            transcript_list = _fetch_transcript_list(video_id)
            if transcript_list is None:
                return None

            for lang in preferred_languages:
                try:
                    fetched_transcript = transcript_list.find_manually_created_transcript([lang]).fetch()
                    break
                except NoTranscriptFound:
                    continue

            if fetched_transcript is None:
                for lang in preferred_languages:
                    try:
                        fetched_transcript = transcript_list.find_generated_transcript([lang]).fetch()
                        break
                    except NoTranscriptFound:
                        continue

            if fetched_transcript is None:
                for transcript in transcript_list:
                    if getattr(transcript, 'is_translatable', False):
                        try:
                            fetched_transcript = transcript.translate('en').fetch()
                            break
                        except Exception:
                            continue

        return _normalize_transcript_text(fetched_transcript)

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


def summarize_transcript(transcript_text, max_points=4):
    """Create a compact 3-4 bullet summary from transcript text."""
    if not transcript_text:
        return []

    cleaned = re.sub(r'\s+', ' ', transcript_text).strip()
    if not cleaned:
        return []

    sentences = re.split(r'(?<=[.!?])\s+', cleaned)
    bullets = []
    seen = set()

    for sentence in sentences:
        s = sentence.strip(' -•\n\t')
        if len(s) < 35:
            continue

        normalized = s.lower()
        if normalized in seen:
            continue

        if len(s) > 180:
            s = s[:177].rstrip() + '...'

        bullets.append(f"- {s}")
        seen.add(normalized)

        if len(bullets) >= max_points:
            return bullets

    # Fallback when punctuation is sparse: chunk by words
    if not bullets:
        words = cleaned.split()
        chunk_size = max(20, min(40, len(words) // max_points if len(words) > max_points else 20))
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size]).strip()
            if len(chunk) < 35:
                continue
            if len(chunk) > 180:
                chunk = chunk[:177].rstrip() + '...'
            bullets.append(f"- {chunk}")
            if len(bullets) >= max_points:
                break

    return bullets


def format_views(views):
    if not views:
        return "-"
    if views >= 1_000_000:
        return f"{views / 1_000_000:.1f}M"
    if views >= 1_000:
        return f"{views / 1_000:.0f}K"
    return str(views)


def format_duration(seconds):
    if not seconds:
        return "-"
    try:
        return str(datetime.timedelta(seconds=int(seconds)))
    except Exception:
        return "-"


def parse_upload_datetime(upload_date, timestamp):
    if upload_date:
        try:
            return datetime.datetime.strptime(upload_date, "%Y%m%d")
        except Exception:
            pass

    if timestamp:
        try:
            return datetime.datetime.fromtimestamp(int(timestamp))
        except Exception:
            pass

    return None


def format_upload_age(upload_date, timestamp):
    upload_dt = parse_upload_datetime(upload_date, timestamp)
    if upload_dt is None:
        return "-"

    delta_days = max((datetime.datetime.now() - upload_dt).days, 0)
    if delta_days == 0:
        return "Today"
    if delta_days == 1:
        return "1 day ago"
    return f"{delta_days} days ago"


def enrich_video_metadata(ydl, video_id, fallback_upload_date=None, fallback_timestamp=None):
    """Fetch upload metadata when listing extraction omits it."""
    if fallback_upload_date or fallback_timestamp:
        return fallback_upload_date, fallback_timestamp

    try:
        details = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
        return details.get('upload_date'), details.get('timestamp')
    except Exception:
        return None, None


# --- PAGE CONFIG ---
st.set_page_config(page_title="Executive Tracker", page_icon="📊", layout="wide")

# --- CSS STYLING ---
st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)

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
        "https://www.youtube.com/@CanalTech/videos",
    ],
    "Macro": [
        "https://www.youtube.com/@BobEUnlimited/videos",
        "https://www.youtube.com/@macrovoices7508/videos",
        "https://www.youtube.com/@EconomistaSincero/videos",
        "https://www.youtube.com/@RichRP/videos",
    ],
    "Geral": [
        "https://www.youtube.com/@StockPickers/videos",
        "https://www.youtube.com/@mmakers/videos",
        "https://www.youtube.com/@business/videos",
        "https://www.youtube.com/@wealthhighgovernance/videos",
        "https://www.youtube.com/@MastersofScale_/videos",
        "https://www.youtube.com/@allin/videos",
        "https://www.youtube.com/@PodcastFlow/videos",
        "https://www.youtube.com/@Podpah/videos",
    ],
}


# --- DATA ENGINE ---
@st.cache_data(ttl=3600)
def get_channel_data(category_name):
    channels = CATEGORIES[category_name]
    all_videos = []

    # Not using flat mode to improve upload date / timestamp availability.
    ydl_opts = {
        'extract_flat': False,
        'playlist_items': '1-7',
        'lazy_playlist': True,
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'skip_download': True,
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
                    if not v:
                        continue

                    vid_id = v.get('id')
                    if not vid_id:
                        continue

                    upload_date, timestamp = enrich_video_metadata(
                        ydl,
                        vid_id,
                        fallback_upload_date=v.get('upload_date'),
                        fallback_timestamp=v.get('timestamp'),
                    )

                    all_videos.append(
                        {
                            'channel': channel_title,
                            'channel_url': channel_url,
                            'title': v.get('title'),
                            'url': f"https://www.youtube.com/watch?v={vid_id}",
                            'views': v.get('view_count'),
                            'duration': v.get('duration'),
                            'upload_date': upload_date,
                            'timestamp': timestamp,
                            'id': vid_id,
                        }
                    )
            except Exception:
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
    st.caption("💡 Using official YouTube Transcript API")


# --- MAIN CONTENT ---
st.title(f"📺 {selected_category}")

with st.spinner("Updating Intelligence..."):
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

            h0, h1, h2, h3, h4, h5, h6 = st.columns([1, 4, 1, 1, 1, 1, 1])
            h0.markdown("<small style='color:grey'>SUMM</small>", unsafe_allow_html=True)
            h1.markdown("<small style='color:grey'>VIDEO TITLE</small>", unsafe_allow_html=True)
            h2.markdown("<small style='color:grey'>AGE</small>", unsafe_allow_html=True)
            h3.markdown("<small style='color:grey'>VIEWS</small>", unsafe_allow_html=True)
            h4.markdown("<small style='color:grey'>LENGTH</small>", unsafe_allow_html=True)
            h5.markdown("<small style='color:grey'>EXTRA</small>", unsafe_allow_html=True)
            h6.markdown("<small style='color:grey'>TRANS</small>", unsafe_allow_html=True)

            st.divider()

            for i, v in enumerate(channel_videos):
                c0, c1, c2, c3, c4, c5, c6 = st.columns([1, 4, 1, 1, 1, 1, 1])

                transcript_key = f"transcript_{v['id']}"
                summary_key = f"summary_{v['id']}"

                with c0:
                    with st.popover("🧠"):
                        st.caption("Quick Summary")
                        if st.button("Generate bullets", key=f"sum_{v['id']}_{i}"):
                            with st.spinner("Building summary..."):
                                transcript = get_transcript(v['url'])
                                st.session_state[transcript_key] = transcript
                                st.session_state[summary_key] = summarize_transcript(transcript)

                        summary_lines = st.session_state.get(summary_key)
                        if summary_lines:
                            st.markdown("\n".join(summary_lines))
                        elif summary_key in st.session_state:
                            st.caption("No summary available.")

                c1.markdown(f"[{v['title']}]({v['url']})", unsafe_allow_html=True)
                c2.write(format_upload_age(v.get('upload_date'), v.get('timestamp')))
                c3.write(format_views(v['views']))
                c4.write(format_duration(v['duration']))

                with c5:
                    with st.popover("✨"):
                        st.caption("Copy Link:")
                        st.code(v['url'], language="text")
                        st.caption("Summarize:")
                        st.link_button("Go to Gemini 💎", GEM_URL)

                with c6:
                    if st.button("📄", key=f"btn_{v['id']}_{i}", help="Fetch Transcript"):
                        with st.spinner("Fetching..."):
                            st.session_state[transcript_key] = get_transcript(v['url'])

                    transcript_content = st.session_state.get(transcript_key)
                    if transcript_content and len(transcript_content.strip()) > 0:
                        st.download_button(
                            label="💾",
                            data=f"# {v['title']}\n\n{transcript_content}",
                            file_name=f"transcript_{v['id']}.md",
                            mime="text/markdown",
                            key=f"dl_{v['id']}_{i}",
                        )
                    elif transcript_key in st.session_state:
                        st.error("N/A")

                if i < len(channel_videos) - 1:
                    st.markdown("<hr style='margin: 5px 0; opacity: 0.1;'>", unsafe_allow_html=True)
