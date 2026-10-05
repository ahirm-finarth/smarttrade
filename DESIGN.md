---
name: FinArth Smart Trade
description: A trade register and inspection ledger for precise operations.
colors:
  canvas: '#f6f7f8'
  surface: '#ffffff'
  ink: '#172a32'
  muted: '#596b73'
  line: '#dde4e6'
  accent: '#12645b'
  accent-hover: '#0c4d46'
  nav: '#172e34'
  pass: '#176343'
  pass-bg: '#e9f4ed'
  refer: '#815213'
  refer-bg: '#fff2dc'
  block: '#a33138'
  block-bg: '#fcecef'
  demo-ink: '#765016'
  demo-bg: '#fff6e6'
  focus: '#278a7b'
  neutral-label: '#edf1f2'
  nav-text: '#d3e0e0'
  nav-muted: '#b9cbcb'
  nav-line: '#395157'
  nav-hover: '#28464b'
  secondary-hover: '#edf3f2'
  table-heading: '#f9fafb'
  row-hover: '#f3f8f6'
  tab-hover: '#f5f8f7'
  skeleton: '#e6ecee'
  product-tone: '#1f6c60'
  product-tone-1: '#579082'
  product-tone-2: '#98b6ad'
  product-tone-3: '#bbceca'
typography:
  display:
    fontFamily: Arial, Helvetica, sans-serif
    fontSize: 30px
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: -0.025em
  headline:
    fontFamily: Arial, Helvetica, sans-serif
    fontSize: 18px
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: -0.015em
  title:
    fontFamily: Arial, Helvetica, sans-serif
    fontSize: 16px
    fontWeight: 600
    lineHeight: 1.55
  body:
    fontFamily: Arial, Helvetica, sans-serif
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: Arial, Helvetica, sans-serif
    fontSize: 12px
    fontWeight: 600
    lineHeight: 1.55
  record:
    fontFamily: Arial, Helvetica, sans-serif
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.55
  column-label:
    fontFamily: Arial, Helvetica, sans-serif
    fontSize: 11px
    fontWeight: 500
    lineHeight: 1.55
  outcome-label:
    fontFamily: Arial, Helvetica, sans-serif
    fontSize: 11px
    fontWeight: 600
    lineHeight: 1.55
  tab-label:
    fontFamily: Arial, Helvetica, sans-serif
    fontSize: 12px
    fontWeight: 500
    lineHeight: 1.55
rounded:
  label: 4px
  control: 6px
  surface: 12px
spacing:
  tight: 8px
  control-gap: 10px
  compact: 12px
  record: 18px
  mobile-gutter: 20px
  surface: 24px
  panel: 28px
  desktop-gutter: 38px
components:
  button-primary:
    backgroundColor: '{colors.accent}'
    textColor: '{colors.surface}'
    typography: '{typography.label}'
    rounded: '{rounded.control}'
    padding: 9px 14px
  button-primary-hover:
    backgroundColor: '{colors.accent-hover}'
  button-secondary:
    backgroundColor: '{colors.surface}'
    textColor: '{colors.ink}'
    typography: '{typography.label}'
    rounded: '{rounded.control}'
    padding: 9px 14px
  button-secondary-hover:
    backgroundColor: '{colors.secondary-hover}'
  search-field:
    backgroundColor: '{colors.surface}'
    textColor: '{colors.ink}'
    typography: '{typography.record}'
    rounded: '{rounded.control}'
    padding: 0 12px
  nav-link:
    backgroundColor: transparent
    textColor: '{colors.nav-text}'
    rounded: '{rounded.control}'
    padding: 12px
  nav-link-hover:
    backgroundColor: '{colors.nav-hover}'
    textColor: '{colors.surface}'
  outcome-pass:
    backgroundColor: '{colors.pass-bg}'
    textColor: '{colors.pass}'
    typography: '{typography.outcome-label}'
    rounded: '{rounded.label}'
    padding: 3px 8px
  outcome-refer:
    backgroundColor: '{colors.refer-bg}'
    textColor: '{colors.refer}'
    rounded: '{rounded.label}'
    padding: 3px 8px
    typography: '{typography.outcome-label}'
  outcome-block:
    backgroundColor: '{colors.block-bg}'
    textColor: '{colors.block}'
    rounded: '{rounded.label}'
    padding: 3px 8px
    typography: '{typography.outcome-label}'
  outcome-neutral:
    backgroundColor: '{colors.neutral-label}'
    textColor: '{colors.muted}'
    rounded: '{rounded.label}'
    padding: 3px 8px
    typography: '{typography.outcome-label}'
  register:
    backgroundColor: '{colors.surface}'
    textColor: '{colors.ink}'
    rounded: '{rounded.surface}'
  workspace-tab:
    backgroundColor: transparent
    textColor: '{colors.muted}'
    typography: '{typography.tab-label}'
    padding: 18px 12px 16px
  workspace-tab-selected:
    backgroundColor: transparent
    textColor: '{colors.accent}'
---

# Design System: FinArth Smart Trade

## Overview

**Creative North Star: "Trade register and inspection ledger"**

The trade register and inspection ledger is the visual anchor: aligned entries, exact monetary values, quiet rules, and clear section labels. Deep teal navigation frames white working surfaces on a pale neutral canvas. The interface feels precise, calm, and familiar to operations staff.

Density follows the task. Tables keep comparison compact while headings, filters, and metadata have enough space to orient the reader. Color identifies controls and supplied reference states; text labels carry their meaning. The implemented world uses a system sans-serif and flat surfaces so the records remain the strongest visual signal.

**Key Characteristics:**

- Aligned records and tabular financial numerals.
- Restrained teal actions and navigation.
- Flat white surfaces with fine neutral borders.
- Compact rectangular labels with explicit text.
- Visible keyboard focus and responsive record containment.

## Colors

A deep teal primary accent sits within cool neutral surfaces; muted green, amber, and red identify supplied reference states.

### Primary

- **Operations Teal** (`accent`): action backgrounds, selected tabs, caret, and field focus. **Deep Operations Teal** (`accent-hover`) darkens primary-button hover.
- **Navigation Teal** (`nav`): the persistent application frame; `nav-hover`, `nav-text`, `nav-muted`, and `nav-line` handle its local hierarchy.
- **Product Teals** (`product-tone` through `product-tone-3`): the four observed distribution fills. These identify product segments rather than outcomes.

### Secondary

- **Reference Green** (`pass`, `pass-bg`), **Reference Amber** (`refer`, `refer-bg`), and **Reference Red** (`block`, `block-bg`): paired text and background treatments for outcome labels. The same foreground colors appear on their dashboard values.
- **Demo Amber** (`demo-ink`, `demo-bg`): the synthetic-data indicator, separate from outcome labels.

### Neutral

- **Cool Canvas** (`canvas`) and **White Record** (`surface`): page ground and working surfaces.
- **Ledger Ink** (`ink`) and **Quiet Slate** (`muted`): primary content and secondary labels.
- **Fine Rule** (`line`): borders and dividers; `table-heading` distinguishes column labels.
- **Neutral Label** (`neutral-label`): missing outcomes, counts, and tab counts.
- `secondary-hover`, `row-hover`, and `tab-hover` provide the implemented quiet interaction fills; `skeleton` marks static loading placeholders.
- **Focus Teal** (`focus`): the shared keyboard outline.

**The Reference State Rule.** Outcome colors always accompany explicit PASS, REFER, BLOCK, or missing-value text. They do not turn supplied references into calculated decisions.

## Typography

**Display and Body Font:** Arial, Helvetica, sans-serif. The familiar system stack is intentional for this operations interface and needs no remote font.

### Hierarchy

- **Display:** desktop page headings; the frontmatter carries the shared heading definition. Dashboard headings reduce to (26px) on mobile. Case identifiers use (27px) on desktop and (20px) on mobile, retaining tabular numerals.
- **Headline:** section headings.
- **Title:** subsection and empty-state headings.
- **Body:** general prose and case fact values.
- **Label:** button text; **Tab Label:** selectable workspace tabs.
- **Record:** table cells, input text, metadata, and supporting copy. Register cells use (11px), monetary values (12px), and secondary record lines (10px).
- **Column Label:** table headers; **Outcome Label:** compact state tags.

Supporting section copy is bounded at (70ch); empty-state copy at (60ch); state-page explanations at (65ch). Uppercase is reserved for the small phase marker, with (0.1em) tracking.

**The Ledger Alignment Rule.** Right-align comparable monetary columns and use tabular numerals. Keep identifiers and monetary strings intact where the source permits.

## Layout

The desktop shell uses a fixed navigation rail (218px), a topbar (66px), and content gutters (38px), with a content maximum width (1600px). Page content starts at (34px) and increases to (42px) on wide screens at the (1600px) breakpoint.

At widths up to (1100px), the rail narrows to (185px) and gutters to (26px). At widths up to (760px), navigation becomes a top strip, the topbar becomes (54px), gutters become (20px), and the rail offset disappears. Dashboard metrics move from four columns to two. Filters stack; case facts move to two columns and overview content to one.

Record tables scroll inside their containers. The case register keeps a minimum table width (1050px). Tabs also scroll horizontally. Shared record cells use (18px) padding, reduced to (16px) on mobile; headers use (12px 18px), then (12px 16px). Large working surfaces use their existing contextual padding: register headings (24px), product panels (22px 26px), workspace panels (28px), and mobile panels (22px 20px).

## Elevation & Depth

Depth comes from the dark navigation frame, white working surfaces, fine borders, and pale state fills. There are no box shadows. Hover changes color without shifting the layout. Static skeletons use a neutral fill rather than animation.

**The Flat Surface Rule.** Use borders, background changes, and spacing to establish hierarchy; the current system has no box shadows.

## Shapes

The repeated silhouette is a restrained rectangle: compact labels use the `label` radius, interactive controls the `control` radius, and large bordered surfaces the `surface` radius. The synthetic-data indicator uses a small (5px) corner; tab counts use (3px). Dividers and container outlines are single-pixel rules. Tabs use a (2px) bottom rule for selection.

## Components

### Buttons

Confident, compact rectangular controls. Primary buttons use Operations Teal with white text; secondary buttons use white surfaces, Ledger Ink, and Fine Rule borders. Both share (38px) minimum height on desktop and (44px) on mobile. Hover follows the frontmatter variants with a background-color transition (160ms ease-out). Disabled buttons use opacity (0.65) and a waiting cursor. Keyboard focus is a (3px) Focus Teal outline offset by (4px).

### Inputs / Fields

Quiet white fields with a single Fine Rule border and the control radius. The search field contains a small inline icon and a transparent input. Its wrapper owns a (2px) Operations Teal focus outline offset by (2px); the inner input has no separate outline. Native selects use (39px) desktop height and share the mobile minimum target (44px). Search placeholder text uses Quiet Slate.

### Navigation

A deep teal frame with muted light text, compact icons, and roomy links. Links lighten on hover against Navigation Hover. The shell has no additional active-link visual treatment. On mobile, navigation becomes horizontal and the secondary register shortcut is hidden. Workspace tabs use Quiet Slate at rest, a pale fill on hover, and teal text plus a bottom rule when selected. Their keyboard focus outline is inset (4px); arrow keys, Home, and End move among tabs.

### Chips

Outcome labels are informational, not controls. Small rectangular tinted backgrounds hold explicit state text; the neutral variant says "Not supplied" for missing outcomes. The case header uses a larger version (12px type; 5px 12px padding). Count labels stay neutral and sit beside their section or tab names.

### Cards / Containers

Large register, metric, product, and workspace surfaces use white backgrounds, Fine Rule outlines, and the surface radius. Borders and internal spacing supply structure. Register and workspace containers clip their outer corners while the table or tab strip owns horizontal scrolling.

### Record Tables

The signature pattern is an aligned inventory with pale column headings and fine row rules. Monetary columns use tabular numerals and right alignment. Register rows receive a pale hover fill; the case identifier remains the explicit link and gains an underline on link hover. Missing records use a centered explanatory empty state rather than a blank panel.

## Do's and Don'ts

### Do:

- **Do** reuse the extracted colors, system font, and three recurring corner sizes.
- **Do** keep money aligned and preserve tabular numerals.
- **Do** keep wide record tables and tabs inside horizontally scrollable containers.
- **Do** pair outcome colors with text and retain visible keyboard focus.
- **Do** use the existing reduced-motion behavior and static loading skeletons.

### Don't:

- **Don't** replace the quiet record hierarchy with decorative effects or shadows.
- **Don't** use outcome color alone to communicate a record state.
- **Don't** shrink record text below the established scale to force a wide table onto mobile.
- **Don't** add a remote font dependency to this system-font interface.
