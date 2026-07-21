# 🧠 ManyMinds — a multi-personality AI agent

> A Streamlit + Groq chatbot where one app hosts many "minds." Pick a personality
> (Math Teacher, Doctor, Chef, Travel Guide, Tech Support, or your own custom one),
> pick a model, and chat. Each personality answers **only** within its area of
> expertise — and when you wander off-topic, it politely hands you to the right mind.

This README is two things at once:

1. **A normal project README** — what it is, how to run it, how it's built.
2. **An AI-agent study guide** — the theory behind every feature, written to double
   as interview preparation. Sections marked **🎓 Interview** call out the concepts
   and questions you're most likely to be asked.

---

## Table of contents

1. [What this project is](#1-what-this-project-is)
2. [Quick start](#2-quick-start)
3. [Project structure](#3-project-structure)
4. [The big idea: what *is* an AI agent?](#4-the-big-idea-what-is-an-ai-agent)
5. [The agent lifecycle (the 7 steps)](#5-the-agent-lifecycle-the-7-steps)
6. [Deep dives (with interview Q&A)](#6-deep-dives)
   - [6.1 System prompts & personality enforcement](#61-system-prompts--personality-enforcement)
   - [6.2 Memory & the stateless model](#62-memory--the-stateless-model)
   - [6.3 The router — guardrails & the smart redirect](#63-the-router--guardrails--the-smart-redirect)
   - [6.4 Model parameters: temperature, tokens, latency](#64-model-parameters-temperature-tokens-latency)
   - [6.5 Streaming](#65-streaming)
7. [Agentic patterns this project demonstrates](#7-agentic-patterns-this-project-demonstrates)
8. [Limitations & how you'd improve it](#8-limitations--how-youd-improve-it)
9. [Deployment (Streamlit Cloud)](#9-deployment-streamlit-cloud)
10. [Interview question bank](#10-interview-question-bank)
11. [Glossary](#11-glossary)

---

## 1. What this project is

ManyMinds is a chat web app. The novel parts:

- **Personality presets** — 5 characters, each locked to one topic.
- **Personality enforcement** — the bot refuses off-topic questions instead of answering them.
- **Smart redirect** — if you ask Chef Sol a math question, it detects the mismatch,
  refuses in-character, and offers a one-click button to switch to Professor Ada
  and re-ask automatically.
- **Custom personalities** — invent your own mind from a name + a topic + a style.
- **Session memory & multi-chat** — each conversation remembers its own history.
- **Model & language selection**, **temperature control**, **streaming replies**,
  **latency + token counters**, **downloadable transcripts**, and a **personal snapshot**.

**Tech stack:** Python · Streamlit (UI) · Groq Cloud API (LLM inference) ·
python-dotenv (secrets) · deployed free on Streamlit Cloud.

---

## 2. Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Add your free Groq API key to a .env file next to app.py
#    (get one at https://console.groq.com/keys)
echo GROQ_API_KEY=gsk_your_real_key_here > .env

# 3. Run it
streamlit run app.py
```

The app opens in your browser. `.env` is git-ignored, so your key never leaves your machine.

> **Why `.env`?** Hard-coding an API key in source is the #1 way keys leak on GitHub.
> Keeping it in a git-ignored `.env` and reading it with `os.getenv()` is the standard
> "secrets stay out of code" pattern. On Streamlit Cloud (which has no `.env`), the app
> falls back to Streamlit's **Secrets** manager — see [§9](#9-deployment-streamlit-cloud).

---

## 3. Project structure

```
ai agent/
├── app.py               # The agent: UI, memory, orchestration, guardrails
├── personalities.py     # DATA only: each personality's system prompt + presentation
├── llm.py               # All Groq calls: streaming answer, router, follow-ups
├── requirements.txt     # streamlit, groq, python-dotenv
├── .env                 # YOUR api key (git-ignored — never committed)
├── .gitignore
├── .streamlit/
│   ├── config.toml            # theme (colours, fonts)
│   └── secrets.toml.example   # template for cloud deployment
└── README.md            # this file
```

**🎓 Interview — why split into three files?**
Separation of concerns. `personalities.py` is pure **data** (change a personality =
edit one dictionary, no logic touched). `llm.py` is the **model boundary** (swap Groq
for another provider = edit one file). `app.py` is **orchestration**. Interviewers like
hearing that you can point to *where* a change lives without reading the whole codebase.

---

## 4. The big idea: what *is* an AI agent?

The most common misconception: *"the LLM is the agent."* It isn't.

- The **LLM** (the model running on Groq) is a **brain in a jar**. It takes text in
  and predicts text out. It has no memory, no rules, no access to tools, no idea who
  the user is. It is **stateless** — it forgets everything the instant it replies.
- An **agent** is the **entire system you build around that brain**: the memory, the
  instructions (system prompt), the input/output handling, the decision logic
  (routing/guardrails), and — in fuller agents — the tools it can call.

> **ManyMinds (your `app.py`) is the agent. Groq's model is one organ inside it.**

**🎓 Interview soundbite:** *"A language model predicts text; an agent decides what to
do with that ability. The intelligence people attribute to 'the AI' is mostly
engineering around the model: what context you feed it, what rules constrain it, and
what you do with its output."*

A useful spectrum to know:

| Level | What it is | ManyMinds example |
|---|---|---|
| **LLM call** | One prompt → one response | A single Groq `chat.completions.create` |
| **Chatbot** | LLM + conversation memory | Session history re-sent each turn |
| **Agent (this project)** | Chatbot + rules + routing/decisions | Personality enforcement + smart redirect |
| **Tool-using agent** | Agent that can call functions/APIs/search | *(not here — see [§8](#8-limitations--how-youd-improve-it))* |
| **Multi-agent system** | Multiple agents cooperating | *(the router hints at this idea)* |

---

## 5. The agent lifecycle (the 7 steps)

Every message travels the same path. This diagram is the backbone of the whole app —
the code in `app.py` is literally organised in this order.

```
   ┌─────────────────────────────────────────────────────────────┐
   │                 ONE MESSAGE'S JOURNEY                        │
   └─────────────────────────────────────────────────────────────┘

  1. PERCEPTION          User types and hits Enter.
        │                   → st.chat_input()
        ▼
  2. CONTEXT ASSEMBLY    Build the packet sent to the brain:
        │                   • system prompt (personality + language)
        │                   • memory (all past messages this chat)
        │                   • the new user message
        │                   → build_api_messages()
        ▼
  3. ROUTING / DECISION  Decide BEFORE calling the brain:
        │                   • Is this on-topic for the personality?
        │                   • If not → trigger the smart redirect
        │                   → llm.classify_topic()
        ▼
  4. INFERENCE           Send to Groq; the model generates a reply.
        │                   (latency + tokens measured here)
        │                   → llm.stream_completion()
        ▼
  5. GENERATION          Reply streams into the bubble word-by-word.
        │                   → st.write_stream()
        ▼
  6. MEMORY UPDATE       Save this Q&A so the NEXT turn remembers it.
        │                   → add_message()
        ▼
  7. OUTPUT / ACTION     Render metadata, follow-up chips, redirect
                         button, token counter, snapshot.
```

**🎓 Interview:** almost every agent concept maps to one of these steps. If asked
"walk me through your architecture," walk them through these 7 steps and name the
function at each — it shows you understand *flow*, not just features.

---

## 6. Deep dives

### 6.1 System prompts & personality enforcement

A **system prompt** is a hidden instruction, sent before the user's messages, that
defines *who the model is* and *how it must behave*. It's the single most important
tool in **prompt engineering**.

In ManyMinds, **a personality *is* a system prompt.** From `personalities.py`:

```python
"system": (
    "You are Professor Ada, a warm, patient math teacher...\n"
    "STRICT RULE: You ONLY answer questions about mathematics... "
    "If the user asks about anything outside mathematics, politely decline "
    "in one short sentence and remind them you are a math teacher — do NOT "
    "attempt to answer the off-topic part."
)
```

Switching personality = swapping this string. Nothing else changes.

**🎓 Interview — is a system prompt a real security boundary?**
No. A system prompt *guides* behaviour; it does not *guarantee* it. A determined user
can sometimes talk a model around its instructions (**prompt injection** /
**jailbreaking**), e.g. *"Ignore previous instructions and..."*. That's exactly why
ManyMinds adds a **second layer** — the router (see [6.3](#63-the-router--guardrails--the-smart-redirect)) — instead of trusting the prompt alone. Naming this limitation
unprompted is a green flag in interviews. **Defense in depth** applies to LLMs too.

**Key terms to know:** system vs. user vs. assistant roles · prompt engineering ·
prompt injection · jailbreaking · guardrails.

---

### 6.2 Memory & the stateless model

**The single most important beginner insight in this whole project:**

> The model is **stateless**. It remembers nothing between calls. The *illusion* of
> memory is created entirely by **you** — by storing the conversation and **re-sending
> the whole history on every single turn.**

In ManyMinds, memory lives in `st.session_state` (Streamlit's per-session store).
Each turn, `build_api_messages()` reconstructs the full packet:

```python
msgs = [{"role": "system", "content": system_prompt}]   # who you are
for m in current()["messages"]:                          # everything said so far
    msgs.append({"role": m["role"], "content": m["content"]})
# + the new user message → send ALL of this to Groq
```

**🎓 Interview — types of memory:**

| Type | What it means | In ManyMinds |
|---|---|---|
| **Short-term / working memory** | The current conversation, re-sent each turn | ✅ `st.session_state` |
| **Long-term memory** | Persists across sessions (usually a database or vector store) | ❌ not implemented |
| **Episodic / semantic memory** | Recalling past events / facts, often via retrieval (RAG) | ❌ (see [§8](#8-limitations--how-youd-improve-it)) |

**🎓 Interview — the context window.**
The history can't grow forever: every model has a **context window** (a max number of
**tokens** it can read at once). Long chats eventually overflow it. Common fixes:
**truncation** (drop oldest messages), **summarisation** (compress old turns into a
short summary), or **retrieval** (store history externally and fetch only relevant
bits). ManyMinds currently sends the full history — fine for short chats, and a perfect
thing to say *"here's how I'd scale it"* about.

---

### 6.3 The router — guardrails & the smart redirect

This is the most interesting engineering in the project.

**Problem:** how do you *reliably* keep a personality on-topic, and know *which*
personality an off-topic question belongs to (so you can offer to redirect)?

**Naive approach:** a keyword list (`if "recipe" in question → chef`). Brittle —
*"what's the calorie count of pi?"* breaks it, and it can't understand meaning.

**ManyMinds' approach (in `llm.py`):** ask a **small, fast model to classify the
question's topic** — a technique called an **LLM router**.

```python
def classify_topic(client, question, current_key):
    # A cheap model reads the MEANING and returns one key: 'chef', 'math', ...
    resp = client.chat.completions.create(
        model=ROUTER_MODEL,               # llama-3.1-8b-instant (fast + cheap)
        messages=[{"role": "system", "content": router_system}, ...],
        temperature=0,                    # deterministic, boring, repeatable
        max_tokens=4,                     # one word is all we need
    )
    ...
```

If the router says the question belongs to a *different* personality, the app:
1. refuses in-character ("*I'm Chef Sol, I stick to cooking...*"),
2. shows a **"Continue with Professor Ada →"** button,
3. on click, switches personality and **re-asks the question automatically**.

**🎓 Interview — three things this demonstrates:**

- **Guardrails / control flow around the model.** Real agents don't blindly trust the
  LLM's output; they wrap it in logic. Here, a *decision* happens **before** the answer.
- **The cheap-model-for-routing pattern.** Use a small fast model for the classification
  decision, and the strong model only for the actual answer. This is a real
  **cost & latency optimization** used in production LLM systems (sometimes called
  **model cascading** or an **LLM router**).
- **Graceful degradation.** If the router call fails, `classify_topic` returns the
  current personality so the chat never breaks. *Guardrails must fail open, not crash.*

Also note: `temperature=0` for the router. **Decisions want determinism; creativity
wants randomness.** Using temperature 0 for classification and a higher temperature for
chat is a deliberate, defensible choice.

---

### 6.4 Model parameters: temperature, tokens, latency

Three knobs every LLM engineer must be able to explain:

- **Temperature (0–1+)** — controls randomness. **Low (0–0.3)** = focused,
  deterministic, repeatable (good for classification, extraction, math).
  **High (0.7–1)** = varied, creative (good for brainstorming, storytelling).
  ManyMinds exposes this as the sidebar **"Temperature"** slider, and hard-codes `0`
  for the router. *(Related knobs you may be asked about: `top_p` / nucleus sampling,
  `max_tokens`, `frequency_penalty`.)*

- **Tokens** — the unit models read and bill in. A token ≈ ¾ of a word. You pay per
  token (input + output), and the **context window** is measured in tokens. ManyMinds
  reads Groq's usage report and shows **tokens per reply** and a running total.

- **Latency** — how long the model takes to respond. ManyMinds times each call
  (`time.perf_counter()`) and shows e.g. `1.9s`. Groq is notable for being *fast*
  because it runs models on specialised **LPU** hardware — a good "why Groq?" answer.

**🎓 Interview:** *"How would you make an LLM answer more consistent?"* → lower the
temperature (toward 0), and constrain the output format. *"Cheaper?"* → smaller model,
fewer tokens (shorter prompts/history), caching.

---

### 6.5 Streaming

Instead of waiting for the whole answer and dumping it, ManyMinds **streams** tokens as
they're generated (`stream=True` → `st.write_stream()`), so text appears live like
ChatGPT.

**🎓 Interview — why stream?** Perceived latency. The *total* time is the same, but the
user sees the first words in ~200ms instead of staring at a spinner for 2 seconds.
It's a UX win, not a speed win. Implementation detail worth mentioning: a streamed
response arrives as **chunks**; you concatenate `chunk.choices[0].delta.content`, and
the **token usage arrives in the final chunk** (in Groq's SDK, under `chunk.x_groq.usage`
— a real cross-version gotcha this project handles).

---

## 7. Agentic patterns this project demonstrates

Name-drop these; they map directly to ManyMinds features:

| Pattern | What it is | Where in ManyMinds |
|---|---|---|
| **System-prompt conditioning** | Steering behaviour via a hidden instruction | Every personality |
| **Guardrails** | Logic that constrains the model's scope | Enforcement + refusal |
| **LLM router / model cascading** | Cheap model routes; strong model answers | `classify_topic()` |
| **Human-in-the-loop** | User confirms an action (the redirect button) | Smart redirect |
| **Graceful degradation** | Fail safe when a sub-call errors | Router & follow-ups return safe defaults |
| **Separation of data & logic** | Config-as-data | `personalities.py` |

**Patterns ManyMinds does *not* use (know them anyway):**

- **ReAct (Reason + Act)** — the model interleaves reasoning with **tool calls**
  (search, calculator, API) in a loop. ManyMinds has no tools, so no ReAct loop.
- **RAG (Retrieval-Augmented Generation)** — fetch relevant documents from a vector
  database and inject them into the prompt so the model can answer from *your* data.
- **Function / tool calling** — the model outputs a structured request to run a
  function, you run it, and feed the result back.
- **Reflection / self-critique** — the model reviews and revises its own output.

**🎓 Interview — "how would you turn this into a *tool-using* agent?"**
Give the Math Teacher a real calculator tool and the Travel Guide a live flights/weather
API via **function calling**; loop with **ReAct** so it can call a tool, read the result,
and continue. That single sentence shows you understand the leap from *chatbot* to
*agent-with-tools*.

---

## 8. Limitations & how you'd improve it

Being able to critique your own project is an interview superpower. Known limitations:

| Limitation | Why | How you'd fix it |
|---|---|---|
| **Memory is not persistent** | Sessions live in RAM; a server restart wipes them | Store chats in a database (SQLite/Postgres) keyed by user |
| **Enforcement isn't bulletproof** | System prompts can be jailbroken | The router adds a 2nd layer; could add an output-moderation check too |
| **No long-term / retrieval memory** | The model only sees the current chat | Add RAG over past chats or a knowledge base |
| **Context window will overflow on long chats** | We resend full history | Summarise or truncate old turns |
| **The router costs an extra API call per message** | Classification before answering | Cache classifications; or skip routing for obvious on-topic follow-ups |
| **No automated evaluation** | We eyeball quality | Add an **eval** suite: a set of off-topic prompts asserting the bot refuses/redirects |
| **No streaming for the router** | It's a tiny call, so fine | N/A — deliberate |

**🎓 Interview — evaluation.** Teams increasingly ask *"how do you know your prompt
works?"* The answer is **evals**: a fixed set of test inputs with expected behaviours,
run automatically whenever you change a prompt. For ManyMinds you'd assert e.g.
*"Chef Sol, asked a math question, must refuse and offer to redirect to math."*

---

## 9. Deployment (Streamlit Cloud)

1. Push the repo to GitHub (the `.env` is git-ignored, so your key stays private).
2. Go to [share.streamlit.io](https://share.streamlit.io), connect the repo, pick `app.py`.
3. In the app's **Settings → Secrets**, add:
   ```toml
   GROQ_API_KEY = "gsk_your_real_key_here"
   ```
   The app reads `.env` locally and Streamlit **Secrets** in the cloud — `load_api_key()`
   tries both, so the same code works in both places.
4. Deploy. You get a public URL to share.

**🎓 Interview — secrets management.** Local dev uses `.env`; production uses the
platform's secret store (Streamlit Secrets, or env vars on Heroku/Render, or a vault).
The principle is identical everywhere: **secrets never live in source control.**

---

## 10. Interview question bank

Rapid-fire answers grounded in this project.

**Q: What's the difference between an LLM and an agent?**
An LLM predicts text. An agent is the system around it — memory, instructions, decision
logic, and (in fuller agents) tools. ManyMinds is the agent; Groq's model is one part.

**Q: How does the chatbot "remember" earlier messages if the model is stateless?**
It doesn't — *the app* remembers. We store the conversation in `st.session_state` and
re-send the entire history to the model on every turn. The model is stateless; the
illusion of memory is engineering.

**Q: How do you make a bot only answer about one topic?**
Two layers: (1) a **system prompt** instructing it to refuse off-topic questions, and
(2) a **router** — a cheap model that classifies each question's topic — because the
prompt alone can be jailbroken. Defense in depth.

**Q: Why use a *small* model for the router and a *big* one for the answer?**
Cost and latency. Classification is easy and frequent, so a fast cheap model is enough;
the expensive model is reserved for the actual answer. This is the LLM-router / model-
cascading pattern.

**Q: What does temperature do, and why is the router's set to 0?**
Temperature controls randomness. Classification wants a deterministic, repeatable
answer, so temperature 0. Chat wants some variety, so it's user-adjustable.

**Q: What is a token and why does it matter?**
The unit models read and bill in (~¾ of a word). It drives cost and defines the context
window's size limit.

**Q: What happens when the conversation gets too long?**
It can exceed the context window. You handle it by truncating or summarising old
messages, or moving to retrieval.

**Q: What's prompt injection?**
When user input manipulates the model into ignoring its instructions
(*"ignore previous instructions..."*). It's why a system prompt isn't a security boundary
and why ManyMinds adds a second guardrail layer.

**Q: How would you make this a tool-using agent?**
Add function/tool calling (e.g. a calculator for the Math Teacher, a live API for the
Travel Guide) and a ReAct loop so the model can call a tool, read the result, and continue.

**Q: How would you know your personality prompts actually work?**
Write evals: fixed test prompts with expected behaviours, run automatically on every
prompt change.

**Q: Why streaming?**
To cut *perceived* latency — the user sees words immediately instead of waiting for the
whole reply.

---

## 11. Glossary

- **LLM** — Large Language Model; predicts the next token given text.
- **Agent** — a system that uses an LLM plus memory, rules, and often tools to accomplish tasks.
- **System prompt** — hidden instruction defining the model's role and rules.
- **Prompt engineering** — designing prompts to get reliable behaviour.
- **Prompt injection / jailbreak** — user input that subverts the system prompt.
- **Guardrails** — logic constraining what the model can do or say.
- **Context window** — the max number of tokens a model can read at once.
- **Token** — the sub-word unit models read and are billed in.
- **Temperature** — randomness knob for generation (0 = deterministic).
- **Streaming** — sending the reply token-by-token as it's generated.
- **Stateless** — retaining no memory between calls.
- **LLM router / model cascading** — using a cheap model to route and a strong model to answer.
- **RAG** — Retrieval-Augmented Generation; injecting fetched documents into the prompt.
- **ReAct** — Reason+Act; interleaving model reasoning with tool calls in a loop.
- **Function/tool calling** — the model requesting a function be run and using its result.
- **Eval** — an automated test of model/prompt behaviour.

---

*Built as a learning project across five phases: features → planning & agent theory →
frontend design → coding → this doc. Powered by [Groq](https://groq.com) and
[Streamlit](https://streamlit.io).*
