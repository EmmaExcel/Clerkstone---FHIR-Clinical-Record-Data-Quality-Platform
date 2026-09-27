# Clerkstone - Accessibility (WCAG 2.2 AA Conformance Notes)

> How the front end meets WCAG 2.2 AA, and how conformance is *verified*. Accessibility is a DTAC
> usability pillar, a mandatory requirement for all NHS digital services, and a named desirable in
> the target roles. Companion documents: [DTAC_self_assessment.md](./DTAC_self_assessment.md).

## 1. Conformance target

- **Standard:** WCAG 2.2, level **AA**.
- **Design system:** NHS.UK Design System (`nhsuk-react-components` + `nhsuk-frontend`), which
  bakes in accessible components, semantic markup, and the NHS header/footer pattern.
- **Verification:** automated (`@axe-core/playwright` in CI) **plus** a manual keyboard-only pass and
  a screen-reader pass (VoiceOver on macOS; NVDA documented for Windows). Automated checks are a
  floor, not the ceiling - the manual passes catch what axe-core cannot.

## 2. Success criteria → implementation map

| WCAG 2.2 AA criterion | Implementation |
|---|---|
| **1.1.1 Non-text content** | Every chart/icon has a text alternative; severity is never colour-only (see 1.4.1); decorative icons are `aria-hidden`. |
| **1.3.1 Info and relationships** | Semantic HTML (`<header>`, `<nav>`, `<main>`, `<h1>…<h6>`, `<table>`, `<dl>` for patient summaries); form labels programmatically associated. |
| **1.3.2 Meaningful sequence** | DOM order matches visual/reading order; timeline entries are ordered lists. |
| **1.4.1 Use of colour** | **Severity is never colour-only**: error/warning/info findings use icon + text + colour together. Quality-flag badges pair a symbol with the rule text. |
| **1.4.3 Contrast (minimum)** | Text contrast ≥ 4.5:1; large text ≥ 3:1; NHS colour palette checked against its documented contrast ratios. |
| **1.4.10 Reflow** | Responsive layout down to 320 px (tested); no horizontal scroll at 400% zoom. |
| **1.4.11 Non-text contrast** | Focus indicators, chart series and badges meet 3:1. |
| **1.4.13 Content on hover/focus** | No hover-only content; tooltips are hover *and* focus dismissible. |
| **2.1.1 / 2.1.2 Keyboard** | Every interaction is keyboard-complete: search is debounced but still keyboard-navigable; findings table is fully operable without a mouse. |
| **2.4.1 Bypass blocks** | Skip-to-content link as the first focusable element. |
| **2.4.2 Page titled** | Unique, descriptive `<title>` per route (patient name, run ID). |
| **2.4.3 Focus order** | Logical tab order; focus is not lost when async results replace content. |
| **2.4.7 Focus visible** | Visible focus indicator on every interactive element (no `outline: none` without replacement). |
| **3.2.3 / 3.2.4 Consistent navigation & identification** | NHS header/footer consistent across pages; repeated components labelled identically. |
| **3.3.1 / 3.3.2 Error identification & labels/suggestions** | Form errors identified in text and programmatically; API errors surfaced as human-readable `OperationOutcome` diagnostics, not raw JSON. |
| **4.1.2 Name, Role, Value** | Native controls and NHS components with correct ARIA; `aria-live` regions on async results and on the quality-dashboard refresh. |
| **4.1.3 Status messages** | `role="status"` / `aria-live="polite"` announces "N findings loaded", "run complete", etc. |

## 3. The timeline - the accessibility-critical view

The clinical timeline is the densest screen, so it gets the most attention:

- Entries are a semantic list grouped by encounter, announced by type ("Encounter", "Observation").
- Quality-flag badges are not colour-only: each shows the rule ID in text plus an icon.
- The resource viewer's FHIRPath highlight (the "money screenshot") is **not** conveyed by colour
  alone - the highlighted element is also announced in text and reachable via the finding's link.
- Charts (severity donut, top-10 rules bar) have text equivalents and a data table alternative so a
  screen reader reaches the same numbers.

## 4. Testing

| Layer | Tool | Target |
|---|---|---|
| Automated per-page scan | `@axe-core/playwright` in CI | **Zero serious violations** |
| Manual keyboard-only pass | Playwright journey + manual | Every journey operable without a mouse |
| Screen-reader pass | VoiceOver (macOS) / NVDA (Windows) | Timeline, dashboard, finding drill-down announced sensibly |
| Colour-contrast | axe-core + NHS palette ratios | ≥ 4.5:1 text, ≥ 3:1 large/non-text |
| Responsive | Playwright at 320 px | No horizontal scroll, touch targets ≥ 44 px |

## 5. Known limitations (honest)

- Automated axe-core scans catch roughly 30-50% of WCAG issues; the manual passes are what matter,
  and they are documented here as having been performed, not merely claimed.
- No formal accessibility audit by a specialist has been conducted - this is a portfolio prototype,
  and that is stated plainly rather than implying certification.
- The `<canvas>`/chart rendering path is kept simple specifically so the same data is available as
  text/table for assistive technology.
