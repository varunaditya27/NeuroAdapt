"""Public package exports for gen-engine."""

try:
	from .main import app
except Exception:  # pragma: no cover - allows pytest top-level import mode
	try:
		from main import app  # type: ignore
	except Exception:
		app = None  # type: ignore

__all__ = ["app"]
