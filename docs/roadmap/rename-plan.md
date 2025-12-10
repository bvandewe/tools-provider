# Project Rename Plan: tools-provider → agent-gateway

**Status:** `PLANNED`
**Date:** December 10, 2025
**Target Name:** `agent-gateway`

---

## Overview

This document outlines the plan to rename the project from `tools-provider` to `agent-gateway` across the entire codebase.

### Name Variants to Replace

| Current | New | Usage |
|---------|-----|-------|
| `tools-provider` | `agent-gateway` | Directory names, URLs, kebab-case |
| `tools_provider` | `agent_gateway` | Python imports, snake_case |
| `ToolsProvider` | `AgentGateway` | Class names, PascalCase |
| `TOOLS_PROVIDER` | `AGENT_GATEWAY` | Environment variables, UPPER_CASE |

---

## Scope Analysis

### Files Requiring Changes

#### Category 1: Directory/File Renames (Critical Path)

| Current Path | New Path | Notes |
|--------------|----------|-------|
| `src/tools-provider/` | `src/agent-gateway/` | Main app directory |
| `tools-provider.code-workspace` | `agent-gateway.code-workspace` | VS Code workspace |
| `docs/specs/tools-provider.md` | `docs/specs/agent-gateway.md` | Spec document |
| `deployment/keycloak/tools-provider-realm-export.json` | `deployment/keycloak/agent-gateway-realm-export.json` | Keycloak config |

#### Category 2: Configuration Files (High Impact)

| File | Changes Required |
|------|------------------|
| `mkdocs.yml` | Site name, URLs |
| `docker-compose.yml` | Service names, container names, labels |
| `pyproject.toml` (root) | Project name |
| `src/tools-provider/pyproject.toml` | Package name |
| `src/tools-provider/Makefile` | References |
| `Makefile` (root) | References |
| `.github/copilot-instructions.md` | All references |
| `pyrightconfig.json` | Paths |

#### Category 3: Python Source Files

| File | Type of Change |
|------|----------------|
| `src/tools-provider/application/settings.py` | App name, service name |
| `src/tools-provider/observability/metrics.py` | Metric prefixes |
| `src/tools-provider/application/events/domain/*.py` | Logger names |
| `src/agent-host/application/settings.py` | `tools_provider_url` → `agent_gateway_url` |
| `src/agent-host/application/services/tool_provider_client.py` | Class rename, file rename |
| `src/agent-host/api/controllers/*.py` | References |
| `src/agent-host/main.py` | Import paths |
| `src/upstream-sample/app/main.py` | References |
| `src/upstream-sample/app/auth/dependencies.py` | References |

#### Category 4: Documentation Files (26 files)

```
docs/index.md
docs/README.md
docs/architecture/read-model-reconciliation.md
docs/architecture/system-integration.md
docs/frontend/session-lifecycle.md
docs/implementation/overview.md
docs/implementation/source-registration.md
docs/roadmap/proactive-agent-implementation-plan.md
docs/roadmap/proactive-agent-roadmap.md
docs/security/keycloak-token-exchange-setup.md
docs/security/session-management.md
docs/specs/agent-host-lld.md
docs/specs/agent-host-plan.md
docs/specs/design-review.md
docs/specs/implementation-plan.md
docs/specs/integration.md
docs/specs/pattern-mapping.md
docs/specs/proactive-agent.md
docs/specs/tools-provider.md → agent-gateway.md
docs/troubleshooting/circuit-breaker.md
docs/troubleshooting/token-exchange-case-study.md
README.md
CHANGELOG.md
```

#### Category 5: VS Code / IDE Configuration

| File | Changes |
|------|---------|
| `tools-provider.code-workspace` | Rename file + update all internal references |
| `.vscode/settings.json` | Path references |
| `.vscode.sample/settings.json` | Path references |

#### Category 6: Scripts

| File | Changes |
|------|---------|
| `scripts/get_token.sh` | References |
| `scripts/test_token_exchange.py` | References |
| `scripts/rename_project.py` | Update (or use to execute rename) |
| `deployment/keycloak/configure-master-realm.sh` | Realm name references |

#### Category 7: Generated/Build Files (Rebuild Required)

| Directory | Action |
|-----------|--------|
| `site/` | Regenerate with `mkdocs build` |
| `src/tools-provider/static/` | Rebuild UI with `make build-ui` |
| `src/tools-provider/ui/src/tmp_build/` | Auto-regenerates |
| `*.dist-info` directories | Reinstall packages |

---

## Execution Plan

### Phase 1: Preparation (15 min)

- [ ] Create feature branch: `git checkout -b rename/agent-gateway`
- [ ] Backup current state: `git stash` any uncommitted changes
- [ ] Verify all tests pass before rename

### Phase 2: Directory Renames (10 min)

```bash
# Order matters - do these first
mv src/tools-provider src/agent-gateway
mv tools-provider.code-workspace agent-gateway.code-workspace
mv docs/specs/tools-provider.md docs/specs/agent-gateway.md
mv deployment/keycloak/tools-provider-realm-export.json deployment/keycloak/agent-gateway-realm-export.json
```

### Phase 3: Global Find & Replace (30 min)

Execute in order:

| Step | Find | Replace | Scope |
|------|------|---------|-------|
| 1 | `tools-provider` | `agent-gateway` | All files |
| 2 | `tools_provider` | `agent_gateway` | All files |
| 3 | `ToolsProvider` | `AgentGateway` | All files |
| 4 | `TOOLS_PROVIDER` | `AGENT_GATEWAY` | All files |
| 5 | `🔧 tools-provider` | `🔧 agent-gateway` | Workspace file |

### Phase 4: File-Specific Updates (20 min)

#### 4.1 agent-host Client Rename

```bash
# Rename file
mv src/agent-host/application/services/tool_provider_client.py \
   src/agent-host/application/services/agent_gateway_client.py

# Update class name inside:
# ToolProviderClient → AgentGatewayClient
```

#### 4.2 Settings Updates

**`src/agent-gateway/application/settings.py`:**

```python
# Update app_name and any hardcoded references
app_name: str = Field(default="agent-gateway")
```

**`src/agent-host/application/settings.py`:**

```python
# Rename field
agent_gateway_url: str = Field(default="http://localhost:8000")
# Was: tools_provider_url
```

#### 4.3 Docker Compose

```yaml
services:
  agent-gateway:  # was: tools-provider
    container_name: agent-gateway
    # ...
```

#### 4.4 Keycloak Configuration

- Update realm name in export JSON
- Update `configure-master-realm.sh` script
- Note: May require Keycloak admin changes if realm already exists

### Phase 5: Rebuild & Verify (20 min)

```bash
# Reinstall Python packages
cd src/agent-gateway && poetry install
cd src/agent-host && poetry install

# Rebuild UIs
make build-ui

# Rebuild docs
mkdocs build

# Run tests
make test
```

### Phase 6: Validation Checklist (15 min)

- [ ] `make up` - Docker services start correctly
- [ ] `make run` - agent-gateway starts on port 8000
- [ ] `make run-agent` - agent-host starts on port 8001
- [ ] `make test` - All tests pass
- [ ] `mkdocs serve` - Documentation builds and serves
- [ ] VS Code workspace opens correctly
- [ ] Python imports resolve correctly
- [ ] API endpoints respond correctly

### Phase 7: Commit & Merge (10 min)

```bash
git add -A
git commit -m "refactor: rename tools-provider to agent-gateway

- Rename src/tools-provider → src/agent-gateway
- Update all references across codebase
- Update Docker, Keycloak, and VS Code configs
- Update documentation and mkdocs
- Rename ToolProviderClient → AgentGatewayClient

BREAKING CHANGE: Service renamed, update any external references"

git push origin rename/agent-gateway
# Create PR and merge
```

---

## Post-Rename Tasks

### External Updates Required

| System | Update Required |
|--------|-----------------|
| GitHub repo name | Optional: rename repository |
| GitHub Pages URL | Will change if repo renamed |
| Keycloak realm | May need to recreate or update |
| Any CI/CD pipelines | Update paths |
| Any external documentation | Update references |
| Bookmarks/links | Update URLs |

### Communication

- Notify team of rename
- Update any external documentation
- Update any deployment scripts not in repo

---

## Rollback Plan

If issues arise:

```bash
git checkout main
git branch -D rename/agent-gateway
```

---

## Estimated Total Time

| Phase | Time |
|-------|------|
| Preparation | 15 min |
| Directory Renames | 10 min |
| Find & Replace | 30 min |
| File-Specific Updates | 20 min |
| Rebuild & Verify | 20 min |
| Validation | 15 min |
| Commit & Merge | 10 min |
| **Total** | **~2 hours** |

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Broken imports | Medium | High | Run all tests post-rename |
| Keycloak realm issues | Low | Medium | Test auth flow thoroughly |
| Missed references | Low | Low | grep for old names post-rename |
| Docker cache issues | Low | Low | `docker-compose down -v` to clear |

---

## Automation Option

The existing `scripts/rename_project.py` could be enhanced to automate most of this. Alternatively, use VS Code's global find-and-replace with regex support.

---

**Ready to execute when approved.**
