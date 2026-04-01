#!/usr/bin/env python3
"""Auto Build Claw - thin entrypoint.

Delegates to the shared orchestration engine in stellars_claude_code_plugins.
Resources are bundled in the module and auto-copied to .auto-build-claw/resources/
on first use. No resources_dir needed.
"""

import sys
from pathlib import Path

# Resolve engine: try pip/editable install first, fallback to repo-relative path
try:
    from stellars_claude_code_plugins.engine.orchestrator import main
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from stellars_claude_code_plugins.engine.orchestrator import main

if __name__ == "__main__":
    main()
