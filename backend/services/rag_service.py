import re
from typing import List, Tuple

def chunk_text(text: str, chunk_size: int = 600, overlap: int = 100) -> List[str]:
    """Split text into overlapping semantic chunks."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current_chunk = []
    current_len = 0

    for p in paragraphs:
        p_len = len(p)
        if current_len + p_len > chunk_size and current_chunk:
            combined = "\n\n".join(current_chunk)
            chunks.append(combined)
            # Keep last paragraph for overlap if short
            if len(current_chunk[-1]) < overlap:
                current_chunk = [current_chunk[-1], p]
                current_len = len(current_chunk[0]) + p_len
            else:
                current_chunk = [p]
                current_len = p_len
        else:
            current_chunk.append(p)
            current_len += p_len

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    if not chunks and text.strip():
        chunks.append(text.strip()[:1000])

    return chunks

def tokenize_vietnamese(text: str) -> List[str]:
    """Simple tokenization for Vietnamese query matching."""
    text = text.lower()
    tokens = re.findall(r"\b[\w\d_]+\b", text)
    # Filter common stop words
    stopwords = {"là", "và", "của", "các", "có", "những", "cho", "với", "được", "trong", "về", "một", "thì", "khi", "lại"}
    return [t for t in tokens if t not in stopwords and len(t) > 1]

def search_relevant_chunks(query: str, chunks: List[str], top_k: int = 4) -> List[str]:
    """Score chunks by query term frequency and semantic density."""
    query_tokens = tokenize_vietnamese(query)
    if not query_tokens:
        return chunks[:top_k]

    scored: List[Tuple[float, str]] = []
    for chunk in chunks:
        chunk_lower = chunk.lower()
        score = 0.0
        for token in query_tokens:
            count = chunk_lower.count(token)
            if count > 0:
                score += 1.0 + (count * 0.2)
        
        # Exact phrase bonus
        if query.lower().strip() in chunk_lower:
            score += 5.0

        if score > 0:
            scored.append((score, chunk))

    # Sort descending by score
    scored.sort(key=lambda x: x[0], reverse=True)
    
    results = [s[1] for s in scored[:top_k]]
    # Fallback to first few chunks if no matches
    if not results:
        results = chunks[:top_k]
    return results
