"""Functional end-to-end tests for the svg-infographics toolchain.

Exercises the workflows an agent actually runs - scaffold, map, workflow
status, layer-filtered placement, connector routing gates, arrival
validators, the ship gate - through the Python API and the console CLI
(``python -m stellars_claude_code_plugins.svg_tools.cli``).
"""

import json
import subprocess
import sys
import textwrap

import pytest

CLI = [sys.executable, "-m", "stellars_claude_code_plugins.svg_tools.cli"]


def run_cli(*args, **kwargs):
    return subprocess.run(
        CLI + [str(a) for a in args], capture_output=True, text=True, **kwargs
    )


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
            "scaffold", "--format", fmt, "--cards", "3", "--title", "TITLE",
            "--out", out,
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
            "scaffold", "--format", "doc-grid", "--cols", "2", "--rows", "1",
            "--cards", "5", "--out", tmp_path / "x.svg",
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
            "connector", "--mode", "l-chamfer", "--chamfer", "4",
            "--standoff", "2", "--arrow", "end", "--direction", "forward",
            *args,
        )

    def test_infeasible_end_dir_blocks(self):
        """E->S with target at the same height: gate must block with
        ROUTE-DIR-REVERSED-END and ROUTE-THROUGH-TARGET."""
        r = self._connector(
            "--src-rect", "100,100,120,60", "--start-dir", "E",
            "--tgt-rect", "400,100,120,60", "--end-dir", "S",
        )
        assert r.returncode == 2
        assert "ROUTE-DIR-REVERSED-END" in r.stderr
        assert "ROUTE-THROUGH-TARGET" in r.stderr

    def test_same_axis_pair_needs_z_route(self):
        """E->E from a 1-bend threader violates the start axis - gate fires."""
        r = self._connector(
            "--src-rect", "100,100,120,60", "--start-dir", "E",
            "--tgt-rect", "400,300,120,60", "--end-dir", "E",
        )
        assert r.returncode == 2
        assert "ROUTE-AXIS-MISMATCH" in r.stderr

    def test_feasible_pair_passes(self):
        """E->S with the target below-right: clean 1-bend, gate stays open."""
        r = self._connector(
            "--src-rect", "100,100,120,60", "--start-dir", "E",
            "--tgt-rect", "400,300,120,60", "--end-dir", "S",
        )
        assert r.returncode == 0, r.stderr
        assert "trimmed for arrowhead" in r.stdout

    def test_reversed_start_sign_blocks(self):
        """start_dir=W with the target east: axis matches (h) but the sign
        is opposite - the old axis-only check let this through."""
        r = run_cli(
            "connector", "--mode", "l", "--from", "100,100", "--to", "400,300",
            "--start-dir", "W", "--arrow", "end", "--direction", "forward",
        )
        assert r.returncode == 2
        assert "ROUTE-DIR-REVERSED:" in r.stderr

    def test_ack_token_survives_flag_changes(self):
        """The stale-token burner: a token issued in run A still acks the
        same warning after an unrelated flag is added in run B."""
        base = [
            "connector", "--mode", "l-chamfer",
            "--src-rect", "100,100,120,60", "--start-dir", "E",
            "--tgt-rect", "400,300,120,60", "--end-dir", "S",
            "--chamfer", "4", "--standoff", "2", "--arrow", "end",
        ]
        first = run_cli(*base)  # missing --direction -> warning + token
        assert first.returncode == 2
        import re

        tokens = sorted(set(re.findall(r"W-[0-9a-f]{8}", first.stderr)))
        assert len(tokens) == 1
        second = run_cli(
            *base, "--color", "#7c3aed",
            "--ack-warning", f"{tokens[0]}=direction defaults acceptable in test",
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
                str(layered_scene), tolerance=2, min_area=100,
                exclude_ids=(), **kw,
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
            "empty-space", "--svg", layered_scene, "--ignore-layers", "callouts",
            "--tolerance", "20",
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
            src_rect=(40, 120, 80, 60), start_dir="E",
            tgt_rect=(480, 120, 80, 60), end_dir="E",
            auto_route=True, svg=str(svg), arrow="end",
        )
        direct = calc_l(
            src_rect=(40, 120, 80, 60), start_dir="E",
            tgt_rect=(480, 120, 80, 60), end_dir="E",
            auto_route=True, svg=str(svg), arrow="end",
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
        grid = "\n".join(
            line for line in r.stdout.splitlines() if line.startswith("  ")
        )
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
            "scaffold", "--format", "slide-16x9", "--cards", "2",
            "--title", "T", "--out", out,
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
            "scaffold", "--format", "doc-flow", "--cards", "2",
            "--title", "FLOW", "--out", out,
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
