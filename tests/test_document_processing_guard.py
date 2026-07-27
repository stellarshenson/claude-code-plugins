"""The import guard in `document_processing/__init__.py` raises when groundrails is absent.

That branch is reachable only off Python 3.12, which is exactly where
`test_document_processing_cli.py` skips - so without this file the guard's message
ships untested on every CI leg. Here the absence the other module skips over is what
makes the assertion possible.
"""

from __future__ import annotations

import importlib
import importlib.util

import pytest


def test_guard_explains_the_interpreter_requirement():
    """Absent groundrails must raise a message naming the engine and the 3.12 pin,
    not the bare "No module named 'groundrails'" that says nothing about why."""
    if importlib.util.find_spec("groundrails") is not None:
        pytest.skip("groundrails installed - the guard branch is unreachable here")

    with pytest.raises(ModuleNotFoundError) as exc:
        importlib.import_module("stellars_claude_code_plugins.document_processing")

    msg = str(exc.value)
    assert "groundrails" in msg
    assert "3.12" in msg
    # The absence is by design only OFF 3.12. An earlier revision interpolated the
    # running version here, which made the sentence claim by-design absence on 3.12
    # itself - the one interpreter where absence means a broken install.
    assert "every other interpreter" in msg
