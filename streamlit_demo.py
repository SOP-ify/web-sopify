# streamlit_demo.py
#
# -> demo UI chat untuk test ML SOP-ify
#      -> text-to-sop  : ketik catatan → generate SOP
#      -> audio-to-text: rekam suara → auto-fill input (voice → STT → teks)
#      -> auto-save    : hasil generate langsung disimpan ke MongoDB via /api/v1/sop
# -> token hardcoded, tanpa login
# -> jalankan: streamlit run streamlit_demo.py

import hashlib
from typing import Optional

import requests
import streamlit as st

try:
    from audio_recorder_streamlit import audio_recorder
    AUDIO_OK = True
except ImportError:
    AUDIO_OK = False

# ── config ─────────────────────────────────────────────────────────────────────

import os

API_BASE = os.environ.get("API_URL", "http://localhost:8000").rstrip("/")
TOKEN    = os.environ.get("API_TOKEN", "")
HEADERS  = {"Authorization": f"Bearer {TOKEN}"}


STYLES = {
    "📄 Dokumen Terstruktur": "dokumen_terstruktur",
    "💬 Chat WhatsApp":       "chat_wa",
    "🎙️ Instruksi Lisan":    "instruksi_lisan",
    "📊 Diagram Mermaid":     "diagram_mermaid",
    "📋 Kolom Tabel":         "kolom_tabel",
    "🧪 Fine-Tune Prompt":    "fine_tune",
}

KATEGORI_LIST = [
    "F&B / Kuliner", "Retail / Toko", "Kecantikan / Salon",
    "Otomotif / Bengkel", "Industri Rumahan / Makanan", "Jasa / Layanan",
    "Pertanian / Perkebunan", "Pendidikan / Kursus",
    "Logistik / Ekspedisi", "Kesehatan / Apotek", "Lainnya...",
]

# ── page setup ─────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="SOP-ify · Demo",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem !important; padding-bottom: 0 !important; }

/* user bubble */
.user-bubble {
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    color: white; padding: 14px 18px;
    border-radius: 18px 18px 4px 18px;
    margin: 8px 0 8px 18%; font-size: 0.93rem;
    line-height: 1.5; box-shadow: 0 2px 14px rgba(99,102,241,0.35);
}

/* bot bubble */
.bot-bubble {
    background: #1a1a2e; border: 1px solid #2d2d44;
    color: #e2e2e9; padding: 18px 22px;
    border-radius: 18px 18px 18px 4px;
    margin: 8px 18% 8px 0; font-size: 0.9rem;
    line-height: 1.6; box-shadow: 0 2px 14px rgba(0,0,0,0.25);
}
.bot-bubble pre { background: #0d0d1a; border-radius: 8px; padding: 14px; font-size: 0.82rem; overflow-x: auto; white-space: pre-wrap; }
.bot-bubble code { color: #a5b4fc; }
.bot-bubble summary { cursor: pointer; color: #a5b4fc; font-size: 0.85rem; margin-bottom: 8px; }
.bot-bubble summary:hover { color: #c4b5fd; }

/* step card */
.step-card {
    background: #0d0d1a; border-left: 3px solid #6366f1;
    border-radius: 0 8px 8px 0; padding: 10px 14px;
    margin: 6px 0; font-size: 0.87rem;
}
.step-num   { color: #6366f1; font-weight: 700; font-size: 0.85rem; }
.step-title { color: #c4c4d4; font-weight: 600; }
.step-desc  { color: #8a8a9e; font-size: 0.83rem; margin-top: 2px; }

/* badge */
.meta-badge {
    display: inline-block; background: #2d2d44; color: #a5b4fc;
    font-size: 0.74rem; padding: 2px 10px;
    border-radius: 20px; margin: 4px 3px 12px 0;
}
.badge-green { background: #14321f; color: #4ade80; }
.badge-save  { background: #1a2744; color: #60a5fa; }

/* ── generating animation ─────────────────────────────────────────────────── */
.generating-bubble {
    background: #1a1a2e; border: 1px solid #3730a3;
    color: #e2e2e9; padding: 20px 22px;
    border-radius: 18px 18px 18px 4px;
    margin: 8px 18% 8px 0;
    box-shadow: 0 2px 20px rgba(99,102,241,0.2);
    position: relative; overflow: hidden;
}
.gen-shimmer {
    position: absolute; top: 0; left: -100%; width: 60%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(99,102,241,0.08), transparent);
    animation: shimmer 2s infinite;
}
@keyframes shimmer {
    0%   { left: -100%; }
    100% { left: 200%; }
}
.gen-header {
    display: flex; align-items: center; gap: 12px;
    margin-bottom: 16px;
}
.gen-title { color: #a5b4fc; font-weight: 600; font-size: 0.95rem; }

/* dot bounce */
.dots { display: flex; gap: 5px; align-items: center; }
.dots span {
    width: 8px; height: 8px; border-radius: 50%;
    background: #6366f1; display: block;
    animation: bounce 1.2s infinite ease-in-out;
}
.dots span:nth-child(1) { animation-delay: 0s; }
.dots span:nth-child(2) { animation-delay: 0.18s; }
.dots span:nth-child(3) { animation-delay: 0.36s; }
@keyframes bounce {
    0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
    30%            { transform: translateY(-8px); opacity: 1; }
}

/* step timeline */
.gen-steps { display: flex; flex-direction: column; gap: 10px; }
.gen-step {
    display: flex; align-items: center; gap: 10px;
    font-size: 0.85rem; color: #555;
}
.gen-step.done   { color: #4ade80; }
.gen-step.active { color: #a5b4fc; font-weight: 500; }
.gen-step .icon  { width: 22px; text-align: center; font-size: 1rem; }
.step-bar {
    height: 3px; border-radius: 2px;
    background: #2d2d44; margin-top: 12px; overflow: hidden;
}
.step-bar-fill {
    height: 100%; background: linear-gradient(90deg, #6366f1, #8b5cf6);
    border-radius: 2px;
    animation: fill-bar 60s linear forwards;
}
@keyframes fill-bar {
    0%   { width: 0%; }
    80%  { width: 85%; }
    100% { width: 92%; }
}

/* empty state */
.empty-chat { text-align: center; padding: 60px 20px; color: #444; }
.empty-chat h2 { font-size: 2.2rem; margin-bottom: 8px; }
.empty-chat p  { font-size: 0.95rem; color: #555; }

/* sidebar */
[data-testid="stSidebar"] { background: #0a0a16; }
[data-testid="stSidebar"] label { color: #a5b4fc !important; font-size: 0.85rem !important; }

.voice-hint { font-size: 0.76rem; color: #555; text-align: center; margin-top: 2px; }
.saved-hint { font-size: 0.78rem; color: #60a5fa; }
</style>
""", unsafe_allow_html=True)

# ── session state ──────────────────────────────────────────────────────────────

for key, default in [
    ("messages",         []),
    ("last_audio_hash",  None),
    ("model_status",     None),
    ("clear_catatan",    False),
    ("generating",       False),    # True saat sedang generate
    ("pending_payload",  None),     # data yang dikirim ke API
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── pending state → HARUS sebelum widget apapun di-render ─────────────────────

if st.session_state.clear_catatan:
    st.session_state["_catatan_key"] = ""
    st.session_state.clear_catatan = False

# ── api helpers ────────────────────────────────────────────────────────────────

import sys
from datetime import datetime

def _log(label: str, content: str = "", color: str = "\033[96m") -> None:
    """Print log ke terminal dengan timestamp dan separator."""
    reset = "\033[0m"
    bold  = "\033[1m"
    ts    = datetime.now().strftime("%H:%M:%S")
    sep   = "─" * 60
    # pakai stderr supaya tidak ditangkap Streamlit
    sys.stderr.write(f"\n{color}{sep}{reset}\n")
    sys.stderr.write(f"{bold}{color}[{ts}] {label}{reset}\n")
    if content:
        sys.stderr.write(content + "\n")
    sys.stderr.write(f"{color}{sep}{reset}\n")
    sys.stderr.flush()


def call_stt(audio_bytes: bytes) -> Optional[str]:
    _log(
        "🎤 STT: Kirim audio ke /ml/audio-to-text",
        f"  audio size : {len(audio_bytes):,} bytes\n"
        f"  language   : id",
        color="\033[95m",  # magenta
    )
    try:
        resp = requests.post(
            f"{API_BASE}/api/v1/ml/audio-to-text",
            headers=HEADERS,
            files={"audio": ("recording.wav", audio_bytes, "audio/wav")},
            data={"language": "id"},
            timeout=60,
        )
        transcript = resp.json().get("data", {}).get("transcript") if resp.ok else None
        if transcript:
            _log(
                "✅ STT: Transkrip berhasil",
                f"  status     : {resp.status_code}\n"
                f"  transcript :\n\n{transcript}",
                color="\033[92m",  # green
            )
        else:
            _log(
                f"❌ STT: Gagal ({resp.status_code})",
                f"  response   : {resp.text[:300]}",
                color="\033[91m",  # red
            )
        return transcript
    except Exception as e:
        _log("❌ STT: Exception", str(e), color="\033[91m")
        st.error(f"STT error: {e}")
        return None


def call_text_to_sop(payload: dict) -> Optional[dict]:
    body = {
        "sop_name":       payload["sop_name"],
        "kategori":       payload["kategori"],
        "catatan":        payload["catatan"],
        "style":          payload["style_val"],
        "max_new_tokens": 512,
        "temperature":    payload["temperature"],
    }
    _log(
        "🚀 TEXT-TO-SOP: Kirim request ke /ml/text-to-sop",
        f"  sop_name    : {body['sop_name']}\n"
        f"  kategori    : {body['kategori']}\n"
        f"  style       : {body['style']}\n"
        f"  temperature : {body['temperature']}\n"
        f"  max_tokens  : {body['max_new_tokens']}\n"
        f"  catatan     :\n\n{body['catatan']}",
        color="\033[96m",  # cyan
    )
    try:
        resp = requests.post(
            f"{API_BASE}/api/v1/ml/text-to-sop",
            headers=HEADERS,
            json=body,
            timeout=180,
        )
        if resp.ok:
            data = resp.json().get("data", {})
            steps_preview = "\n".join(
                f"  #{s['no']} {s['judul']}: {s['deskripsi'][:60]}..."
                if len(s['deskripsi']) > 60 else
                f"  #{s['no']} {s['judul']}: {s['deskripsi']}"
                for s in data.get("steps", [])
            )
            _log(
                "✅ TEXT-TO-SOP: Generate berhasil",
                f"  status      : {resp.status_code}\n"
                f"  step_count  : {data.get('step_count', 0)}\n"
                f"  valid       : {data.get('valid')}\n"
                f"  gen_time    : {data.get('generation_time_seconds', 0):.2f}s\n"
                f"\n--- RAW SOP OUTPUT ---\n\n{data.get('sop', '')}\n"
                f"\n--- STEPS ---\n{steps_preview}",
                color="\033[92m",  # green
            )
            return data
        else:
            _log(
                f"❌ TEXT-TO-SOP: API error ({resp.status_code})",
                f"  detail : {resp.json().get('detail', resp.text[:300])}",
                color="\033[91m",
            )
            st.error(f"API {resp.status_code}: {resp.json().get('detail', resp.text)}")
            return None
    except requests.exceptions.Timeout:
        _log("⏱ TEXT-TO-SOP: Timeout setelah 180s", color="\033[93m")
        st.error("⏱ Timeout — model sedang sibuk, coba lagi beberapa detik.")
        return None
    except Exception as e:
        _log("❌ TEXT-TO-SOP: Exception", str(e), color="\033[91m")
        st.error(f"Request error: {e}")
        return None


def save_to_history(payload: dict, result: dict) -> Optional[str]:
    """Simpan hasil generate SOP ke MongoDB via /api/v1/sop.
    - input  : payload (dict submission), result (dict dari text-to-sop)
    - output : sop_id (str) kalau berhasil disimpan, None kalau gagal
    """
    _log(
        "💾 SAVE: Simpan ke MongoDB via /api/v1/sop",
        f"  sop_name : {payload['sop_name']}\n"
        f"  step_count: {result.get('step_count', 0)}",
        color="\033[94m",  # blue
    )
    try:
        body = {
            "sop_name":                 payload["sop_name"],
            "kategori":                 payload["kategori"],
            "catatan":                  payload["catatan"],
            "sop":                      result["sop"],
            "style":                    payload["style_val"],
            "steps":                    result["steps"],
            "step_count":               result["step_count"],
            "valid":                    result["valid"],
            "attempt":                  1,
            "generation_time_seconds":  result.get("generation_time_seconds"),
        }
        resp = requests.post(
            f"{API_BASE}/api/v1/sop",
            headers=HEADERS,
            json=body,
            timeout=10,
        )
        if resp.ok:
            sop_id = resp.json().get("data", {}).get("id")
            _log(
                "✅ SAVE: Tersimpan ke MongoDB",
                f"  sop_id : {sop_id}\n"
                f"  status : {resp.status_code}",
                color="\033[92m",
            )
            return sop_id
        else:
            _log(
                f"❌ SAVE: Gagal ({resp.status_code})",
                f"  detail : {resp.json().get('detail', resp.text[:200])}",
                color="\033[91m",
            )
            return None
    except Exception as e:
        _log("❌ SAVE: Exception", str(e), color="\033[91m")
        return None


def check_model_status() -> dict:
    try:
        resp = requests.get(f"{API_BASE}/api/v1/ml/status", headers=HEADERS, timeout=5)
        return resp.json().get("data", {}) if resp.ok else {}
    except Exception:
        return {}

# ── sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 📋 SOP-ify")
    st.markdown("*ML Demo — Gemma 2 + LoRA*")
    st.divider()

    if st.button("🔄 Cek Status Model", use_container_width=True):
        st.session_state.model_status = check_model_status()

    if st.session_state.model_status:
        s = st.session_state.model_status
        sop_ok = s.get("sop_generator_loaded", False)
        stt_ok = s.get("stt_engine_loaded", False)
        dev    = s.get("sop_generator_device", "-")
        st.markdown(
            f"{'🟢' if sop_ok else '🔴'} SOP Model: "
            f"`{'loaded' if sop_ok else 'not loaded'}`"
            + (f" `({dev})`" if sop_ok else "") + "\n\n"
            + f"{'🟢' if stt_ok else '🔴'} Whisper STT: "
            f"`{'loaded' if stt_ok else 'not loaded'}`"
        )

    st.divider()
    st.markdown("**⚙️ Pengaturan**")

    sop_name_input = st.text_input("Nama SOP", placeholder="Kosongkan = otomatis")

    kat_choice = st.selectbox("Kategori Usaha", KATEGORI_LIST)
    kategori = (
        st.text_input("Ketik kategori:", placeholder="contoh: Laundry")
        if kat_choice == "Lainnya..." else kat_choice
    )

    style_label = st.selectbox("Format Output", list(STYLES.keys()))
    style_val   = STYLES[style_label]

    temperature = st.slider(
        "Temperature", 0.1, 1.2, 0.7, 0.05,
        help="Rendah = konsisten, tinggi = kreatif"
    )

    st.divider()
    if st.button("🗑️ Hapus Riwayat Chat", use_container_width=True):
        st.session_state.messages    = []
        st.session_state.generating  = False
        st.session_state.pending_payload = None
        st.rerun()

import re
import base64
import json as _json

def _render_mermaid_block(mermaid_code: str) -> None:
    """Render mermaid diagram via mermaid.ink API (server-side render → PNG).
    - input  : mermaid_code (string isi diagram, tanpa fence/tag)
    - output : preview fixed-width + expander full-width via st.image
    - catatan: mermaid.ink di-fetch oleh browser user, tidak ada CSP/iframe issue
    """
    try:
        config  = {"code": mermaid_code, "mermaid": {"theme": "dark"}}
        encoded = base64.urlsafe_b64encode(_json.dumps(config).encode()).decode()
        url     = f"https://mermaid.ink/img/{encoded}"
        # preview: fixed width supaya tidak melebar/terlalu panjang
        st.image(url, width=560)
        # expander untuk lihat ukuran penuh
        with st.expander("🔍 Lihat diagram penuh"):
            st.image(url, width="stretch")
    except Exception as e:
        st.code(mermaid_code, language="text")
        st.caption(f"⚠️ Diagram gagal dirender: {e}")


def _extract_mermaid_code(raw: str) -> Optional[str]:
    """Ekstrak kode mermaid dari berbagai format output model.
    - format 1 : ```mermaid\\n...\\n```
    - format 2 : [mermaid flowchart]\\n...\\n[/mermaid]
    - format 3 : graph TD/LR/TB/BT/RL\\n... (langsung tanpa fence)
    - output   : kode bersih atau None kalau tidak ketemu
    """
    # format 1: backtick fence
    m = re.search(r'```mermaid\s*\n(.*?)```', raw, re.DOTALL)
    if m:
        return m.group(1).strip()

    # format 2: custom tag [mermaid...] ... [/mermaid]
    m = re.search(r'\[mermaid[^\]]*\]\s*\n?(.*?)\[/mermaid\]', raw, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()

    # format 3: raw graph statement (tanpa fence)
    m = re.search(r'(graph\s+(?:TD|LR|TB|BT|RL)\b.*?)(?:\n\n|\Z)', raw, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()

    return None


def _render_sop_with_mermaid(sop_text: str) -> None:
    """Render teks SOP — split mermaid blocks dan render sebagai diagram.
    - input  : sop_text (full SOP string, bisa berisi mermaid dalam berbagai format)
    - output : teks di-render sebagai st.code, diagram di-render via mermaid.ink
    """
    # gabungkan pattern semua format mermaid yang mungkin muncul dari model
    combined_pattern = (
        r'(```mermaid.*?```'              # format 1: backtick fence
        r'|\[mermaid[^\]]*\].*?\[/mermaid\])'  # format 2: custom tag
    )
    parts = re.split(combined_pattern, sop_text, flags=re.DOTALL | re.IGNORECASE)

    for part in parts:
        diagram_code = _extract_mermaid_code(part)
        if diagram_code:
            st.caption("📊 Diagram Flowchart")
            _render_mermaid_block(diagram_code)
        elif part.strip():
            # skip baris yang cuma image link (![...](url)) - link invalid dari model
            clean = re.sub(r'!\[.*?\]\(.*?\)', '', part).strip()
            if clean:
                st.code(clean, language="markdown")




def _render_bot_bubble(msg: dict, auto_expand: bool = False) -> None:
    """Render satu bubble response SOP dari assistant."""
    data      = msg["data"]
    sop_name  = msg.get("sop_name", "SOP")
    sty       = msg.get("style", "")
    saved_id  = msg.get("saved_id")

    # normalisasi steps ke plain dict (bisa berupa Pydantic model atau dict)
    raw_steps = data.get("steps", []) or []
    steps: list[dict] = []
    for s in raw_steps:
        if isinstance(s, dict):
            steps.append(s)
        elif hasattr(s, "model_dump"):
            steps.append(s.model_dump())
        elif hasattr(s, "__dict__"):
            steps.append(vars(s))
        else:
            steps.append({"no": "?", "judul": str(s), "deskripsi": ""})

    # ambil sop text — pastikan string, tidak embed di HTML karena
    # markdown backtick (```mermaid) di dalamnya diproses ulang oleh Streamlit
    sop_raw  = data.get("sop") or ""
    sop_text = str(sop_raw)

    # debug: log tipe data saat render
    _log(
        "\U0001f5a5\ufe0f  RENDER: tipe data",
        f"  sop type  : {type(sop_raw).__name__}\n"
        f"  sop[:120] : {sop_text[:120].replace(chr(10), ' ')}\n"
        f"  steps[0]  : {str(raw_steps[0])[:80] if raw_steps else 'empty'}",
        color="\033[90m",
    )

    valid_badge = "✅ valid" if data.get("valid") else "⚠️ review"
    badges = (
        f'<span class="meta-badge">⏱ {data.get("generation_time_seconds", 0):.1f}s</span>'
        f'<span class="meta-badge">📝 {data.get("step_count", 0)} langkah</span>'
        f'<span class="meta-badge">{valid_badge}</span>'
        f'<span class="meta-badge">{sty}</span>'
    )
    if saved_id:
        badges += '<span class="meta-badge badge-save">💾 Tersimpan</span>'

    def _clean_step_desc(desc: str) -> str:
        """Strip markdown image links dan mermaid code block dari deskripsi step."""
        # hapus image link: ![...](url)
        desc = re.sub(r'!\[.*?\]\(.*?\)', '[lihat diagram di bawah]', desc)
        # hapus mermaid fence: ```mermaid...```
        desc = re.sub(r'```mermaid.*?```', '[lihat diagram di bawah]', desc, flags=re.DOTALL)
        # hapus custom mermaid tag
        desc = re.sub(r'\[mermaid[^\]]*\].*?\[/mermaid\]', '[lihat diagram di bawah]', desc, flags=re.DOTALL | re.IGNORECASE)
        return desc.strip()

    # step cards — pakai `steps` yang sudah dinormalisasi (bukan data.get(\"steps\") langsung)
    steps_html = "".join(
        f'<div class="step-card">'
        f'<span class="step-num">#{s.get("no","?")}</span> '
        f'<span class="step-title">{s.get("judul","")}</span>'
        f'<div class="step-desc">{_clean_step_desc(s.get("deskripsi",""))}'
        + (f' \u00b7 PIC: {s["pic"]}' if s.get("pic") else "")
        + (f' \u00b7 {s["durasi"]}' if s.get("durasi") else "")
        + '</div></div>'
        for s in steps
    )

    # render header + badges + step cards
    st.markdown(
        f'<div class="bot-bubble">'
        f'<b>\U0001f4cb {sop_name}</b><br>'
        f'{badges}<br>'
        + (f'<b style="color:#a5b4fc;font-size:0.87rem">Langkah-langkah:</b>'
           f'{steps_html}' if steps_html else "")
        + '</div>',
        unsafe_allow_html=True,
    )

    # render SOP full text — parse mermaid blocks dan render sebagai diagram
    # auto_expand=True untuk message terbaru, False untuk history
    if sop_text.strip():
        with st.expander("📄 Lihat teks lengkap SOP", expanded=auto_expand):
            _render_sop_with_mermaid(sop_text)


# ── main area title ────────────────────────────────────────────────────────────

st.markdown("### 💬 Generate SOP")

# ── GENERATING STATE: jalankan API call + tampilkan animasi ───────────────────
#
# Flow state machine:
#   send_btn pressed → set pending_payload + generating=True → rerun
#   Run berikutnya (generating=True): render chat + animasi → blocking API call
#                                      → save DB → add to messages → rerun
#   Run berikutnya: render chat normal (hasil sudah ada)

if st.session_state.generating and st.session_state.pending_payload:
    payload = st.session_state.pending_payload

    # tampilkan chat history (sudah include user message yang tadi di-append)
    for i, msg in enumerate(st.session_state.messages):
        if msg["role"] == "user":
            st.markdown(
                f'<div class="user-bubble">'
                f'🧑 <b>{msg.get("sop_name","SOP")}</b>'
                f'<br><br>{msg["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            is_latest = (i == len(st.session_state.messages) - 1)
            _render_bot_bubble(msg, auto_expand=is_latest)



    # ── animasi generating bubble ──────────────────────────────────────────────
    gen_area = st.empty()
    gen_area.markdown(f"""
    <div class="generating-bubble">
        <div class="gen-shimmer"></div>
        <div class="gen-header">
            <div class="dots">
                <span></span><span></span><span></span>
            </div>
            <div class="gen-title">Generating "{payload['sop_name']}"...</div>
        </div>
        <div class="gen-steps">
            <div class="gen-step done">
                <span class="icon">✅</span> Menerima catatan proses kerja
            </div>
            <div class="gen-step active">
                <span class="icon">🧠</span> Menganalisis dengan Gemma 2 + LoRA
            </div>
            <div class="gen-step">
                <span class="icon">⚡</span> Menyusun langkah-langkah SOP
            </div>
            <div class="gen-step">
                <span class="icon">💾</span> Menyimpan ke database
            </div>
        </div>
        <div class="step-bar"><div class="step-bar-fill"></div></div>
    </div>
    """, unsafe_allow_html=True)

    # ── blocking API call — CSS animation tetap jalan di browser ──────────────
    result = call_text_to_sop(payload)

    # ── setelah API selesai ────────────────────────────────────────────────────
    gen_area.empty()

    saved_id = None
    if result:
        # simpan ke MongoDB
        saved_id = save_to_history(payload, result)

        # append ke messages
        st.session_state.messages.append({
            "role":      "assistant",
            "data":      result,
            "sop_name":  payload["sop_name"],
            "style":     payload["style_label"],
            "saved_id":  saved_id,
        })

    # reset state → rerun untuk render normal
    st.session_state.generating      = False
    st.session_state.pending_payload = None
    st.rerun()

    st.stop()  # safety stop (st.rerun() raises exception tapi biar eksplisit)


if not st.session_state.messages:
    st.markdown("""
    <div class="empty-chat">
        <h2>📋</h2>
        <p>Ketik atau rekam catatan proses kerja kamu<br>
           SOP akan digenerate dan <b>otomatis tersimpan</b> ke database.</p>
    </div>
    """, unsafe_allow_html=True)
else:
    for i, msg in enumerate(st.session_state.messages):
        if msg["role"] == "user":
            st.markdown(
                f'<div class="user-bubble">'
                f'🧑 <b>{msg.get("sop_name","SOP")}</b>'
                f'<br><br>{msg["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            is_latest = (i == len(st.session_state.messages) - 1)
            _render_bot_bubble(msg, auto_expand=is_latest)

st.divider()

# ── input area ─────────────────────────────────────────────────────────────────

col_voice, col_text = st.columns([1, 5])

with col_voice:
    st.markdown("**🎤 Voice**")
    if AUDIO_OK:
        audio_bytes = audio_recorder(
            text="",
            recording_color="#ef4444",
            neutral_color="#6366f1",
            icon_name="microphone",
            icon_size="2x",
            pause_threshold=2.5,
        )
        st.markdown('<p class="voice-hint">Klik → rekam → klik lagi</p>', unsafe_allow_html=True)

        # proses audio SEBELUM textarea di-render di col_text
        if audio_bytes and len(audio_bytes) > 1000:
            audio_hash = hashlib.md5(audio_bytes).hexdigest()
            if audio_hash != st.session_state.last_audio_hash:
                st.session_state.last_audio_hash = audio_hash
                with st.spinner("🔄 Mentranskrip suara..."):
                    transcript = call_stt(audio_bytes)
                if transcript:
                    st.session_state["_catatan_key"] = transcript
                    st.toast("✅ Voice berhasil ditranskrip!", icon="🎤")
                else:
                    st.warning("Transkrip kosong — bicara lebih jelas atau ketik manual.")
    else:
        st.caption("`pip install audio-recorder-streamlit`")

with col_text:
    catatan = st.text_area(
        "Catatan proses kerja",
        placeholder=(
            "Ceritakan alur kerja secara bebas...\n"
            "Contoh: 'Setiap pagi jam 6 karyawan datang, nyalain kompor, "
            "cek tabung gas, siapkan bahan-bahan...'"
        ),
        height=120,
        key="_catatan_key",
        disabled=st.session_state.generating,
    )

col_send, col_meta = st.columns([1, 4])
with col_send:
    send_btn = st.button(
        "🚀 Generate SOP",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.generating,
    )

with col_meta:
    if catatan:
        wc = len(catatan.split())
        st.markdown(
            f'<span class="meta-badge">{wc} kata</span>'
            f'<span class="meta-badge">{style_label}</span>'
            f'<span class="meta-badge">{kategori}</span>',
            unsafe_allow_html=True,
        )
    if st.session_state.generating:
        st.markdown(
            '<span class="meta-badge" style="background:#1e2744;color:#93c5fd">'
            '⏳ Sedang generating...</span>',
            unsafe_allow_html=True,
        )

# ── send handler ───────────────────────────────────────────────────────────────

if send_btn:
    if not catatan.strip():
        st.warning("⚠️ Ketik dulu catatan proses kerjanya!")
        st.stop()

    final_name = sop_name_input.strip() or (
        "SOP " + " ".join(catatan.strip().split()[:4]).title()
    )

    # simpan user message
    st.session_state.messages.append({
        "role":     "user",
        "content":  catatan,
        "sop_name": final_name,
    })

    # simpan payload untuk di-proses di run berikutnya (generating state)
    st.session_state.pending_payload = {
        "sop_name":    final_name,
        "kategori":    kategori,
        "catatan":     catatan,
        "style_val":   style_val,
        "style_label": style_label,
        "temperature": temperature,
    }
    st.session_state.generating   = True
    st.session_state.clear_catatan = True
    st.rerun()
