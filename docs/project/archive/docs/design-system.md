# Movie Ranking Frontend - Design System

## Design Tokens

### Colors

```css
:root {
  /* Primary - Deep Blue (trust, reliability) */
  --color-primary-50: #eff6ff;
  --color-primary-100: #dbeafe;
  --color-primary-500: #3b82f6;
  --color-primary-600: #2563eb;
  --color-primary-700: #1d4ed8;

  /* Neutral - Slate Gray */
  --color-neutral-50: #f8fafc;
  --color-neutral-100: #f1f5f9;
  --color-neutral-200: #e2e8f0;
  --color-neutral-300: #cbd5e1;
  --color-neutral-400: #94a3b8;
  --color-neutral-500: #64748b;
  --color-neutral-600: #475569;
  --color-neutral-700: #334155;
  --color-neutral-800: #1e293b;
  --color-neutral-900: #0f172a;

  /* Semantic Colors */
  --color-success: #22c55e;
  --color-warning: #f59e0b;
  --color-error: #ef4444;

  /* Star Rating - Gold */
  --color-star-filled: #fbbf24;
  --color-star-empty: #d1d5db;

  /* Background */
  --color-bg-primary: #ffffff;
  --color-bg-secondary: #f8fafc;
  --color-bg-tertiary: #f1f5f9;
}
```

### Typography

```css
:root {
  /* Font Family */
  --font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;

  /* Font Sizes */
  --text-xs: 0.75rem;    /* 12px */
  --text-sm: 0.875rem;   /* 14px */
  --text-base: 1rem;     /* 16px */
  --text-lg: 1.125rem;   /* 18px */
  --text-xl: 1.25rem;    /* 20px */
  --text-2xl: 1.5rem;    /* 24px */
  --text-3xl: 1.875rem;  /* 30px */

  /* Font Weights */
  --font-normal: 400;
  --font-medium: 500;
  --font-semibold: 600;
  --font-bold: 700;

  /* Line Heights */
  --leading-tight: 1.25;
  --leading-normal: 1.5;
  --leading-relaxed: 1.625;
}
```

### Spacing

```css
:root {
  --space-1: 0.25rem;   /* 4px */
  --space-2: 0.5rem;    /* 8px */
  --space-3: 0.75rem;   /* 12px */
  --space-4: 1rem;      /* 16px */
  --space-5: 1.25rem;   /* 20px */
  --space-6: 1.5rem;    /* 24px */
  --space-8: 2rem;      /* 32px */
  --space-10: 2.5rem;   /* 40px */
  --space-12: 3rem;     /* 48px */
  --space-16: 4rem;     /* 64px */
}
```

### Border Radius

```css
:root {
  --radius-sm: 0.25rem;  /* 4px */
  --radius-md: 0.375rem; /* 6px */
  --radius-lg: 0.5rem;   /* 8px */
  --radius-xl: 0.75rem;  /* 12px */
  --radius-full: 9999px;
}
```

### Shadows

```css
:root {
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);
}
```

### Breakpoints

```css
/* Mobile first approach */
/* sm: 640px */
/* md: 768px */
/* lg: 1024px */
/* xl: 1280px */
```

---

## Component Specifications

### 1. Button Component

**Variants:** primary, secondary, ghost
**Sizes:** sm, md, lg
**States:** default, hover, active, disabled, loading

```
Props:
- variant: 'primary' | 'secondary' | 'ghost'
- size: 'sm' | 'md' | 'lg'
- disabled: boolean
- loading: boolean
- fullWidth: boolean
- type: 'button' | 'submit'
- onClick: () => void
- children: ReactNode
```

**Specifications:**

| Size | Height | Padding X | Font Size |
|------|--------|-----------|-----------|
| sm   | 32px   | 12px      | 14px      |
| md   | 40px   | 16px      | 14px      |
| lg   | 48px   | 24px      | 16px      |

**Primary Button:**
- Background: var(--color-primary-600)
- Text: white
- Hover: var(--color-primary-700)
- Active: var(--color-primary-800)
- Disabled: opacity 0.5, cursor not-allowed

**Secondary Button:**
- Background: transparent
- Border: 1px solid var(--color-neutral-300)
- Text: var(--color-neutral-700)
- Hover: var(--color-neutral-50) background

**Loading State:**
- Show spinner icon
- Text changes to "Loading..."
- Disabled interaction

---

### 2. Input Component

**Types:** text, email, password
**States:** default, focus, error, disabled

```
Props:
- type: 'text' | 'email' | 'password'
- label: string
- placeholder: string
- value: string
- onChange: (value: string) => void
- error: string | null
- disabled: boolean
- required: boolean
```

**Specifications:**
- Height: 44px (touch-friendly)
- Padding: 12px 16px
- Border: 1px solid var(--color-neutral-300)
- Border Radius: var(--radius-lg)
- Font Size: 16px (prevents zoom on iOS)

**States:**
- Focus: border-color var(--color-primary-500), ring 2px var(--color-primary-100)
- Error: border-color var(--color-error), error message below in red
- Disabled: background var(--color-neutral-100), cursor not-allowed

**Label:**
- Font Size: 14px
- Font Weight: 500
- Margin Bottom: 6px
- Color: var(--color-neutral-700)

**Error Message:**
- Font Size: 12px
- Color: var(--color-error)
- Margin Top: 4px

---

### 3. Star Rating Component

**Usage:** Display and input for 1-5 star ratings

```
Props:
- value: number (1-5)
- onChange?: (value: number) => void
- readonly: boolean
- size: 'sm' | 'md' | 'lg'
```

**Specifications:**

| Size | Star Size | Gap |
|------|-----------|-----|
| sm   | 16px      | 2px |
| md   | 24px      | 4px |
| lg   | 32px      | 6px |

**Behavior:**
- Filled stars: var(--color-star-filled)
- Empty stars: var(--color-star-empty)
- Interactive: hover shows preview, click confirms
- Readonly: no hover effects, no cursor pointer
- Keyboard: arrow keys to navigate, enter to select

**Accessibility:**
- role="radiogroup"
- Each star: role="radio", aria-checked
- aria-label="Rating: X out of 5 stars"

---

### 4. Card Component

**Usage:** Container for movie rankings in list

```
Props:
- children: ReactNode
- padding: 'sm' | 'md' | 'lg'
```

**Specifications:**
- Background: var(--color-bg-primary)
- Border: 1px solid var(--color-neutral-200)
- Border Radius: var(--radius-xl)
- Shadow: var(--shadow-sm)
- Padding: var(--space-4) for md

**Hover (if interactive):**
- Shadow: var(--shadow-md)
- Transform: translateY(-1px)
- Transition: 150ms ease

---

### 5. Movie Ranking Card

**Usage:** Display a single ranking in the list

**Layout:**
```
┌─────────────────────────────────────┐
│  Movie Title                    ★★★★☆│
│  Year: 2024                         │
│  Rated on: Jan 10, 2024             │
└─────────────────────────────────────┘
```

**Specifications:**
- Title: var(--text-lg), var(--font-semibold), var(--color-neutral-900)
- Year: var(--text-sm), var(--color-neutral-500)
- Date: var(--text-xs), var(--color-neutral-400)
- Stars: aligned right on desktop, below title on mobile

**Responsive:**
- Mobile: Stack vertically, stars below title
- Desktop: Flex row, title left, stars right

---

### 6. Empty State Component

**Usage:** When user has no rankings

```
Props:
- title: string
- description: string
- action?: { label: string, onClick: () => void }
```

**Layout:**
```
      [Icon]

   No movies ranked yet

   Start by adding a movie and
   giving it a rating.

   [Add Your First Movie]
```

**Specifications:**
- Icon: 48px, var(--color-neutral-300)
- Title: var(--text-xl), var(--font-semibold)
- Description: var(--text-base), var(--color-neutral-500)
- Centered, max-width 300px
- Padding: var(--space-12) vertical

---

### 7. Header/Navigation

**Layout:**
```
┌─────────────────────────────────────┐
│  Movie Ranking           [Logout]   │
└─────────────────────────────────────┘
```

**Specifications:**
- Height: 64px
- Background: var(--color-bg-primary)
- Border Bottom: 1px solid var(--color-neutral-200)
- Logo: var(--text-xl), var(--font-bold)
- Padding: 0 var(--space-4)

**Mobile:**
- Same layout, hamburger menu if needed (MVP: just logout)

---

### 8. Form Container

**Usage:** Wrapper for auth forms

**Layout:**
```
┌─────────────────────────────────────┐
│                                     │
│         Movie Ranking               │
│                                     │
│    ┌─────────────────────────┐      │
│    │      Login Form         │      │
│    │                         │      │
│    │   [Email]               │      │
│    │   [Password]            │      │
│    │                         │      │
│    │   [Login Button]        │      │
│    │                         │      │
│    │   Don't have an account?│      │
│    │   Register              │      │
│    └─────────────────────────┘      │
│                                     │
└─────────────────────────────────────┘
```

**Specifications:**
- Centered vertically and horizontally
- Form card: max-width 400px
- Background: var(--color-bg-primary)
- Padding: var(--space-8)
- Border Radius: var(--radius-xl)
- Shadow: var(--shadow-lg)

---

### 9. Modal Component

**Usage:** Add movie dialog

```
Props:
- isOpen: boolean
- onClose: () => void
- title: string
- children: ReactNode
```

**Specifications:**
- Backdrop: rgba(0, 0, 0, 0.5)
- Modal: max-width 480px, centered
- Background: var(--color-bg-primary)
- Border Radius: var(--radius-xl)
- Padding: var(--space-6)
- Header: title + close button
- Animation: fade in + scale up (150ms)

**Accessibility:**
- Focus trap inside modal
- Escape to close
- aria-modal="true"
- Return focus on close

---

### 10. Alert/Toast Component

**Usage:** Success/error feedback messages

```
Props:
- type: 'success' | 'error' | 'info'
- message: string
- onDismiss?: () => void
```

**Specifications:**
- Position: top center, fixed
- Min Width: 300px
- Padding: var(--space-4)
- Border Radius: var(--radius-lg)
- Auto dismiss: 5 seconds

**Colors:**
- Success: green background tint, green border
- Error: red background tint, red border
- Info: blue background tint, blue border

---

## Page Layouts

### Auth Pages (Login/Register)

```
┌──────────────────────────────────────────┐
│                                          │
│                                          │
│           ┌──────────────────┐           │
│           │   Logo/Title     │           │
│           │                  │           │
│           │   Form Fields    │           │
│           │                  │           │
│           │   Submit Button  │           │
│           │                  │           │
│           │   Link to other  │           │
│           └──────────────────┘           │
│                                          │
│                                          │
└──────────────────────────────────────────┘
```

- Full viewport height
- Centered content
- Background: var(--color-bg-secondary)

### Rankings Page

**Desktop:**
```
┌──────────────────────────────────────────┐
│  Header                        [Logout]  │
├──────────────────────────────────────────┤
│                                          │
│  My Rankings                 [Add Movie] │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │  Movie Title              ★★★★☆    │  │
│  │  2024                              │  │
│  └────────────────────────────────────┘  │
│  ┌────────────────────────────────────┐  │
│  │  Another Movie            ★★★★★    │  │
│  │  2023                              │  │
│  └────────────────────────────────────┘  │
│                                          │
│           [Load More]                    │
│                                          │
└──────────────────────────────────────────┘
```

**Mobile:**
```
┌─────────────────────┐
│ Movie Ranking    [=]│
├─────────────────────┤
│                     │
│ My Rankings         │
│ [+ Add Movie]       │
│                     │
│ ┌─────────────────┐ │
│ │ Movie Title     │ │
│ │ 2024            │ │
│ │ ★★★★☆           │ │
│ └─────────────────┘ │
│                     │
│ ┌─────────────────┐ │
│ │ Another Movie   │ │
│ │ 2023            │ │
│ │ ★★★★★           │ │
│ └─────────────────┘ │
│                     │
│ [Load More]         │
│                     │
└─────────────────────┘
```

---

## Interaction States

### Loading States

1. **Button Loading:** Spinner + "Loading..." text
2. **Page Loading:** Centered spinner
3. **List Loading:** Skeleton cards (3 items)
4. **Form Submitting:** Disabled inputs + button loading

### Error States

1. **Field Error:** Red border + error message below
2. **Form Error:** Alert banner above form
3. **API Error:** Toast notification
4. **Page Error:** Full page error with retry button

### Success States

1. **Form Submit:** Green toast notification
2. **Action Complete:** Brief success message

---

## Animations

Keep animations minimal for performance:

1. **Page Transitions:** None (instant)
2. **Modal:** Fade in (150ms)
3. **Toast:** Slide down + fade (200ms)
4. **Button Hover:** Background transition (150ms)
5. **Card Hover:** Shadow + lift (150ms)

---

## Accessibility Checklist

- [ ] All interactive elements keyboard accessible
- [ ] Focus visible on all focusable elements
- [ ] Color contrast minimum 4.5:1
- [ ] Form labels properly associated
- [ ] Error messages announced to screen readers
- [ ] Skip link for keyboard users
- [ ] Semantic HTML throughout
- [ ] ARIA labels where needed
