---
name: AgentGuard System
colors:
  surface: '#fdf8f8'
  surface-dim: '#ddd9d8'
  surface-bright: '#fdf8f8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f7f3f2'
  surface-container: '#f1edec'
  surface-container-high: '#ebe7e6'
  surface-container-highest: '#e5e2e1'
  on-surface: '#1c1b1b'
  on-surface-variant: '#444748'
  inverse-surface: '#313030'
  inverse-on-surface: '#f4f0ef'
  outline: '#747878'
  outline-variant: '#c4c7c7'
  surface-tint: '#5f5e5e'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#1c1b1b'
  on-primary-container: '#858383'
  inverse-primary: '#c8c6c5'
  secondary: '#0058be'
  on-secondary: '#ffffff'
  secondary-container: '#2170e4'
  on-secondary-container: '#fefcff'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#1c1b1a'
  on-tertiary-container: '#868382'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e5e2e1'
  primary-fixed-dim: '#c8c6c5'
  on-primary-fixed: '#1c1b1b'
  on-primary-fixed-variant: '#474746'
  secondary-fixed: '#d8e2ff'
  secondary-fixed-dim: '#adc6ff'
  on-secondary-fixed: '#001a42'
  on-secondary-fixed-variant: '#004395'
  tertiary-fixed: '#e6e2df'
  tertiary-fixed-dim: '#cac6c4'
  on-tertiary-fixed: '#1c1b1a'
  on-tertiary-fixed-variant: '#484645'
  background: '#fdf8f8'
  on-background: '#1c1b1b'
  surface-variant: '#e5e2e1'
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
    fontFamily: monospace
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
  rail-width: 64px
  sidebar-width: 240px
  gutter: 16px
  margin: 24px
  stack-compact: 8px
  stack-dense: 4px
---

## Brand & Style

This design system is built for mission-critical AI governance. The aesthetic is **Corporate Modern** with a focus on **Precision Minimalism**. It prioritizes utility and rapid information processing over decorative flourishes. The interface acts as a high-fidelity instrument panel, using subtle tonal shifts and rigid structural alignment to organize complex runtime data. 

The emotional response is one of calm, authoritative control. By using a warm off-white foundation rather than a sterile pure white, the system reduces eye strain for long-term monitoring sessions while maintaining a sophisticated, enterprise-grade atmosphere. Visual weight is communicated through thin borders and layout hierarchy rather than shadows or depth effects.

## Colors

The palette is strictly functional. The neutral foundation uses a warm off-white for the primary background to soften the interface, while dark charcoal provides high-contrast legibility for text. 

Semantic colors are the primary vehicles for communication in this system. 
- **Emerald Green (#10B981)**: Indicates 'Allow' states and healthy agent behaviors.
- **Amber (#F59E0B)**: Signals 'Review' or 'Pending' status, requiring human intervention.
- **Red (#EF4444)**: Reserved for 'Block' actions and critical security violations.
- **Blue (#3B82F6)**: Used for system-level information, evidence logs, and active navigation highlights.

## Typography

This system utilizes **Geist** for its technical precision and optimal legibility at small scales. The type scale is intentionally compact to maximize information density.

- **Headlines**: Used sparingly for page titles and major section headers.
- **Labels**: Capitalized with slight letter spacing for secondary metadata and table headers.
- **Mono**: Employed for agent logs, IDs, and raw code snippets to distinguish machine-generated content from system UI.
- **Line Heights**: Kept tight to support the dashboard's high-density layout.

## Layout & Spacing

The architecture follows a **Persistent Triple-Pane Layout** designed for rapid navigation between agent environments.

1.  **Icon Rail (64px)**: Far left. Contains high-level context switchers (Dashboard, Global Settings, User Profile).
2.  **Primary Sidebar (240px)**: Left. Contains hierarchical navigation (Guardrail sets, individual agents, filtered logs).
3.  **Main Workspace**: Fluid. Houses the core dashboard widgets and data tables.

The layout uses a **fixed-fluid hybrid model**. Sidebars are fixed to maintain tool accessibility, while the main workspace expands to utilize all remaining screen real estate. Spacing is governed by a 4px grid, emphasizing density. Margins between widgets should be 16px to maintain clear separation without wasting space.

## Elevation & Depth

This design system avoids traditional shadows in favor of **Tonal Layers and Thin Borders**.

- **Surface 0 (Background)**: `#F9F8F6` – The lowest layer.
- **Surface 1 (Cards/Widgets)**: `#FFFFFF` – Used for primary content containers to create a subtle lift against the off-white background.
- **Borders**: All containers and interactive elements use a 1px solid border (`#E5E5E1`).
- **Interactive States**: Hover states are indicated by a slight darkening of the background (e.g., `#F2F1EE`) rather than a shadow or glow.

## Shapes

The shape language is rigid and professional. A low radius of **4px to 8px** is applied to buttons and cards to provide a modern feel without sacrificing the "engineered" look of the dashboard. Smaller elements like tags and checkboxes use the smaller 4px radius, while larger workspace cards may use up to 8px.

## Components

- **Buttons**: Flat, 1px border. Primary buttons use the Charcoal background with white text. Secondary buttons use a white background with the standard gray border.
- **Status Chips**: Small, rectangular with a 2px radius. Use semantic background colors at 10% opacity with 100% opacity text of the same hue (e.g., Light Green background with Dark Green text for "Allowed").
- **Data Tables**: The core of the system. High density, 12px type, no vertical borders between columns. Rows are separated by a 1px horizontal line (`#E5E5E1`).
- **Input Fields**: Minimalist. 1px border, Geist 13px text. On focus, the border shifts to Blue (#3B82F6) with no outer glow.
- **Guardrail Widgets**: Specialized cards that feature a summary metric (e.g., "Violations Today") and a sparkline chart for temporal context.
- **Iconography**: 16px to 20px strokes. Icons should be technical and linear, using consistent 1.5px stroke weights.