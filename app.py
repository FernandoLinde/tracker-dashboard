import datetime
import re
from itertools import groupby

import streamlit as st
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled, VideoUnavailable


# --- HELPERS ---

def extract_video_id(video_url: str) -> str:
    if 'v=' in video_url:
        return video_url.split('v=')[-1].split('&')[0]
    if 'youtu.be/' in video_url:
        return video_url.split('youtu.be/')[-1].split('?')[0]
    return video_url


def get_ytt_api_instance():
    try:
        return YouTubeTranscriptApi()
    except Exception:
        return None


def fetch_transcript_list(video_id: str):
    api = get_ytt_api_instance()

    if api and hasattr(api, 'list'):
        return api.list(video_id)

    if hasattr(YouTubeTranscriptApi, 'list_transcripts'):
        return YouTubeTranscriptApi.list_transcripts(video_id)

    return None


def direct_fetch_transcript(video_id: str, languages):
    api = get_ytt_api_instance()

    if api and hasattr(api, 'fetch'):
        return api.fetch(video_id, languages=languages)

    if hasattr(YouTubeTranscriptApi, 'get_transcript'):
        return YouTubeTranscriptApi.get_transcript(video_id, languages=languages)

    return None


def transcript_to_text(transcript_payload):
    if not transcript_payload:
        return None

    parts = []
    for item in transcript_payload:
        if hasattr(item, 'text'):
            value = item.text
        elif isinstance(item, dict):
            value = item.get('text')
        else:
            value = None

        if value:
            parts.append(str(value).strip())

    merged = "\n".join([p for p in parts if p]).strip()
    return merged if merged else None


def get_transcript(video_url: str):
    video_id = extract_video_id(video_url)
    preferred_languages = ['pt', 'pt-BR', 'en', 'en-US', 'es', 'fr', 'de']

    try:
        fetched = None

        try:
            fetched = direct_fetch_transcript(video_id, preferred_languages)
        except NoTranscriptFound:
            fetched = None

        if fetched is None:
            transcript_list = fetch_transcript_list(video_id)
            if transcript_list is None:
                return None

            for lang in preferred_languages:
                try:
                    fetched = transcript_list.find_manually_created_transcript([lang]).fetch()
                    break
                except NoTranscriptFound:
                    continue

            if fetched is None:
                for lang in preferred_languages:
                    try:
                        fetched = transcript_list.find_generated_transcript([lang]).fetch()
                        break
                    except NoTranscriptFound:
                        continue

            if fetched is None:
                for transcript in transcript_list:
                    if getattr(transcript, 'is_translatable', False):
                        try:
                            fetched = transcript.translate('en').fetch()
                            break
                        except Exception:
                            continue

        return transcript_to_text(fetched)

    except TranscriptsDisabled:
        return None
    except NoTranscriptFound:
        return None
    except VideoUnavailable:
        return None
    except Exception:
        return None


def summarize_transcript(transcript_text: str, max_points=4):
    if not transcript_text:
        return []

    cleaned = re.sub(r'\s+', ' ', transcript_text).strip()
    if not cleaned:
        return []

    bullets = []
    seen = set()

    for sentence in re.split(r'(?<=[.!?])\s+', cleaned):
        s = sentence.strip(' -•\n\t')
        if len(s) < 40:
            continue
        key = s.lower()
        if key in seen:
            continue

        if len(s) > 170:
            s = s[:167].rstrip() + '...'

        bullets.append(f"- {s}")
        seen.add(key)
        if len(bullets) >= max_points:
            return bullets

    # fallback for low punctuation transcripts
    if not bullets:
        words = cleaned.split()
        chunk = 28
        for i in range(0, len(words), chunk):
            part = " ".join(words[i:i + chunk]).strip()
            if len(part) < 40:
                continue
            if len(part) > 170:
                part = part[:167].rstrip() + '...'
            bullets.append(f"- {part}")
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
    dt = parse_upload_datetime(upload_date, timestamp)
    if dt is None:
        return "-"

    days = max((datetime.datetime.now() - dt).days, 0)
    if days == 0:
        return "Today"
    if days == 1:
        return "1 day ago"
    return f"{days} days ago"


def enrich_video_metadata(ydl, video_id, fallback_upload_date=None, fallback_timestamp=None):
    if fallback_upload_date or fallback_timestamp:
        return fallback_upload_date, fallback_timestamp

    try:
        details = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
        if not details:
            return None, None
        return details.get('upload_date'), details.get('timestamp')
    except Exception:
        return None, None


# --- PAGE CONFIG ---
st.set_page_config(page_title="Executive Tracker", page_icon="📊", layout="wide")

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
        'skip_download': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for channel_url in channels:
            try:
                info = ydl.extract_info(channel_url, download=False)
                if not info:
                    continue

                entries = info.get('entries', [])
                channel_title = info.get('channel') or info.get('uploader') or channel_url.split('@')[-1].split('/')[0]

                for entry in entries:
                    if not entry:
                        continue

                    vid_id = entry.get('id')
                    if not vid_id:
                        continue

                    upload_date, timestamp = enrich_video_metadata(
                        ydl,
                        vid_id,
                        fallback_upload_date=entry.get('upload_date'),
                        fallback_timestamp=entry.get('timestamp'),
                    )

                    all_videos.append(
                        {
                            'channel': channel_title,
                            'channel_url': channel_url,
                            'title': entry.get('title') or '(untitled)',
                            'url': f"https://www.youtube.com/watch?v={vid_id}",
                            'views': entry.get('view_count'),
                            'duration': entry.get('duration'),
                            'upload_date': upload_date,
                            'timestamp': timestamp,
                            'id': vid_id,
                        }
                    )
            except Exception:
                continue

    return all_videos


with st.sidebar:
    st.title("📊 Menu")
    selected_category = st.radio("Select Category:", list(CATEGORIES.keys()))
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.caption("💡 Using YouTube transcript + yt-dlp")


st.title(f"📺 {selected_category}")

with st.spinner("Updating Intelligence..."):
    videos = get_channel_data(selected_category)

if not videos:
    st.error("No videos found. Check connection / channel URLs.")
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

            for i, video in enumerate(channel_videos):
                c0, c1, c2, c3, c4, c5, c6 = st.columns([1, 4, 1, 1, 1, 1, 1])

                transcript_key = f"transcript_{video['id']}"
                summary_key = f"summary_{video['id']}"

                with c0:
                    with st.popover("🧠"):
                        st.caption("Quick Summary")
                        if st.button("Generate", key=f"sum_{video['id']}_{i}"):
                            with st.spinner("Building summary..."):
                                transcript = get_transcript(video['url'])
                                st.session_state[transcript_key] = transcript
                                st.session_state[summary_key] = summarize_transcript(transcript)

                        summary_lines = st.session_state.get(summary_key)
                        if summary_lines:
                            st.markdown("\n".join(summary_lines))
                        elif summary_key in st.session_state:
                            st.caption("No summary available.")

                c1.markdown(f"[{video['title']}]({video['url']})", unsafe_allow_html=True)
                c2.write(format_upload_age(video.get('upload_date'), video.get('timestamp')))
                c3.write(format_views(video.get('views')))
                c4.write(format_duration(video.get('duration')))

                with c5:
                    with st.popover("✨"):
                        st.caption("Copy Link:")
                        st.code(video['url'], language="text")
                        st.caption("External summary:")
                        st.link_button("Go to Gemini 💎", GEM_URL)

                with c6:
                    if st.button("📄", key=f"btn_{video['id']}_{i}", help="Fetch Transcript"):
                        with st.spinner("Fetching transcript..."):
                            st.session_state[transcript_key] = get_transcript(video['url'])

                    transcript_content = st.session_state.get(transcript_key)
                    if transcript_content and len(transcript_content.strip()) > 0:
                        st.download_button(
                            label="💾",
                            data=f"# {video['title']}\n\n{transcript_content}",
                            file_name=f"transcript_{video['id']}.md",
                            mime="text/markdown",
                            key=f"dl_{video['id']}_{i}",
                        )
                    elif transcript_key in st.session_state:
                        st.error("N/A")

                if i < len(channel_videos) - 1:
                    st.markdown("<hr style='margin: 5px 0; opacity: 0.1;'>", unsafe_allow_html=True)
