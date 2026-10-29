---
name: Variance Workspace
description: A tabbed code binder for preparing and triaging Alberta variance applications.
colors:
  ink: "#1a1815"
  ink-2: "#4d4943"
  spine: "#1a1815"
  leaf: "#fbfaf6"
  leaf-2: "#eeece6"
  rule: "#cbc7bd"
  white-field: "#ffffff"
  hue-orange: "#e8691f"
  hue-yellow: "#f2c200"
  hue-grass: "#3fa34d"
  hue-teal: "#1d9f9a"
  hue-ultra: "#2b3fd1"
  hue-violet: "#7a3fd4"
  vermilion: "#c8281e"
  vermilion-text: "#b3201a"
  vermilion-tint: "#fdeceb"
  action-blue: "#1f2fb0"
  action-blue-hover: "#16227f"
  st-complete: "#14602a"
  st-complete-bg: "#e3f3e6"
  st-missing: "#8a3300"
  st-missing-bg: "#fde8d8"
  st-uncertain: "#5e4700"
  st-uncertain-bg: "#fdf3c4"
  st-professional: "#4d2194"
  st-professional-bg: "#ebe2fa"
  st-lookup: "#1c2f9e"
  st-lookup-bg: "#e1e6fb"
typography:
  display:
    fontFamily: "Hanken Grotesk, Segoe UI, Helvetica Neue, Arial, sans-serif"
    fontSize: "44px"
    fontWeight: 800
    lineHeight: 1.15
    letterSpacing: "-0.015em"
  headline:
    fontFamily: "Hanken Grotesk, Segoe UI, Helvetica Neue, Arial, sans-serif"
    fontSize: "34px"
    fontWeight: 800
    lineHeight: 1.15
    letterSpacing: "-0.015em"
  title:
    fontFamily: "Hanken Grotesk, Segoe UI, Helvetica Neue, Arial, sans-serif"
    fontSize: "22px"
    fontWeight: 700
    lineHeight: 1.15
  body:
    fontFamily: "Literata, Georgia, Iowan Old Style, Palatino Linotype, serif"
    fontSize: "17px"
    fontWeight: 400
    lineHeight: "26px"
  label:
    fontFamily: "Hanken Grotesk, Segoe UI, Helvetica Neue, Arial, sans-serif"
    fontSize: "14px"
    fontWeight: 700
    lineHeight: 1.15
  code:
    fontFamily: "JetBrains Mono, Cascadia Mono, Consolas, monospace"
    fontSize: "12.5px"
    fontWeight: 600
    lineHeight: "20px"
rounded:
  none: "0px"
  punch: "50%"
spacing:
  s1: "4px"
  s2: "8px"
  s3: "12px"
  s4: "16px"
  s5: "24px"
  s6: "32px"
  s7: "48px"
  s8: "64px"
components:
  button-primary:
    backgroundColor: "{colors.action-blue}"
    textColor: "#ffffff"
    rounded: "{rounded.none}"
    padding: "8px 18px"
    height: "44px"
    typography: "{typography.label}"
  button-primary-hover:
    backgroundColor: "{colors.action-blue-hover}"
  button-secondary:
    backgroundColor: "{colors.leaf}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "8px 18px"
    height: "44px"
  button-secondary-hover:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.leaf}"
  input:
    backgroundColor: "{colors.white-field}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "8px 12px"
    height: "44px"
  leaf:
    backgroundColor: "{colors.leaf}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "36px 48px 0"
  tab:
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    width: "82px"
    padding: "10px 4px 10px 9px"
  pill-status:
    backgroundColor: "{colors.st-complete-bg}"
    textColor: "{colors.st-complete}"
    rounded: "{rounded.none}"
    padding: "1px 8px 1px 6px"
  tag-code-badge:
    backgroundColor: "{colors.ink}"
    textColor: "#ffffff"
    rounded: "{rounded.none}"
    padding: "0 7px"
---

# Design System: Variance Workspace

## Overview

**Creative North Star: "The Tabbed Code Binder"**

The workspace is a reference binder: a near-black spine, a rail of colored index tabs down the left edge, and a milk-white leaf sitting on a board that takes the open tab's hue. The rail is map, progress meter and navigation at once; tab height grows with the work still open (84px + 9px per open item, capped at 168px). The open tab widens into the board the page rests on.

Density is calm and reading-first: bookish serif body at 17/26, plain grotesque for heads and labels, mono for article numbers and attribution codes. Everything is square, ruled in 2px ink, and flat. Motion is absent apart from a stepped spinner and the reduced-motion guard.

Product commitments that bind the look: no government, Safety Codes Council or event logos, nothing implying official status; AI output is always tagged as a draft.

**Key Characteristics:**
- Six full-strength section hues, one active at a time on the board; the rest live only on the rail.
- Milk-white leaf with 2px ink border and one short hard shadow.
- Square corners everywhere; circles only for radio marks and binder punch holes.
- Vermilion reserved for errors, blockers and the errata slip.
- Status is carried by tinted pill plus text, never color alone.

## Colors

A warm-ink and paper base with six saturated index hues; one deep blue for actions.

### Primary
- **Action Ultramarine** (#1f2fb0): primary buttons, links, focus ring, caret. Hover #16227f. Distinct from the section hue so actions never read as navigation.

### Secondary (section hues)
- **Oxide Orange** (#e8691f), **Chrome Yellow** (#f2c200), **Grass** (#3fa34d), **Teal** (#1d9f9a): tab and board fills with ink text.
- **Ultramarine Tab** (#2b3fd1), **Violet** (#7a3fd4): tab and board fills with white text.
- The board hue also fills checked radios/checkboxes, count chips, article-number chips and meter fills via `--hue`.

### Tertiary
- **Vermilion** (#c8281e; text #b3201a; tint #fdeceb): errors, blocker tags, errata slip, rejected suggestions.

### Neutral
- **Binder Ink** (#1a1815): text, borders, spine, top bar, footer.
- **Soft Ink** (#4d4943): secondary text.
- **Milk Leaf** (#fbfaf6): page surface. **Leaf Shade** (#eeece6): bars, pane heads, hover, quotes.
- **Pencil Rule** (#cbc7bd): hairline dividers. **Field White** (#ffffff): inputs and cards sitting on the leaf.

### Status pairs (text on tint)
Complete #14602a on #e3f3e6; Missing #8a3300 on #fde8d8; Uncertain #5e4700 on #fdf3c4; Needs professional #4d2194 on #ebe2fa; Lookup #1c2f9e on #e1e6fb.

### Named Rules
**The One Board Rule.** Only the open section's hue floods the board; other hues appear on rail tabs alone.
**The Vermilion Reserve Rule.** Vermilion marks errors and errata only; never decoration or a section hue.
**The Action Apart Rule.** Buttons and links use Action Ultramarine, not a section hue.

## Typography

**Display/Head Font:** Hanken Grotesk (Segoe UI, Helvetica Neue, Arial)
**Body Font:** Literata (Georgia, Iowan Old Style, Palatino Linotype)
**Label/Mono Font:** JetBrains Mono (Cascadia Mono, Consolas)

**Character:** A printed manual: a literary text face for the rules, a blunt grotesque for the apparatus, mono for citations.

### Hierarchy
- **Display** (800, 44px, 1.15): home heading only, max 18ch.
- **Headline** (800, 34px; reviewer lead 26px): page h1.
- **Title** (700, 22px): section h2; card heads 16-20px.
- **Body** (400, 17px/26px): leaf prose; lead 18/28; small 14.5/21; measure capped at 64-70ch.
- **Label** (700, 13.5-16px grotesque): field labels, buttons, pills, tabs, tags. Sentence case.
- **Code** (600, 12.5px mono, +0.04em): article numbers and code-book badges.

### Named Rules
**The Source Line Rule.** A citation is followed by its mono source line (article, page); the mono face means "verifiable".
**The Sentence Case Rule.** Labels stay sentence case; the only uppercase is short status stamps (DRAFT, errata flag).

## Layout

Binder grid: 96px rail beside a fluid board (`minmax(0,1fr)`), board padded 18px top / 28px right so the leaf sits inset with the strip line above it. Leaf padding 36px 48px (wide: 24px 28px). Pages are a main column (max 820px) plus a 260px sticky aside; map views drop the aside; the reviewer uses three panes 290 / fluid / 340 at 780px tall. Spacing follows a 4/8/12/16/24/32/48/64 scale. A sticky bottom action bar (Leaf Shade, 2px ink top rule) carries Back and the primary Next action. Designed for desktop 1280px and up; there are no narrow-width breakpoints.

## Elevation & Depth

Flat. Depth comes from ruled borders and the paper-on-board stack. The one shadow is a short hard offset on the leaf and modal edge (`4px 4px 0 #1a1815`); the errata slip carries a 2px pencil-rule offset. No blur, gradients or glass. The modal scrim is flat 72% ink.

### Named Rules
**The One Hard Edge Rule.** Only the leaf and modal get the 4px hard shadow; cards and fields stay flat.

## Shapes

Square corners (0 radius) on buttons, inputs, cards, tabs, tags and pills. Index tabs have a single clipped upper-right corner (12px chamfer); the open tab drops the clip and merges into the board. Radios are circles with a hue-filled punched center; checkboxes are squares with a tick. Two punch-hole circles (16px) mark the leaf's bound edge. Borders are 2px ink for interactive/structural objects and 1px pencil rule for dividers; a dashed 2px border marks empty or missing states.

## Components

### Buttons
- **Shape:** square, 2px ink border, 44px min height (lg 52, sm 34).
- **Primary:** Action Ultramarine fill, white text, 8px 18px.
- **Secondary:** Milk Leaf with ink border; hover inverts to ink fill.
- **Ghost:** underlined text, Leaf Shade on hover. Disabled: Leaf Shade, rule border, gray text.
- **Focus:** 3px ultramarine outline, 2px offset (white on the rail and top bar).

### Chips and status
- **Status pill:** 2px current-color border, tinted fill, icon plus text.
- **Tag:** Leaf Shade, 1px ink border, grotesque 13.5px. Blocker is vermilion fill; confirm is yellow.
- **Code badge:** ink fill, white mono; NFC, NPC, NECB use dedicated dark fills, NBC uses Action Ultramarine.
- **Draft/AI tag:** yellow, 2px ink border, marks every AI output.

### Cards / Containers
Field White, 2px ink border (2px rule when unselected, ink when on), padding 16px 24px, no radius, no shadow. Dividers are 1px rule.

### Inputs / Fields
Field White, 2px ink border, 44px high, serif 16px; focus is a 3px outline; help text is 14.5px Soft Ink. Units are mono, right-aligned inside the field.

### Navigation (signature: tab rail)
Vertical `ol` of index tabs 82px wide, 6px gap, each with number, label and open-count ("n open" or "clear"). Hover widens to 88px; current merges into the board at 98px with no clip; locked tabs are dark gray with a CSS padlock mark. Top bar: ink with brand left, save state and a segmented applicant/reviewer toggle right (2px leaf border, pressed = leaf fill).

### Errata slip
White strip, 5px vermilion top rule, slight -0.3deg tilt, vermilion text and a solid vermilion label; the single error voice.

### Tabs (segmented)
Square 2px ink group; selected = ink fill, leaf text.

## Do's and Don'ts

### Do:
- **Do** print the source line (mono article, page, quote) under every citation.
- **Do** label AI output with the yellow DRAFT/AI tag and keep humans signing.
- **Do** keep every control at 44px or taller (34px only for sm).
- **Do** pair status color with an icon and text.
- **Do** use `--hue` for fills tied to the open section and Action Ultramarine for actions.

### Don't:
- **Don't** add gradients, glass, blur or soft shadows.
- **Don't** round corners except radios and punch holes.
- **Don't** use a section hue for errors or vermilion for navigation.
- **Don't** use logos or government-like branding.
- **Don't** express completeness as a safety or approval claim.
