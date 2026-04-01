"""Integration tests for the orchestration engine.

Tests the orchestrator's initialization, state management, display helpers,
and command functions using minimal YAML fixtures. Gate functions (claude -p)
are mocked since they require the claude CLI.
"""

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from stellars_claude_code_plugins.engine import orchestrator as orch


@pytest.fixture(autouse=True)
def reset_orchestrator():
    """Reset module-level state between tests."""
    orch._initialized = False
    orch._MODEL = None
    orch.ITERATION_TYPES.clear()
    orch.PHASE_AGENTS.clear()
    orch._PHASE_START.clear()
    orch._PHASE_END.clear()
    orch._AUTO_ACTION_REGISTRY.clear()
    yield


class TestInitialize:
    """Tests for _initialize with minimal and real YAML resources."""

    def test_initialize_minimal(self, minimal_resources):
        orch._initialize(minimal_resources)
        assert orch._initialized is True
        assert orch._MODEL is not None
        assert "test_workflow" in orch.ITERATION_TYPES
        assert orch.CMD == "python orchestrate.py"

    def test_initialize_sets_paths(self, minimal_resources):
        orch._initialize(minimal_resources)
        assert orch.DEFAULT_ARTIFACTS_DIR is not None
        assert orch.STATE_FILE is not None
        assert orch.LOG_FILE is not None

    def test_initialize_builds_iteration_types(self, minimal_resources):
        orch._initialize(minimal_resources)
        wf = orch.ITERATION_TYPES["test_workflow"]
        assert wf["phases"] == ["ALPHA", "BETA", "GAMMA"]
        assert "ALPHA" in wf["required"]
        assert "BETA" in wf["skippable"]

    def test_initialize_builds_phase_agents(self, minimal_resources):
        orch._initialize(minimal_resources)
        assert "ALPHA" in orch.PHASE_AGENTS
        assert orch.PHASE_AGENTS["ALPHA"] == ["researcher"]

    def test_initialize_builds_phase_callables(self, minimal_resources):
        orch._initialize(minimal_resources)
        assert "ALPHA" in orch._PHASE_START
        assert "ALPHA" in orch._PHASE_END
        assert callable(orch._PHASE_START["ALPHA"])

    def test_initialize_builds_auto_action_registry(self, minimal_resources):
        orch._initialize(minimal_resources)
        assert "plan_save" in orch._AUTO_ACTION_REGISTRY
        assert "iteration_advance" in orch._AUTO_ACTION_REGISTRY

    def test_initialize_real_resources(self, auto_build_claw_resources):
        orch._initialize(auto_build_claw_resources)
        assert "full" in orch.ITERATION_TYPES
        assert orch._MODEL.app.name != ""

    def test_reinitialize_clears_old_state(self, minimal_resources, auto_build_claw_resources):
        orch._initialize(minimal_resources)
        assert "test_workflow" in orch.ITERATION_TYPES
        orch._initialize(auto_build_claw_resources)
        assert "test_workflow" not in orch.ITERATION_TYPES
        assert "full" in orch.ITERATION_TYPES


class TestDisplayHelpers:
    """Tests for _msg and _cli display functions."""

    def test_msg_basic(self, minimal_resources):
        orch._initialize(minimal_resources)
        result = orch._msg("no_active")
        assert result == "No active iteration."

    def test_msg_with_kwargs(self, minimal_resources):
        orch._initialize(minimal_resources)
        result = orch._msg("validate_issues", count=3)
        assert "3" in result

    def test_msg_missing_key_returns_key(self, minimal_resources):
        orch._initialize(minimal_resources)
        result = orch._msg("nonexistent_key")
        assert result == "nonexistent_key"

    def test_cli_description(self, minimal_resources):
        orch._initialize(minimal_resources)
        result = orch._cli("description", "")
        assert "Test orchestration CLI" in result

    def test_cli_commands(self, minimal_resources):
        orch._initialize(minimal_resources)
        result = orch._cli("commands", "new")
        assert "Start new iteration" in result


class TestStateManagement:
    """Tests for state persistence functions."""

    def test_now_format(self):
        result = orch._now()
        assert "T" in result
        assert "+" in result or "Z" in result

    def test_yaml_dump_basic(self):
        data = {"key": "value", "number": 42}
        result = orch._yaml_dump(data)
        loaded = yaml.safe_load(result)
        assert loaded == data

    def test_yaml_dump_long_string_wraps(self):
        data = {"text": "a " * 100}
        result = orch._yaml_dump(data)
        assert "|" in result  # literal block style

    def test_load_state_missing_file(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.STATE_FILE = tmp_path / "nonexistent.yaml"
        result = orch._load_state()
        assert result is None

    def test_save_load_state_roundtrip(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        state_file = tmp_path / "state.yaml"
        orch.STATE_FILE = state_file
        state = {"iteration": 1, "type": "test_workflow", "current_phase": "ALPHA"}
        orch._save_state(state)
        loaded = orch._load_state()
        assert loaded["iteration"] == 1
        assert loaded["type"] == "test_workflow"

    def test_load_yaml_list_missing_file(self):
        result = orch._load_yaml_list(Path("/nonexistent/file.yaml"))
        assert result == []

    def test_append_yaml_entry(self, tmp_path):
        path = tmp_path / "entries.yaml"
        orch._append_yaml_entry(path, {"id": 1, "data": "first"})
        orch._append_yaml_entry(path, {"id": 2, "data": "second"})
        entries = orch._load_yaml_list(path)
        assert len(entries) == 2
        assert entries[0]["id"] == 1
        assert entries[1]["id"] == 2

    def test_init_artifacts_dir(self, tmp_path):
        artifacts = tmp_path / "artifacts"
        orch.DEFAULT_ARTIFACTS_DIR = artifacts
        orch._init_artifacts_dir(artifacts)
        assert artifacts.exists()
        assert orch.STATE_FILE == artifacts / "state.yaml"
        assert orch.LOG_FILE == artifacts / "log.yaml"

    def test_clean_artifacts_dir_preserves_context(self, tmp_path):
        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        (artifacts / "state.yaml").write_text("test")
        (artifacts / "context.yaml").write_text("test")
        (artifacts / "other.yaml").write_text("test")
        orch.DEFAULT_ARTIFACTS_DIR = artifacts
        orch._clean_artifacts_dir(artifacts)
        assert not (artifacts / "state.yaml").exists()
        assert not (artifacts / "other.yaml").exists()
        assert (artifacts / "context.yaml").exists()


class TestPhaseNavigation:
    """Tests for phase navigation helpers."""

    def test_next_phase(self, minimal_resources):
        orch._initialize(minimal_resources)
        state = {"type": "test_workflow", "current_phase": "ALPHA"}
        assert orch._next_phase(state) == "BETA"

    def test_next_phase_last(self, minimal_resources):
        orch._initialize(minimal_resources)
        state = {"type": "test_workflow", "current_phase": "GAMMA"}
        assert orch._next_phase(state) is None

    def test_phase_dir_creates_folder(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        state = {"type": "test_workflow", "current_phase": "ALPHA"}
        pdir = orch._phase_dir(state)
        assert pdir.exists()
        assert "phase_01_alpha" in pdir.name


class TestBuildContext:
    """Tests for template context building."""

    def test_build_context_minimal(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch.FAILURES_FILE = tmp_path / "failures.yaml"

        orch.STATE_FILE = tmp_path / "state.yaml"

        state = {
            "iteration": 1,
            "total_iterations": 3,
            "type": "test_workflow",
            "current_phase": "ALPHA",
            "objective": "test objective",
        }
        ctx = orch._build_context(state, phase="ALPHA", event="start")
        assert ctx["objective"] == "test objective"
        assert ctx["iteration"] == 1
        assert ctx["total"] == 3
        assert ctx["remaining"] == 2
        assert "CMD" in ctx

    def test_build_context_with_failures(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch.FAILURES_FILE = tmp_path / "failures.yaml"

        orch.STATE_FILE = tmp_path / "state.yaml"

        failures = [{"mode": "FM-1", "iteration": 1, "description": "test failure"}]
        orch.FAILURES_FILE.write_text(yaml.dump(failures))

        state = {"iteration": 1, "total_iterations": 1, "type": "test_workflow",
                 "current_phase": "ALPHA", "objective": "test"}
        ctx = orch._build_context(state, phase="ALPHA")
        assert "Prior failures" in ctx["prior_context"]


class TestPhaseCallables:
    """Tests for YAML-driven phase template rendering."""

    def test_phase_start_renders_template(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch.STATE_FILE = tmp_path / "state.yaml"
        orch.FAILURES_FILE = tmp_path / "failures.yaml"


        state = {"iteration": 1, "total_iterations": 1, "type": "test_workflow",
                 "current_phase": "ALPHA", "objective": "build something"}
        orch._save_state(state)

        result = orch._PHASE_START["ALPHA"]()
        assert "Start alpha phase" in result
        assert "build something" in result

    def test_phase_end_renders_template(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch.STATE_FILE = tmp_path / "state.yaml"
        orch.FAILURES_FILE = tmp_path / "failures.yaml"


        state = {"iteration": 1, "total_iterations": 1, "type": "test_workflow",
                 "current_phase": "ALPHA", "objective": "test"}
        orch._save_state(state)

        result = orch._PHASE_END["ALPHA"]()
        assert "End alpha phase" in result


class TestLifecycleGateResolution:
    """Tests for _resolve_lifecycle_gate discovering gate names from model metadata."""

    def test_resolve_start_gate(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.STATE_FILE = tmp_path / "state.yaml"
        state = {"type": "test_workflow", "current_phase": "ALPHA"}
        orch._save_state(state)
        gate_key = orch._resolve_lifecycle_gate("ALPHA", "start")
        assert "readback" in gate_key  # discovers readback from start_gate_types

    def test_resolve_end_gate(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.STATE_FILE = tmp_path / "state.yaml"
        state = {"type": "test_workflow", "current_phase": "ALPHA"}
        orch._save_state(state)
        gate_key = orch._resolve_lifecycle_gate("ALPHA", "end")
        assert "gatekeeper" in gate_key  # discovers gatekeeper from end_gate_types

    def test_resolve_unknown_lifecycle_fallback(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.STATE_FILE = tmp_path / "state.yaml"
        state = {"type": "test_workflow", "current_phase": "ALPHA"}
        orch._save_state(state)
        gate_key = orch._resolve_lifecycle_gate("ALPHA", "unknown")
        assert gate_key == "ALPHA::unknown"


class TestPrevImplementable:
    """Tests for _prev_implementable using reject_to from model."""

    def test_fallback_to_first_phase(self, minimal_resources):
        """Without reject_to in any phase, falls back to first phase."""
        orch._initialize(minimal_resources)
        state = {"type": "test_workflow", "current_phase": "GAMMA"}
        result = orch._prev_implementable(state)
        assert result == "ALPHA"  # first phase in workflow


class TestAutoActions:
    """Tests for auto-action dispatch."""

    def test_run_auto_actions_no_actions(self, minimal_resources):
        orch._initialize(minimal_resources)
        state = {"type": "test_workflow", "current_phase": "ALPHA"}
        orch.STATE_FILE = Path("/tmp/nonexistent_state.yaml")
        result = orch._run_auto_actions("ALPHA", state)
        assert result is False


class TestCmdValidate:
    """Tests for the validate command."""

    def test_validate_minimal_model(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        args = argparse.Namespace()
        with pytest.raises(SystemExit) as exc_info:
            orch.cmd_validate(args)
        assert exc_info.value.code == 0

    def test_validate_real_model(self, auto_build_claw_resources, tmp_path):
        orch._initialize(auto_build_claw_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        args = argparse.Namespace()
        with pytest.raises(SystemExit) as exc_info:
            orch.cmd_validate(args)
        assert exc_info.value.code == 0


class TestCmdNew:
    """Tests for the new command."""

    def test_cmd_new_creates_state(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)

        args = argparse.Namespace(
            type="test_workflow",
            objective="build a widget",
            iterations=1,
            benchmark="",
            clean=False,
            dry_run=False,
        )
        orch.cmd_new(args)

        state = orch._load_state()
        assert state is not None
        assert state["objective"] == "build a widget"
        assert state["type"] == "test_workflow"
        assert state["current_phase"] == "ALPHA"
        assert state["phase_status"] == "pending"

    def test_cmd_new_dry_run(self, minimal_resources, tmp_path, capsys):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path

        args = argparse.Namespace(
            type="test_workflow",
            objective="test",
            iterations=1,
            benchmark="",
            clean=False,
            dry_run=True,
        )
        # dry_run prints plan and returns (no sys.exit on success)
        orch.cmd_new(args)
        captured = capsys.readouterr()
        assert "ALPHA" in captured.out
        assert "BETA" in captured.out
        assert "GAMMA" in captured.out


class TestCmdStatus:
    """Tests for the status command."""

    def test_status_no_active(self, minimal_resources, tmp_path, capsys):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch.STATE_FILE = tmp_path / "state.yaml"

        args = argparse.Namespace()
        orch.cmd_status(args)
        captured = capsys.readouterr()
        assert "No active iteration" in captured.out

    def test_status_with_active(self, minimal_resources, tmp_path, capsys):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)

        state = {
            "iteration": 1,
            "total_iterations": 1,
            "type": "test_workflow",
            "objective": "test objective",
            "current_phase": "BETA",
            "phase_status": "in_progress",
            "completed_phases": ["ALPHA"],
            "skipped_phases": [],
            "rejected_count": 0,
            "started_at": "2026-01-01T00:00:00+00:00",
            "phase_outputs": {},
            "phase_agents": {},
        }
        orch._save_state(state)

        args = argparse.Namespace()
        orch.cmd_status(args)
        captured = capsys.readouterr()
        # Minimal fixtures don't have full message templates, so _msg returns
        # the key name when no template is found. Verify status ran and printed
        # the expected message keys (which means the right code paths executed).
        assert "status_header" in captured.out
        assert "status_objective" in captured.out
        assert "status_phase_item" in captured.out


class TestCmdLogFailure:
    """Tests for the log-failure command."""

    def test_log_failure(self, minimal_resources, tmp_path, capsys):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)

        state = {"iteration": 1, "type": "test_workflow", "current_phase": "ALPHA",
                 "phase_status": "in_progress"}
        orch._save_state(state)

        args = argparse.Namespace(mode="FM-TEST", desc="something broke")
        orch.cmd_log_failure(args)

        failures = orch._load_yaml_list(orch.FAILURES_FILE)
        assert len(failures) == 1
        assert failures[0]["mode"] == "FM-TEST"
        assert failures[0]["description"] == "something broke"


class TestIndependentWorkflow:
    """Tests for independent workflow flag."""

    def test_independent_workflow_starts(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        args = argparse.Namespace(
            type="test_workflow", objective="test", iterations=1,
            benchmark="", clean=False, dry_run=False,
        )
        orch.cmd_new(args)
        state = orch._load_state()
        assert state is not None
        assert state["type"] == "test_workflow"

    def test_non_independent_workflow_fails(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        # Mark test_workflow as non-independent
        orch._MODEL.workflow_types["test_workflow"].independent = False
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        args = argparse.Namespace(
            type="test_workflow", objective="test", iterations=1,
            benchmark="", clean=False, dry_run=False,
        )
        with pytest.raises(SystemExit):
            orch.cmd_new(args)


class TestRunUntilComplete:
    """Tests for --iterations 0 (run-until-complete) mode."""

    def test_next_iteration_continues_when_score_nonzero(self, minimal_resources, tmp_path, capsys):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)

        state = {
            "iteration": 1, "total_iterations": 0, "type": "test_workflow",
            "objective": "test", "current_phase": "GAMMA",
            "phase_status": "complete", "completed_phases": ["ALPHA", "BETA", "GAMMA"],
            "skipped_phases": [], "rejected_count": 0, "started_at": "2026-01-01",
            "phase_outputs": {}, "phase_agents": {},
            "benchmark_scores": [{"score": 5}],
        }
        orch._save_state(state)
        orch._run_next_iteration(state)
        assert state["iteration"] == 2  # advanced to next

    def test_next_iteration_stops_when_score_zero(self, minimal_resources, tmp_path, capsys):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)

        state = {
            "iteration": 3, "total_iterations": 0, "type": "test_workflow",
            "objective": "test", "current_phase": "GAMMA",
            "completed_phases": [], "skipped_phases": [], "rejected_count": 0,
            "started_at": "2026-01-01", "phase_outputs": {}, "phase_agents": {},
            "benchmark_scores": [{"score": 5}, {"score": 2}, {"score": 0}],
        }
        orch._save_state(state)
        orch._run_next_iteration(state)
        captured = capsys.readouterr()
        assert "Benchmark conditions met" in captured.out
        assert state["iteration"] == 3  # did NOT advance

    def test_safety_cap_at_20(self, minimal_resources, tmp_path, capsys):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)

        state = {
            "iteration": 20, "total_iterations": 0, "type": "test_workflow",
            "objective": "test", "current_phase": "GAMMA",
            "completed_phases": [], "skipped_phases": [], "rejected_count": 0,
            "started_at": "2026-01-01", "phase_outputs": {}, "phase_agents": {},
            "benchmark_scores": [{"score": 3}],
        }
        orch._save_state(state)
        orch._run_next_iteration(state)
        captured = capsys.readouterr()
        assert "20 iterations" in captured.out


class TestPluginEntrypoint:
    """Tests that the plugin entrypoint resolves correctly."""

    def test_entrypoint_import(self):
        """Verify the engine can be imported from the package."""
        from stellars_claude_code_plugins.engine.orchestrator import main
        assert callable(main)

    def test_entrypoint_file_exists(self):
        """Verify the plugin entrypoint script exists."""
        entrypoint = (
            Path(__file__).resolve().parent.parent
            / "auto-build-claw" / "skills" / "auto-build-claw" / "orchestrate.py"
        )
        assert entrypoint.exists()
        content = entrypoint.read_text()
        assert "from stellars_claude_code_plugins.engine.orchestrator import main" in content
        assert "resources_dir" in content
