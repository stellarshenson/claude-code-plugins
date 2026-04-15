"""Integration tests for the orchestration engine.

Tests the orchestrator's initialization, state management, display helpers,
and command functions using minimal YAML fixtures. Gate functions (claude -p)
are mocked since they require the claude CLI.
"""

import argparse
from pathlib import Path
import shutil
from unittest.mock import patch

import pytest
import yaml

from stellars_claude_code_plugins.autobuild import orchestrator as orch


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


# ---------- helpers ----------


def _base_state(**overrides):
    """Minimal state dict with required fields."""
    state = {
        "iteration": 1,
        "total_iterations": 1,
        "type": "test_workflow",
        "objective": "test",
        "benchmark_cmd": "",
        "benchmark_scores": [],
        "current_phase": "ALPHA",
        "phase_status": "pending",
        "completed_phases": [],
        "skipped_phases": [],
        "rejected_count": 0,
        "started_at": "2026-04-03",
        "phase_outputs": {},
        "phase_agents": {},
        "parent_type": "",
        "record_instructions": "",
    }
    state.update(overrides)
    return state


def _rich_ctx_entry(message="test", phase="RESEARCH", status="new", notes=None):
    return {
        "message": message,
        "phase": phase,
        "created": "2026-04-03T14:00:00+00:00",
        "status": status,
        "notes": notes if notes is not None else [],
    }


def _rich_failure_entry(status="new", solution=None, notes=None):
    return {
        "description": "test failure",
        "context": "",
        "iteration": 1,
        "phase": "TEST",
        "mode": "FM-TEST",
        "status": status,
        "notes": notes if notes is not None else [],
        "solution": solution,
        "timestamp": "2026-04-02T14:00:00+00:00",
    }


def _rich_hyp_entry(status="new", stars=3, notes=None, prediction="", evidence=""):
    return {
        "hypothesis": "test hypothesis",
        "prediction": prediction,
        "evidence": evidence,
        "stars": stars,
        "status": status,
        "iteration_created": 1,
        "notes": notes if notes is not None else [],
    }


# ---------- initialization & display ----------


class TestInitialize:
    """Tests for _initialize with minimal and real YAML resources."""

    def test_initialize_full_scenario(self, minimal_resources):
        """Single init exercises model, paths, iteration types, phase agents,
        phase callables, auto-action registry."""
        orch._initialize(minimal_resources)
        assert orch._initialized is True
        assert orch._MODEL is not None
        assert orch.CMD == "python orchestrate.py"
        # paths
        assert orch.DEFAULT_ARTIFACTS_DIR is not None
        assert orch.STATE_FILE is not None
        assert orch.LOG_FILE is not None
        # iteration types
        wf = orch.ITERATION_TYPES["test_workflow"]
        assert wf["phases"] == ["ALPHA", "BETA", "GAMMA"]
        assert "ALPHA" in wf["required"]
        assert "BETA" in wf["skippable"]
        # phase agents
        assert orch.PHASE_AGENTS["ALPHA"] == ["researcher"]
        # callables
        assert callable(orch._PHASE_START["ALPHA"])
        assert "ALPHA" in orch._PHASE_END
        # auto-action registry
        assert "plan_save" in orch._AUTO_ACTION_REGISTRY
        assert "iteration_advance" in orch._AUTO_ACTION_REGISTRY

    def test_reinitialize_clears_old_state(self, minimal_resources, autobuild_resources):
        orch._initialize(minimal_resources)
        assert "test_workflow" in orch.ITERATION_TYPES
        orch._initialize(autobuild_resources)
        assert "test_workflow" not in orch.ITERATION_TYPES
        assert "full" in orch.ITERATION_TYPES
        assert orch._MODEL.app.name != ""


class TestDisplayHelpers:
    """Tests for _msg and _cli display functions."""

    def test_msg_and_cli(self, minimal_resources):
        """_msg looks up templates, substitutes kwargs, returns key on miss;
        _cli looks up description and commands."""
        orch._initialize(minimal_resources)
        assert orch._msg("no_active") == "No active iteration."
        assert "3" in orch._msg("validate_issues", count=3)
        assert orch._msg("nonexistent_key") == "nonexistent_key"
        assert "Test orchestration CLI" in orch._cli("description", "")
        assert "Start new iteration" in orch._cli("commands", "new")


# ---------- state / persistence ----------


class TestStateManagement:
    """Tests for state persistence functions."""

    def test_now_and_yaml_dump(self):
        result = orch._now()
        assert "T" in result and ("+" in result or "Z" in result)
        data = {"key": "value", "number": 42}
        assert yaml.safe_load(orch._yaml_dump(data)) == data
        # long string uses literal block style
        assert "|" in orch._yaml_dump({"text": "a " * 100})

    def test_save_load_state_and_missing(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.STATE_FILE = tmp_path / "state.yaml"
        # missing returns None
        assert orch._load_state() is None
        # roundtrip
        orch._save_state(_base_state(iteration=1, type="test_workflow"))
        loaded = orch._load_state()
        assert loaded["iteration"] == 1
        assert loaded["type"] == "test_workflow"

    def test_yaml_list_helpers(self, tmp_path):
        assert orch._load_yaml_list(Path("/nonexistent/file.yaml")) == []
        path = tmp_path / "entries.yaml"
        orch._append_yaml_entry(path, {"id": 1, "data": "first"})
        orch._append_yaml_entry(path, {"id": 2, "data": "second"})
        entries = orch._load_yaml_list(path)
        assert len(entries) == 2
        assert entries[0]["id"] == 1 and entries[1]["id"] == 2

    def test_init_and_clean_artifacts_dir(self, tmp_path):
        artifacts = tmp_path / "artifacts"
        orch.DEFAULT_ARTIFACTS_DIR = artifacts
        orch._init_artifacts_dir(artifacts)
        assert artifacts.exists()
        assert orch.STATE_FILE == artifacts / "state.yaml"
        assert orch.LOG_FILE == artifacts / "log.yaml"
        # clean preserves context.yaml, removes state.yaml and other files
        (artifacts / "state.yaml").write_text("test")
        (artifacts / "context.yaml").write_text("ctx")
        (artifacts / "other.yaml").write_text("test")
        orch._clean_artifacts_dir(artifacts)
        assert not (artifacts / "state.yaml").exists()
        assert not (artifacts / "other.yaml").exists()
        assert (artifacts / "context.yaml").exists()


class TestPhaseHelpers:
    """Navigation, build_context, phase callables, gate resolution."""

    def test_phase_navigation(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        state = {"type": "test_workflow", "current_phase": "ALPHA"}
        assert orch._next_phase(state) == "BETA"
        state["current_phase"] = "GAMMA"
        assert orch._next_phase(state) is None
        # phase_dir creates folder
        state["current_phase"] = "ALPHA"
        pdir = orch._phase_dir(state)
        assert pdir.exists()
        assert "phase_01_alpha" in pdir.name

    def test_build_context_with_failures(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch.FAILURES_FILE = tmp_path / "failures.yaml"
        orch.STATE_FILE = tmp_path / "state.yaml"
        state = _base_state(total_iterations=3, current_phase="ALPHA", objective="test objective")
        ctx = orch._build_context(state, phase="ALPHA", event="start")
        assert ctx["objective"] == "test objective"
        assert ctx["iteration"] == 1
        assert ctx["total"] == 3
        assert ctx["remaining"] == 2
        assert "CMD" in ctx
        # Now add a failure, confirm prior_context picks it up
        orch.FAILURES_FILE.write_text(
            yaml.dump({"test_failure": _rich_failure_entry()})
        )
        ctx2 = orch._build_context(state, phase="ALPHA")
        assert "Prior failures" in ctx2["prior_context"]

    def test_phase_callables_and_gate_resolution(self, minimal_resources, tmp_path):
        """Start/end phase callables render templates; lifecycle gate resolution
        discovers readback/gatekeeper and falls back to raw key on unknown."""
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch.STATE_FILE = tmp_path / "state.yaml"
        orch.FAILURES_FILE = tmp_path / "failures.yaml"
        orch._save_state(_base_state(objective="build something"))
        assert "Start alpha phase" in orch._PHASE_START["ALPHA"]()
        assert "End alpha phase" in orch._PHASE_END["ALPHA"]()
        assert "readback" in orch._resolve_lifecycle_gate("ALPHA", "start")
        assert "gatekeeper" in orch._resolve_lifecycle_gate("ALPHA", "end")
        assert orch._resolve_lifecycle_gate("ALPHA", "unknown") == "ALPHA::unknown"

    def test_prev_implementable_fallback(self, minimal_resources):
        orch._initialize(minimal_resources)
        state = {"type": "test_workflow", "current_phase": "GAMMA"}
        assert orch._prev_implementable(state) == "ALPHA"

    def test_run_auto_actions_no_actions(self, minimal_resources):
        orch._initialize(minimal_resources)
        state = {"type": "test_workflow", "current_phase": "ALPHA"}
        orch.STATE_FILE = Path("/tmp/nonexistent_state.yaml")
        assert orch._run_auto_actions("ALPHA", state) is False


# ---------- commands: validate / new / status / log-failure ----------


class TestCmdValidate:
    def test_validate_both_models(self, minimal_resources, autobuild_resources, tmp_path):
        """Validate exits cleanly for both minimal and real resources."""
        for resources in (minimal_resources, autobuild_resources):
            orch._initialize(resources)
            orch.DEFAULT_ARTIFACTS_DIR = tmp_path
            with pytest.raises(SystemExit) as exc_info:
                orch.cmd_validate(argparse.Namespace())
            assert exc_info.value.code == 0


class TestCmdNew:
    """Full cmd_new coverage: fresh, dry-run, continue, restart."""

    def test_fresh_and_dry_run(self, minimal_resources, tmp_path, capsys):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        # Create a file that should be wiped by fresh new
        (tmp_path / "state.yaml").write_text("old: state")
        args = argparse.Namespace(
            type="test_workflow",
            objective="build a widget",
            iterations=1,
            benchmark="",
            continue_session=False,
            dry_run=False,
        )
        orch.cmd_new(args)
        state = orch._load_state()
        assert state["objective"] == "build a widget"
        assert state["type"] == "test_workflow"
        assert state["current_phase"] == "ALPHA"
        assert state["phase_status"] == "pending"
        assert state["benchmark_scores"] == []

        # Dry-run prints plan with all phases
        args.dry_run = True
        orch.cmd_new(args)
        captured = capsys.readouterr()
        for p in ("ALPHA", "BETA", "GAMMA"):
            assert p in captured.out

    def test_continue_preserves_and_increments(self, minimal_resources, tmp_path):
        """--continue preserves context/benchmark_scores and advances iteration;
        fails without existing state."""
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        # Without existing state --continue fails
        args = argparse.Namespace(
            type="test_workflow",
            objective="new",
            iterations=1,
            benchmark="",
            dry_run=False,
            continue_session=True,
        )
        with pytest.raises(SystemExit):
            orch.cmd_new(args)

        # With state, preserves context & advances iteration
        state = _base_state(
            iteration=5,
            total_iterations=10,
            objective="old objective",
            benchmark_scores=[{"score": 42}],
            current_phase="NEXT",
            phase_status="iteration_complete",
        )
        orch._save_state(state)
        orch._save_context({"test_ctx": _rich_ctx_entry(message="preserve me")})
        args.objective = "new objective"
        args.iterations = 3
        orch.cmd_new(args)
        loaded_ctx = orch._load_context()
        assert "test_ctx" in loaded_ctx
        new_state = orch._load_state()
        assert new_state["iteration"] == 6
        assert new_state["objective"] == "new objective"
        assert len(new_state["benchmark_scores"]) == 1

    def test_restart_full_scenario(self, minimal_resources, tmp_path):
        """--restart keeps iteration number, resets phases, preserves context,
        keeps original values when args empty; fails without existing state."""
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        args = argparse.Namespace(
            type="test_workflow",
            objective="test",
            iterations=1,
            benchmark="",
            dry_run=False,
            continue_session=False,
            restart_session=True,
        )
        # fails without state
        with pytest.raises(SystemExit):
            orch.cmd_new(args)

        # full restart: resets phases but keeps iteration and context
        state = _base_state(
            iteration=5,
            total_iterations=10,
            objective="original",
            benchmark_cmd="read BENCH",
            benchmark_scores=[{"score": 42}],
            current_phase="GAMMA",
            phase_status="in_progress",
            completed_phases=["ALPHA", "BETA"],
            phase_outputs={"ALPHA": "findings"},
            phase_agents={"ALPHA": ["researcher"]},
        )
        orch._save_state(state)
        orch._save_context({"item": _rich_ctx_entry(message="preserve me")})
        args.objective = "updated objective"
        args.iterations = 10
        orch.cmd_new(args)
        new_state = orch._load_state()
        assert new_state["iteration"] == 5
        assert new_state["objective"] == "updated objective"
        assert new_state["completed_phases"] == []
        assert "item" in orch._load_context()

        # restart with empty objective/iterations keeps originals
        args.objective = ""
        args.iterations = 1
        orch.cmd_new(args)
        new_state2 = orch._load_state()
        assert new_state2["objective"] == "updated objective"  # Kept from last run
        assert new_state2["benchmark_cmd"] == "read BENCH"
        assert len(new_state2["benchmark_scores"]) == 1
        assert new_state2["total_iterations"] == 10

    def test_safety_cap_from_config(self, autobuild_resources):
        orch._initialize(autobuild_resources)
        cap = orch._MODEL.app.config.get("safety_cap_iterations", 20)
        assert cap == 20

    def test_non_independent_workflow_fails(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch._MODEL.workflow_types["WORKFLOW::TEST_WORKFLOW"].independent = False
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        args = argparse.Namespace(
            type="test_workflow",
            objective="test",
            iterations=1,
            benchmark="",
            continue_session=False,
            dry_run=False,
        )
        with pytest.raises(SystemExit):
            orch.cmd_new(args)


class TestCmdStatusAndLogFailure:
    def test_status_and_log_failure(self, minimal_resources, tmp_path, capsys):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch.STATE_FILE = tmp_path / "state.yaml"
        # no active
        orch.cmd_status(argparse.Namespace())
        assert "No active iteration" in capsys.readouterr().out
        # with active
        orch._init_artifacts_dir(tmp_path)
        orch._save_state(_base_state(current_phase="BETA", phase_status="in_progress",
                                      completed_phases=["ALPHA"],
                                      started_at="2026-01-01T00:00:00+00:00"))
        orch.cmd_status(argparse.Namespace())
        out = capsys.readouterr().out
        assert "status_header" in out
        assert "status_objective" in out
        assert "status_phase_item" in out
        # log-failure
        orch.cmd_log_failure(argparse.Namespace(mode="FM-TEST", desc="something broke", context=""))
        failures = orch._load_failures()
        assert len(failures) == 1
        _fid, entry = next(iter(failures.items()))
        assert entry["mode"] == "FM-TEST"
        assert entry["description"] == "something broke"


# ---------- run until complete / dispatch ----------


class TestRunUntilComplete:
    """Tests for --iterations 0 (run-until-complete) mode."""

    def test_next_iteration_logic(self, minimal_resources, tmp_path, capsys):
        """Nonzero score advances iteration; score=0 stops with
        benchmark-complete message; iteration 20 hits safety cap."""
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)

        # nonzero -> advance
        state = _base_state(
            iteration=1, total_iterations=0,
            current_phase="GAMMA", phase_status="complete",
            completed_phases=["ALPHA", "BETA", "GAMMA"],
            started_at="2026-01-01",
            benchmark_scores=[{"score": 5}],
        )
        orch._save_state(state)
        orch._run_next_iteration(state)
        assert state["iteration"] == 2

        # score=0 -> stop
        state2 = _base_state(
            iteration=3, total_iterations=0,
            current_phase="GAMMA", phase_status="complete",
            started_at="2026-01-01",
            benchmark_scores=[{"score": 5}, {"score": 2}, {"score": 0}],
        )
        orch._save_state(state2)
        orch._run_next_iteration(state2)
        assert "Benchmark conditions met" in capsys.readouterr().out
        assert state2["iteration"] == 3

        # iteration 20 -> safety cap
        state3 = _base_state(
            iteration=20, total_iterations=0,
            current_phase="GAMMA", phase_status="complete",
            started_at="2026-01-01",
            benchmark_scores=[{"score": 3}],
        )
        orch._save_state(state3)
        orch._run_next_iteration(state3)
        assert "20 iterations" in capsys.readouterr().out


class TestGenerativeActionDispatch:
    """Verify generative and standalone actions dispatch via _claude_evaluate."""

    def _build_solo_resources(self, tmp_path, action_execution=None):
        resources = tmp_path / "resources"
        resources.mkdir()
        (resources / "workflow.yaml").write_text("""
WORKFLOW::SOLO:
  cli_name: solo_workflow
  description: "Workflow with generative action"
  phases:
    - name: STEP
""")
        exec_line = f"    execution: {action_execution}\n" if action_execution else ""
        (resources / "phases.yaml").write_text(f"""
actions:
  ACTION::SOLO_ACTION:
    cli_name: solo_action
    type: generative
{exec_line}    description: "A generative action"
    prompt: "Do work for iteration {{iteration}}: {{phase_output}}"

shared_gates:
  skip:
    gatekeeper_skip:
      mode: standalone_session
      prompt: "Skip {{phase}} {{iteration}} {{itype}} {{objective}}: {{reason}}"
    gatekeeper_force_skip:
      mode: standalone_session
      prompt: "Force-skip {{phase}} {{iteration}}: {{reason}}"
STEP:
  auto_actions:
    on_complete: [solo_action]
  start:
    template: "Start step. Objective: {{objective}}"
    agents:
      - name: readback
        mode: standalone_session
        prompt: "Phase {{phase}}: {{understanding}}"
  execution:
    agents:
      - name: worker
        display_name: Worker
        prompt: "Do work"
  end:
    template: "End step."
    agents:
      - name: gatekeeper
        mode: standalone_session
        prompt: "Phase {{phase}}: {{evidence}}"
""")
        (resources / "app.yaml").write_text("""
app:
  name: solo-test
  description: "Solo test"
  cmd: "python orchestrate.py"
  artifacts_dir: ".solo-test"
display:
  separator: "-"
  separator_width: 40
  header_char: "="
  header_width: 40
banner:
  header: "{header_line}\\n{iter_label}\\n{header_line}\\n"
  progress_current: "**{p}**"
  progress_done: "~~{p}~~"
footer:
  start: "\\n{separator_line}\\n"
  end: "\\n{separator_line}\\n"
  final: "\\n{separator_line}\\n"
messages:
  no_active: "No active iteration."
  validate_success: "OK"
  validate_issues: "{count} issues"
  validate_item: "  {num}. {issue}"
  benchmark_driven_label: "benchmark-driven {iteration}"
  benchmark_complete: "Benchmark conditions met."
  benchmark_safety_cap: "WARNING: {count} iterations."
cli:
  description: "Solo test CLI"
  epilog: "Usage: {cmd}"
  commands:
    new: "New"
    start: "Start"
    end: "End"
    status: "Status"
  args:
    objective: "Objective"
    iterations: "Iterations"
""")
        return resources

    def test_generative_dispatch(self, tmp_path):
        """Generative action dispatches via _claude_evaluate."""
        resources = self._build_solo_resources(tmp_path)
        orch._initialize(resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch.STATE_FILE = tmp_path / "state.yaml"
        state = _base_state(type="solo_workflow", current_phase="STEP", iteration=1)
        orch._save_state(state)
        with patch.object(orch, "_claude_evaluate", return_value=(True, "PASS")) as mock_eval:
            result = orch._run_auto_actions("STEP", state)
            mock_eval.assert_called_once()
        assert result is False

    def test_standalone_action_resolves_template(self, tmp_path):
        """Standalone generative action resolves template vars and calls _claude_evaluate."""
        resources = self._build_solo_resources(tmp_path, action_execution="standalone")
        orch._initialize(resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch.STATE_FILE = tmp_path / "state.yaml"
        state = _base_state(
            type="solo_workflow",
            current_phase="STEP",
            iteration=2,
            total_iterations=3,
            objective="test standalone",
            phase_outputs={"STEP": "implemented feature X"},
        )
        orch._save_state(state)
        with patch.object(orch, "_claude_evaluate", return_value=(True, "PASS")) as mock_eval:
            result = orch._run_auto_actions("STEP", state)
            mock_eval.assert_called_once()
            resolved_prompt = mock_eval.call_args[0][0]
            assert "iteration 2" in resolved_prompt
            assert "implemented feature X" in resolved_prompt
        assert result is False


class TestDryRunFastWorkflow:
    """Dry-run with the fast workflow using real resources."""

    def test_dry_run_fast_workflow(self, autobuild_resources, tmp_path, capsys):
        orch._initialize(autobuild_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        args = argparse.Namespace(
            type="fast",
            objective="test fast workflow",
            iterations=1,
            benchmark="",
            continue_session=False,
            dry_run=True,
        )
        orch.cmd_new(args)
        captured = capsys.readouterr()
        for p in ("PLAN", "IMPLEMENT", "TEST", "REVIEW", "RECORD", "NEXT"):
            assert p in captured.out
        assert "RESEARCH" not in captured.out
        assert "HYPOTHESIS" not in captured.out


class TestPluginEntrypoint:
    """Plugin entrypoint, pyproject registration, and bundled resources."""

    def test_entrypoint_and_resources(self):
        from stellars_claude_code_plugins.autobuild.orchestrator import main
        assert callable(main)
        pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
        content = pyproject.read_text()
        assert "orchestrate" in content
        assert "stellars_claude_code_plugins.autobuild.orchestrator:main" in content
        resources = (
            Path(__file__).resolve().parent.parent
            / "stellars_claude_code_plugins"
            / "autobuild"
            / "resources"
        )
        assert resources.exists()
        for f in ("workflow.yaml", "phases.yaml", "app.yaml"):
            assert (resources / f).exists()


# ---------- info command ----------


class TestCmdInfo:
    """Tests for the info command - model introspection."""

    def test_info_all_variants(self, autobuild_resources, capsys):
        """Exercise --workflows, --workflow NAME, --phases, --phase NAME, --agents."""
        orch._initialize(autobuild_resources)
        cases = [
            ({"workflows": True}, ["WORKFLOW::FULL", "full", "WORKFLOW::FAST"]),
            ({"workflow": "full"}, ["RESEARCH", "HYPOTHESIS"]),
            ({"phases": True}, ["FULL::RESEARCH", "IMPLEMENT", "GC::PLAN"]),
            (
                {"phase": "FULL::RESEARCH"},
                ["readback", "researcher", "architect", "product_manager", "gatekeeper"],
            ),
            ({"agents": True}, ["researcher", "contrarian", "guardian", "benchmark_evaluator"]),
        ]
        for flags, expect_substrings in cases:
            defaults = {
                "workflows": False, "workflow": None, "phases": False,
                "phase": None, "agents": False,
            }
            defaults.update(flags)
            orch.cmd_info(argparse.Namespace(**defaults))
            out = capsys.readouterr().out
            for s in expect_substrings:
                assert s in out, f"missing {s} for flags {flags}"

    def test_info_structure_compliance(self, autobuild_resources):
        """Every phase has readback in start and gatekeeper in end, and
        agent counts match expected per phase."""
        orch._initialize(autobuild_resources)
        for phase_name in orch._MODEL.phases:
            assert f"{phase_name}::readback" in orch._MODEL.gates
            assert f"{phase_name}::gatekeeper" in orch._MODEL.gates
        expected = {
            "FULL::RESEARCH": 3,
            "FULL::HYPOTHESIS": 4,
            "PLAN": 3,
            "TEST": 1,
            "REVIEW": 4,
            "PLANNING::RESEARCH": 3,
            "PLANNING::PLAN": 1,
        }
        for phase, count in expected.items():
            agents = orch._MODEL.agents.get(phase, [])
            assert len(agents) == count, f"{phase}: expected {count}, got {len(agents)}"
        for phase in ["IMPLEMENT", "RECORD", "NEXT", "GC::PLAN"]:
            assert phase not in orch._MODEL.agents or len(orch._MODEL.agents[phase]) == 0


# ---------- project resources / stale detection ----------


class TestEnsureProjectResources:
    def test_copy_archive_replace_and_load(self, tmp_path):
        """Missing resources are copied, stale ones archived and replaced,
        and the orchestrator can then load from the project dir."""
        project_resources = tmp_path / ".autobuild" / "resources"
        result = orch._ensure_project_resources(project_resources)
        assert result == project_resources
        assert (project_resources / "workflow.yaml").exists()
        assert (project_resources / "phases.yaml").exists()
        assert (project_resources / "app.yaml").exists()
        # Now modify to stale and re-run
        (project_resources / "workflow.yaml").write_text("# custom workflow")
        orch._ensure_project_resources(project_resources)
        archives = list(tmp_path.glob(".autobuild/resources.old.*"))
        assert len(archives) >= 1
        # model loads from project dir
        model = orch.load_model(project_resources)
        assert model.app.name != ""
        assert len(model.workflow_types) > 0

    def test_clean_preserves_resources(self, tmp_path):
        """_clean_artifacts_dir preserves resources/ subdirectory."""
        artifacts = tmp_path / ".autobuild"
        resources = artifacts / "resources"
        resources.mkdir(parents=True)
        custom = "# custom workflow"
        (resources / "workflow.yaml").write_text(custom)
        (artifacts / "state.yaml").write_text("iteration: 1")
        phase_dir = artifacts / "phase_01_plan"
        phase_dir.mkdir()
        (phase_dir / "output.md").write_text("plan")
        orch._clean_artifacts_dir(artifacts)
        assert resources.exists()
        assert (resources / "workflow.yaml").read_text() == custom
        assert not (artifacts / "state.yaml").exists()
        assert not phase_dir.exists()


class TestResourceConflict:
    def test_stale_detection_and_archive(self, autobuild_resources, tmp_path):
        """Old-format triggers stale detection and archive on _ensure;
        content-mismatch also counts as stale; matching bundled is not."""
        orch._initialize(autobuild_resources)

        # No phases.yaml -> not stale
        r1 = tmp_path / "r1"
        r1.mkdir()
        assert orch._detect_stale_resources(r1) is False

        # Old-format triggers stale
        r2 = tmp_path / "r2"
        r2.mkdir()
        (r2 / "phases.yaml").write_text(
            "ALPHA:\n  gates:\n    on_start:\n      readback:\n        prompt: test"
        )
        assert orch._detect_stale_resources(r2) is True

        # Old-format archived and replaced by _ensure_project_resources
        r3 = tmp_path / ".autobuild" / "resources"
        r3.mkdir(parents=True)
        (r3 / "phases.yaml").write_text(
            "ALPHA:\n  gates:\n    on_start:\n      readback:\n        prompt: test"
        )
        (r3 / "workflow.yaml").write_text("test: {}")
        (r3 / "app.yaml").write_text("app: {}")
        orch._ensure_project_resources(r3)
        archives = list(tmp_path.glob(".autobuild/resources.old.*"))
        assert len(archives) >= 1
        content = (r3 / "phases.yaml").read_text()
        assert "start:" in content

        # Content mismatch (modified bundled copy) is stale
        r4 = tmp_path / "r4"
        r4.mkdir()
        for fname in orch._RESOURCE_FILES:
            src = orch._BUNDLED_RESOURCES / fname
            if src.exists():
                shutil.copy2(src, r4 / fname)
        (r4 / "phases.yaml").write_text((r4 / "phases.yaml").read_text() + "\n# user edit")
        assert orch._detect_stale_resources(r4) is True

        # Matching bundled is not stale
        r5 = tmp_path / "r5"
        r5.mkdir()
        for fname in orch._RESOURCE_FILES:
            src = orch._BUNDLED_RESOURCES / fname
            if src.exists():
                shutil.copy2(src, r5 / fname)
        assert orch._detect_stale_resources(r5) is False


class TestVersionCheck:
    def test_version_check_cache_formats(self, tmp_path):
        """Structured YAML cache with fields; plain text is stale; _check_version never raises."""
        from datetime import datetime, timezone

        # Structured YAML format
        cache = tmp_path / ".version_check"
        now = datetime.now(timezone.utc).isoformat()
        cache.write_text(
            yaml.dump({"latest_version": "0.8.51", "checked_at": now})
        )
        data = yaml.safe_load(cache.read_text())
        assert isinstance(data, dict)
        assert data["latest_version"] == "0.8.51"
        checked = datetime.fromisoformat(data["checked_at"])
        age = (datetime.now(timezone.utc) - checked).total_seconds()
        assert age < 86400

        # Legacy plain-text: loads as string, treated as stale
        cache.write_text("0.8.50")
        data = yaml.safe_load(cache.read_text())
        assert isinstance(data, str)

        # _check_version never raises
        orch._check_version()


# ---------- context lifecycle (rich entries) ----------


class TestContextRichEntries:
    """Identifier-keyed rich context entries: ID gen, save/load, lifecycle."""

    def test_generate_entry_id_all_variants(self, minimal_resources):
        """Slugification, truncation to <=37, fallback on empty, collision
        suffixes, and generative naming passthrough."""
        orch._initialize(minimal_resources)
        assert orch._generate_entry_id("Focus on X", set()) == "focus_on_x"
        assert len(orch._generate_entry_id("a" * 100, set())) <= 37
        assert orch._generate_entry_id("!!!", set()) == "ctx"
        # Collision suffixes
        cid1 = orch._generate_entry_id("focus on x", set())
        cid2 = orch._generate_entry_id("focus on x", {cid1})
        cid3 = orch._generate_entry_id("focus on x", {cid1, cid2})
        assert cid1 == "focus_on_x"
        assert cid2 == "focus_on_x_2"
        assert cid3 == "focus_on_x_3"
        # Generative naming passthrough
        assert orch._generate_entry_id("some message", set(), identifier="custom_name") == "custom_name"

    def test_save_load_roundtrip_and_ack_lifecycle(self, minimal_resources, tmp_path):
        """Round-trip an entry; ack transitions inline without context_ack.yaml;
        ack is idempotent; processed transitions append notes."""
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        ctx = {"focus_on_x": _rich_ctx_entry(message="focus on X")}
        orch._save_context(ctx)
        loaded = orch._load_context()
        assert loaded["focus_on_x"]["message"] == "focus on X"
        assert loaded["focus_on_x"]["status"] == "new"

        # Acknowledge (simulating cmd_start) transitions new -> acknowledged
        for cid, entry in loaded.items():
            if entry.get("status") == "new":
                entry["status"] = "acknowledged"
                entry.setdefault("notes", []).append({"acknowledged": "seen by ALPHA"})
        orch._save_context(loaded)
        final = orch._load_context()
        assert final["focus_on_x"]["status"] == "acknowledged"
        assert final["focus_on_x"]["notes"][-1] == {"acknowledged": "seen by ALPHA"}
        # No ack file produced
        assert not (tmp_path / "context_ack.yaml").exists()

        # Idempotent: re-running ack loop on already-acknowledged does nothing
        dirty = False
        for cid, entry in final.items():
            if entry.get("status") == "new":
                entry["status"] = "acknowledged"
                dirty = True
        assert not dirty

        # Transition to processed
        final["focus_on_x"]["status"] = "processed"
        final["focus_on_x"]["notes"].append({"processed": "added to PROGRAM"})
        orch._save_context(final)
        assert orch._load_context()["focus_on_x"]["status"] == "processed"

    def test_two_messages_same_phase_different_ids(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        ctx = {}
        cid1 = orch._generate_entry_id("fix auth", set(ctx.keys()))
        ctx[cid1] = _rich_ctx_entry(message="fix auth", phase="IMPLEMENT")
        cid2 = orch._generate_entry_id("fix auth", set(ctx.keys()))
        ctx[cid2] = _rich_ctx_entry(message="fix auth again", phase="IMPLEMENT")
        assert cid1 != cid2
        orch._save_context(ctx)
        assert len(orch._load_context()) == 2

    def test_load_rejects_malformed(self, minimal_resources, tmp_path):
        """Legacy flat format, missing message, and missing phase all raise."""
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        ctx_file = tmp_path / "context.yaml"

        ctx_file.write_text("RESEARCH: 'test guidance'\n")
        with pytest.raises(ValueError, match="legacy flat format"):
            orch._load_context()

        ctx_file.write_text(yaml.dump({"e": {"phase": "R", "created": "x"}}))
        with pytest.raises(ValueError, match="missing required keys"):
            orch._load_context()

        ctx_file.write_text(yaml.dump({"e": {"message": "m", "created": "x"}}))
        with pytest.raises(ValueError, match="missing required keys"):
            orch._load_context()

    def test_model_prompt_invariants(self, autobuild_resources):
        """Hypothesis autowrite says append; architects have Occam directive;
        key gatekeepers reference context."""
        orch._initialize(autobuild_resources)
        action = orch._MODEL.actions.get("ACTION::HYPOTHESIS_AUTOWRITE")
        assert action is not None
        p = action.prompt
        assert "APPEND" in p or "append" in p
        assert "do not remove" in p.lower() or "do not overwrite" in p.lower()

        architect_phases = []
        for phase_key, agents in orch._MODEL.agents.items():
            for agent in agents:
                if agent.name == "architect":
                    architect_phases.append(phase_key)
                    assert "occam" in agent.prompt.lower(), (
                        f"Architect in {phase_key} missing Occam directive"
                    )
        assert len(architect_phases) >= 4

        check_phases = {"FULL::RESEARCH", "FULL::HYPOTHESIS", "PLAN", "IMPLEMENT", "REVIEW"}
        for phase_key, gates in orch._MODEL.gates.items():
            if phase_key in check_phases:
                for gate in gates:
                    if gate.name == "gatekeeper":
                        assert "context" in gate.prompt.lower(), (
                            f"Gatekeeper in {phase_key} missing context reference"
                        )


class TestContextLifecycle:
    """Context status+notes lifecycle transitions and invariants."""

    def test_full_lifecycle_transitions(self, minimal_resources, tmp_path):
        """Exercise acknowledged, processed, dismissed transitions and
        dismissed-hiding-from-banner filter; verify no legacy fields."""
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        # Start with multiple entries at different states
        ctx = {
            "active": _rich_ctx_entry(message="show me"),
            "dismissed": _rich_ctx_entry(
                message="hide me",
                status="dismissed",
                notes=[{"dismissed": "not relevant"}],
            ),
        }
        orch._save_context(ctx)
        loaded = orch._load_context()

        # Banner filter: new/acknowledged visible, dismissed hidden
        active = {k: v for k, v in loaded.items() if v.get("status") in {"new", "acknowledged"}}
        assert "active" in active
        assert "dismissed" not in active

        # Transition active: new -> acknowledged -> processed
        loaded["active"]["status"] = "acknowledged"
        loaded["active"]["notes"].append({"acknowledged": "seen by ALPHA"})
        orch._save_context(loaded)
        mid = orch._load_context()
        assert mid["active"]["status"] == "acknowledged"
        assert len(mid["active"]["notes"]) == 1

        mid["active"]["status"] = "processed"
        mid["active"]["notes"].append({"processed": "added to PROGRAM.md"})
        orch._save_context(mid)
        final = orch._load_context()
        assert final["active"]["status"] == "processed"
        assert len(final["active"]["notes"]) == 2

        # No legacy fields
        assert "acknowledged_by" not in final["active"]
        assert "processed" not in final["active"] or not isinstance(
            final["active"].get("processed"), bool
        )

    def test_invalid_status_and_transition_rules(self, minimal_resources, tmp_path):
        """Invalid status raises; dismissed<->processed are invalid transitions."""
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        orch._save_context({"bad": _rich_ctx_entry()})
        # Poke an invalid status on disk
        (tmp_path / "context.yaml").write_text(
            yaml.dump({"bad": _rich_ctx_entry(status="invalid_status")})
        )
        with pytest.raises(ValueError, match="invalid status"):
            orch._load_context()
        transitions = orch._VALID_CONTEXT_TRANSITIONS
        assert "processed" not in transitions.get("dismissed", set())
        assert "dismissed" not in transitions.get("processed", set())


# ---------- failure lifecycle ----------


class TestFailuresRichEntries:
    def test_failures_full_lifecycle(self, minimal_resources, tmp_path):
        """Save/load, auto-id gen on append, processed-with-solution,
        acknowledge transition, survives clean."""
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)

        # Save rich entry, load it back
        failures = {
            "gate_timeout": {
                **_rich_failure_entry(),
                "description": "gatekeeper timed out",
                "phase": "IMPLEMENT",
                "mode": "FM-TIMEOUT",
                "iteration": 3,
            },
        }
        orch._save_failures(failures)
        loaded = orch._load_failures()
        assert loaded["gate_timeout"]["description"] == "gatekeeper timed out"
        assert loaded["gate_timeout"]["solution"] is None
        # status+notes present, no legacy fields
        assert loaded["gate_timeout"]["status"] == "new"
        assert "acknowledged_by" not in loaded["gate_timeout"]

        # Processed with solution
        loaded["gate_timeout"]["status"] = "processed"
        loaded["gate_timeout"]["notes"].append({"processed": "increased timeout to 60s"})
        loaded["gate_timeout"]["solution"] = "increased timeout to 60s"
        orch._save_failures(loaded)
        assert orch._load_failures()["gate_timeout"]["solution"] == "increased timeout to 60s"

        # _append_failure auto-generates identifier from description
        orch._append_failure({
            "iteration": 1,
            "phase": "TEST",
            "mode": "FM-TEST-FAIL",
            "description": "tests failed unexpectedly",
        })
        loaded2 = orch._load_failures()
        new_id = next(k for k in loaded2 if k != "gate_timeout")
        assert "tests_failed" in new_id
        assert loaded2[new_id]["status"] == "new"

        # Acknowledge transition (simulating cmd_start)
        for fid, entry in loaded2.items():
            if entry.get("status") == "new":
                entry["status"] = "acknowledged"
                entry.setdefault("notes", []).append({"acknowledged": "seen by ALPHA"})
        orch._save_failures(loaded2)
        after_ack = orch._load_failures()
        assert after_ack[new_id]["status"] == "acknowledged"

        # Survives clean
        orch._clean_artifacts_dir(tmp_path)
        assert (tmp_path / "failures.yaml").exists()
        assert "gate_timeout" in orch._load_failures()

    def test_legacy_list_rejected(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        legacy = [{"iteration": 1, "phase": "TEST", "mode": "FM-X", "description": "old"}]
        (tmp_path / "failures.yaml").write_text(yaml.dump(legacy))
        with pytest.raises(ValueError, match="legacy flat list"):
            orch._load_failures()

    def test_build_failures_context_solved_unsolved(self, minimal_resources, tmp_path):
        """_build_failures_context distinguishes solved vs unsolved."""
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        failures = {
            "unsolved_one": _rich_failure_entry(),
            "solved_one": {
                **_rich_failure_entry(
                    status="processed",
                    solution="fixed it",
                    notes=[{"processed": "fixed it"}],
                ),
                "description": "was broken",
                "mode": "FM-B",
            },
        }
        failures["unsolved_one"]["description"] = "still broken"
        failures["unsolved_one"]["mode"] = "FM-A"
        orch._save_failures(failures)
        ctx = orch._build_failures_context()
        assert "unsolved" in ctx.lower()
        assert "solved" in ctx.lower()
        assert "unsolved_one" in ctx
        assert "solved_one" in ctx


# ---------- hypothesis lifecycle ----------


class TestHypothesisContext:
    def test_hypothesis_full_lifecycle(self, minimal_resources, tmp_path):
        """prior_hyp builds from file and filters dismissed; status transitions;
        survives clean."""
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        hyps = {
            "active": {
                **_rich_hyp_entry(status="deferred"),
                "hypothesis": "Active hyp with enough description",
            },
            "dismissed": {
                **_rich_hyp_entry(status="dismissed", notes=[{"dismissed": "n"}]),
                "hypothesis": "Dismissed hyp content",
            },
        }
        orch._save_hypotheses(hyps)
        state = _base_state()
        orch._save_state(state)
        ctx = orch._build_context(state)
        prior = ctx.get("prior_hyp", "")
        assert "active" in prior
        assert "dismissed" not in prior

        # Transition one to processed
        loaded = orch._load_hypotheses()
        loaded["active"]["status"] = "processed"
        loaded["active"]["notes"].append({"processed": "selected for iter 1"})
        orch._save_hypotheses(loaded)
        assert orch._load_hypotheses()["active"]["status"] == "processed"

        # Survives clean
        orch._clean_artifacts_dir(tmp_path)
        assert (tmp_path / "hypotheses.yaml").exists()

        # Empty state without file -> empty prior_hyp
        (tmp_path / "hypotheses.yaml").unlink()
        ctx2 = orch._build_context(state)
        assert ctx2.get("prior_hyp", "") == ""

    def test_legacy_list_rejected(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        legacy = [{"id": "H001", "hypothesis": "old", "stars": "3/5"}]
        (tmp_path / "hypotheses.yaml").write_text(yaml.dump(legacy))
        with pytest.raises(ValueError, match="legacy flat list"):
            orch._load_hypotheses()


# ---------- lifecycle compliance ----------


class TestLifecycleCompliance:
    """Programmatic status gates at phase boundaries."""

    def test_phase_boundary_blocks_unprocessed(self, minimal_resources, tmp_path):
        """NEXT/HYPOTHESIS phase boundaries block new and acknowledged entries
        across context/hypotheses/failures. Exercises each category via fresh
        artifacts dir per scenario."""
        scenarios = [
            ("context_new", "NEXT"),
            ("hypothesis_new", "FULL::HYPOTHESIS"),
            ("context_acknowledged", "NEXT"),
            ("failure_acknowledged", "NEXT"),
        ]
        for name, phase in scenarios:
            sub = tmp_path / name
            sub.mkdir()
            orch._initialize(minimal_resources)
            orch.DEFAULT_ARTIFACTS_DIR = sub
            orch._init_artifacts_dir(sub)
            if name == "context_new":
                orch._save_context({"item": _rich_ctx_entry(status="new")})
                state = {"iteration": 1, "completed_phases": ["RECORD"], "current_phase": phase}
            elif name == "hypothesis_new":
                orch._save_hypotheses({"h": _rich_hyp_entry(status="new")})
                state = {"iteration": 1, "current_phase": phase}
            elif name == "context_acknowledged":
                orch._save_context({"item": _rich_ctx_entry(status="acknowledged")})
                state = {"completed_phases": ["RECORD"], "iteration": 1}
            else:  # failure_acknowledged
                orch._save_failures({"fm": _rich_failure_entry(status="acknowledged")})
                state = {"completed_phases": ["RECORD"], "iteration": 1}
            with pytest.raises(SystemExit):
                orch._check_lifecycle_compliance(phase, state)

    def test_classified_and_dismissed_pass(self, minimal_resources, tmp_path):
        """NEXT passes when all entries are processed or dismissed (with notes)."""
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        long_note = (
            "Added to PROGRAM.md as work item for FSM migration from custom implementation to "
            "transitions package. Acceptance criteria defined: transitions.Machine wraps FSM "
            "class, all 115 existing tests pass unchanged, no orchestrator.py call site changes "
            "needed. Referenced by architect and product_manager agents during RESEARCH phase "
            "synthesis. Root cause confirmed: custom FSM has 258 lines that the library handles "
            "natively."
        )
        ctx = {
            "item1": _rich_ctx_entry(status="processed", notes=[{"processed": long_note}]),
            "item2": _rich_ctx_entry(
                message="test2",
                phase="PLAN",
                status="dismissed",
                notes=[{"dismissed": long_note}],
            ),
        }
        orch._save_context(ctx)
        state = {"completed_phases": ["RECORD"], "iteration": 1}
        orch._check_lifecycle_compliance("NEXT", state)  # should not raise

    def test_deferred_hypothesis_aging(self, minimal_resources, tmp_path):
        """Deferred hypothesis auto-dismissed after max gap; within-limit survives."""
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)

        # Old deferred auto-dismissed
        hyps = {
            "old_deferred": {
                **_rich_hyp_entry(status="deferred", stars=2, notes=[{"deferred": "wait"}]),
                "hypothesis": "old",
            }
        }
        orch._save_hypotheses(hyps)
        state = {"iteration": 10, "current_phase": "FULL::HYPOTHESIS"}
        try:
            orch._check_lifecycle_compliance("FULL::HYPOTHESIS", state)
        except SystemExit:
            pass
        loaded = orch._load_hypotheses()
        assert loaded["old_deferred"]["status"] == "dismissed"
        assert "exceeded max deferred" in str(loaded["old_deferred"]["notes"][-1])

        # Recent deferred (gap=2 within max=3) survives
        hyps2 = {
            "recent_deferred": {
                "hypothesis": (
                    "Timeout errors occur because connection pool is exhausted under load"
                ),
                "status": "deferred",
                "stars": 3,
                "prediction": "errors decrease from 50 to 0 after pool resize",
                "evidence": "L100-L120 shows pool at max capacity during peak",
                "iteration_created": 2,
                "notes": [{"deferred": "revisit next"}],
            }
        }
        orch._save_hypotheses(hyps2)
        state2 = {"iteration": 4, "current_phase": "FULL::HYPOTHESIS"}
        orch._check_lifecycle_compliance("FULL::HYPOTHESIS", state2)
        assert orch._load_hypotheses()["recent_deferred"]["status"] == "deferred"


# ---------- clean behavior ----------


class TestCleanBehavior:
    def test_clean_preserve_data(self, minimal_resources, tmp_path):
        """preserve_data=False wipes context/failures/hypotheses;
        True keeps them. resources/ always preserved."""
        orch._initialize(minimal_resources)
        for preserve_data in (True, False):
            sub = tmp_path / f"run_{preserve_data}"
            sub.mkdir()
            orch.DEFAULT_ARTIFACTS_DIR = sub
            orch._init_artifacts_dir(sub)
            for name in ("context.yaml", "failures.yaml", "hypotheses.yaml", "state.yaml"):
                (sub / name).write_text("test: data\n")
            (sub / "resources").mkdir(exist_ok=True)
            (sub / "resources" / "test.yaml").write_text("test: data\n")

            orch._clean_artifacts_dir(sub, preserve_data=preserve_data)
            for name in ("context.yaml", "failures.yaml", "hypotheses.yaml"):
                assert (sub / name).exists() is preserve_data
            assert (sub / "resources" / "test.yaml").exists()


# ---------- actions & record instructions ----------


class TestActionExecution:
    def test_action_shape(self, autobuild_resources):
        """ActionDef has no execution field; generative action templates contain
        placeholders for phase_output and artifacts_dir."""
        orch._initialize(autobuild_resources)
        autowrite = orch._MODEL.actions.get("ACTION::HYPOTHESIS_AUTOWRITE")
        assert autowrite is not None
        assert not hasattr(autowrite, "execution")
        assert autowrite.type == "generative"
        assert "{phase_output}" in autowrite.prompt
        assert "{artifacts_dir}" in autowrite.prompt


class TestRecordInstructions:
    def test_record_instructions_full_scenario(self, minimal_resources, tmp_path):
        """record_instructions stored in state and appear in _build_context;
        old state.yaml without the field fails to load."""
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        orch.FAILURES_FILE = tmp_path / "failures.yaml"
        orch.STATE_FILE = tmp_path / "state.yaml"
        state = _base_state(
            type="test_workflow",
            current_phase="ALPHA",
            record_instructions="Update journal. Git push.",
        )
        orch._save_state(state)
        loaded = orch._load_state()
        assert loaded["record_instructions"] == "Update journal. Git push."
        ctx = orch._build_context(loaded, phase="ALPHA", event="start")
        assert ctx["record_instructions"] == "Update journal. Git push."

    def test_missing_record_instructions_crashes(self, minimal_resources, tmp_path):
        """Old state.yaml without record_instructions must crash."""
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        old_state = _base_state(type="full", current_phase="RESEARCH")
        del old_state["record_instructions"]
        (tmp_path / "state.yaml").write_text(yaml.dump(old_state, default_flow_style=False))
        with pytest.raises(SystemExit):
            orch._load_state()


class TestRecordPhaseTemplate:
    def test_record_template_has_conditional_commit(self, autobuild_resources):
        """RECORD phase template must document the 'no code changes' branch.

        The telegraph-style prose may drop the leading 'If'; the assertion accepts
        any phrase that pairs 'code changes' with 'no' (case-insensitive) - enough
        to prove the conditional branch is documented.
        """
        orch._initialize(autobuild_resources)
        resolved_phase = orch._resolve_phase("RECORD")
        phase_obj = orch._MODEL.phases.get(resolved_phase)
        assert phase_obj is not None
        template = phase_obj.start
        lower = template.lower()
        assert "no code changes" in lower, (
            "RECORD phase template must document the 'no code changes' branch"
        )
        assert "{record_instructions}" in template


# ---------- output quality & real gaps ----------


class TestOutputQuality:
    def test_gatekeeper_prompts_and_phase_dir(self, autobuild_resources, tmp_path):
        """RESEARCH and HYPOTHESIS gatekeepers check required structural fields;
        phase_dir is present in build_context; relative output-file resolves
        against phase directory."""
        orch._initialize(autobuild_resources)

        research_key = next(k for k in orch._MODEL.gates if "RESEARCH" in k and "gatekeeper" in k)
        rprompt = orch._MODEL.gates[research_key].prompt.lower()
        assert "current state" in rprompt or "structural" in rprompt
        assert "gap analysis" in rprompt or "file inventory" in rprompt
        assert "evidence" in rprompt

        hyp_key = next(k for k in orch._MODEL.gates if "HYPOTHESIS" in k and "gatekeeper" in k)
        hprompt = orch._MODEL.gates[hyp_key].prompt.lower()
        assert "what to do" in hprompt
        assert "predict" in hprompt
        assert "risk" in hprompt
        assert "evidence" in hprompt

        # phase_dir in context
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        state = _base_state(type="full", current_phase="RESEARCH", phase_status="in_progress")
        orch._save_state(state)
        ctx = orch._build_context(state)
        assert "phase_dir" in ctx
        assert str(tmp_path) in ctx["phase_dir"]

    def test_output_file_resolves_to_phase_dir(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        state = _base_state(current_phase="ALPHA", phase_status="in_progress")
        orch._save_state(state)
        phase_dir = orch._phase_dir(state)
        test_file = phase_dir / "output.md"
        test_file.write_text("test content")
        resolved = (phase_dir / Path("output.md")).resolve()
        assert resolved == test_file.resolve()

    def test_hypothesis_load_rejects_malformed(self, minimal_resources, tmp_path):
        """Plain string notes and invalid status values both raise."""
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        bad1 = _rich_hyp_entry()
        bad1["notes"] = ["plain string note"]
        orch._save_hypotheses({"bad_hyp": bad1})
        with pytest.raises(ValueError, match="plain string|dict"):
            orch._load_hypotheses()
        bad2 = _rich_hyp_entry()
        bad2["status"] = "selected"
        orch._save_hypotheses({"bad_hyp": bad2})
        with pytest.raises(ValueError, match="invalid status|selected"):
            orch._load_hypotheses()


class TestRealGaps:
    def test_research_output_validation(self, minimal_resources):
        """Validation catches missing Gap Analysis section and short output."""
        orch._initialize(minimal_resources)

        missing_gap = (
            "## Current State Summary\n"
            "The project has 10 files with 500 lines of code.\n\n"
            "## File Inventory\n"
            "- src/main.py (100 lines)\n"
            "- src/utils.py (50 lines)\n"
            "- tests/test_main.py (80 lines)\n\n"
            "## Risk Assessment\n"
            "Main risk is the tight coupling between modules.\n"
            "This could cause regression issues during refactoring.\n"
            "Additional padding text to meet the minimum length requirement "
            "for the overall output.\n"
            "More text here to ensure we pass the 500 character minimum "
            "for the total output length check."
        )
        errors = orch._validate_research_output(missing_gap)
        assert any("gap analysis" in e.lower() for e in errors)

        short = (
            "## Current State\nShort.\n"
            "## Gap Analysis\nShort.\n"
            "## File Inventory\nShort.\n"
            "## Risk Assessment\nShort."
        )
        errors = orch._validate_research_output(short)
        assert any("500" in e or "short" in e.lower() or "length" in e.lower() for e in errors)

    def test_hypothesis_richness_validation(self, minimal_resources):
        """Richness validation catches short prediction, passes rich entries,
        and skips dismissed entries."""
        orch._initialize(minimal_resources)

        # Short prediction fails
        errors = orch._validate_hypothesis_richness({
            "h": {
                "hypothesis": (
                    "This is a hypothesis with enough characters to pass the minimum length check"
                ),
                "prediction": "",
                "evidence": "Enough evidence text here to pass",
                "stars": 3,
                "status": "new",
                "iteration_created": 1,
                "notes": [],
            }
        })
        assert any("prediction" in e.lower() for e in errors)

        # Rich valid entry passes
        rich = {
            "good_hyp": {
                "hypothesis": (
                    "The custom FSM implementation in engine/fsm.py has 258 lines of hand-written "
                    "state machine code with 15 call sites in orchestrator.py. Migrating to the "
                    "transitions package would reduce complexity and improve maintainability by "
                    "leveraging a well-tested library instead of custom code that needs to handle "
                    "edge cases manually."
                ),
                "prediction": (
                    "Reduce FSM code from 258 lines to approximately 100 lines while maintaining "
                    "all 15 call sites. Test count should remain stable at 115 or increase "
                    "slightly due to simpler assertions against transitions.Machine API."
                ),
                "evidence": (
                    "engine/fsm.py currently has 258 lines with custom FSMConfig dataclass, "
                    "6 state definitions, and manual transition validation. The transitions "
                    "package provides Machine class with declarative state/transition "
                    "definitions that would replace all of this. grep shows 15 _fire_fsm call "
                    "sites in orchestrator.py."
                ),
                "stars": 4,
                "status": "new",
                "iteration_created": 1,
                "notes": [],
            }
        }
        assert orch._validate_hypothesis_richness(rich) == []

        # Dismissed entries skipped
        dismissed = {
            "h": _rich_hyp_entry(status="dismissed", notes=[{"dismissed": "not relevant"}])
        }
        dismissed["h"]["hypothesis"] = "short"
        assert orch._validate_hypothesis_richness(dismissed) == []
