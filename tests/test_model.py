"""Unit tests for the YAML model loader and validator."""

import warnings

import pytest

from stellars_claude_code_plugins.engine.model import (
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


class TestLoadModel:
    """Tests for loading YAML resources into a Model."""

    def test_load_minimal_resources(self, minimal_resources):
        model = load_model(minimal_resources)
        assert isinstance(model, Model)

    def test_workflow_types_loaded(self, minimal_resources):
        model = load_model(minimal_resources)
        assert "WORKFLOW::TEST_WORKFLOW" in model.workflow_types
        wf = model.workflow_types["WORKFLOW::TEST_WORKFLOW"]
        assert wf.description == "A test workflow"
        assert wf.cli_name == "test_workflow"
        assert wf.phase_names == ["ALPHA", "BETA", "GAMMA"]

    def test_workflow_required_skippable(self, minimal_resources):
        model = load_model(minimal_resources)
        wf = model.workflow_types["WORKFLOW::TEST_WORKFLOW"]
        assert "ALPHA" in wf.required
        assert "GAMMA" in wf.required
        assert "BETA" in wf.skippable

    def test_phases_loaded(self, minimal_resources):
        model = load_model(minimal_resources)
        assert "ALPHA" in model.phases
        assert "BETA" in model.phases
        assert "GAMMA" in model.phases
        assert "{objective}" in model.phases["ALPHA"].start

    def test_agents_loaded(self, minimal_resources):
        model = load_model(minimal_resources)
        assert "ALPHA" in model.agents
        assert len(model.agents["ALPHA"]) == 1
        agent = model.agents["ALPHA"][0]
        assert agent.name == "researcher"
        assert agent.display_name == "Researcher"

    def test_gates_loaded(self, minimal_resources):
        model = load_model(minimal_resources)
        assert "ALPHA::readback" in model.gates
        assert "ALPHA::gatekeeper" in model.gates
        assert "gatekeeper_skip" in model.gates
        assert "gatekeeper_force_skip" in model.gates

    def test_gates_from_start_end(self, minimal_resources):
        """Gates under start.agents/end.agents are extracted correctly."""
        model = load_model(minimal_resources)
        # start -> readback
        rb = model.gates["ALPHA::readback"]
        assert "understanding" in rb.prompt
        # end -> gatekeeper
        gk = model.gates["ALPHA::gatekeeper"]
        assert "evidence" in gk.prompt

    def test_shared_gates_from_skip(self, minimal_resources):
        """Shared gates under skip are extracted correctly."""
        model = load_model(minimal_resources)
        skip = model.gates["gatekeeper_skip"]
        assert "phase" in skip.prompt
        force = model.gates["gatekeeper_force_skip"]
        assert "force-skip" in force.prompt

    def test_gate_lifecycle_metadata(self, minimal_resources):
        """Gate lifecycle sets are populated from start/end/skip structure."""
        model = load_model(minimal_resources)
        assert "readback" in model.start_gate_types
        assert "gatekeeper" in model.end_gate_types
        assert "gatekeeper_skip" in model.skip_gate_types
        assert "gatekeeper_force_skip" in model.skip_gate_types

    def test_app_config_loaded(self, minimal_resources):
        model = load_model(minimal_resources)
        assert model.app.name == "test-plugin"
        assert model.app.cmd == "python orchestrate.py"
        assert model.app.artifacts_dir == ".test-plugin"

    def test_display_config(self, minimal_resources):
        model = load_model(minimal_resources)
        assert model.app.display.separator == "-"
        assert model.app.display.separator_width == 40

    def test_banner_config(self, minimal_resources):
        model = load_model(minimal_resources)
        assert "{iter_label}" in model.app.banner.header
        assert "**{p}**" in model.app.banner.progress_current

    def test_cli_config(self, minimal_resources):
        model = load_model(minimal_resources)
        assert "new" in model.app.cli.commands
        assert "start" in model.app.cli.commands

    def test_messages_loaded(self, minimal_resources):
        model = load_model(minimal_resources)
        assert "no_active" in model.app.messages
        assert "validate_success" in model.app.messages

    def test_actions_loaded_with_fqn(self, minimal_resources):
        """Actions loaded with FQN keys and cli_name."""
        model = load_model(minimal_resources)
        assert "ACTION::TEST_ACTION" in model.actions
        action = model.actions["ACTION::TEST_ACTION"]
        assert action.cli_name == "test_action"
        assert action.type == "programmatic"


class TestLoadModelErrors:
    """Tests for error handling in model loading."""

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


class TestLoadAutoBuildClaw:
    """Tests loading the real auto-build-claw YAML resources."""

    def test_load_real_resources(self, auto_build_claw_resources):
        model = load_model(auto_build_claw_resources)
        assert isinstance(model, Model)

    def test_real_workflow_types(self, auto_build_claw_resources):
        model = load_model(auto_build_claw_resources)
        assert "WORKFLOW::FULL" in model.workflow_types
        wf = model.workflow_types["WORKFLOW::FULL"]
        assert wf.cli_name == "full"
        assert len(wf.phase_names) > 0
        assert "IMPLEMENT" in wf.phase_names
        assert "TEST" in wf.phase_names

    def test_real_workflow_cli_names(self, auto_build_claw_resources):
        """All workflows have cli_name set."""
        model = load_model(auto_build_claw_resources)
        for wf_name, wf in model.workflow_types.items():
            assert wf.cli_name, f"Workflow {wf_name} missing cli_name"

    def test_real_workflow_fqn_format(self, auto_build_claw_resources):
        """All workflows use WORKFLOW::NAME FQN format."""
        model = load_model(auto_build_claw_resources)
        for wf_name in model.workflow_types:
            assert wf_name.startswith("WORKFLOW::"), f"Workflow {wf_name} not FQN"

    def test_real_depends_on_fqn(self, auto_build_claw_resources):
        """depends_on uses FQN format."""
        model = load_model(auto_build_claw_resources)
        wf = model.workflow_types["WORKFLOW::FULL"]
        assert wf.depends_on == "WORKFLOW::PLANNING"

    def test_real_phases_have_templates(self, auto_build_claw_resources):
        model = load_model(auto_build_claw_resources)
        for name, phase in model.phases.items():
            assert phase.start or phase.start_continue, f"Phase {name} has no start template"

    def test_real_agents_have_names(self, auto_build_claw_resources):
        model = load_model(auto_build_claw_resources)
        for phase_key, agents in model.agents.items():
            for agent in agents:
                assert agent.name, f"Agent in {phase_key} has empty name"
                assert agent.display_name, f"Agent {agent.name} in {phase_key} has empty display_name"

    def test_real_gates_have_prompts(self, auto_build_claw_resources):
        model = load_model(auto_build_claw_resources)
        for gate_key, gate in model.gates.items():
            assert gate.prompt, f"Gate {gate_key} has empty prompt"

    def test_real_actions_loaded(self, auto_build_claw_resources):
        model = load_model(auto_build_claw_resources)
        assert "ACTION::PLAN_SAVE" in model.actions
        assert model.actions["ACTION::PLAN_SAVE"].type == "programmatic"
        assert model.actions["ACTION::PLAN_SAVE"].cli_name == "plan_save"
        assert "ACTION::HYPOTHESIS_AUTOWRITE" in model.actions
        assert model.actions["ACTION::HYPOTHESIS_AUTOWRITE"].type == "generative"
        assert model.actions["ACTION::HYPOTHESIS_AUTOWRITE"].prompt != ""

    def test_real_gate_lifecycle_metadata(self, auto_build_claw_resources):
        """Real model has gate lifecycle metadata populated."""
        model = load_model(auto_build_claw_resources)
        assert len(model.start_gate_types) > 0
        assert len(model.end_gate_types) > 0
        assert len(model.skip_gate_types) > 0

    def test_real_auto_verify_on_test(self, auto_build_claw_resources):
        """Real FULL::TEST phase has auto_verify set."""
        model = load_model(auto_build_claw_resources)
        test_phase = model.phases.get("TEST")
        assert test_phase is not None
        assert test_phase.auto_verify is True

    def test_real_model_validates(self, auto_build_claw_resources):
        model = load_model(auto_build_claw_resources)
        issues = validate_model(model)
        assert issues == [], f"Validation issues: {issues}"

    def test_agents_loaded_from_phases(self, auto_build_claw_resources):
        """Agents are loaded from phases.yaml (no agents.yaml)."""
        model = load_model(auto_build_claw_resources)
        assert "FULL::RESEARCH" in model.agents
        assert len(model.agents["FULL::RESEARCH"]) == 3
        names = [a.name for a in model.agents["FULL::RESEARCH"]]
        assert "researcher" in names
        assert "architect" in names
        assert "product_manager" in names

    def test_three_files_loaded(self, auto_build_claw_resources):
        """Only 3 resource files needed (no agents.yaml)."""
        import os
        files = os.listdir(auto_build_claw_resources)
        assert "agents.yaml" not in files
        assert "workflow.yaml" in files
        assert "phases.yaml" in files
        assert "app.yaml" in files


class TestValidateModel:
    """Tests for model validation logic."""

    def test_valid_minimal_model(self, minimal_resources):
        model = load_model(minimal_resources)
        issues = validate_model(model)
        assert issues == [], f"Unexpected issues: {issues}"

    def test_missing_workflow_description(self, tmp_path):
        resources = tmp_path / "resources"
        resources.mkdir()
        (resources / "workflow.yaml").write_text("""
WORKFLOW::BAD:
  cli_name: bad
  phases:
    - name: ALPHA
""")
        (resources / "phases.yaml").write_text("""
shared_gates:
  skip:
    gatekeeper_skip:
      prompt: "{phase} {iteration} {itype} {objective} {reason}"
    gatekeeper_force_skip:
      prompt: "{phase} {iteration} {reason}"
ALPHA:
  auto_actions:
    on_complete: []
  start:
    template: 'hello'
    agents:
      - name: readback
        prompt: "{understanding}"
  execution:
    agents:
      - name: a
        display_name: A
        prompt: do
  end:
    template: 'bye'
    agents:
      - name: gatekeeper
        prompt: "{evidence}"
""")
        (resources / "app.yaml").write_text("app:\n  name: test\n  cmd: test")
        model = load_model(resources)
        issues = validate_model(model)
        assert any("missing 'description'" in i for i in issues)

    def test_invalid_agent_mode(self, minimal_resources):
        model = load_model(minimal_resources)
        model.agents["ALPHA"][0].mode = "invalid_mode"
        issues = validate_model(model)
        assert any("invalid mode" in i for i in issues)

    def test_duplicate_agent_names(self, minimal_resources):
        model = load_model(minimal_resources)
        dup = Agent(name="researcher", display_name="Dup", prompt="x")
        model.agents["ALPHA"].append(dup)
        issues = validate_model(model)
        assert any("duplicate agent name" in i for i in issues)

    def test_missing_app_name(self, minimal_resources):
        model = load_model(minimal_resources)
        model.app.name = ""
        issues = validate_model(model)
        assert any("app.name" in i for i in issues)

    def test_missing_app_cmd(self, minimal_resources):
        model = load_model(minimal_resources)
        model.app.cmd = ""
        issues = validate_model(model)
        assert any("app.cmd" in i for i in issues)

    def test_validate_fqn_workflow_format(self, tmp_path):
        """Workflows without WORKFLOW:: prefix are flagged."""
        resources = tmp_path / "resources"
        resources.mkdir()
        (resources / "workflow.yaml").write_text("""
bad_name:
  cli_name: bad
  description: "not FQN"
  phases:
    - name: ALPHA
""")
        (resources / "phases.yaml").write_text("""
shared_gates:
  skip:
    gatekeeper_skip:
      prompt: "{phase} {iteration} {itype} {objective} {reason}"
    gatekeeper_force_skip:
      prompt: "{phase} {iteration} {reason}"
ALPHA:
  auto_actions:
    on_complete: []
  start:
    template: 'hello'
    agents:
      - name: readback
        prompt: "{understanding}"
  execution:
    agents: []
  end:
    template: 'bye'
    agents:
      - name: gatekeeper
        prompt: "{evidence}"
""")
        (resources / "app.yaml").write_text("app:\n  name: test\n  cmd: test")
        model = load_model(resources)
        issues = validate_model(model)
        assert any("FQN format" in i for i in issues)

    def test_validate_cli_name_uniqueness(self, tmp_path):
        """Duplicate cli_names are flagged."""
        resources = tmp_path / "resources"
        resources.mkdir()
        (resources / "workflow.yaml").write_text("""
WORKFLOW::A:
  cli_name: same
  description: "first"
  phases:
    - name: ALPHA
WORKFLOW::B:
  cli_name: same
  description: "second"
  phases:
    - name: ALPHA
""")
        (resources / "phases.yaml").write_text("""
shared_gates:
  skip:
    gatekeeper_skip:
      prompt: "{phase} {iteration} {itype} {objective} {reason}"
    gatekeeper_force_skip:
      prompt: "{phase} {iteration} {reason}"
ALPHA:
  auto_actions:
    on_complete: []
  start:
    template: 'hello'
    agents:
      - name: readback
        prompt: "{understanding}"
  execution:
    agents: []
  end:
    template: 'bye'
    agents:
      - name: gatekeeper
        prompt: "{evidence}"
""")
        (resources / "app.yaml").write_text("app:\n  name: test\n  cmd: test")
        model = load_model(resources)
        issues = validate_model(model)
        assert any("conflicts" in i for i in issues)

    def test_validate_warns_old_gates_structure(self, tmp_path):
        """Phases using old gates: key produce a validation warning."""
        resources = tmp_path / "resources"
        resources.mkdir()
        (resources / "workflow.yaml").write_text("""
WORKFLOW::OLD:
  cli_name: old
  description: "old structure"
  phases:
    - name: LEGACY
""")
        (resources / "phases.yaml").write_text("""
shared_gates:
  skip:
    gatekeeper_skip:
      prompt: "{phase} {iteration} {itype} {objective} {reason}"
    gatekeeper_force_skip:
      prompt: "{phase} {iteration} {reason}"
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
""")
        (resources / "app.yaml").write_text("app:\n  name: test\n  cmd: test")
        model = load_model(resources)
        issues = validate_model(model)
        assert any("gates:" in i and "deprecated" in i.lower() for i in issues), (
            f"Expected deprecation warning for old 'gates:' structure, got: {issues}"
        )


class TestValidateModelActions:
    """Tests for action validation in validate_model."""

    def test_validate_catches_missing_action_definition(self, tmp_path):
        """validate_model flags auto_actions that reference undefined actions."""
        resources = tmp_path / "resources"
        resources.mkdir()
        (resources / "workflow.yaml").write_text("""
WORKFLOW::ACT:
  cli_name: act
  description: "Workflow with bad action ref"
  phases:
    - name: STEP
""")
        (resources / "phases.yaml").write_text("""
actions:
  ACTION::REAL:
    cli_name: real_action
    type: programmatic
    description: "exists"
shared_gates:
  skip:
    gatekeeper_skip:
      prompt: "{phase} {iteration} {itype} {objective} {reason}"
    gatekeeper_force_skip:
      prompt: "{phase} {iteration} {reason}"
STEP:
  auto_actions:
    on_complete: [real_action, nonexistent_action]
  start:
    template: "Start"
    agents:
      - name: readback
        prompt: "{understanding}"
  execution:
    agents:
      - name: a
        display_name: A
        prompt: do
  end:
    template: "End"
    agents:
      - name: gatekeeper
        prompt: "{evidence}"
""")
        (resources / "app.yaml").write_text("app:\n  name: test\n  cmd: test")
        model = load_model(resources)
        issues = validate_model(model)
        assert any("nonexistent_action" in i for i in issues)
        # real_action is known via cli_name, so it should not be flagged
        assert not any("unknown action 'real_action'" in i for i in issues)

    def test_validate_action_fqn_format(self, tmp_path):
        """Actions without ACTION:: prefix are flagged."""
        resources = tmp_path / "resources"
        resources.mkdir()
        (resources / "workflow.yaml").write_text("""
WORKFLOW::WF:
  cli_name: wf
  description: "test"
  phases:
    - name: STEP
""")
        (resources / "phases.yaml").write_text("""
actions:
  bad_action:
    type: programmatic
    description: "not FQN"
shared_gates:
  skip:
    gatekeeper_skip:
      prompt: "{phase} {iteration} {itype} {objective} {reason}"
    gatekeeper_force_skip:
      prompt: "{phase} {iteration} {reason}"
STEP:
  auto_actions:
    on_complete: []
  start:
    template: "Start"
    agents:
      - name: readback
        prompt: "{understanding}"
  execution:
    agents: []
  end:
    template: "End"
    agents:
      - name: gatekeeper
        prompt: "{evidence}"
""")
        (resources / "app.yaml").write_text("app:\n  name: test\n  cmd: test")
        model = load_model(resources)
        issues = validate_model(model)
        assert any("ACTION::" in i for i in issues)


class TestResolvePhaseKey:
    """Tests for resolve_phase_key strict namespace resolution."""

    def test_namespaced_match(self):
        registry = {"FULL::RESEARCH", "RESEARCH"}
        assert resolve_phase_key("FULL", "RESEARCH", registry) == "FULL::RESEARCH"

    def test_bare_fallback(self):
        registry = {"RECORD"}
        assert resolve_phase_key("FULL", "RECORD", registry) == "RECORD"

    def test_missing_raises_keyerror(self):
        registry = {"FULL::IMPLEMENT"}
        with pytest.raises(KeyError, match="not found"):
            resolve_phase_key("GC", "IMPLEMENT", registry)

    def test_no_match_raises_keyerror(self):
        registry = {"OTHER"}
        with pytest.raises(KeyError, match="not found"):
            resolve_phase_key("FULL", "MISSING", registry)

    def test_namespaced_preferred_over_bare(self):
        registry = {"GC::PLAN", "PLAN", "FULL::PLAN"}
        assert resolve_phase_key("GC", "PLAN", registry) == "GC::PLAN"

    def test_bare_used_when_no_namespace(self):
        """When no workflow-specific key exists, bare name is used."""
        registry = {"PLAN", "FULL::PLAN"}
        assert resolve_phase_key("HOTFIX", "PLAN", registry) == "PLAN"


class TestWorkflowType:
    """Tests for WorkflowType dataclass post_init logic."""

    def test_phase_classification(self):
        wf = WorkflowType(
            description="test",
            phases=[
                {"name": "A", "skippable": False},
                {"name": "B", "skippable": True},
                {"name": "C"},  # default: required
            ],
        )
        assert wf.phase_names == ["A", "B", "C"]
        assert "A" in wf.required
        assert "B" in wf.skippable
        assert "C" in wf.required

    def test_depends_on_default(self):
        wf = WorkflowType(description="test", phases=[])
        assert wf.depends_on == ""
        assert wf.independent is True

    def test_cli_name_field(self):
        wf = WorkflowType(description="test", phases=[], cli_name="full")
        assert wf.cli_name == "full"


class TestPhaseDataclass:
    """Tests for Phase dataclass fields."""

    def test_defaults(self):
        p = Phase()
        assert p.start == ""
        assert p.end == ""
        assert p.reject_to is None
        assert p.auto_actions is None
        assert p.auto_verify is False

    def test_with_reject_to(self):
        p = Phase(reject_to={"phase": "IMPLEMENT", "condition": "always"})
        assert p.reject_to["phase"] == "IMPLEMENT"

    def test_with_auto_actions(self):
        p = Phase(auto_actions={"on_complete": ["plan_save"]})
        assert "plan_save" in p.auto_actions["on_complete"]


class TestActionDef:
    """Tests for ActionDef dataclass."""

    def test_programmatic_defaults(self):
        a = ActionDef(type="programmatic", description="test")
        assert a.type == "programmatic"
        assert a.prompt == ""
        assert a.cli_name == ""

    def test_generative_with_prompt(self):
        a = ActionDef(type="generative", description="test", prompt="do something")
        assert a.type == "generative"
        assert a.prompt == "do something"

    def test_cli_name_field(self):
        a = ActionDef(type="programmatic", description="test", cli_name="plan_save")
        assert a.cli_name == "plan_save"
