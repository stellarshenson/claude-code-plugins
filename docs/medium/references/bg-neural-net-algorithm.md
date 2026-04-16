# Neural / Dendritic Pattern Algorithm

## Space Colonization (primary algorithm)

The gold standard for organic branching patterns. Runions et al. 2007, algorithmicbotany.org.

**How it works:**
1. Place attractor points (goals) in space, weighted by density gradient
2. Seed nodes at canvas edges (root neurons)
3. Each iteration: each active node finds nearby attractors, computes average direction, extends one step
4. When a node reaches an attractor, the attractor is consumed (prevents clumping)
5. Probabilistically branch - fork perpendicular to parent direction
6. Result: a tree graph with long parent-child chains

**Why it works for dendrites:**
- Produces biologically realistic branching with long primary axons and shorter dendrites
- Attractor consumption creates natural spreading without explicit repulsion
- Tree structure means each root-to-leaf path is ONE continuous polyline
- Unlike random walks or DLA, space colonization has "memory" - each extension continues from existing structure

## Key parameters

| Parameter | Effect | Typical value |
|-----------|--------|---------------|
| `reach` | Max distance to sense an attractor | 30-40% of canvas |
| `step` | Growth distance per iteration | 3-6% of canvas min dim |
| `branch_prob` | Fork probability per step | 0.15-0.35 |
| `attractor_density` | Number of goal points | 30-100, weighted by gradient |
| `merge_radius` | Distance for connecting to existing | 2-3x step |

## Density gradient integration

- More attractors placed in dense areas -> more branching there
- Sparse areas: fewer attractors -> traces terminate earlier (synapse dots)
- Local density modulates branch probability: dense = fork more, sparse = continue straight

## Rendering

- Chain tree into continuous polylines (root -> junction -> ... -> terminal)
- Smooth curves: quadratic bezier through chain node positions
- Thickness tapers root-to-tip: `stroke_width * (1 - depth/max_depth * 0.75)`
- Synapse dots at terminal nodes only (degree-1 non-root nodes)

## Alternative algorithms

**Diffusion Limited Aggregation (DLA)** - particles random-walk and stick. Produces fractal dendrites but fragments, no long runs. Better as secondary fill.

**L-systems** - recursive string rewriting. Compact representation but tends toward artificial symmetry.

**Dendry** (Galin et al.) - locally computable dendritic generation with parametric control. More biologically accurate but slower.

## References

- [Space Colonization Paper](https://algorithmicbotany.org/papers/colonization.egwnp2007.pdf)
- [Jason Webb: 2D Space Colonization](https://github.com/jasonwebb/2d-space-colonization-experiments)
- [Space Colonization in JavaScript](https://medium.com/@jason.webb/space-colonization-algorithm-in-javascript-6f683b743dc5)
- [Dendry: Dendritic Pattern Model](https://perso.liris.cnrs.fr/eric.galin/Articles/2019-branching.pdf)
- [Axon/Dendrite Branching Optimization](https://www.nature.com/articles/s41598-022-24813-2)
