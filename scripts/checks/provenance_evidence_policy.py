"""Compatibility shim for canonical media provenance validators."""
try:
    from agent.media_provenance import has_license_denial, is_affirmative_license_scope, select_affirmative_license_scope
except ModuleNotFoundError:
    from pathlib import Path
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from agent.media_provenance import has_license_denial, is_affirmative_license_scope, select_affirmative_license_scope
__all__ = ["has_license_denial", "is_affirmative_license_scope", "select_affirmative_license_scope"]
