from __future__ import annotations


def split_text_windows(text: str, *, window: int = 800, overlap: int = 0) -> list[str]:
    cleaned = text.strip()
    if not cleaned:
        return []
    if len(cleaned) <= window:
        return [cleaned]
    if overlap >= window:
        raise ValueError("overlap должен быть меньше window")
    chunks: list[str] = []
    start = 0
    step = window - overlap
    while start < len(cleaned):
        piece = cleaned[start : start + window].strip()
        if piece:
            chunks.append(piece)
        start += step
    return chunks
