---
name: AgentGuard Tracer
colors:
  surface: '#f9f9f9'
  surface-dim: '#dadada'
  surface-bright: '#f9f9f9'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f3f3'
  surface-container: '#f1edec'
  surface-container-high: '#e8e8e8'
  surface-container-highest: '#e2e2e2'
  on-surface: '#1b1b1b'
  on-surface-variant: '#4c4546'
  inverse-surface: '#303030'
  inverse-on-surface: '#f1f1f1'
  outline: '#7e7576'
  outline-variant: '#c4c7c7'
  surface-tint: '#5e5e5e'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#1b1b1b'
  on-primary-container: '#848484'
  inverse-primary: '#c6c6c6'
  secondary: '#085ac0'
  on-secondary: '#ffffff'
  secondary-container: '#5b94fd'
  on-secondary-container: '#002c66'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#1b1b1b'
  on-tertiary-container: '#848484'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e2e2e2'
  primary-fixed-dim: '#c6c6c6'
  on-primary-fixed: '#1b1b1b'
  on-primary-fixed-variant: '#474747'
  secondary-fixed: '#d8e2ff'
  secondary-fixed-dim: '#adc6ff'
  on-secondary-fixed: '#001a42'
  on-secondary-fixed-variant: '#004395'
  tertiary-fixed: '#e2e2e2'
  tertiary-fixed-dim: '#c6c6c6'
  on-tertiary-fixed: '#1b1b1b'
  on-tertiary-fixed-variant: '#474747'
  background: '#f9f9f9'
  on-background: '#1b1b1b'
  surface-variant: '#e2e2e2'
  success-green: '#166534'
  success-bg: '#dcfce7'
  warning-yellow: '#854d0e'
  warning-bg: '#fef9c3'
  error-red: '#ba1a1a'
  error-bg: '#ffdad6'
typography:
  headline-lg:
    fontFamily: Geist
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Geist
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-md:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Geist
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  label-md:
    fontFamily: Geist
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  label-sm:
    fontFamily: Geist
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
  mono:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  sidebar-width: 240px
  rail-width: 64px
  margin: 24px
  gutter: 16px
  stack-compact: 8px
  stack-dense: 4px
---

## Brand & Style

AgentGuard Tracer is a technical governance platform designed for AI engineers and security administrators. The brand personality is **Technical, Authoritative, and Precise**. 

The design style follows a **Corporate / Modern** aesthetic with a lean toward **Minimalist Developer Tools**. It prioritizes information density and clarity over decorative elements. The UI uses a strict hierarchical structure to convey stability and control, utilizing a neutral foundation with sharp, intentional pops of "Action Blue" to guide the user's focus through complex data sets.

## Colors

The palette is built on a high-contrast foundation to ensure legibility in data-heavy environments. 

- **Primary (#000000):** Used for navigation backgrounds and core text to establish a strong structural frame.
- **Secondary (#0058be):** An authoritative blue used for primary actions, active states, and links.
- **Neutral/Surface:** A range of warm grays (`#fdf8f8` to `#e5e2e1`) separates the navigation, header, and content areas without relying on heavy borders.
- **Semantic Colors:** Critical for state communication. "Allowed" actions use emerald greens; "Blocked" actions use the system error red; "Approval Required" uses a cautionary amber. These should always include a background tint and a high-contrast text foreground for accessibility.

## Typography

The system uses **Geist** as the primary typeface, chosen for its technical precision and readability at small sizes. 

- **Headlines:** Use a semi-bold weight (600) with slight negative letter-spacing to maintain a compact, professional feel.
- **Body & Labels:** Stick to a 13px or 14px base. Labels utilize a heavier weight and increased letter-spacing for uppercase or small-cap contexts to distinguish them from interactive text.
- **Monospaced:** Essential for IDs, timestamps, and code-like "Action Paths." Use **JetBrains Mono** or a clean system mono to ensure character distinction (e.g., 0 vs O).

## Layout & Spacing

The layout utilizes a **Fixed Sidebar + Fluid Content** model. 

- **Navigation:** A permanent 240px sidebar on desktop provides top-level context.
- **Hierarchy:** The main canvas is wrapped in a 24px margin. Within the canvas, a vertical stack of 16px (gutter) separates the filter bar, the data table, and pagination.
- **Density:** Inside components like tables or list items, use "dense" spacing (4px to 8px) to maximize the information visible on a single screen without scrolling.
- **Breakpoints:** On mobile, the sidebar should collapse into a hamburger menu or bottom navigation bar, and the 24px margin should reduce to 16px.

## Elevation & Depth

This system avoids heavy drop shadows, opting instead for **Tonal Layering** and **Thin Outlines**.

- **Level 0 (Background):** The base layer uses the `surface` color (#fdf8f8).
- **Level 1 (Containers):** Tables and search cards use `surface-container-lowest` (#ffffff) with a 1px border in `outline-variant` (#c4c7c7).
- **Level 2 (Interaction):** Hover states on table rows use `surface-container-low` to provide immediate feedback without lifting the element off the page. 
- **Active State:** Navigation items use a 2px vertical border-end in the secondary color to indicate the active page, maintaining a flat but clear hierarchy.

## Shapes

The shape language is **Soft and Functional**. 

Standard components (buttons, input fields, cards) use a 4px (0.25rem) corner radius. This provides a modern feel while remaining professional and "boxed," fitting the technical nature of a trace explorer. Tags and status chips may use a slightly higher radius (up to 6px) to distinguish them as discrete metadata units, but never full pills unless used for specific "user" avatars.

## Components

- **Buttons:** Primary buttons are solid `secondary` blue with white text. Secondary buttons are outlined or use a `surface-container` fill.
- **Chips (Status):** Status indicators must use semantic coloring (e.g., Green for Allowed) with an background opacity of ~15-20% and 100% opacity for the border and text.
- **Data Tables:** Use a sticky header with a `surface-container` background. Rows should feature a transition on hover and include a "hidden-until-hover" action (like a "Details" button) to reduce visual noise.
- **Input Fields:** Search bars should include a leading icon and a subtle border that transforms to a 2px blue outline on focus.
- **Navigation Links:** Use a generous 8px-12px vertical padding. Active states should be high-contrast (Secondary color font + Background tint).