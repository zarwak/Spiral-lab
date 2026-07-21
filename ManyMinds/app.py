"""
app.py  —  ManyMinds: a multi-personality AI agent, powered by Groq.
======================
The main Streamlit application. This file is the "agent" itself: it wires the
UI to the model, holds the memory, and enforces the guardrails.

Read this alongside the Phase 2 lifecycle diagram — the code is organised in
that same order:
    1. Perception     -> st.chat_input (the user types)
    2. Context assembly -> build_api_messages() (system prompt + memory)
    3. Routing        -> classify_topic() (on-topic? redirect?)
    4. Inference      -> stream_completion() (call Groq)
    5. Generation     -> st.write_stream() (show it live)
    6. Memory update  -> add_message() (save to session_state)
    7. Output         -> metadata, follow-up chips, insights

Run it locally with:   streamlit run app.py
"""

import os
import time
import uuid
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

import llm

# Load the .env file that sits next to this script, so GROQ_API_KEY is available
# via os.getenv() no matter which folder we launch Streamlit from. The .env is
# git-ignored, so your key never gets pushed to GitHub.
load_dotenv(Path(__file__).with_name(".env"))
from personalities import (
    PERSONALITIES,
    CUSTOM_COLORS,
    MODELS,
    LANGUAGES,
    build_system_prompt,
)

# ---------------------------------------------------------------------------
# App identity — change this line to rebrand the whole app.
# ---------------------------------------------------------------------------
APP_NAME = "ManyMinds"

# MINIMAL palette — one soft off-white canvas for every personality, a
# light-grey sidebar, and colour used only as a whisper. Change these to
# re-theme the whole app.
MIN_BG = "#FBFAF8"          # the single canvas colour (same for all personalities)
MIN_BORDER = "#E7E5E1"      # hairline borders
SIDEBAR_BG = "#F3F2EE"
SIDEBAR_TEXT = "#33322E"

# Welcome screen uses the same minimal canvas (accent only used for tiny touches).
NEUTRAL = {"bg": MIN_BG, "accent": "#C25E3A", "ink": "#232323"}

# ---------------------------------------------------------------------------
# 0. PAGE CONFIG  — must be the first Streamlit call.
# ---------------------------------------------------------------------------
st.set_page_config(page_title=APP_NAME, page_icon="💬", layout="wide")


# ---------------------------------------------------------------------------
# 1. API KEY  — read from secrets, or let the user paste one (for first runs).
# ---------------------------------------------------------------------------
def load_api_key() -> str | None:
    # 1) Local development: read from the .env file.
    key = os.getenv("GROQ_API_KEY")
    if key:
        return key
    # 2) Streamlit Cloud deployment: there's no .env there, so fall back to
    #    Streamlit's Secrets manager (you'll paste the key in the Cloud UI).
    try:
        if "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# 2. SESSION STATE  — the app's MEMORY. Streamlit reruns this whole script on
#    every interaction, so anything that must survive between reruns lives in
#    st.session_state (a dict that persists for the browser session).
# ---------------------------------------------------------------------------
def new_session(personality_key: str = "math") -> str:
    """Create a fresh chat and make it the active one. Returns its id."""
    sid = uuid.uuid4().hex[:8]
    st.session_state.sessions[sid] = {
        "title": "New chat",
        "personality": personality_key,
        "messages": [],          # each: {"role", "content", + meta for assistant}
        "created": time.time(),
        "started": False,        # False until the user picks a personality on the
                                 # welcome screen (or creates a custom one)
    }
    st.session_state.current_id = sid
    return sid


def init_state() -> None:
    ss = st.session_state
    ss.setdefault("sessions", {})
    ss.setdefault("custom_personalities", {})
    ss.setdefault("model_label", list(MODELS.keys())[0])
    ss.setdefault("language", LANGUAGES[0])
    ss.setdefault("temperature", 0.6)
    ss.setdefault("pending_redirect", None)   # {"to": key, "question": str}
    ss.setdefault("submit_text", None)        # text to process this run
    ss.setdefault("skip_route", False)        # skip the router (after a redirect)
    ss.setdefault("show_create", False)       # show the custom-creator on welcome
    if not ss.sessions:
        new_session()


init_state()


def all_personalities() -> dict:
    """Presets + any user-created custom personalities, merged."""
    merged = dict(PERSONALITIES)
    merged.update(st.session_state.custom_personalities)
    return merged


def current() -> dict:
    """The active session object."""
    return st.session_state.sessions[st.session_state.current_id]


def current_personality() -> dict:
    key = current()["personality"]
    return all_personalities().get(key, PERSONALITIES["math"])


def add_message(role: str, content: str, **meta) -> None:
    """Append a message to the active session (step 6: Memory update)."""
    sess = current()
    sess["messages"].append({"role": role, "content": content, **meta})
    # Auto-title the chat from the first user message.
    if role == "user" and sess["title"] == "New chat":
        sess["title"] = (content[:28] + "…") if len(content) > 28 else content


def build_api_messages() -> list:
    """Assemble exactly what we send to Groq (step 2: Context assembly).

    = system prompt (personality + language)  +  the whole conversation so far.
    This is how a STATELESS model appears to 'remember': we resend history
    every turn.
    """
    p = current_personality()
    system = build_system_prompt(p, st.session_state.language)
    msgs = [{"role": "system", "content": system}]
    for m in current()["messages"]:
        msgs.append({"role": m["role"], "content": m["content"]})
    return msgs


# ---------------------------------------------------------------------------
# 3. LOOK & FEEL  — a MINIMAL, near-monochrome look. One soft off-white canvas
#    for every personality; colour appears only as a faint accent on the user's
#    own message bubbles (and the terracotta accent on primary controls).
# ---------------------------------------------------------------------------
def inject_css(p: dict) -> None:
    st.markdown(
        f"""
        <style>
          .stApp {{ background-color: {MIN_BG}; }}
          section[data-testid="stSidebar"] {{ background-color: {SIDEBAR_BG}; }}
          /* pull the sidebar content up to remove the blank space at the top */
          section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{
              padding-top: 1rem;
          }}
          section[data-testid="stSidebar"] h1,
          section[data-testid="stSidebar"] h2,
          section[data-testid="stSidebar"] h3,
          section[data-testid="stSidebar"] label,
          section[data-testid="stSidebar"] p,
          section[data-testid="stSidebar"] .stMarkdown {{ color: {SIDEBAR_TEXT} !important; }}
          section[data-testid="stSidebar"] [data-testid="stExpander"] details {{
              background-color: #FFFFFF;
              border: 1px solid {MIN_BORDER};
              border-radius: 10px;
          }}
          /* a whisper of the personality accent — only on the user's own bubbles */
          [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {{
              background-color: {p['accent']}12;  /* accent at ~7% opacity */
          }}
          /* one flat canvas — top bar and bottom input area match the page */
          header[data-testid="stHeader"] {{ background: transparent; }}
          [data-testid="stBottom"],
          [data-testid="stBottom"] > div,
          [data-testid="stBottomBlockContainer"] {{
              background-color: {MIN_BG} !important;
          }}
          /* the input box: clean white with a neutral hairline border */
          [data-testid="stChatInput"] {{
              background-color: #FFFFFF;
              border: 1px solid {MIN_BORDER};
          }}
          /* slightly smaller text in the personality / model / language row */
          [data-baseweb="select"] {{ font-size: 13px; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ===========================================================================
#  CUSTOM PERSONALITY  — shared by the sidebar AND the welcome screen
# ===========================================================================
def make_custom_personality(name: str, scope: str, style: str) -> None:
    """Create a user-defined personality (a user-authored system prompt) and
    switch to it. This is feature #15 — and a neat demo of 'a personality is
    just a system prompt'."""
    key = f"custom:{name}"
    st.session_state.custom_personalities[key] = {
        "role": name,
        "name": name,
        "icon": "✨",
        "scope": scope,
        "greeting": f"Hi! I'm **{name}**. I only talk about {scope}. What would you like to know?",
        "starters": [f"Tell me about {scope}", "How do I get started?", "Give me a quick tip"],
        "system": (
            f"You are {name}. {style}\n"
            f"STRICT RULE: You ONLY answer questions about {scope}. "
            "If asked about anything else, politely decline in one short "
            "sentence and remind them of your topic."
        ),
        **CUSTOM_COLORS,
    }
    current()["personality"] = key
    current()["started"] = True


def delete_custom_personality(key: str) -> None:
    """Remove a user-created personality. Any chat currently using it falls back
    to the Math Teacher so nothing breaks."""
    st.session_state.custom_personalities.pop(key, None)
    for sess in st.session_state.sessions.values():
        if sess["personality"] == key:
            sess["personality"] = "math"


def render_custom_form(form_key: str) -> None:
    """The name / topic / style form. `form_key` must be unique per location."""
    with st.form(form_key, clear_on_submit=True):
        cname = st.text_input("Name", placeholder="Coach Max")
        cscope = st.text_input("Only talks about…", placeholder="fitness and workouts")
        crules = st.text_area("Personality / style", placeholder="Energetic, motivating, uses simple language.")
        if st.form_submit_button("Create & start"):
            if cname and cscope:
                make_custom_personality(cname, cscope, crules)
                st.session_state.show_create = False
                st.rerun()
            else:
                st.warning("Give it at least a name and a topic.")


# ===========================================================================
#  SIDEBAR  — New chat, history, creativity, custom personality, downloads
# ===========================================================================
def render_sidebar() -> None:
    ss = st.session_state
    with st.sidebar:
        st.markdown(f"## {APP_NAME}")

        if st.button("➕  New chat", use_container_width=True):
            new_session(current()["personality"])
            ss.pending_redirect = None
            st.rerun()

        st.markdown("#### Recent")
        # Newest first. Each chat is a button that reopens it.
        for sid, sess in sorted(
            ss.sessions.items(), key=lambda kv: kv[1]["created"], reverse=True
        ):
            label = ("• " if sid == ss.current_id else "  ") + sess["title"]
            if st.button(label, key=f"open_{sid}", use_container_width=True):
                ss.current_id = sid
                ss.pending_redirect = None
                st.rerun()

        st.divider()

        # --- Temperature (a.k.a. creativity) ---
        ss.temperature = st.slider(
            "Temperature", 0.0, 1.0, ss.temperature, 0.1,
            help="Low = focused and factual. High = more creative and varied.",
        )

        # --- Custom personality creator + manager (feature #15) ---
        with st.expander("✨ Create a personality"):
            # List existing custom personalities, each with a delete button.
            if ss.custom_personalities:
                st.caption("Your personalities")
                for ckey in list(ss.custom_personalities.keys()):
                    cp = ss.custom_personalities[ckey]
                    row, delcol = st.columns([4, 1])
                    row.write(f"{cp['icon']} {cp['name']}")
                    if delcol.button("🗑", key=f"del_{ckey}", help=f"Delete {cp['name']}"):
                        delete_custom_personality(ckey)
                        st.rerun()
                st.divider()
            render_custom_form("custom_form_sidebar")

        st.divider()

        # --- Download transcript (feature #16) ---
        transcript = "\n\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in current()["messages"]
        )
        st.download_button(
            "⬇️  Download this chat",
            data=transcript or "No messages yet.",
            file_name=f"manyminds_{ss.current_id}.txt",
            use_container_width=True,
        )

        # --- Token usage footer (feature #17) ---
        # `or 0` guards against messages whose token count is None (some Groq
        # SDK versions don't report usage for a streamed reply).
        used = sum((m.get("total_tokens") or 0) for m in current()["messages"])
        st.caption(f"Tokens used this chat: **{used:,}**")

        # --- Your snapshot (personal insights) ---
        render_snapshot()


def render_snapshot() -> None:
    """A small 'favourite personality / model / avg speed' summary."""
    ss = st.session_state
    with st.expander("📊 Your snapshot"):
        counts, latencies, msg_count = {}, [], 0
        for sess in ss.sessions.values():
            for m in sess["messages"]:
                if m["role"] == "user":
                    msg_count += 1
                if m["role"] == "assistant":
                    counts[sess["personality"]] = counts.get(sess["personality"], 0) + 1
                    if m.get("latency"):
                        latencies.append(m["latency"])
        fav_key = max(counts, key=counts.get) if counts else current()["personality"]
        fav = all_personalities().get(fav_key, current_personality())
        avg = f"{sum(latencies) / len(latencies):.1f}s" if latencies else "—"
        st.markdown(
            f"- Favourite personality: **{fav['role']}**\n"
            f"- Current model: **{ss.model_label}**\n"
            f"- Language: **{ss.language}**\n"
            f"- Messages you've sent: **{msg_count}**\n"
            f"- Average reply speed: **{avg}**"
        )


# ===========================================================================
#  MAIN AREA  — welcome picker, right control panel, header, chat
# ===========================================================================
def is_started() -> bool:
    """A chat is 'started' once the user has picked a personality (or it already
    has messages). Until then we show the welcome picker."""
    return current().get("started", False) or bool(current()["messages"])


CARD_HEIGHT = 250  # fixed card height so every welcome card lines up on a grid


def render_welcome() -> None:
    """The landing screen for a new/empty chat: pick which mind to talk to."""
    st.markdown(f"# Welcome to {APP_NAME}")
    st.markdown("#### Choose a mind to talk to")
    st.caption(
        "Each personality answers only within its own area of expertise. "
        "You can switch anytime — or build your own."
    )
    st.write("")

    # Fixed-height cards + equal column gaps = a clean, aligned 3×2 grid.
    keys = list(PERSONALITIES.keys())
    cols = st.columns(3, gap="medium")

    for i, key in enumerate(keys):
        pp = PERSONALITIES[key]
        scope_short = pp["scope"].split("—")[-1].strip()
        with cols[i % 3]:
            with st.container(border=True, height=CARD_HEIGHT):
                st.markdown(f"### {pp['icon']} {pp['name']}")
                st.caption(pp["role"])
                st.write(scope_short[:70] + ("…" if len(scope_short) > 70 else ""))
                if st.button("Choose", key=f"choose_{key}", use_container_width=True):
                    current()["personality"] = key
                    current()["started"] = True
                    st.rerun()

    # 6th card — create your own custom personality (fills the grid to 3×2).
    with cols[len(keys) % 3]:
        with st.container(border=True, height=CARD_HEIGHT):
            st.markdown("### ✨ Your own")
            st.caption("Custom")
            st.write("Invent a personality — a name, a topic it sticks to, and a style.")
            if st.button("Create →", key="choose_custom", use_container_width=True):
                st.session_state.show_create = True
                st.rerun()

    # The inline creator form (opens under the grid when the 6th card is clicked).
    if st.session_state.show_create:
        st.write("")
        st.markdown("##### ✨ Create your personality")
        render_custom_form("custom_form_welcome")


def render_control_row() -> None:
    """A compact selector row beneath the chat, aligned to the RIGHT — like a
    chat composer's bottom bar (personality · model · language). Each dropdown
    shows its current value, so no separate labels are needed (kept collapsed).

    Note: Streamlit pins st.chat_input to the very bottom of the page, so this
    row sits directly ABOVE the input — the closest layout to 'beneath the chat,
    on the right' that native Streamlit allows.
    """
    ss = st.session_state
    people = all_personalities()
    keys = list(people.keys())
    labels = [f"{people[k]['icon']} {people[k]['name']}" for k in keys]

    # Big left spacer pushes the three dropdowns over to the right.
    _, c_p, c_m, c_l = st.columns([4, 2.2, 2.6, 1.8])

    with c_p:
        idx = keys.index(current()["personality"]) if current()["personality"] in keys else 0
        chosen = st.selectbox(
            "Personality", labels, index=idx,
            key="persona_select", label_visibility="collapsed",
        )
        new_key = keys[labels.index(chosen)]
        if new_key != current()["personality"]:
            current()["personality"] = new_key
            st.rerun()  # rerun so the tint + header update immediately

    with c_m:
        ss.model_label = st.selectbox(
            "Model", list(MODELS.keys()),
            index=list(MODELS.keys()).index(ss.model_label),
            label_visibility="collapsed",
        )

    with c_l:
        ss.language = st.selectbox(
            "Language", LANGUAGES, index=LANGUAGES.index(ss.language),
            label_visibility="collapsed",
        )


def render_history(p: dict) -> None:
    """Draw the conversation. If empty, show the greeting + starter chips."""
    msgs = current()["messages"]

    if not msgs:
        with st.chat_message("assistant", avatar=p["icon"]):
            st.markdown(p["greeting"])
        st.caption("Try one of these:")
        cols = st.columns(len(p["starters"]))
        for col, q in zip(cols, p["starters"]):
            if col.button(q, key=f"starter_{q}", use_container_width=True):
                queue_submit(q)
        return

    for m in msgs:
        if m["role"] == "user":
            with st.chat_message("user", avatar="🧑"):
                st.markdown(m["content"])
        else:
            with st.chat_message("assistant", avatar=p["icon"]):
                st.markdown(m["content"])
                bits = []
                if m.get("latency"):
                    bits.append(f"{m['latency']:.1f}s")
                if m.get("total_tokens"):
                    bits.append(f"{m['total_tokens']} tokens")
                if bits:
                    st.caption(" · ".join(bits))

    # Follow-up chips under the last assistant message (feature: follow-ups).
    last = msgs[-1]
    if last["role"] == "assistant" and last.get("followups"):
        cols = st.columns(len(last["followups"]))
        for col, q in zip(cols, last["followups"]):
            if col.button(q, key=f"follow_{len(msgs)}_{q}", use_container_width=True):
                queue_submit(q)


def render_redirect_banner() -> None:
    """The smart-redirect: offer to switch to the right personality and re-ask."""
    pr = st.session_state.pending_redirect
    if not pr:
        return
    target = all_personalities()[pr["to"]]
    st.info(f"🔎 That looks like a **{target['role']}** question — the current "
            f"personality stays on its own topic.")
    if st.button(f"Continue with {target['icon']} {target['name']} →", type="primary"):
        current()["personality"] = pr["to"]
        st.session_state.skip_route = True          # we already know it fits
        queue_submit(pr["question"], clear_redirect=True)


def queue_submit(text: str, clear_redirect: bool = False) -> None:
    """Stash a message to be processed, then rerun so the flow is clean."""
    st.session_state.submit_text = text
    if clear_redirect:
        st.session_state.pending_redirect = None
    st.rerun()


# ===========================================================================
#  PROCESSING  — the heart: route, then either redirect or answer
# ===========================================================================
def process(client, text: str) -> None:
    ss = st.session_state
    p = current_personality()
    add_message("user", text)

    # --- Step 3: Routing (skip for custom bots or right after a redirect) ---
    is_custom = current()["personality"].startswith("custom:")
    route = None
    if not ss.skip_route and not is_custom:
        with st.spinner("Thinking…"):
            route = llm.classify_topic(client, text, current()["personality"])
    ss.skip_route = False

    if route and route in PERSONALITIES and route != current()["personality"] and route != "general":
        # Off-topic -> refuse in-character and offer the redirect button.
        refusal = (
            f"That's a bit outside my area — I'm **{p['name']}**, your "
            f"{p['role'].lower()}, so I stick to {p['scope'].split('—')[0].strip()}. "
        )
        add_message("assistant", refusal)
        ss.pending_redirect = {"to": route, "question": text}
        st.rerun()
        return

    # --- Steps 4+5: Inference + Generation (streamed live) ---
    meta = {}
    with st.chat_message("assistant", avatar=p["icon"]):
        model_id = MODELS[ss.model_label]
        try:
            full = st.write_stream(
                llm.stream_completion(
                    client, model_id, build_api_messages(), ss.temperature, meta
                )
            )
        except Exception as e:
            full = f"⚠️ Sorry, something went wrong talking to Groq: `{e}`"
            st.markdown(full)

    # --- Step 6: Memory update (save with metadata) ---
    followups = llm.suggest_followups(client, model_id, p, full) if meta else []
    add_message(
        "assistant", full,
        latency=meta.get("latency"),
        total_tokens=meta.get("total_tokens"),
        model=ss.model_label,
        followups=followups,
    )

    # Give the chat a meaningful "essence" title on the first real answer
    # (so the Recent list shows the topic, not the user's opening "hi").
    if meta and not current().get("titled"):
        title = llm.suggest_title(client, text, full)
        if title:
            current()["title"] = title
            current()["titled"] = True

    ss.pending_redirect = None
    st.rerun()


# ===========================================================================
#  MAIN
# ===========================================================================
def main() -> None:
    ss = st.session_state
    api_key = load_api_key()

    render_sidebar()

    if not api_key:
        inject_css(NEUTRAL)
        st.warning("No Groq API key found. Add `GROQ_API_KEY=your_key` to the "
                   "`.env` file next to app.py, then rerun. "
                   "Get a free key at console.groq.com/keys.")
        st.stop()

    client = llm.get_client(api_key)

    # NEW USER / NEW CHAT → the welcome picker. Neutral tint, no chat input yet.
    if not is_started():
        inject_css(NEUTRAL)
        render_welcome()
        st.stop()

    # STARTED → tint to the chosen personality, then lay out the chat.
    p = current_personality()
    inject_css(p)

    # The whole conversation lives in one container.
    chat_box = st.container()
    with chat_box:
        st.markdown(f"#### {p['icon']} {p['name']}")
        st.caption(f"_{p['scope'].split('—')[0].strip().capitalize()}_")
        render_history(p)
        render_redirect_banner()

    # Step 1: Perception — the input box. Enter submits; Shift+Enter = new line.
    typed = st.chat_input(f"Message {p['name']}…")
    if typed:
        ss.submit_text = typed

    # Process a new turn BEFORE drawing the selector row, so the new user +
    # assistant bubbles stream in first and the row stays directly beneath them.
    if ss.submit_text:
        text = ss.submit_text
        ss.submit_text = None
        with chat_box:
            process(client, text)  # streams, then st.rerun()

    # The selector row is the LAST thing inside the chat flow — it sits directly
    # beneath the chat bubbles (personality · model · language), aligned right.
    with chat_box:
        render_control_row()


if __name__ == "__main__":
    main()
