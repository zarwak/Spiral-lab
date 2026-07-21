"""
llm.py
======
Everything that talks to the Groq API lives here. Keeping the "brain" calls in
one file means app.py can focus on the UI, and if you ever swap Groq for
another provider you only edit this file.

Three jobs:
  1. get_client()        -> create a Groq client from the API key
  2. stream_completion() -> the ACTUAL chat answer, streamed word-by-word,
                            while capturing latency + token usage
  3. classify_topic()    -> the "router" that powers the smart-redirect feature
  4. suggest_followups() -> generate 2 short follow-up questions

Recall the lifecycle from Phase 2: this file is step 4 (Inference). The model
is STATELESS — it only knows what we send it in `messages` every single time.
"""

import json
import time

from groq import Groq

from personalities import ROUTER_MODEL, PERSONALITIES


def get_client(api_key: str) -> Groq:
    """Create the Groq client. One object, reused for every call."""
    return Groq(api_key=api_key)


def stream_completion(client, model, messages, temperature, meta):
    """Call Groq and yield the reply in small pieces (streaming).

    `meta` is a dict we WRITE INTO as a side-channel: because a generator can
    only `yield` text, we stash the latency and token count in `meta` so the
    caller can read them after the stream finishes. Streamlit's
    st.write_stream() consumes this generator and shows text as it arrives.

    Why stream? It makes the app feel alive (text appears as it's generated)
    instead of freezing for two seconds and dumping a wall of text.
    """
    start = time.perf_counter()
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        stream=True,
    )
    for chunk in stream:
        # Normal chunks carry a piece of the reply in choices[0].delta.content.
        if chunk.choices:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
        # Groq attaches the token usage to the FINAL chunk. Depending on the SDK
        # version it lives either on `chunk.usage` or inside `chunk.x_groq.usage`,
        # so we check both and take whichever is present.
        usage = getattr(chunk, "usage", None)
        if usage is None:
            x_groq = getattr(chunk, "x_groq", None)
            usage = getattr(x_groq, "usage", None) if x_groq else None
        if usage:
            meta["prompt_tokens"] = usage.prompt_tokens
            meta["completion_tokens"] = usage.completion_tokens
            meta["total_tokens"] = usage.total_tokens

    meta["latency"] = time.perf_counter() - start


def classify_topic(client, question: str, current_key: str) -> str:
    """Decide which personality a question really belongs to (the 'router').

    This is the brain behind the smart-redirect feature. Instead of a brittle
    keyword list, we ask a small, fast model to read the MEANING of the question
    and pick the best-matching personality — or 'general' for greetings/thanks.

    Returns one of the personality keys ('math', 'doctor', ...), or 'general'.
    Any failure just returns the current key, so the chat never breaks because
    of the router — guardrails should degrade gracefully.
    """
    # Build a compact menu of options for the router to choose from.
    options = "\n".join(
        f"- {key}: {p['scope']}" for key, p in PERSONALITIES.items()
    )
    router_system = (
        "You are a strict topic router. Read the user's message and reply with "
        "ONLY a single lowercase word: the key of the category it best fits.\n"
        f"Categories:\n{options}\n"
        "- general: greetings, thanks, small talk, or anything that fits no "
        "category above.\n"
        "Reply with just the key, nothing else."
    )
    try:
        resp = client.chat.completions.create(
            model=ROUTER_MODEL,
            messages=[
                {"role": "system", "content": router_system},
                {"role": "user", "content": question},
            ],
            temperature=0,        # we want a deterministic, boring answer
            max_tokens=4,         # one word is plenty
        )
        answer = resp.choices[0].message.content.strip().lower()
        # Keep only a valid key; otherwise treat as 'general'.
        for key in PERSONALITIES:
            if key in answer:
                return key
        return "general"
    except Exception:
        # If the router call fails for any reason, don't block the chat.
        return current_key


def suggest_title(client, user_msg: str, assistant_msg: str):
    """Generate a short 'essence of the chat' title (2–4 words) for the Recent
    list, so a chat that opened with 'hi' still gets a meaningful label.
    Best-effort: returns None on any failure and the caller keeps the old title.
    """
    try:
        # Put the exchange INSIDE a user message. If the request ended on an
        # assistant message the model thinks it already replied and returns
        # nothing — a subtle but real chat-format gotcha.
        resp = client.chat.completions.create(
            model=ROUTER_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You write very short chat titles: 2 to 4 words, "
                        "sentence case, no quotes, no punctuation. Reply with "
                        "only the title."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Title this chat.\nUser: {user_msg}\n"
                        f"Assistant: {assistant_msg}"
                    ),
                },
            ],
            temperature=0.3,
            max_tokens=12,
        )
        title = resp.choices[0].message.content.strip().strip('"').strip()
        return title[:40] if title else None
    except Exception:
        return None


def suggest_followups(client, model, personality, last_answer: str):
    """Ask the model for 2 short follow-up questions the user might tap next.

    Returns a list of strings (possibly empty). Kept cheap and best-effort:
    if anything goes wrong we just return [] and the UI shows no chips.
    """
    try:
        resp = client.chat.completions.create(
            model=ROUTER_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are helping a {personality['role']} chatbot. Based "
                        "on the assistant's last answer, suggest exactly 2 very "
                        "short follow-up questions the user might ask next, "
                        "staying within the topic. Reply as a JSON array of 2 "
                        'strings, e.g. ["...", "..."]. No other text.'
                    ),
                },
                {"role": "assistant", "content": last_answer},
            ],
            temperature=0.5,
            max_tokens=60,
        )
        text = resp.choices[0].message.content.strip()
        # The model sometimes wraps JSON in ```; strip code fences if present.
        if text.startswith("```"):
            text = text.strip("`").split("\n", 1)[-1]
        data = json.loads(text)
        if isinstance(data, list):
            return [str(x) for x in data][:2]
    except Exception:
        pass
    return []
