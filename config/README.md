# Canonical launch artifacts

This directory is the only source location for launch-safety configuration
artifacts. The canonical filenames are:

- `launch-indexing-policy.json`
- `ai-disclosure.json`

Do not copy these artifacts into application directories. Docker builds and
release archives consume the files directly from this root `config/` boundary.
The JSON artifacts are introduced by their dedicated launch-safety tasks.
