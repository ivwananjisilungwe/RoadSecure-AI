# RoadSecure — Dark SOC Design System

**Version:** 1.0 · **Direction:** Dark Security Operations Center console · **Status:** Applied to `app.py`

---

## 1. Design intent

RoadSecure is a defensive cybersecurity monitoring prototype for road transport information systems. The interface has three jobs:

1. **Surface risk at a glance** — anomaly counts, severity and open alerts must be readable in under two seconds.
2. **Feel like an operator's console, not a marketing site** — dense but calm, technical but legible.
3. **Stay honest** — the UI must not imply validated accuracy or live production telemetry that the prototype does not have.

The chosen direction is a **Dark SOC console**: deep near-black navy surfaces, hairline borders, restrained cyan/teal accents, mono-spaced numerics, and a subtle technical grid. It is the natural fit for a monitoring tool and avoids the "generic admin template" look.

### Guiding principles

| Principle | Application |
|---|---|
| **Calm density** | Tight information spacing, but generous card padding and clear typographic hierarchy. |
| **Colour means something** | Accent cyan = interactive/system; green = healthy; amber = attention; red = critical. Colour is never decorative-only. |
| **Data deserves mono** | Every number, IP, score and timestamp uses `JetBrains Mono` so columns align. |
| **Depth without heaviness** | Double-bezel surfaces and inset highlights instead of dark drop shadows. |
| **Motion with intent** | Only `transform`/`opacity`, one custom easing curve, staggered entry. Reduced-motion respected. |

---

## 2. Foundations

### 2.1 Colour tokens

Three-layer architecture: **primitive → semantic → component**. All component styles reference semantic variables.

#### Primitive

| Token | Value | Role |
|---|---|---|
| `--c-ink-950` | `#04070f` | Page background |
| `--c-ink-900` | `#070c17` | Deep base |
| `--c-ink-850` | `#0a1120` | Primary surface |
| `--c-ink-800` | `#0d1628` | Raised surface |
| `--c-ink-700` | `#131f36` | Hover surface |
| `--c-slate-100` | `#eaf0fb` | Primary text |
| `--c-slate-300` | `#b6c4db` | Secondary text |
| `--c-slate-400` | `#8d9eb9` | Muted text |
| `--c-slate-500` | `#63758f` | Dim / metadata |
| `--c-cyan` | `#22d3ee` | Primary accent |
| `--c-teal` | `#2dd4bf` | Secondary accent |
| `--c-green` | `#34d399` | Healthy / normal |
| `--c-amber` | `#fbbf24` | Warning / high |
| `--c-rose` | `#fb7185` | Critical |
| `--c-red` | `#f43f5e` | Danger gauge |
| `--c-violet` | `#a78bfa` | Medium / ML |
| `--c-blue` | `#60a5fa` | Supporting |

#### Semantic

```css
--bg: var(--c-ink-950);
--surface: var(--c-ink-850);
--surface-2: var(--c-ink-800);
--line: rgba(148,163,184,.10);
--line-2: rgba(148,163,184,.18);
--text: var(--c-slate-100);
--muted: var(--c-slate-400);
--dim: var(--c-slate-500);
--accent: var(--c-cyan);
--accent-soft: rgba(34,211,238,.13);
--ok: var(--c-green);
--warn: var(--c-amber);
--danger: var(--c-rose);
```

Severity colours are intentionally distinct in both hue and label text, so status is never communicated by colour alone.

### 2.2 Typography

| Role | Family | Weights | Notes |
|---|---|---|---|
| Display / headings | **Space Grotesk** | 500, 600, 700 | `-.025em` tracking; geometric, technical character |
| Body / UI | **Plus Jakarta Sans** | 400–800 | Humanist, highly legible at 11–13px |
| Data / numerics | **JetBrains Mono** | 400, 500, 600 | All scores, counts, IPs, times, formulas |

Type scale: `9px` eyebrow/caps · `10px` table head · `11px` button/label · `12px` body-small · `14px` body · `16px` h2 · `29px` h1 · `33px` stat value.

Fonts are loaded from Google Fonts. No banned system fonts (Inter, Roboto, Arial, Helvetica) are used.

### 2.3 Spacing, radius, elevation

- Base card padding: `20px 21px`
- Grid gap: `14px` (stats) / `18px` (panels)
- Radii: `--r-sm: 10px` · `--r-md: 14px` · `--r-lg: 20px`
- "Double bezel": 1px gradient outer shell + inset inner core with `inset 0 1px 0 rgba(255,255,255,.045)` highlight. No harsh dark shadows.
- Ambient background: fixed radial glows + 46px technical grid masked by an elliptical fade. Both layers are `pointer-events:none`.

---

## 3. Layout

```
┌──────────────┬──────────────────────────────────────────────┐
│              │  TOPBAR  eyebrow + H1      live · clock      │
│  SIDEBAR     ├──────────────────────────────────────────────┤
│  250px       │                                              │
│              │  CONTENT  (stats grid / panel grids)          │
│  brand       │                                              │
│  nav         │                                              │
│  status      │                                              │
└──────────────┴──────────────────────────────────────────────┘
```

- Sidebar is fixed, glass-blurred, with a gradient hairline right border.
- Active navigation is detected from `location.pathname` in a tiny inline script — no server-side route changes.
- Main content is capped at `1620px` and padded `30px 34px`.
- Responsive: ≤1100px stats become 2 columns and grids stack; ≤780px the sidebar becomes a horizontal top rail with icon-only nav, all grids become single-column.

---

## 4. Components

| Component | Specification |
|---|---|
| **Stat card** | Icon badge tinted by tone (cyan/violet/amber/green), uppercase label, 33px mono value, trend caption, decorative SVG sparkline. |
| **Panel** | Double-bezel shell, header with 16px accent icon + title, optional right-side meta/filters, body with table or form. |
| **Data table** | Uppercase 9px tracked headers, 1px row dividers, hover tint, stacked identity cells (name + small device), mono numerals. |
| **Severity pill** | Capsule, 9.5px uppercase, leading status dot, tinted background + border. `critical / high / medium / low`. |
| **Status pill** | Quieter 10px neutral capsule for workflow state (Open / Investigating / Resolved). |
| **Buttons** | Pill-shaped, gradient accent, inset top highlight, "island" trailing icon in a nested circle. Hover lifts, active compresses. Secondary/ghost variants for non-primary actions. |
| **Filters** | Capsule tab row; active tab gets cyan border + soft fill. |
| **Form controls** | Dark translucent inputs, hairline borders, cyan focus ring (`0 0 0 3px rgba(34,211,238,.10)`), mono-friendly sizing. |
| **Check toggles** | Two-column cards; checked state revealed via `:has(input:checked)` with cyan border and fill — no JS. |
| **Risk gauge** | `conic-gradient` ring driven by `--score`, severity-coloured, with a recessed centre showing score/100. |
| **Flash message** | Green tinted toast with 0.7s rise animation. |
| **Icons** | Custom inline SVG, `stroke-width:1.5`, `currentColor`. No icon fonts or thick icon sets. |

---

## 5. Motion

- Single easing curve: `cubic-bezier(.32,.72,0,1)`.
- Entry: `rise` (opacity 0→1, translateY 14px→0) over 0.8s, staggered `.07s` per card via `:nth-child`.
- Hover: transform only (lift `translateY(-2px)`, press `scale(.98)`, nav `translateX(3px)`, nested icon `translate(2px,-1px)`).
- Status dot: expanding ring pulse over 2.4s.
- No layout-triggering animation. `@media (prefers-reduced-motion: reduce)` disables all animation and transition.

---

## 6. Accessibility

- Semantic HTML: `<nav>`, `<main>`, `<header>`, `<table>` with `<thead>/<tbody>`, real `<label>`/`<input>` pairs.
- Status conveyed by text + colour, never colour alone.
- Focus-visible cyan rings on all interactive controls.
- `lang="en"` and `color-scheme: dark` declared.
- Reduced-motion support.
- Contrast target: primary text `#eaf0fb` on `#0a1120` ≈ 15:1; muted text ≈ 6:1.

---

## 7. Screen notes

| Screen | Design treatment |
|---|---|
| **Dashboard** | Four tone-coded stat cards with sparklines; recent activity table; primary "Simulate activity" CTA with nested icon. |
| **Activity & Alerts** | Filter capsule row bound to the existing `?status=` query; dense event table with score, signals, severity and inline status update. |
| **Simulate Activity** | Two-column form/result split. Result panel shows the conic risk gauge and structured score readout; includes a "try suspicious activity" tip card. |
| **Incident Management** | Creation form + incident register; priority uses severity pills; empty state is explicit. |
| **Evaluation** | Three count cards, an honest scope notice, and numbered formula cards. Deliberately avoids any accuracy claim. |

---

## 8. Implementation & deliverables

- **Applied design:** `app.py` — `CSS` constant, inline SVG icon constants, `BASE` layout, and all five page templates. Backend routes, SQL, forms and ML logic are unchanged.
- **Design board:** `design/roadsecure-design-system.html` — self-contained visual reference with tokens, components and all five screen mockups. Open it directly in a browser; no server or dependencies required.
- **Imagery note:** AI image generation was attempted for conceptual hero artwork but the image provider returned an `Invalid credential` error, so no generated raster assets are included. The design board is vector/CSS-native and can be exported to high-resolution images with any browser screenshot tool once you want that step.

---

*RoadSecure · Academic prototype · Synthetic demonstration data only*
