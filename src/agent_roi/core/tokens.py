"""Token estimation for tools that don't report real usage.

Some tools (notably GitHub Copilot) log the conversation text but not the token
counts. For those, we estimate counts so cost can still be *approximated* and
compared across tools. Estimated interactions are flagged
(``Interaction.estimated = True``) so reports never present them as exact.

The estimator is a dependency-free heuristic so it works fully offline (this is
a local-first tool). It blends a character-based and word-based estimate, which
tracks real BPE token counts closely enough for reporting — typically within
~10-15% for mixed English/code text. We deliberately avoid pulling a tokenizer
that downloads model files at runtime.
"""

from __future__ import annotations

# Empirically, English + code averages ~4 characters per token, and tokens run
# ~1.3x the whitespace-delimited word count. Averaging the two estimates is more
# robust than either alone across prose, code, and JSON-heavy text.
_CHARS_PER_TOKEN = 4.0
_TOKENS_PER_WORD = 1.3


def estimate_tokens(text: str) -> int:
    """Estimate the number of tokens in a piece of text (offline heuristic)."""
    if not text:
        return 0
    char_estimate = len(text) / _CHARS_PER_TOKEN
    word_estimate = len(text.split()) * _TOKENS_PER_WORD
    return max(1, round((char_estimate + word_estimate) / 2))
