# Design reference report

**Source:** "MyDNA Landing Page" concept by Levi Wilson, on Dribbble, reached through a Pinterest pin. Inspired by it, not affiliated with it.

The source is a picture, not a live site, so `extract.mjs` could not run: it would have measured Pinterest or Dribbble instead. Colours were sampled from the pixels of a 736 by 552px JPEG. Downscaling softens thin text, so `--muted` and `--border-control` are less exact than the large fills.

**Status:** applied to the whole site on 2026-11-06, in `web/src/styles/tokens.css`, the only place colours are defined. `docs/DESIGN.md` holds the rules.

## Sampled

| Role | Value | Taken from |
|---|---|---|
| Page | `#eaeaea` | Area around the card |
| Surface | `#ffffff` | The card |
| Headings | `#000000` | Darkest pixel of the headline |
| Primary | `#161616` | Median of the "Scroll for more" pill |
| Body text | `#494949` | Darkest pixel of the paragraph |
| Border | `#d8d8d8` | Edge of the lower panel |
| Control outline | `#595959` | Darkest pixel of the outlined pill |
| Accent | `#805090` | The DNA art, whose common colours run from `#805090` to `#c080d0` |

## Chosen, not sampled

- `--primary-hover` `#333333` and `--primary-tint` `#f4f4f4`, needed for states the picture does not show.
- `--ai-tint` `#f3ecf6`, a light tint of the accent.
- Danger, warning and success stay as they are. Red still means emergency only.

## Not measured

Type sizes, spacing, radii, motion, hover states, other pages and a dark mode. There are no pages to visit and no pricing page. The typeface is a neo-grotesque that was not identified, and Manrope stays.

## Checks

The contrast test and axe run with these tokens in the web test suite.

## Not to copy

The DNA art, the MYDNA name and the page's words belong to their author. `docs/DESIGN.md` also bans decorative art, so without new art this look is black and white with violet on AI content only.
