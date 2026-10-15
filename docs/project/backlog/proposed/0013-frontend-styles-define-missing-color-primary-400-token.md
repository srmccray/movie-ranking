---
id: '0013'
title: 'frontend/src/styles/variables.css: define the missing --color-primary-400 token'
status: Proposed
governing_adrs:
- ADR-0002
governing_prds:
- PRD-0006
governing_stories:
- US-0007
dependencies: []
target_bc: frontend
priority: P2
---

# TASK-0013: frontend/src/styles/variables.css: define the missing --color-primary-400 token

## Summary
`frontend/src/styles/pages/analytics-charts.css` uses `var(--color-primary-400)` twice, but `variables.css` defines only the 50, 100, 200, 500, 600 and 700 steps of the primary scale. The browser drops the invalid declaration, so those chart elements silently render in the default fill/color. Define the token.

Priority: P2. Size: XS. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- Uses: `frontend/src/styles/pages/analytics-charts.css:65` (`fill: var(--color-primary-400);`) and `:96` (`color: var(--color-primary-400);`). Inspect both rules to see which chart elements they style before choosing the value.
- Definitions: `frontend/src/styles/variables.css:11-16` (`--color-primary-50: rgba(168, 85, 247, 0.08)`, `-100`, `-200`, `--color-primary-500: #a855f7`, `-600: #9333ea`, `-700: #7e22ce`). These are the Tailwind purple 500/600/700 values, so add `--color-primary-400: #c084fc;` (Tailwind purple-400) between `-200` and `-500`.
- Run `grep -rhn "var(--[a-z0-9-]*)" frontend/src/styles | grep -o "\-\-[a-z0-9-]*" | sort -u` and compare against the definitions in `variables.css` to confirm no other token is undefined; if any is, add it in the same PR.

## Notes and Risks
- Contrast: `#c084fc` on the dark chart background is lighter than `-500`; check the activity chart still reads well in a browser (`/run` or `npm run dev`) and attach a before/after screenshot to the PR.
- Broader token and contrast work belongs to the UI refresh wave and is out of scope here.

## Definition of Done
- [ ] `--color-primary-400` is defined in `frontend/src/styles/variables.css`.
- [ ] No `var(--...)` used under `frontend/src/styles` refers to an undefined custom property (shown by the grep in the blueprint).
- [ ] The analytics chart elements styled at `analytics-charts.css:65` and `:96` render with the new color in a browser.
- [ ] `cd frontend && npm run build` exits 0.

```gherkin
Scenario: The analytics chart uses a defined primary shade
  Given --color-primary-400 is defined in variables.css
  When Casey opens the Analytics page
  Then the elements styled with var(--color-primary-400) have a computed fill/color of rgb(192, 132, 252)
```

## INVEST Criteria
- **Independent**: No task dependencies; executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Fixes a real, silent styling bug in the analytics charts; PRD-0006, US-0007.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Extra small: a handful of lines in one or two files.
- **Testable**: A computed-style check in the browser (Playwright `toHaveCSS` or devtools) observes the rendered color; no internals involved.
