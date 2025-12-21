# SASS 7-1 Architecture Migration Guide

## Overview

This document describes the migration from the flat SASS structure to the industry-standard 7-1 pattern architecture.

**Migration Status: ✅ COMPLETED**

The codebase has been fully migrated to the 7-1 architecture pattern. Legacy files have been removed.

## Directory Structure

```
src/styles/
├── abstracts/              # Design tokens, mixins, functions
│   ├── _index.scss         # @forward all abstracts
│   ├── _variables.scss     # Color, typography, spacing tokens
│   ├── _mixins.scss        # Reusable style patterns
│   └── _functions.scss     # SASS utility functions
│
├── base/                   # Reset and typography
│   ├── _index.scss
│   ├── _reset.scss         # CSS reset, box-sizing
│   └── _typography.scss    # Base typography styles
│
├── layout/                 # Structural layout
│   ├── _index.scss
│   ├── _grid.scss          # Flexbox utilities, containers
│   ├── _header.scss        # App header styles
│   ├── _sidebar.scss       # Sidebar/navigation
│   └── _main.scss          # Main content area
│
├── components/             # Reusable UI components
│   ├── _index.scss
│   ├── _messages.scss      # Chat message bubbles
│   ├── _input.scss         # Input area, forms
│   ├── _modals.scss        # Modal dialogs
│   ├── _buttons.scss       # Button variants
│   ├── _cards.scss         # Card components
│   ├── _definitions.scss   # Definition lists
│   ├── _header.scss        # Header component styles
│   └── _sidebar.scss       # Sidebar component styles
│
├── widgets/                # Interactive widget styles
│   ├── _index.scss
│   ├── _base.scss          # Common widget patterns
│   ├── _text-display.scss  # Text/markdown display
│   ├── _multiple-choice.scss
│   ├── _free-text.scss
│   ├── _slider.scss
│   ├── _rating.scss
│   ├── _progress.scss
│   ├── _timer.scss
│   └── _code-editor.scss
│
├── pages/                  # Page-specific styles
│   ├── _index.scss
│   ├── _admin.scss         # /admin management UI
│   └── _canvas.scss        # /canvas flow editor
│
├── themes/                 # Theming
│   ├── _index.scss
│   └── _dark.scss          # Dark mode overrides
│
├── vendors/                # Third-party overrides
│   ├── _index.scss
│   └── _bootstrap-overrides.scss
│
├── utilities/              # Utility classes
│   ├── _index.scss
│   ├── _animations.scss    # Keyframes and animation classes
│   ├── _helpers.scss       # Display, spacing, text utilities
│   └── _responsive.scss    # Breakpoint utilities
│
├── main.scss               # Main chat interface entry point
├── admin.scss              # Admin interface entry point
├── canvas.scss             # Canvas/flow editor entry point
│
└── SASS-MIGRATION.md       # This documentation
```

## Migration History (Completed)

The following steps were completed during the migration:

### ✅ Step 1: Created 7-1 Directory Structure

All directories created with proper `_index.scss` files.

### ✅ Step 2: Migrated Styles to Modular Files

All styles were refactored into appropriate module files following the 7-1 pattern.

### ✅ Step 3: Updated Entry Points

Templates now reference the proper entry points:

- `_head.jinja` → `main.scss`
- `admin.jinja` → `admin.scss`

### ✅ Step 4: Removed Legacy Files

Removed all deprecated flat-structure files:

- `_variables.scss`, `_base.scss`, `_layout.scss`, `_animations.scss`, `_responsive.scss`
- Old `main.scss` and `admin.scss` entry points

### ✅ Step 5: Verified Build

Build compiles successfully with:

```bash
npm run build
```

## Key Improvements

### Modern SASS Syntax

- Uses `@use` and `@forward` instead of deprecated `@import`
- Proper namespacing prevents variable conflicts
- Better tree-shaking support

### Design Tokens

All design values are centralized in `abstracts/_variables.scss`:

```scss
// Colors
$color-primary: #0d6efd;
$color-primary-dark: #0b5ed7;

// Spacing
$spacing-1: 0.25rem;  // 4px
$spacing-4: 1rem;     // 16px

// Typography
$font-size-sm: 0.875rem;  // 14px
$font-size-base: 1rem;    // 16px
```

### Reusable Mixins

Common patterns in `abstracts/_mixins.scss`:

```scss
@mixin flex-center {
    display: flex;
    align-items: center;
    justify-content: center;
}

@mixin widget-option {
    display: flex;
    align-items: center;
    gap: $spacing-3;
    padding: $spacing-3 $spacing-4;
    // ... more styles
}
```

### Widget Styles

Each widget has its own file in `widgets/`:

- Styles are scoped to the custom element tag (`ax-slider`, `ax-rating`, etc.)
- Common patterns use `_base.scss` mixins
- Easy to find and modify widget-specific styles

## Adding New Widget Styles

1. Create `widgets/_new-widget.scss`:

   ```scss
   @use '../abstracts' as *;

   ax-new-widget {
       display: block;
       // Widget-specific styles
   }
   ```

2. Add to `widgets/_index.scss`:

   ```scss
   @forward 'new-widget';
   ```

3. Add to entry points if needed

## Responsive Design

Use the mixins from `abstracts/_mixins.scss`:

```scss
.my-component {
    padding: $spacing-4;

    @include respond-to('md') {
        padding: $spacing-6;
    }

    @include respond-to('lg') {
        padding: $spacing-8;
    }
}
```

## Dark Mode

Dark mode is handled via CSS custom properties in `themes/_dark.scss`:

```scss
[data-bs-theme="dark"] {
    --color-bg-primary: #1a1a2e;
    --color-text-primary: #e8e8e8;
    // ...
}
```

Components use these variables for automatic dark mode support.

---

**Status:** Migration files created, ready for entry point switch.
**Date:** 2024
**Phase:** 5A.1 Complete
