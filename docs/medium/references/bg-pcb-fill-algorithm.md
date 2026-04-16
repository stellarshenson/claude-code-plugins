# PCB-like Circuit Fill Algorithm

## Pipeline

The most convincing PCB background patterns use a pipeline of algorithms, not a single approach.

1. **Sample anchor points / pads** - place terminal locations weighted by density gradient
2. **Connect with tree or graph** - MST, Steiner tree, or space colonization connecting terminals
3. **Route paths** - orthogonal or 45-degree constrained routing using A* or maze routing on an occupancy grid
4. **Widen traces, add pads/vias** - right-skewed thickness distribution, ring pads at endpoints
5. **Recursive gap filling** - insert smaller branches into remaining empty space

## Algorithm families

**Routing-style** (maze routing, Lee's algorithm, A* search) - real PCB routers. Produces manufacturable traces but overkill for decorative fill.

**Tree/net construction** - generate a graph of nets using MST or Steiner-tree-like connection over sampled terminals, then route geometrically. Gives the branch-and-pad feel without full EDA constraints.

**Region growth** - flood-fill-like polygon growth around obstacles. Shows up in copper pours. Different from trace routing - grows as regions that fill all legal free space.

**L-systems / graph grammars** - recursive rule systems for branching networks. Controllable but can look artificial due to symmetry.

**Space partition / skeleton** - Voronoi partitions, medial-axis extraction, space-filling curves. Even coverage without dead zones.

## Implementation (our approach)

We use **space colonization** (Runions et al. 2007) as the tree construction step, combined with:
- Occupancy grid for collision avoidance (no trace crossings)
- Grid snapping (4px) for clean PCB geometry
- 45-degree constrained rendering via chain polylines
- Density gradient via IDW interpolation controlling attractor placement
- Right-skewed stroke width distribution (many thin, fewer thick)

## References

- [Routing Algorithms for VLSI Design](https://web.eecs.umich.edu/~mazum/ClassDescriptions/Routing.pdf)
- [Global and Detailed Routing](https://cc.ee.ntu.edu.tw/~ywchang/Courses/PD_Source/EDA_routing.pdf)
- [Mathematics of PCB Trace Routing](https://tinycomputers.io/posts/the-mathematics-of-pcb-trace-routing.html)
- [Procedural Graphics: Trees and Circuit Boards](https://narf.pl/posts/procedural-trees)
- [Space Colonization Paper](https://algorithmicbotany.org/papers/colonization.egwnp2007.pdf)
