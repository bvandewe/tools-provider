"""
Kitchen Router - Chef/Kitchen Operations

Endpoints:
- GET /api/kitchen/queue - View pending orders (chef, admin)
- GET /api/kitchen/active - View orders being prepared (chef, admin)
- POST /api/kitchen/orders/{order_id}/start - Start cooking an order (chef, admin)
- POST /api/kitchen/orders/{order_id}/complete - Mark order as ready (chef, admin)
"""

import logging
from datetime import datetime, timezone
from typing import Annotated

from app.auth.dependencies import ChefOnly, UserInfo
from app.models.schemas import CookingUpdate, KitchenQueueItem, OrderStatus
from app.routers.orders import _orders
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


def _order_to_queue_item(order) -> KitchenQueueItem:
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

    # Get paid orders waiting for preparation
    queue_orders = [o for o in _orders.values() if o.status == OrderStatus.PAID]

    # Sort by created_at (oldest first - FIFO)
    queue_orders.sort(key=lambda o: o.created_at)

    return [_order_to_queue_item(o) for o in queue_orders]


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

    # Get orders being prepared
    active_orders = [o for o in _orders.values() if o.status == OrderStatus.PREPARING]

    # Sort by started_at (oldest first)
    active_orders.sort(key=lambda o: o.started_at or o.created_at)

    return [_order_to_queue_item(o) for o in active_orders]


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

    # Get ready orders
    ready_orders = [o for o in _orders.values() if o.status == OrderStatus.READY]

    # Sort by completed_at (oldest first)
    ready_orders.sort(key=lambda o: o.completed_at or o.created_at)

    return [_order_to_queue_item(o) for o in ready_orders]


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

    if order_id not in _orders:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_id}' not found",
        )

    order = _orders[order_id]

    # Validate order status
    if order.status != OrderStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start cooking. Order status is '{order.status.value}', expected 'paid'",
        )

    # Update order
    now = datetime.now(timezone.utc)
    order.status = OrderStatus.PREPARING
    order.started_at = now
    order.updated_at = now
    order.chef_id = user.sub
    order.chef_username = user.username
    _orders[order_id] = order

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

    if order_id not in _orders:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_id}' not found",
        )

    order = _orders[order_id]

    # Validate order status
    if order.status != OrderStatus.PREPARING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot complete. Order status is '{order.status.value}', expected 'preparing'",
        )

    # Update order
    now = datetime.now(timezone.utc)
    order.status = OrderStatus.READY
    order.completed_at = now
    order.updated_at = now

    # If a different chef completes, update chef info
    if order.chef_id != user.sub:
        order.chef_id = user.sub
        order.chef_username = user.username

    _orders[order_id] = order

    logger.info(f"Order {order_id} ready for pickup, completed by '{user.username}'")

    return CookingUpdate(
        order_id=order_id,
        status=OrderStatus.READY,
        chef_id=user.sub,
        chef_username=user.username,
        message=f"Order {order_id} is ready for pickup!",
        timestamp=now,
    )


@router.post(
    "/orders/{order_id}/deliver",
    response_model=CookingUpdate,
    summary="Mark order as delivered/completed",
    description="Mark an order as delivered or picked up. **Requires chef or admin role.**",
)
async def deliver_order(
    order_id: str,
    user: Annotated[UserInfo, Depends(ChefOnly)],
) -> CookingUpdate:
    """Mark order as delivered/completed."""
    logger.info(f"User '{user.username}' marking order as delivered: {order_id}")

    if order_id not in _orders:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_id}' not found",
        )

    order = _orders[order_id]

    # Validate order status
    if order.status != OrderStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot mark as delivered. Order status is '{order.status.value}', expected 'ready'",
        )

    # Update order
    now = datetime.now(timezone.utc)
    order.status = OrderStatus.COMPLETED
    order.updated_at = now
    _orders[order_id] = order

    logger.info(f"Order {order_id} marked as completed/delivered by '{user.username}'")

    return CookingUpdate(
        order_id=order_id,
        status=OrderStatus.COMPLETED,
        chef_id=order.chef_id or user.sub,
        chef_username=order.chef_username or user.username,
        message=f"Order {order_id} has been delivered/picked up. Thank you!",
        timestamp=now,
    )
