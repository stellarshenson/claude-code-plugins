# Equations in markdown cells

Resource for the `notebook-standards` skill. How to write math in notebook markdown cells - unicode glyphs inline, full equations as standalone display blocks. Referenced by the `/datascience:notebook` and `/datascience:fix-notebook` commands.

Write math liberally - express every quantitative relationship (weighting, loss, metric, update rule) as an equation, not just prose. A markdown cell that describes a formula in words should show the formula. The more of the method captured as equations, the more re-usable the notebook is downstream.

- **Inline math in unicode** - prefer unicode glyphs over `$...$` for inline expressions so they survive copy-paste and read even where MathJax does not run: `τ(i) = Σⱼ Tᵢⱼ·posⱼ / Σⱼ Tᵢⱼ`. Use subscripts (ᵢ ⱼ ₖ ₙ), superscripts (xⁿ), operators (Σ Π ∫ √ ∇ ·), relations (≤ ≥ ≈ ≠ →), Greek (α β τ λ μ σ) directly in the text
- **Full / display equations on a standalone line** - put each display equation on its own line, blank line above and below, as a standalone `$$...$$` block: `$$P(A|B) = \frac{P(B|A) P(A)}{P(B)}$$`. These are meant to be rasterised to images later - Medium, DOCX and other export surfaces do not run MathJax - so one equation per standalone line keeps each independently selectable and pasteable as an image
- **JupyterLab renders both** - inline `$f(x)=ax+b$` and the `$$...$$` display blocks render via MathJax in the live notebook
- **Escape dollar amounts in prose** - when `$` means "dollar", escape as `\$5` so MathJax does not eat everything between the two unescaped dollars
- **In repo `.md` files OUTSIDE notebooks** (READMEs, SKILL.md, docs/): workspace rule applies - escape always with `\$`, no equations expected (the rendered Markdown surfaces don't run MathJax)

## Quick glyph reference

| Need | Glyphs |
|------|--------|
| Subscripts | ᵢ ⱼ ₖ ₙ ₀ ₁ ₂ ₊ ₋ |
| Superscripts | ⁰ ¹ ² ³ ⁿ ˣ ⁺ ⁻ |
| Operators | Σ Π ∫ ∂ ∇ √ ∛ · × ÷ ⊙ ⊗ |
| Relations | ≤ ≥ ≈ ≠ ≡ ∝ → ⇒ ↦ ∈ ∉ ⊂ ∪ ∩ |
| Greek | α β γ δ ε θ λ μ σ τ φ ω Δ Σ Ω |
