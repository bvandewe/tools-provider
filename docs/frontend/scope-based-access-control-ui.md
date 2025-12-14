# Frontend Changes for Scope-Based Access Control

This document outlines the UI changes needed in agent-host frontend to support the new scope-based access control feature implemented in tools-provider.

## 1. Source Registration UI (Admin)

**New field in source registration form:**

- Add `required_scopes` input (tag/chip input or comma-separated list)
- Label: "Required Scopes (optional)"
- Help text: "Scopes required for ALL tools from this source. Overrides auto-discovered scopes."
- Example placeholder: `orders:read, orders:write`

**API change:**

```typescript
// POST /api/sources request body
{
  name: string;
  url: string;
  // ... existing fields ...
  required_scopes?: string[];  // NEW
}
```

---

## 2. Tool Details Display

**Show scope requirements on tool cards/details:**

- Display `required_scopes` from `tool.execution_profile.required_scopes`
- Visual indicator (e.g., 🔒 icon) if scopes are required
- Tooltip showing: "Requires scopes: orders:read, orders:write"

**Optional enhancement:**

- Compare user's scopes (from JWT) with tool's required scopes
- Show warning badge if user lacks required scopes

---

## 3. Error Handling for 403 Insufficient Scope

**When tool execution returns 403 with `insufficient_scope`:**

```typescript
// Error response structure
{
  error: "insufficient_scope",
  error_description: "Missing required scope(s): orders:write",
  required_scopes: ["orders:read", "orders:write"],
  missing_scopes: ["orders:write"]
}
```

**UI treatment:**

- Show clear error message in chat: "You don't have permission to use this tool."
- Display missing scopes: "Missing scope: `orders:write`"
- Suggest action: "Contact your administrator to request access."
- Use warning/amber color (not red error) since it's authorization, not a failure

---

## 4. User Scope Display (Optional)

**In user profile dropdown or settings:**

- Show user's current scopes from token
- Parse from `scope` claim in JWT (space-separated)
- Display as tags/chips

---

## 5. Source Details View (Admin)

**Show configured scopes on source detail page:**

- Display `required_scopes` if set
- Show "Auto-discovered" vs "Admin override" indicator
- Allow editing scopes via PATCH `/api/sources/{id}`

---

## Summary Table

| Component | Change | Priority |
|-----------|--------|----------|
| Source Registration Form | Add `required_scopes` input | High |
| Tool Card/Details | Display required scopes | Medium |
| Chat Error Handler | Handle `insufficient_scope` 403 | High |
| Source Details (Admin) | Show/edit scopes | Medium |
| User Profile | Display user's scopes | Low |

---

## Files to Modify

| Path (likely) | Change |
|---------------|--------|
| `ui/src/components/SourceForm.js` | Add required_scopes field |
| `ui/src/components/ToolCard.js` | Display scope badges |
| `ui/src/services/api.js` | Update source registration payload |
| `ui/src/components/ChatMessage.js` | Handle scope error display |
| `ui/src/utils/errorHandler.js` | Parse insufficient_scope errors |

---

## Related Backend Documentation

- [Scope-Based Access Control Architecture](../architecture/scope-based-access-control.md)
- [Upstream Service Integration Spec](../specs/upstream-service-integration-spec.md)
- [Source Registration](../implementation/source-registration.md)
