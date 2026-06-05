# Design system

The web UI follows a design system derived from **Linear**.

- [`DESIGN.md`](./DESIGN.md) is the source-of-truth design spec (color tokens,
  typography, spacing, radii, component styles). AI agents and contributors
  should read it before changing the frontend so the UI stays consistent.

The tokens in `DESIGN.md` are mirrored as CSS custom properties in
[`../web/src/index.css`](../web/src/index.css) (the `:root` block). When you add
a token to one, add it to the other.

## Attribution

`DESIGN.md` is adapted from the
[VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md)
collection (`design-md/linear.app/DESIGN.md`). It is an analysis of Linear's
public marketing design system, used here purely as a styling reference.
