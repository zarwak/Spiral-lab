# Conclusion

## Which model performed best, and why

**Claude, narrowly — but Gemini is close enough that the honest answer is "it depends what you need."**

- If you need a summary a busy person will actually *read* — Gemini wins. The headers do real work; it's the only one of the three that's skimmable in under 15 seconds.
- If you need a summary you could cite from, or use to decide whether the paper is worth your time — Claude wins. It's the only one that got specific about who wrote it, when, and what the actual mathematical claim is, and every one of those specifics held up against the real paper.
- GPT is competent and made zero factual errors, but it's also the summary you'd get from almost any model on almost any computational-learning-theory paper — it doesn't show clear evidence of having engaged with *this* document's specific content versus the general shape of "papers about hallucination."

Given the task explicitly weights Accuracy as one of four criteria and defines it as "correctly represent the information in the source document" — not just "avoid being wrong" — the model that correctly included the *most* verifiable information (Claude) has the strongest claim to first place. Gemini is a close second on the strength of its structure.

## The one thing worth fixing before Day 2

Every model scored 10/10 on Hallucinations. That sounds like a clean result, but it's a weak test: "Why Language Models Hallucinate" is a paper OpenAI publicized heavily in September 2025. All three models likely already had facts about it baked into their training data, so this exercise couldn't distinguish "the model read my document carefully" from "the model already knew this paper." A model that ignored the source entirely and answered from memory would score identically here.

**Fix for Day 2:** pick a document none of the three models could plausibly have memorized — something obscure, unpublished, very recent, or synthetic (e.g., a paper you lightly edit to change a few facts, then check whether the summaries reflect your edited version or the original). That's the only way this eval actually measures grounded reading instead of recall. This is the same principle behind a golden eval set in any real eval harness: the test has to be able to fail, or a pass proves nothing.

## Next action

Rebuild this exact folder structure for Day 2, but swap in a source document the models can't have memorized, and fill in `02-prompt-used.md` with the real prompt *before* you run it, not after. That turns this from a one-off comparison into the start of an actual eval harness — which is worth more on a resume than either the folder or the paper it's about.
