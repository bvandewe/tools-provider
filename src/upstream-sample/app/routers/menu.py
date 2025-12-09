"""
Menu Router - Pizzeria Menu Management with MongoDB Persistence

Endpoints:
- GET /api/menu - List all menu items (any authenticated user)
- GET /api/menu/{item_id} - Get menu item details (any authenticated user)
- POST /api/menu - Create menu item (manager, admin only)
- PUT /api/menu/{item_id} - Update menu item (manager, admin only)
- DELETE /api/menu/{item_id} - Delete menu item (manager, admin only)
"""

import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import AnyAuthenticated, ManagerOnly, UserInfo
from app.database import MENU_COLLECTION, get_collection, get_next_sequence
from app.models.schemas import MenuCategory, MenuItem, MenuItemCreate, MenuItemUpdate, OperationResponse

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Sample Data Initialization
# ============================================================================


async def init_sample_menu():
    """Initialize sample menu items if collection is empty."""
    menu_col = get_collection(MENU_COLLECTION)

    # Check if we already have items
    count = await menu_col.count_documents({})
    if count > 0:
        logger.info(f"Menu collection already has {count} items, skipping initialization")
        return

    logger.info("Initializing sample menu items...")

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
        seq = await get_next_sequence("menu_items")
        item_id = f"menu_{seq:04d}"
        now = datetime.now(UTC)

        item = MenuItem(
            id=item_id,
            **item_data.model_dump(),
            created_at=now,
            updated_at=now,
        )

        await menu_col.insert_one(item.model_dump())

    logger.info(f"✅ Initialized {len(sample_items)} sample menu items")


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

    menu_col = get_collection(MENU_COLLECTION)

    # Build filter
    filter_query: dict = {}
    if category:
        filter_query["category"] = category.value
    if available_only:
        filter_query["available"] = True

    # Fetch items
    cursor = menu_col.find(filter_query)
    items = [MenuItem(**doc) async for doc in cursor]

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

    menu_col = get_collection(MENU_COLLECTION)
    doc = await menu_col.find_one({"id": item_id})

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Menu item '{item_id}' not found",
        )

    return MenuItem(**doc)


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
    logger.info(f"Manager '{user.username}' creating menu item: {item_data.name}")

    menu_col = get_collection(MENU_COLLECTION)

    seq = await get_next_sequence("menu_items")
    item_id = f"menu_{seq:04d}"
    now = datetime.now(UTC)

    item = MenuItem(
        id=item_id,
        **item_data.model_dump(),
        created_at=now,
        updated_at=now,
    )

    await menu_col.insert_one(item.model_dump())
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

    menu_col = get_collection(MENU_COLLECTION)

    # Find existing item
    existing_doc = await menu_col.find_one({"id": item_id})
    if not existing_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Menu item '{item_id}' not found",
        )

    existing = MenuItem(**existing_doc)
    update_data = item_data.model_dump(exclude_unset=True)

    # Build updated item
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
        updated_at=datetime.now(UTC),
    )

    # Update in database
    await menu_col.replace_one({"id": item_id}, updated_item.model_dump())
    logger.info(f"Updated menu item: {item_id}")

    return updated_item


@router.delete(
    "/{item_id}",
    response_model=OperationResponse,
    summary="Delete a menu item",
    description="Delete a menu item. **Requires manager or admin role.**",
)
async def delete_menu_item(
    item_id: str,
    user: Annotated[UserInfo, Depends(ManagerOnly)],
) -> OperationResponse:
    """Delete a menu item (manager/admin only)."""
    logger.info(f"Manager '{user.username}' deleting menu item: {item_id}")

    menu_col = get_collection(MENU_COLLECTION)

    # Check if item exists
    existing_doc = await menu_col.find_one({"id": item_id})
    if not existing_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Menu item '{item_id}' not found",
        )

    # Delete the item
    result = await menu_col.delete_one({"id": item_id})

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete menu item '{item_id}'",
        )

    logger.info(f"Deleted menu item: {item_id}")

    return OperationResponse(
        success=True,
        message=f"Menu item '{item_id}' deleted successfully",
        item_id=item_id,
    )
