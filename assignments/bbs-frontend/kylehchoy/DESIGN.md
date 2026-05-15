# Design System — thenetwork

The single source of truth for every visual decision in this project.
Read this before writing CSS, before adding a component, before choosing a font
size or a color. If you find yourself reaching for a value not in this file,
either it belongs here, or you do not need it.

---

## 1. Product Context

- **What this is:** *thenetwork*. A bulletin-board-style online directory for
  University of Austin (UATX) students. Built on top of the A2 FastAPI backend
  (posts, threads, reactions, FTS, profiles, identity via `X-Username`).
- **Who it's for:** UATX undergrads. Intellectually serious by self-selection.
  Reads books; writes; argues. Will notice if the typography is generic.
- **Space/positioning:** A counter-text to the modern engagement-engine social
  network. UATX is positioned as the anti-Harvard; the product is a structural
  and verbal homage to 2004 thefacebook.com (which started as a Harvard
  directory) reskinned in UATX brand DNA. The footer states the thesis
  directly: *"An online directory. Not a feed."*
- **Memorable thing:** A 2004 college directory, made for serious people, at a
  serious school, with proper typography. Two layers run in parallel: the
  *shape* says Facebook 2004 (masthead bar, lowercase wordmark, two-column,
  Wall / Poke / "is online" / `my profile | my friends | my privacy | logout`).
  The *paint* says UATX (cream + gold + black, Newsreader + Antonio, editorial
  restraint).
- **Approved direction:** Variant C "The Almanac" — see
  `~/.gstack/projects/SoftwareEngineering/designs/wall-feed-20260515/variant-C.html`
  for the locked reference.

## 2. Aesthetic Direction

- **Direction:** Editorial / classical with structural homage to early-2000s
  college BBS. Magazine-quality restraint applied to a directory-era layout.
- **Decoration level:** Minimal. Hairlines only. No shadows, no blurs, no
  gradients, no decorative blobs, no card-lift. The only ornament is a 1px
  hairline rule and the gold masthead bar.
- **Mood:** "*The New Criterion* runs a Wall." Bookish, refined, deliberate.
- **Reference:**
  `~/.gstack/projects/SoftwareEngineering/designs/wall-feed-20260515/variant-C.html`
  (locked May 15, 2026).
- **Anti-patterns (never ship these):** purple/violet gradients, blue accent
  of any kind, drop shadows on cards, rounded corners larger than 2px, Inter
  as body font, `system-ui` as display font, 3-column SaaS feature grid,
  generic stock-photo hero, Tailwind default neutral palette.

## 3. Typography

**Two fonts only. No third font. No display font.** Newsreader carries
content; Antonio carries chrome.

- **Body / post content / headlines:** **Newsreader**
  - Google Fonts, variable, optical-size axis 6..72
  - Weights loaded: 400, 500, 600; italic 400, 500
  - Why: humanist transitional serif optimized for screens. The optical-size
    axis means it holds up from 14px metadata to 32px headings without
    looking thin or precious. Free analog to UATX's actual `GT Super` (which
    is Grilli Type, paid).
- **Chrome / wordmark / eyebrow labels / nav / section headers / sidebar
  labels:** **Antonio**
  - Google Fonts, weights 400, 500, 600
  - Why: tall, narrow, condensed sans-serif. Used uppercase + tracked, it
    is the visible signal "this is a UATX product." Free analog to UATX's
    actual `GT America Condensed` (also Grilli Type, also paid).
- **Loading:** Single `<link>` in `index.html` to Google Fonts (no
  self-hosting for v1; revisit if bundle weight matters):
  ```html
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Antonio:wght@400;500;600&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400;1,6..72,500&display=swap" rel="stylesheet">
  ```

### Type scale (rem, 16px base)

| Token       | rem    | px  | Use                                         |
|-------------|--------|-----|---------------------------------------------|
| `--t-xs`    | 0.625  | 10  | Antonio tracked uppercase — footer / dense  |
| `--t-sm`    | 0.6875 | 11  | Antonio tracked uppercase — eyebrows, nav   |
| `--t-base`  | 0.875  | 14  | Newsreader sidebar body, italic tagline     |
| `--t-md`    | 1.0625 | 17  | Newsreader post body (default reading size) |
| `--t-lg`    | 1.5    | 24  | Antonio wordmark, page titles               |
| `--t-xl`    | 2.0    | 32  | Newsreader stat numerals                    |
| `--t-2xl`   | 2.5    | 40  | Reserved — page-level hero (rare)           |

Antonio tracking: `letter-spacing: 0.14em–0.20em`, `text-transform: uppercase`.
Newsreader body: `line-height: 1.55`. Sidebar names: `font-variant: small-caps`.

## 4. Color

**One accent. Cream paper, antique gold, true black. No blue anywhere.**

| Token            | Hex       | Use                                                |
|------------------|-----------|----------------------------------------------------|
| `--cream`        | `#F7F7F1` | Page background (NOT white)                        |
| `--white`        | `#FFFFFF` | Inline surfaces (compose box only, if at all)      |
| `--gold`         | `#B89A5F` | Masthead, accent, active state, links on hover     |
| `--gold-light`   | `#C2A86F` | Reserved — secondary chrome if needed (rare)       |
| `--gold-tint`    | `#EEE6D0` | Reserved — sparse use, e.g. compose-box tint       |
| `--black`        | `#000000` | Body type, headlines                               |
| `--muted`        | `#717480` | Eyebrow labels, footer text, sidebar sub-text      |
| `--hairline`     | `#DDDDDD` | The ONLY divider — never a shadow                  |

**Dark mode:** Not v1. If shipped later, redesign palette top-down (warm
near-black `#0F0E0C` body, cream `#E8E0D0` text, brighter gold `#D4B070`).
Do not auto-invert.

**Why these values:** Pulled from `uaustin.org` brand kit (`#B89A5F` is the
exact UATX gold). Cream `#F7F7F1` matches UATX's page background. The gold is
muted antique brass, not yellow and not orange — that distinction matters.

## 5. Spacing

**8pt grid. Comfortable density. Generous gutters.**

| Token       | px   | Use                                              |
|-------------|------|--------------------------------------------------|
| `--s-2xs`   | 4    | Hairline padding, dot indicators                 |
| `--s-xs`    | 8    | Inline gaps in eyebrows                          |
| `--s-sm`    | 12   | Compose-row gaps, tight cards                    |
| `--s-md`    | 16   | Default block padding                            |
| `--s-lg`    | 24   | Page padding, sidebar inter-section              |
| `--s-xl`    | 32   | Vertical spacing between Wall posts              |
| `--s-2xl`   | 48   | Main column ↔ sidebar gutter, page top padding   |
| `--s-3xl`   | 64   | Page bottom padding, hero spacing                |

## 6. Layout

- **Page wrap:** centered on cream, `max-width: 860px`.
- **Two-column main:** content column `580px`, sidebar `200px`, gutter `48px`.
- **Reading column ≤ 580px:** typographic optimum at 17px serif body. Do not
  widen.
- **Masthead:** `40px` tall, gold full-bleed, lowercase Antonio wordmark
  flush-left, uppercase-tracked Antonio nav flush-right (`my profile | my
  friends | my privacy | logout`).
- **Tagline strip:** Newsreader italic, centered, beneath masthead, separated
  by hairline above and below.
- **Wall posts:** no boxes, no backgrounds. Hairline `#DDDDDD` between posts.
  Antonio eyebrow line (tracked uppercase) → Newsreader 17px/1.55 body →
  Antonio footer line (tracked uppercase, gray) with reactions.
- **Sidebar:** typographic, no boxes. Antonio uppercase tracked section
  headers with `border-bottom: 1px solid var(--gold)`; content beneath in
  Newsreader (large numerals at 32px; usernames in small-caps).
- **Footer:** Newsreader italic on cream, with one Antonio uppercase span for
  the thesis line.
- **Border radius:** `≤ 2px` anywhere. No pill buttons. No "card" radii.
- **Borders:** `1px solid` only. No 2px, no 4px, no double borders.
- **Mobile breakpoints:** `< 760px` collapses to single column with sidebar
  below content. `< 480px` reduces page padding to `16px` and base type to
  16px. Test at `320px` width before shipping.

## 7. Motion

**Minimal-functional. ~250ms max. No scroll-driven, no parallax.**

| Token              | Value                  | Use                                       |
|--------------------|------------------------|-------------------------------------------|
| `--m-fast`         | 150ms ease-out         | Hover states, focus rings                 |
| `--m-base`         | 200ms ease-out         | Optimistic post insertion (fade + 4px up) |
| `--m-slow`         | 250ms ease-out         | Polled reply arrival (slide-in from left) |

Polled reply arrival is the ONE "delight" moment in the entire app. Every
other state change is instantaneous or 150ms fade.

## 8. Vocabulary (verbal layer of the Facebook 2004 homage)

These terms are part of the brand. Use them in UI copy, not generic
alternatives:

| Use this        | Not this              |
|-----------------|-----------------------|
| Wall            | Feed                  |
| Post to the Wall | Compose / Tweet / Share |
| Poke            | (a low-stakes ping)   |
| is online       | active / online now   |
| my profile      | profile               |
| my friends      | following / followers |
| my privacy      | settings / preferences |
| logout          | sign out              |
| Network         | Community / Followers |
| Notes           | Comments              |

**Compose placeholder:** `Dare to think. Dare to post.` (UATX's voice
"Dare to think. Dare to build." adapted for the surface.)

**Footer thesis (every page):** *"A UATX Student Production. An online
directory. Not a feed."*

## 9. Decisions Log

| Date       | Decision                                                 | Rationale                                                                                    |
|------------|----------------------------------------------------------|----------------------------------------------------------------------------------------------|
| 2026-05-15 | Locked Variant C "The Almanac" from /design-shotgun      | Editorial restraint with hairlines-only treatment matched UATX brand register best.          |
| 2026-05-15 | Compose placeholder = "Dare to think. Dare to post."     | Lifts UATX's actual voice ("Dare to think. Dare to build.") into the most-visible surface.   |
| 2026-05-15 | Newsreader + Antonio instead of GT Super + GT America    | Free / OFL-licensed analogs of UATX's paid Grilli Type stack; same register, zero cost.      |
| 2026-05-15 | No third font; sidebar uses small-caps Newsreader        | Two fonts already cover serif content + tracked sans chrome; a third would muddy the system. |
| 2026-05-15 | No blue, no Facebook blue, anywhere                      | The gold-on-cream IS the brand differentiator. Any blue muddies the UATX-vs-Harvard riff.    |
| 2026-05-15 | Reading column capped at 580px                           | 17px serif body at 580px gives ~70-character line length — the typographic reading optimum.  |
| 2026-05-15 | Hairlines only between posts; no boxes                   | Boxes would push the design toward "card-based SaaS." Hairlines preserve the editorial mood. |
| 2026-05-15 | Footer thesis printed on every page                      | Teaches the design's argument to viewers who never open the README.                          |
