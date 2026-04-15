"""Unit tests for the YAML model loader and validator.

Aggressive consolidation: one structural test per resource set, one parametrized
test per validator error class, one parametrized test per dataclass. Previous
revision had 57 tests mostly asserting individual fields after reloading the
same fixture 16 times - those are now a single comprehensive structural test.
"""

import pytest

from stellars_claude_code_plugins.autobuild.model import (
    ActionDef,
    Agent,
    AppConfig,
    Gate,
    Model,
    Phase,
    WorkflowType,
    load_model,
    resolve_phase_key,
    validate_model,
)


# ---------------------------------------------------------------------------
# Model loading - structural tests
# ---------------------------------------------------------------------------


class TestLoadModel:
    """One structural test asserts every aspect of the minimal fixture in one
    pass - workflow types, phases, agents, gates, app, actions. Previous
    revision had 16 separate tests that reloaded the same fixture 16 times."""

    def test_minimal_resources_full_structure(self, minimal_resources):
        model = load_model(minimal_resources)
        assert isinstance(model, Model)

        # Workflow types
        assert "WORKFLOW::TEST_WORKFLOW" in model.workflow_types
        wf = model.workflow_types["WORKFLOW::TEST_WORKFLOW"]
        assert wf.description == "A test workflow"
        assert wf.cli_name == "test_workflow"
        assert wf.phase_names == ["ALPHA", "BETA", "GAMMA"]
        assert "ALPHA" in wf.required
        assert "GAMMA" in wf.required
        assert "BETA" in wf.skippable

        # Phases loaded with start templates
        for name in ("ALPHA", "BETA", "GAMMA"):
            assert name in model.phases
        assert "{objective}" in model.phases["ALPHA"].start

        # Agents (researcher on ALPHA)
        assert "ALPHA" in model.agents
        assert len(model.agents["ALPHA"]) == 1
        alpha_agent = model.agents["ALPHA"][0]
        assert alpha_agent.name == "researcher"
        assert alpha_agent.display_name == "Researcher"

        # Gates - start/end/skip/force-skip
        assert "ALPHA::readback" in model.gates
        assert "ALPHA::gatekeeper" in model.gates
        assert "gatekeeper_skip" in model.gates
        assert "gatekeeper_force_skip" in model.gates
        assert "understanding" in model.gates["ALPHA::readback"].prompt
        assert "evidence" in model.gates["ALPHA::gatekeeper"].prompt
        assert "phase" in model.gates["gatekeeper_skip"].prompt
        assert "force-skip" in model.gates["gatekeeper_force_skip"].prompt

        # Gate lifecycle metadata populated from start/end/skip sections
        assert "readback" in model.start_gate_types
        assert "gatekeeper" in model.end_gate_types
        assert "gatekeeper_skip" in model.skip_gate_types
        assert "gatekeeper_force_skip" in model.skip_gate_types

        # App config
        assert model.app.name == "test-plugin"
        assert model.app.cmd == "python orchestrate.py"
        assert model.app.artifacts_dir == ".test-plugin"
        assert model.app.display.separator == "-"
        assert model.app.display.separator_width == 40
        assert "{iter_label}" in model.app.banner.header
        assert "**{p}**" in model.app.banner.progress_current
        assert "new" in model.app.cli.commands
        assert "no_active" in model.app.messages
        assert "validate_success" in model.app.messages

        # Actions
        assert "ACTION::TEST_ACTION" in model.actions
        assert model.actions["ACTION::TEST_ACTION"].cli_name == "test_action"
        assert model.actions["ACTION::TEST_ACTION"].type == "programmatic"


class TestLoadModelErrors:
    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Required resource file"):
            load_model(tmp_path)

    def test_malformed_yaml_raises(self, tmp_path):
        resources = tmp_path / "resources"
        resources.mkdir()
        (resources / "workflow.yaml").write_text(": invalid: yaml: [")
        (resources / "phases.yaml").write_text("{}")
        (resources / "app.yaml").write_text("{}")
        with pytest.raises(ValueError, match="Malformed YAML"):
            load_model(resources)


# ---------------------------------------------------------------------------
# Real autobuild resources - structural smoke tests
# ---------------------------------------------------------------------------


class TestLoadAutobuild:
    """Real autobuild resources load, validate, and expose expected shapes.
    Previous revision had 14 tests each loading the same real fixture - those
    are consolidated here into one structural assertion + one validation call.
    """

    def test_real_resources_structure_and_validate(self, autobuild_resources):
        model = load_model(autobuild_resources)
        assert isinstance(model, Model)

        # Workflow FQN + cli_name + depends_on all coherent
        assert "WORKFLOW::FULL" in model.workflow_types
        full = model.workflow_types["WORKFLOW::FULL"]
        assert full.cli_name == "full"
        assert full.depends_on == "WORKFLOW::PLANNING"
        assert "IMPLEMENT" in full.phase_names
        assert "TEST" in full.phase_names
        for wf_name, wf in model.workflow_types.items():
            assert wf_name.startswith("WORKFLOW::"), f"{wf_name} missing FQN prefix"
            assert wf.cli_name, f"{wf_name} missing cli_name"

        # Every phase has a template, every agent named, every gate has a prompt
        for name, phase in model.phases.items():
            assert phase.start or phase.start_continue, f"{name} missing start template"
        for phase_key, agents in model.agents.items():
            for agent in agents:
                assert agent.name, f"agent in {phase_key} has empty name"
                assert agent.display_name, f"agent {agent.name} has empty display_name"
        for gate_key, gate in model.gates.items():
            assert gate.prompt, f"gate {gate_key} has empty prompt"

        # Gate lifecycle populated
        assert len(model.start_gate_types) > 0
        assert len(model.end_gate_types) > 0
        assert len(model.skip_gate_types) > 0

        # Actions - both programmatic + generative
        assert "ACTION::PLAN_SAVE" in model.actions
        assert model.actions["ACTION::PLAN_SAVE"].type == "programmatic"
        assert model.actions["ACTION::PLAN_SAVE"].cli_name == "plan_save"
        assert "ACTION::HYPOTHESIS_AUTOWRITE" in model.actions
        assert model.actions["ACTION::HYPOTHESIS_AUTOWRITE"].type == "generative"
        assert model.actions["ACTION::HYPOTHESIS_AUTOWRITE"].prompt != ""

        # Agents loaded from phases.yaml (no separate agents.yaml)
        assert "FULL::RESEARCH" in model.agents
        names = [a.name for a in model.agents["FULL::RESEARCH"]]
        assert "researcher" in names

        # auto_verify flag on TEST phase
        test_phase = model.phases.get("TEST")
        assert test_phase is not None
        assert test_phase.auto_verify is True

        # Resource file layout (agents.yaml is NOT a separate file)
        import os
        files = os.listdir(autobuild_resources)
        assert "agents.yaml" not in files
        assert {"workflow.yaml", "phases.yaml", "app.yaml"}.issubset(set(files))

        # validate() returns no issues for the real model
        issues = validate_model(model)
        assert issues == [], f"real model validation issues: {issues}"


# ---------------------------------------------------------------------------
# Validation - parametrized error cases
# ---------------------------------------------------------------------------


def _write_minimal_yamls(resources, workflow_body, phases_body, app_body="app:\n  name: test\n  cmd: test"):
    """Helper to write a minimal resource trio for validation edge cases."""
    resources.mkdir()
    (resources / "workflow.yaml").write_text(workflow_body)
    (resources / "phases.yaml").write_text(phases_body)
    (resources / "app.yaml").write_text(app_body)


_GATE_STUB = """
shared_gates:
  skip:
    gatekeeper_skip:
      prompt: "{phase} {iteration} {itype} {objective} {reason}"
    gatekeeper_force_skip:
      prompt: "{phase} {iteration} {reason}"
"""


def _minimal_phase_body(name="ALPHA", extra_actions=None):
    actions_block = ""
    if extra_actions:
        actions_block = "actions:\n" + extra_actions + "\n"
    return actions_block + _GATE_STUB + f"""
{name}:
  auto_actions:
    on_complete: []
  start:
    template: 'hello'
    agents:
      - name: readback
        prompt: "{{understanding}}"
  execution:
    agents:
      - name: a
        display_name: A
        prompt: do
  end:
    template: 'bye'
    agents:
      - name: gatekeeper
        prompt: "{{evidence}}"
"""


class TestValidateModel:
    """Validation produces expected issues for malformed resources.
    One parametrized test replaces 9 separate per-error-class tests."""

    def test_valid_minimal_model(self, minimal_resources):
        model = load_model(minimal_resources)
        assert validate_model(model) == []

    @pytest.mark.parametrize(
        "mutate, expected_substring",
        [
            # In-memory mutations of a valid model - each should surface one issue
            ("invalid_agent_mode", "invalid mode"),
            ("duplicate_agent", "duplicate agent name"),
            ("empty_app_name", "app.name"),
            ("empty_app_cmd", "app.cmd"),
        ],
        ids=["invalid_agent_mode", "duplicate_agent", "empty_app_name", "empty_app_cmd"],
    )
    def test_validator_catches_mutation(self, minimal_resources, mutate, expected_substring):
        model = load_model(minimal_resources)
        if mutate == "invalid_agent_mode":
            model.agents["ALPHA"][0].mode = "invalid_mode"
        elif mutate == "duplicate_agent":
            model.agents["ALPHA"].append(Agent(name="researcher", display_name="Dup", prompt="x"))
        elif mutate == "empty_app_name":
            model.app.name = ""
        elif mutate == "empty_app_cmd":
            model.app.cmd = ""
        issues = validate_model(model)
        assert any(expected_substring in i for i in issues), f"expected '{expected_substring}' in {issues}"

    @pytest.mark.parametrize(
        "workflow_yaml, expected_substring",
        [
            # Missing description on a workflow entry
            (
                "WORKFLOW::BAD:\n  cli_name: bad\n  phases:\n    - name: ALPHA\n",
                "missing 'description'",
            ),
            # Workflow without WORKFLOW:: FQN prefix
            (
                'bad_name:\n  cli_name: bad\n  description: "not FQN"\n  phases:\n    - name: ALPHA\n',
                "FQN format",
            ),
            # Two workflows share the same cli_name
            (
                'WORKFLOW::A:\n  cli_name: same\n  description: "first"\n  phases:\n    - name: ALPHA\nWORKFLOW::B:\n  cli_name: same\n  description: "second"\n  phases:\n    - name: ALPHA\n',
                "conflicts",
            ),
        ],
        ids=["missing_description", "workflow_not_fqn", "duplicate_cli_name"],
    )
    def test_validator_flags_workflow_yaml(self, tmp_path, workflow_yaml, expected_substring):
        resources = tmp_path / "resources"
        _write_minimal_yamls(resources, workflow_yaml, _minimal_phase_body())
        model = load_model(resources)
        issues = validate_model(model)
        assert any(expected_substring in i for i in issues), f"expected '{expected_substring}' in {issues}"

    def test_validate_warns_on_deprecated_gates_key(self, tmp_path):
        """Phases using the old `gates:` key surface a deprecation warning."""
        resources = tmp_path / "resources"
        resources.mkdir()
        (resources / "workflow.yaml").write_text(
            'WORKFLOW::OLD:\n  cli_name: old\n  description: "old"\n  phases:\n    - name: LEGACY\n'
        )
        (resources / "phases.yaml").write_text(
            _GATE_STUB
            + """
LEGACY:
  start: 'hello'
  end: 'bye'
  gates:
    on_start:
      readback:
        prompt: "{understanding}"
    on_end:
      agents:
        - name: a
          display_name: A
          prompt: do
      gatekeeper:
        prompt: "{evidence}"
"""
        )
        (resources / "app.yaml").write_text("app:\n  name: test\n  cmd: test")
        model = load_model(resources)
        issues = validate_model(model)
        assert any("gates:" in i and "deprecated" in i.lower() for i in issues), (
            f"expected deprecation warning, got: {issues}"
        )

    @pytest.mark.parametrize(
        "action_yaml, phase_body_actions, expected_substring",
        [
            # auto_actions references an undefined action name
            (
                "  ACTION::REAL:\n    cli_name: real_action\n    type: programmatic\n    description: exists\n",
                "[real_action, nonexistent_action]",
                "nonexistent_action",
            ),
            # Action without ACTION:: FQN prefix
            (
                "  bad_action:\n    type: programmatic\n    description: not FQN\n",
                "[]",
                "ACTION::",
            ),
        ],
        ids=["missing_action_def", "action_not_fqn"],
    )
    def test_validate_actions(self, tmp_path, action_yaml, phase_body_actions, expected_substring):
        resources = tmp_path / "resources"
        workflow = 'WORKFLOW::WF:\n  cli_name: wf\n  description: "t"\n  phases:\n    - name: STEP\n'
        phases = (
            "actions:\n"
            + action_yaml
            + _GATE_STUB
            + f"""
STEP:
  auto_actions:
    on_complete: {phase_body_actions}
  start:
    template: 'Start'
    agents:
      - name: readback
        prompt: "{{understanding}}"
  execution:
    agents:
      - name: a
        display_name: A
        prompt: do
  end:
    template: 'End'
    agents:
      - name: gatekeeper
        prompt: "{{evidence}}"
"""
        )
        _write_minimal_yamls(resources, workflow, phases)
        model = load_model(resources)
        issues = validate_model(model)
        assert any(expected_substring in i for i in issues), f"expected '{expected_substring}' in {issues}"


# ---------------------------------------------------------------------------
# resolve_phase_key - namespace resolution
# ---------------------------------------------------------------------------


class TestResolvePhaseKey:
    """Parametrized table - 6 individual tests collapsed to 1 method."""

    @pytest.mark.parametrize(
        "workflow, phase, registry, expected_key_or_error",
        [
            ("FULL", "RESEARCH", {"FULL::RESEARCH", "RESEARCH"}, "FULL::RESEARCH"),
            ("FULL", "RECORD", {"RECORD"}, "RECORD"),
            ("GC", "PLAN", {"GC::PLAN", "PLAN", "FULL::PLAN"}, "GC::PLAN"),
            ("HOTFIX", "PLAN", {"PLAN", "FULL::PLAN"}, "PLAN"),
            ("GC", "IMPLEMENT", {"FULL::IMPLEMENT"}, KeyError),
            ("FULL", "MISSING", {"OTHER"}, KeyError),
        ],
        ids=["namespaced_match", "bare_fallback", "namespaced_over_bare", "bare_when_no_ns", "missing_ns", "no_match"],
    )
    def test_resolve(self, workflow, phase, registry, expected_key_or_error):
        if expected_key_or_error is KeyError:
            with pytest.raises(KeyError, match="not found"):
                resolve_phase_key(workflow, phase, registry)
        else:
            assert resolve_phase_key(workflow, phase, registry) == expected_key_or_error


# ---------------------------------------------------------------------------
# Dataclass defaults - 9 individual tests collapsed to 3
# ---------------------------------------------------------------------------


class TestDataclasses:
    """Compact dataclass contract tests. Previous revision had 9 separate
    one-assertion methods across TestWorkflowType / TestPhaseDataclass /
    TestActionDef."""

    def test_workflow_type_classification_and_fields(self):
        wf = WorkflowType(
            description="test",
            phases=[
                {"name": "A", "skippable": False},
                {"name": "B", "skippable": True},
                {"name": "C"},  # default: required
            ],
            cli_name="full",
        )
        assert wf.phase_names == ["A", "B", "C"]
        assert "A" in wf.required
        assert "B" in wf.skippable
        assert "C" in wf.required
        assert wf.cli_name == "full"

        wf_default = WorkflowType(description="test", phases=[])
        assert wf_default.depends_on == ""
        assert wf_default.independent is True

    def test_phase_defaults_and_options(self):
        p_default = Phase()
        assert p_default.start == ""
        assert p_default.end == ""
        assert p_default.reject_to is None
        assert p_default.auto_actions is None
        assert p_default.auto_verify is False

        p_with_options = Phase(
            reject_to={"phase": "IMPLEMENT", "condition": "always"},
            auto_actions={"on_complete": ["plan_save"]},
        )
        assert p_with_options.reject_to["phase"] == "IMPLEMENT"
        assert "plan_save" in p_with_options.auto_actions["on_complete"]

    def test_action_def_programmatic_and_generative(self):
        prog = ActionDef(type="programmatic", description="test", cli_name="plan_save")
        assert prog.type == "programmatic"
        assert prog.prompt == ""
        assert prog.cli_name == "plan_save"

        gen = ActionDef(type="generative", description="test", prompt="do something")
        assert gen.type == "generative"
        assert gen.prompt == "do something"
