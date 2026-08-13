"""Functional end-to-end tests for the svg-infographics toolchain.

Exercises the workflows an agent actually runs - scaffold, map, workflow
status, layer-filtered placement, connector routing gates, arrival
validators, the ship gate - through the Python API and the console CLI
(``python -m stellars_claude_code_plugins.svg_tools.cli``).
"""

import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

CLI = [sys.executable, "-m", "stellars_claude_code_plugins.svg_tools.cli"]


def run_cli(*args, **kwargs):
    return subprocess.run(CLI + [str(a) for a in args], capture_output=True, text=True, **kwargs)


# The open tag every hand-written CSS fixture below starts from.
SVG_OPEN = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'


def css_rules(tmp_path, svg: str, name: str = "t.svg") -> list[str]:
    """The rule names `check_css_compliance` reports for `svg`.

    Six classes carried a byte-identical private copy of this, so widening the
    checker's signature meant editing the same four lines six times.
    """
    from stellars_claude_code_plugins.svg_tools.check_css import check_css_compliance

    f = tmp_path / name
    f.write_text(svg)
    violations, _stats = check_css_compliance(str(f))
    return [v.rule for v in violations]


def roster(tmp_path, svg: str, name: str = "r.svg"):
    """`({label: (status, note)}, counts)` - the gate's checklist for `svg`."""
    from stellars_claude_code_plugins.svg_tools.finalize import build_checklist, finalize

    f = tmp_path / name
    f.write_text(svg)
    ran: set[str] = set()
    hard, soft = finalize(f, None, ran)
    rows, counts = build_checklist(f, hard, soft, rendered=False, ran=ran)
    return {label: (status, note) for _g, label, status, note in rows}, counts


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def layered_scene(tmp_path):
    """A five-layer scene: two cards, one clean connector, a callout blob."""
    svg = tmp_path / "scene.svg"
    svg.write_text(
        textwrap.dedent("""\
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 400">
          <style>
            .card { fill: #0284c7; fill-opacity: 0.05; stroke: #0284c7; stroke-width: 1; }
            .fg-1 { fill: #1e3a5f; }
            @media (prefers-color-scheme: dark) {
              .card { stroke: #4fb7ea; }
              .fg-1 { fill: #cfe2f5; }
            }
          </style>
          <rect x="0" y="0" width="640" height="400" fill="transparent"/>
          <g id="background"></g>
          <g id="nodes">
            <g id="card-src"><rect class="card" x="60" y="60" width="160" height="80"/></g>
            <g id="card-tgt"><rect class="card" x="420" y="260" width="160" height="80"/></g>
          </g>
          <g id="connectors">
            <path id="conn-ok" d="M222,100 L500,100 L500,258" fill="none" stroke="#0284c7" stroke-width="1.2" opacity="0.4"/>
          </g>
          <g id="content">
            <text class="fg-1" x="140" y="105" font-size="11" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif">source</text>
          </g>
          <g id="callouts">
            <g id="callout-note"><rect x="80" y="300" width="120" height="50" fill="#7c3aed" fill-opacity="0.1" stroke="#7c3aed"/></g>
          </g>
        </svg>
    """)
    )
    return svg


@pytest.fixture
def parallel_arrival_svg(tmp_path):
    """Connector arriving parallel along the target's top edge (the bane)."""
    svg = tmp_path / "parallel.svg"
    svg.write_text(
        textwrap.dedent("""\
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 260">
          <style>
            .card { fill: #0284c7; fill-opacity: 0.05; stroke: #0284c7; stroke-width: 1; }
            @media (prefers-color-scheme: dark) { .card { stroke: #4fb7ea; } }
          </style>
          <g id="nodes">
            <rect id="card-src" class="card" x="100" y="30" width="120" height="50"/>
            <rect id="card-tgt" class="card" x="400" y="100" width="120" height="60"/>
          </g>
          <g id="connectors">
            <path id="conn-bane" d="M160,80 L160,98 L458,98" fill="none" stroke="#0284c7" stroke-width="1.2" opacity="0.4"/>
            <polygon points="466,98 456,93 456,103" fill="#0284c7" opacity="0.6"/>
          </g>
        </svg>
    """)
    )
    return svg


# ---------------------------------------------------------------------------
# Scaffold pipeline: every format births a file that passes every gate
# ---------------------------------------------------------------------------


class TestScaffoldPipeline:
    @pytest.mark.parametrize(
        "fmt",
        [
            "doc-stats",
            "doc-timeline",
            "doc-flow",
            "doc-header",
            "doc-grid",
            "slide-16x9",
            "slide-4x3",
            "square",
        ],
    )
    def test_every_format_scaffolds_clean(self, tmp_path, fmt):
        """scaffold -> validate -> check -> finalize, zero findings, for
        every preset - tools produce good stuff by design."""
        from stellars_claude_code_plugins.svg_tools.finalize import finalize

        out = tmp_path / f"{fmt}.svg"
        r = run_cli(
            "scaffold",
            "--format",
            fmt,
            "--cards",
            "3",
            "--title",
            "TITLE",
            "--out",
            out,
        )
        assert r.returncode == 0, r.stderr

        v = run_cli("validate", "--svg", out)
        assert v.returncode == 0, v.stderr + v.stdout

        c = run_cli("check", "--svg", out, "--cards", "3")
        c_out = c.stdout + c.stderr
        assert "check: OK" in c_out, c_out
        assert "layer_discipline" not in c_out

        hard, soft = finalize(out)
        assert hard == [], f"{fmt}: HARD findings on fresh scaffold: {hard}"
        assert soft == [], f"{fmt}: SOFT findings on fresh scaffold: {soft}"

    def test_grid_snaps_to_5px(self):
        """Columns, rows and sizes land on the 5px layout grid for the
        5-divisible canvases."""
        from stellars_claude_code_plugins.svg_tools.scaffold import FORMATS, compute_grid

        for fmt_name in ("doc-grid", "slide-16x9", "square"):
            grid = compute_grid(FORMATS[fmt_name], cols=3, rows=2)
            for v in grid["columns"] + grid["rows"] + [grid["col_w"], grid["row_h"]]:
                assert v % 5 == 0, f"{fmt_name}: {v} not on 5px grid ({grid})"

    def test_cards_overflow_grid_errors(self, tmp_path):
        r = run_cli(
            "scaffold",
            "--format",
            "doc-grid",
            "--cols",
            "2",
            "--rows",
            "1",
            "--cards",
            "5",
            "--out",
            tmp_path / "x.svg",
        )
        assert r.returncode == 2
        assert "does not fit" in r.stderr

    def test_scaffold_stdout_when_no_out(self):
        r = run_cli("scaffold", "--format", "doc-stats")
        assert r.returncode == 0
        assert "<svg xmlns" in r.stdout
        assert '<g id="callouts">' in r.stdout

    def test_doc_header_slot_anatomy(self, tmp_path):
        """doc-header without --cards ships slot placeholders (banner
        plate, title, subtitle, logo, decor) instead of grid cards - and
        still finalizes clean."""
        from stellars_claude_code_plugins.svg_tools.finalize import finalize

        out = tmp_path / "header.svg"
        r = run_cli("scaffold", "--format", "doc-header", "--out", out)
        assert r.returncode == 0, r.stderr
        text = out.read_text()
        for sid in ("slot-banner-plate", "slot-title", "slot-subtitle", "slot-logo", "slot-decor"):
            assert f'id="{sid}" data-placeholder="true"' in text, sid
        assert 'id="card-1"' not in text
        hard, soft = finalize(out)
        assert hard == [] and soft == [], (hard, soft)
        # --cards still overrides the slot anatomy with grid cards
        r2 = run_cli("scaffold", "--format", "doc-header", "--cards", "2", "--out", out, "--force")
        assert r2.returncode == 0
        assert 'id="card-1"' in out.read_text()

    def test_multi_granularity_grid_layers(self, tmp_path):
        """Hidden grid-100 / grid-20 / grid-5 pattern layers ship in every
        scaffold, invisible to the checkers (defs + display=none)."""
        out = tmp_path / "g.svg"
        run_cli("scaffold", "--format", "slide-16x9", "--out", out)
        text = out.read_text()
        for scale in (100, 20, 5):
            assert f'<g id="grid-{scale}" display="none">' in text
            assert f'id="grid-pat-{scale}"' in text
        r = run_cli("connectors", "--svg", out)
        assert "Found 0 connectors" in r.stdout


# ---------------------------------------------------------------------------
# Routing: direction gates at calc time
# ---------------------------------------------------------------------------


class TestRoutingGatesFunctional:
    def _connector(self, *args):
        return run_cli(
            "connector",
            "--mode",
            "l-chamfer",
            "--chamfer",
            "4",
            "--standoff",
            "2",
            "--arrow",
            "end",
            "--direction",
            "forward",
            *args,
        )

    def test_infeasible_end_dir_blocks(self):
        """E->S with target at the same height: gate must block with
        ROUTE-DIR-REVERSED-END and ROUTE-THROUGH-TARGET."""
        r = self._connector(
            "--src-rect",
            "100,100,120,60",
            "--start-dir",
            "E",
            "--tgt-rect",
            "400,100,120,60",
            "--end-dir",
            "S",
        )
        assert r.returncode == 2
        assert "ROUTE-DIR-REVERSED-END" in r.stderr
        assert "ROUTE-THROUGH-TARGET" in r.stderr

    def test_same_axis_pair_needs_z_route(self):
        """E->E from a 1-bend threader violates the start axis - gate fires."""
        r = self._connector(
            "--src-rect",
            "100,100,120,60",
            "--start-dir",
            "E",
            "--tgt-rect",
            "400,300,120,60",
            "--end-dir",
            "E",
        )
        assert r.returncode == 2
        assert "ROUTE-AXIS-MISMATCH" in r.stderr

    def test_feasible_pair_passes(self):
        """E->S with the target below-right: clean 1-bend, gate stays open."""
        r = self._connector(
            "--src-rect",
            "100,100,120,60",
            "--start-dir",
            "E",
            "--tgt-rect",
            "400,300,120,60",
            "--end-dir",
            "S",
        )
        assert r.returncode == 0, r.stderr
        assert "trimmed for arrowhead" in r.stdout

    def test_reversed_start_sign_blocks(self):
        """start_dir=W with the target east: axis matches (h) but the sign
        is opposite - the old axis-only check let this through."""
        r = run_cli(
            "connector",
            "--mode",
            "l",
            "--from",
            "100,100",
            "--to",
            "400,300",
            "--start-dir",
            "W",
            "--arrow",
            "end",
            "--direction",
            "forward",
        )
        assert r.returncode == 2
        assert "ROUTE-DIR-REVERSED:" in r.stderr

    def test_ack_token_survives_flag_changes(self):
        """The stale-token burner: a token issued in run A still acks the
        same warning after an unrelated flag is added in run B."""
        base = [
            "connector",
            "--mode",
            "l-chamfer",
            "--src-rect",
            "100,100,120,60",
            "--start-dir",
            "E",
            "--tgt-rect",
            "400,300,120,60",
            "--end-dir",
            "S",
            "--chamfer",
            "4",
            "--standoff",
            "2",
            "--arrow",
            "end",
        ]
        first = run_cli(*base)  # missing --direction -> warning + token
        assert first.returncode == 2
        import re

        tokens = sorted(set(re.findall(r"W-[0-9a-f]{8}", first.stderr)))
        assert len(tokens) == 1
        second = run_cli(
            *base,
            "--color",
            "#7c3aed",
            "--ack-warning",
            f"{tokens[0]}=direction defaults acceptable in test",
        )
        assert second.returncode == 0, second.stderr
        assert "Acknowledged 1 warning" in second.stderr


# ---------------------------------------------------------------------------
# Post-hoc validators: parallel arrivals on all four edges
# ---------------------------------------------------------------------------


class TestArrivalValidatorFunctional:
    def _card(self):
        from stellars_claude_code_plugins.svg_tools.check_connectors import BBox, CardRect

        return [CardRect(elem_id="card", label="card", bbox=BBox(200, 200, 100, 100))]

    @pytest.mark.parametrize(
        "points,edge",
        [
            ([(50, 198), (248, 198)], "top"),  # eastbound along top edge
            ([(50, 302), (248, 302)], "bottom"),  # eastbound along bottom edge
            ([(198, 50), (198, 248)], "left"),  # southbound along left edge
            ([(302, 50), (302, 248)], "right"),  # southbound along right edge
        ],
    )
    def test_parallel_arrival_each_edge_flagged(self, points, edge):
        from stellars_claude_code_plugins.svg_tools.check_connectors import (
            Connector,
            check_edge_arrival_direction,
        )

        conn = Connector(elem_id="c", tag="path", points=points)
        issues = check_edge_arrival_direction([conn], self._card())
        assert len(issues) == 1, f"{edge}: {issues}"
        assert f"{edge} edge" in issues[0]

    @pytest.mark.parametrize(
        "points",
        [
            [(250, 100), (250, 198)],  # perpendicular into top
            [(250, 400), (250, 302)],  # perpendicular into bottom
            [(80, 250), (198, 250)],  # perpendicular into left
            [(420, 250), (302, 250)],  # perpendicular into right
        ],
    )
    def test_perpendicular_arrival_each_edge_clean(self, points):
        from stellars_claude_code_plugins.svg_tools.check_connectors import (
            Connector,
            check_edge_arrival_direction,
        )

        conn = Connector(elem_id="c", tag="path", points=points)
        assert check_edge_arrival_direction([conn], self._card()) == []

    def test_cli_flags_parallel_arrival_and_arrowhead(self, parallel_arrival_svg):
        r = run_cli("connectors", "--svg", parallel_arrival_svg)
        assert "[edge-arrival]" in r.stdout
        assert "[arrowhead-edge]" in r.stdout

    def test_finalize_blocks_parallel_arrival_as_hard(self, parallel_arrival_svg):
        r = run_cli("finalize", parallel_arrival_svg)
        assert r.returncode == 2  # warning-ack gate blocks
        assert "HARD: [connectors] [edge-arrival]" in r.stderr

    def test_manifold_candidates_reported_by_cli(self, tmp_path):
        """Three strokes sharing one endpoint: the standalone connectors CLI
        must suggest a manifold (used to be finalize-only)."""
        svg = tmp_path / "fan.svg"
        svg.write_text(
            textwrap.dedent("""\
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300">
              <g id="connectors">
                <path id="f1" d="M50,50 L200,150" fill="none" stroke="#000"/>
                <path id="f2" d="M50,150 L200,150" fill="none" stroke="#000"/>
                <path id="f3" d="M50,250 L200,150" fill="none" stroke="#000"/>
              </g>
            </svg>
        """)
        )
        r = run_cli("connectors", "--svg", svg)
        assert "manifold-candidate" in r.stdout


# ---------------------------------------------------------------------------
# Layers: transparency, hidden guides, filters
# ---------------------------------------------------------------------------


class TestLayerAwareness:
    def test_guide_grid_not_connectors(self, tmp_path):
        """display="none" guide lines must not classify as connectors."""
        svg = tmp_path / "guides.svg"
        svg.write_text(
            textwrap.dedent("""\
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300">
              <g id="guide-grid" display="none">
                <line x1="100" y1="0" x2="100" y2="300" stroke="red"/>
                <line x1="0" y1="150" x2="400" y2="150" stroke="red"/>
              </g>
            </svg>
        """)
        )
        r = run_cli("connectors", "--svg", svg)
        assert "Found 0 connectors" in r.stdout

    def test_layer_groups_transparent_in_overlaps(self, layered_scene):
        """The five layer wrappers must not be compared as atomic bboxes -
        the callout blob inside <g id="callouts"> would otherwise overlap
        the whole nodes-layer bbox."""
        from stellars_claude_code_plugins.svg_tools.check_overlaps import (
            analyze_overlaps,
            parse_svg,
        )

        elements = parse_svg(str(layered_scene))
        violations = [
            (a.label, b.label)
            for _i, _j, a, b, _pct, cls in analyze_overlaps(elements)
            if cls == "violation"
        ]
        assert violations == [], violations

    def test_empty_space_layer_filters(self, layered_scene):
        """Include / exclude semantics move free area the right way."""
        from stellars_claude_code_plugins.svg_tools.calc_empty_space import (
            find_empty_regions,
        )

        def total_free(**kw):
            regions = find_empty_regions(
                str(layered_scene),
                tolerance=2,
                min_area=100,
                exclude_ids=(),
                **kw,
            )
            return sum(r["area"] for r in regions)

        baseline = total_free()
        nodes_only = total_free(layers=("nodes",))
        no_nodes = total_free(ignore_layers=("nodes",))
        assert nodes_only > baseline  # fewer obstacle sources -> more free
        assert no_nodes > nodes_only  # cards dwarf the connector+text+callout

    def test_empty_space_unknown_layer_rejected(self, layered_scene):
        from stellars_claude_code_plugins.svg_tools.calc_empty_space import (
            find_empty_regions,
        )

        with pytest.raises(ValueError, match="unknown layer"):
            find_empty_regions(str(layered_scene), layers=("cards",))

    def test_empty_space_cli_layer_flags(self, layered_scene):
        ok = run_cli(
            "empty-space",
            "--svg",
            layered_scene,
            "--ignore-layers",
            "callouts",
            "--tolerance",
            "20",
        )
        assert ok.returncode == 0, ok.stderr
        bad = run_cli("empty-space", "--svg", layered_scene, "--layers", "bogus")
        assert bad.returncode == 2
        assert "unknown layer" in bad.stderr

    def test_auto_route_ignore_layers_unblocks(self, tmp_path):
        """An obstacle wall in the callouts layer forces a detour; ignoring
        the callouts layer lets the router go straight through."""
        svg = tmp_path / "wall.svg"
        svg.write_text(
            textwrap.dedent("""\
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 300">
              <g id="nodes">
                <rect id="a" x="40" y="120" width="80" height="60" fill="#0284c7" fill-opacity="0.1"/>
                <rect id="b" x="480" y="120" width="80" height="60" fill="#0284c7" fill-opacity="0.1"/>
              </g>
              <g id="callouts">
                <rect id="wall" x="280" y="20" width="40" height="260" fill="#7c3aed"/>
              </g>
            </svg>
        """)
        )
        from stellars_claude_code_plugins.svg_tools.calc_connector import calc_l

        detour = calc_l(
            src_rect=(40, 120, 80, 60),
            start_dir="E",
            tgt_rect=(480, 120, 80, 60),
            end_dir="E",
            auto_route=True,
            svg=str(svg),
            arrow="end",
        )
        direct = calc_l(
            src_rect=(40, 120, 80, 60),
            start_dir="E",
            tgt_rect=(480, 120, 80, 60),
            end_dir="E",
            auto_route=True,
            svg=str(svg),
            arrow="end",
            route_ignore_layers=("callouts",),
        )

        # Ignoring the wall must never yield a longer route.
        def path_len(res):
            pts = res["samples"]
            return sum(
                abs(pts[i + 1][0] - pts[i][0]) + abs(pts[i + 1][1] - pts[i][1])
                for i in range(len(pts) - 1)
            )

        assert path_len(direct) <= path_len(detour)
        # And the direct route may pass straight through the wall band.
        xs = [p[0] for p in direct["samples"]]
        assert max(xs) >= 470

    def test_manifest_layer_discipline_warns(self, tmp_path, parallel_arrival_svg):
        """SVG without the five layers -> layer_discipline WARN; a
        misordered file warns about z-order."""
        r = run_cli("check", "--svg", parallel_arrival_svg)
        r_out = r.stdout + r.stderr
        assert "layer_discipline" in r_out
        assert "missing canonical layer group(s)" in r_out

        misordered = tmp_path / "misordered.svg"
        misordered.write_text(
            textwrap.dedent("""\
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
              <style>@media (prefers-color-scheme: dark) { .x { fill: #fff; } }</style>
              <g id="callouts"></g>
              <g id="background"></g>
              <g id="nodes"></g>
              <g id="connectors"></g>
              <g id="content"></g>
            </svg>
        """)
        )
        r2 = run_cli("check", "--svg", misordered)
        assert "out of z-order" in r2.stdout + r2.stderr


# ---------------------------------------------------------------------------
# Space map
# ---------------------------------------------------------------------------


class TestSpaceMapFunctional:
    def test_map_letters_and_stats(self, layered_scene):
        r = run_cli("map", "--svg", layered_scene, "--cell", "20")
        assert r.returncode == 0, r.stderr
        grid = "\n".join(line for line in r.stdout.splitlines() if line.startswith("  "))
        for letter in ("n", "c", "t", "o"):
            assert letter in grid, f"letter {letter} missing from map:\n{r.stdout}"
        assert "layer occupancy:" in r.stdout
        assert "free regions" in r.stdout

    def test_map_json_shape(self, layered_scene):
        r = run_cli("map", "--svg", layered_scene, "--json")
        report = json.loads(r.stdout)
        assert set(report) == {"canvas", "cell", "grid", "layers", "free_regions"}
        assert report["free_regions"], "expected at least one placement rect"
        first = report["free_regions"][0]
        assert first["area"] >= report["free_regions"][-1]["area"]
        # every free rect lies inside the canvas
        x0, y0, w, h = report["canvas"]
        for rect in report["free_regions"]:
            assert x0 <= rect["x"] and rect["x"] + rect["w"] <= x0 + w + report["cell"]
            assert y0 <= rect["y"] and rect["y"] + rect["h"] <= y0 + h + report["cell"]

    def test_map_api_topmost_wins(self, layered_scene):
        """Cells where the callout blob sits show 'o' even though nodes/
        content may also occupy - topmost layer wins."""
        from stellars_claude_code_plugins.svg_tools.space_map import space_map

        report = space_map(str(layered_scene), cell=20)
        joined = "\n".join(report["grid"])
        assert "o" in joined
        assert report["layers"]["callouts"]["occupancy_pct"] > 0


# ---------------------------------------------------------------------------
# Workflow status
# ---------------------------------------------------------------------------


class TestWorkflowStatusFunctional:
    def test_missing_file_phase_scaffold(self, tmp_path):
        r = run_cli("workflow", "--svg", tmp_path / "nope.svg")
        assert "PHASE: scaffold" in r.stdout
        assert "scaffold --format" in r.stdout

    def test_fresh_scaffold_phase_author(self, tmp_path):
        out = tmp_path / "wip.svg"
        run_cli(
            "scaffold",
            "--format",
            "slide-16x9",
            "--cards",
            "2",
            "--title",
            "T",
            "--out",
            out,
        )
        r = run_cli("workflow", "--svg", out)
        assert "PHASE: author" in r.stdout
        assert "placeholder" in r.stdout
        # scaffold gate already satisfied - no repeated scaffold work
        assert "[x] scaffold" in r.stdout

    def test_authored_file_progresses_past_author(self, tmp_path):
        """Stripping data-placeholder + filling description + text moves the
        file to the finalize/ship end of the pipeline."""
        out = tmp_path / "wip.svg"
        run_cli(
            "scaffold",
            "--format",
            "doc-flow",
            "--cards",
            "2",
            "--title",
            "FLOW",
            "--out",
            out,
        )
        content = out.read_text()
        content = content.replace(' data-placeholder="true"', "")
        content = content.replace("<short role description>", "flow band")
        out.write_text(content)
        r = run_cli("workflow", "--svg", out, "--json")
        report = json.loads(r.stdout)
        assert report["phase"] in ("ship", "finalize")
        gates = {g["gate"]: g["ok"] for g in report["gates"]}
        assert gates["scaffold"] and gates["author"] and gates["content"]

    def test_json_gates_shape(self, tmp_path):
        out = tmp_path / "wip.svg"
        run_cli("scaffold", "--format", "square", "--out", out)
        r = run_cli("workflow", "--svg", out, "--json", "--no-finalize")
        report = json.loads(r.stdout)
        assert [g["gate"] for g in report["gates"]] == ["scaffold", "author", "content"]
        assert all({"gate", "ok", "detail", "next"} <= set(g) for g in report["gates"])


# ---------------------------------------------------------------------------
# CLI grammar parity
# ---------------------------------------------------------------------------


class TestCliGrammar:
    def test_validate_accepts_both_forms(self, tmp_path):
        out = tmp_path / "s.svg"
        run_cli("scaffold", "--format", "doc-stats", "--out", out)
        positional = run_cli("validate", out)
        flagged = run_cli("validate", "--svg", out)
        assert positional.returncode == 0
        assert flagged.returncode == 0

    def test_validate_no_files_errors(self):
        r = run_cli("validate")
        assert r.returncode == 2
        assert "no SVG files" in r.stderr

    def test_catalogue_lists_new_subcommands(self):
        r = run_cli("--help")
        for sub in ("scaffold", "workflow", "map"):
            assert sub in r.stdout


class TestArrowheadAxisFunctional:
    """The arrowhead must continue the stroke that stops short of it.

    A connector's stroke is trimmed by the head length to make room for the
    head. On a curve whose tangent turns over that trimmed stretch, a head
    built on the tangent AT the endpoint points somewhere the visible stroke
    never went, and reads as a bent flag. Regression: manifold fan strands
    shipped with heads 17-18 degrees off their own line on this fixture, and
    18-22 on the deck that reported it.
    """

    @staticmethod
    def _fan():
        from stellars_claude_code_plugins.svg_tools.calc_connector import calc_manifold

        return calc_manifold(
            starts=[(1000, 475)],
            ends=[(1103, 405), (1103, 440), (1103, 475), (1103, 510), (1103, 545)],
            spine_start=(1020, 475),
            spine_end=(1060, 475),
            shape="spline",
            head_len=10,
            head_half_h=5,
            arrow="end",
        )

    @staticmethod
    def _axis_vs_arrival(strand):
        import math
        import re

        tip, a, b = strand["end"]["arrow"]["polygon"]
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        axis = math.degrees(math.atan2(tip[1] - mid[1], tip[0] - mid[0]))
        pts = re.findall(r"[-\d.]+,[-\d.]+", strand["trimmed_path_d"])
        ex, ey = (float(v) for v in pts[-1].split(","))
        arrival = math.degrees(math.atan2(tip[1] - ey, tip[0] - ex))
        return abs((axis - arrival + 180) % 360 - 180)

    def test_curved_strand_heads_follow_their_stroke(self):
        for i, strand in enumerate(self._fan()["end_strands"]):
            delta = self._axis_vs_arrival(strand)
            assert delta < 1.0, f"end strand {i}: head {delta:.1f}deg off its stroke"

    def test_straight_strand_is_exact(self):
        # The middle strand of the fan is straight - chord and tangent agree,
        # so the fix must be a no-op there.
        # abs=1e-3, not 1e-9: trimmed_path_d round-trips through a %.2f string,
        # so a tighter bar passes on rounding luck rather than on the property.
        assert self._axis_vs_arrival(self._fan()["end_strands"][2]) == pytest.approx(0.0, abs=1e-3)

    @staticmethod
    def _svg_with(tmp_path, name, stroke_d, poly_pts):
        f = tmp_path / name
        f.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">'
            f'<path d="{stroke_d}" fill="none" stroke="#000"/>'
            f'<polygon points="{poly_pts}"/>'
            "</svg>"
        )
        return f

    @staticmethod
    def _head_rotated(tip, length, half_h, heading_deg, roll_deg):
        """Isoceles head at `tip`, axis rotated `roll_deg` off `heading_deg`."""
        import math

        a = math.radians(heading_deg + roll_deg)
        pts = [tip]
        for sign in (-1, 1):
            lx, ly = -length, sign * half_h
            pts.append(
                (
                    tip[0] + math.cos(a) * lx - math.sin(a) * ly,
                    tip[1] + math.sin(a) * lx + math.cos(a) * ly,
                )
            )
        return " ".join(f"{x:.2f},{y:.2f}" for x, y in pts)

    def _run_gate(self, svg):
        from stellars_claude_code_plugins.svg_tools.check_connectors import (
            check_arrowhead_axis_alignment,
            parse_svg,
        )

        _cards, connectors, _labels, heads = parse_svg(svg)
        return check_arrowhead_axis_alignment(connectors, heads)

    def test_apex_survives_the_ratio_cliff(self):
        """Tip detection must not flip to a base vertex as the head gets stubbier.

        The old rule (furthest from the opposite edge midpoint) held only while
        half_h < length/sqrt(3) = 0.577 - and the connector docs recommend head
        sizes on both sides of that line.
        """
        import math
        import tempfile

        from stellars_claude_code_plugins.svg_tools.check_connectors import parse_svg

        for length, half_h in ((10, 5), (10, 5.8), (8, 6), (9, 7), (4, 3)):
            pts = self._head_rotated((300.0, 200.0), length, half_h, 0.0, 0.0)
            with tempfile.NamedTemporaryFile("w", suffix=".svg", delete=False) as fh:
                fh.write(
                    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">'
                    f'<polygon points="{pts}"/></svg>'
                )
                path = fh.name
            head = parse_svg(path)[3][0]
            assert head.tip == pytest.approx((300.0, 200.0)), (
                f"head {length},{half_h}: apex misdetected as {head.tip}"
            )
            assert head.length == pytest.approx(length, abs=1e-6)
            assert math.isclose(head.length, length, rel_tol=1e-9)

    def test_gate_flags_a_head_rotated_off_its_line(self, tmp_path):
        # Stroke arrives heading east and stops one head length short; the head
        # is a correct isoceles triangle rolled 20 degrees off that arrival.
        pts = self._head_rotated((300.0, 200.0), 10.0, 5.0, 0.0, 20.0)
        svg = self._svg_with(tmp_path, "rolled.svg", "M200,200 L290,200", pts)
        issues = self._run_gate(svg)
        assert issues, "a head rolled 20deg off its own stroke must be caught"
        assert "arrowhead-axis" in issues[0]
        assert "20.0deg off" in issues[0], issues[0]

    def test_gate_passes_an_aligned_head(self, tmp_path):
        pts = self._head_rotated((300.0, 200.0), 10.0, 5.0, 0.0, 0.0)
        svg = self._svg_with(tmp_path, "aligned.svg", "M200,200 L290,200", pts)
        assert self._run_gate(svg) == []

    def test_tolerance_bar_is_pinned(self, tmp_path):
        """The documented 10deg bar must be the bar - mutating it has to fail."""
        under = self._head_rotated((300.0, 200.0), 10.0, 5.0, 0.0, 8.0)
        over = self._head_rotated((300.0, 200.0), 10.0, 5.0, 0.0, 12.0)
        assert self._run_gate(self._svg_with(tmp_path, "u.svg", "M200,200 L290,200", under)) == []
        assert self._run_gate(self._svg_with(tmp_path, "o.svg", "M200,200 L290,200", over))

    def test_pairing_ignores_a_stroke_that_merely_passes_close(self, tmp_path):
        """Nearest-endpoint pairing bound heads to unrelated ticks; the band must not."""
        pts = self._head_rotated((300.0, 200.0), 10.0, 5.0, 0.0, 0.0)
        svg = self._svg_with(tmp_path, "dense.svg", "M200,200 L290,200", pts)
        svg.write_text(
            svg.read_text().replace(
                "</svg>", '<path d="M296,194 L296,186" fill="none" stroke="#000"/></svg>'
            )
        )
        assert self._run_gate(svg) == [], "a 6px tick near the tip is not the head's stroke"


class TestCornerArrivalFunctional:
    """A head must not be rotated by a corner that sits inside the trimmed stretch.

    Where an L route's final leg is shorter than the head, the chord reaches back
    around the bend. Measured up to 84deg off the true arrival before the clamp -
    a diagonal arrow onto an edge it should enter square, with no warning.
    """

    def test_short_final_leg_still_arrives_square(self):
        import math

        from stellars_claude_code_plugins.svg_tools.calc_connector import calc_l

        for dy in (2, 4, 6, 8, 10, 20):
            r = calc_l(
                src_x=100,
                src_y=160 - dy,
                tgt_x=300,
                tgt_y=160,
                head_len=10,
                head_half_h=5,
                arrow="end",
                stem_min=0,
            )
            tip, a, b = r["end"]["arrow"]["polygon"]
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            axis = math.degrees(math.atan2(tip[1] - mid[1], tip[0] - mid[0]))
            assert axis == pytest.approx(90.0, abs=0.5), (
                f"final leg dy={dy}: head at {axis:.2f}deg"
            )


class TestChecklistRoster:
    """The roster exists so an unchecked aspect is visible, not silently a pass."""

    @staticmethod
    def _svg(tmp_path):
        f = tmp_path / "roster.svg"
        f.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.a { fill: #0b2d3c; }"
            "@media (prefers-color-scheme: dark) { .a { fill: #e4f3fa; } }</style>"
            '<text class="a" x="20" y="40" font-family="Arial" font-size="14">hello</text>'
            "</svg>"
        )
        return f

    def test_absent_subject_reports_na_not_pass(self, tmp_path):
        from stellars_claude_code_plugins.svg_tools.finalize import build_checklist, finalize

        svg = self._svg(tmp_path)
        hard, soft = finalize(svg)
        rows, counts = build_checklist(svg, hard, soft, rendered=False)
        by_label = {label: status for _g, label, status, _n in rows}
        # No connectors and no arrowheads in this file - those rows must not
        # claim a pass they never earned.
        assert by_label["head continues its stroke"] == "NA"
        assert by_label["no zero-length segments"] == "NA"
        assert by_label["rendered geometry"] == "NA"
        assert counts["NA"] >= 3

    def test_theme_rows_read_the_real_block(self, tmp_path):
        from stellars_claude_code_plugins.svg_tools.finalize import build_checklist, finalize

        svg = self._svg(tmp_path)
        ran: set[str] = set()
        hard, soft = finalize(svg, None, ran)
        rows, _ = build_checklist(svg, hard, soft, rendered=False, ran=ran)
        by_label = {label: status for _g, label, status, _n in rows}
        assert by_label["dark block present"] == "PASS"
        # A real PASS, earned by a layer that ran - not a row defaulting to
        # SKIP because `finalize` forgot to record its layer.
        assert by_label["overrides change the rendering"] == "PASS"
        assert by_label["no #000/#fff"] == "PASS"
        assert by_label["text meets WCAG AA"] == "PASS"

        # Strip the dark block: presence fails, and the rows that depend on it
        # go NA rather than passing on an absent block.
        plain = tmp_path / "plain.svg"
        plain.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.a { fill: #0b2d3c; }</style>"
            '<text class="a" x="20" y="40" font-family="Arial" font-size="14">hello</text>'
            "</svg>"
        )
        rows2, _ = build_checklist(plain, *finalize(plain), rendered=False)
        by2 = {label: status for _g, label, status, _n in rows2}
        assert by2["dark block present"] == "FAIL"
        assert by2["overrides change the rendering"] == "NA"

    def test_every_roster_row_renders(self, tmp_path):
        from stellars_claude_code_plugins.svg_tools.finalize import (
            build_checklist,
            finalize,
            format_checklist,
        )

        svg = self._svg(tmp_path)
        rows, counts = build_checklist(svg, *finalize(svg), rendered=False)
        out = format_checklist("roster.svg", rows, counts)
        for _g, label, _s, _n in rows:
            assert label in out
        assert f"{sum(counts.values())} aspects" in out

    def test_unrun_layer_reports_skip_not_pass(self, tmp_path):
        """Malformed XML aborts every downstream layer - none of them passed."""
        from stellars_claude_code_plugins.svg_tools.finalize import build_checklist, finalize

        broken = tmp_path / "broken.svg"
        # Unclosed root: validate errors, so finalize returns before css /
        # contrast / connectors run. The file also carries a literal #ffffff and
        # an inert dark block, both of which those layers would have caught.
        broken.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.a { fill: #111111; }"
            "@media (prefers-color-scheme: dark) { .a { fill: #111112; } }</style>"
            '<rect width="400" height="200" fill="#ffffff"/>'
            '<text class="a" x="20" y="40">hello</text>'
        )
        ran: set[str] = set()
        hard, soft = finalize(broken, None, ran)
        rows, counts = build_checklist(broken, hard, soft, rendered=False, ran=ran)
        by_label = {label: status for _g, label, status, _n in rows}

        assert by_label["xml well-formed"] == "FAIL"
        # The exact rows that would have caught the seeded defects.
        assert by_label["no #000/#fff"] == "SKIP"
        assert by_label["overrides change the rendering"] == "SKIP"
        assert by_label["text meets WCAG AA"] == "SKIP"
        assert counts["PASS"] <= 1  # only the raw-text dark-block probe can pass
        assert counts["SKIP"] >= 20

    def test_crashed_layer_does_not_pass_its_rows(self, tmp_path):
        """A `check failed` diagnostic carries no rule token - it must still fail."""
        from stellars_claude_code_plugins.svg_tools.finalize import build_checklist

        svg = self._svg(tmp_path)
        soft = ["[css] check failed: could not convert string to float: '50%'"]
        rows, _ = build_checklist(svg, [], soft, rendered=False, ran={"css"})
        theme = {label: status for g, label, status, _n in rows if g == "theme"}
        for label, status in theme.items():
            if label == "dark block present":
                continue
            assert status == "SKIP", f"{label} read {status} on a crashed css layer"

    def test_no_finding_is_unrepresented_on_the_corpus(self):
        """Every real finding must land on a FAIL row.

        The roster restates rule names as string literals, so nothing but a
        corpus run binds a row to the checker it claims to report. Before this
        test, 1046 findings across 20 example files sat behind rows printing
        NA, and 62 more matched no row at all - both invisible to a suite that
        only ever asserted on synthetic files.
        """
        import glob
        from pathlib import Path as _P

        from stellars_claude_code_plugins.svg_tools.finalize import build_checklist, finalize

        files = sorted(glob.glob("svg-infographics/examples/*.svg"))
        assert files, "example corpus missing"
        unrepresented: list[str] = []
        for p in files:
            path = _P(p)
            ran: set[str] = set()
            hard, soft = finalize(path, None, ran)
            rows, _ = build_checklist(path, hard, soft, rendered=False, ran=ran)
            failing = [
                (layer, token)
                for (_g, label, layer, token, _n) in _checklist_rows()
                if label in {lab for _gg, lab, s, _nn in rows if s == "FAIL"}
            ]
            catch_all = {
                lab for _g, lab, s, _n in rows if s == "FAIL" and lab.startswith("other ")
            }
            for f in hard + soft:
                if "] check failed" in f:
                    continue
                layer = f[1 : f.index("]")]
                if any(
                    f.startswith(f"[{lay}]") and (tok is None or tok in f) for lay, tok in failing
                ):
                    continue
                if f"other {layer.lower()} findings" in catch_all:
                    continue
                unrepresented.append(f"{path.name}: {f[:70]}")
        assert not unrepresented, (
            f"{len(unrepresented)} findings no FAIL row reports: {unrepresented[:3]}"
        )

    def test_every_roster_token_is_a_rule_some_checker_emits(self):
        """A mistyped token is a permanent silent PASS.

        The catch-all row closes "no row claims this finding"; it cannot close
        "this row claims a rule nobody emits" - the misspelled row just goes
        quiet while its findings land in the catch-all. Renaming `edge-snap` to
        `edge_snap` left the corpus test green and the row printing PASS over
        seven real findings.
        """
        from pathlib import Path as _P

        from stellars_claude_code_plugins.svg_tools.finalize import _CHECKLIST

        owners = {
            "css": "check_css.py",
            "connectors": "check_connectors.py",
            "overlaps": "check_overlaps.py",
            "alignment": "check_alignment.py",
            "contrast": "check_contrast.py",
            "collide": "finalize.py",
            "visual": "check_visual.py",
            "validate": "check_svg_valid.py",
        }
        src = _P("src/stellars_claude_code_plugins/svg_tools")
        cache = {n: (src / n).read_text(encoding="utf-8") for n in set(owners.values())}
        orphan = []
        for _group, label, layer, token, _needs in _CHECKLIST:
            if token is None or token.startswith("@"):
                continue
            owner = owners.get(layer)
            assert owner, f"row {label!r} names layer {layer!r} with no known owner module"
            # Delimited, not a bare substring: `edge_snap` occurs inside the
            # function name `check_edge_snap`, so a substring match calls a
            # mistyped token healthy.
            if f"[{token}]" not in cache[owner] and f'"{token}"' not in cache[owner]:
                orphan.append(f"{label!r} -> {token!r} not emitted by {owner}")
        assert not orphan, "roster rows bound to rules nobody emits: " + "; ".join(orphan)

    def test_tier_counts_are_not_conflated(self, tmp_path):
        from stellars_claude_code_plugins.svg_tools.finalize import build_checklist

        svg = self._svg(tmp_path)
        rows, _ = build_checklist(
            svg,
            ["[validate] ERROR one"],
            ["[validate] WARN a", "[validate] WARN b"],
            rendered=False,
            ran={"validate"},
        )
        note = {label: n for _g, label, _s, n in rows}["xml well-formed"]
        assert note == "1 HARD, 2 SOFT", note


def _checklist_rows():
    from stellars_claude_code_plugins.svg_tools.finalize import _CHECKLIST

    return _CHECKLIST


class TestThemeChecksFunctional:
    """Deleting either theme check must break a test.

    A mutation battery over the previous revision killed nothing here: replacing
    `check_dark_mode_effective` or `check_theme_background` with `return []`,
    and dropping `_MIN_THEME_LUM_DELTA` to 0.0, all left the suite green.
    """

    @staticmethod
    def _css(light: str, dark: str, body: str = "") -> str:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            f"<style>{light}@media (prefers-color-scheme: dark) {{{dark}}}</style>"
            f"{body}</svg>"
        )

    def test_inert_dark_block_is_reported(self, tmp_path):
        light = "".join(f".c{i} {{ fill: #10202{i}; }}" for i in range(6))
        dark = "".join(f".c{i} {{ fill: #10202{i}; }}" for i in range(6))
        assert "inert-dark-mode" in css_rules(tmp_path, self._css(light, dark))

    def test_a_real_repaint_is_not_reported(self, tmp_path):
        light = "".join(f".c{i} {{ fill: #10202{i}; }}" for i in range(6))
        dark = "".join(f".c{i} {{ fill: #e8f0f{i}; }}" for i in range(6))
        assert "inert-dark-mode" not in css_rules(tmp_path, self._css(light, dark))

    def test_one_honest_override_does_not_silence_the_rest(self, tmp_path):
        """The `any()` gate let a single repainted class clear 400 inert ones."""
        light = (
            "".join(f".c{i} {{ fill: #10202{i}; }}" for i in range(6)) + ".ok { fill: #ffffff; }"
        )
        dark = (
            "".join(f".c{i} {{ fill: #10202{i}; }}" for i in range(6)) + ".ok { fill: #0a0a0a; }"
        )
        assert "inert-dark-mode" in css_rules(tmp_path, self._css(light, dark))

    def test_threshold_is_pinned_from_below(self, tmp_path):
        """Deltas of 1/255 are inert; a threshold of 0 would call them a repaint."""
        light = "".join(f".c{i} {{ fill: #303030; }}" for i in range(6))
        dark = "".join(f".c{i} {{ fill: #303031; }}" for i in range(6))
        assert "inert-dark-mode" in css_rules(tmp_path, self._css(light, dark))

    def test_theme_invariant_minority_is_allowed(self, tmp_path):
        """Text on a non-inverting accent is legitimately the same in both themes."""
        light = (
            "".join(f".c{i} {{ fill: #10202{i}; }}" for i in range(5)) + ".on { fill: #ffffff; }"
        )
        dark = (
            "".join(f".c{i} {{ fill: #e8f0f{i}; }}" for i in range(5)) + ".on { fill: #ffffff; }"
        )
        assert "inert-dark-mode" not in css_rules(tmp_path, self._css(light, dark))

    def test_inline_filled_backplate_is_reported(self, tmp_path):
        svg = self._css(
            ".a { fill: #101010; }",
            ".a { fill: #f0f0f0; }",
            '<rect width="400" height="200" fill="#fdfdfd"/>',
        )
        assert "unthemed-background" in css_rules(tmp_path, svg)

    def test_backplate_found_without_a_name(self, tmp_path):
        """Only 5 of the 71 example files carry a canvas-covering rect, and
        none of those 5 names it - name-first matching judged almost nothing."""
        svg = self._css(
            ".plate { fill: #fdfdfd; } .a { fill: #101010; }",
            ".plate { fill: #fcfcfc; } .a { fill: #f0f0f0; }",
            '<rect class="plate" width="400" height="200"/>',
        )
        assert "unthemed-background" in css_rules(tmp_path, svg)

    def test_a_decoy_group_does_not_end_the_search(self, tmp_path):
        """Name-first matching stopped at `<g id="background">` holding texture."""
        svg = self._css(
            ".plate { fill: #fdfdfd; } .a { fill: #101010; }",
            ".plate { fill: #fcfcfc; } .a { fill: #f0f0f0; }",
            '<g id="background"><path d="M0 0 L10 10"/></g>'
            '<rect class="plate" width="400" height="200"/>',
        )
        assert "unthemed-background" in css_rules(tmp_path, svg)

    def test_an_inverting_backplate_is_clean(self, tmp_path):
        svg = self._css(
            ".plate { fill: #fdfdfd; } .a { fill: #101010; }",
            ".plate { fill: #0b1620; } .a { fill: #f0f0f0; }",
            '<rect class="plate" width="400" height="200"/>',
        )
        assert "unthemed-background" not in css_rules(tmp_path, svg)

    def test_scaffold_placeholder_plate_is_not_judged(self, tmp_path):
        svg = self._css(
            ".slot { fill: #fdfdfd; } .a { fill: #101010; }",
            ".a { fill: #f0f0f0; }",
            '<rect class="slot" width="400" height="200"/>',
        )
        assert "unthemed-background" not in css_rules(tmp_path, svg)

    def test_stroke_only_classes_need_a_dark_override(self, tmp_path):
        svg = self._css(".rule { stroke: #223344; }", ".other { fill: #ffffff; }")
        assert "missing-dark-override" in css_rules(tmp_path, svg)

    def test_fill_none_is_not_painting(self, tmp_path):
        svg = self._css(".hairline { fill: none; }", ".other { fill: #ffffff; }")
        assert "missing-dark-override" not in css_rules(tmp_path, svg)


class TestLuma255:
    """Both theme checks go blind on any colour format this cannot read."""

    def test_formats(self):
        from stellars_claude_code_plugins.svg_tools.check_css import _luma255

        white = pytest.approx(255.0)
        assert _luma255("#ffffff") == white
        assert _luma255("#fff") == white
        # `!important` is captured into the value by the CSS value regex, and a
        # hex-only match dropped every declaration carrying it - 12 such values
        # are live in this repo's own charts.
        assert _luma255("#ffffff !important") == white
        assert _luma255("rgb(255,255,255)") == white
        assert _luma255("rgba(255, 255, 255, 0.5)") == white
        assert _luma255("#ffffffcc") == white  # 8-digit: alpha ignored
        assert _luma255("#000000") == 0.0
        # Genuinely unresolvable - must stay None rather than guess.
        for unknown in ("var(--x)", "currentColor", "none", "transparent", "", None):
            assert _luma255(unknown) is None

    def test_important_values_are_measured_end_to_end(self, tmp_path):
        from stellars_claude_code_plugins.svg_tools.check_css import check_css_compliance

        f = tmp_path / "imp.svg"
        f.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>" + "".join(f".c{i} {{ fill: #1e3a5{i} !important; }}" for i in range(6)) + ""
            "@media (prefers-color-scheme: dark) {"
            + "".join(f".c{i} {{ fill: #1e3a6{i} !important; }}" for i in range(6))
            + "}</style></svg>"
        )
        violations, _ = check_css_compliance(str(f))
        assert "inert-dark-mode" in [v.rule for v in violations]


class TestRosterHonestyRound3:
    """Rows must not claim more coverage than their checker has.

    Every case here shipped a green row over a file that violates the rule the
    row names - the roster's own failure mode, one level up from the findings.
    """

    def test_forbidden_colour_in_css_is_caught(self, tmp_path):
        """`no #000/#fff` read only presentation attributes, so a class
        declaring `fill: #ffffff` - where the project tells authors to put
        colour - passed the row named for forbidding exactly that."""
        by, _ = roster(
            tmp_path,
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.card { fill: #ffffff; } .t { fill: #000000; }"
            "@media (prefers-color-scheme: dark) { .card { fill: #101820; }"
            " .t { fill: #e8f0f8; } }</style>"
            '<rect class="card" width="400" height="200"/>'
            '<text class="t" x="20" y="40" font-family="Segoe UI, Arial, sans-serif">hi</text>'
            "</svg>",
        )
        assert by["no #000/#fff"][0] == "FAIL"

    def test_backplate_that_gets_lighter_is_not_an_inversion(self, tmp_path):
        """A signless delta called a dark→white flip a 227/255 'inversion'."""
        by, _ = roster(
            tmp_path,
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.bg { fill: #12181e; } .t { fill: #e8f0f8; }"
            "@media (prefers-color-scheme: dark) { .bg { fill: #f7fbff; }"
            " .t { fill: #12181e; } }</style>"
            '<rect class="bg" width="400" height="200"/>'
            '<text class="t" x="20" y="40" font-family="Segoe UI, Arial, sans-serif">hi</text>'
            "</svg>",
        )
        assert by["background inverts"][0] == "FAIL"

    def test_arrowhead_rows_need_every_input_their_checker_consumes(self):
        """Heads but no connectors: the axis checker cannot produce a verdict."""
        from pathlib import Path as _P

        from stellars_claude_code_plugins.svg_tools.finalize import build_checklist, finalize

        p = _P("svg-infographics/examples/65_embroidery_basic_tier.svg")
        if not p.exists():
            pytest.skip("example corpus file missing")
        ran: set[str] = set()
        hard, soft = finalize(p, None, ran)
        rows, _ = build_checklist(p, hard, soft, rendered=False, ran=ran)
        by = {label: status for _g, label, status, _n in rows}
        for row in ("head points into the card", "head continues its stroke", "stem/head ratio"):
            assert by[row] == "NA", f"{row} claimed {by[row]} with no connectors or cards"

    def test_operator_requested_skip_is_not_nagged(self, tmp_path):
        """`--no-visual` is a choice, not an unjudged layer to chase."""
        from stellars_claude_code_plugins.svg_tools.finalize import (
            build_checklist,
            finalize,
            format_checklist,
        )

        f = tmp_path / "c.svg"
        f.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.t { fill: #12181e; }"
            "@media (prefers-color-scheme: dark) { .t { fill: #e8f0f8; } }</style>"
            '<text class="t" x="20" y="40" font-family="Segoe UI, Arial, sans-serif">hi</text>'
            "</svg>"
        )
        ran: set[str] = set()
        hard, soft = finalize(f, None, ran)
        rows, counts = build_checklist(
            f, hard, soft, rendered=False, ran=ran, skip_reasons={"visual": "--no-visual"}
        )
        out = format_checklist("c.svg", rows, counts)
        assert "(--no-visual)" in out
        assert "these are not passes" not in out

        # A layer that died on its own is still chased.
        rows2, counts2 = build_checklist(f, hard, soft, rendered=False, ran=ran)
        assert "these are not passes" in format_checklist("c.svg", rows2, counts2)

    def test_missing_dark_block_row_is_counted_hard(self, tmp_path):
        """Deriving the tier from an empty note filed this FAIL as advisory."""
        from stellars_claude_code_plugins.svg_tools.finalize import (
            build_checklist,
            finalize,
            format_checklist,
        )

        f = tmp_path / "nodark.svg"
        f.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.t { fill: #12181e; }</style>"
            '<text class="t" x="20" y="40" font-family="Segoe UI, Arial, sans-serif">hi</text>'
            "</svg>"
        )
        ran: set[str] = set()
        rows, counts = build_checklist(f, *finalize(f, None, ran), rendered=False, ran=ran)
        by = {label: (s, n) for _g, label, s, n in rows}
        assert by["dark block present"] == ("FAIL", "1 SOFT")
        assert "0 hard, 0 soft" not in format_checklist("nodark.svg", rows, counts)

    def test_na_says_which_subject_is_missing(self, tmp_path):
        by, _ = roster(
            tmp_path,
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.t { fill: #12181e; }"
            "@media (prefers-color-scheme: dark) { .t { fill: #e8f0f8; } }</style>"
            '<text class="t" x="20" y="40" font-family="Segoe UI, Arial, sans-serif">hi</text>'
            "</svg>",
        )
        assert by["no zero-length segments"] == ("NA", "no parsed connector")


class TestThemeBlindSpots:
    """Each case shipped a clean verdict on a file with no working dark theme."""

    def test_dark_block_that_overrides_no_paint_is_inert(self, tmp_path):
        """Coverage checks the class NAME; a class whose paint is never
        overridden keeps its light colour and was measured by nobody."""
        light = "".join(f".c{i} {{ fill: #10203{i}; }}" for i in range(6))
        dark = "".join(f".c{i} {{ opacity: 1; }}" for i in range(6))
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            f"<style>{light}@media (prefers-color-scheme: dark) {{{dark}}}</style></svg>"
        )
        assert "missing-dark-override" in css_rules(tmp_path, svg)

    def test_stroke_left_light_while_fill_inverts(self, tmp_path):
        light = "".join(f".c{i} {{ fill: #10203{i}; stroke: #20304{i}; }}" for i in range(6))
        dark = "".join(f".c{i} {{ fill: #e8f0f{i}; }}" for i in range(6))
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            f"<style>{light}@media (prefers-color-scheme: dark) {{{dark}}}</style></svg>"
        )
        assert "missing-dark-override" in css_rules(tmp_path, svg)

    def test_non_rendering_rect_does_not_become_the_backplate(self, tmp_path):
        """A full-canvas rect in <defs>/<mask> is idiomatic and paints nothing,
        but being written first it won every area tie."""
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            '<defs><symbol id="s"><rect width="400" height="200" fill="#123456"/></symbol>'
            '<mask id="m"><rect width="400" height="200" fill="#ffffff"/></mask></defs>'
            "<style>.plate { fill: #fdfdfd; }"
            "@media (prefers-color-scheme: dark) { .plate { fill: #0b1620; } }</style>"
            '<rect class="plate" width="400" height="200"/></svg>'
        )
        assert "unthemed-background" not in css_rules(tmp_path, svg)

    def test_clip_path_rect_does_not_hide_a_bad_backplate(self, tmp_path):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            '<defs><clipPath id="c"><rect width="400" height="200"/></clipPath></defs>'
            "<style>.plate { fill: #fdfdfd; }"
            "@media (prefers-color-scheme: dark) { .plate { fill: #fcfcfc; } }</style>"
            '<rect class="plate" width="400" height="200"/></svg>'
        )
        assert "unthemed-background" in css_rules(tmp_path, svg)

    def test_transformed_rect_is_not_read_at_its_raw_coordinates(self, tmp_path):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.plate { fill: #fdfdfd; }"
            "@media (prefers-color-scheme: dark) { .plate { fill: #0b1620; } }</style>"
            '<g transform="translate(2000,0)"><rect width="400" height="200" fill="#123456"/></g>'
            '<rect class="plate" width="400" height="200"/></svg>'
        )
        assert "unthemed-background" not in css_rules(tmp_path, svg)

    def test_plate_sized_in_em_is_judged(self, tmp_path):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.t { fill: #101820; }"
            "@media (prefers-color-scheme: dark) { .t { fill: #e8f0f8; } }</style>"
            '<rect width="25em" height="12.5em" fill="#fdfdfd"/></svg>'
        )
        assert "unthemed-background" in css_rules(tmp_path, svg)

    def test_gradient_plate_cannot_answer_the_media_query(self, tmp_path):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 400">'
            '<defs><linearGradient id="bg"><stop offset="0" stop-color="#f5f9fc"/>'
            '<stop offset="1" stop-color="#e8eef4"/></linearGradient></defs>'
            "<style>.t { fill: #1e3a5f; }"
            "@media (prefers-color-scheme: dark) { .t { fill: #a8d4f0; } }</style>"
            '<rect width="800" height="400" fill="url(#bg)"/></svg>'
        )
        assert "unthemed-background" in css_rules(tmp_path, svg)

    def test_style_bodies_merge_rather_than_overwrite(self):
        """Concatenating <style> bodies made duplicate class names last-write-wins."""
        from stellars_claude_code_plugins.svg_tools.check_css import parse_style_block

        light, _dark, _, _meta = parse_style_block(
            "<svg><style>.card { fill: #f0f0f0; }</style>"
            "<g><style>.card { stroke-width: 2; }</style></g></svg>"
        )
        assert light["card"]["fill"] == "#f0f0f0"
        assert light["card"]["stroke-width"] == "2"

    def test_light_only_media_query_is_not_a_dark_block(self, tmp_path):
        from stellars_claude_code_plugins.svg_tools.finalize import build_checklist, finalize

        f = tmp_path / "lightonly.svg"
        f.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.t { fill: #101820; }"
            "@media (prefers-color-scheme: light) { .t { fill: #101821; } }</style>"
            '<text class="t" x="20" y="40" font-family="Segoe UI, Arial, sans-serif">hi</text>'
            "</svg>"
        )
        ran: set[str] = set()
        rows, _ = build_checklist(f, *finalize(f, None, ran), rendered=False, ran=ran)
        by = {label: status for _g, label, status, _n in rows}
        assert by["dark block present"] == "FAIL"
        assert by["overrides change the rendering"] == "NA"

    def test_dark_block_with_no_class_rules_is_not_a_pass(self, tmp_path):
        from stellars_claude_code_plugins.svg_tools.finalize import build_checklist, finalize

        f = tmp_path / "emptydark.svg"
        f.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.t { fill: #101820; }"
            "@media (prefers-color-scheme: dark) { text { fill: #f0f0f0; } }</style>"
            '<text class="t" x="20" y="40" font-family="Segoe UI, Arial, sans-serif">hi</text>'
            "</svg>"
        )
        ran: set[str] = set()
        rows, _ = build_checklist(f, *finalize(f, None, ran), rendered=False, ran=ran)
        by = {label: status for _g, label, status, _n in rows}
        assert by["overrides change the rendering"] == "NA"
        assert by["background inverts"] == "NA"

    def test_the_largest_covering_rect_is_the_ground(self, tmp_path):
        """A bleed decoration written before the plate must not be judged in
        its place - document order is not evidence of which one is the ground."""
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            # The decoy inverts correctly, so only WHICH rect gets judged can
            # change the verdict - the plate beneath it does not invert.
            "<style>.deco { fill: #f0f4f8; } .plate { fill: #fdfdfd; }"
            "@media (prefers-color-scheme: dark) { .deco { fill: #0b1620; }"
            " .plate { fill: #fcfcfc; } }</style>"
            '<rect class="deco" width="376" height="188"/>'
            '<rect class="plate" width="400" height="200"/></svg>'
        )
        rules = css_rules(tmp_path, svg)
        assert "unthemed-background" in rules, "the real plate went unjudged"


class TestParserWidth:
    """CSS shapes the regex parser used to drop, silently taking a check with them."""

    @staticmethod
    def _parse(css: str):
        from stellars_claude_code_plugins.svg_tools.check_css import parse_style_block

        return parse_style_block(f"<svg><style>{css}</style></svg>")

    def test_grouped_selector_registers_every_class(self):
        light, _d, _c, _m = self._parse(".fg-1, .fg-2 { fill: #1e3a5f; }")
        assert set(light) == {"fg-1", "fg-2"}

    def test_grouped_dark_override_is_not_reported_missing(self, tmp_path):
        from stellars_claude_code_plugins.svg_tools.check_css import check_css_compliance

        f = tmp_path / "g.svg"
        f.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.fg-1, .fg-2 { fill: #1e3a5f; }"
            "@media (prefers-color-scheme: dark) { .fg-1, .fg-2 { fill: #cfe2f5; } }</style>"
            "</svg>"
        )
        violations, _ = check_css_compliance(str(f))
        assert "missing-dark-override" not in [v.rule for v in violations]

    def test_element_and_id_rules_are_visible(self):
        _l, _d, _c, meta = self._parse("text { fill: #000000; } #plate { fill: #ffffff; }")
        assert set(meta["light_rules"]) == {"text", "#plate"}

    def test_comment_mentioning_at_media_does_not_eat_the_next_rule(self):
        light, _d, _c, _m = self._parse(
            "/* dark via @media ( see below ) */ .plate { fill: #fdfdfd; }"
        )
        assert "plate" in light

    def test_nested_media_does_not_empty_the_light_stylesheet(self):
        light, dark, _c, _m = self._parse(
            "@media (min-width: 1px) { .z { fill: #111111; }"
            " @media (prefers-color-scheme: dark) { .z { fill: #eeeeee; } } }"
            " .plate { fill: #fdfdfd; }"
        )
        assert "plate" in light, "a nested query truncated the light rules"
        assert "z" in dark

    def test_dark_block_probe_ignores_comments_and_accepts_legal_spacing(self):
        _l, _d, _c, m1 = self._parse(".a { fill: #101010; }")
        assert m1["has_dark_block"] is False
        _l, _d, _c, m2 = self._parse(
            ".a { fill: #101010; } @media (prefers-color-scheme : dark) { .a { fill: #efefef; } }"
        )
        assert m2["has_dark_block"] is True

    def test_a_file_with_no_style_element_has_no_dark_block(self):
        from stellars_claude_code_plugins.svg_tools.check_css import parse_style_block

        # A shipped example reported a dark block from the words appearing in
        # an XML comment, with no <style> element in the file at all.
        _l, _d, _c, meta = parse_style_block(
            "<svg><!-- DARK MODE (CSS prefers-color-scheme: dark) --><rect/></svg>"
        )
        assert meta["has_dark_block"] is False


class TestGuardsArePinned:
    """One test per guard a mutation survived."""

    def test_opacity_one_still_requires_a_dark_override(self, tmp_path):
        """`_COMPOSITED_OPACITY` at 1.0 would exempt every fully opaque class."""
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.solid { fill: #1e3a5f; opacity: 1; }"
            "@media (prefers-color-scheme: dark) { .other { fill: #ffffff00; } }</style></svg>"
        )
        assert "missing-dark-override" in css_rules(tmp_path, svg)

    def test_important_opacity_still_exempts_a_faint_paint(self, tmp_path):
        """The shared value regex captures `!important` into the value."""
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.card { fill: #00a6ff; fill-opacity: 0.04 !important; stroke: #00a6ff; }"
            "@media (prefers-color-scheme: dark) { .card { stroke: #4fb7ea; } }</style></svg>"
        )
        assert "missing-dark-override" not in css_rules(tmp_path, svg)

    def test_percentage_opacity_is_read(self, tmp_path):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.card { fill: #00a6ff; fill-opacity: 4%; stroke: #00a6ff; }"
            "@media (prefers-color-scheme: dark) { .card { stroke: #4fb7ea; } }</style></svg>"
        )
        assert "missing-dark-override" not in css_rules(tmp_path, svg)

    def test_backplate_delta_bar_is_pinned(self, tmp_path):
        """`_MIN_BACKPLATE_LUM_DELTA` at 0 would call any dark value an inversion."""
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.plate { fill: #8a8a8a; }"
            "@media (prefers-color-scheme: dark) { .plate { fill: #7e7e7e; } }</style>"
            '<rect class="plate" width="400" height="200"/></svg>'
        )
        assert "unthemed-background" in css_rules(tmp_path, svg)

    def test_a_top_level_mask_is_still_non_rendering(self, tmp_path):
        """NONRENDER_TAGS shrunk to {"defs"} would judge a top-level mask."""
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            '<mask id="m"><rect width="400" height="200" fill="#ffffff"/></mask>'
            "<style>.plate { fill: #fdfdfd; }"
            "@media (prefers-color-scheme: dark) { .plate { fill: #0b1620; } }</style>"
            '<rect class="plate" width="400" height="200"/></svg>'
        )
        assert css_rules(tmp_path, svg) == []

    def test_unparseable_offset_drops_the_rect_rather_than_reading_zero(self, tmp_path):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.t { fill: #101820; }"
            "@media (prefers-color-scheme: dark) { .t { fill: #e8f0f8; } }</style>"
            '<rect x="wat" width="400" height="200" fill="#fdfdfd"/></svg>'
        )
        assert "unthemed-background" not in css_rules(tmp_path, svg)

    def test_plate_with_explicit_plus_sign_is_judged(self, tmp_path):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900">'
            "<style>.t { fill: #101820; }"
            "@media (prefers-color-scheme: dark) { .t { fill: #e8f0f8; } }</style>"
            '<rect width="+1600" height="+900" fill="#fdfdfd"/></svg>'
        )
        assert "unthemed-background" in css_rules(tmp_path, svg)

    def test_crashed_token_less_layer_skips_rather_than_fails(self, tmp_path):
        """The faithful crashed/hits swap survived: a `None`-token row claimed
        the crash diagnostic itself as a hit and reported a confident FAIL."""
        from stellars_claude_code_plugins.svg_tools.finalize import build_checklist

        f = tmp_path / "c.svg"
        f.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.t { fill: #101820; }"
            "@media (prefers-color-scheme: dark) { .t { fill: #e8f0f8; } }</style>"
            '<text class="t" x="20" y="40" font-family="Segoe UI, Arial, sans-serif">hi</text>'
            "</svg>"
        )
        rows, _ = build_checklist(
            f,
            [],
            ["[alignment] check failed: boom"],
            rendered=False,
            ran={"validate", "overlaps", "connectors", "contrast", "collide", "css"},
        )
        by = {label: (s, n) for _g, label, s, n in rows}
        assert by["alignment and rhythm"] == ("SKIP", "checker crashed")

    def test_gradient_declared_in_a_class_is_resolved(self, tmp_path):
        """`url(#bg)` in a class was unmeasurable, so it printed PASS - and the
        inline-fill remedy text told authors to move fills into exactly that."""
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            '<defs><linearGradient id="bg"><stop offset="0" stop-color="#f5f9fc"/>'
            '<stop offset="1" stop-color="#e8eef4"/></linearGradient></defs>'
            "<style>.plate { fill: url(#bg); }"
            "@media (prefers-color-scheme: dark) { .plate { fill: url(#bg); } }</style>"
            '<rect class="plate" width="400" height="200"/></svg>'
        )
        assert "unthemed-background" in css_rules(tmp_path, svg)

    def test_a_gradient_that_inverts_is_clean(self, tmp_path):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            '<defs><linearGradient id="lt"><stop stop-color="#f5f9fc"/>'
            '<stop stop-color="#e8eef4"/></linearGradient>'
            '<linearGradient id="dk"><stop stop-color="#0b1620"/>'
            '<stop stop-color="#101a24"/></linearGradient></defs>'
            "<style>.plate { fill: url(#lt); }"
            "@media (prefers-color-scheme: dark) { .plate { fill: url(#dk); } }</style>"
            '<rect class="plate" width="400" height="200"/></svg>'
        )
        assert "unthemed-background" not in css_rules(tmp_path, svg)

    def test_style_attribute_opacity_on_text_is_caught(self, tmp_path):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.t { fill: #101820; }"
            "@media (prefers-color-scheme: dark) { .t { fill: #e8f0f8; } }</style>"
            '<text class="t" style="opacity:0.35" x="20" y="40">hi</text></svg>'
        )
        assert "text-opacity" in css_rules(tmp_path, svg)

    def test_fill_opacity_attribute_on_text_is_caught(self, tmp_path):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.t { fill: #101820; }"
            "@media (prefers-color-scheme: dark) { .t { fill: #e8f0f8; } }</style>"
            '<text class="t" fill-opacity="0.3" x="20" y="40">hi</text></svg>'
        )
        assert "text-opacity" in css_rules(tmp_path, svg)

    def test_a_half_canvas_rect_is_not_the_plate(self, tmp_path):
        """BACKPLATE_COVER_MIN at 0.50 would promote an ordinary panel."""
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.panel { fill: #fdfdfd; } .t { fill: #101820; }"
            "@media (prefers-color-scheme: dark) { .panel { fill: #fcfcfc; }"
            " .t { fill: #e8f0f8; } }</style>"
            '<rect class="panel" width="220" height="110"/></svg>'
        )
        assert "unthemed-background" not in css_rules(tmp_path, svg)

    def test_card_relative_rows_need_cards_even_with_connectors(self, tmp_path):
        """Connectors but no cards: cc_edge_snap iterates cards and cannot speak."""
        from stellars_claude_code_plugins.svg_tools.finalize import build_checklist, finalize

        f = tmp_path / "conn.svg"
        f.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.t { fill: #101820; }"
            "@media (prefers-color-scheme: dark) { .t { fill: #e8f0f8; } }</style>"
            '<g id="connectors"><path id="c1" d="M20,20 L200,20" fill="none" '
            'stroke="#0284c7" stroke-width="1.2"/></g></svg>'
        )
        ran: set[str] = set()
        rows, _ = build_checklist(f, *finalize(f, None, ran), rendered=False, ran=ran)
        by = {label: status for _g, label, status, _n in rows}
        assert by["endpoints snap to edges"] == "NA"
        assert by["labels clear the route"] == "NA"

    def test_a_visible_pattern_rect_is_not_the_plate(self, tmp_path):
        """Un-hiding the guide grid made its pattern rect the backplate, and the
        only finding in the whole gate was an ack the operator had to hand-type."""
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            '<defs><pattern id="grid-pat-100" width="100" height="100">'
            '<path d="M0 0 L0 100"/></pattern></defs>'
            "<style>.t { fill: #101820; }"
            "@media (prefers-color-scheme: dark) { .t { fill: #e8f0f8; } }</style>"
            '<g id="grid-100"><rect width="400" height="200" fill="url(#grid-pat-100)"/></g>'
            "</svg>"
        )
        assert "unthemed-background" not in css_rules(tmp_path, svg)


class TestRound5Regressions:
    """Each case shipped a verdict the tool had not earned."""

    S = SVG_OPEN

    def test_commented_out_style_is_not_live_css(self, tmp_path):
        """The probe moved into the parser, but the parser read the whole file."""
        svg = (
            self.S + "<!--<style>.plate { fill: #f8fafc; }"
            "@media (prefers-color-scheme: dark) { .plate { fill: #0b1620; } }</style>-->"
            '<rect class="plate" width="400" height="200" fill="#f8fafc"/></svg>'
        )
        assert "missing-dark-block" in css_rules(tmp_path, svg)

    def test_unterminated_css_comment_runs_to_end(self, tmp_path):
        svg = (
            self.S + "<style>/* note: .plate { fill: #fdfdfd; }"
            "@media (prefers-color-scheme: dark) { .plate { fill: #0b1620; } }</style></svg>"
        )
        assert "missing-dark-block" in css_rules(tmp_path, svg)

    def test_id_rule_beats_class_rule(self, tmp_path):
        """CSS specificity: #id is 100, .class is 10. The helper had it backwards."""
        svg = (
            self.S + "<style>.chrome { fill: none; } #plate { fill: #f8fafc; }"
            "@media (prefers-color-scheme: dark) { #plate { fill: #f8fafc; }"
            " .chrome { fill: none; } }</style>"
            '<rect id="plate" class="chrome" width="400" height="200"/></svg>'
        )
        assert "unthemed-background" in css_rules(tmp_path, svg)

    def test_id_themed_plate_is_measured(self, tmp_path):
        svg = (
            self.S + "<style>#plate { fill: #f8fafc; }"
            "@media (prefers-color-scheme: dark) { #plate { fill: #f8fafc; } }</style>"
            '<rect id="plate" width="400" height="200"/></svg>'
        )
        assert "unthemed-background" in css_rules(tmp_path, svg)

    def test_element_rule_plate_is_measured(self, tmp_path):
        svg = (
            self.S + "<style>rect { fill: #f8fafc; }"
            "@media (prefers-color-scheme: dark) { rect { fill: #f8fafc; } }</style>"
            '<rect width="400" height="200"/></svg>'
        )
        assert "unthemed-background" in css_rules(tmp_path, svg)

    def test_one_plate_two_classes_reports_once(self, tmp_path):
        svg = (
            self.S + "<style>.plate { fill: #fdfdfd; } .bg { fill: #fdfdfd; }"
            "@media (prefers-color-scheme: dark) { .plate { fill: #fcfcfc; }"
            " .bg { fill: #fcfcfc; } }</style>"
            '<rect class="plate bg" width="400" height="200"/></svg>'
        )
        assert css_rules(tmp_path, svg).count("unthemed-background") == 1

    def test_important_does_not_readmit_the_guide_grid(self, tmp_path):
        """Three characters put round-4's pattern exclusion back to sleep."""
        svg = (
            self.S + '<defs><pattern id="grid"><path d="M0 0"/></pattern></defs>'
            "<style>.guide { fill: url(#grid) !important; } .plate { fill: #fdfdfd; }"
            "@media (prefers-color-scheme: dark) { .plate { fill: #fcfcfc; } }</style>"
            '<rect class="guide" width="400" height="200"/>'
            '<rect class="plate" width="400" height="200"/></svg>'
        )
        assert "unthemed-background" in css_rules(tmp_path, svg)

    def test_important_gradient_is_still_resolved(self, tmp_path):
        svg = (
            self.S + '<defs><linearGradient id="bg"><stop stop-color="#f5f9fc"/>'
            '<stop stop-color="#e8eef4"/></linearGradient></defs>'
            "<style>.plate { fill: url(#bg) !important; }"
            "@media (prefers-color-scheme: dark) { .plate { fill: url(#bg) !important; } }</style>"
            '<rect class="plate" width="400" height="200"/></svg>'
        )
        assert "unthemed-background" in css_rules(tmp_path, svg)

    def test_none_important_is_not_painting(self, tmp_path):
        svg = (
            self.S + "<style>.hairline { fill: none !important; }"
            "@media (prefers-color-scheme: dark) { .x { fill: #111111; } }</style></svg>"
        )
        assert "missing-dark-override" not in css_rules(tmp_path, svg)

    def test_functional_pseudo_commas_mint_no_classes(self, tmp_path):
        from stellars_claude_code_plugins.svg_tools.check_css import parse_css_rules

        assert sorted(parse_css_rules(".ghost:is(.a, .b) { fill: #ff0000; }")) == [".ghost"]

    def test_descendant_selector_keys_on_its_last_component(self):
        from stellars_claude_code_plugins.svg_tools.check_css import parse_css_rules

        assert sorted(parse_css_rules("g.card > rect.body { fill: #111111; }")) == [".body"]

    def test_a_descendant_element_is_not_an_element_rule(self):
        """`.color-2 a:visited` registered a bare `a` rule that then painted
        every <a> in the document through the cascade."""
        from stellars_claude_code_plugins.svg_tools.check_css import parse_css_rules

        assert "a" not in parse_css_rules(".color-2 a:visited { fill: #000000; }")

    def test_attribute_selector_rules_are_scanned(self, tmp_path):
        svg = (
            self.S + '<style>rect[data-role="badge"] { fill: #ffffff; }'
            "@media (prefers-color-scheme: dark) { .x { fill: #111111; } }</style></svg>"
        )
        assert "forbidden-color" in css_rules(tmp_path, svg)

    def test_transform_does_not_exempt_paint_from_the_colour_scan(self, tmp_path):
        """The transform test belongs to geometry; sharing it with the colour
        scan exempted 1938 of 7358 corpus elements."""
        svg = (
            self.S + "<style>.x { fill: #123456; }"
            "@media (prefers-color-scheme: dark) { .x { fill: #abcdef; } }</style>"
            '<g transform="translate(5,5)"><rect fill="#ffffff" width="10" height="10"/></g></svg>'
        )
        assert "forbidden-color" in css_rules(tmp_path, svg)

    def test_percentage_fill_opacity_does_not_crash_the_layer(self, tmp_path):
        svg = (
            self.S + "<style>.x { fill: #123456; }"
            "@media (prefers-color-scheme: dark) { .x { fill: #abcdef; } }</style>"
            '<rect stroke="#334455" fill-opacity="50%" width="10" height="10"/></svg>'
        )
        assert css_rules(tmp_path, svg) == []

    def test_stats_header_agrees_with_the_findings(self, tmp_path):
        from stellars_claude_code_plugins.svg_tools.check_css import check_css_compliance

        f = tmp_path / "e.svg"
        f.write_text(
            self.S + "<style>.box { fill: #101820; }"
            "@media (prefers-color-scheme: dark) { text { fill: #f0f0f0; } }</style></svg>"
        )
        violations, stats = check_css_compliance(str(f))
        assert stats["has_dark_mode"] is True
        assert "missing-dark-block" not in [v.rule for v in violations]

    def test_every_dark_block_oracle_agrees(self, tmp_path):
        from stellars_claude_code_plugins.svg_tools.check_css import (
            has_dark_block,
            parse_style_block,
        )
        from stellars_claude_code_plugins.svg_tools.workflow import inspect_svg

        spaced = "<svg><style>.a{fill:#111111}@media (prefers-color-scheme : dark){.a{fill:#eeeeee}}</style></svg>"
        commented = "<svg><!--<style>@media (prefers-color-scheme: dark){.a{fill:#eeeeee}}</style>--></svg>"
        for i, (text, expected) in enumerate(((spaced, True), (commented, False))):
            assert parse_style_block(text)[3]["has_dark_block"] is expected
            assert has_dark_block(text) is expected
            # The consumers delegate rather than re-deriving; assert one of them
            # end-to-end so the delegation itself is covered.
            f = tmp_path / f"o{i}.svg"
            f.write_text(text)
            assert inspect_svg(f)["has_dark_mode"] is expected


class TestRosterSubjectGating:
    """A row may only PASS when its subject exists."""

    def test_background_inverts_is_na_without_a_plate(self, tmp_path):
        """59 of 71 example files printed PASS with no plate ever examined."""
        by, _ = roster(
            tmp_path,
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.t { fill: #101820; }"
            "@media (prefers-color-scheme: dark) { .t { fill: #e8f0f8; } }</style>"
            '<text class="t" x="20" y="40" font-family="Segoe UI, Arial, sans-serif">hi</text>'
            "</svg>",
        )
        assert by["background inverts"] == ("NA", "no canvas-covering <rect>")

    def test_theme_rows_are_na_without_painting_rules(self, tmp_path):
        by, _ = roster(
            tmp_path,
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.spacer { stroke-width: 2; }"
            "@media (prefers-color-scheme: dark) { .spacer { stroke-width: 3; } }</style>"
            "</svg>",
        )
        assert by["every painting rule overridden"][0] == "NA"
        assert by["overrides change the rendering"][0] == "NA"

    def test_text_rows_are_na_when_text_is_only_in_a_comment(self, tmp_path):
        by, _ = roster(
            tmp_path,
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.t { fill: #101820; }"
            "@media (prefers-color-scheme: dark) { .t { fill: #e8f0f8; } }</style>"
            "<!-- <text>not real</text> --></svg>",
        )
        assert by["no inline fill on text"][0] == "NA"
        assert by["text meets WCAG AA"][0] == "NA"

    def test_deck_row_skips_when_the_cross_file_check_never_ran(self, tmp_path):
        """A hand-built row with only PASS and FAIL announced consistency
        nobody had measured - the same lie the per-file rows had just lost."""
        import contextlib
        import io

        from stellars_claude_code_plugins.svg_tools.finalize import main

        clean = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">'
            "<style>.panel { fill: #eeeeee; }"
            "@media (prefers-color-scheme: dark) { .panel { fill: #17202a; } }</style>"
            '<rect class="panel" x="10" y="10" width="180" height="80"/></svg>'
        )
        a, b = tmp_path / "a.svg", tmp_path / "b.svg"
        a.write_text(clean)
        b.write_text(clean)
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            main([str(a), str(b), "--no-visual", "--checklist"])
        out = err.getvalue()
        assert "CHECKLIST  deck" in out
        assert "[SKIP] files are mutually consistent" in out
        assert "[PASS] files are mutually consistent" not in out
        assert "1 aspects" not in out, "singular row printed with a plural noun"

    def test_no_dark_block_fails_both_the_presence_and_coverage_rows(self, tmp_path):
        """With no dark block nothing is overridden, so coverage FAILs on its
        own findings - FAIL precedes NA, which is why gating that row on the
        dark block was unreachable."""
        by, _ = roster(
            tmp_path,
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.t { fill: #101820; }</style>"
            '<text class="t" x="20" y="40" font-family="Segoe UI, Arial, sans-serif">hi</text>'
            "</svg>",
        )
        assert by["dark block present"][0] == "FAIL"
        assert by["every painting rule overridden"][0] == "FAIL"

    def test_overlaps_row_is_judged_on_elements_not_cards(self, tmp_path):
        """The overlaps layer runs on its own element model; keying the row on
        the connector layer's card count reverts a documented fix."""
        by, _ = roster(
            tmp_path,
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.t { fill: #101820; }"
            "@media (prefers-color-scheme: dark) { .t { fill: #e8f0f8; } }</style>"
            '<text class="t" x="21" y="41" font-family="Segoe UI, Arial, sans-serif">one</text>'
            '<text class="t" x="23" y="87" font-family="Segoe UI, Arial, sans-serif">two</text>'
            "</svg>",
        )
        assert by["no element overlaps"][0] != "NA"


class TestRound5Guards:
    """Guards whose mutants outlived the first battery."""

    S = SVG_OPEN

    def test_gradient_luma_is_the_mean_of_its_stops(self, tmp_path):
        """One near-black stop in an otherwise light gradient must not make the
        ground read as dark - `max` over the stops would let it."""
        svg = (
            self.S + '<defs><linearGradient id="lt"><stop stop-color="#f8fafc"/>'
            '<stop stop-color="#eef2f6"/></linearGradient>'
            '<linearGradient id="dk"><stop stop-color="#000000"/>'
            '<stop stop-color="#f0f0f0"/></linearGradient></defs>'
            "<style>.plate { fill: url(#lt); }"
            "@media (prefers-color-scheme: dark) { .plate { fill: url(#dk); } }</style>"
            '<rect class="plate" width="400" height="200"/></svg>'
        )
        # The dark gradient averages 120/255 - a dark ground, 130 below the
        # light plate, so it inverts. Reading `max` instead would see 240 and
        # call the same gradient a light ground that barely moved.
        assert "unthemed-background" not in css_rules(tmp_path, svg)

    def test_a_dangling_paint_reference_is_unmeasurable_not_black(self, tmp_path):
        """Returning 0.0 for a missing `url(#id)` reads a broken reference as a
        perfectly dark ground."""
        svg = (
            self.S + "<style>.plate { fill: #f8fafc; }"
            "@media (prefers-color-scheme: dark) { .plate { fill: url(#nope); } }</style>"
            '<rect class="plate" width="400" height="200"/></svg>'
        )
        assert "unthemed-background" in css_rules(tmp_path, svg)

    def test_exactly_half_inert_is_not_a_majority(self, tmp_path):
        """The documented boundary: inert must EXCEED half to fire."""
        light = "".join(f".c{i} {{ fill: #10203{i}; stroke: #20304{i}; }}" for i in range(3))
        dark = "".join(f".c{i} {{ fill: #e8f0f{i}; stroke: #20304{i}; }}" for i in range(3))
        svg = (
            self.S + f"<style>{light}@media (prefers-color-scheme: dark) {{{dark}}}</style></svg>"
        )
        assert "inert-dark-mode" not in css_rules(tmp_path, svg)

    def test_a_plate_offset_far_from_the_origin_is_not_the_ground(self, tmp_path):
        """BACKPLATE_ORIGIN_TOL governs which rect is picked; only its twin
        BACKPLATE_COVER_MIN was pinned."""
        svg = (
            self.S + "<style>.panel { fill: #fdfdfd; }"
            "@media (prefers-color-scheme: dark) { .panel { fill: #fcfcfc; } }</style>"
            '<rect class="panel" x="80" y="40" width="400" height="200"/></svg>'
        )
        assert "unthemed-background" not in css_rules(tmp_path, svg)

    def test_a_path_plate_reads_as_no_plate_rather_than_a_guess(self, tmp_path):
        """Path plates are OUT OF SCOPE, and the roster says so instead of
        guessing.

        Reading `d` as absolute alternating x/y is wrong in both directions -
        `M0 0 h1920 v1080 h-1920 z` boxes as 3840 wide (the plate vanishes) and
        a swoosh's control points reach the corners (a decoration is promoted).
        A confident verdict from a broken box is worse than an honest NA, so
        this file must produce neither a finding nor a PASS.
        """
        from stellars_claude_code_plugins.svg_tools.finalize import build_checklist, finalize

        svg = (
            self.S + "<style>.plate { fill: #f8fafc; }"
            "@media (prefers-color-scheme: dark) { .plate { fill: #f7fbff; } }</style>"
            '<path class="plate" d="M0,0 L400,0 L400,200 L0,200 Z"/></svg>'
        )
        assert "unthemed-background" not in css_rules(tmp_path, svg)
        f = tmp_path / "pathplate.svg"
        f.write_text(svg)
        ran: set[str] = set()
        rows, _ = build_checklist(f, *finalize(f, None, ran), rendered=False, ran=ran)
        by = {label: (status, note) for _g, label, status, note in rows}
        assert by["background inverts"] == ("NA", "no canvas-covering <rect>")

    def test_a_relative_full_bleed_path_is_not_mistaken_for_a_plate(self, tmp_path):
        """The exact spelling a pure-relative optimizer pass emits."""
        import xml.etree.ElementTree as ET

        from stellars_claude_code_plugins.svg_tools.check_css import find_backplate

        svg = (
            self.S + "<style>.plate { fill: #f8fafc; }</style>"
            '<path class="plate" d="M0 0 h400 v200 h-400 z"/></svg>'
        )
        f = tmp_path / "relplate.svg"
        f.write_text(svg)
        assert find_backplate(ET.parse(str(f)).getroot(), {".plate": {"fill": "#f8fafc"}}) is None


class TestRound6Cascade:
    """The CSS cascade is ONE oracle. Every defect below came from a second,
    partial copy of it deciding a theme verdict on its own."""

    S = SVG_OPEN

    def test_a_light_id_rule_outranks_a_dark_class_rule(self, tmp_path):
        """A @media block ADDS declarations - it does not replace the sheet.

        `#bg-plate` (1,0,0) keeps beating `.plate` (0,1,0) under the query, so
        the ground renders near-white in dark mode. Resolving the dark paint
        against the dark map alone declared it inverted.
        """
        svg = (
            self.S + "<style>#bg-plate { fill: #f5f9fc; } .plate { fill: #f5f9fc; }"
            "@media (prefers-color-scheme: dark) { .plate { fill: #12181e; } }</style>"
            '<rect id="bg-plate" class="plate" width="400" height="200"/></svg>'
        )
        assert "unthemed-background" in css_rules(tmp_path, svg)

    def test_a_silent_dark_block_does_not_fall_through_to_the_attribute(self, tmp_path):
        """With the dark block saying nothing about `.plate`, the cascade used
        to drop to the presentation attribute - a theme-invariant value that can
        never be the dark paint, and which happened to look like an inversion."""
        svg = (
            self.S + "<style>.plate { fill: #f5f9fc; } .x { fill: #445566; }"
            "@media (prefers-color-scheme: dark) { .x { fill: #99aabb; } }</style>"
            '<rect class="plate" fill="#12181e" width="400" height="200"/></svg>'
        )
        assert "unthemed-background" in css_rules(tmp_path, svg)

    def test_an_element_rule_paints_the_plate_and_is_honoured(self, tmp_path):
        """`rect { fill: … }` beats a stale presentation attribute, so a plate
        themed that way is correctly themed - a scan covering only class and id
        rules called it inline-painted and sent it back for repair."""
        svg = (
            self.S + "<style>rect { fill: #f5f9fc; }"
            "@media (prefers-color-scheme: dark) { rect { fill: #12181e; } }</style>"
            '<rect fill="#ffffee" width="400" height="200"/></svg>'
        )
        assert "unthemed-background" not in css_rules(tmp_path, svg)

    def test_an_id_themed_plate_is_judged_not_skipped(self, tmp_path):
        """A textbook inversion written with an id selector. The row was gated
        on dark CLASS rules, so it read NA - permanently, for every such file -
        under a note claiming the file had no dark rules."""
        from stellars_claude_code_plugins.svg_tools.finalize import build_checklist, finalize

        svg = (
            self.S + "<style>#plate { fill: #f5f9fc; }"
            "@media (prefers-color-scheme: dark) { #plate { fill: #12181e; } }</style>"
            '<rect id="plate" width="400" height="200"/></svg>'
        )
        f = tmp_path / "idplate.svg"
        f.write_text(svg)
        ran: set[str] = set()
        rows, _ = build_checklist(f, *finalize(f, None, ran), rendered=False, ran=ran)
        by = {label: status for _g, label, status, _n in rows}
        assert by["background inverts"] == "PASS"

    def test_equal_specificity_is_decided_by_source_order(self, tmp_path):
        """A browser reads the stylesheet, not the order of names in the
        attribute.

        BOTH directions are asserted deliberately. With one `class="a b"`
        fixture, reading the attribute left-to-right and reading it
        right-to-left each land on the right answer half the time - so a single
        case cannot tell either wrong rule from the right one.
        """
        import xml.etree.ElementTree as ET

        from stellars_claude_code_plugins.svg_tools.check_css import (
            build_render_model,
            parse_style_block,
        )

        def winner(css, name):
            svg = self.S + f"<style>{css}</style>" + '<rect class="a b"/></svg>'
            f = tmp_path / name
            f.write_text(svg)
            _l, _d, _c, meta = parse_style_block(svg)
            root = ET.parse(str(f)).getroot()
            _nr, _dis, resolve_paint, _w, _p, _own = build_render_model(root)
            rect = next(e for e in root.iter() if e.tag.endswith("rect"))
            return resolve_paint(rect, "fill", meta["light_rules"])

        # `.b` declared last -> `.b` paints, though `a` comes first in the attr.
        assert winner(".a { fill: #eeeeee; } .b { fill: #111111; }", "o1.svg") == "#111111"
        # `.a` declared last -> `.a` paints, though `b` comes last in the attr.
        assert winner(".b { fill: #111111; } .a { fill: #eeeeee; }", "o2.svg") == "#eeeeee"

    def test_specificity_order_is_id_then_class_then_element_then_attribute(self, tmp_path):
        import xml.etree.ElementTree as ET

        from stellars_claude_code_plugins.svg_tools.check_css import (
            build_render_model,
            parse_style_block,
        )

        css = "#i { fill: #100000; } .c { fill: #200000; } rect { fill: #300000; }"
        svg = self.S + f"<style>{css}</style>" + '<rect id="i" class="c" fill="#400000"/></svg>'
        f = tmp_path / "spec.svg"
        f.write_text(svg)
        _l, _d, _c, meta = parse_style_block(svg)
        root = ET.parse(str(f)).getroot()
        _nr, _dis, resolve, _w, _p, _own = build_render_model(root)
        rect = next(e for e in root.iter() if e.tag.endswith("rect"))
        rules = dict(meta["light_rules"])
        assert resolve(rect, "fill", rules) == "#100000"
        rules.pop("#i")
        assert resolve(rect, "fill", rules) == "#200000"
        rules.pop(".c")
        assert resolve(rect, "fill", rules) == "#300000"
        rules.pop("rect")
        assert resolve(rect, "fill", rules) == "#400000"


class TestRound6PlateElection:
    """The ground is the topmost opaque shape covering the canvas."""

    S = SVG_OPEN

    def _plate(self, tmp_path, svg):
        import xml.etree.ElementTree as ET

        from stellars_claude_code_plugins.svg_tools.check_css import (
            find_backplate,
            parse_style_block,
        )

        f = tmp_path / "p.svg"
        f.write_text(svg)
        _l, _d, _c, meta = parse_style_block(svg)
        return find_backplate(ET.parse(str(f)).getroot(), meta["light_rules"])

    def test_a_faint_full_bleed_wash_is_not_the_ground(self, tmp_path):
        """A 4%-opacity bleed composites OVER the ground; electing it judged
        the decoration's theme and left the real plate unexamined."""
        svg = (
            self.S
            + "<style>.plate { fill: #f5f9fc; } .wash { fill: #e8eef4; fill-opacity: 0.04; }"
            "@media (prefers-color-scheme: dark) { .plate { fill: #f8fbff; }"
            " .wash { fill: #10161c; fill-opacity: 0.04; } }</style>"
            '<rect class="plate" width="400" height="200"/>'
            '<rect class="wash" x="-10" y="-5" width="420" height="210"/></svg>'
        )
        assert self._plate(tmp_path, svg).get("class") == "plate"

    def test_the_topmost_covering_rect_wins_not_the_first(self, tmp_path):
        """Document order IS paint order: a 94%-coverage decoration painted
        UNDER a full-bleed plate is hidden by it. Taking the FIRST candidate
        judged the buried one."""
        svg = (
            self.S + "<style>.deco { fill: #f0f4f8; } .plate { fill: #fdfdfd; }</style>"
            '<rect class="deco" width="376" height="188"/>'
            '<rect class="plate" width="400" height="200"/></svg>'
        )
        assert self._plate(tmp_path, svg).get("class") == "plate"


class TestRound6RosterHonesty:
    """Rows that reported a verdict where nothing was measured."""

    def test_deck_consistency_is_na_when_no_file_holds_a_card(self, tmp_path):
        """`check_cross_file_consistency` returns [] both when the deck agrees
        and when neither of its comparisons had a subject. This repo's own deck
        is in the second state and was told it was mutually consistent."""
        from stellars_claude_code_plugins.svg_tools.check_visual import consistency_subjects

        datas = [
            {
                "file": str(tmp_path / f"{i}.svg"),
                "elements": [{"tag": "rect", "id": "", "class": ""}],
            }
            for i in range(2)
        ]
        for d in datas:
            Path(d["file"]).write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"></svg>'
            )
        assert consistency_subjects(datas) == 0

    def test_the_deck_row_itself_reads_na_with_no_cards_anywhere(self, tmp_path):
        """End-to-end through `main`, because the free PASS lived in the branch
        there rather than in the helper that counts the subjects."""
        files = []
        for i in range(2):
            f = tmp_path / f"d{i}.svg"
            f.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
                f'<text x="10" y="{20 + i}" class="t">hi</text></svg>'
            )
            files.append(str(f))
        out = subprocess.run(
            [sys.executable, "-m", "stellars_claude_code_plugins.svg_tools.finalize"]
            + files
            + ["--checklist"],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": os.environ.get("PYTHONPATH") or "src"},
        )
        deck = out.stderr.split("CHECKLIST  deck")[1]
        row = next(ln for ln in deck.splitlines() if "mutually consistent" in ln)
        assert "NA" in row and "no cards to compare" in row, row

    def test_a_painting_rule_of_any_shape_is_gated_and_judged_alike(self, tmp_path):
        """The gate read every selector shape while the checker read classes
        only, so an unthemed `text {}` / `#id {}` file printed PASS. Gate and
        checker now share one predicate, so the row can only be FAIL or NA."""
        from stellars_claude_code_plugins.svg_tools.finalize import build_checklist, finalize

        f = tmp_path / "elemrules.svg"
        f.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>text { fill: #1a5a6e; } #spine { stroke: #005f7a; } .x { opacity: 1; }</style>"
            '<line id="spine" x1="0" y1="0" x2="10" y2="10"/></svg>'
        )
        ran: set[str] = set()
        rows, _ = build_checklist(f, *finalize(f, None, ran), rendered=False, ran=ran)
        by = {label: status for _g, label, status, _n in rows}
        assert by["every painting rule overridden"] == "FAIL"

    def test_rules_that_paint_nothing_leave_the_row_unjudged(self, tmp_path):
        """`fill: none !important` paints nothing, so the gate must not count it
        as a subject - it was, and the row took a free PASS."""
        from stellars_claude_code_plugins.svg_tools.finalize import build_checklist, finalize

        f = tmp_path / "nopaint.svg"
        f.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.hair { fill: none !important; stroke: none !important; }"
            "@media (prefers-color-scheme: dark) { .hair { opacity: 1; } }</style>"
            '<line class="hair" x1="0" y1="0" x2="10" y2="10"/></svg>'
        )
        ran: set[str] = set()
        rows, _ = build_checklist(f, *finalize(f, None, ran), rendered=False, ran=ran)
        by = {label: (status, note) for _g, label, status, note in rows}
        assert by["every painting rule overridden"] == ("NA", "no painting rules")
        assert by["overrides change the rendering"][0] == "NA"

    def test_a_dark_block_sharing_no_selector_measures_nothing(self, tmp_path):
        """Light paints `.t`, the dark block redeclares `text` - the two never
        meet, so there is no pair to compare and the row must not say clean."""
        from stellars_claude_code_plugins.svg_tools.finalize import build_checklist, finalize

        f = tmp_path / "disjoint.svg"
        f.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            "<style>.t { fill: #101820; }"
            "@media (prefers-color-scheme: dark) { text { fill: #f0f0f0; } }</style>"
            '<text class="t" x="20" y="40">hi</text></svg>'
        )
        ran: set[str] = set()
        rows, _ = build_checklist(f, *finalize(f, None, ran), rendered=False, ran=ran)
        by = {label: status for _g, label, status, _n in rows}
        assert by["overrides change the rendering"] == "NA"

    def test_the_alignment_row_and_the_overlaps_row_never_share_a_noun(self):
        """Two parsers, two inventory keys - and two DIFFERENT labels, or the
        block prints `no elements` under `no element overlaps (1 HARD)`."""
        from stellars_claude_code_plugins.svg_tools.finalize import _NEEDS_LABEL

        assert _NEEDS_LABEL["aligned_elements"] != _NEEDS_LABEL["elements"]

    def test_every_needed_key_has_an_operator_label(self):
        """The `.get(k, k)` fallback prints the raw internal key at an operator.
        It fired once on four keys, so the next key added to a row's `needs`
        fails here instead of shipping `no aligned_elements` in a roster."""
        from stellars_claude_code_plugins.svg_tools.finalize import _CHECKLIST, _NEEDS_LABEL

        needed = {k for _g, _l, _lay, _t, needs in _CHECKLIST for k in (needs or "").split("+") if k}
        assert needed - set(_NEEDS_LABEL) == set()

    def test_every_roster_note_fits_eighty_columns(self, tmp_path):
        """A wrapped roster is a roster nobody reads. The compound rows are the
        long ones, so build the file that makes every gate fire at once."""
        from stellars_claude_code_plugins.svg_tools.finalize import (
            _CHECKLIST,
            _NEEDS_LABEL,
            format_checklist,
        )

        rows = []
        for group, label, _layer, _token, needs in _CHECKLIST:
            note = (
                "no " + " or ".join(_NEEDS_LABEL.get(k, k) for k in needs.split("+"))
                if needs
                else ""
            )
            rows.append((group, label, "NA", note))
        out = format_checklist(
            "widest.svg", rows, {"PASS": 0, "FAIL": 0, "NA": len(rows), "SKIP": 0}
        )
        longest = max(out.splitlines(), key=len)
        assert len(longest) <= 80, f"{len(longest)} cols: {longest!r}"


class TestRound6Findings:
    """Findings the roster counted but the operator could not act on."""

    def test_each_forbidden_colour_gets_its_own_ack_token(self, tmp_path):
        """`enforce_warning_acks` dedupes byte-identical findings, so a label
        naming only the tag collapsed four defects into one pasteable ack."""
        from stellars_claude_code_plugins.svg_tools.check_css import check_css_compliance

        f = tmp_path / "whites.svg"
        f.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            '<text x="10" y="20" fill="#fff">89%</text>'
            '<text x="10" y="60" fill="#fff">89%</text>'
            '<text x="10" y="90" fill="#fff">89%</text></svg>'
        )
        found = [v for v in check_css_compliance(str(f))[0] if v.rule == "forbidden-color"]
        assert len(found) == 3
        assert len({f"{v.element} - {v.detail}" for v in found}) == 3

    def test_an_inline_style_white_fill_fails_the_row_that_forbids_it(self, tmp_path):
        """`style="fill:#ffffff"` paints exactly what the attribute spelling
        does; reading only the attribute left `no #000/#fff` printing PASS."""
        from stellars_claude_code_plugins.svg_tools.finalize import build_checklist, finalize

        f = tmp_path / "stylewhite.svg"
        f.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            '<rect x="0" y="0" width="10" height="10" style="fill:#ffffff"/></svg>'
        )
        ran: set[str] = set()
        rows, _ = build_checklist(f, *finalize(f, None, ran), rendered=False, ran=ran)
        by = {label: status for _g, label, status, _n in rows}
        assert by["no #000/#fff"] == "FAIL"

    def test_a_black_marker_inside_defs_is_not_exempt(self, tmp_path):
        """A marker paints wherever it is cited. Exempting <defs> AND <marker>
        is the same hole twice, since markers are written inside defs."""
        from stellars_claude_code_plugins.svg_tools.check_css import check_css_compliance

        f = tmp_path / "marker.svg"
        f.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            '<defs><marker id="ah"><path d="M0 0 L8 4 L0 8 z" fill="#000000"/></marker></defs>'
            '<path d="M20 100 L300 100" stroke="#1a5a6e" marker-end="url(#ah)"/></svg>'
        )
        assert any(v.rule == "forbidden-color" for v in check_css_compliance(str(f))[0])

    def test_white_inside_a_mask_is_still_an_alpha_value(self, tmp_path):
        from stellars_claude_code_plugins.svg_tools.check_css import check_css_compliance

        f = tmp_path / "mask.svg"
        f.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            '<defs><mask id="m"><rect width="400" height="200" fill="#ffffff"/></mask></defs>'
            '<rect width="400" height="200" mask="url(#m)" fill="#1a5a6e"/></svg>'
        )
        assert not any(v.rule == "forbidden-color" for v in check_css_compliance(str(f))[0])

    def test_deck_findings_carry_their_own_ack_class(self):
        """Stripping the `[file.svg] ` prefix unconditionally ate the deck
        finding's own tag, so the documented --ack-class SOFT-CONSISTENCY
        could not reach it."""
        from stellars_claude_code_plugins.svg_tools.finalize import _layer

        # The class is read from the UNPREFIXED finding, so no rule has to guess
        # where a `[file.svg] ` prefix ends. A payload that itself opens with a
        # bracket is the case that broke the guess.
        assert _layer("[consistency] mixed card body construction") == "CONSISTENCY"
        assert _layer('[alignment] [  2] text "TITLE" - not on 5px grid') == "ALIGNMENT"
        assert _layer("[connectors] [l-routing] leg 3 is diagonal") == "CONNECTORS"


class TestRound6RenderIsolation:
    """One unreadable file must not take the visual layer from the whole deck."""

    def test_one_bad_file_does_not_zero_the_layer_for_its_siblings(self, tmp_path):
        good = tmp_path / "good.svg"
        good.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
            '<rect x="10" y="10" width="50" height="50" fill="#1a5a6e"/></svg>'
        )
        bad = tmp_path / "bad.svg"
        bad.write_text("<svg><this is not xml")
        out = subprocess.run(
            [
                sys.executable,
                "-m",
                "stellars_claude_code_plugins.svg_tools.finalize",
                str(good),
                str(bad),
                "--checklist",
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": os.environ.get("PYTHONPATH") or "src"},
        )
        block = out.stderr.split("CHECKLIST  good.svg")[1].split("CHECKLIST")[0]
        row = next(ln for ln in block.splitlines() if "rendered geometry" in ln)
        assert "SKIP" not in row, f"the healthy file lost its layer to its sibling: {row!r}"

    def test_a_dead_renderer_is_named_as_such_not_as_not_run(self, tmp_path):
        """`not run` elsewhere means the document aborted. A renderer failure is
        a different cause and must not borrow that string."""
        from stellars_claude_code_plugins.svg_tools.finalize import build_checklist

        f = tmp_path / "x.svg"
        f.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200"></svg>')
        rows, _ = build_checklist(
            f,
            [],
            [],
            rendered=False,
            ran=set(),
            skip_reasons={"visual": "renderer unavailable"},
        )
        by = {label: (status, note) for _g, label, status, note in rows}
        assert by["rendered geometry"] == ("SKIP", "renderer unavailable")

    def test_a_crashed_checker_says_why_in_the_roster(self):
        """The one state meaning "the tool is broken, not your file" was
        withholding the reason it already held."""
        from stellars_claude_code_plugins.svg_tools.finalize import format_checklist

        out = format_checklist(
            "x.svg",
            [("theme", "no #000/#fff", "SKIP", "checker crashed")],
            {"PASS": 0, "FAIL": 0, "NA": 0, "SKIP": 1},
            ["css checker crashed: ValueError: bad token at line 4"],
        )
        assert "ValueError: bad token at line 4" in out


class TestRound6MutantPins:
    """Behaviour an independent mutation battery showed nothing distinguished.

    Each of these survived the whole suite when inverted, which means the rule
    it encodes was documented but never checked.
    """

    S = SVG_OPEN

    def test_important_is_stripped_only_from_the_end(self):
        """Anchored: a colour merely CONTAINING the word must survive intact."""
        from stellars_claude_code_plugins.svg_tools.check_css import strip_important

        assert strip_important("#1a5a6e !important") == "#1a5a6e"
        assert strip_important("url(#important-grad)") == "url(#important-grad)"

    def test_an_unterminated_xml_comment_swallows_the_rest_of_the_file(self):
        """Without the EOF fallback the regex matches nothing and a commented-out
        stylesheet reads as live CSS."""
        from stellars_claude_code_plugins.svg_tools.check_css import parse_style_block

        svg = self.S + "<!-- <style>.a { fill: #ffffff; }</style>"
        light, _d, colors, meta = parse_style_block(svg)
        assert light == {} and colors == set() and meta["light_rules"] == {}

    def test_an_unterminated_css_comment_swallows_the_rest_of_the_block(self):
        from stellars_claude_code_plugins.svg_tools.check_css import parse_style_block

        svg = self.S + "<style>.a { fill: #123456; } /* .b { fill: #654321; }</style>"
        light, _d, _c, _m = parse_style_block(svg)
        assert "a" in light and "b" not in light

    def test_a_transparent_full_canvas_rect_is_not_the_ground(self, tmp_path):
        """A transparent plate inherits the document ground, which inverts on
        its own - judging it reported a defect on the documented idiom."""
        import xml.etree.ElementTree as ET

        from stellars_claude_code_plugins.svg_tools.check_css import find_backplate

        f = tmp_path / "t.svg"
        f.write_text(self.S + '<rect width="400" height="200" fill="transparent"/></svg>')
        assert find_backplate(ET.parse(str(f)).getroot(), {}) is None

    def test_a_rect_starting_far_off_canvas_is_a_bleed_not_the_ground(self, tmp_path):
        """Each axis separately: a fixture off-canvas in both is still caught
        when only one of the two bounds survives."""
        import xml.etree.ElementTree as ET

        from stellars_claude_code_plugins.svg_tools.check_css import find_backplate

        def plate(x, y, name):
            f = tmp_path / name
            f.write_text(
                self.S
                + f'<rect x="{x}" y="{y}" width="800" height="400" fill="#f5f9fc"/></svg>'
            )
            return find_backplate(ET.parse(str(f)).getroot(), {})

        assert plate(-200, 0, "bx.svg") is None, "off-canvas in x"
        assert plate(0, -100, "by.svg") is None, "off-canvas in y"

    def test_a_percentage_sized_plate_resolves_against_the_viewbox(self, tmp_path):
        import xml.etree.ElementTree as ET

        from stellars_claude_code_plugins.svg_tools.check_css import find_backplate

        f = tmp_path / "pct.svg"
        f.write_text(self.S + '<rect width="100%" height="100%" fill="#f5f9fc"/></svg>')
        assert find_backplate(ET.parse(str(f)).getroot(), {}) is not None

    def test_a_dimension_in_an_unknown_unit_is_not_read_as_user_units(self, tmp_path):
        """Defaulting an unrecognised unit to 1.0 invents a plate out of a
        dimension nobody resolved."""
        import xml.etree.ElementTree as ET

        from stellars_claude_code_plugins.svg_tools.check_css import find_backplate

        f = tmp_path / "u.svg"
        f.write_text(self.S + '<rect width="400q" height="200q" fill="#f5f9fc"/></svg>')
        assert find_backplate(ET.parse(str(f)).getroot(), {}) is None

    def test_the_two_element_parsers_keep_separate_inventory_keys(self):
        """On this shipped example the overlaps parser sees elements and the
        alignment parser does not. Collapsing the keys gives the alignment row
        its only PASS, and that PASS is false."""
        from stellars_claude_code_plugins.svg_tools.finalize import build_checklist, finalize

        f = Path("svg-infographics/examples/stellars-tech_jupyterhub_logo_basic.svg")
        if not f.is_file():
            pytest.skip("example not present")
        ran: set[str] = set()
        rows, _ = build_checklist(f, *finalize(f, None, ran), rendered=False, ran=ran)
        by = {label: status for _g, label, status, _n in rows}
        assert by["no element overlaps"] == "FAIL"
        assert by["alignment and rhythm"] == "NA"


class TestRound5CascadeFollowups:
    """The round-5 review findings, pinned. Each test is a mutation the fix
    dies on: revert the mechanism and exactly one of these fails."""

    S = SVG_OPEN

    def _model(self, tmp_path, svg, name="t.svg"):
        import xml.etree.ElementTree as ET

        from stellars_claude_code_plugins.svg_tools.check_css import (
            build_render_model,
            parse_style_block,
        )

        f = tmp_path / name
        f.write_text(svg)
        _l, _d, _c, meta = parse_style_block(svg)
        root = ET.parse(str(f)).getroot()
        return root, meta, build_render_model(root)

    def test_theme_paint_dark_side_stops_at_the_same_declaration(self, tmp_path):
        """An ancestor's dark repaint never outranks the node's own light rule:
        resolving the dark side against the dark map alone walked to a DIFFERENT
        element and ranked two declarations that never competed."""
        from stellars_claude_code_plugins.svg_tools.check_css import theme_paint

        svg = (
            self.S
            + "<style>.lbl { fill: #1e3a5f; } .grp { fill: #3b4a5a; }"
            "@media (prefers-color-scheme: dark) { .grp { fill: #101418; } }</style>"
            '<g class="grp"><g class="lbl"><text x="5" y="20">hi</text></g></g></svg>'
        )
        root, meta, model = self._model(tmp_path, svg)
        _nr, _dis, _res, winning_paint, _p, _own = model
        text = next(e for e in root.iter() if e.tag.endswith("text"))
        paint = theme_paint(
            text, "fill", meta["light_rules"], meta["dark_rules"], winning_paint
        )
        assert paint.dark == "#1e3a5f"
        assert paint.overridden is False

    def test_important_class_ties_break_on_source_order(self, tmp_path):
        """Two important declarations of one property tie on importance AND
        specificity; the attribute's name order is not the tiebreak."""
        svg = (
            self.S
            + "<style>.a { fill: #0000ff !important; } .b { fill: #ff0000 !important; }</style>"
            '<rect class="a b" width="10" height="10"/></svg>'
        )
        root, meta, model = self._model(tmp_path, svg)
        _nr, _dis, resolve, _w, _p, _own = model
        rect = next(e for e in root.iter() if e.tag.endswith("rect"))
        assert resolve(rect, "fill", meta["light_rules"]) == "#ff0000"

    def test_a_light_important_survives_the_merged_sheet(self, tmp_path):
        """A normal dark declaration never displaces a light `!important` - the
        dark block ADDS rules, and a dict merge silently dropped the ranking."""
        from stellars_claude_code_plugins.svg_tools.check_css import merged_rules, theme_paint

        svg = (
            self.S
            + "<style>.card { fill: #e8eef5 !important; }"
            "@media (prefers-color-scheme: dark) { .card { fill: #101418; } }</style>"
            '<rect class="card" width="400" height="200"/></svg>'
        )
        root, meta, model = self._model(tmp_path, svg)
        _nr, _dis, _res, winning_paint, _p, _own = model
        merged = merged_rules(meta["light_rules"], meta["dark_rules"])
        rect = next(e for e in root.iter() if e.tag.endswith("rect"))
        assert winning_paint(rect, "fill", merged)[1].startswith("#e8eef5")
        paint = theme_paint(
            rect, "fill", meta["light_rules"], meta["dark_rules"], winning_paint, merged=merged
        )
        assert paint.dark == paint.light
        assert paint.overridden is False

    def test_dark_fill_none_on_text_is_a_failure_not_silence(self, tmp_path):
        """`fill:none` under the dark query renders nothing: the row scores
        1.00:1 and fails. No row at all read as PASS."""
        from stellars_claude_code_plugins.svg_tools.check_contrast import (
            check_all_contrasts,
            parse_svg_for_contrast,
        )

        f = tmp_path / "t.svg"
        f.write_text(
            self.S
            + "<style>.lbl { fill: #24405f; }"
            "@media (prefers-color-scheme: dark) { .lbl { fill: none; } }</style>"
            '<text class="lbl" x="5" y="20">hi</text></svg>'
        )
        texts, bgs, lc, dc = parse_svg_for_contrast(str(f))
        results, hints = check_all_contrasts(texts, bgs, lc, dc)
        dark = [r for r in results if r.mode == "dark"]
        assert len(dark) == 1 and dark[0].ratio == 1.0 and dark[0].aa_pass is False

    def test_dark_var_on_text_is_unmeasurable_not_silence(self, tmp_path):
        """The doctrine the ground already got: a dark paint nobody can read is
        reported, never dropped."""
        from stellars_claude_code_plugins.svg_tools.check_contrast import (
            check_all_contrasts,
            parse_svg_for_contrast,
        )

        f = tmp_path / "t.svg"
        f.write_text(
            self.S
            + "<style>.lbl { fill: #24405f; }"
            "@media (prefers-color-scheme: dark) { .lbl { fill: var(--fg); } }</style>"
            '<text class="lbl" x="5" y="20">hi</text></svg>'
        )
        texts, bgs, lc, dc = parse_svg_for_contrast(str(f))
        results, hints = check_all_contrasts(texts, bgs, lc, dc)
        assert not [r for r in results if r.mode == "dark"]
        assert any("UNMEASURABLE" in h and "var(--fg)" in h for h in hints)

    def test_dark_fill_none_on_a_plate_falls_through_to_the_document(self, tmp_path):
        """A plate painted `none` in the dark block is no ground at all under
        the query - not an unreadable one. The conflation blocked a legible
        document with a HARD."""
        from stellars_claude_code_plugins.svg_tools.check_contrast import (
            check_all_contrasts,
            parse_svg_for_contrast,
        )

        f = tmp_path / "t.svg"
        f.write_text(
            self.S
            + "<style>.card { fill: #dfe7ee; } .lbl { fill: #24405f; }"
            "@media (prefers-color-scheme: dark) { .card { fill: none; }"
            " .lbl { fill: #dfe8f2; } }</style>"
            '<rect class="card" x="0" y="5" width="100" height="30"/>'
            '<text class="lbl" x="5" y="20">hi</text></svg>'
        )
        texts, bgs, lc, dc = parse_svg_for_contrast(str(f))
        assert bgs and bgs[0].dark_paints_nothing and not bgs[0].dark_unreadable
        results, hints = check_all_contrasts(texts, bgs, lc, dc)
        dark = [r for r in results if r.mode == "dark"]
        assert len(dark) == 1 and dark[0].effective_bg == "#1e1e1e"
        assert not [h for h in hints if "UNMEASURABLE" in h]

    def test_a_shape_blends_its_dark_fill_at_the_dark_alpha(self, tmp_path):
        """`Shape` carried a dark colour beside the LIGHT alpha: a 4%-wash plate
        repainted solid in dark scored 1.06 FAIL on a 5.35 PASS document."""
        from stellars_claude_code_plugins.svg_tools.check_contrast import (
            check_object_contrasts,
            parse_svg_shapes,
        )

        f = tmp_path / "s.svg"
        f.write_text(
            self.S
            + "<style>.card { fill: #00a6ff; fill-opacity: 0.04; }"
            "@media (prefers-color-scheme: dark) { .card { fill-opacity: 1; } }</style>"
            '<rect class="card" x="20" y="20" width="100" height="100"/></svg>'
        )
        shapes, _lc, dark_cls, cw, ch = parse_svg_shapes(str(f))
        results = check_object_contrasts(shapes, dark_cls, cw, ch)
        dark = [r for r in results if r.mode == "dark"]
        assert len(dark) == 1 and dark[0].fill_ratio > 3.0 and dark[0].passed

    def test_class_declared_group_opacity_reaches_the_plate_election(self, tmp_path):
        """`.grain{opacity:0.06}` on a group is a wash however it is spelled;
        reading only the attribute elected the wash as the page."""
        import xml.etree.ElementTree as ET

        from stellars_claude_code_plugins.svg_tools.check_css import (
            find_backplate,
            parse_style_block,
        )

        svg = (
            self.S
            + "<style>.page { fill: #12181e; } .grain { opacity: 0.06; }</style>"
            '<rect class="page" width="400" height="200"/>'
            '<g class="grain"><rect width="400" height="200" fill="#f7fbff"/></g></svg>'
        )
        f = tmp_path / "g.svg"
        f.write_text(svg)
        _l, _d, _c, meta = parse_style_block(svg)
        plate = find_backplate(ET.parse(str(f)).getroot(), meta["light_rules"])
        assert plate is not None and plate.get("class") == "page"

    def test_display_none_in_the_style_spelling_is_not_live_paint(self, tmp_path):
        """Authoring tools emit `style="display:none"`; the attribute-only test
        scanned a hidden group as two false HARD findings."""
        from stellars_claude_code_plugins.svg_tools.check_contrast import parse_svg_for_contrast

        f = tmp_path / "h.svg"
        f.write_text(
            self.S
            + '<g style="display:none"><text x="5" y="20" fill="#000000">draft</text></g>'
            '<text x="5" y="60" fill="#12181e">live</text></svg>'
        )
        texts, _bgs, _lc, _dc = parse_svg_for_contrast(str(f))
        assert [t.content for t in texts] == ["live"]

    def test_geometry_that_is_not_a_number_is_skipped_not_crashed_on(self, tmp_path):
        """`width="100%"` and a per-glyph `x="40 52 64"` are legal SVG; bare
        `float()` died on both, and the drill-in command printed the traceback."""
        from stellars_claude_code_plugins.svg_tools.check_contrast import parse_svg_for_contrast

        f = tmp_path / "w.svg"
        f.write_text(
            self.S
            + '<rect width="100%" height="100%" fill="#f5f9fc"/>'
            '<text x="40 52 64" y="20" fill="#12181e">abc</text></svg>'
        )
        texts, bgs, _lc, _dc = parse_svg_for_contrast(str(f))
        assert len(texts) == 1 and texts[0].x == 40.0
        assert any(b.w == 400.0 for b in bgs)

    def test_a_normal_dark_override_under_a_light_important_is_not_coverage(self, tmp_path):
        """The dark declaration LOSES, so the paint keeps its light value;
        presence in the dark rule read as coverage and the file rendered
        identically in both themes under two PASS rows."""
        from stellars_claude_code_plugins.svg_tools.check_css import (
            check_dark_mode_coverage,
            parse_style_block,
        )

        svg = (
            self.S
            + "<style>.card { fill: #e8eef5 !important; }"
            "@media (prefers-color-scheme: dark) { .card { fill: #101418; } }</style>"
            + '<rect class="card" width="10" height="10"/></svg>'
        )
        _l, _d, _c, meta = parse_style_block(svg)
        violations = check_dark_mode_coverage(meta["light_rules"], meta["dark_rules"])
        assert any(v.rule == "missing-dark-override" for v in violations)

    def test_a_transformed_named_arrowhead_is_counted_not_parked(self, tmp_path):
        """A `<polygon>` under a transform parses at raw coordinates - 45 heads
        across 9 corpus files sat at the origin, unpaired, under PASS rows.
        The parser refuses it; the inventory counts the refusal."""
        import xml.etree.ElementTree as ET

        from stellars_claude_code_plugins.svg_tools.check_connectors import parse_svg as cc_parse
        from stellars_claude_code_plugins.svg_tools.finalize import _skipped_connectors

        f = tmp_path / "a.svg"
        f.write_text(
            self.S
            + '<g transform="translate(40,30)">'
            '<line class="connector" x1="0" y1="0" x2="50" y2="0"/>'
            '<polygon class="arrow" points="50,-4 60,0 50,4"/>'
            "</g></svg>"
        )
        _cards, _conns, _labels, heads = cc_parse(str(f))
        assert heads == []
        assert _skipped_connectors(ET.parse(str(f)).getroot()) == {"line": 1, "polygon": 1}


class TestRound5CleanVerdict:
    """The clean branch's verdict reads the roster it stands under."""

    S = SVG_OPEN
    CLEAN = (
        "<style>.t { fill: #12181e; }"
        "@media (prefers-color-scheme: dark) { .t { fill: #e8f0f8; } }</style>"
        '<text class="t" x="20" y="40">hi</text></svg>'
    )

    def test_unasked_skips_flip_the_verdict_and_the_exit_code(self, tmp_path, monkeypatch, capsys):
        """Zero findings beside unjudged aspects is not a ship decision: the
        roster nagged `these are not passes` and the verdict printed
        `OK - shippable` over it, exit 0, with --json carrying no trace."""
        import json

        from stellars_claude_code_plugins.svg_tools import finalize as fin
        from stellars_claude_code_plugins.svg_tools import render_inspect

        def _boom(_paths):
            raise RuntimeError("no renderer here")

        monkeypatch.setattr(render_inspect, "extract_bboxes", _boom)
        f = tmp_path / "c.svg"
        f.write_text(self.S + self.CLEAN)
        rc = fin.main([str(f), "--json"])
        assert rc == 1
        out = json.loads(capsys.readouterr().out)
        skipped = out["files"][str(f)]["skipped"]
        assert skipped.get("rendered geometry") == "renderer unavailable"

    def test_an_asked_skip_stays_shippable(self, tmp_path, capsys):
        """`--no-visual` is the operator's choice, not an unjudged layer."""
        from stellars_claude_code_plugins.svg_tools import finalize as fin

        f = tmp_path / "c.svg"
        f.write_text(self.S + self.CLEAN)
        rc = fin.main([str(f), "--no-visual"])
        assert rc == 0
        assert "OK - shippable" in capsys.readouterr().err


class TestRound6TieBreakSpaces:
    """The `@seq` offsets live in ONE coordinate space. Splicing the light
    text compressed it while the dark parse kept original offsets, and
    `m.start()` demoted the first rule after a blanked span - the merged-sheet
    tie-break then resolved cross-selector ties to the wrong class."""

    S = SVG_OPEN

    def _paint(self, tmp_path, css, cls):
        import xml.etree.ElementTree as ET

        from stellars_claude_code_plugins.svg_tools.check_css import (
            build_render_model,
            parse_style_block,
            theme_paint,
        )

        svg = self.S + f"<style>{css}</style>" + f'<rect class="{cls}" width="9" height="9"/></svg>'
        f = tmp_path / "t.svg"
        f.write_text(svg)
        _l, _d, _c, meta = parse_style_block(svg)
        root = ET.parse(str(f)).getroot()
        _nr, _dis, _res, winning_paint, _p, _own = build_render_model(root)
        rect = next(e for e in root.iter() if e.tag.endswith("rect"))
        return theme_paint(rect, "fill", meta["light_rules"], meta["dark_rules"], winning_paint)

    def test_a_dark_override_keeps_its_place_in_source_order(self, tmp_path):
        """Browser: `.a` dark (latest) wins the tie against light `.b`. The
        first dark rule used to record offset 0 and lose every tie."""
        paint = self._paint(
            tmp_path,
            ".a { fill: #111111; } .b { fill: #222222; }"
            "@media (prefers-color-scheme: dark) { .a { fill: #101418; } }",
            "a b",
        )
        assert paint.light == "#222222"
        assert paint.dark == "#101418"
        assert paint.overridden is True

    def test_a_light_rule_after_the_block_keeps_its_offset(self, tmp_path):
        """`.y` sits after the @media block, so it beats dark-only `.e` under
        the query. Spliced light offsets made the dark rule look later."""
        paint = self._paint(
            tmp_path,
            ".x { fill: #eeeeee; }"
            "@media (prefers-color-scheme: dark) { .d { fill: #111111; } .e { fill: #222222; } }"
            ".y { fill: #aaaaaa; }",
            "e y",
        )
        assert paint.dark == "#aaaaaa"
        assert paint.overridden is False

    def test_the_seq_offset_points_at_the_selector(self, tmp_path):
        """Not at the blank run the rule regex swallows ahead of it."""
        from stellars_claude_code_plugins.svg_tools.check_css import _SEQ, parse_style_block

        css = (
            ".a { fill: #111111; } "
            "@media (prefers-color-scheme: dark) { .a { fill: #222222; } } "
            ".b { fill: #333333; }"
        )
        _l, _d, _c, meta = parse_style_block(self.S + f"<style>{css}</style></svg>")
        assert meta["light_rules"][".b"][_SEQ]["fill"] == css.index(".b")
        assert meta["dark_rules"][".a"][_SEQ]["fill"] == css.index(".a", css.index("@media"))

    def test_a_single_theme_sheet_parses_no_dark_rules(self, tmp_path):
        """The guard: an all-blank dark string is the rule regex's quadratic
        worst case, and there is nothing to find in it."""
        from stellars_claude_code_plugins.svg_tools.check_css import parse_style_block

        _l, _d, _c, meta = parse_style_block(
            self.S + "<style>.a { fill: #111111; }</style></svg>"
        )
        assert meta["has_dark_block"] is False
        assert meta["dark_rules"] == {}

    def test_display_none_hides_in_any_case(self, tmp_path):
        """`display="NONE"` and `style="DISPLAY:None"` hide in a renderer; the
        case-sensitive comparison scanned them as live paint."""
        from stellars_claude_code_plugins.svg_tools.check_contrast import parse_svg_for_contrast

        f = tmp_path / "c.svg"
        f.write_text(
            self.S
            + '<g display="NONE"><text x="5" y="20" fill="#000000">a</text></g>'
            + '<g style="DISPLAY:None "><text x="5" y="40" fill="#000000">b</text></g>'
            + '<text x="5" y="60" fill="#12181e">live</text></svg>'
        )
        texts, _b, _lc, _dc = parse_svg_for_contrast(str(f))
        assert [t.content for t in texts] == ["live"]


class TestRound6RosterVerdicts:
    """Both verdict branches answer to the roster, and the arrowhead row can
    reach its SKIP state."""

    S = SVG_OPEN

    def test_skipped_named_polygon_routes_the_head_row_to_skip(self, tmp_path):
        """One parsed head beside nine the parser refused printed PASS. The
        skipped count is per tag now: a skipped polygon is an unjudged HEAD."""
        from stellars_claude_code_plugins.svg_tools.finalize import build_checklist, finalize

        f = tmp_path / "a.svg"
        f.write_text(
            self.S
            + "<style>.card { fill: #eeeeee; }"
            "@media (prefers-color-scheme: dark) { .card { fill: #17202a; } }</style>"
            '<rect class="card" x="10" y="10" width="100" height="60"/>'
            '<polygon points="120,25 130,28 120,31"/>'
            '<g transform="translate(200,0)"><polygon class="arrow" points="0,0 10,3 0,6"/></g>'
            "</svg>"
        )
        ran: set[str] = set()
        rows, _ = build_checklist(f, *finalize(f, None, ran), rendered=False, ran=ran)
        by = {label: (status, note) for _g, label, status, note in rows}
        status, note = by["head points into the card"]
        assert status == "SKIP"
        assert note == "arrowheads the parser skipped"

    def test_acked_soft_findings_do_not_ship_over_unjudged_aspects(self, tmp_path, capsys):
        """The findings branch consulted no roster: acked SOFT + exit 0 beside
        nine connector aspects the parser skipped. Same doctrine as the clean
        branch, now both branches."""
        import re

        import pytest

        from stellars_claude_code_plugins.svg_tools import finalize as fin

        f = tmp_path / "s.svg"
        f.write_text(
            self.S
            + "<style>.t { fill: #12181e; } .ghost { fill: #aabbcc; }"
            "@media (prefers-color-scheme: dark) { .t { fill: #e8f0f8; } }</style>"
            '<text class="t" x="20" y="40">hi</text>'
            '<g transform="translate(300,150)"><line class="connector" x1="0" y1="0" x2="50" y2="0"/>'
            "</g></svg>"
        )
        with pytest.raises(SystemExit):
            fin.main([str(f), "--no-visual"])
        acks = []
        for tok in re.findall(r"W-[0-9a-f]{8}", capsys.readouterr().err):
            acks += ["--ack-warning", f"{tok}=fixture"]
        rc = fin.main([str(f), "--no-visual", *acks])
        err = capsys.readouterr().err
        assert rc == 1
        assert "NOT VERIFIED" in err
        assert "connectors the parser skipped" in err

    def test_acked_soft_findings_ship_when_everything_was_judged(self, tmp_path, capsys):
        """The sibling arm: same ack flow, nothing unjudged - exit stays 0."""
        import re

        import pytest

        from stellars_claude_code_plugins.svg_tools import finalize as fin

        f = tmp_path / "s.svg"
        f.write_text(
            self.S
            + "<style>.t { fill: #12181e; } .ghost { fill: #aabbcc; }"
            "@media (prefers-color-scheme: dark) { .t { fill: #e8f0f8; } }</style>"
            '<text class="t" x="20" y="40">hi</text></svg>'
        )
        with pytest.raises(SystemExit):
            fin.main([str(f), "--no-visual"])
        acks = []
        for tok in re.findall(r"W-[0-9a-f]{8}", capsys.readouterr().err):
            acks += ["--ack-warning", f"{tok}=fixture"]
        rc = fin.main([str(f), "--no-visual", *acks])
        assert rc == 0


class TestRound7Followups:
    """Round-7 latent findings: one coordinate space for the same-selector
    dark landing, one machinery for the two `display:none` matchers, one
    semantics per JSON key."""

    S = SVG_OPEN

    def test_later_light_redeclaration_wins_over_the_dark_landing(self, tmp_path):
        """merged_rules landed the dark declaration unconditionally, but a
        light redeclaration AFTER the media block wins the equal-specificity
        tie in a browser - the offsets share one space now, so the tie is
        decidable and the landing must yield."""
        from stellars_claude_code_plugins.svg_tools.check_css import (
            merged_rules,
            parse_style_block,
        )

        css = (
            ".a { fill: #111111; }"
            "@media (prefers-color-scheme: dark) { .a { fill: #222222; } }"
            ".a { fill: #333333; }"
        )
        _l, _d, _c, meta = parse_style_block(self.S + f"<style>{css}</style></svg>")
        merged = merged_rules(meta["light_rules"], meta["dark_rules"])
        assert merged[".a"]["fill"] == "#333333"

    def test_dark_landing_still_wins_when_it_is_the_later_declaration(self, tmp_path):
        """The sibling arm: the redeclaration sits BEFORE the media block, so
        the dark declaration is the later one and must still land."""
        from stellars_claude_code_plugins.svg_tools.check_css import (
            merged_rules,
            parse_style_block,
        )

        css = (
            ".a { fill: #111111; }"
            ".a { fill: #333333; }"
            "@media (prefers-color-scheme: dark) { .a { fill: #222222; } }"
        )
        _l, _d, _c, meta = parse_style_block(self.S + f"<style>{css}</style></svg>")
        merged = merged_rules(meta["light_rules"], meta["dark_rules"])
        assert merged[".a"]["fill"] == "#222222"

    def test_dark_important_lands_over_a_later_light_normal(self, tmp_path):
        """Importance outranks source order: the landing guard compares
        offsets only at EQUAL importance, or an early dark `!important` would
        lose to a later light normal - the cascade runs importance first."""
        from stellars_claude_code_plugins.svg_tools.check_css import (
            merged_rules,
            parse_style_block,
        )

        css = (
            "@media (prefers-color-scheme: dark) { .a { fill: #222222 !important; } }"
            ".a { fill: #333333; }"
        )
        _l, _d, _c, meta = parse_style_block(self.S + f"<style>{css}</style></svg>")
        merged = merged_rules(meta["light_rules"], meta["dark_rules"])
        assert merged[".a"]["fill"] == "#222222 !important"

    def test_later_light_important_wins_over_an_earlier_dark_important(self, tmp_path):
        """Both flagged - the tie IS source order, and the later light wins."""
        from stellars_claude_code_plugins.svg_tools.check_css import (
            merged_rules,
            parse_style_block,
        )

        css = (
            "@media (prefers-color-scheme: dark) { .a { fill: #222222 !important; } }"
            ".a { fill: #333333 !important; }"
        )
        _l, _d, _c, meta = parse_style_block(self.S + f"<style>{css}</style></svg>")
        merged = merged_rules(meta["light_rules"], meta["dark_rules"])
        assert merged[".a"]["fill"] == "#333333 !important"

    def test_theme_paint_answers_the_later_light_value(self, tmp_path):
        """End to end through the resolver the HARD tier consumes: dark side
        of a same-selector pair follows source order, not landing order."""
        import xml.etree.ElementTree as ET

        from stellars_claude_code_plugins.svg_tools.check_css import (
            build_render_model,
            parse_style_block,
            theme_paint,
        )

        css = (
            ".a { fill: #111111; }"
            "@media (prefers-color-scheme: dark) { .a { fill: #222222; } }"
            ".a { fill: #333333; }"
        )
        svg = self.S + f"<style>{css}</style>" + '<rect class="a"/></svg>'
        f = tmp_path / "tp.svg"
        f.write_text(svg)
        _l, _d, _c, meta = parse_style_block(svg)
        root = ET.parse(str(f)).getroot()
        _nr, _dis, _res, winning_paint, _p, _own = build_render_model(root)
        rect = next(e for e in root.iter() if e.tag.endswith("rect"))
        tp = theme_paint(rect, "fill", meta["light_rules"], meta["dark_rules"], winning_paint)
        assert tp.light == "#333333"
        assert tp.dark == "#333333"
        assert tp.overridden is False

    def test_important_display_none_hides_from_the_colour_scan(self, tmp_path):
        """`display:none !important` compared unequal to "none", so the group
        scanned as live paint while the connector walk hid it - one element,
        two answers, and the invisible glyphs reached the HARD tier."""
        import xml.etree.ElementTree as ET

        from stellars_claude_code_plugins.svg_tools.check_css import build_render_model

        svg = (
            self.S
            + '<g style="display:none !important">'
            '<text x="20" y="40" fill="#eeeeee">ghost</text></g></svg>'
        )
        root = ET.fromstring(svg)
        is_nonrendering, *_ = build_render_model(root)
        text = next(e for e in root.iter() if e.tag.endswith("text"))
        assert is_nonrendering(text) is True

    def test_important_display_none_hides_from_the_connector_walk(self, tmp_path):
        """The other matcher, same spelling - both sides now run one regex."""
        from stellars_claude_code_plugins.svg_tools.check_connectors import parse_svg

        f = tmp_path / "c.svg"
        f.write_text(
            self.S
            + '<g style="display:none !important">'
            '<line x1="0" y1="0" x2="50" y2="0"/></g></svg>'
        )
        assert parse_svg(str(f))[1] == []

    def test_border_display_none_does_not_hide(self, tmp_path):
        """The substring matcher read `border-display:none` as hidden - a
        connectors-only false positive the declaration parse rejects."""
        from stellars_claude_code_plugins.svg_tools.check_connectors import parse_svg

        f = tmp_path / "c.svg"
        f.write_text(
            self.S
            + '<g style="border-display:none">'
            '<line x1="0" y1="0" x2="50" y2="0"/></g></svg>'
        )
        assert len(parse_svg(str(f))[1]) == 1

    def test_clean_branch_json_carries_totals(self, tmp_path, capsys):
        """The findings branch grew `totals`; the clean branch omitted it, so
        a consumer's `data["totals"]["hard"]` failed on exactly the green
        path. One schema on every exit."""
        import json

        from stellars_claude_code_plugins.svg_tools import finalize as fin

        f = tmp_path / "c.svg"
        f.write_text(
            self.S
            + "<style>.t { fill: #12181e; }"
            "@media (prefers-color-scheme: dark) { .t { fill: #e8f0f8; } }</style>"
            '<text class="t" x="20" y="40">hi</text></svg>'
        )
        rc = fin.main([str(f), "--json", "--no-visual"])
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["totals"] == {"hard": 0, "soft": 0}

    def test_hard_path_json_carries_the_real_skipped_map(self, tmp_path, capsys):
        """`roster_skips` was built only when no HARD findings existed, so the
        same `skipped` key meant "nothing unjudged" on two paths and "not
        consulted" on the third - one key, two semantics."""
        import json
        import re

        import pytest

        from stellars_claude_code_plugins.svg_tools import finalize as fin

        f = tmp_path / "h.svg"
        f.write_text(
            self.S
            + "<style>.t { fill: #12181e; } .bad { fill: #fdfdfd; }"
            "@media (prefers-color-scheme: dark) { .t { fill: #e8f0f8; } }</style>"
            '<text class="t" x="20" y="40">hi</text>'
            '<text class="bad" x="20" y="60">x</text>'
            '<g transform="translate(300,150)">'
            '<line class="connector" x1="0" y1="0" x2="50" y2="0"/></g>'
            "</svg>"
        )
        with pytest.raises(SystemExit):
            fin.main([str(f), "--no-visual", "--json"])
        acks = []
        for tok in re.findall(r"W-[0-9a-f]{8}", capsys.readouterr().err):
            acks += ["--ack-warning", f"{tok}=fixture"]
        rc = fin.main([str(f), "--no-visual", "--json", *acks])
        assert rc == 1
        out = json.loads(capsys.readouterr().out)
        skipped = out["files"][str(f)]["skipped"]
        assert skipped
        assert any("parser skipped" in note for note in skipped.values())

    def test_mixed_run_prints_a_verdict_for_the_healthy_file(self, tmp_path, capsys):
        """A mixed findings run printed NOT VERIFIED for the unjudged file and
        nothing at all for the healthy one - silence read as "also
        unverified", the inference the roster exists to kill."""
        import re

        import pytest

        from stellars_claude_code_plugins.svg_tools import finalize as fin

        head = (
            "<style>.t { fill: #12181e; } .ghost { fill: #aabbcc; }"
            "@media (prefers-color-scheme: dark) { .t { fill: #e8f0f8; } }</style>"
            '<text class="t" x="20" y="40">hi</text>'
        )
        bad = tmp_path / "bad.svg"
        bad.write_text(
            self.S
            + head
            + '<g transform="translate(300,150)">'
            '<line class="connector" x1="0" y1="0" x2="50" y2="0"/></g></svg>'
        )
        good = tmp_path / "good.svg"
        good.write_text(self.S + head + "</svg>")
        with pytest.raises(SystemExit):
            fin.main([str(bad), str(good), "--no-visual"])
        acks = []
        for tok in re.findall(r"W-[0-9a-f]{8}", capsys.readouterr().err):
            acks += ["--ack-warning", f"{tok}=fixture"]
        rc = fin.main([str(bad), str(good), "--no-visual", *acks])
        err = capsys.readouterr().err
        assert rc == 1
        assert f"finalize {bad}: NOT VERIFIED" in err
        assert f"finalize {good}: OK - findings acked, all aspects judged." in err
        assert err.index("NOT VERIFIED") < err.index("OK - findings acked")


class TestRound8Followups:
    """Round-8 findings: the third hidden-subtree predicate joins the shared
    one, and the HARD path stops withholding the unjudged aspects from the
    surface the operator plans the editing pass on."""

    S = SVG_OPEN

    def test_border_display_none_stays_in_the_overlaps_model(self, tmp_path):
        """The third predicate was still a substring read: a `*-display:none`
        custom property silently dropped a visible subtree from the HARD-tier
        overlaps model while the colour scan and connector walk read it live."""
        from stellars_claude_code_plugins.svg_tools.check_overlaps import parse_svg

        f = tmp_path / "o.svg"
        f.write_text(
            self.S
            + '<g style="border-display:none"><text x="20" y="40">live</text></g></svg>'
        )
        assert len(parse_svg(str(f))) == 1

    def test_display_none_important_hides_from_the_overlaps_model(self, tmp_path):
        """The flag spelling must hide here exactly as in the other two layers."""
        from stellars_claude_code_plugins.svg_tools.check_overlaps import parse_svg

        f = tmp_path / "o.svg"
        f.write_text(
            self.S
            + '<g style="display:none !important"><text x="20" y="40">ghost</text></g></svg>'
        )
        assert parse_svg(str(f)) == []

    def test_hard_path_names_the_unjudged_aspects_at_planning_time(self, tmp_path, capsys):
        """The HARD path printed only `N hard, M soft` plus the re-run-ONCE
        protocol; the operator fixed the findings, re-ran, and met the
        unjudged aspects one gate cycle later than the protocol promised."""
        import re

        import pytest

        from stellars_claude_code_plugins.svg_tools import finalize as fin

        f = tmp_path / "h.svg"
        f.write_text(
            self.S
            + "<style>.t { fill: #12181e; } .bad { fill: #fdfdfd; }"
            "@media (prefers-color-scheme: dark) { .t { fill: #e8f0f8; } }</style>"
            '<text class="t" x="20" y="40">hi</text>'
            '<text class="bad" x="20" y="60">x</text>'
            '<g transform="translate(300,150)">'
            '<line class="connector" x1="0" y1="0" x2="50" y2="0"/></g>'
            "</svg>"
        )
        with pytest.raises(SystemExit):
            fin.main([str(f), "--no-visual"])
        acks = []
        for tok in re.findall(r"W-[0-9a-f]{8}", capsys.readouterr().err):
            acks += ["--ack-warning", f"{tok}=fixture"]
        rc = fin.main([str(f), "--no-visual", *acks])
        err = capsys.readouterr().err
        assert rc == 1
        assert "NOT VERIFIED" in err
        assert "connectors the parser skipped" in err
        assert err.index("batch-fix protocol") < err.index("NOT VERIFIED")

    def test_uniform_acked_soft_run_prints_the_ok_line(self, tmp_path, capsys):
        """The OK verdict line went to the mixed branch only; the commonest
        acked state (one file, everything judged) got the next: guidance and
        no verdict line at all."""
        import re

        import pytest

        from stellars_claude_code_plugins.svg_tools import finalize as fin

        f = tmp_path / "s.svg"
        f.write_text(
            self.S
            + "<style>.t { fill: #12181e; } .ghost { fill: #aabbcc; }"
            "@media (prefers-color-scheme: dark) { .t { fill: #e8f0f8; } }</style>"
            '<text class="t" x="20" y="40">hi</text></svg>'
        )
        with pytest.raises(SystemExit):
            fin.main([str(f), "--no-visual"])
        acks = []
        for tok in re.findall(r"W-[0-9a-f]{8}", capsys.readouterr().err):
            acks += ["--ack-warning", f"{tok}=fixture"]
        rc = fin.main([str(f), "--no-visual", *acks])
        err = capsys.readouterr().err
        assert rc == 0
        assert "OK - findings acked, all aspects judged." in err
