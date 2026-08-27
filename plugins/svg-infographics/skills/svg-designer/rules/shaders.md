# Shader-mimicking effects (SVG filter recipes)

Shader-style atmospheric effects achievable via native SVG filter primitives. No JavaScript, no Canvas. The 10 recipes below cover frosted glass, water ripples, iridescent surfaces, chromatic aberration, embossed metal, light leaks, bokeh, lens flare, holographic foil, and paper grain.

**Used by beautify dimension 8.** Sub-agents read this file and paste the chosen recipe's `<defs>` block verbatim into the target SVG, then apply `filter="url(#name)"` on the chosen element. Do NOT invent filter chains - the noise-based effects (turbulence + displacement) require very specific parameter ranges to look right.

## When shader effects help

- **Premium / brand-forward decks** - holographic-foil + chromatic-aberration on titles signals premium without changing layout
- **Atmospheric backgrounds** - water-ripple + bokeh on a hero card creates depth without adding visual noise to the content layer
- **Tactile materiality** - paper-grain + light-leak makes a digital-flat infographic feel printed / hand-crafted
- **Focal emphasis** - frosted-glass on the title card pulls the eye without using colour

## When shader effects hurt

- **Word / print delivery** - rasterisers DROP filters entirely. Either ship a print-stripped variant (`+_print.svg`) or accept the degradation
- **Text legibility** - never apply distortion (water-ripple, displacement, chromatic-aberration) to body text. Titles tolerate subtle effects only
- **Performance** - complex filter chains slow browser render. Stay within the perf budget below
- **Information density** - infographics with dense KPI grids don't have visual room for atmospheric effects. Use sparingly

## Performance budget (hard limits)

- **Max 3 filter primitives per chain.** A chain of 5+ `feTurbulence` / `feDisplacementMap` / `feComposite` operations chokes browser render at scroll-into-view
- **Max 4 distinct named filters per SVG.** Each filter is a render-tree pass; 4 is the empirical ceiling before perceptible lag
- **`filterUnits="userSpaceOnUse"` MANDATORY** with explicit `x` / `y` / `width` / `height` regions. Default `objectBoundingBox` calculates region wrong for noise-based effects and produces invisible output. Always specify the bounding box in canvas coordinates
- **No SMIL animation by default.** Animating `feTurbulence baseFrequency` produces beautiful water but doubles file size and breaks print rasterisers entirely. Opt-in via beautify Batch 5 `animation: subtle` only

## Print-compatibility strategy

Word, LibreOffice, and most PDF rasterisers DROP SVG filters silently. The filtered element is rendered without the filter (i.e. flat). When `shader mode != off` is selected in beautify, two delivery strategies:

- **`strip-on-export` (DEFAULT)** - beautify produces both `<file>+.svg` (filters applied) and `<file>+_print.svg` (filters stripped). The article skill picks the print variant for Word delivery, the live variant for web / Medium / HTML
- **`preserve-effects`** - only the live variant is produced. The user accepts that Word will render the SVG flat

Mechanical strip: remove every `<filter ...>...</filter>` block from `<defs>` and every `filter="url(#...)"` attribute from elements. A sed-style pass on the raw XML is enough; no parser needed.

## The 10 recipes

Each recipe lists: the `<defs>` block to paste, the target element pattern, level guidance (which beautify level lights this up), and one anti-pattern to avoid.

---

### 1. frosted-glass

What it mimics: a frosted glass card pane (think Apple macOS Big Sur translucent panels).

```xml
<filter id="frosted-glass" filterUnits="userSpaceOnUse" x="0" y="0" width="1800" height="1100">
  <feGaussianBlur in="SourceGraphic" stdDeviation="6" result="blur"/>
  <feFlood flood-color="#ffffff" flood-opacity="0.10" result="haze"/>
  <feComposite in="haze" in2="blur" operator="in" result="frosted"/>
  <feMerge>
    <feMergeNode in="frosted"/>
    <feMergeNode in="SourceGraphic"/>
  </feMerge>
</filter>
```

Apply to: card body `<rect>` or background `<g>` group. Replace the filterUnits x/y/width/height with the target's bounding box for tight region calculation.

```xml
<rect class="card-body" x="100" y="200" width="320" height="180" filter="url(#frosted-glass)"/>
```

Level guidance: `low` (one focal card), `medium` (multiple card bodies), `high` (every card body), `absurd` (also modal overlays).

Print compat: filter dropped; card renders as solid colour - fine, no information lost.

Anti-pattern: don't apply to text containers - the blur eats the text. Apply only to card bodies / background plates.

---

### 2. water-ripple

What it mimics: surface refraction through wavy glass or shallow water.

```xml
<filter id="water-ripple" filterUnits="userSpaceOnUse" x="0" y="0" width="1800" height="1100">
  <feTurbulence type="turbulence" baseFrequency="0.025" numOctaves="2" seed="3" result="noise"/>
  <feDisplacementMap in="SourceGraphic" in2="noise" scale="10" xChannelSelector="R" yChannelSelector="G"/>
</filter>
```

Apply to: background `<g id="bg">` group containing decorative elements - NEVER on the content layer.

```xml
<g id="bg-band" filter="url(#water-ripple)">
  <!-- decorative shapes, gradient bands, NOT TEXT -->
</g>
```

Level guidance: `medium` (subtle bg band), `high` (whole background distorted), `absurd` (foreground decorative cards too).

Parameter ranges:
- `baseFrequency` 0.02-0.05 - low values = wide rolling waves, high values = tight chop
- `scale` 5-15 - low = whisper of distortion, high = obvious refraction
- `numOctaves` 2-3 - more octaves = more detail (and slower render)
- `seed` any integer - changes the noise pattern; pick a value the design likes

Print compat: filter dropped; background renders flat - acceptable.

Anti-pattern: never apply to text or anything with sharp edges that must read literally. Water-ripple destroys typography.

---

### 3. iridescent

What it mimics: oil slick on water, mother-of-pearl, beetle shell.

```xml
<filter id="iridescent" filterUnits="userSpaceOnUse" x="0" y="0" width="1800" height="1100">
  <feTurbulence type="fractalNoise" baseFrequency="0.015" numOctaves="2" seed="7" result="noise"/>
  <feColorMatrix in="noise" type="hueRotate" values="180" result="shifted"/>
  <feComposite in="shifted" in2="SourceGraphic" operator="in" result="iri"/>
  <feBlend in="iri" in2="SourceGraphic" mode="screen"/>
</filter>
```

Apply to: premium badges, focal cards, achievement tiles.

```xml
<rect class="badge premium" x="600" y="80" width="200" height="80" filter="url(#iridescent)"/>
```

Level guidance: `low` (one premium badge), `medium` (focal card), `high` (every premium element), `absurd` (everywhere).

Print compat: filter dropped; element renders as base colour - acceptable but loses the premium signal.

Anti-pattern: don't apply to large solid areas - the iridescent shimmer becomes a distracting noise pattern at scale. Keep to <200px wide elements.

---

### 4. chromatic-aberration

What it mimics: bad-CRT fringe, cheap-camera lens fringe at the corners, glitch art.

```xml
<filter id="chromatic-aberration" filterUnits="userSpaceOnUse" x="0" y="0" width="1800" height="1100">
  <feColorMatrix in="SourceGraphic" type="matrix"
    values="1 0 0 0 0   0 0 0 0 0   0 0 0 0 0   0 0 0 1 0" result="r"/>
  <feOffset in="r" dx="-1.5" dy="0" result="r-shift"/>
  <feColorMatrix in="SourceGraphic" type="matrix"
    values="0 0 0 0 0   0 1 0 0 0   0 0 0 0 0   0 0 0 1 0" result="g"/>
  <feColorMatrix in="SourceGraphic" type="matrix"
    values="0 0 0 0 0   0 0 0 0 0   0 0 1 0 0   0 0 0 1 0" result="b"/>
  <feOffset in="b" dx="1.5" dy="0" result="b-shift"/>
  <feMerge>
    <feMergeNode in="r-shift"/>
    <feMergeNode in="g"/>
    <feMergeNode in="b-shift"/>
  </feMerge>
</filter>
```

Apply to: titles (NOT body text), accent borders, focal numbers.

```xml
<text class="title" x="100" y="60" filter="url(#chromatic-aberration)">Headline</text>
```

Level guidance: `low` (one hero title), `medium` (all titles), `high` (titles + accent borders), `absurd` (also numbers, KPI values).

Parameters: `dx` offset 1-2px. Higher than 2 = unreadable. Lower than 1 = invisible. Tune to 1.5 for default.

Print compat: filter dropped; title renders as flat colour - perfect fallback.

Anti-pattern: never on body text. Even 1px offset on 12pt text makes it illegible.

---

### 5. embossed-metal

What it mimics: brushed metal nameplate, coin face, debossed card stock.

```xml
<filter id="embossed-metal" filterUnits="userSpaceOnUse" x="0" y="0" width="1800" height="1100">
  <feTurbulence type="fractalNoise" baseFrequency="0.6" numOctaves="2" seed="2" result="bump"/>
  <feSpecularLighting in="bump" surfaceScale="3" specularConstant="0.8"
    specularExponent="20" lighting-color="#ffffff" result="spec">
    <feDistantLight azimuth="135" elevation="45"/>
  </feSpecularLighting>
  <feComposite in="spec" in2="SourceGraphic" operator="in" result="lit"/>
  <feBlend in="lit" in2="SourceGraphic" mode="multiply"/>
</filter>
```

Apply to: KPI badges, achievement tiles, sectional dividers.

```xml
<rect class="kpi-badge" x="80" y="400" width="160" height="160" filter="url(#embossed-metal)"/>
```

Level guidance: `low` (one badge), `medium` (KPI row), `high` (KPI row + dividers), `absurd` (everywhere).

Parameters:
- `surfaceScale` 2-4 - height of the bump (higher = more pronounced texture)
- `specularExponent` 10-30 - sharpness of the highlight (higher = mirror-shiny, lower = matte)
- `azimuth` / `elevation` - light source angle; 135°/45° = top-left, classic emboss

Print compat: filter dropped; renders as flat colour - acceptable.

Anti-pattern: don't apply to elements smaller than 60x60px - the bump texture has no room to read.

---

### 6. light-leak

What it mimics: vintage film edge glow, lens flare bleed, sunset overlay.

```xml
<filter id="light-leak" filterUnits="userSpaceOnUse" x="-200" y="-200" width="2200" height="1500">
  <feGaussianBlur in="SourceGraphic" stdDeviation="35" result="blur"/>
  <feComposite in="blur" in2="SourceGraphic" operator="over"/>
</filter>

<radialGradient id="leak-gradient" cx="10%" cy="10%" r="40%">
  <stop offset="0%" stop-color="#ffd27a" stop-opacity="0.7"/>
  <stop offset="60%" stop-color="#ff8e3c" stop-opacity="0.3"/>
  <stop offset="100%" stop-color="#ff8e3c" stop-opacity="0"/>
</radialGradient>
```

Apply to: a `<rect>` covering the corner / edge zone, filled with the gradient, with the filter applied for soft falloff:

```xml
<rect x="0" y="0" width="600" height="400" fill="url(#leak-gradient)"
  filter="url(#light-leak)" style="mix-blend-mode: screen;"/>
```

Level guidance: `low` (one corner), `medium` (two corners), `high` (corner + edge band), `absurd` (all four corners + diagonal flare).

Notes: `mix-blend-mode: screen` is what makes the leak look additive (not just a coloured rectangle). Falls back to `over` blend if the renderer doesn't support `mix-blend-mode`.

Print compat: blend mode + filter both drop; renders as solid coloured rect - bad. Strip for print.

Anti-pattern: don't place a light leak over high-information density area (KPI tile grid). Reserve for low-information whitespace corners.

---

### 7. bokeh

What it mimics: out-of-focus background lights, party scene depth-of-field.

```xml
<filter id="bokeh-blur" filterUnits="userSpaceOnUse" x="0" y="0" width="1800" height="1100">
  <feGaussianBlur stdDeviation="8"/>
</filter>
```

Apply to: a `<g>` group of scattered `<circle>` elements:

```xml
<g id="bokeh-bg" filter="url(#bokeh-blur)" opacity="0.4">
  <circle cx="200" cy="150" r="20" fill="#5cc8e0"/>
  <circle cx="450" cy="300" r="28" fill="#da8230"/>
  <circle cx="780" cy="120" r="16" fill="#5cc8e0"/>
  <circle cx="1100" cy="450" r="34" fill="#0096d1"/>
  <circle cx="1450" cy="200" r="22" fill="#d4a04a"/>
  <!-- 5-15 circles scattered across empty-space-detected zones -->
</g>
```

Level guidance: `low` (4-6 dots), `medium` (8-12 dots), `high` (15-20 dots), `absurd` (30+ dots).

Notes: place each circle inside empty-space-detected zones (run `empty-space --edges-only` first). Vary radius 12-36px and opacity per circle (0.2-0.6) for natural distribution. Pick colours from the theme palette ONLY.

Print compat: filter dropped; circles render sharp - looks like solid dots, not bokeh. Either accept (still decorative) or strip the whole bokeh-bg group for print.

Anti-pattern: don't apply bokeh in the content layer - blurred dots behind text destroy contrast.

---

### 8. lens-flare

What it mimics: anamorphic camera flare diagonal streak.

```xml
<filter id="lens-flare-blur" filterUnits="userSpaceOnUse" x="0" y="0" width="1800" height="1100">
  <feGaussianBlur stdDeviation="3"/>
</filter>

<linearGradient id="flare-streak" x1="0%" y1="0%" x2="100%" y2="100%">
  <stop offset="0%" stop-color="#ffffff" stop-opacity="0"/>
  <stop offset="45%" stop-color="#ffd27a" stop-opacity="0.8"/>
  <stop offset="50%" stop-color="#ffffff" stop-opacity="1"/>
  <stop offset="55%" stop-color="#ffd27a" stop-opacity="0.8"/>
  <stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
</linearGradient>
```

Apply to: a long thin `<rect>` or `<line>` along a diagonal, with the streak gradient + the blur filter:

```xml
<rect x="100" y="50" width="800" height="6" fill="url(#flare-streak)"
  transform="rotate(20 500 53)" filter="url(#lens-flare-blur)"
  style="mix-blend-mode: screen;"/>
```

Level guidance: `low` (skip - too dramatic for low), `medium` (one diagonal streak from hero corner), `high` (streak + 2-3 small flare circles along it), `absurd` (multi-streak chromatic flare stack).

Print compat: blend mode + filter drop; renders as solid bar - bad. Strip for print.

Anti-pattern: don't aim the flare at content - it implies brightness on text, which is visually overwhelming.

---

### 9. holographic-foil

What it mimics: Pokemon-card foil sheen, holographic sticker.

```xml
<linearGradient id="holo-foil-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
  <stop offset="0%" stop-color="#ff77ae"/>
  <stop offset="20%" stop-color="#5cc8e0"/>
  <stop offset="40%" stop-color="#ffd27a"/>
  <stop offset="60%" stop-color="#9a7dff"/>
  <stop offset="80%" stop-color="#5cc8e0"/>
  <stop offset="100%" stop-color="#ff77ae"/>
</linearGradient>

<filter id="holo-foil" filterUnits="userSpaceOnUse" x="0" y="0" width="1800" height="1100">
  <feTurbulence type="fractalNoise" baseFrequency="0.08" numOctaves="1" seed="5" result="noise"/>
  <feColorMatrix in="noise" type="matrix"
    values="0 0 0 0 1   0 0 0 0 1   0 0 0 0 1   0 0 0 0.3 0" result="sparkle"/>
  <feComposite in="sparkle" in2="SourceGraphic" operator="in" result="sparkle-in"/>
  <feGaussianBlur in="sparkle-in" stdDeviation="0.5" result="sparkle-soft"/>
  <feBlend in="sparkle-soft" in2="SourceGraphic" mode="screen"/>
</filter>
```

Apply to: premium banner / hero card. The element fills with the foil gradient AND wears the filter:

```xml
<rect class="hero" x="100" y="100" width="1000" height="200"
  fill="url(#holo-foil-gradient)" filter="url(#holo-foil)"/>
```

Level guidance: `medium` (one premium banner), `high` (banner + premium card), `absurd` (everywhere).

Notes: the gradient gives the iridescent base; the filter adds the sparkle texture. Both work together - just gradient without filter looks flat-rainbow, just filter without gradient looks dirty.

Print compat: gradient survives, filter drops; element renders as rainbow gradient without sparkle - still premium, acceptable degradation.

Anti-pattern: don't apply to KPI numbers - the rainbow gradient makes digits unreadable. Banners and decorative panels only.

---

### 10. paper-grain

What it mimics: frosted-paper texture, vintage print stock, watercolour paper.

```xml
<filter id="paper-grain" filterUnits="userSpaceOnUse" x="0" y="0" width="1800" height="1100">
  <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="4" result="grain"/>
  <feColorMatrix in="grain" type="matrix"
    values="0 0 0 0 0   0 0 0 0 0   0 0 0 0 0   0 0 0 0.05 0"/>
</filter>
```

Apply to: a full-canvas `<rect>` placed as the very last child of the SVG so it sits above all content:

```xml
<rect x="0" y="0" width="1800" height="1100" fill="black"
  filter="url(#paper-grain)" style="pointer-events: none;"/>
```

Level guidance: `low` (very subtle, alpha 0.03), `medium` (alpha 0.05), `high` (alpha 0.08), `absurd` (alpha 0.12 + larger baseFrequency 1.2).

Notes: grain sits OVER everything as a subtle texture. Don't go above 0.12 alpha - text legibility starts to suffer. `baseFrequency` 0.9 = fine grain; 0.5 = coarse paper; 1.5 = micro-grain.

Print compat: filter dropped; nothing renders - no paper texture, page is clean. Print rendition looks fine, just less tactile.

Anti-pattern: don't use paper-grain on infographics already heavy with circuit-trace or neural-net background textures - the two compete and produce muddy noise.

---

## Composition examples (worked combos)

When the brief calls for atmospheric depth, pick 2-3 compatible recipes. Each example below is a real, ship-ready combination.

### Combo 1: "Underwater report card"

Theme: submerged / aquatic. Pairs:
- `water-ripple` on the background `<g id="bg">` (the whole canvas wobbles subtly)
- `frosted-glass` on every card body (the cards look like glass panes lying on the water)
- `bokeh` with 8 small blue/cyan dots in empty corners (sub-surface light particles)

Files: `<doc>+.svg` with all 3 filters + `<doc>+_print.svg` with all filters stripped.

### Combo 2: "Premium proposal"

Theme: high-end consulting / VC deck. Pairs:
- `holographic-foil` on the hero banner / title block
- `paper-grain` overlay (alpha 0.05) covering the whole canvas
- `chromatic-aberration` on section titles (subtle, dx 1px)

Files: same +/+_print split. The gradient on holo-foil survives the print strip, so the print variant still has a coloured banner.

### Combo 3: "Vintage photo article"

Theme: retro / printed / tactile. Pairs:
- `light-leak` in top-left corner (warm amber)
- `paper-grain` overlay
- `embossed-metal` on the publication-date badge

Files: same +/+_print split. Print variant loses the light leak but keeps the badge as a flat colour, and the paper grain is invisible.

### Combo 4: "Blueprint diagram"

Theme: engineering / technical / Tron. Pairs:
- `chromatic-aberration` on all titles AND axis labels
- `bokeh` with 6 cyan dots scattered (digital data particles)
- `embossed-metal` on the title plate

Files: same +/+_print split. Print variant: titles return to flat, badge becomes flat colour, bokeh dots become sharp circles.

### Combo 5: "Holographic banner only"

Theme: minimal premium - just one shiny element. Pairs:
- `holographic-foil` on the top banner

Files: same +/+_print split. Single-effect; the simplest combo and the lowest-risk starting point for the user's first beautify-with-shaders run.

## Anti-patterns (don't ship these combos)

- **Three filter chains on one element.** Stacking water-ripple + iridescent + chromatic-aberration on a card body produces an illegible visual stew AND tanks render performance. Pick ONE per element
- **Distortion on text.** water-ripple, displacement-based effects, large chromatic-aberration (dx >2px) on text = unreadable
- **Light leak across the content layer.** If the leak overlaps KPI numbers or body paragraphs, the eye fights the bright spot
- **paper-grain stacked with circuit-trace bg texture.** Two competing background textures = muddy noise. Pick one
- **No print-strip variant.** Shipping only `<file>+.svg` with filters when the user is sending the SVG to a Word doc = silent quality loss. Always ship both unless the user explicitly opts for `preserve-effects`
