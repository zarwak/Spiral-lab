# Source Document

Based on what all three summaries describe (same authors, same theorem, same birthday example), the document tested was:

**Title:** Why Language Models Hallucinate
**Authors:** Adam Tauman Kalai (OpenAI), Ofir Nachum (OpenAI), Santosh S. Vempala (Georgia Tech), Edwin Zhang (OpenAI)
**Published:** September 4, 2025
**arXiv:** [2509.04664](https://arxiv.org/abs/2509.04664) (cs.CL)
**License:** CC BY 4.0
**Official announcement:** https://openai.com/index/why-language-models-hallucinate/

## Paraphrased abstract

The paper argues hallucinations aren't a mysterious glitch — they're the predictable output of two things. First, pretraining: minimizing cross-entropy loss statistically forces errors on facts with no learnable pattern, like exact birthdays that show up once in the training set. Second, post-training evaluation: binary right/wrong grading rewards confident guessing over admitting uncertainty, so models stay in what the authors call "test-taking mode." Their proposed fix isn't another hallucination-specific benchmark — it's re-scoring the benchmarks that already dominate leaderboards (GPQA, MMLU-Pro, SWE-bench, and others) so they stop giving zero credit for "I don't know."

## PDF 

### Why Language Models Hallucinate

1. Grab it yourself — [arxiv.org/pdf/2509.04664](https://arxiv.org/pdf/2509.04664). It's CC BY 4.0, so you're free to keep a copy here.
2. Upload it to me in a later message and I'll place it in this folder for you.

**Important for the deliverable:** I fetched the actual paper text (introduction, related work, and pretraining sections) directly and checked each summary's specific claims against it — not just the three summaries against each other. That's what backs the Accuracy and Hallucinations scores in `04-comparison-table.md`. If this had been a paper I couldn't find or verify, those two columns would need to say "unverified" instead of a score.
