# Day 1 — LLM Comparison: Document Summarization

**Task:** compare GPT, Gemini, and Claude summarizing the same paper, scored on quality, accuracy, conciseness, and hallucinations.

**Source:** ["Why Language Models Hallucinate"](https://arxiv.org/abs/2509.04664) — Kalai, Nachum, Vempala, Zhang (OpenAI / Georgia Tech, Sept 2025).

## Headline result

All three summaries fact-checked clean against the actual paper — zero hallucinations, verified against the primary source rather than just cross-checking the three against each other. But that result is worth less than it looks: this paper is famous enough that all three models probably already knew it from training, which undercuts it as a hallucination test. Full explanation in `05-conclusion.md`.

On the criteria that could actually differentiate them:

| Model | Overall | One-line why |
|---|---|---|
| Claude | 8.75/10 | Most complete and precise — named authors/date/theorem correctly, all verified |
| Gemini | 9/10 | Best structured, fully accurate, most skimmable |
| GPT | 7/10 | Accurate but generic — reads like a template, not close engagement with this paper |

## Files

| File | What's in it |
|---|---|
| `00-task-brief.md` | The assignment as given |
| `01-source-document.md` | Verified citation + why the PDF itself isn't in this folder |
| `02-prompt-used.md` | prompt given to all llms |
| `03-summaries/` | The three raw outputs, unedited |
| `04-comparison-table.md` | Full scored table + per-model reasoning |
| `05-conclusion.md` | Verdict, the eval-design flaw to fix, and next action |

## Why this is worth doing properly

This is your LLM-evaluation rep — golden test cases, comparing model outputs, catching hallucinations against a source of truth. That's a named gap on your roadmap and one of the higher-leverage ones to close. Treat this as commit #1 of a small eval harness, not a homework file you close and forget — `05-conclusion.md` has the specific next step to make Day 2 a real test instead of an easier rerun of Day 1.
