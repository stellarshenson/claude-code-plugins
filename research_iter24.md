# Research - Iteration 24: Version Check Structured YAML

## Current code: _check_version (L2869-2901)
- Cache file: `.auto-build-claw/.version_check` (plain text, version string only)
- Cache check: `time.time() - cache_file.stat().st_mtime` < 86400 (mtime-based)
- Cache write: `cache_file.write_text(latest)` (plain text)
- If cached: returns early without querying PyPI
- If not cached or expired: queries PyPI, writes cache, compares versions

## Target format
```yaml
latest_version: "0.8.51"
checked_at: "2026-04-02T14:00:00+00:00"
```

## Changes needed
1. Read cache: parse YAML, check `checked_at` field for 24h expiry
2. Write cache: write YAML dict with `latest_version` and `checked_at`
3. Legacy: if file contains plain text (not YAML dict), read as version string and rewrite as YAML
