#!/usr/bin/env python3
"""
Name matching utilities (platformized)
- Normalizes input (lowercase, strip accents, remove honorifics, punctuation)
- Generates variants
- Computes composite similarity score to match user-provided names to known candidates

No external dependencies; uses only Python stdlib.
"""

from typing import List, Dict, Any, Callable, Tuple, Optional
import unicodedata
import re
import difflib
import logging

logger = logging.getLogger(__name__)

HONORIFICS = [
    'dra', 'dr', 'doutora', 'doutor', 'prof', 'profa', 'sr', 'sra', 'srta'
]


def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        return ''
    # remove accents
    text_nfkd = unicodedata.normalize('NFKD', text)
    text_ascii = ''.join(c for c in text_nfkd if not unicodedata.combining(c))
    text_ascii = text_ascii.lower()
    # remove honorifics
    for h in HONORIFICS:
        text_ascii = re.sub(rf'\b{re.escape(h)}\.?\b', ' ', text_ascii)
    # remove non-alphanum (keep spaces)
    text_ascii = re.sub(r'[^a-z0-9\s]', ' ', text_ascii)
    # collapse spaces
    text_ascii = re.sub(r'\s+', ' ', text_ascii).strip()
    return text_ascii


def generate_variants(text_norm: str) -> List[str]:
    if not text_norm:
        return []
    tokens = text_norm.split()
    variants = set([text_norm])
    # first token, first two tokens
    if tokens:
        variants.add(tokens[0])
    if len(tokens) >= 2:
        variants.add(' '.join(tokens[:2]))
    # prefixes of last token (help for diminutives like "dine" from "geraldine")
    last = tokens[-1] if tokens else ''
    for n in [3, 4, 5]:
        if len(last) >= n:
            variants.add(last[:n])
    return list(variants)


def _prefix_score(a: str, b: str) -> float:
    common = 0
    for ca, cb in zip(a, b):
        if ca == cb:
            common += 1
        else:
            break
    if not b:
        return 0.0
    return min(1.0, common / max(len(b), 1))


def _bigram_overlap(a: str, b: str) -> float:
    def bigrams(s: str) -> set:
        return set(s[i:i+2] for i in range(max(len(s)-1, 0)))
    A, B = bigrams(a), bigrams(b)
    if not A or not B:
        return 0.0
    inter = len(A & B)
    union = len(A | B)
    return inter / union if union else 0.0


def composite_similarity(query: str, target: str) -> float:
    a = normalize_text(query)
    b = normalize_text(target)
    if not a or not b:
        return 0.0
    # primary ratio
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    # prefix bonus focuses on target beginning match
    pscore = _prefix_score(a, b)
    # bigram overlap captures internal similarity
    bigr = _bigram_overlap(a, b)
    # substring bonus
    substr = 1.0 if (a in b or b in a) else 0.0
    score = 0.5 * ratio + 0.25 * pscore + 0.2 * bigr + 0.05 * substr
    return max(0.0, min(1.0, score))


class NameMatcher:
    def __init__(self, min_score: float = 0.8, gap_score: float = 0.08, gray_lower: float = 0.65):
        self.min_score = min_score
        self.gap_score = gap_score
        self.gray_lower = gray_lower

    def find_best(self, user_text: str, candidates: List[Any], get_name: Callable[[Any], str]) -> Dict[str, Any]:
        qnorm = normalize_text(user_text)
        variants = generate_variants(qnorm)
        scored: List[Tuple[float, Any, str]] = []
        for cand in candidates:
            name = get_name(cand) or ''
            best_for_cand = 0.0
            best_var = ''
            for v in [qnorm] + variants:
                s = composite_similarity(v, name)
                if s > best_for_cand:
                    best_for_cand = s
                    best_var = v
            scored.append((best_for_cand, cand, best_var))
        scored.sort(key=lambda x: x[0], reverse=True)
        if not scored:
            return {"match": None, "score": 0.0, "candidates": []}
        top_score, top_cand, used = scored[0]
        result = {
            "match": top_cand,
            "score": top_score,
            "used_variant": used,
            "candidates": [(float(s), get_name(c)) for s, c, _ in scored[:5]]
        }
        # Decision flags
        result["confident"] = top_score >= self.min_score and (len(scored) == 1 or top_score - scored[1][0] >= self.gap_score)
        result["ambiguous"] = (self.gray_lower <= top_score < self.min_score) or (len(scored) > 1 and top_score - scored[1][0] < self.gap_score)
        logger.info(f"NameMatcher: query='{user_text}' -> top={get_name(top_cand)} score={top_score:.3f} candidates={result['candidates']}")
        return result 