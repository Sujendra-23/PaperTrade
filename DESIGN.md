---
name: PaperTrade
description: A precise graphite workspace for simulated market operations.
colors:
  bg: "#101318"
  panel: "#15191f"
  line: "#2a3038"
  text: "#e7ebef"
  muted: "#98a2af"
  green: "#9addb6"
  red: "#ee9b93"
  buy-action: "#a3ddba"
  buy-action-hover: "#bbe9cc"
  buy-action-ink: "#16251c"
  sell-action: "#edada3"
  sell-action-hover: "#f5c2b9"
  sell-action-ink: "#331d19"
  field: "#11161c"
  field-line: "#343e47"
  field-focus: "#86ac92"
  picked-field: "#1f3128"
  selected-instrument: "#20282c"
  selected-instrument-line: "#2e3b3c"
  auth-bg: "#11161b"
  auth-panel: "#1b222a"
  auth-field: "#131920"
  auth-line: "#343e48"
  chart-positive: "#93d7b0"
  chart-negative: "#ef9990"
  chart-grid: "#262c33"
  warning: "#e6c994"
  warning-bg: "#352e22"
  warning-line: "#5b5038"
typography:
  display:
    fontFamily: "\"DM Sans Variable\", sans-serif"
    fontSize: "64px"
    fontWeight: 450
    lineHeight: 1.06
    letterSpacing: "-0.04em"
  headline:
    fontFamily: "\"DM Sans Variable\", sans-serif"
    fontSize: "24px"
    fontWeight: 550
    letterSpacing: "-0.035em"
  price:
    fontFamily: "\"DM Sans Variable\", sans-serif"
    fontSize: "31px"
    fontWeight: 500
    letterSpacing: "-0.04em"
  metric:
    fontFamily: "\"DM Sans Variable\", sans-serif"
    fontSize: "23px"
    fontWeight: 500
    letterSpacing: "-0.045em"
  instrument-title:
    fontFamily: "\"DM Sans Variable\", sans-serif"
    fontSize: "16px"
    fontWeight: 600
    letterSpacing: "-0.01em"
  panel-title:
    fontFamily: "\"DM Sans Variable\", sans-serif"
    fontSize: "12px"
    fontWeight: 550
    letterSpacing: "-0.01em"
  body:
    fontFamily: "\"DM Sans Variable\", sans-serif"
    fontSize: "13px"
    fontWeight: 400
  label:
    fontFamily: "\"DM Sans Variable\", sans-serif"
    fontSize: "10px"
    fontWeight: 400
  number:
    fontFamily: "\"IBM Plex Mono\", monospace"
    fontSize: "10px"
    fontWeight: 400
  field-number:
    fontFamily: "\"IBM Plex Mono\", monospace"
    fontSize: "12px"
    fontWeight: 400
rounded:
  tag: "3px"
  control: "4px"
  field: "5px"
  panel: "7px"
  brand: "8px"
  auth-panel: "10px"
spacing:
  compact: "3px"
  icon-gap: "6px"
  label-gap: "8px"
  control-inset: "12px"
  mobile-gutter: "14px"
  grid-gap: "16px"
  panel-inset: "18px"
  section: "23px"
  auth-panel: "32px"
components:
  button-primary:
    backgroundColor: "{colors.buy-action}"
    textColor: "{colors.buy-action-ink}"
    rounded: "{rounded.field}"
    padding: "12px 15px"
    width: "100%"
  button-buy:
    backgroundColor: "{colors.buy-action}"
    textColor: "{colors.buy-action-ink}"
    rounded: "{rounded.control}"
    height: "38px"
    width: "100%"
  button-buy-hover:
    backgroundColor: "{colors.buy-action-hover}"
    textColor: "{colors.buy-action-ink}"
  button-sell:
    backgroundColor: "{colors.sell-action}"
    textColor: "{colors.sell-action-ink}"
    rounded: "{rounded.control}"
    height: "38px"
    width: "100%"
  button-sell-hover:
    backgroundColor: "{colors.sell-action-hover}"
    textColor: "{colors.sell-action-ink}"
  button-guest:
    textColor: "{colors.text}"
    rounded: "{rounded.field}"
    height: "43px"
    width: "100%"
  price-field:
    backgroundColor: "{colors.field}"
    textColor: "{colors.text}"
    typography: "{typography.field-number}"
    rounded: "{rounded.control}"
    padding: "0 12px"
    height: "39px"
  price-field-picked:
    backgroundColor: "{colors.picked-field}"
  panel:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text}"
    rounded: "{rounded.panel}"
  auth-panel:
    backgroundColor: "{colors.auth-panel}"
    textColor: "{colors.text}"
    rounded: "{rounded.auth-panel}"
    padding: "32px"
  depth-row:
    typography: "{typography.number}"
    height: "22px"
    padding: "0 12px"
    width: "100%"
  nav-item-active:
    textColor: "#e9eff2"
    height: "64px"
  status-open:
    backgroundColor: "#293b38"
    textColor: "#afd5c1"
    rounded: "{rounded.tag}"
    padding: "3px 5px"
  watch-item-selected:
    backgroundColor: "{colors.selected-instrument}"
    textColor: "{colors.text}"
    padding: "14px 16px"
    width: "100%"
---

# Design System: PaperTrade

## Overview

**Creative North Star: "Market operations console"**

The market operations console is a quiet analytical workspace: blue graphite surfaces, a restrained green/coral vocabulary, and dense, aligned numbers. Price and account figures carry the hierarchy; panel headings and chrome stay compact. The sign-in surface opens the same world with a larger, lighter headline and a simple two-column invitation.

Flat panels, fine slate borders, and small changes in surface tone separate the work. Data updates preserve their positions. Illustration, photography, and ornamental motion do not form part of the implemented system.

**Key Characteristics:**

- Graphite surfaces with semantic green and coral.
- Humanist labels paired with monospaced market detail.
- Flat, lightly rounded panels with aligned, compact data.
- Stable live updates and a visible depth-to-ticket acknowledgement.

## Colors

Blue graphite neutrals carry the screen; pale green and coral mark actions and market meaning. Frontmatter is the normative value source. The token names `bg`, `panel`, `line`, `muted`, `green`, and `red` preserve the existing CSS custom-property names; other names describe observed, repeated assignments.

### Primary

- **Practice Green** (`green`): positive values, bid prices, live dots, keyboard focus, success messages, and the picked-price border.
- **Buy Action** (`buy-action`, `buy-action-hover`, `buy-action-ink`): pale green filled buy and primary actions with dark text. The generic primary button has a slightly lighter hover (`#bdeacc`) and darker hover text (`#152c1d`) than the trading buy button.
- **Chart Green** (`chart-positive`): the positive chart trace and its fading area fill; preserve this distinct observed chart value.

### Secondary

- **Sell Coral** (`red`): ask prices, negative values, errors, and cancel hover emphasis.
- **Sell Action** (`sell-action`, `sell-action-hover`, `sell-action-ink`): filled sell action and its hover state.
- **Chart Coral** (`chart-negative`): the negative chart trace and fading area fill.

### Tertiary

- **Connection Amber** (`warning`, `warning-bg`, `warning-line`): the interruption/retry banner only. It is a state color, not a decorative accent.

### Neutral

- **Graphite Canvas** (`bg`) and **Graphite Panel** (`panel`): workspace canvas and bordered working panels.
- **Slate Divider** (`line`): shell rules, panel borders, section divisions, and table structure.
- **Cool Text** (`text`) and **Muted Slate** (`muted`): primary reading and supporting context.
- **Recessed Field** (`field`, `field-line`, `field-focus`): ticket input surface, resting border, and focus border. **Picked Field** (`picked-field`) acknowledges a depth-price selection.
- **Selected Instrument** (`selected-instrument`, `selected-instrument-line`): selected watch row, supported by a narrow green marker.
- **Auth Graphite** (`auth-bg`, `auth-panel`, `auth-field`, `auth-line`): the slightly lighter sign-in panel above its dark page and recessed fields.
- **Chart Grid** (`chart-grid`): sparse horizontal dashed chart rules.

**The Semantic Accent Rule.** Green identifies buys, positive direction, success, and focused action; coral identifies sells, negative direction, and errors. Most of the workspace remains graphite and neutral.

## Typography

**Display and Body Font:** DM Sans Variable, with sans-serif fallback; locally bundled through Fontsource.
**Number Font:** IBM Plex Mono, with monospace fallback; bundled at weights 400 and 500.

The sans is compact and approachable, while the mono keeps the dense market columns steady. The 13px root underpins a deliberately compact desktop interface; there is no invented modular type ratio.

### Hierarchy

- **Display:** the sign-in headline uses `display`, with desktop line height (1.06). It steps to 57px at 1250px, 48px at 900px, and 49px in the single-column 640px layout.
- **Headline:** workspace headings use `headline`; on phones they step to 21px. The guide heading is 26px with line height (1.3). The sign-in form title is 23px, then 22px on phones.
- **Price:** the main quoted price uses `price`, with tabular numerals; it becomes 29px on phones.
- **Metric:** account figures use `metric`, with tabular numerals; they become 26px on wide displays, 21px in the intermediate desktop layout, and return to 23px on phones.
- **Titles:** selected instrument titles use `instrument-title`; working panel headings use `panel-title`.
- **Body and labels:** `body` is the root role. Supporting text is commonly 11–12px, field and summary labels 10px, metadata 8–10px. The auth introduction is 15px with line height (1.8), stepping to 13px on phones. Guide prose is 13px with line height (1.85).
- **Numbers:** `number` is the standard compact market/table role; tape detail is 9px on desktop. `field-number` is the ticket input role. Mobile depth and tape values become 11px.

**The Number Alignment Rule.** Use IBM Plex Mono for compact trading data and tabular numerals for large account and price figures. Keep the humanist sans for labels and explanatory copy.

## Layout

The desktop shell has a 64px top bar, a 216px watchlist, and a fluid main area capped at 1920px. Main padding is 27px 25px at the top and sides. A four-column account strip sits between horizontal rules, with vertical separators between metrics. The heading, metrics, and trading content share the same left edge.

The working grid is a fluid chart, a 231px order book, and a 275px ticket with a 16px gap. The blotter spans chart and book; the trade tape sits below the ticket. Panels stretch together in the first row. Chart height is 251px. Typical panel headings are 52px tall; blotter and tape headings are 49px. Panel insets cluster around 12px, 15–18px, and 20px rather than a strict single-step scale.

- **At 1600px and above:** the book and ticket grow to 255px and 300px; chart height becomes 255px and several number roles grow slightly.
- **At 1250px and below:** the watchlist narrows to 185px. The working grid becomes a fluid chart plus a 245px ticket. Book and tape move to row two; the blotter spans row three. Book bids and asks become adjacent columns, with explicit Buy/Sell column labels, a shared spread row, and a shared legend. Main side padding becomes 20px.
- **At 900px and below:** the shell becomes one column with a 60px top bar. The watchlist becomes a horizontally scrolling instrument strip. Its search, section labels, footnote, company names, and ticker tiles are hidden. The selected marker moves from the left edge to the bottom edge. Trading content remains two columns, with a 265px ticket.
- **At 640px and below:** the main area uses 14px gutters and 21px top padding. Navigation keeps its icons and accessible text while visually suppressing text labels; the connection text and avatar are hidden. Account metrics form a two-by-two grid. Panels stack in this order: chart, ticket, order book, blotter, tape. Gaps become 14px. Chart height becomes 230px. Ticket fields and submit buttons grow to 43px; side controls grow to 36px and book rows to 25px. Tables retain their columns and scroll inside their wrapper. Footer copy stacks.

Sign-in uses a maximum 1100px two-column layout (1.25fr / 1fr), with a 130px gap and 70px vertical padding. The page has 5vw side gutters. The gap becomes 70px at 1250px and 40px at 900px. At 640px it becomes one column with a 34px gap, 22px page gutters, and 44px layout padding; the feature list is hidden and the form remains full width.

## Elevation & Depth

Depth is tonal and structural: a dark canvas, slightly lighter working surfaces, darker fields, and fine borders. The guide drawer uses a translucent near-black full-screen backdrop and a left border, with a maximum width of 440px. The chart tooltip is a compact dark rectangle with a slate border and 5px corners. Neither needs a shadow.

**The Flat Surface Rule.** Separate panels with tone and a single slate border. No box shadows are present in the shipped system.

**The Stable Market Rule.** Live updates replace values without animating the chart trace or rearranging the surrounding interface. A picked depth price is acknowledged in the ticket rather than by moving the market.

Buttons transition color and background over 150ms; the limit-price border transitions over 200ms. Loading icons rotate linearly over 1s. Reduced-motion preference disables all animations and transitions. The chart trace explicitly disables data animation. The depth-picked state lasts 900ms; it changes field color and border without translation or scaling.

## Shapes

Working panels have gently softened corners (`panel`). Trading controls use the tighter `control` radius; inputs and auth actions use `field`; small status tags use `tag`. The auth form is the roomiest container (`auth-panel`). The brand tile uses `brand`; avatars and connection dots are circular. This is a fine-border system: borders are generally 1px, active navigation and watch markers 2px. Panel overflow is clipped to the rounded perimeter, while tables get their own scrolling wrapper.

Depth bars sit behind numbers, flush to the right, with width proportional to visible liquidity. Their translucent green/coral fill is data encoding, distinct from the filled buy/sell buttons. Chart fill uses a subtle vertical fade (16% opacity to zero) beneath a thin 1.6px line.

## Components

### Buttons

Primary actions are compact, legible, and filled. The buy and sell variants use their corresponding action tokens, 38px height, full ticket width, and 11px semibold labels. On phones they become 43px and 12px. The generic primary action uses 12px semibold text, 12px 15px padding, and 5px corners; the auth instance is 43px tall. The guest action is outlined with a 43px height and a subtle raised hover surface. Cancel uses a small outlined control whose border and text become coral on hover. Icon controls use a quiet neutral hover surface.

Disabled buttons use opacity (0.55) and a waiting cursor. Keyboard focus uses a 2px green outline with 4px offset. Hover changes color or surface; there is no lift or scale.

### Inputs / Fields

Ticket quantity and limit-price fields are recessed, lightly rounded, and 39px tall, with mono values. Quantity is flanked by minus/plus buttons and a shares suffix. Price has dollar and USD prefixes/suffixes. Focus-within changes the wrapper border to the field-focus token. Phone fields become 43px. Search is a separate icon-led field with a `/` key hint and a green-toned focus border. The shortcut focuses it on desktop.

Auth fields are 43px tall, have 12px internal padding and sans text, and use the auth-field surface with an explicit label above. Their focus border becomes green. Input focus is indicated through border or wrapper treatment rather than an outer input outline. Validation and request errors remain text with error coloring; the system has no separate invented error-input variant.

### Navigation

Top navigation is a low-chrome row of icon and label pairs. Default text is muted; active text is lighter, with a 2px green underline at the bottom edge of the bar. On phones the same buttons display icons only. Blotter tabs use the same underline logic, with tiny mono count tags. Order-kind tabs use a finer 1px light underline; chart ranges use a small filled selected surface. Selection is visually distinct from hover.

### Status tags and feedback

Statuses use small 3px corners and 9px sans labels. Open and partial states have a muted teal-green background; filled has a slightly warmer green background; cancelled stays neutral. Side and status words accompany the semantic color. Order success and error feedback sits immediately below the ticket action with an icon and wrapping text. Connection interruption uses the amber bordered banner with an inline Retry action. Empty book, chart, table, and activity states retain context in quiet text rather than using illustration.

### Working panels and account strip

Chart, book, ticket, blotter, tape, and activity share the same panel surface, slate border, and 7px corners. Their internal rows and headings define density; they are not padded uniformly as generic cards. The account strip stays on the main canvas between rules, with large tabular figures above smaller explanatory text. The sign-in panel uses 32px padding, stepping to 26px at 900px and 25px at 640px.

### Watchlist instrument

Each row aligns a small ticker tile, symbol/company, and a right-aligned price/change pair. Selection adds a quiet surface, top/bottom rules, and a green edge marker. Hover uses a lighter neutral surface. The mobile version becomes a compact horizontal instrument segment and keeps the same selected context with its marker at the bottom.

### Depth-to-ticket interaction

Order-book rows are real buttons with an accessible bid/ask price name. Clicking any level copies its price into the ticket, switches the ticket to a limit order, and briefly sets the price wrapper to the picked-field surface with a green border. The price remains after the 900ms acknowledgement ends. A repeat click is acknowledged again. Choosing another instrument clears the selected-price handoff. Bid and ask choice does not change the order's buy/sell side. Market mode replaces the price field with a compact protective-collar explanation. Keep this connection explicit and visible across responsive layouts.

### Guide drawer

A right-aligned dialog covers the full height, with a dim backdrop and no shadow. It has an explicit close icon, restrained prose, a source link, and a full-width primary return action. Opening focuses the close control; Tab stays within drawer controls, Escape closes it, and closing restores focus to the guide trigger.

## Do's and Don'ts

### Do:

- **Do** reserve green and coral for order side, direction, feedback, and actionable emphasis.
- **Do** keep price, size, totals, and timestamps aligned with monospaced numerals; keep large figures tabular.
- **Do** preserve the depth-to-ticket price transfer and its brief visible acknowledgement.
- **Do** let the instrument strip and data tables scroll horizontally within their own containers.
- **Do** retain simulation context, labels, and explicit empty, connection, and order outcomes.
- **Do** suppress animations and transitions when reduced motion is requested.

### Don't:

- **Don't** add shadows to the flat panel vocabulary.
- **Don't** animate the chart trace or apply positional animation to live market updates.
- **Don't** turn the compact workspace into oversized promotional cards.
- **Don't** replace the restrained green/coral semantics with arbitrary decorative accents.
- **Don't** add an eyebrow above the sign-in headline; the implemented hierarchy starts with the headline.
