"""Synthetic coding acceptance task: correct cached-input billing."""


def cost_usd(input_tokens, output_tokens, cached_tokens):
    # Current bug: cached tokens are charged twice.
    return (input_tokens * 0.4 + cached_tokens * 0.1 + output_tokens * 1.6) / 1_000_000
