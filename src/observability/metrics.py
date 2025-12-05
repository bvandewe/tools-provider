"""Business metrics for Tools Provider service.

Defines OpenTelemetry metrics for all aggregates:
- Tasks: Legacy task management
- Sources: Upstream API sources
- SourceTools: Individual tools from sources
- ToolGroups: Tool curation and grouping
"""

from opentelemetry import metrics

meter = metrics.get_meter(__name__)

# =============================================================================
# TASK METRICS (Legacy)
# =============================================================================

tasks_created = meter.create_counter(
    name="tools_provider.tasks.created",
    description="Total tasks created",
    unit="1",
)

tasks_completed = meter.create_counter(
    name="tools_provider.tasks.completed",
    description="Total tasks completed",
    unit="1",
)

tasks_failed = meter.create_counter(
    name="tools_provider.tasks.failed",
    description="Total task failures",
    unit="1",
)

task_processing_time = meter.create_histogram(
    name="tools_provider.task.processing_time",
    description="Time to process task operations",
    unit="ms",
)

# =============================================================================
# SOURCE METRICS
# =============================================================================

sources_registered = meter.create_counter(
    name="tools_provider.sources.registered",
    description="Total upstream sources registered",
    unit="1",
)

sources_deleted = meter.create_counter(
    name="tools_provider.sources.deleted",
    description="Total upstream sources deleted",
    unit="1",
)

sources_refreshed = meter.create_counter(
    name="tools_provider.sources.refreshed",
    description="Total source inventory refreshes",
    unit="1",
)

source_refresh_failures = meter.create_counter(
    name="tools_provider.sources.refresh_failures",
    description="Total source refresh failures",
    unit="1",
)

source_processing_time = meter.create_histogram(
    name="tools_provider.source.processing_time",
    description="Time to process source operations",
    unit="ms",
)

# =============================================================================
# SOURCE TOOL METRICS
# =============================================================================

tools_discovered = meter.create_counter(
    name="tools_provider.tools.discovered",
    description="Total tools discovered from sources",
    unit="1",
)

tools_enabled = meter.create_counter(
    name="tools_provider.tools.enabled",
    description="Total tools enabled by admin",
    unit="1",
)

tools_disabled = meter.create_counter(
    name="tools_provider.tools.disabled",
    description="Total tools disabled by admin",
    unit="1",
)

tools_deleted = meter.create_counter(
    name="tools_provider.tools.deleted",
    description="Total tools deleted",
    unit="1",
)

tools_deprecated = meter.create_counter(
    name="tools_provider.tools.deprecated",
    description="Total tools deprecated (removed from upstream)",
    unit="1",
)

tool_processing_time = meter.create_histogram(
    name="tools_provider.tool.processing_time",
    description="Time to process tool operations",
    unit="ms",
)

# =============================================================================
# TOOL GROUP METRICS
# =============================================================================

tool_groups_created = meter.create_counter(
    name="tools_provider.tool_groups.created",
    description="Total tool groups created",
    unit="1",
)

tool_groups_updated = meter.create_counter(
    name="tools_provider.tool_groups.updated",
    description="Total tool group updates",
    unit="1",
)

tool_groups_deleted = meter.create_counter(
    name="tools_provider.tool_groups.deleted",
    description="Total tool groups deleted",
    unit="1",
)

tool_groups_activated = meter.create_counter(
    name="tools_provider.tool_groups.activated",
    description="Total tool group activations",
    unit="1",
)

tool_groups_deactivated = meter.create_counter(
    name="tools_provider.tool_groups.deactivated",
    description="Total tool group deactivations",
    unit="1",
)

tool_group_selectors_added = meter.create_counter(
    name="tools_provider.tool_groups.selectors_added",
    description="Total selectors added to tool groups",
    unit="1",
)

tool_group_selectors_removed = meter.create_counter(
    name="tools_provider.tool_groups.selectors_removed",
    description="Total selectors removed from tool groups",
    unit="1",
)

tool_group_tools_added = meter.create_counter(
    name="tools_provider.tool_groups.tools_added",
    description="Total explicit tools added to groups",
    unit="1",
)

tool_group_tools_removed = meter.create_counter(
    name="tools_provider.tool_groups.tools_removed",
    description="Total explicit tools removed from groups",
    unit="1",
)

tool_group_tools_excluded = meter.create_counter(
    name="tools_provider.tool_groups.tools_excluded",
    description="Total tools excluded from groups",
    unit="1",
)

tool_group_tools_included = meter.create_counter(
    name="tools_provider.tool_groups.tools_included",
    description="Total tools included (un-excluded) from groups",
    unit="1",
)

tool_group_processing_time = meter.create_histogram(
    name="tools_provider.tool_group.processing_time",
    description="Time to process tool group operations",
    unit="ms",
)

tool_group_resolution_time = meter.create_histogram(
    name="tools_provider.tool_group.resolution_time",
    description="Time to resolve tools for a group",
    unit="ms",
)
