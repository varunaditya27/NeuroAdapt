"""
Analogy Engine — 3-Analogy Escape Hatch (Tier 2, 2-5 seconds)

================================================================================
PURPOSE:
    Generate 3 different analogies to explain a complex concept.
    Triggered when learner clicks "I don't understand" or pre-emptively.
    Each analogy maps concept to familiar domain (brain, traffic, cooking, etc).

TIER: 2 (Fast, 2-5 seconds)

DEPENDENCIES:
    - ollama==0.4.1 : Gemma 4 generates analogies
    - prompts/analogy_generator.txt : System prompt for analogy generation
    - spacy==3.8.2 : Extract concept entities
    - tenacity : Retry with different seeds

EXTERNAL SERVICES:
    - Ollama : Gemma 4 E2B model
    - PostgreSQL : Log analogies for learner preference tracking
    - Redis (optional) : Cache analogies by concept

INPUT:
    concept: str : What to explain (e.g., "Neural Networks")
    slide_content: str : Additional context
    learner_level: "grade5" | "grade8" | "university"
    session_id: str : For logging

OUTPUT:
    {
        "concept": str,
        "analogies": [
            {
                "id": int,
                "title": str,
                "source_domain": str,
                "explanation": str,
                "example": str,
                "readability_grade": float
            },
            {
                "id": int,
                "title": str,
                "source_domain": str,
                "explanation": str,
                "example": str,
                "readability_grade": float
            },
            {
                "id": int,
                "title": str,
                "source_domain": str,
                "explanation": str,
                "example": str,
                "readability_grade": float
            }
        ],
        "generation_time_ms": int,
        "learner_selected": null (updated after user interaction)
    }

ALGORITHM:
    1. Parse concept to extract key properties
    2. Call Gemma 4 with prompt requesting 3 analogies:
        - Domain 1: Biological/body-based
        - Domain 2: Mechanical/transport
        - Domain 3: Everyday/cooking
    3. Each analogy includes:
        - Title
        - Source domain
        - 2-3 sentence explanation
        - Real-world example
    4. Verify readability level matches target
    5. Store response + track if learner selected one
    6. Return 3 analogies

ANALOGY DOMAINS:
    - Brain/Body : For abstract concepts (neurons, networks, systems)
    - Traffic/Transport : For flow, routing, connections
    - Cooking/Recipes : For combinations, processes, transformations
    - Building/Construction : For structure, assembly, layers
    - Music/Orchestra : For harmony, timing, coordination
    - Garden/Nature : For growth, cycles, balance
    - Sports/Games : For competition, strategy, scoring

RESEARCH:
    - Analogies improve problem-solving from 10% to 80% success (Gick & Holyoak)
    - Multiple analogies (3+) more effective than single (Glynn)
    - Learner-selected analogies have 40% higher engagement

KEY FUNCTIONS:
    - generate_analogies(concept, slide_content, learner_level) → dict
    - extract_concept_properties(concept) → dict
    - generate_analogy_prompt(concept, properties, domain) → str
    - validate_readability_level(text, target_level) → bool
    - track_analogy_selection(learner_id, concept, selected_analogy_id) → None

ERROR HANDLING:
    - Gemma 4 timeout: Return cached analogies if available, else fallback
    - Invalid domain: Skip that analogy, retry with different seed
    - Readability mismatch: Regenerate with stricter prompt

CONSTRAINTS:
    - Always 3 analogies (fixed)
    - Each explanation < 150 words
    - Hard timeout: 3 seconds
    - Max retries: 2

INTEGRATION:
    - Called by action_router when action_id = 2 + learner feedback
    - Learner selects best analogy → logged to PostgreSQL
    - Selection preference used for future analogy generation
    - Analogies cached by concept for reuse

RELATED:
    - text_simplify may trigger analogy_engine as fallback
    - Frontend ContentRenderer displays 3-option carousel
    - Analogy selections improve personalization model
================================================================================
"""

# TODO: Implement generate_analogies() main function
# TODO: Load analogy generator prompt
# TODO: Implement concept property extraction
# TODO: Call Gemma 4 for each domain
# TODO: Verify readability level
# TODO: Implement retry logic with different domains
# TODO: Add learner preference tracking
# TODO: Implement caching by concept
# TODO: Add error handling with fallbacks
