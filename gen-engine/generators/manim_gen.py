"""
Manim Animation Generator — STEM Concept Visualization (Tier 3, 10-45 seconds)

================================================================================
PURPOSE:
    Generate pedagogically-sound animations for abstract STEM concepts.
    Uses writer-reviewer loop to auto-correct Manim code errors.
    Renders to MP4 with calm narration (separate TTS call).

TIER: 3 (Async, 10-45 seconds)

DEPENDENCIES:
    - ollama==0.4.1 : Gemma 4 writes Manim code, reviewer fixes errors
    - manim==0.18.1 : Render animations to MP4
    - ffmpeg (system) : Video encoding
    - numpy==2.1.0 : Math for animations
    - prompts/manim_expert.txt : Writer system prompt
    - prompts/manim_reviewer.txt : Reviewer system prompt
    - subprocess : Execute manim CLI

EXTERNAL SERVICES:
    - Ollama : Gemma 4 E2B model (writer + reviewer)
    - ffmpeg : Video rendering (subprocess)
    - Temp disk : Store intermediate MP4 files (~50MB per render)

INPUT:
    concept: str : What to animate (e.g., "Projectile Motion")
    slide_content: str : Full context
    learner_level: "grade5" | "grade8" | "university"
    session_id: str : For logging

OUTPUT:
    {
        "animation_url": str,
        "format": "mp4",
        "duration_seconds": float,
        "resolution": "1280x720",
        "framerate": 30,
        "writer_attempts": int,
        "reviewer_attempts": int,
        "generation_time_ms": int,
        "error": null | str
    }

WRITER-REVIEWER ALGORITHM:
    1. Writer Step:
        a. Call Gemma 4 with manim_expert prompt
        b. Request Python Scene code that animates concept
        c. Include example output from prompt
    2. Validate & Execute Step:
        a. Write code to temp file
        b. Execute: manim -ql scene.py SceneClass -o output.mp4
        c. Check return code
    3. If failure:
        a. Capture stderr (syntax/render error)
        b. Reviewer Step:
            - Call Gemma 4 with manim_reviewer prompt
            - Include original code + error message
            - Request fixed code
        c. Go back to step 2 (max 2 retries total)
    4. If success:
        a. Move MP4 to output dir
        b. Return URL

MANIM CODE EXAMPLE (Writer generates):
    ```python
    from manim import *

    class ProjectileMotion(Scene):
        def construct(self):
            title = Text("Projectile Motion", font_size=48)
            self.play(Write(title))
            self.wait(1)
            
            # Ball trajectory
            ball = Dot(radius=0.2, color=BLUE)
            path = ParametricFunction(
                lambda t: np.array([5*t - 5, -4.9*t**2 + 10*t - 2, 0]),
                t_range=[0, 2],
                color=YELLOW
            )
            self.play(Create(path))
            self.play(MoveAlongPath(ball, path), run_time=2)
            self.wait(1)
    ```

KEY FUNCTIONS:
    - generate_animation(concept, slide_content, learner_level) → dict
    - call_writer(concept, slide_content) → str
    - execute_manim(code) → tuple[bool, str, str]
    - call_reviewer(code, error_message) → str
    - move_to_output_dir(temp_mp4_path) → str

ERROR HANDLING:
    - Gemma 4 timeout: Fall back to static image + text
    - Manim render timeout (>45s): Kill process, return best frame as image
    - Syntax error after 2 retries: Return text explanation + fallback
    - Disk full: Clean old temp files, retry
    - Invalid Scene class: Reviewer detects & fixes

CONSTRAINTS:
    - Video resolution: 1280x720 (fixed)
    - Quality: "-ql" (low quality for speed)
    - Max duration: 30 seconds (will be cut to 15s for UI)
    - Hard timeout: 45 seconds total (20s for writer + 15s for render + 10s for reviewer)
    - Max retries: 2
    - Temp space: Ensure 100MB free on disk

OPTIMIZATION:
    - Cache generated animations by concept + level
    - Reuse animations for identical concepts across sessions
    - Pre-render common STEM concepts during off-peak

RESEARCH:
    - Animations improve learning gains d=0.67 vs static (LLM2Manim 2026)
    - Learners with low prior knowledge benefit most
    - Progressing animations (slow reveal) more effective than instant

INTEGRATION:
    - Called by action_router when action_id = 3 + content_type="animation"
    - Results cached by (concept, learner_level) pair
    - Rendered MP4 served by frontend via <video> tag
    - Audio added separately via Kokoro TTS

RELATED:
    - kokoro_tts generates narration separately (sync via timestamps)
    - chunk_renderer adds progressive text alongside animation
    - image_gen fallback if animation fails

================================================================================
"""

# TODO: Implement generate_animation() main function
# TODO: Load writer prompt (manim_expert.txt)
# TODO: Implement Gemma 4 writer call
# TODO: Implement manim execution with subprocess
# TODO: Implement error capture and parsing
# TODO: Load reviewer prompt (manim_reviewer.txt)
# TODO: Implement reviewer call for error correction
# TODO: Implement retry loop (max 2 writer + 2 reviewer)
# TODO: Implement output file management and cleanup
# TODO: Add caching by concept
# TODO: Add error handling with image fallback
# TODO: Add metrics tracking
