"""Word-approximate chunking for the starter; token sizes are estimates."""

from app.core.config import get_settings

WORDS_PER_TOKEN = 0.75


def chunk_text(text: str) -> list[str]:
    settings = get_settings()
    words = text.split()
    if not words:
        return []
    chunk_words = max(int(settings.chunk_size * WORDS_PER_TOKEN), 1)
    overlap_words = int(settings.chunk_overlap * WORDS_PER_TOKEN)
    step = max(chunk_words - overlap_words, 1)
    chunks = []
    for start in range(0, len(words), step):
        chunks.append(" ".join(words[start : start + chunk_words]))
        if start + chunk_words >= len(words):
            break
    return chunks
