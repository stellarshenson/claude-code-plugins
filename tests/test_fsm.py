"""Unit tests for the FSM engine (transitions-based).

Aggressive consolidation: parametrized state transition tables replace
individual per-transition methods. Previous revision had 31 tests split
across TestFSMBasic (11), TestFSMGuards (5), TestFSMActions (3),
TestPhaseLifecycleFSM (12) - each asserting one transition. This revision
uses parametrized scenario tables for lifecycle paths and keeps one
targeted test per guard/action feature.
"""

import pytest

from stellars_claude_code_plugins.autobuild.fsm import (
    ADVANCE,
    COMPLETE,
    END,
    FSM,
    GATE_FAIL,
    GATE_PASS,
    GATEKEEPER,
    IN_PROGRESS,
    PENDING,
    READBACK,
    READBACK_FAIL,
    READBACK_PASS,
    REJECT,
    REJECTED,
    SKIP,
    SKIPPED,
    START,
    build_phase_lifecycle_fsm,
)


# ---------------------------------------------------------------------------
# Core FSM engine - construction, transitions, log, reset, can_fire
# ---------------------------------------------------------------------------


class TestFSMCore:
    """Engine contract tests: initial state, transition firing, log, reset,
    can_fire, invalid events. Replaces 11 one-assertion tests with one
    scenario test that exercises the whole flow, plus one invalid-event test."""

    @pytest.fixture
    def simple_fsm(self):
        return FSM(
            [
                {"trigger": "start", "source": "pending", "dest": "in_progress"},
                {"trigger": "end", "source": "in_progress", "dest": "complete"},
            ]
        )

    def test_full_scenario(self, simple_fsm):
        # Initial state
        assert simple_fsm.current_state == PENDING
        assert simple_fsm.can_fire(START) is True
        assert simple_fsm.can_fire(END) is False

        # Fire with constant + string forms - both accepted
        assert simple_fsm.fire(START) == IN_PROGRESS
        assert simple_fsm.current_state == IN_PROGRESS
        assert simple_fsm.fire("end") == COMPLETE

        # Log captured both transitions
        assert len(simple_fsm.log) == 2
        assert simple_fsm.log[0]["from"] == "pending"
        assert simple_fsm.log[0]["to"] == "in_progress"
        assert simple_fsm.log[1]["to"] == "complete"

        # reset() returns to PENDING; reset(state) jumps to a specific state
        simple_fsm.reset()
        assert simple_fsm.current_state == PENDING
        simple_fsm.reset(COMPLETE)
        assert simple_fsm.current_state == COMPLETE

        # Direct state assignment still works (used by orchestrator rehydration)
        simple_fsm.current_state = IN_PROGRESS
        assert simple_fsm.current_state == IN_PROGRESS

    def test_invalid_event_raises(self, simple_fsm):
        with pytest.raises(ValueError):
            simple_fsm.fire(END)  # no pending -> complete transition


# ---------------------------------------------------------------------------
# Guards - pass/fail/all-fail/unknown/context propagation
# ---------------------------------------------------------------------------


class TestFSMGuards:
    """Guard contract: first passing guard wins, all-fail raises, unknown
    raises, context propagates. 5 tests collapsed to 2."""

    @pytest.fixture
    def guarded_fsm(self):
        return FSM(
            [
                {"trigger": "start", "source": "pending", "dest": "in_progress", "guard": "is_ready"},
                {"trigger": "start", "source": "pending", "dest": "rejected", "guard": "not_ready"},
            ]
        )

    @pytest.mark.parametrize(
        "is_ready, not_ready, expected",
        [
            (True, False, IN_PROGRESS),  # first guard passes
            (False, True, REJECTED),  # first fails, second passes
            (False, False, "raise"),  # all fail
        ],
        ids=["first_passes", "second_passes", "all_fail"],
    )
    def test_guard_selection(self, guarded_fsm, is_ready, not_ready, expected):
        guarded_fsm.register_guard("is_ready", lambda **ctx: is_ready)
        guarded_fsm.register_guard("not_ready", lambda **ctx: not_ready)
        if expected == "raise":
            with pytest.raises(ValueError):
                guarded_fsm.fire(START)
        else:
            assert guarded_fsm.fire(START) == expected

    def test_unknown_guard_and_context(self):
        # Unknown guard raises
        fsm1 = FSM([{"trigger": "start", "source": "pending", "dest": "in_progress", "guard": "missing"}])
        with pytest.raises(ValueError, match="Unknown guard"):
            fsm1.fire(START)

        # Context keyword args propagate to guard + action functions
        received = {}
        fsm2 = FSM([{"trigger": "start", "source": "pending", "dest": "in_progress", "guard": "check"}])
        fsm2.register_guard("check", lambda **ctx: (received.update(ctx), True)[1])
        fsm2.fire(START, phase="RESEARCH", iteration=1)
        assert received["phase"] == "RESEARCH"
        assert received["iteration"] == 1


# ---------------------------------------------------------------------------
# Actions - execution, unknown, context
# ---------------------------------------------------------------------------


class TestFSMActions:
    """Action contract: executes on transition, unknown raises, context
    propagates. 3 tests collapsed to 1."""

    def test_action_contract(self):
        # Action executes + receives context
        fsm = FSM([{"trigger": "start", "source": "pending", "dest": "in_progress", "action": "capture"}])
        received = {}
        fsm.register_action("capture", lambda **ctx: received.update(ctx))
        fsm.fire(START, phase="TEST", data="hello")
        assert received["phase"] == "TEST"
        assert received["data"] == "hello"

        # Unknown action raises
        fsm_bad = FSM([{"trigger": "start", "source": "pending", "dest": "in_progress", "action": "missing"}])
        with pytest.raises(ValueError, match="Unknown action"):
            fsm_bad.fire(START)


# ---------------------------------------------------------------------------
# Phase lifecycle FSM - happy path, retry loops, skip, reject, advance
# ---------------------------------------------------------------------------


class TestPhaseLifecycleFSM:
    """Lifecycle transition table replaces 10 individual path tests. Each
    parametrized row drives the fsm through a scripted event sequence and
    asserts the final state."""

    @pytest.fixture
    def fsm(self):
        return build_phase_lifecycle_fsm()

    @pytest.mark.parametrize(
        "events, final_state",
        [
            # Happy path: readback pass -> gate pass -> complete
            ([START, READBACK_PASS, END, GATE_PASS], COMPLETE),
            # Readback fail -> back to pending
            ([START, READBACK_FAIL], PENDING),
            # Gate fail -> back to in_progress
            ([START, READBACK_PASS, END, GATE_FAIL], IN_PROGRESS),
            # Reject from in_progress -> rejected
            ([START, READBACK_PASS, REJECT], REJECTED),
            # Advance from rejected -> pending (next phase)
            ([START, READBACK_PASS, REJECT, ADVANCE], PENDING),
            # Skip from pending -> skipped, advance -> pending
            ([SKIP], SKIPPED),
            ([SKIP, ADVANCE], PENDING),
            # Advance from complete -> pending (next phase)
            ([START, READBACK_PASS, END, GATE_PASS, ADVANCE], PENDING),
            # Readback retry loop - three attempts, third passes
            (
                [
                    START, READBACK_FAIL,
                    START, READBACK_FAIL,
                    START, READBACK_PASS,
                ],
                IN_PROGRESS,
            ),
            # Gate retry loop - three attempts, third passes
            (
                [
                    START, READBACK_PASS,
                    END, GATE_FAIL,
                    END, GATE_FAIL,
                    END, GATE_PASS,
                ],
                COMPLETE,
            ),
        ],
        ids=[
            "happy_path", "readback_fail", "gate_fail", "reject_in_progress",
            "advance_from_rejected", "skip", "skip_advance",
            "advance_from_complete", "readback_retry", "gate_retry",
        ],
    )
    def test_lifecycle_path(self, fsm, events, final_state):
        for evt in events:
            fsm.fire(evt)
        assert fsm.current_state == final_state

    def test_simulate_produces_reports_and_preserves_state(self, fsm):
        """simulate() drives the FSM through phase lists without mutating
        the real state, returning one report per phase with transitions."""
        fsm.fire(START)  # put the real FSM in READBACK

        reports = fsm.simulate(["RESEARCH", "PLAN", "IMPLEMENT"])
        assert len(reports) == 3
        for r in reports:
            assert r["valid"] is True
            assert len(r["transitions"]) == 5  # 5 transitions per phase lifecycle

        # simulate() must not mutate the real state
        assert fsm.current_state == READBACK
