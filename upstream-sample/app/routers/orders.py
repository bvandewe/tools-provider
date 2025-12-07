"""
Orders Router - Customer Order Management

Endpoints:
- GET /api/orders - List all orders (chef, manager, admin)
- GET /api/orders/my - List customer's own orders (customer)
- GET /api/orders/{order_id} - Get order details (owner, chef, manager, admin)
- POST /api/orders - Place a new order (customer)
- POST /api/orders/{order_id}/pay - Pay for an order (order owner)
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated

from app.auth.dependencies import ChefOrManager, CustomerOnly, UserInfo, get_current_user
from app.models.schemas import Order, OrderCreate, OrderItem, OrderStatus, PaymentRequest, PaymentResponse
from app.routers.menu import _menu_items
from fastapi import APIRouter, Depends, HTTPException, status

logger = logging.getLogger(__name__)

router = APIRouter()

# ============================================================================
# In-Memory Data Store (Demo Only)
# ============================================================================

_orders: dict[str, Order] = {}


# ============================================================================
# Order Endpoints
# ============================================================================


@router.get(
    "",
    response_model=list[Order],
    summary="List all orders (Staff)",
    description="List all orders for kitchen/management view. **Requires chef, manager, or admin role.**",
)
async def list_all_orders(
    user: Annotated[UserInfo, Depends(ChefOrManager)],
    status_filter: OrderStatus | None = None,
) -> list[Order]:
    """List all orders (staff only)."""
    logger.info(f"Staff '{user.username}' listing all orders (status_filter={status_filter})")

    orders = list(_orders.values())

    if status_filter:
        orders = [o for o in orders if o.status == status_filter]

    # Sort by created_at descending (newest first)
    orders.sort(key=lambda o: o.created_at, reverse=True)

    return orders


@router.get(
    "/my",
    response_model=list[Order],
    summary="List my orders (Customer)",
    description="List the current customer's orders. **Requires customer role.**",
)
async def list_my_orders(
    user: Annotated[UserInfo, Depends(CustomerOnly)],
) -> list[Order]:
    """List customer's own orders."""
    logger.info(f"Customer '{user.username}' listing their orders")

    orders = [o for o in _orders.values() if o.customer_id == user.sub]

    # Sort by created_at descending (newest first)
    orders.sort(key=lambda o: o.created_at, reverse=True)

    return orders


@router.get(
    "/{order_id}",
    response_model=Order,
    summary="Get order details",
    description="Get details of a specific order. Customers can only view their own orders.",
)
async def get_order(
    order_id: str,
    user: Annotated[UserInfo, Depends(get_current_user)],
) -> Order:
    """Get order details."""
    logger.info(f"User '{user.username}' fetching order: {order_id}")

    if order_id not in _orders:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_id}' not found",
        )

    order = _orders[order_id]

    # Check access: owner, chef, manager, or admin can view
    is_owner = order.customer_id == user.sub
    is_staff = user.has_any_role(["developer", "manager", "admin"])

    if not is_owner and not is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own orders",
        )

    return order


@router.post(
    "",
    response_model=Order,
    status_code=status.HTTP_201_CREATED,
    summary="Place a new order",
    description="Place a new order. **Requires customer role.**",
)
async def create_order(
    order_data: OrderCreate,
    user: Annotated[UserInfo, Depends(CustomerOnly)],
) -> Order:
    """Create a new order (customer only)."""
    logger.info(f"Customer '{user.username}' placing order with {len(order_data.items)} items")

    # Resolve order items and calculate totals
    order_items: list[OrderItem] = []
    total = 0.0

    for item in order_data.items:
        if item.menu_item_id not in _menu_items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Menu item '{item.menu_item_id}' not found",
            )

        menu_item = _menu_items[item.menu_item_id]

        if not menu_item.available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Menu item '{menu_item.name}' is currently unavailable",
            )

        subtotal = menu_item.unit_price_usd * item.quantity
        total += subtotal

        order_items.append(
            OrderItem(
                menu_item_id=item.menu_item_id,
                menu_item_name=menu_item.name,
                quantity=item.quantity,
                unit_price=menu_item.unit_price_usd,
                subtotal=subtotal,
                special_instructions=item.special_instructions,
            )
        )

    # Create order
    order_id = f"order_{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)

    order = Order(
        id=order_id,
        customer_id=user.sub,
        customer_username=user.username,
        items=order_items,
        status=OrderStatus.PENDING,
        total=round(total, 2),
        delivery_address=order_data.delivery_address,
        special_instructions=order_data.special_instructions,
        created_at=now,
        updated_at=now,
    )

    _orders[order_id] = order
    logger.info(f"Created order: {order_id} (total: ${order.total:.2f})")

    return order


@router.post(
    "/{order_id}/pay",
    response_model=PaymentResponse,
    summary="Pay for an order",
    description="Process payment for an order. **Only the order owner can pay.**",
)
async def pay_for_order(
    order_id: str,
    payment: PaymentRequest,
    user: Annotated[UserInfo, Depends(CustomerOnly)],
) -> PaymentResponse:
    """Pay for an order (order owner only)."""
    logger.info(f"Customer '{user.username}' paying for order: {order_id}")

    if order_id not in _orders:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_id}' not found",
        )

    order = _orders[order_id]

    # Verify ownership
    if order.customer_id != user.sub and not user.has_role("admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only pay for your own orders",
        )

    # Check order status
    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order cannot be paid. Current status: {order.status.value}",
        )

    # Simulate payment processing
    transaction_id = f"txn_{uuid.uuid4().hex[:12]}"

    # Update order status
    order.status = OrderStatus.PAID
    order.updated_at = datetime.now(timezone.utc)
    _orders[order_id] = order

    logger.info(f"Payment processed for order {order_id}: ${order.total:.2f} via {payment.payment_method.value}")

    return PaymentResponse(
        order_id=order_id,
        amount=order.total,
        status="success",
        transaction_id=transaction_id,
        message=f"Payment of ${order.total:.2f} processed successfully via {payment.payment_method.value}",
    )


@router.post(
    "/{order_id}/cancel",
    response_model=Order,
    summary="Cancel an order",
    description="Cancel an order. Customers can cancel pending orders; managers can cancel any order.",
)
async def cancel_order(
    order_id: str,
    user: Annotated[UserInfo, Depends(get_current_user)],
) -> Order:
    """Cancel an order."""
    logger.info(f"User '{user.username}' cancelling order: {order_id}")

    if order_id not in _orders:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_id}' not found",
        )

    order = _orders[order_id]
    is_owner = order.customer_id == user.sub
    is_manager = user.has_any_role(["manager", "admin"])

    # Check access
    if not is_owner and not is_manager:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only cancel your own orders",
        )

    # Customers can only cancel pending orders
    if is_owner and not is_manager:
        if order.status not in [OrderStatus.PENDING]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You can only cancel pending orders. Contact management for other cancellations.",
            )

    # Managers can cancel any non-completed order
    if order.status in [OrderStatus.COMPLETED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel a completed order",
        )

    order.status = OrderStatus.CANCELLED
    order.updated_at = datetime.now(timezone.utc)
    _orders[order_id] = order

    logger.info(f"Order {order_id} cancelled by '{user.username}'")

    return order
