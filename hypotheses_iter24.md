# Hypotheses - Iteration 24: Version Check YAML

## H1: YAML cache with checked_at will survive file copy operations
- **Root cause**: mtime-based cache at L2882 (`cache_file.stat().st_mtime`) can change on file copy, rsync, or git clone - making the cache appear expired when it isn't, or fresh when it's stale
- **Prediction**: using `checked_at` ISO8601 timestamp inside the YAML content makes expiry independent of filesystem metadata. File copy preserves content but may change mtime - structured YAML is immune to this.
- **Evidence**: L2882 uses `time.time() - cache_file.stat().st_mtime` which depends on OS file metadata
- **Stars**: 4

## H2: Legacy plain-text handling should be a silent one-time migration
- **Root cause**: existing .version_check files contain just "0.8.51" (plain text). yaml.safe_load("0.8.51") returns the string "0.8.51", not a dict.
- **Prediction**: detecting `isinstance(data, str)` after yaml.safe_load is a valid migration path here (unlike context.yaml where we rejected migration). For a non-critical cache file, graceful migration is pragmatic - read the version string, rewrite as YAML dict. This is a cache, not user data.
- **Evidence**: BENCHMARK.md S10 item 5: "Legacy plain-text .version_check handled gracefully (read as version string, rewrite as YAML)"
- **Stars**: 3

## H3: The 24h cache window should use datetime comparison, not time.time()
- **Root cause**: current code uses `time.time() - mtime` which mixes epoch seconds. checked_at as ISO8601 needs datetime parsing.
- **Prediction**: using `datetime.fromisoformat(checked_at)` compared to `datetime.now(timezone.utc)` gives portable, readable expiry logic. The overhead of datetime parsing is negligible for a once-per-startup check.
- **Evidence**: _now() already returns ISO8601 strings throughout the codebase
- **Stars**: 3
