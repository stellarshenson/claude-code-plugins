"""Unit tests for the YAML model loader and validator."""

import pytest

from stellars_claude_code_plugins.engine.model import (
    ActionDef,
    Agent,
    AppConfig,
    Gate,
    Model,
    Phase,
    WorkflowType,
    _resolve_key,
    load_model,
    validate_model,
)


class TestLoadModel:
    """Tests for loading YAML resources into a Model."""

    def test_load_minimal_resources(self, minimal_resources):
        model = load_model(minimal_resources)
        assert isinstance(model, Model)

    def test_workflow_types_loaded(self, minimal_resources):
        model = load_model(minimal_resources)
        assert "test_workflow" in model.workflow_types
        wf = model.workflow_types["test_workflow"]
        assert wf.description == "A test workflow"
        assert wf.phase_names == ["ALPHA", "BETA", "GAMMA"]

    def test_workflow_required_skippable(self, minimal_resources):
        model = load_model(minimal_resources)
        wf = model.workflow_types["test_workflow"]
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

    def test_gates_from_on_start_on_end(self, minimal_resources):
        """Gates under on_start/on_end are extracted correctly."""
        model = load_model(minimal_resources)
        # on_start -> readback
        rb = model.gates["ALPHA::readback"]
        assert "understanding" in rb.prompt
        # on_end -> gatekeeper
        gk = model.gates["ALPHA::gatekeeper"]
        assert "evidence" in gk.prompt

    def test_shared_gates_from_on_skip(self, minimal_resources):
        """Shared gates under on_skip are extracted correctly."""
        model = load_model(minimal_resources)
        skip = model.gates["gatekeeper_skip"]
        assert "phase" in skip.prompt
        force = model.gates["gatekeeper_force_skip"]
        assert "force-skip" in force.prompt

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

    def test_actions_default_empty(self, minimal_resources):
        """Actions default to empty dict when not in workflow.yaml."""
        model = load_model(minimal_resources)
        assert model.actions == {}


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
        (resources / "agents.yaml").write_text("{}")
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
        assert "full" in model.workflow_types
        wf = model.workflow_types["full"]
        assert len(wf.phase_names) > 0
        assert "IMPLEMENT" in wf.phase_names
        assert "TEST" in wf.phase_names

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
        assert "plan_save" in model.actions
        assert model.actions["plan_save"].type == "programmatic"
        assert "hypothesis_autowrite" in model.actions
        assert model.actions["hypothesis_autowrite"].type == "generative"
        assert model.actions["hypothesis_autowrite"].prompt != ""

    def test_real_model_validates(self, auto_build_claw_resources):
        model = load_model(auto_build_claw_resources)
        issues = validate_model(model)
        assert issues == [], f"Validation issues: {issues}"


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
bad_workflow:
  phases:
    - name: ALPHA
""")
        (resources / "phases.yaml").write_text("ALPHA:\n  start: 'hello'\n  end: 'bye'")
        (resources / "agents.yaml").write_text("""
shared_gates:
  on_skip:
    gatekeeper_skip:
      prompt: "{phase} {iteration} {itype} {objective} {reason}"
    gatekeeper_force_skip:
      prompt: "{phase} {iteration} {reason}"
ALPHA:
  agents:
    - name: a
      display_name: A
      prompt: do
  gates:
    on_start:
      readback:
        prompt: "{understanding}"
    on_end:
      gatekeeper:
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


class TestResolveKey:
    """Tests for _resolve_key namespace resolution with FULL fallback."""

    def test_namespaced_match(self):
        registry = {"FULL::RESEARCH", "RESEARCH"}
        assert _resolve_key("full", "RESEARCH", registry) == "FULL::RESEARCH"

    def test_bare_fallback(self):
        registry = {"RECORD"}
        assert _resolve_key("full", "RECORD", registry) == "RECORD"

    def test_full_fallback(self):
        registry = {"FULL::IMPLEMENT"}
        assert _resolve_key("gc", "IMPLEMENT", registry) == "FULL::IMPLEMENT"

    def test_no_match_returns_bare(self):
        registry = {"OTHER"}
        assert _resolve_key("full", "MISSING", registry) == "MISSING"

    def test_namespaced_preferred_over_bare(self):
        registry = {"GC::PLAN", "PLAN", "FULL::PLAN"}
        assert _resolve_key("gc", "PLAN", registry) == "GC::PLAN"

    def test_full_fallback_over_bare(self):
        """When workflow has no namespaced key, FULL:: is tried before bare."""
        registry = {"FULL::PLAN"}
        assert _resolve_key("hotfix", "PLAN", registry) == "FULL::PLAN"


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


class TestPhaseDataclass:
    """Tests for Phase dataclass fields."""

    def test_defaults(self):
        p = Phase()
        assert p.start == ""
        assert p.end == ""
        assert p.reject_to is None
        assert p.auto_actions is None

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

    def test_generative_with_prompt(self):
        a = ActionDef(type="generative", description="test", prompt="do something")
        assert a.type == "generative"
        assert a.prompt == "do something"
