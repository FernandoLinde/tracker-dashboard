import datetime
import html
import json
import re
import urllib.parse
import urllib.request

import streamlit as st
import yt_dlp
try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    YouTubeTranscriptApi = None

# --- PAGE CONFIG (Must be first) ---
st.set_page_config(page_title="Executive Tracker", page_icon=":bar_chart:", layout="wide")

# --- CONFIGURATION ---
GEM_URL = "https://gemini.google.com/gem/1HTDzIGbVXIA7dJodfgK3jahP3sayuWWl?usp=sharing"
MAX_VIDEOS_PER_CHANNEL = 5
PREFERRED_LANGUAGES = ["pt-BR", "pt", "en", "en-US"]
REQUEST_TIMEOUT_SECONDS = 15

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

# --- CUSTOM CSS ---
st.markdown(
    """
<style>
    div[data-testid="stVerticalBlock"] > div { margin-bottom: -10px; }
    hr { margin-top: 6px; margin-bottom: 6px; }
    div[data-testid="column"] { display: flex; align-items: center; }
</style>
""",
    unsafe_allow_html=True,
)


def extract_video_id(video_url_or_id):
    if not video_url_or_id:
        return None
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", video_url_or_id):
        return video_url_or_id

    parsed = urllib.parse.urlparse(video_url_or_id)
    host = (parsed.netloc or "").lower()

    if "youtu.be" in host:
        candidate = parsed.path.strip("/").split("/")[0]
        return candidate if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate or "") else None

    if "youtube.com" in host:
        if parsed.path.startswith("/watch"):
            candidate = urllib.parse.parse_qs(parsed.query).get("v", [None])[0]
            return candidate if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate or "") else None

        for prefix in ("/shorts/", "/embed/", "/live/"):
            if parsed.path.startswith(prefix):
                candidate = parsed.path.replace(prefix, "").split("/")[0]
                return candidate if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate or "") else None

    return None


def parse_upload_date(upload_date):
    if not upload_date:
        return None
    try:
        return datetime.datetime.strptime(str(upload_date), "%Y%m%d")
    except ValueError:
        return None


def format_date(upload_date, timestamp):
    dt_obj = parse_upload_date(upload_date)
    if dt_obj:
        return dt_obj.strftime("%Y-%m-%d")

    if timestamp:
        try:
            return datetime.datetime.fromtimestamp(int(timestamp)).strftime("%Y-%m-%d")
        except (TypeError, ValueError, OSError):
            return "-"

    return "-"


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
    except (TypeError, ValueError):
        return "-"


def _sort_timestamp(upload_date, timestamp):
    if timestamp:
        try:
            return int(timestamp)
        except (TypeError, ValueError):
            pass

    dt_obj = parse_upload_date(upload_date)
    if dt_obj:
        return int(dt_obj.replace(tzinfo=datetime.timezone.utc).timestamp())

    return 0


def _clean_text(raw_text):
    text = html.unescape(raw_text or "")
    text = text.replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _join_segments(segments):
    pieces = []
    for segment in segments:
        text = _clean_text(segment.get("text", ""))
        if text:
            pieces.append(text)
    return " ".join(pieces).strip()


def _transcript_from_api(video_id):
    if YouTubeTranscriptApi is None:
        raise RuntimeError("youtube-transcript-api is not installed.")

    api = YouTubeTranscriptApi()

    if hasattr(api, "fetch"):
        fetched = api.fetch(video_id, languages=PREFERRED_LANGUAGES)
        if hasattr(fetched, "to_raw_data"):
            raw_segments = fetched.to_raw_data()
        else:
            raw_segments = [
                {
                    "text": getattr(item, "text", ""),
                    "start": getattr(item, "start", 0),
                    "duration": getattr(item, "duration", 0),
                }
                for item in fetched
            ]
        return _join_segments(raw_segments), getattr(fetched, "language_code", None)

    if hasattr(YouTubeTranscriptApi, "get_transcript"):
        raw_segments = YouTubeTranscriptApi.get_transcript(video_id, languages=PREFERRED_LANGUAGES)
        return _join_segments(raw_segments), None

    raw_segments = api.get_transcript(video_id, languages=PREFERRED_LANGUAGES)
    return _join_segments(raw_segments), None


def _choose_caption_tracks(caption_dict):
    if not caption_dict:
        return []

    ordered = []
    seen = set()

    def push(track):
        if not track:
            return
        track_key = track.get("url") or id(track)
        if track_key not in seen:
            ordered.append(track)
            seen.add(track_key)

    for wanted in PREFERRED_LANGUAGES:
        for key, tracks in caption_dict.items():
            if key.lower() == wanted.lower():
                for track in tracks:
                    push(track)

    for wanted in PREFERRED_LANGUAGES:
        for key, tracks in caption_dict.items():
            if key.lower().startswith(wanted.lower().split("-")[0]):
                for track in tracks:
                    push(track)

    for tracks in caption_dict.values():
        for track in tracks:
            push(track)

    return ordered


def _parse_caption_payload(payload, ext_hint):
    ext = (ext_hint or "").lower()
    stripped_payload = payload.lstrip()

    if ext in {"json3", "srv3"} or stripped_payload.startswith("{"):
        data = json.loads(payload)
        events = data.get("events", [])
        pieces = []
        for event in events:
            for seg in event.get("segs", []):
                piece = _clean_text(seg.get("utf8", ""))
                if piece:
                    pieces.append(piece)
        return " ".join(pieces).strip()

    lines = []
    for line in payload.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("WEBVTT"):
            continue
        if "-->" in stripped:
            continue
        if re.fullmatch(r"\d+", stripped):
            continue
        lines.append(_clean_text(stripped))
    return " ".join(lines).strip()


def _transcript_from_ydlp(video_url):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)

    if not info:
        return None, None, "yt-dlp could not load this video."

    last_error = None
    for source_name, caption_dict in (
        ("manual subtitles", info.get("subtitles") or {}),
        ("auto captions", info.get("automatic_captions") or {}),
    ):
        tracks = _choose_caption_tracks(caption_dict)
        if not tracks:
            continue

        for track in tracks:
            caption_url = track.get("url")
            ext_hint = track.get("ext")
            if not caption_url:
                continue

            try:
                with urllib.request.urlopen(caption_url, timeout=15) as response:
                    payload = response.read().decode("utf-8", errors="ignore")
                transcript_text = _parse_caption_payload(payload, ext_hint)
                if transcript_text:
                    return transcript_text, source_name, None
            except Exception as exc:
                last_error = f"Failed to download captions: {exc}"

    if last_error:
        return None, None, last_error

    return None, None, "No subtitles or auto-captions were found for this video."


@st.cache_data(ttl=3600)
def get_video_transcript(video_url, video_id):
    if not video_id:
        return {"ok": False, "error": "Could not parse a valid YouTube video id."}

    try:
        transcript_text, language = _transcript_from_api(video_id)
        if transcript_text:
            return {
                "ok": True,
                "text": transcript_text,
                "source": "youtube-transcript-api",
                "language": language or "auto",
            }
    except Exception as exc:
        api_error = f"{type(exc).__name__}: {exc}"
    else:
        api_error = "youtube-transcript-api returned an empty transcript."

    transcript_text, source_name, fallback_error = _transcript_from_ydlp(video_url)
    if transcript_text:
        return {
            "ok": True,
            "text": transcript_text,
            "source": f"yt-dlp ({source_name})",
            "language": "unknown",
        }

    return {
        "ok": False,
        "error": f"Transcript failed. API error: {api_error}. Fallback error: {fallback_error}",
    }


def summarize_transcript(transcript_text, max_points=5):
    sentences = re.split(r"(?<=[.!?])\s+", transcript_text)
    sentences = [sentence.strip() for sentence in sentences if sentence.strip()]

    if len(sentences) <= max_points:
        return sentences

    stop_words = {
        "the", "and", "that", "this", "with", "from", "have", "were", "what", "about", "would", "there",
        "para", "com", "uma", "que", "por", "isso", "como", "mais", "muito", "sobre", "entre", "tambem",
    }

    frequencies = {}
    for sentence in sentences:
        for token in re.findall(r"[A-Za-zÀ-ÿ0-9']+", sentence.lower()):
            if len(token) < 3 or token in stop_words:
                continue
            frequencies[token] = frequencies.get(token, 0) + 1

    if not frequencies:
        return sentences[:max_points]

    scored = []
    for index, sentence in enumerate(sentences):
        tokens = re.findall(r"[A-Za-zÀ-ÿ0-9']+", sentence.lower())
        if not tokens:
            continue
        score = sum(frequencies.get(token, 0) for token in tokens) / (len(tokens) ** 0.5)
        scored.append((score, index, sentence))

    top = sorted(scored, key=lambda item: item[0], reverse=True)[:max_points]
    top = sorted(top, key=lambda item: item[1])
    return [item[2] for item in top]


def build_prompt(video_url, summary_points, transcript_text):
    summary_block = "\n".join(f"- {point}" for point in summary_points)
    clipped_transcript = transcript_text[:8000]
    return (
        f"Resuma e destaque os principais pontos do video: {video_url}\n\n"
        f"Resumo inicial:\n{summary_block}\n\n"
        f"Transcricao (recorte):\n{clipped_transcript}"
    )


@st.cache_data(ttl=1800)
def get_channel_data(category_name):
    channels = CATEGORIES[category_name]
    all_videos = []
    errors = []
    seen_video_ids = set()

    flat_opts = {
        "extract_flat": True,
        "playlist_items": f"1-{MAX_VIDEOS_PER_CHANNEL}",
        "lazy_playlist": True,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "skip_download": True,
        "socket_timeout": REQUEST_TIMEOUT_SECONDS,
        "retries": 1,
    }
    detail_opts = {
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "skip_download": True,
        "socket_timeout": REQUEST_TIMEOUT_SECONDS,
        "retries": 1,
    }

    with yt_dlp.YoutubeDL(flat_opts) as flat_ydl, yt_dlp.YoutubeDL(detail_opts) as detail_ydl:
        for channel_url in channels:
            clean_url = channel_url.rstrip("/")
            if not clean_url.endswith("/videos"):
                clean_url += "/videos"

            try:
                info = flat_ydl.extract_info(clean_url, download=False)
                if not info:
                    errors.append(f"Channel failed: {clean_url}")
                    continue

                entries = info.get("entries") or []
                channel_title = info.get("channel") or info.get("title") or clean_url.split("@")[-1]

                for entry in entries:
                    if not entry:
                        continue

                    video_id = entry.get("id") or extract_video_id(entry.get("url"))
                    if not video_id or video_id in seen_video_ids:
                        continue

                    video_url = entry.get("webpage_url") or f"https://www.youtube.com/watch?v={video_id}"
                    upload_date = entry.get("upload_date")
                    timestamp = entry.get("timestamp")
                    views = entry.get("view_count")
                    duration = entry.get("duration")
                    title = entry.get("title") or "Untitled"

                    try:
                        detail = detail_ydl.extract_info(video_url, download=False)
                    except Exception:
                        detail = None
                    if detail:
                        upload_date = upload_date or detail.get("upload_date")
                        timestamp = timestamp or detail.get("timestamp")
                        views = views if views is not None else detail.get("view_count")
                        duration = duration or detail.get("duration")
                        if title == "Untitled":
                            title = detail.get("title") or title

                    seen_video_ids.add(video_id)
                    all_videos.append(
                        {
                            "id": video_id,
                            "channel": channel_title,
                            "title": title,
                            "url": video_url,
                            "views": views,
                            "duration": duration,
                            "upload_date": upload_date,
                            "timestamp": timestamp,
                            "sort_ts": _sort_timestamp(upload_date, timestamp),
                        }
                    )
            except Exception as exc:
                errors.append(f"Channel failed: {clean_url} ({type(exc).__name__})")

    # Full extraction fallback when all channels returned empty.
    if not all_videos:
        fallback_opts = {
            "playlist_items": f"1-{MAX_VIDEOS_PER_CHANNEL}",
            "lazy_playlist": True,
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
            "skip_download": True,
            "socket_timeout": REQUEST_TIMEOUT_SECONDS,
            "retries": 1,
        }
        with yt_dlp.YoutubeDL(fallback_opts) as ydl:
            for channel_url in channels:
                clean_url = channel_url.rstrip("/")
                if not clean_url.endswith("/videos"):
                    clean_url += "/videos"

                try:
                    info = ydl.extract_info(clean_url, download=False)
                    entries = info.get("entries") or []
                    channel_title = info.get("channel") or info.get("title") or clean_url.split("@")[-1]
                    for entry in entries:
                        if not entry:
                            continue
                        video_id = entry.get("id") or extract_video_id(entry.get("url"))
                        if not video_id or video_id in seen_video_ids:
                            continue
                        seen_video_ids.add(video_id)
                        all_videos.append(
                            {
                                "id": video_id,
                                "channel": channel_title,
                                "title": entry.get("title") or "Untitled",
                                "url": entry.get("webpage_url") or f"https://www.youtube.com/watch?v={video_id}",
                                "views": entry.get("view_count"),
                                "duration": entry.get("duration"),
                                "upload_date": entry.get("upload_date"),
                                "timestamp": entry.get("timestamp"),
                                "sort_ts": _sort_timestamp(entry.get("upload_date"), entry.get("timestamp")),
                            }
                        )
                except Exception as exc:
                    errors.append(f"Fallback failed: {clean_url} ({type(exc).__name__})")

    all_videos.sort(key=lambda item: item.get("sort_ts", 0), reverse=True)
    return all_videos, errors


def render_transcript_panel(video):
    video_id = video.get("id") or extract_video_id(video.get("url"))
    transcript_data = get_video_transcript(video.get("url"), video_id)

    st.subheader("Transcript")
    st.caption(f"Selected video: {video.get('title')}")
    st.markdown(f"[Open on YouTube]({video.get('url')})")

    if not transcript_data["ok"]:
        st.error(transcript_data["error"])
        return

    transcript_text = transcript_data["text"]
    summary_points = summarize_transcript(transcript_text)
    gemini_prompt = build_prompt(video.get("url"), summary_points, transcript_text)

    left, right = st.columns([1, 2])
    left.markdown("**Summary**")
    if summary_points:
        for point in summary_points:
            left.write(f"- {point}")
    else:
        left.write("- No summary could be generated.")

    left.caption(f"Transcript source: {transcript_data.get('source')}")
    left.link_button("Open Gemini", GEM_URL, use_container_width=True)
    with left.popover("Gemini Prompt"):
        st.code(gemini_prompt, language="text")

    right.markdown("**Transcript Text**")
    right.text_area(
        "Transcript content",
        transcript_text,
        height=360,
        key=f"transcript_{video_id}",
        label_visibility="collapsed",
    )
    right.download_button(
        "Download Transcript (.txt)",
        data=transcript_text.encode("utf-8"),
        file_name=f"{video_id}_transcript.txt",
        mime="text/plain",
        use_container_width=True,
    )


# --- SIDEBAR ---
with st.sidebar:
    st.title("Menu")
    selected_category = st.radio("Category:", list(CATEGORIES.keys()))
    if st.button("Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- MAIN CONTENT ---
st.title(f"{selected_category} Videos")

manual_url = st.text_input("Paste a YouTube URL (optional):")
if st.button("Fetch Transcript From URL", use_container_width=True):
    manual_video_id = extract_video_id(manual_url)
    st.session_state["selected_video"] = {
        "id": manual_video_id,
        "title": manual_url or "Manual URL",
        "url": manual_url,
    }

with st.spinner("Loading channels..."):
    videos, fetch_errors = get_channel_data(selected_category)

if fetch_errors:
    with st.expander("Channel loading issues"):
        for issue in fetch_errors:
            st.write(f"- {issue}")

selected_video = st.session_state.get("selected_video")
if selected_video and selected_video.get("url"):
    render_transcript_panel(selected_video)
    st.markdown("---")

if not videos:
    st.error("No videos found for this category.")
    if st.button("Retry Channel Fetch", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    if fetch_errors:
        st.warning("Some channels returned errors. See details below.")
        for issue in fetch_errors[:8]:
            st.write(f"- {issue}")
else:
    cols = st.columns([2, 1.2, 4.8, 1, 1, 1])
    cols[0].markdown("**Channel**")
    cols[1].markdown("**Summary**")
    cols[2].markdown("**Video Title**")
    cols[3].markdown("**Date**")
    cols[4].markdown("**Views**")
    cols[5].markdown("**Length**")
    st.markdown("---")

    for video in videos:
        c1, c2, c3, c4, c5, c6 = st.columns([2, 1.2, 4.8, 1, 1, 1])
        c1.write(video["channel"])

        if c2.button("Summary", key=f"summary_{video['id']}", use_container_width=True):
            st.session_state["selected_video"] = video
            st.rerun()

        c3.markdown(f"[{video['title']}]({video['url']})")
        c4.write(format_date(video.get("upload_date"), video.get("timestamp")))
        c5.write(format_views(video.get("views")))
        c6.write(format_duration(video.get("duration")))
        st.divider()
