"""
Pydantic schemas for the Pizzeria Backend API.

These are simple data models for demo purposes - no persistence layer.
"""

from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


class MenuCategory(str, Enum):
    """Menu item categories."""

    PIZZA = "pizza"
    PASTA = "pasta"
    SALAD = "salad"
    DESSERT = "dessert"
    BEVERAGE = "beverage"
    APPETIZER = "appetizer"


class OrderStatus(str, Enum):
    """Order status progression."""

    PENDING = "pending"  # Order placed, awaiting payment
    PAID = "paid"  # Payment received, waiting for kitchen
    PREPARING = "preparing"  # Chef started cooking
    READY = "ready"  # Food ready for pickup/delivery
    COMPLETED = "completed"  # Order delivered/picked up
    CANCELLED = "cancelled"  # Order cancelled


# ============================================================================
# Menu Schemas
# ============================================================================


class MenuItemBase(BaseModel):
    """Base schema for menu items."""

    # NOTE: Field renamed from 'price' to 'unit_price_usd' to work around a neuroglia
    # deserialization bug where field names containing 'price', 'cost', 'amount', 'total',
    # or 'fee' trigger incorrect Decimal conversion in nested Dict[str, Any] structures.
    # See: notes/NEUROGLIA_DECIMAL_HEURISTIC_BUG.md

    model_config = {"populate_by_name": True}

    name: Annotated[str, Field(min_length=1, max_length=100, description="Item name")]
    description: Annotated[str | None, Field(max_length=500, description="Item description")] = None
    unit_price_usd: Annotated[float, Field(gt=0, description="Unit price in USD")]
    category: MenuCategory
    available: bool = True
    ingredients: list[str] = Field(default_factory=list, description="List of ingredients")
    allergens: list[str] = Field(default_factory=list, description="Allergen information")


class MenuItemCreate(MenuItemBase):
    """Schema for creating a new menu item."""

    pass


class MenuItemUpdate(BaseModel):
    """Schema for updating a menu item (all fields optional)."""

    model_config = {"populate_by_name": True}

    name: Annotated[str | None, Field(min_length=1, max_length=100)] = None
    description: Annotated[str | None, Field(max_length=500)] = None
    unit_price_usd: Annotated[float | None, Field(gt=0)] = None
    category: MenuCategory | None = None
    available: bool | None = None
    ingredients: list[str] | None = None
    allergens: list[str] | None = None


class MenuItem(MenuItemBase):
    """Full menu item schema with ID."""

    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Order Schemas
# ============================================================================


class OrderItemCreate(BaseModel):
    """Schema for items in an order creation request."""

    menu_item_id: str
    quantity: Annotated[int, Field(ge=1, le=99, description="Quantity ordered")]
    special_instructions: str | None = None


class OrderItem(OrderItemCreate):
    """Order item with resolved details."""

    menu_item_name: str
    unit_price: float
    subtotal: float


class OrderCreate(BaseModel):
    """Schema for creating a new order."""

    items: Annotated[list[OrderItemCreate], Field(min_length=1, description="Order items")]
    delivery_address: str | None = Field(None, max_length=500, description="Delivery address (if delivery)")
    special_instructions: str | None = Field(None, max_length=1000, description="Special instructions for the order")


class Order(BaseModel):
    """Full order schema."""

    id: str
    customer_id: str
    customer_username: str
    items: list[OrderItem]
    status: OrderStatus
    total: float
    delivery_address: str | None = None
    special_instructions: str | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None  # When chef started preparing
    completed_at: datetime | None = None  # When order was marked ready
    chef_id: str | None = None  # Chef who prepared the order
    chef_username: str | None = None

    class Config:
        from_attributes = True


# ============================================================================
# Payment Schemas
# ============================================================================


class PaymentMethod(str, Enum):
    """Supported payment methods."""

    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    CASH = "cash"
    DIGITAL_WALLET = "digital_wallet"


class PaymentRequest(BaseModel):
    """Payment request schema."""

    payment_method: PaymentMethod
    # In a real app, this would include card details, etc.
    # For demo, we just simulate payment


class PaymentResponse(BaseModel):
    """Payment response schema."""

    order_id: str
    amount: float
    status: str
    transaction_id: str
    message: str


# ============================================================================
# Kitchen Schemas
# ============================================================================


class KitchenQueueItem(BaseModel):
    """Order as seen in the kitchen queue."""

    order_id: str
    customer_username: str
    items: list[OrderItem]
    status: OrderStatus
    special_instructions: str | None
    created_at: datetime
    wait_time_minutes: int  # Time since order was placed


class CookingUpdate(BaseModel):
    """Response when starting/completing cooking."""

    order_id: str
    status: OrderStatus
    chef_id: str
    chef_username: str
    message: str
    timestamp: datetime


# ============================================================================
# Generic Response Schemas
# ============================================================================


class OperationResponse(BaseModel):
    """Generic operation response for mutations that don't return the full entity."""

    success: bool
    message: str
    item_id: str | None = None
    order_id: str | None = None
