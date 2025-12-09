"""Tests for ToolSelector value object.

Tests pattern matching logic for tool selectors including:
- Source patterns
- Name patterns
- Path patterns
- Method patterns
- Tag filtering
- Label filtering
"""

from domain.models import ToolSelector


class TestToolSelectorMatching:
    """Test ToolSelector.matches() method."""

    def test_matches_all_by_default(self) -> None:
        """Test that default selector matches any tool."""
        selector = ToolSelector(id="test-selector")

        assert selector.matches(
            source_name="any-source",
            tool_name="any-tool",
            source_path="/any/path",
            tags=["any-tag"],
        )

    def test_matches_source_pattern(self) -> None:
        """Test matching by source pattern."""
        selector = ToolSelector(id="test-selector", source_pattern="billing-*")

        assert selector.matches(
            source_name="billing-service",
            tool_name="create_invoice",
            source_path="/invoices",
            tags=[],
        )
        assert not selector.matches(
            source_name="user-service",
            tool_name="create_invoice",
            source_path="/invoices",
            tags=[],
        )

    def test_matches_name_pattern(self) -> None:
        """Test matching by name pattern."""
        selector = ToolSelector(id="test-selector", name_pattern="create_*")

        assert selector.matches(
            source_name="any-source",
            tool_name="create_user",
            source_path="/users",
            tags=[],
        )
        assert not selector.matches(
            source_name="any-source",
            tool_name="delete_user",
            source_path="/users",
            tags=[],
        )

    def test_matches_path_pattern(self) -> None:
        """Test matching by path pattern."""
        selector = ToolSelector(id="test-selector", path_pattern="/api/v2/*")

        assert selector.matches(
            source_name="any-source",
            tool_name="any-tool",
            source_path="/api/v2/users",
            tags=[],
        )
        assert not selector.matches(
            source_name="any-source",
            tool_name="any-tool",
            source_path="/api/v1/users",
            tags=[],
        )

    def test_matches_method_pattern(self) -> None:
        """Test matching by HTTP method pattern."""
        selector = ToolSelector(id="test-selector", method_pattern="POST")

        assert selector.matches(
            source_name="any-source",
            tool_name="any-tool",
            source_path="/users",
            tags=[],
            method="POST",
        )
        assert not selector.matches(
            source_name="any-source",
            tool_name="any-tool",
            source_path="/users",
            tags=[],
            method="GET",
        )

    def test_matches_required_tags(self) -> None:
        """Test matching by required tags (all must be present)."""
        selector = ToolSelector(id="test-selector", required_tags=["finance", "billing"])

        # Has all required tags
        assert selector.matches(
            source_name="any-source",
            tool_name="any-tool",
            source_path="/",
            tags=["finance", "billing", "extra"],
        )
        # Missing one required tag
        assert not selector.matches(
            source_name="any-source",
            tool_name="any-tool",
            source_path="/",
            tags=["finance"],
        )

    def test_matches_excluded_tags(self) -> None:
        """Test matching with excluded tags (none must be present)."""
        selector = ToolSelector(id="test-selector", excluded_tags=["deprecated", "internal"])

        # No excluded tags present
        assert selector.matches(
            source_name="any-source",
            tool_name="any-tool",
            source_path="/",
            tags=["finance", "billing"],
        )
        # Has an excluded tag
        assert not selector.matches(
            source_name="any-source",
            tool_name="any-tool",
            source_path="/",
            tags=["finance", "deprecated"],
        )


class TestToolSelectorLabelMatching:
    """Test ToolSelector label filtering."""

    def test_matches_required_label_ids_single(self) -> None:
        """Test matching by single required label ID."""
        selector = ToolSelector(id="test-selector", required_label_ids=["label-123"])

        assert selector.matches(
            source_name="any-source",
            tool_name="any-tool",
            source_path="/",
            tags=[],
            label_ids=["label-123", "label-456"],
        )
        assert not selector.matches(
            source_name="any-source",
            tool_name="any-tool",
            source_path="/",
            tags=[],
            label_ids=["label-456"],
        )

    def test_matches_required_label_ids_multiple(self) -> None:
        """Test matching by multiple required label IDs (all must be present)."""
        selector = ToolSelector(id="test-selector", required_label_ids=["label-123", "label-456"])

        # Has all required labels
        assert selector.matches(
            source_name="any-source",
            tool_name="any-tool",
            source_path="/",
            tags=[],
            label_ids=["label-123", "label-456", "label-789"],
        )
        # Missing one required label
        assert not selector.matches(
            source_name="any-source",
            tool_name="any-tool",
            source_path="/",
            tags=[],
            label_ids=["label-123"],
        )
        # Missing all required labels
        assert not selector.matches(
            source_name="any-source",
            tool_name="any-tool",
            source_path="/",
            tags=[],
            label_ids=[],
        )

    def test_matches_required_label_ids_with_none(self) -> None:
        """Test that label matching handles None label_ids gracefully."""
        selector = ToolSelector(id="test-selector", required_label_ids=["label-123"])

        # When label_ids is None, should not match
        assert not selector.matches(
            source_name="any-source",
            tool_name="any-tool",
            source_path="/",
            tags=[],
            label_ids=None,
        )

    def test_matches_without_required_labels(self) -> None:
        """Test that selector without required labels matches regardless of tool labels."""
        selector = ToolSelector(id="test-selector")  # No required_label_ids

        # Should match even without labels
        assert selector.matches(
            source_name="any-source",
            tool_name="any-tool",
            source_path="/",
            tags=[],
            label_ids=None,
        )
        # Should match with labels
        assert selector.matches(
            source_name="any-source",
            tool_name="any-tool",
            source_path="/",
            tags=[],
            label_ids=["label-123"],
        )


class TestToolSelectorSerialization:
    """Test ToolSelector serialization and deserialization."""

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        selector = ToolSelector(
            id="test-selector",
            source_pattern="billing-*",
            name_pattern="create_*",
            path_pattern="/api/*",
            method_pattern="POST",
            required_tags=["finance"],
            excluded_tags=["deprecated"],
            required_label_ids=["label-123"],
        )

        data = selector.to_dict()

        assert data["id"] == "test-selector"
        assert data["source_pattern"] == "billing-*"
        assert data["name_pattern"] == "create_*"
        assert data["path_pattern"] == "/api/*"
        assert data["method_pattern"] == "POST"
        assert data["required_tags"] == ["finance"]
        assert data["excluded_tags"] == ["deprecated"]
        assert data["required_label_ids"] == ["label-123"]

    def test_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        data = {
            "id": "test-selector",
            "source_pattern": "billing-*",
            "name_pattern": "create_*",
            "path_pattern": "/api/*",
            "method_pattern": "POST",
            "required_tags": ["finance"],
            "excluded_tags": ["deprecated"],
            "required_label_ids": ["label-123"],
        }

        selector = ToolSelector.from_dict(data)

        assert selector.id == "test-selector"
        assert selector.source_pattern == "billing-*"
        assert selector.name_pattern == "create_*"
        assert selector.path_pattern == "/api/*"
        assert selector.method_pattern == "POST"
        assert selector.required_tags == ["finance"]
        assert selector.excluded_tags == ["deprecated"]
        assert selector.required_label_ids == ["label-123"]

    def test_from_dict_with_defaults(self) -> None:
        """Test deserialization with missing optional fields."""
        data = {"id": "test-selector"}

        selector = ToolSelector.from_dict(data)

        assert selector.id == "test-selector"
        assert selector.source_pattern == "*"
        assert selector.name_pattern == "*"
        assert selector.path_pattern is None
        assert selector.method_pattern is None
        assert selector.required_tags == []
        assert selector.excluded_tags == []
        assert selector.required_label_ids == []

    def test_roundtrip_serialization(self) -> None:
        """Test that to_dict/from_dict are symmetric."""
        original = ToolSelector(
            id="test-selector",
            source_pattern="billing-*",
            name_pattern="create_*",
            path_pattern="/api/*",
            method_pattern="POST",
            required_tags=["finance"],
            excluded_tags=["deprecated"],
            required_label_ids=["label-123", "label-456"],
        )

        roundtrip = ToolSelector.from_dict(original.to_dict())

        assert roundtrip.id == original.id
        assert roundtrip.source_pattern == original.source_pattern
        assert roundtrip.name_pattern == original.name_pattern
        assert roundtrip.path_pattern == original.path_pattern
        assert roundtrip.method_pattern == original.method_pattern
        assert roundtrip.required_tags == original.required_tags
        assert roundtrip.excluded_tags == original.excluded_tags
        assert roundtrip.required_label_ids == original.required_label_ids
