# Comparison Table

**Method:** Accuracy and Hallucinations weren't scored by comparing the three summaries to each other — that only catches disagreements, not shared mistakes. Each summary's specific claims (authors, dates, the core theorem, named benchmarks, terminology) were checked against the actual paper text (arXiv 2509.04664, fetched directly). Conciseness is backed by an actual word count (`wc -w`), not eyeballing — first pass estimate was wrong, see the note below the table.

| Model | Summary Quality | Accuracy | Conciseness | Hallucinations | Overall Score |
|---|---|---|---|---|---|
| GPT (ChatGPT) | 6/10 | 8/10 | 5/10 | 10/10 | **7/10** |
| Gemini | 9/10 | 9/10 | 7/10 | 10/10 | **9/10** |
| Claude | 7/10 | 10/10 | 9/10 | 10/10 | **8.75/10** |

## Word counts (objective, via `wc -w`)

| Model | Words |
|---|---|
| GPT | 199 |
| Claude | 199 |
| Gemini | 220 |

GPT and Claude are the same length. Gemini is the longest. That's worth flagging because it's the opposite of what a first-glance read suggests — Claude's paragraphs *feel* denser, so I assumed they'd be longer, and checked instead of trusting that impression. They weren't. That's the whole reason Conciseness is scored on information preserved per word, not on which one "reads" longer.

## Per-model notes

### GPT — 7/10
Everything it states is correct, but it's the least falsifiable of the three: no author names, no date, no specific benchmark names, no quantitative claim. "Distribution shift," "computational hardness," and "epistemic uncertainty" are real concepts the paper touches (they map to real sections — arbitrary facts, an appendix on computational intractability, additional factors like noisy data), but stated this generically they read as boilerplate hallucination-survey language that would fit almost any paper on this topic, not evidence GPT engaged with *this* paper specifically. Same word count as Claude (199) but noticeably less specific content packed into it — that's what the Conciseness score is penalizing, not length.

### Gemini — 9/10
Best-structured by a clear margin — the four headers (Purpose/Method/Findings/Challenges) make it the easiest of the three to actually scan. Everything checkable came back accurate: the "reduction from unsupervised to supervised learning" framing is the paper's own description of its novel contribution (Section 2), and "test-taking mode" is an exact phrase from the paper's introduction, used correctly. "10 dominant evaluation benchmarks" checks out too — a companion analysis by the same authors evaluated exactly ten benchmarks, nine of which penalized "I don't know." One phrase, "behavioral calibration," I couldn't independently confirm in the sections I read — plausible, not verified. Longest of the three at 220 words, though the length is structural (headers) rather than padding.

### Claude — 8.75/10
The most complete and the only one to name authors, affiliation, and date — and every one of those specifics checked out (Kalai, Nachum, and Zhang are OpenAI; Vempala is Georgia Tech; published September 4, 2025). It's also the only one to state the actual theorem ("roughly twice the IIV misclassification rate") instead of gesturing at "theoretical lower bounds" — the paper's real bound is err ≥ 2·err_iiv − (correction term), so "roughly twice" is an accurate plain-English rendering, not an approximation that drifted. VC dimension, agnostic learning, and Good-Turing missing-mass estimation are all genuinely part of the paper's theoretical apparatus (Section 3.3.1 and Section 2, Related Work). The four "open challenges" line up one-to-one with the paper's actual Section 5 subsection titles (Open-ended generations; Search and reasoning are not panaceas; Latent context; the socio-technical leaderboard problem). Weakest on Summary Quality — it's two long paragraphs with no headers, so despite being tied for shortest by word count, it's the hardest of the three to skim.

