"""
Text Simplification Generator — Tier 2 (2-5 seconds)

================================================================================
PURPOSE:
    Simplify complex text to target reading level using Gemma 4 E2B.
    Verify output with Flesch-Kincaid scoring.
    Retry loop ensures FK grade meets target.

TIER: 2 (Fast, 2-5 seconds)

DEPENDENCIES:
    - ollama==0.4.1 : Local LLM inference
    - textstat==0.7.3 : Flesch-Kincaid scoring
    - spacy==3.8.2 : Sentence tokenization
    - prompts/simplify_*.txt : Few-shot prompt templates
    - tenacity : Exponential backoff retry logic

EXTERNAL SERVICES:
    - Ollama (http://localhost:11434) : Gemma 4 E2B model
    - PostgreSQL (for caching) : Store simplifications by hash

INPUT:
    text: str : Original text to simplify
    target_level: "grade5" | "grade8" | "university" : Target FK grade
    session_id: str : For logging/caching

FK GRADE TARGETS:
    - grade5: FK ≤ 6.0 (ages 11-12, severe difficulty)
    - grade8: FK ≤ 9.0 (ages 13-14, default)
    - university: FK ≤ 13.0 (ages 18+, minimal changes)

OUTPUT:
    {
        "simplified_text": str,
        "fk_grade": float,
        "original_fk": float,
        "chunks": list[str],
        "attempts": int,
        "cache_hit": bool
    }

ALGORITHM:
    1. Check cache (MD5 hash of text + target_level)
    2. If cache miss:
        a. Call Gemma 4 with few-shot prompt
        b. Compute FK score of output
        c. If FK ≤ target: return
        d. If FK > target AND attempts < 2:
            - Call with stricter prompt + error feedback
            - Retry step b-c
        e. If attempts exhausted: return best attempt + warning
    3. Chunk result by sentences for progressive reveal

KEY FUNCTIONS:
    - simplify_text(text, target_level, session_id) → dict
    - compute_fk_score(text) → float
    - chunk_by_sentences(text) → list[str]
    - load_prompt_template(level) → str
    - retry_with_stricter_prompt(text, fk_score, target) → str

ERROR HANDLING:
    - Ollama timeout: Serve original text + warning
    - FK computation failure: Return unverified simplified text + warning
    - Cache miss after 2 retries: Return best attempt with flag

CONSTRAINTS:
    - Max token input: 1024 (split if necessary)
    - Max token output: 512
    - Retry attempts: Max 2
    - Hard timeout: 5 seconds

INTEGRATION:
    - Called by action_router when action_id = 2
    - Results cached for 24 hours
    - FK scores logged for learner analytics

RELATED:
    - quiz_injector uses simplified text for question generation
    - chunk_renderer uses chunks for progressive reveal
================================================================================
"""

# TODO: Implement simplify_text() main function
# TODO: Load Gemma 4 few-shot templates
# TODO: Implement FK verification loop
# TODO: Implement cache lookup/storage
# TODO: Implement sentence chunking
# TODO: Add retry logic with stricter prompts
# TODO: Add error handling with fallbacks
# TODO: Add logging/metrics
