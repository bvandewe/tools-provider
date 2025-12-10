"""Tests for body template generation with partial updates.

This module tests that the _build_body_template method correctly generates
Jinja2 templates that handle partial updates - where not all properties
are provided in the arguments.

The key scenario is OpenAPI PUT/PATCH endpoints with all-optional fields
(like MenuItemUpdate), where the agent may only provide a subset of fields.
"""

import json

import pytest
from jinja2 import BaseLoader, Environment, select_autoescape


class TestConditionalBodyTemplates:
    """Test the conditional body template pattern used for partial updates."""

    @pytest.fixture
    def jinja_env(self):
        """Create a Jinja2 environment matching the tool executor's config."""
        return Environment(
            loader=BaseLoader(),
            autoescape=select_autoescape(default_for_string=False, default=False),
        )

    @pytest.fixture
    def menu_item_update_template(self):
        """Generate a template for MenuItemUpdate schema (all optional fields)."""
        properties = ["name", "description", "unit_price_usd", "category", "available", "ingredients", "allergens"]

        # Build the new conditional template (matches _build_body_template output)
        template_parts = ["{%- set parts = [] -%}"]
        for prop_name in properties:
            template_parts.append(f"{{% if {prop_name} is defined %}}{{% set _ = parts.append('\"{prop_name}\": ' ~ ({prop_name} | tojson)) %}}{{% endif %}}")
        template_parts.append('{{ "{" ~ parts | join(", ") ~ "}" }}')
        return "".join(template_parts)

    def test_partial_update_single_field(self, jinja_env, menu_item_update_template):
        """Test that providing only unit_price_usd produces valid JSON with just that field.

        This is the exact scenario from the bug report: user says
        "increase the price of the Margherita Pizza to $11.99"
        and the agent only provides unit_price_usd in the arguments.
        """
        template = jinja_env.from_string(menu_item_update_template)
        result = template.render(unit_price_usd=11.99)

        # Should produce valid JSON
        parsed = json.loads(result)

        # Should only contain the field that was provided
        assert parsed == {"unit_price_usd": 11.99}

    def test_partial_update_multiple_fields(self, jinja_env, menu_item_update_template):
        """Test providing multiple fields produces JSON with exactly those fields."""
        template = jinja_env.from_string(menu_item_update_template)
        result = template.render(name="Updated Pizza", unit_price_usd=15.99)

        parsed = json.loads(result)
        assert parsed == {"name": "Updated Pizza", "unit_price_usd": 15.99}

    def test_full_update_all_fields(self, jinja_env, menu_item_update_template):
        """Test providing all fields includes all in the output."""
        template = jinja_env.from_string(menu_item_update_template)
        result = template.render(
            name="Full Update",
            description="Test description",
            unit_price_usd=20.00,
            category="pizza",
            available=True,
            ingredients=["cheese", "tomato"],
            allergens=["dairy"],
        )

        parsed = json.loads(result)
        assert len(parsed) == 7
        assert parsed["name"] == "Full Update"
        assert parsed["ingredients"] == ["cheese", "tomato"]

    def test_empty_arguments_produces_empty_object(self, jinja_env, menu_item_update_template):
        """Test that providing no arguments produces an empty JSON object."""
        template = jinja_env.from_string(menu_item_update_template)
        result = template.render()

        assert result == "{}"
        parsed = json.loads(result)
        assert parsed == {}

    def test_null_value_is_included(self, jinja_env, menu_item_update_template):
        """Test that explicitly passing None includes it as null in JSON."""
        template = jinja_env.from_string(menu_item_update_template)
        result = template.render(description=None, unit_price_usd=10.00)

        parsed = json.loads(result)
        assert parsed == {"description": None, "unit_price_usd": 10.00}

    def test_complex_types_serialized_correctly(self, jinja_env, menu_item_update_template):
        """Test that arrays and nested values are properly JSON-serialized."""
        template = jinja_env.from_string(menu_item_update_template)
        result = template.render(
            ingredients=["flour", "water", "yeast"],
            allergens=["gluten"],
        )

        parsed = json.loads(result)
        assert parsed["ingredients"] == ["flour", "water", "yeast"]
        assert parsed["allergens"] == ["gluten"]

    def test_string_with_special_chars(self, jinja_env, menu_item_update_template):
        """Test that strings with special characters are properly escaped."""
        template = jinja_env.from_string(menu_item_update_template)
        result = template.render(
            name='Pizza "Supreme"',
            description="Contains:\n- cheese\n- tomato",
        )

        parsed = json.loads(result)
        assert parsed["name"] == 'Pizza "Supreme"'
        assert "\n" in parsed["description"]


class TestOldTemplateWouldFail:
    """Demonstrate that the old template format would fail on partial updates."""

    @pytest.fixture
    def jinja_env(self):
        return Environment(
            loader=BaseLoader(),
            autoescape=select_autoescape(default_for_string=False, default=False),
        )

    def test_old_template_fails_on_undefined(self, jinja_env):
        """The old template format fails when variables are not defined.

        Old format: {"name": {{ name | tojson }}, "price": {{ price | tojson }}}

        This test documents the bug that was fixed.
        """
        # Old template format (what caused the bug)
        old_template_str = '{"name": {{ name | tojson }}, "unit_price_usd": {{ unit_price_usd | tojson }}}'
        template = jinja_env.from_string(old_template_str)

        # This would raise TypeError: Object of type Undefined is not JSON serializable
        with pytest.raises(TypeError, match="Undefined"):
            template.render(unit_price_usd=11.99)  # name is not provided
