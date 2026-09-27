"""Compatibility shim for canonical media provenance validators."""
try:
    from agent.media_provenance import is_placeholder_hostname, is_public_provenance_url
except ModuleNotFoundError:
    from pathlib import Path
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from agent.media_provenance import is_placeholder_hostname, is_public_provenance_url
__all__ = ["is_public_provenance_url", "is_placeholder_hostname"]
