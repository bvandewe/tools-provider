"""
Kitchen Router - Chef/Kitchen Operations with MongoDB Persistence

Endpoints:
- GET /api/kitchen/queue - View pending orders (chef, admin)
- GET /api/kitchen/active - View orders being prepared (chef, admin)
- GET /api/kitchen/ready - View orders ready for pickup (chef, admin)
- POST /api/kitchen/orders/{order_id}/start - Start cooking an order (chef, admin)
- POST /api/kitchen/orders/{order_id}/complete - Mark order as ready (chef, admin)
- POST /api/kitchen/orders/{order_id}/deliver - Mark order as delivered (chef, admin)
"""

import logging
from datetime import datetime, timezone
from typing import Annotated

from app.auth.dependencies import ChefOnly, UserInfo
from app.database import ORDERS_COLLECTION, get_collection
from app.models.schemas import CookingUpdate, KitchenQueueItem, Order, OrderStatus
from fastapi import APIRouter, Depends, HTTPException, status

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Helper Functions
# ============================================================================


def _calculate_wait_time(created_at: datetime) -> int:
    """Calculate wait time in minutes since order was created."""
    now = datetime.now(timezone.utc)
    delta = now - created_at
    return int(delta.total_seconds() / 60)


def _order_to_queue_item(order: Order) -> KitchenQueueItem:
    """Convert an order to a kitchen queue item."""
    return KitchenQueueItem(
        order_id=order.id,
        customer_username=order.customer_username,
        items=order.items,
        status=order.status,
        special_instructions=order.special_instructions,
        created_at=order.created_at,
        wait_time_minutes=_calculate_wait_time(order.created_at),
    )


# ============================================================================
# Kitchen Endpoints
# ============================================================================


@router.get(
    "/queue",
    response_model=list[KitchenQueueItem],
    summary="View kitchen queue",
    description="View orders waiting to be prepared (paid but not started). **Requires chef or admin role.**",
)
async def get_kitchen_queue(
    user: Annotated[UserInfo, Depends(ChefOnly)],
) -> list[KitchenQueueItem]:
    """Get orders waiting to be cooked."""
    logger.info(f"Chef '{user.username}' viewing kitchen queue")

    orders_col = get_collection(ORDERS_COLLECTION)

    # Get paid orders waiting for preparation, sorted by created_at (FIFO)
    cursor = orders_col.find({"status": OrderStatus.PAID.value}).sort("created_at", 1)
    orders = [Order(**doc) async for doc in cursor]

    return [_order_to_queue_item(o) for o in orders]


@router.get(
    "/active",
    response_model=list[KitchenQueueItem],
    summary="View active orders",
    description="View orders currently being prepared. **Requires chef or admin role.**",
)
async def get_active_orders(
    user: Annotated[UserInfo, Depends(ChefOnly)],
) -> list[KitchenQueueItem]:
    """Get orders currently being prepared."""
    logger.info(f"Chef '{user.username}' viewing active orders")

    orders_col = get_collection(ORDERS_COLLECTION)

    # Get orders being prepared, sorted by started_at
    cursor = orders_col.find({"status": OrderStatus.PREPARING.value}).sort("started_at", 1)
    orders = [Order(**doc) async for doc in cursor]

    return [_order_to_queue_item(o) for o in orders]


@router.get(
    "/ready",
    response_model=list[KitchenQueueItem],
    summary="View ready orders",
    description="View orders ready for pickup/delivery. **Requires chef or admin role.**",
)
async def get_ready_orders(
    user: Annotated[UserInfo, Depends(ChefOnly)],
) -> list[KitchenQueueItem]:
    """Get orders ready for pickup/delivery."""
    logger.info(f"Chef '{user.username}' viewing ready orders")

    orders_col = get_collection(ORDERS_COLLECTION)

    # Get ready orders, sorted by completed_at
    cursor = orders_col.find({"status": OrderStatus.READY.value}).sort("completed_at", 1)
    orders = [Order(**doc) async for doc in cursor]

    return [_order_to_queue_item(o) for o in orders]


@router.post(
    "/orders/{order_id}/start",
    response_model=CookingUpdate,
    summary="Start cooking an order",
    description="Mark an order as being prepared. **Requires chef or admin role.**",
)
async def start_cooking(
    order_id: str,
    user: Annotated[UserInfo, Depends(ChefOnly)],
) -> CookingUpdate:
    """Start cooking an order (chef only)."""
    logger.info(f"Chef '{user.username}' starting to cook order: {order_id}")

    orders_col = get_collection(ORDERS_COLLECTION)
    doc = await orders_col.find_one({"id": order_id})

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_id}' not found",
        )

    order = Order(**doc)

    # Validate order status
    if order.status != OrderStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start cooking. Order status is '{order.status.value}', expected 'paid'",
        )

    # Update order in database
    now = datetime.now(timezone.utc)
    await orders_col.update_one(
        {"id": order_id},
        {
            "$set": {
                "status": OrderStatus.PREPARING.value,
                "started_at": now,
                "updated_at": now,
                "chef_id": user.sub,
                "chef_username": user.username,
            }
        },
    )

    logger.info(f"Order {order_id} cooking started by chef '{user.username}'")

    return CookingUpdate(
        order_id=order_id,
        status=OrderStatus.PREPARING,
        chef_id=user.sub,
        chef_username=user.username,
        message=f"Order {order_id} is now being prepared by {user.username}",
        timestamp=now,
    )


@router.post(
    "/orders/{order_id}/complete",
    response_model=CookingUpdate,
    summary="Complete cooking an order",
    description="Mark an order as ready for pickup/delivery. **Requires chef or admin role.**",
)
async def complete_cooking(
    order_id: str,
    user: Annotated[UserInfo, Depends(ChefOnly)],
) -> CookingUpdate:
    """Mark order as ready (chef only)."""
    logger.info(f"Chef '{user.username}' completing order: {order_id}")

    orders_col = get_collection(ORDERS_COLLECTION)
    doc = await orders_col.find_one({"id": order_id})

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_id}' not found",
        )

    order = Order(**doc)

    # Validate order status
    if order.status != OrderStatus.PREPARING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot complete. Order status is '{order.status.value}', expected 'preparing'",
        )

    # Update order in database
    now = datetime.now(timezone.utc)
    await orders_col.update_one(
        {"id": order_id},
        {
            "$set": {
                "status": OrderStatus.READY.value,
                "completed_at": now,
                "updated_at": now,
            }
        },
    )

    logger.info(f"Order {order_id} marked as ready by chef '{user.username}'")

    return CookingUpdate(
        order_id=order_id,
        status=OrderStatus.READY,
        chef_id=user.sub,
        chef_username=user.username,
        message=f"Order {order_id} is ready for pickup/delivery",
        timestamp=now,
    )


@router.post(
    "/orders/{order_id}/deliver",
    response_model=CookingUpdate,
    summary="Mark order as delivered",
    description="Mark a ready order as delivered/completed. **Requires chef or admin role.**",
)
async def deliver_order(
    order_id: str,
    user: Annotated[UserInfo, Depends(ChefOnly)],
) -> CookingUpdate:
    """Mark order as delivered/completed (chef only)."""
    logger.info(f"Chef '{user.username}' marking order as delivered: {order_id}")

    orders_col = get_collection(ORDERS_COLLECTION)
    doc = await orders_col.find_one({"id": order_id})

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_id}' not found",
        )

    order = Order(**doc)

    # Validate order status
    if order.status != OrderStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot mark as delivered. Order status is '{order.status.value}', expected 'ready'",
        )

    # Update order in database
    now = datetime.now(timezone.utc)
    await orders_col.update_one(
        {"id": order_id},
        {
            "$set": {
                "status": OrderStatus.COMPLETED.value,
                "updated_at": now,
            }
        },
    )

    logger.info(f"Order {order_id} marked as delivered by '{user.username}'")

    return CookingUpdate(
        order_id=order_id,
        status=OrderStatus.COMPLETED,
        chef_id=user.sub,
        chef_username=user.username,
        message=f"Order {order_id} has been delivered/completed",
        timestamp=now,
    )
