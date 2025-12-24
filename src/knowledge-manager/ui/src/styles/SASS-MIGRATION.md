# SASS 7-1 Architecture Migration Guide

## Overview

This document describes the SASS architecture using the industry-standard 7-1 pattern.

**Migration Status: ✅ COMPLETED**

The codebase follows the 7-1 architecture pattern, aligned with agent-host for consistent UX across all apps.

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
│   └── _main.scss          # Main content area
│
├── components/             # Reusable UI components
│   ├── _index.scss
│   ├── _navbar.scss        # Navigation bar
│   ├── _footer.scss        # Footer component
│   ├── _cards.scss         # Card components
│   ├── _buttons.scss       # Button variants
│   ├── _modals.scss        # Modal dialogs
│   └── _status.scss        # Status indicators, loaders
│
├── pages/                  # Page-specific styles
│   ├── _index.scss
│   ├── _dashboard.scss     # Dashboard page styles
│   └── _admin.scss         # Admin page styles
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
├── main.scss               # Main entry point
│
└── SASS-MIGRATION.md       # This documentation
```

## Key Features

### Design Token Alignment

All design tokens are centralized and aligned with agent-host and tools-provider:

- **Colors**: Same primary, secondary, success, danger, warning, info palette
- **Typography**: Same font family, sizes, and weights
- **Spacing**: Same 4px-based spacing scale
- **Border Radius**: Same rounded corners (4px, 8px, 12px, 18px)
- **Shadows**: Same shadow scale

### Modern SASS Syntax

- Uses `@import` for compatibility with Parcel
- Variables are defined with `!default` for easy overriding
- Proper namespacing prevents variable conflicts

### Component Consistency

All components match the patterns in tools-provider and agent-host:

- **Navbar**: Sticky top, light theme, same login/logout pattern
- **Footer**: Same three-column layout with version display
- **Cards**: Same hover effects and styling
- **Buttons**: Same border-radius and focus states
- **Modals**: Same rounded corners and shadows

### Theme Support

Dark theme is fully supported using Bootstrap's `data-bs-theme` attribute:

```html
<html lang="en" data-bs-theme="light">
```

The theme toggle button switches between light and dark modes, saving preference to localStorage.

## Usage

### Entry Point

The main entry point is `main.scss`, which imports all partials in the correct order:

1. Abstracts (variables, mixins, functions)
2. Vendors (Bootstrap)
3. Vendor overrides
4. Base (reset, typography)
5. Layout (grid, main)
6. Components
7. Pages
8. Themes
9. Utilities

### Adding New Components

1. Create a new partial in the appropriate folder (e.g., `components/_new-component.scss`)
2. Add `@forward "new-component";` to the folder's `_index.scss`
3. Add `@import "components/new-component";` to `main.scss`

### Using Variables

Variables are available throughout the codebase after the abstracts imports:

```scss
.my-component {
    color: $color-primary;
    padding: $spacing-4;
    border-radius: $border-radius-md;
    transition: all $transition-fast;
}
```

### Using Mixins

Common patterns are available as mixins:

```scss
.my-centered-element {
    @include flex-center;
}

.my-truncated-text {
    @include text-truncate;
}

.my-scrollable {
    @include custom-scrollbar;
}
```

## Build

The SCSS is compiled by Parcel during the build process:

```bash
cd ui && npm run build
```

Or via Makefile:

```bash
make build-ui
```

## Verification

After building, verify that:

1. All styles compile without errors
2. Light and dark themes work correctly
3. Navbar and footer match tools-provider styling
4. All components render properly
