# Luxurious Brutalism × Tech-Noir
## CSS Design System Specification

**Purpose**
A constrained, high-signal UI system for dashboards, portfolios, and internal tools.
Optimized for readability, hierarchy, and state awareness—not decoration.

This system prioritizes:
- Constraint over flair
- Structure over ornament
- Luminance and contrast over shadows
- Density without chaos

---

## 1. Design Principles

### 1.1 Constraint-as-Status
Every visual decision implies intentional limitation.
Nothing is decorative unless it conveys state, hierarchy, or affordance.

### 1.2 Grid Is Semantic
Grids represent *systems*, not layout convenience.
Columns should map to meaning (primary system vs satellites).

### 1.3 Motion Is Feedback
Animation exists only to confirm state change.
No decorative animation.

### 1.4 Accent Is Earned
Hazard yellow is reserved for:
- Active optimization
- Status transitions
- Critical callouts

If yellow is everywhere, the system is lying.

---

## 2. Color System

### 2.1 CSS Variables

```css
:root {
  /* Core Backgrounds */
  --bg-core: #050505;
  --bg-surface: #0F0F0F;
  --bg-surface-2: #1A1A1A;

  /* Typography */
  --text-primary: #FFFFFF;
  --text-secondary: #888888;
  --text-meta: #555555;

  /* Accents */
  --accent-yellow: #F4D35E;
  --accent-alert: #FF3333;

  /* Borders */
  --border-light: rgba(255, 255, 255, 0.08);
  --border-active: rgba(255, 255, 255, 0.2);
}
````

### 2.2 Usage Rules

* Borders define structure
* Luminance defines depth
* No drop shadows
* No gradients except for depth simulation

---

## 3. Typography System

### 3.1 Font Stack

**Primary (UI / Headings / Body)**

* Inter
* Helvetica Now
* Satoshi
* system-ui fallback

**Secondary (Meta / Data / Terminal)**

* JetBrains Mono
* Space Mono
* IBM Plex Mono

---

### 3.2 Typography Tokens

```css
body {
  font-family: 'Inter', system-ui, sans-serif;
  background: var(--bg-core);
  color: var(--text-primary);
}

h1, h2, h3 {
  letter-spacing: -0.04em;
  font-feature-settings: "ss01", "ss04";
  text-rendering: geometricPrecision;
}

.meta {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--text-meta);
  font-variant-numeric: tabular-nums;
}
```

```
## 4. Layout System

### 4.1 Parametric Grid

Used for dashboards, project overviews, system panels.

```css
.grid-container {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: 1px;
  background-color: var(--border-light);
  border: 1px solid var(--border-light);
}

.grid-item {
  background-color: var(--bg-core);
  padding: 2rem;
}
```

**Guideline**

* Left column = primary system
* Right columns = metrics / satellites

---

### 4.2 Vertical Rhythm Lines

```css
.vertical-divider {
  border-right: 1px solid var(--border-light);
}
```

Use sparingly to imply longitudinal structure (timelines, pipelines).

---

## 5. Surface Components

### 5.1 Base Card

```css
.card {
  background: linear-gradient(
    180deg,
    #0F0F0F 0%,
    #0A0A0A 100%
  );
  border: 1px solid var(--border-light);
  padding: 1.5rem;
}
```

---

### 5.2 Interactive Card (Hover Feedback Only)

```css
.card:hover {
  transform: translateY(-1px);
  border-color: var(--border-active);
  transition:
    transform 120ms ease-out,
    border-color 120ms linear;
}
```

No easing beyond 150ms.
Anything slower feels ornamental.

---

## 6. Accent Components

### 6.1 Yellow “Terminal” Card

Reserved for:

* Status: Optimized
* Key skills
* Critical system wins

```css
.card-accent {
  background-color: var(--accent-yellow);
  color: var(--bg-core);
  padding: 2rem;
  border-radius: 4px;
  font-family: 'JetBrains Mono', monospace;
}

.card-accent h3 {
  font-family: 'Inter', sans-serif;
  letter-spacing: -0.03em;
  font-weight: 600;
}
```

---

## 7. Navigation & Overlays

### 7.1 Glass Navigation Bar

```css
.nav-bar {
  background: rgba(5, 5, 5, 0.7);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border-light);
}
```

Navigation floats above content without visual dominance.

---

## 8. Imagery Treatment

### 8.1 Desaturated Default State

```css
.image-muted {
  filter: grayscale(100%) contrast(120%);
  transition: all 0.5s ease;
}
```

### 8.2 Reveal on Interaction

```css
.image-muted:hover {
  filter: grayscale(0%) contrast(100%);
}
```

---

### 8.3 Architectural Masking (Arch Shape)

```css
.image-arch {
  border-radius: 500px 500px 0 0;
}
```

Used sparingly for hero imagery only.

---

## 9. Motion Guidelines

Allowed:

* opacity
* transform
* border-color

Forbidden:

* bounce
* elastic
* looping animation

Motion exists to confirm state—not entertain.

---

## 10. Accessibility Notes

* Contrast ratios exceed WCAG AA by default
* Yellow accent must never contain small text
* Meta text should not be used for primary actions

---

## 11. Intended Use Cases

* Infrastructure dashboards
* CI/CD pipelines
* Personal portfolio (technical roles only)
* Internal tools
* Observability surfaces

This system is **not** intended for:

* Marketing sites
* Lifestyle brands
* Content-heavy blogs

---

## 12. Philosophy Recap

This design system should feel like:

* an instrument panel
* a blueprint
* a system that expects failure and measures it

If it feels pretty, something is wrong.
If it feels calm and precise, it’s working.
