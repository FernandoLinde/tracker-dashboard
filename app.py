import datetime
import re
from itertools import groupby

import streamlit as st
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled, VideoUnavailable


# --- CONFIG ---
st.set_page_config(page_title="Executive Tracker", page_icon="📊", layout="wide")

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

st.markdown(
    """
<style>
    .block-container {padding-top: 2rem; padding-bottom: 4rem;}
    .metric-chip {background:#111827;border:1px solid #2d3748;padding:8px 10px;border-radius:8px;display:inline-block;margin-right:6px}
    .caption {color:#9CA3AF; font-size:0.8rem;}
</style>
""",
    unsafe_allow_html=True,
)


# --- HELPERS ---
def extract_video_id(video_url: str) -> str:
    if 'v=' in video_url:
        return video_url.split('v=')[-1].split('&')[0]
    if 'youtu.be/' in video_url:
        return video_url.split('youtu.be/')[-1].split('?')[0]
    return video_url.strip()


def get_api_instance():
    try:
        return YouTubeTranscriptApi()
    except Exception:
        return None


def fetch_transcript_list(video_id: str):
    api = get_api_instance()
    if api and hasattr(api, 'list'):
        return api.list(video_id)
    if hasattr(YouTubeTranscriptApi, 'list_transcripts'):
        return YouTubeTranscriptApi.list_transcripts(video_id)
    return None


def direct_fetch(video_id: str, languages):
    api = get_api_instance()
    if api and hasattr(api, 'fetch'):
        return api.fetch(video_id, languages=languages)
    if hasattr(YouTubeTranscriptApi, 'get_transcript'):
        return YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
    return None


def normalize_entries(payload):
    rows = []
    if not payload:
        return rows

    for item in payload:
        if hasattr(item, 'text'):
            text = (item.text or '').strip()
            start = float(getattr(item, 'start', 0) or 0)
            dur = float(getattr(item, 'duration', 0) or 0)
        else:
            text = str(item.get('text', '')).strip() if isinstance(item, dict) else ''
            start = float(item.get('start', 0) or 0) if isinstance(item, dict) else 0
            dur = float(item.get('duration', 0) or 0) if isinstance(item, dict) else 0
        if text:
            rows.append({'text': text, 'start': start, 'duration': dur})
    return rows


def format_ts(seconds):
    return str(datetime.timedelta(seconds=int(seconds or 0)))


def get_transcript_entries(video_url: str):
    video_id = extract_video_id(video_url)
    preferred = ['pt', 'pt-BR', 'en', 'en-US', 'es', 'fr', 'de']

    try:
        payload = None
        try:
            payload = direct_fetch(video_id, preferred)
        except NoTranscriptFound:
            payload = None

        if payload is None:
            transcript_list = fetch_transcript_list(video_id)
            if transcript_list is None:
                return []

            for lang in preferred:
                try:
                    payload = transcript_list.find_manually_created_transcript([lang]).fetch()
                    break
                except NoTranscriptFound:
                    continue

            if payload is None:
                for lang in preferred:
                    try:
                        payload = transcript_list.find_generated_transcript([lang]).fetch()
                        break
                    except NoTranscriptFound:
                        continue

            if payload is None:
                for transcript in transcript_list:
                    if getattr(transcript, 'is_translatable', False):
                        try:
                            payload = transcript.translate('en').fetch()
                            break
                        except Exception:
                            continue

        return normalize_entries(payload)
    except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable):
        return []
    except Exception:
        return []


def transcript_to_text(entries):
    return "\n".join([row['text'] for row in entries]).strip()


def summarize_transcript(text, max_points=4):
    if not text:
        return []
    cleaned = re.sub(r'\s+', ' ', text).strip()
    if not cleaned:
        return []

    bullets, seen = [], set()
    for sentence in re.split(r'(?<=[.!?])\s+', cleaned):
        s = sentence.strip(' -•\n\t')
        if len(s) < 45:
            continue
        key = s.lower()
        if key in seen:
            continue
        bullets.append(f"- {s[:177] + '...' if len(s) > 180 else s}")
        seen.add(key)
        if len(bullets) >= max_points:
            return bullets

    if not bullets:
        words = cleaned.split()
        for i in range(0, len(words), 30):
            part = " ".join(words[i:i + 30]).strip()
            if len(part) < 45:
                continue
            bullets.append(f"- {part[:177] + '...' if len(part) > 180 else part}")
            if len(bullets) >= max_points:
                break
    return bullets


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


def get_video_info(video_url: str):
    opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            info = ydl.extract_info(video_url, download=False)
        except Exception:
            return None

    if not info:
        return None

    return {
        'id': info.get('id'),
        'title': info.get('title') or '(untitled)',
        'channel': info.get('channel') or info.get('uploader') or '-',
        'views': info.get('view_count'),
        'duration': info.get('duration'),
        'upload_date': info.get('upload_date'),
        'timestamp': info.get('timestamp'),
        'url': info.get('webpage_url') or video_url,
    }


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


# --- SIDEBAR ---
with st.sidebar:
    st.title("📊 Menu")
    mode = st.radio("Mode", ["Transcript Studio", "Channel Tracker"], index=0)

    if mode == "Channel Tracker":
        selected_category = st.radio("Category", list(CATEGORIES.keys()))
    else:
        selected_category = None

    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.caption("Built for transcript download + quick summaries + upload age")


# --- MAIN ---
if mode == "Transcript Studio":
    st.title("🎬 Transcript Studio")
    st.caption("A youtube-transcript.io style flow adapted for your workflow.")

    default_url = "https://www.youtube.com/watch?v=vvfQnO7OjWI"
    video_url = st.text_input("YouTube URL", value=default_url)

    col_a, col_b = st.columns([1, 1])
    load_clicked = col_a.button("Load Video")
    analyze_clicked = col_b.button("Generate Summary")

    if load_clicked or analyze_clicked:
        info = get_video_info(video_url)
        if not info:
            st.error("Could not load video metadata. Check URL / network.")
        else:
            st.session_state['studio_info'] = info

        entries = get_transcript_entries(video_url)
        st.session_state['studio_entries'] = entries
        st.session_state['studio_text'] = transcript_to_text(entries)

        if analyze_clicked:
            st.session_state['studio_summary'] = summarize_transcript(st.session_state.get('studio_text', ''))

    info = st.session_state.get('studio_info')
    entries = st.session_state.get('studio_entries', [])
    transcript_text = st.session_state.get('studio_text', '')

    if info:
        st.subheader(info['title'])
        st.write(f"**Channel:** {info['channel']}")
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"<div class='metric-chip'>👀 {format_views(info['views'])}</div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-chip'>⏱️ {format_duration(info['duration'])}</div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-chip'>📅 {format_upload_age(info['upload_date'], info['timestamp'])}</div>", unsafe_allow_html=True)
        c4.link_button("Open on YouTube", info['url'])

    if transcript_text:
        st.success(f"Transcript loaded ({len(entries)} segments).")

        search = st.text_input("Search transcript", value="")
        filtered = entries
        if search.strip():
            needle = search.strip().lower()
            filtered = [r for r in entries if needle in r['text'].lower()]

        with st.expander("Transcript", expanded=True):
            for row in filtered[:800]:
                st.markdown(f"**[{format_ts(row['start'])}]** {row['text']}")

        st.download_button(
            "💾 Download transcript (.md)",
            data=f"# {info['title'] if info else 'Transcript'}\n\n{transcript_text}",
            file_name=f"transcript_{extract_video_id(video_url)}.md",
            mime="text/markdown",
            key="studio_download",
        )

    if st.session_state.get('studio_summary'):
        st.subheader("Quick Summary")
        st.markdown("\n".join(st.session_state['studio_summary']))
        st.link_button("Deep-dive in Gemini 💎", GEM_URL)

else:
    st.title(f"📺 {selected_category}")
    with st.spinner("Loading channels..."):
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
                h0.caption("SUM")
                h1.caption("VIDEO")
                h2.caption("AGE")
                h3.caption("VIEWS")
                h4.caption("LENGTH")
                h5.caption("EXTRA")
                h6.caption("TRANS")
                st.divider()

                for i, v in enumerate(channel_videos):
                    c0, c1, c2, c3, c4, c5, c6 = st.columns([1, 4, 1, 1, 1, 1, 1])
                    transcript_key = f"transcript_{v['id']}"
                    summary_key = f"summary_{v['id']}"

                    with c0:
                        with st.popover("🧠"):
                            if st.button("Generate", key=f"sum_{v['id']}_{i}"):
                                txt = transcript_to_text(get_transcript_entries(v['url']))
                                st.session_state[transcript_key] = txt
                                st.session_state[summary_key] = summarize_transcript(txt)
                            summary = st.session_state.get(summary_key)
                            if summary:
                                st.markdown("\n".join(summary))

                    c1.markdown(f"[{v['title']}]({v['url']})")
                    c2.write(format_upload_age(v.get('upload_date'), v.get('timestamp')))
                    c3.write(format_views(v.get('views')))
                    c4.write(format_duration(v.get('duration')))

                    with c5:
                        with st.popover("✨"):
                            st.code(v['url'], language="text")
                            st.link_button("Gemini 💎", GEM_URL)

                    with c6:
                        if st.button("📄", key=f"btn_{v['id']}_{i}"):
                            st.session_state[transcript_key] = transcript_to_text(get_transcript_entries(v['url']))

                        txt = st.session_state.get(transcript_key)
                        if txt:
                            st.download_button(
                                "💾",
                                data=f"# {v['title']}\n\n{txt}",
                                file_name=f"transcript_{v['id']}.md",
                                mime="text/markdown",
                                key=f"dl_{v['id']}_{i}",
                            )
                        elif transcript_key in st.session_state:
                            st.error("N/A")

                    if i < len(channel_videos) - 1:
                        st.markdown("<hr style='margin: 5px 0; opacity: 0.1;'>", unsafe_allow_html=True)
