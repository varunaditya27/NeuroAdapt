"""
Dynamic LLM Provider Selection (Groq vs Ollama)

This module provides flexible routing between Groq (cloud) and Ollama (local) LLMs
based on runtime availability. If GROQ_API_KEY is set, Groq is preferred; otherwise
falls back to Ollama.

Provider Selection Logic:
  1. Startup: Check GROQ_API_KEY presence
  2. If set: Try Groq; fallback to Ollama on error
  3. If unset: Use Ollama only
  4. All failures logged with fallback chain info

Usage:
  from orchestration.llm_provider import get_llm_client, call_llm
  
  # Option 1: Call directly with provider detection
  response = call_llm(
      prompt="Simplify this text...",
      system="You are a text simplifier",
      temperature=0.2,
      max_tokens=4096,
  )
  
  # Option 2: Get client and use directly
  client = get_llm_client()
  # Use client for multiple calls
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional, cast

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

_GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
_GROQ_MODEL = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")
_GROQ_AVAILABLE = bool(_GROQ_API_KEY)

_OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:e2b")

# Cache clients to avoid re-initialization
_GROQ_CLIENT: Any = None
_OLLAMA_INITIALIZED: bool = False

logger.info(
    f"LLM Provider: {'Groq available (fallback: Ollama)' if _GROQ_AVAILABLE else 'Ollama only'}"
)


# ============================================================================
# PROVIDER INITIALIZATION
# ============================================================================


def _init_groq() -> Optional[Any]:
    """Initialize Groq client if API key is available."""
    global _GROQ_CLIENT
    if _GROQ_CLIENT is not None:
        return _GROQ_CLIENT

    if not _GROQ_AVAILABLE:
        return None

    try:
        from groq import Groq

        _GROQ_CLIENT = Groq(api_key=_GROQ_API_KEY)
        logger.info(f"✓ Groq client initialized (model: {_GROQ_MODEL})")
        return _GROQ_CLIENT
    except ImportError:
        logger.warning("Groq SDK not installed; falling back to Ollama only")
        return None
    except Exception as exc:
        logger.warning(f"Groq initialization failed: {exc}; using Ollama")
        return None


def get_active_provider() -> str:
    """Return the active LLM provider name."""
    if _GROQ_AVAILABLE and _init_groq() is not None:
        return "groq"
    return "ollama"


def get_llm_client() -> Any:
    """
    Get initialized LLM client (Groq or Ollama).
    
    Returns:
        Groq client if available, otherwise returns Ollama URL string.
    """
    if _GROQ_AVAILABLE:
        client = _init_groq()
        if client is not None:
            return client
    return _OLLAMA_URL  # Ollama URL passed to _call_ollama


# ============================================================================
# UNIFIED LLM CALLING INTERFACE
# ============================================================================


def _call_groq(
    prompt: str,
    system: str | None = None,
    temperature: float = 0.35,
    max_tokens: int = 900,
    response_format: Optional[dict[str, Any]] = None,
    timeout_seconds: float = 60.0,
) -> str:
    """
    Call Groq API with OpenAI-compatible interface.
    
    Args:
        prompt: User message/prompt
        system: System message (optional)
        temperature: Sampling temperature (0.0-2.0)
        max_tokens: Max response tokens
        response_format: Optional format spec (e.g., {"type": "json_object"})
        timeout_seconds: Request timeout
    
    Returns:
        Model response text
    
    Raises:
        Exception: On API error
    """
    client = _init_groq()
    if client is None:
        raise RuntimeError("Groq not available")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    kwargs = {
        "model": _GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "timeout": timeout_seconds,
    }
    if response_format:
        kwargs["response_format"] = response_format

    try:
        response = client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        return cast(str, content).strip() if content else ""
    except Exception as exc:
        logger.warning(f"Groq API error: {exc}")
        raise


def _call_ollama(
    prompt: str,
    system: str | None = None,
    temperature: float = 0.35,
    max_tokens: int = 900,
    response_format: Optional[dict[str, Any]] = None,
    timeout_seconds: float = 60.0,
) -> str:
    """
    Call Ollama API.
    
    Args:
        prompt: User message/prompt
        system: System message (optional)
        temperature: Sampling temperature
        max_tokens: Max response tokens (num_predict in Ollama)
        response_format: Format spec (not directly supported; logged if provided)
        timeout_seconds: Request timeout
    
    Returns:
        Model response text
    
    Raises:
        Exception: On API error
    """
    import requests

    if response_format:
        logger.debug(f"Ollama: response_format ignored: {response_format}")

    payload = {
        "model": _OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    if system:
        payload["system"] = system

    try:
        response = requests.post(
            f"{_OLLAMA_URL}/api/generate",
            json=payload,
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        return (response.json().get("response") or "").strip()
    except Exception as exc:
        logger.warning(f"Ollama API error: {exc}")
        raise


def call_llm(
    prompt: str,
    system: str | None = None,
    temperature: float = 0.35,
    max_tokens: int = 900,
    response_format: Optional[dict[str, Any]] = None,
    timeout_seconds: float = 60.0,
    provider: Optional[str] = None,
) -> str:
    """
    Call LLM with automatic provider fallback.
    
    **Provider Selection:**
    - If `provider="groq"`: Try Groq; raise error if Groq unavailable
    - If `provider="ollama"`: Use Ollama only
    - If `provider=None`: Auto-detect (Groq if available, else Ollama)
    
    Args:
        prompt: User message/prompt
        system: System message (optional)
        temperature: Sampling temperature (0.0-2.0)
        max_tokens: Max response tokens
        response_format: Optional format spec (e.g., {"type": "json_object"})
        timeout_seconds: Request timeout
        provider: Force provider ("groq" | "ollama" | None for auto)
    
    Returns:
        Model response text
    
    Raises:
        RuntimeError: If provider explicitly requested but unavailable
        Exception: On API errors (after fallback attempts)
    """
    # Explicit provider request
    if provider == "groq":
        if not _GROQ_AVAILABLE or _init_groq() is None:
            raise RuntimeError("Groq requested but API key not configured")
        logger.debug("Using Groq (explicit request)")
        return _call_groq(
            prompt,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            timeout_seconds=timeout_seconds,
        )

    if provider == "ollama":
        logger.debug("Using Ollama (explicit request)")
        return _call_ollama(
            prompt,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            timeout_seconds=timeout_seconds,
        )

    # Auto-detect with fallback chain
    active_provider = get_active_provider()
    logger.debug(f"Using {active_provider} (auto-detected)")

    try:
        if active_provider == "groq":
            return _call_groq(
                prompt,
                system=system,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
                timeout_seconds=timeout_seconds,
            )
        else:
            return _call_ollama(
                prompt,
                system=system,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
                timeout_seconds=timeout_seconds,
            )
    except Exception as exc:
        # Fallback: if Groq failed, try Ollama
        if active_provider == "groq":
            logger.warning(f"Groq failed: {exc}; falling back to Ollama")
            try:
                return _call_ollama(
                    prompt,
                    system=system,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=None,  # Ollama doesn't support JSON format mode
                    timeout_seconds=timeout_seconds,
                )
            except Exception as fallback_exc:
                logger.error(f"Ollama fallback failed: {fallback_exc}")
                raise RuntimeError(
                    f"LLM call failed (Groq: {exc}; Ollama: {fallback_exc})"
                )
        else:
            raise


# ============================================================================
# STARTUP VERIFICATION
# ============================================================================


def verify_llm_provider() -> tuple[str, bool]:
    """
    Verify LLM provider availability at startup.
    
    Returns:
        (provider_name, is_healthy): e.g., ("groq", True) or ("ollama", False)
    """
    provider = get_active_provider()

    try:
        if provider == "groq":
            _init_groq()
            logger.info("✓ Groq provider verified")
            return "groq", True
        else:
            # Ollama: try a quick test call
            import requests

            response = requests.get(f"{_OLLAMA_URL}/api/tags", timeout=2)
            response.raise_for_status()
            logger.info("✓ Ollama provider verified")
            return "ollama", True
    except Exception as exc:
        logger.warning(f"Provider verification failed: {exc}")
        return provider, False
