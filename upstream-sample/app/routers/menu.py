"""
Menu Router - Pizzeria Menu Management

Endpoints:
- GET /api/menu - List all menu items (any authenticated user)
- GET /api/menu/{item_id} - Get menu item details (any authenticated user)
- POST /api/menu - Create menu item (manager, admin only)
- PUT /api/menu/{item_id} - Update menu item (manager, admin only)
- DELETE /api/menu/{item_id} - Delete menu item (manager, admin only)
"""

import logging
from datetime import datetime, timezone
from typing import Annotated

from app.auth.dependencies import AnyAuthenticated, ManagerOnly, UserInfo
from app.models.schemas import MenuCategory, MenuItem, MenuItemCreate, MenuItemUpdate
from fastapi import APIRouter, Depends, HTTPException, status

logger = logging.getLogger(__name__)

router = APIRouter()

# ============================================================================
# In-Memory Data Store (Demo Only)
# ============================================================================

_menu_items: dict[str, MenuItem] = {}
_item_counter = 0


def _init_sample_menu():
    """Initialize sample menu items."""
    global _item_counter

    if _menu_items:
        return

    sample_items = [
        MenuItemCreate(
            name="Margherita Pizza",
            description="Classic tomato sauce, fresh mozzarella, basil",
            unit_price_usd=14.99,
            category=MenuCategory.PIZZA,
            ingredients=["tomato sauce", "mozzarella", "basil", "olive oil"],
            allergens=["gluten", "dairy"],
        ),
        MenuItemCreate(
            name="Pepperoni Pizza",
            description="Tomato sauce, mozzarella, spicy pepperoni",
            unit_price_usd=16.99,
            category=MenuCategory.PIZZA,
            ingredients=["tomato sauce", "mozzarella", "pepperoni"],
            allergens=["gluten", "dairy"],
        ),
        MenuItemCreate(
            name="Quattro Formaggi",
            description="Four cheese pizza: mozzarella, gorgonzola, parmesan, fontina",
            unit_price_usd=18.99,
            category=MenuCategory.PIZZA,
            ingredients=["mozzarella", "gorgonzola", "parmesan", "fontina"],
            allergens=["gluten", "dairy"],
        ),
        MenuItemCreate(
            name="Spaghetti Carbonara",
            description="Classic Roman pasta with eggs, pecorino, guanciale",
            unit_price_usd=15.99,
            category=MenuCategory.PASTA,
            ingredients=["spaghetti", "eggs", "pecorino", "guanciale", "black pepper"],
            allergens=["gluten", "dairy", "eggs"],
        ),
        MenuItemCreate(
            name="Caesar Salad",
            description="Romaine lettuce, croutons, parmesan, Caesar dressing",
            unit_price_usd=10.99,
            category=MenuCategory.SALAD,
            ingredients=["romaine", "croutons", "parmesan", "caesar dressing"],
            allergens=["gluten", "dairy", "eggs", "fish"],
        ),
        MenuItemCreate(
            name="Tiramisu",
            description="Classic Italian dessert with coffee-soaked ladyfingers",
            unit_price_usd=8.99,
            category=MenuCategory.DESSERT,
            ingredients=["mascarpone", "ladyfingers", "espresso", "cocoa"],
            allergens=["gluten", "dairy", "eggs"],
        ),
        MenuItemCreate(
            name="San Pellegrino",
            description="Sparkling mineral water (750ml)",
            unit_price_usd=4.99,
            category=MenuCategory.BEVERAGE,
            ingredients=["sparkling water"],
            allergens=[],
        ),
        MenuItemCreate(
            name="Bruschetta",
            description="Toasted bread with tomatoes, garlic, basil, olive oil",
            unit_price_usd=7.99,
            category=MenuCategory.APPETIZER,
            ingredients=["bread", "tomatoes", "garlic", "basil", "olive oil"],
            allergens=["gluten"],
        ),
    ]

    for item_data in sample_items:
        _item_counter += 1
        item_id = f"menu_{_item_counter:04d}"
        now = datetime.now(timezone.utc)
        _menu_items[item_id] = MenuItem(
            id=item_id,
            **item_data.model_dump(),
            created_at=now,
            updated_at=now,
        )

    logger.info(f"Initialized {len(_menu_items)} sample menu items")


# Initialize on module load
_init_sample_menu()


# ============================================================================
# Menu Endpoints
# ============================================================================


@router.get(
    "",
    response_model=list[MenuItem],
    summary="List all menu items",
    description="Get all menu items. Available to any authenticated user.",
)
async def list_menu_items(
    user: Annotated[UserInfo, Depends(AnyAuthenticated)],
    category: MenuCategory | None = None,
    available_only: bool = False,
) -> list[MenuItem]:
    """List all menu items with optional filtering."""
    logger.info(f"User '{user.username}' listing menu items (category={category}, available_only={available_only})")

    items = list(_menu_items.values())

    if category:
        items = [item for item in items if item.category == category]

    if available_only:
        items = [item for item in items if item.available]

    return items


@router.get(
    "/{item_id}",
    response_model=MenuItem,
    summary="Get menu item details",
    description="Get details of a specific menu item. Available to any authenticated user.",
)
async def get_menu_item(
    item_id: str,
    user: Annotated[UserInfo, Depends(AnyAuthenticated)],
) -> MenuItem:
    """Get a specific menu item by ID."""
    logger.info(f"User '{user.username}' fetching menu item: {item_id}")

    if item_id not in _menu_items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Menu item '{item_id}' not found",
        )

    return _menu_items[item_id]


@router.post(
    "",
    response_model=MenuItem,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new menu item",
    description="Create a new menu item. **Requires manager or admin role.**",
)
async def create_menu_item(
    item_data: MenuItemCreate,
    user: Annotated[UserInfo, Depends(ManagerOnly)],
) -> MenuItem:
    """Create a new menu item (manager/admin only)."""
    global _item_counter

    logger.info(f"Manager '{user.username}' creating menu item: {item_data.name}")

    _item_counter += 1
    item_id = f"menu_{_item_counter:04d}"
    now = datetime.now(timezone.utc)

    item = MenuItem(
        id=item_id,
        **item_data.model_dump(),
        created_at=now,
        updated_at=now,
    )

    _menu_items[item_id] = item
    logger.info(f"Created menu item: {item_id}")

    return item


@router.put(
    "/{item_id}",
    response_model=MenuItem,
    summary="Update a menu item",
    description="Update an existing menu item. **Requires manager or admin role.**",
)
async def update_menu_item(
    item_id: str,
    item_data: MenuItemUpdate,
    user: Annotated[UserInfo, Depends(ManagerOnly)],
) -> MenuItem:
    """Update an existing menu item (manager/admin only)."""
    logger.info(f"Manager '{user.username}' updating menu item: {item_id}")

    if item_id not in _menu_items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Menu item '{item_id}' not found",
        )

    existing = _menu_items[item_id]
    update_data = item_data.model_dump(exclude_unset=True)

    updated_item = MenuItem(
        id=existing.id,
        name=update_data.get("name", existing.name),
        description=update_data.get("description", existing.description),
        unit_price_usd=update_data.get("unit_price_usd", existing.unit_price_usd),
        category=update_data.get("category", existing.category),
        available=update_data.get("available", existing.available),
        ingredients=update_data.get("ingredients", existing.ingredients),
        allergens=update_data.get("allergens", existing.allergens),
        created_at=existing.created_at,
        updated_at=datetime.now(timezone.utc),
    )

    _menu_items[item_id] = updated_item
    logger.info(f"Updated menu item: {item_id}")

    return updated_item


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a menu item",
    description="Delete a menu item. **Requires manager or admin role.**",
)
async def delete_menu_item(
    item_id: str,
    user: Annotated[UserInfo, Depends(ManagerOnly)],
) -> None:
    """Delete a menu item (manager/admin only)."""
    logger.info(f"Manager '{user.username}' deleting menu item: {item_id}")

    if item_id not in _menu_items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Menu item '{item_id}' not found",
        )

    del _menu_items[item_id]
    logger.info(f"Deleted menu item: {item_id}")
